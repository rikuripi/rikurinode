"""Tests for scripts/quality/safe-run.sh, the outer test-safety layer.

Lesson of the previous repository (2026-10-08): mutation runs of a test that
posted `docker restart lnd` through the real child_process restarted the live
mainnet LND four times. Inside the layer a test cannot reach the machine's
container runtime, systemd, network services or processes — even a child
that clears its environment (round 2's verifier) — and node programs refuse.

These tests never run a real node or container program, even if safe-run.sh
is broken: a program is executed only by the absolute path of a stand-in that
the test has first confirmed it resolved to (round 2's verifier: a broken
script turned the old probes into real `reboot` and `docker restart lnd`).
Run inside an outer layer, the tests still look at the inner one: the
stand-ins must be the inner layer's own, and a marker planted in the outer
`/run` must be hidden (round 3's verifier: the outer layer masked both).
Record: docs/build-records/2026-10-10-bootstrap.md
"""
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

SAFE_RUN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "safe-run.sh")
NO_NAMESPACE_OK = os.environ.get("SAFE_RUN_ALLOW_NO_NAMESPACE") == "1"
INSIDE_A_LAYER = os.environ.get("SAFE_RUN_MODE") == "namespace"


def run(script, env=None):
    return subprocess.run([SAFE_RUN, "sh", "-c", script], capture_output=True, text=True, timeout=60,
                          env=env if env is not None else os.environ.copy())


def isolated():
    r = run("echo ${SAFE_RUN_MODE:-}")
    return r.stdout.strip() == "namespace"


def scripts_programs():
    """The programs safe-run.sh replaces with stand-ins, read from the script."""
    with open(SAFE_RUN) as f:
        m = re.search(r"for p in (.*?); do", f.read(), re.S)
    return set(m.group(1).replace("\\\n", " ").split())


class StandIns(unittest.TestCase):
    PROGRAMS = {"docker", "podman", "nerdctl", "ctr", "runc", "nsenter", "sudo", "pkexec", "su", "systemctl",
                "loginctl", "service", "lncli", "bitcoin-cli", "tapcli", "loop", "pool", "hwi", "tailscale",
                "shutdown", "reboot", "poweroff", "halt", "init", "telinit", "pkill", "killall"}

    def test_the_list_is_the_scripts(self):
        self.assertEqual(scripts_programs(), self.PROGRAMS)

    def test_each_program_resolves_to_this_layers_stand_in_that_refuses(self):
        for prog in sorted(self.PROGRAMS):
            # Run it only if it resolved to THIS layer's stand-in, in the same
            # layer: a broken layer prints where it resolved and runs nothing.
            r = run('w="$(command -v %s)"; if [ -n "$SAFE_RUN_BIN" ] && [ "$w" = "$SAFE_RUN_BIN/%s" ]; then '
                    '"$w" restart lnd; echo "rc=$?"; else echo "not this layer\'s stand-in: $w"; fi' % (prog, prog))
            self.assertNotIn("stand-in:", r.stdout, prog)
            self.assertIn("rc=126", r.stdout, prog)
            self.assertIn("refused by the test safety layer: %s restart lnd" % prog, r.stderr, prog)

    def test_docker_host_points_nowhere(self):
        host = run('printf %s "$DOCKER_HOST"').stdout
        self.assertTrue(host.startswith("unix://"), host)
        self.assertFalse(os.path.exists(host[len("unix://"):]), host)

    def test_the_commands_own_result_passes_through(self):
        self.assertEqual(run("exit 3").returncode, 3)
        self.assertEqual(run("true").returncode, 0)

    def test_stand_ins_are_removed_afterwards(self):
        where = run('printf %s "$SAFE_RUN_BIN"').stdout
        self.assertIn("rikuri-safe-bin.", where)
        self.assertFalse(os.path.exists(where), where)


@unittest.skipIf(NO_NAMESPACE_OK and not isolated(),
                 "namespace isolation unavailable here and explicitly allowed (CI: no live node)")
class Namespace(unittest.TestCase):
    """What a child that ignores PATH and DOCKER_HOST can still reach.

    Each probe runs only once the layer reports namespace mode, so a broken
    layer fails here instead of opening connections to a live node."""

    def setUp(self):
        if not isolated():
            self.fail("safe-run.sh did not report namespace mode; probes not run")

    def test_it_runs_isolated(self):
        self.assertTrue(isolated())

    def test_no_runtime_sockets_even_with_a_clean_environment(self):
        # Inside an outer layer /run is already empty; a marker planted there
        # must not show through, or this test could not fail.
        marker = "/run/rikuri-safe-run-test-marker"
        if INSIDE_A_LAYER:
            open(marker, "w").close()
        try:
            r = run('env -i /bin/sh -c "ls -A /run | wc -l; ls -A /var/run/ | wc -l; '
                    'test -e /var/run/docker.sock && echo SOCKET; test -e /run/systemd/private && echo SYSTEMD; true"')
        finally:
            if INSIDE_A_LAYER:
                os.unlink(marker)
        self.assertEqual(r.stdout.split()[:2], ["0", "0"], r.stdout)
        self.assertNotIn("SOCKET", r.stdout)
        self.assertNotIn("SYSTEMD", r.stdout)

    def test_no_network_not_even_loopback(self):
        # Our own listener on this machine's loopback: a child inside the layer
        # must not reach it (no live service is probed).
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        try:
            probe = ('import socket\n'
                     'try:\n'
                     '    socket.create_connection(("127.0.0.1", %d), timeout=2); print("REACHED")\n'
                     'except OSError: print("unreachable")\n' % port)
            r = run("env -i python3 -c '%s'" % probe)
            self.assertIn("unreachable", r.stdout, r.stdout + r.stderr)
            self.assertNotIn("REACHED", r.stdout)
        finally:
            srv.close()

    def test_loopback_is_up_inside(self):
        # A listener inside the layer, on its own loopback, reached from inside:
        # the control plane's integration tests depend on it (2026-10-20, a
        # session without `ip` ran them with loopback down: NetworkUnreachable).
        probe = ('import socket\n'
                 's = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(1)\n'
                 'try:\n'
                 '    socket.create_connection(s.getsockname(), timeout=2); print("UP")\n'
                 'except OSError as e: print("DOWN", e)\n')
        r = run("python3 -c '%s'" % probe)
        self.assertEqual(r.stdout.strip(), "UP", r.stdout + r.stderr)

    def test_a_loopback_that_cannot_come_up_is_a_refusal(self):
        # A stand-in `ip` that fails, first on PATH and confirmed to be what
        # resolves: the layer must refuse before the command runs, not run it
        # with loopback down (2026-10-20: the error was discarded).
        d = tempfile.mkdtemp()
        try:
            fake = os.path.join(d, "ip")
            with open(fake, "w") as f:
                f.write('#!/bin/sh\necho "stand-in ip: cannot $*" >&2\nexit 1\n')
            os.chmod(fake, 0o755)
            env = dict(os.environ, PATH=d + os.pathsep + os.environ["PATH"])
            self.assertEqual(shutil.which("ip", path=env["PATH"]), fake)
            r = run("echo RAN", env)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertNotIn("RAN", r.stdout)
            self.assertIn("stand-in ip: cannot link set lo up", r.stderr)
            self.assertIn("loopback", r.stderr)
        finally:
            shutil.rmtree(d)

    def test_processes_outside_cannot_be_signalled(self):
        # A process of our own outside the layer (never a live one). Its PID
        # number may exist inside as another process (PID namespaces count
        # from 1 — round 3's verifier: as PID 1 the test runner "reached"
        # itself), so the test watches the process, not the kill's answer.
        sleeper = subprocess.Popen(["sleep", "60"])
        try:
            run("kill -TERM %d 2>/dev/null; true" % sleeper.pid)
            time.sleep(0.2)
            self.assertIsNone(sleeper.poll(), "a process outside the layer was signalled")
        finally:
            sleeper.kill()
            sleeper.wait()


class NodeStartTimes(unittest.TestCase):
    """safe-run.sh reads the live node's container start times before and
    after the command, and fails the run if one changed. Here a stand-in
    `docker`, first on PATH and confirmed to be what resolves, answers
    instead of the real one (round 3's verifier: no test covered this)."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        fake = os.path.join(self.dir, "docker")
        with open(fake, "w") as f:
            f.write('#!/bin/sh\n'
                    'n=$(cat "%(d)s/count" 2>/dev/null || echo 0); n=$((n + 1)); echo "$n" > "%(d)s/count"\n'
                    'cat "%(d)s/answer$n" 2>/dev/null; exit 0\n' % {"d": self.dir})
        os.chmod(fake, 0o755)
        self.env = dict(os.environ, PATH=self.dir + os.pathsep + os.environ["PATH"])
        self.assertEqual(shutil.which("docker", path=self.env["PATH"]), fake)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def answers(self, *texts):
        for n, t in enumerate(texts, 1):
            with open(os.path.join(self.dir, "answer%d" % n), "w") as f:
                f.write(t)

    def test_a_restart_during_the_run_fails_it(self):
        self.answers("/lnd=2026-10-09T20:20:27Z\n", "/lnd=2026-10-11T03:00:00Z\n")
        r = run("true", self.env)
        self.assertEqual(r.returncode, 125, r.stderr)
        self.assertIn("a live node container restarted during the run", r.stderr)

    def test_unchanged_start_times_keep_the_commands_result(self):
        self.answers("/lnd=2026-10-09T20:20:27Z\n", "/lnd=2026-10-09T20:20:27Z\n")
        self.assertEqual(run("exit 3", self.env).returncode, 3)

    def test_no_node_here_is_said(self):
        self.answers("", "")
        r = run("true", self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no live node containers found here", r.stderr)


class WithoutIsolation(unittest.TestCase):
    def test_refuses_unless_explicitly_allowed(self):
        env = dict(os.environ, SAFE_RUN_FORCE_NO_NAMESPACE="1")
        env.pop("SAFE_RUN_ALLOW_NO_NAMESPACE", None)
        r = run("echo RAN", env=env)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("RAN", r.stdout)
        self.assertIn("namespace isolation", r.stderr)

    def test_stand_ins_only_when_allowed_and_said(self):
        env = dict(os.environ, SAFE_RUN_FORCE_NO_NAMESPACE="1", SAFE_RUN_ALLOW_NO_NAMESPACE="1")
        r = run("echo ${SAFE_RUN_MODE}", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "stand-ins only")
        self.assertIn("stand-ins only", r.stderr)


if __name__ == "__main__":
    unittest.main()
