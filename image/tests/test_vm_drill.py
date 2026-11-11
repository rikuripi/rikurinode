"""Tests for image/drill/vm_drill.py, the CI rollback drill's harness.

Only its pure parts run here: the command lines it builds (the VM's network
is restricted, KVM is required, the test key goes only onto the drill's
disk), what it reads from bootc, the drop-ins each case uses, and the
bounded wait; also the pass rule, the two containers-range steps, and cases
4 and 5 (bootc switch refusing an unsigned image, staging a signed one) through
a Drill whose VM commands and journal are stand-ins. The rest of the
orchestration runs only in CI, on an x86_64 runner with KVM
(.github/workflows/image.yml, job drill); its proof is the job's runs,
including the red run. No VM, container or network here.
Records: docs/build-records/2026-10-22-ci-vm-drill.md,
docs/build-records/2026-10-24-drill-orchestration-tests.md,
docs/build-records/2026-10-29-node-refuses-unsigned.md
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "drill"))
import vm_drill as d  # noqa: E402

DIGEST = "sha256:" + "a" * 64


class QemuArgv(unittest.TestCase):
    def setUp(self):
        self.argv = d.qemu_argv(disk="/w/disk.raw", vars_fd="/w/vars.fd", serial_log="/w/serial.log",
                                port=2222, pidfile="/w/qemu.pid")

    def test_requires_kvm(self):
        self.assertIn("-enable-kvm", self.argv)

    def test_network_is_restricted_to_ssh_and_the_drills_registry(self):
        # 2c: one forward out, to the registry on the CI machine's loopback (cases 4 and 5).
        # Repair 1 (CI run 40932208792): a `tcp:` target is a character device QEMU
        # connects once at its start, before the registry exists; `cmd:` starts nc
        # for each connection the guest opens.
        netdev = self.argv[self.argv.index("-netdev") + 1]
        self.assertIn("restrict=on", netdev.split(","))
        self.assertIn("hostfwd=tcp:127.0.0.1:2222-:22", netdev.split(","))
        self.assertIn("guestfwd=tcp:10.0.2.100:5000-cmd:nc -N 127.0.0.1 5000", netdev.split(","))
        # 5c.1: the control plane's two ports, on the CI machine's loopback only.
        self.assertIn("hostfwd=tcp:127.0.0.1:8080-:80", netdev.split(","))
        self.assertIn("hostfwd=tcp:127.0.0.1:8443-:443", netdev.split(","))
        self.assertEqual(netdev.count("hostfwd="), 3)
        self.assertEqual(netdev.count("guestfwd="), 1)
        self.assertEqual(self.argv.count("-netdev"), 1)

    def test_uefi_code_is_read_only_and_vars_are_the_runs_own_copy(self):
        drives = [self.argv[i + 1] for i, a in enumerate(self.argv) if a == "-drive"]
        code = [x for x in drives if d.OVMF_CODE in x]
        self.assertEqual(len(code), 1)
        self.assertIn("readonly=on", code[0])
        self.assertTrue(any("file=/w/vars.fd" in x and "readonly" not in x for x in drives))

    def test_boots_the_drill_disk_and_logs_the_serial_console(self):
        joined = " ".join(self.argv)
        self.assertIn("file=/w/disk.raw", joined)
        self.assertIn("file:/w/serial.log", joined)
        self.assertIn("-daemonize", self.argv)
        self.assertEqual(self.argv[self.argv.index("-pidfile") + 1], "/w/qemu.pid")
        self.assertEqual(self.argv[self.argv.index("-display") + 1], "none")


class InstallArgv(unittest.TestCase):
    def setUp(self):
        self.argv = d.install_argv(image="localhost/rikuri-os:ci", workdir="/w")

    def test_installs_the_image_with_its_own_bootc(self):
        i = self.argv.index("localhost/rikuri-os:ci")
        self.assertEqual(self.argv[i + 1:i + 4], ["bootc", "install", "to-disk"])
        self.assertIn("--via-loopback", self.argv)
        self.assertEqual(self.argv[-1], "/output/disk.raw")

    def test_the_test_key_and_kernel_arguments_go_onto_the_disk_only(self):
        self.assertEqual(self.argv[self.argv.index("--root-ssh-authorized-keys") + 1], "/output/key.pub")
        kargs = [self.argv[i + 1] for i, a in enumerate(self.argv) if a == "--karg"]
        self.assertEqual(sorted(kargs), ["console=ttyS0", "systemd.wants=sshd.service"])
        self.assertIn("/w:/output", self.argv)


class SshArgv(unittest.TestCase):
    def test_key_only_batch_mode_to_the_forwarded_port(self):
        argv = d.ssh_argv(key="/w/key", port=2222, command="true")
        self.assertEqual(argv[0], "ssh")
        for opt in ("BatchMode=yes", "IdentitiesOnly=yes", "PasswordAuthentication=no"):
            self.assertIn(opt, argv)
        self.assertEqual(argv[argv.index("-i") + 1], "/w/key")
        self.assertEqual(argv[argv.index("-p") + 1], "2222")
        self.assertEqual(argv[-2:], ["root@127.0.0.1", "true"])
        self.assertTrue(any(a.startswith("ConnectTimeout=") for a in argv))


class Booted(unittest.TestCase):
    def status(self, booted, rollback=None, staged=None):
        def entry(ref, digest):
            return None if ref is None else {"image": {"image": {"image": ref, "transport": "containers-storage"},
                                                       "imageDigest": digest}}
        return json.dumps({"status": {"booted": entry(*booted), "rollback": entry(*rollback) if rollback else None,
                                      "staged": entry(*staged) if staged else None}})

    def test_reads_the_booted_image_and_digest(self):
        text = self.status(("localhost/rikuri-os:ci", DIGEST), rollback=("localhost/rikuri-os:broken", "sha256:" + "b" * 64))
        self.assertEqual(d.booted(text), ("localhost/rikuri-os:ci", DIGEST))
        self.assertEqual(d.rollback(text), ("localhost/rikuri-os:broken", "sha256:" + "b" * 64))

    def test_unreadable_status_gives_none(self):
        # Verifier I2: a status without a digest must not read as (ref, None),
        # or "still on the installed image" becomes None == None.
        no_digest = json.dumps({"status": {"booted": {"image": {"image": {"image": "localhost/rikuri-os:ci"}}}}})
        null_image = json.dumps({"status": {"booted": {"image": None}}})
        bad_digest = json.dumps({"status": {"booted": {"image": {"image": {"image": "x"}, "imageDigest": 5}}}})
        no_ref = json.dumps({"status": {"booted": {"image": {"image": {}, "imageDigest": DIGEST}}}})
        for text in ("", "nope", "{}", '{"status": {"booted": null}}', '{"status": 3}',
                     no_digest, null_image, bad_digest, no_ref):
            with self.subTest(text=text):
                self.assertIsNone(d.booted(text))
                self.assertIsNone(d.rollback(text))


class CaseInputs(unittest.TestCase):
    def test_broken_variant_fails_a_required_check(self):
        text = d.containerfile_broken("localhost/rikuri-os:ci")
        self.assertTrue(text.startswith("FROM localhost/rikuri-os:ci\n"))
        self.assertIn("/etc/greenboot/check/required.d/", text)
        self.assertIn("exit 1", text)

    def test_label_variant_changes_only_a_label(self):
        text = d.containerfile_label("localhost/rikuri-os:ci", "a")
        self.assertEqual(text, "FROM localhost/rikuri-os:ci\nLABEL rikuri.drill=a\n")

    def test_failing_finalize_dropin_replaces_the_stop_command(self):
        self.assertEqual(d.FINALIZE_FAILS, "[Service]\nExecStop=\nExecStop=/usr/bin/false\n")

    def test_holding_finalize_dropin_keeps_finalize_after_the_hold(self):
        lines = d.FINALIZE_HOLDS.splitlines()
        self.assertEqual(lines[:2], ["[Service]", "ExecStop="])
        self.assertTrue(lines[2].startswith("ExecStop=/usr/bin/sleep "))
        self.assertEqual(lines[3], "ExecStop=/usr/bin/ostree admin finalize-staged")
        hold = int(lines[2].rsplit(" ", 1)[1])
        self.assertGreater(hold, d.POWER_CUT_AFTER_S * 4)

    def test_dropins_live_in_run_only(self):
        self.assertTrue(d.DROPIN.startswith("/run/systemd/system/ostree-finalize-staged.service.d/"))


class SerialConsole(unittest.TestCase):
    """Verifier I1: case 3 cuts the power only once the trigger has stopped
    in *this* shutdown, read from the serial log after the reboot's offset."""
    EARLIER = ("[  OK  ] Stopped greenboot-set-rollback-trigger.service - Greenboot Rollback trigger.\r\n"
               "         Stopping ostree-finalize-staged.service - OSTree Finalize Staged Deployment...\r\n")
    NOW = ("\x1b[0;32m  OK  \x1b[0m] Stopped \x1b[0;1;39mgreenboot-set-rollback-trigger.service\x1b[0m"
           " - Greenboot Rollback trigger.\r\n")

    def test_earlier_shutdowns_before_the_offset_do_not_count(self):
        text = self.EARLIER + "boot again\r\n"
        self.assertFalse(d.trigger_stopped(text, offset=len(text)))
        self.assertFalse(d.trigger_stopped(text + "Starting something\r\n", offset=len(text)))

    def test_the_trigger_stopping_after_the_offset_counts(self):
        text = self.EARLIER + "boot again\r\n"
        self.assertTrue(d.trigger_stopped(text + self.NOW, offset=len(text)))

    def test_the_trigger_still_stopping_does_not_count(self):
        # Follow-up nit: "Stopping" means the trigger is still running.
        text = "x" * 10
        self.assertFalse(d.trigger_stopped(text + "         Stopping greenboot-set-rollback-trigger.service - "
                                                  "Greenboot Rollback trigger...\r\n", offset=len(text)))

    def test_finalize_alone_does_not_count(self):
        text = "x" * 10
        self.assertFalse(d.trigger_stopped(text + "Stopping ostree-finalize-staged.service - OSTree Finalize "
                                                  "Staged Deployment...\r\n", offset=len(text)))


class ContainersRange(unittest.TestCase):
    def test_the_range_exactly_once(self):
        self.assertTrue(d.subid_once("drill:524288:65536\ncontainers:2147483647:2147483648\n"))
        for text in ("", "drill:524288:65536\n", "containers:2147483647:2147483648\n" * 2,
                     "containers:2147483647:2147483647\n", " containers:2147483647:2147483648\n"):
            with self.subTest(text=text):
                self.assertFalse(d.subid_once(text))


class ContainersRangeFirstBoot(unittest.TestCase):
    # Build Record 2026-10-24-drill-first-boot-and-finalize, item (a).
    UID = ("[    5.101] h containers-subid[612]: rikuri-containers-subid: /etc/subuid: "
           "added containers:2147483647:2147483648\n")
    GID = UID.replace("subuid", "subgid")

    def test_added_for_both_files(self):
        self.assertTrue(d.subid_added(self.UID + self.GID))

    def test_anything_less_is_not_added(self):
        unsynced = self.GID.rstrip("\n") + ", but syncing its folder failed (EIO); a power cut now may undo it\n"
        present = self.UID.replace("added containers:2147483647:2147483648",
                                   "containers:2147483647:2147483648 is present")
        for text in ("", self.UID, self.GID, self.UID + unsynced, present + self.GID,
                     self.UID + self.GID.replace("2147483648", "65536")):
            with self.subTest(text=text):
                self.assertFalse(d.subid_added(text))

    def test_unchanged_since_the_first_boot(self):
        first = ["drill:524288:65536\ncontainers:2147483647:2147483648\n"] * 2
        self.assertTrue(d.subid_unchanged(first, list(first)))
        for now in ([first[0], first[1] + "x:1:1\n"], [first[0]], [first[0], ""]):
            with self.subTest(now=now):
                self.assertFalse(d.subid_unchanged(first, now))

    def test_unchanged_still_needs_the_range(self):
        self.assertFalse(d.subid_unchanged(["drill:524288:65536\n"] * 2, ["drill:524288:65536\n"] * 2))

    def test_unchanged_needs_both_files(self):
        # Verifier nit 1: all() over no files is True; the length guard refuses it.
        self.assertFalse(d.subid_unchanged([], []))


class UnitAndContainer(unittest.TestCase):
    # Verifier nit 3: Result=success alone is also a unit that never ran.
    def test_the_unit_ran_and_succeeded(self):
        self.assertTrue(d.unit_ran("ActiveState=active\nResult=success\n"))
        for text in ("Result=success\n", "ActiveState=inactive\nResult=success\n",
                     "ActiveState=active\nResult=exit-code\n", ""):
            with self.subTest(text=text):
                self.assertFalse(d.unit_ran(text))

    def test_the_container_started_line_exactly(self):
        self.assertTrue(d.container_started("started\n"))
        for text in ("", "Error: not started\n", "started later\n"):
            with self.subTest(text=text):
                self.assertFalse(d.container_started(text))


class WaitUntil(unittest.TestCase):
    def test_false_or_empty_values_keep_waiting(self):
        values = iter([False, "", 0, [], "done"])
        clock = iter(range(100))
        self.assertEqual(d.wait_until(lambda: next(values), timeout=50, interval=1,
                                      clock=lambda: next(clock), sleep=lambda s: None), "done")

    def test_returns_the_first_true_value(self):
        values = iter([None, None, "ok"])
        clock = iter(range(100))
        self.assertEqual(d.wait_until(lambda: next(values), timeout=50, interval=1,
                                      clock=lambda: next(clock), sleep=lambda s: None), "ok")

    def test_raises_after_the_timeout(self):
        clock = iter(range(0, 1000, 10))
        with self.assertRaises(d.DrillFailure):
            d.wait_until(lambda: None, timeout=30, interval=1, clock=lambda: next(clock),
                         sleep=lambda s: None, what="the VM to answer")


RANGE = "drill:524288:65536\ncontainers:2147483647:2147483648\n"
ADDED = "".join("[    5.1] h containers-subid[612]: rikuri-containers-subid: %s: added "
                "containers:2147483647:2147483648\n" % f for f in d.SUBID_FILES)
WANTED_OK = ("[   10.9] h greenboot[766]:  INFO  greenboot::greenboot > wanted script "
             "/usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid success!\n")
PRESENT = ADDED.replace("added containers:2147483647:2147483648", "containers:2147483647:2147483648 is present")


class StandInDrill(d.Drill):
    """A Drill whose VM is two dicts: file contents and journal text by its
    journalctl arguments. Every journal call is recorded."""

    def __init__(self, artifacts, files, journals):
        super().__init__("localhost/rikuri-os:test", artifacts, artifacts)
        self.files, self.journals, self.journal_calls = files, journals, []
        self.log = lambda message: None

    def vm(self, command, check=True, timeout=300, stdin=None):
        if command.startswith("cat ") and command[4:] in self.files:
            return self.files[command[4:]]
        raise AssertionError("unexpected VM command: %r" % command)

    def journal(self, args):
        self.journal_calls.append(args)
        return self.journals.get(args, "")


class SkippedChecks(unittest.TestCase):
    # greenboot 0.16.4's line for each check greenboot.conf disables (D9; owner, 2026-10-24).
    def test_the_lines_the_first_boot_check_requires(self):
        self.assertEqual(d.DNS_SKIPPED, "Skipping disabled script: 01_repository_dns_check.sh")
        self.assertEqual(d.PLATFORMS_SKIPPED, "Skipping disabled script: 01_update_platforms_check.sh")


class FirstBootChecks(unittest.TestCase):
    # Verifier I1 (2026-10-24): each greenboot condition of the first-boot check is required.
    JOURNAL = ("rikuri-unapplied-update: no rollback trigger set; nothing to do\n"
               " INFO  greenboot::greenboot > Skipping disabled script: 01_repository_dns_check.sh\n"
               " INFO  greenboot::greenboot > Skipping disabled script: 01_update_platforms_check.sh\n"
               " INFO  greenboot            > greenboot health-check passed.\n")
    LINES = {"greenboot passed": "health-check passed",
             "DNS check skipped": "01_repository_dns_check.sh",
             "update-platforms check skipped": "01_update_platforms_check.sh",
             "the check ran": "rikuri-unapplied-update:"}

    def test_every_condition_is_named(self):
        self.assertEqual(list(d.first_boot_checks(self.JOURNAL)), list(self.LINES))

    def test_all_present(self):
        self.assertTrue(all(d.first_boot_checks(self.JOURNAL).values()))

    def test_each_missing_line_fails_its_condition(self):
        for name, fragment in self.LINES.items():
            with self.subTest(name=name):
                journal = "".join(l + "\n" for l in self.JOURNAL.splitlines() if fragment not in l)
                checks = d.first_boot_checks(journal)
                self.assertFalse(checks[name])
                self.assertFalse(all(checks.values()))


class WantedCheck(unittest.TestCase):
    def test_greenboots_success_line_for_the_check(self):
        self.assertTrue(d.wanted_passed(WANTED_OK))
        for text in ("", WANTED_OK.replace("success!", "failed!"), WANTED_OK.replace("50-rikuri", "51-rikuri"),
                     "wanted script /etc/greenboot/check/wanted.d/50-rikuri-containers-subid success!\n",
                     # mutant 2 (08-mutants.out): the exact line, not the path alone
                     "required script /usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid success!\n"):
            with self.subTest(text=text):
                self.assertFalse(d.wanted_passed(text))


class ContainersRangeSteps(unittest.TestCase):
    # Verifier nit 2 of docs/build-records/2026-10-24-drill-first-boot-and-finalize.md.
    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def drill(self, files=None, journal=ADDED, greenboot=WANTED_OK):
        files = dict.fromkeys(d.SUBID_FILES, RANGE) if files is None else files
        return StandInDrill(self.artifacts, files, {"-b -u rikuri-containers-subid": journal,
                                                    "-b -u greenboot-healthcheck": greenboot})

    def result(self, drill, case):
        return [ok for name, ok, _ in drill.results if name == case]

    def test_a_fresh_install_passes_and_is_kept(self):
        drill = self.drill()
        drill.subid_first_boot()
        self.assertEqual(self.result(drill, "the containers range at the first boot"), [True])
        self.assertEqual(drill.first_subid, [RANGE, RANGE])
        with open(os.path.join(self.artifacts, "01a-subid-first-boot.out"), encoding="utf-8") as f:
            kept = f.read()
        self.assertIn("/etc/subuid:\n" + RANGE, kept)
        self.assertIn(ADDED, kept)

    def test_it_reads_this_boots_journal(self):
        drill = self.drill()
        drill.subid_first_boot()
        self.assertEqual(drill.journal_calls, ["-b -u rikuri-containers-subid", "-b -u greenboot-healthcheck"])

    def test_a_range_already_there_at_the_first_boot_fails(self):
        drill = self.drill(journal=PRESENT)
        drill.subid_first_boot()
        self.assertEqual(self.result(drill, "the containers range at the first boot"), [False])

    def test_added_but_not_once_in_a_file_fails(self):
        for text in (RANGE + "containers:2147483647:2147483648\n", "drill:524288:65536\n", ""):
            with self.subTest(text=text):
                drill = self.drill(files={"/etc/subuid": RANGE, "/etc/subgid": text})
                drill.subid_first_boot()
                self.assertEqual(self.result(drill, "the containers range at the first boot"), [False])

    def test_greenboot_must_have_run_the_wanted_check(self):
        for greenboot in ("", WANTED_OK.replace("success!", "failed!"),
                          WANTED_OK.replace("wanted.d", "required.d").replace("wanted script", "required script")):
            with self.subTest(greenboot=greenboot):
                drill = self.drill(greenboot=greenboot)
                drill.subid_first_boot()
                self.assertEqual(self.result(drill, "the containers range at the first boot"), [False])

    def test_after_reboots_passes_only_unchanged(self):
        drill = self.drill()
        drill.subid_first_boot()
        drill.subid_after_reboots()
        self.assertEqual(self.result(drill, "the containers range after reboots"), [True])
        drill.files["/etc/subgid"] = RANGE + "x:1:1\n"
        drill.subid_after_reboots()
        self.assertEqual(self.result(drill, "the containers range after reboots"), [True, False])

    def test_after_reboots_without_a_first_read_fails(self):
        drill = self.drill()
        drill.subid_after_reboots()
        self.assertEqual(self.result(drill, "the containers range after reboots"), [False])


class Verdict(unittest.TestCase):
    def setUp(self):
        self.ALL = [(case, True, "") for case in sorted(d.EXPECTED)]

    def test_every_check_names_a_step(self):
        self.assertEqual(d.EXPECTED, {
            "first boot", "the containers range at the first boot", "case 1, a failing update",
            "case 2b, finalize fails", "case 3, a power cut during the update",
            "the containers range after reboots", "the containers range",
            "case 4, an unsigned update refused", "case 5, a signed update staged",
            "the control plane runs as its own user", "the CA certificate over HTTP",
            "the API over HTTPS with only the node's CA", "a client without the node's CA is refused",
            "the claim screen on tty2", "the claim screen shows the node's address",
            "only SSH, 80 and 443 listen outside",
            "the firewall opens 80, 443 and mDNS", "greenboot's control plane check",
            "no claim code in the journal",
            "HTTPS as rikurisetup.local with only the node's CA",
            "the certificate follows the node's address without a restart", "the node is named rikurisetup",
            "mDNS on the node's interface", "mDNS listens on 5353, LLMNR does not",
            "mDNS only on the node's interface, with a container's bridge up",
            "the certificate screen over HTTP", "the secure page over HTTPS with only the node's CA",
            "the secure page never over HTTP"})

    def test_all_passed_and_no_error_is_zero(self):
        self.assertEqual(d.verdict(self.ALL, None), 0)

    def test_a_missing_check_fails(self):
        for case in sorted(d.EXPECTED):
            with self.subTest(case=case):
                self.assertEqual(d.verdict([r for r in self.ALL if r[0] != case], None), 1)

    def test_a_failed_check_fails_even_if_it_also_passed(self):
        self.assertEqual(d.verdict(self.ALL + [("the containers range", False, "")], None), 1)
        self.assertEqual(d.verdict(self.ALL + [("an extra step", False, "")], None), 1)

    def test_an_error_fails(self):
        self.assertEqual(d.verdict(self.ALL, "timed out"), 1)


class FirstBootStandIn(StandInDrill):
    """first_boot through stand-ins: the boot wait, bootc's status and the three
    harmless commands it runs answer here; everything else as StandInDrill."""
    HARMLESS = ("getenforce", "grub2-editenv /boot/grub2/grubenv list")

    def __init__(self, artifacts, status_text, greenboot):
        super().__init__(artifacts, dict.fromkeys(d.SUBID_FILES, RANGE),
                         {"-b -u rikuri-containers-subid": ADDED, "-b -u greenboot-healthcheck": greenboot})
        self.status_text = status_text

    def wait_up(self, old_boot=None, timeout=600):
        return "boot-1"

    def status(self):
        return self.status_text

    def vm(self, command, check=True, timeout=300, stdin=None):
        if command in self.HARMLESS or command.startswith("echo 'vm-drill marker' > "):
            return ""
        return super().vm(command, check=check, timeout=timeout, stdin=stdin)


class FirstBoot(unittest.TestCase):
    # Verifier I1, repair 1 mutant 3 (06-repair1-mutants.out): first_boot itself
    # must require every condition, not only first_boot_checks name them.
    STATUS = json.dumps({"status": {"booted": {"image": {"image": {"image": "localhost/rikuri-os:ci",
                                                                   "transport": "registry"},
                                                         "imageDigest": DIGEST}},
                                    "rollback": None, "staged": None}})

    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def first_boot(self, greenboot, status=None):
        drill = FirstBootStandIn(self.artifacts, self.STATUS if status is None else status, greenboot)
        drill.first_boot()
        return [ok for name, ok, _ in drill.results if name == "first boot"]

    def test_a_good_first_boot_passes(self):
        self.assertEqual(self.first_boot(FirstBootChecks.JOURNAL + WANTED_OK), [True])

    def test_each_missing_greenboot_line_fails_it(self):
        for name, fragment in FirstBootChecks.LINES.items():
            with self.subTest(name=name):
                journal = "".join(l + "\n" for l in FirstBootChecks.JOURNAL.splitlines() if fragment not in l)
                self.assertEqual(self.first_boot(journal + WANTED_OK), [False])

    def test_an_unreadable_status_fails_it(self):
        self.assertEqual(self.first_boot(FirstBootChecks.JOURNAL + WANTED_OK, status=""), [False])


# --- 2c: the node's own update command and the signature policy -----------------

def status_json(staged=None, spec="localhost/rikuri-os:ci"):
    deployment = (lambda ref, digest: {"image": {"image": {"image": ref, "transport": "registry"},
                                                 "imageDigest": digest}})
    return json.dumps({"spec": {"image": {"image": spec, "transport": "registry"}},
                       "status": {"booted": deployment("localhost/rikuri-os:ci", DIGEST),
                                  "staged": deployment(*staged) if staged else None, "rollback": None}})


# Repair 2: bootc's refusal as CI run 40933775613 printed it (06-case4.out); the
# guessed line before carried skopeo's "Source image rejected: ", which bootc's
# image proxy does not print.
REFUSED = ("error: Switching: Switching (ostree): Preparing import: Fetching manifest: failed to invoke method "
           "OpenImage: A signature was required, but no signature exists\n")
SIGNED = (d.SIGNED_REF, d.SIGNED_DIGEST)


class PublishedPin(unittest.TestCase):
    def test_the_first_published_image_by_name_and_digest(self):
        # docs/build-records/2026-10-28-publish-signed-image.md, Status: run 40794568497.
        self.assertEqual(d.SIGNED_REF, "ghcr.io/rikuripi/rikurinode:44.20261029.1")
        self.assertEqual(d.SIGNED_DIGEST,
                         "sha256:c984d651db4f15be5dac56fcd974d230bc248536fade4ceee29323abadfdecfd")

    def test_the_signature_tag_names_the_digest(self):
        self.assertEqual(d.sig_tag("sha256:" + "b" * 64), "sha256-" + "b" * 64 + ".sig")


class MirrorFiles(unittest.TestCase):
    def test_the_conf_rewrites_only_the_images_name_to_the_forwarded_address(self):
        conf = d.mirror_conf()
        self.assertEqual(conf.count("[[registry]]"), 1)
        self.assertIn('prefix = "ghcr.io/rikuripi/rikurinode"', conf)
        self.assertIn('location = "10.0.2.100:5000/rikuripi/rikurinode"', conf)
        self.assertIn("insecure = true", conf)
        self.assertNotIn("mirror", conf)   # a mirror could fall back to ghcr.io

    def test_the_files_go_beside_the_shipped_ones_never_over_them(self):
        self.assertEqual(sorted(d.MIRROR_FILES), sorted([
            "/etc/containers/registries.conf.d/99-drill-registry.conf",
            "/etc/containers/registries.d/drill-registry.yaml"]))
        for path in d.MIRROR_FILES:
            self.assertNotIn(path, ("/etc/containers/policy.json", "/etc/containers/registries.d/rikuri.yaml"))


class SeedArgv(unittest.TestCase):
    def setUp(self):
        self.argvs = d.seed_argvs("localhost/rikuri-os:ci")

    def test_the_signed_image_and_its_signature_are_copied_by_digest_with_no_login(self):
        copies = [a for a in self.argvs if "skopeo" in a]
        self.assertEqual(len(copies), 2)
        image, sig = copies
        self.assertIn("docker://ghcr.io/rikuripi/rikurinode@" + d.SIGNED_DIGEST, image)
        self.assertEqual(image[-1], "docker://127.0.0.1:5000/rikuripi/rikurinode:44.20261029.1")
        self.assertIn("docker://ghcr.io/rikuripi/rikurinode:" + d.sig_tag(d.SIGNED_DIGEST), sig)
        self.assertEqual(sig[-1], "docker://127.0.0.1:5000/rikuripi/rikurinode:" + d.sig_tag(d.SIGNED_DIGEST))
        for a in copies:
            self.assertIn("--preserve-digests", a)
            self.assertIn("--dest-tls-verify=false", a)
            self.assertFalse([x for x in a if "authfile" in x or "creds" in x], a)
            self.assertIn("localhost/rikuri-os:ci", a)   # the image's own skopeo

    def test_the_image_under_test_goes_in_unsigned(self):
        push = [a for a in self.argvs if "push" in a]
        self.assertEqual(push, [["sudo", "podman", "push", "-q", "--tls-verify=false", "localhost/rikuri-os:ci",
                                 "docker://127.0.0.1:5000/rikuripi/rikurinode:drill-unsigned"]])


class StagedStatus(unittest.TestCase):
    def test_reads_the_staged_deployment_and_the_spec(self):
        text = status_json(staged=SIGNED, spec=d.SIGNED_REF)
        self.assertEqual(d.staged(text), SIGNED)
        self.assertEqual(d.spec_image(text), d.SIGNED_REF)

    def test_nothing_staged_or_unreadable(self):
        self.assertIsNone(d.staged(status_json()))
        self.assertIsNone(d.staged(""))
        self.assertIsNone(d.spec_image(""))


class SignatureRules(unittest.TestCase):
    def test_unsigned_refused_for_its_reason_with_nothing_staged(self):
        self.assertTrue(d.unsigned_refused(1, REFUSED, status_json()))

    def test_unsigned_accepted_or_staged_fails(self):
        self.assertFalse(d.unsigned_refused(0, "", status_json()))
        self.assertFalse(d.unsigned_refused(0, REFUSED, status_json()))   # mutant m7c (06-mutants-repair2.out)
        self.assertFalse(d.unsigned_refused(1, REFUSED, status_json(staged=("x", DIGEST))))
        self.assertFalse(d.unsigned_refused(1, REFUSED, ""))

    def test_unsigned_refused_for_another_reason_fails(self):
        self.assertFalse(d.unsigned_refused(1, "error: pinging container registry 10.0.2.100:5000: connection "
                                               "refused\n", status_json()))
        self.assertFalse(d.unsigned_refused(1, "error: Switching: failed to invoke method OpenImage: pinging "
                                               "container registry 10.0.2.100:5000: connection refused\n",
                                            status_json()))

    def test_the_reason_must_be_the_proxys_answer_to_opening_the_image(self):
        # Repair 2: the policy's reason directly after the proxy's OpenImage error, not anywhere.
        self.assertFalse(d.unsigned_refused(1, "error: Switching: A signature was required, but no signature "
                                               "exists (a log line); failed to invoke method OpenImage: "
                                               "connection refused\n", status_json()))
        self.assertFalse(d.unsigned_refused(1, "error: failed to invoke method GetManifest: A signature was "
                                               "required, but no signature exists\n", status_json()))

    def test_signed_staged_with_its_digest_and_name(self):
        self.assertTrue(d.signed_staged(0, status_json(staged=SIGNED, spec=d.SIGNED_REF)))

    def test_signed_otherwise_fails(self):
        self.assertFalse(d.signed_staged(1, status_json(staged=SIGNED, spec=d.SIGNED_REF)))
        self.assertFalse(d.signed_staged(0, status_json(staged=(d.SIGNED_REF, DIGEST), spec=d.SIGNED_REF)))
        self.assertFalse(d.signed_staged(0, status_json(staged=("ghcr.io/x:1", d.SIGNED_DIGEST), spec=d.SIGNED_REF)))
        self.assertFalse(d.signed_staged(0, status_json(staged=SIGNED, spec="localhost/rikuri-os:ci")))
        self.assertFalse(d.signed_staged(0, status_json()))


class SignatureStandIn(d.Drill):
    """cases 4 and 5 through stand-ins: bootc switch answers from a dict by
    reference, bootc status is fixed, and files written to the VM are kept."""
    SHIPPED = "docker:\n  ghcr.io/rikuripi/rikurinode:\n    use-sigstore-attachments: true\n"

    def __init__(self, artifacts, answers, status_text):
        super().__init__("localhost/rikuri-os:ci", artifacts, artifacts)
        self.answers, self.status_text, self.switched, self.written = answers, status_text, [], {}
        self.log = lambda message: None

    def bootc_switch(self, ref):
        self.switched.append(ref)
        return self.answers[ref]

    def status(self):
        return self.status_text

    def write_in_vm(self, path, text):
        self.written[path] = text

    def vm(self, command, check=True, timeout=300, stdin=None):
        if command == "cat /etc/containers/registries.d/rikuri.yaml":
            return self.SHIPPED
        raise AssertionError("unexpected VM command: %r" % command)


class SignatureCases(unittest.TestCase):
    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def run_case(self, case, answer, status_text):
        ref = {"case4": d.UNSIGNED_REF, "case5": d.SIGNED_REF}[case]
        drill = SignatureStandIn(self.artifacts, {ref: answer}, status_text)
        getattr(drill, case)()
        self.assertEqual(drill.switched, [ref])
        return [(name, ok) for name, ok, _ in drill.results]

    def test_the_unsigned_reference_is_the_images_own_name(self):
        self.assertEqual(d.UNSIGNED_REF, "ghcr.io/rikuripi/rikurinode:drill-unsigned")

    def test_case4_passes_only_on_the_policys_refusal(self):
        self.assertEqual(self.run_case("case4", (1, REFUSED), status_json()),
                         [("case 4, an unsigned update refused", True)])
        self.assertEqual(self.run_case("case4", (0, ""), status_json(staged=(d.UNSIGNED_REF, DIGEST))),
                         [("case 4, an unsigned update refused", False)])

    def test_case5_passes_only_when_the_signed_image_is_staged(self):
        self.assertEqual(self.run_case("case5", (0, ""), status_json(staged=SIGNED, spec=d.SIGNED_REF)),
                         [("case 5, a signed update staged", True)])
        self.assertEqual(self.run_case("case5", (1, REFUSED), status_json()),
                         [("case 5, a signed update staged", False)])
        # Mutant m14 (02-mutants.out): a switch that succeeds but stages another digest fails too.
        self.assertEqual(self.run_case("case5", (0, ""), status_json(staged=(d.SIGNED_REF, DIGEST),
                                                                     spec=d.SIGNED_REF)),
                         [("case 5, a signed update staged", False)])

    def test_the_mirror_files_are_written_with_the_shipped_setting_renamed(self):
        drill = SignatureStandIn(self.artifacts, {}, "")
        drill.configure_mirror()
        self.assertEqual(sorted(drill.written), sorted(d.MIRROR_FILES))
        self.assertEqual(drill.written["/etc/containers/registries.conf.d/99-drill-registry.conf"], d.mirror_conf())
        self.assertEqual(drill.written["/etc/containers/registries.d/drill-registry.yaml"],
                         "docker:\n  10.0.2.100:5000/rikuripi/rikurinode:\n    use-sigstore-attachments: true\n")

    def test_both_cases_are_required_for_a_pass(self):
        self.assertIn("case 4, an unsigned update refused", d.EXPECTED)
        self.assertIn("case 5, a signed update staged", d.EXPECTED)


# ---- 5c.1: the control plane on the node ---------------------------------------
# docs/build-records/2026-11-06-5c1-control-plane-on-node.md

PEM_CERT = ("-----BEGIN CERTIFICATE-----\n"
            "MAoCAQECAQICAQM=\n"          # base64 of 30 0a 02 01 01 02 01 02 02 01 03, not a real one
            "-----END CERTIFICATE-----\n")
PEM_FP = ":".join("%02X" % b for b in __import__("hashlib").sha256(
    bytes.fromhex("300a020101020102020103")).digest())
SETUP = json.dumps({"claimed": False, "claim": "armed", "ca_fingerprint_sha256": PEM_FP,
                    "names": ["localhost"]}).encode()
SS = ("LISTEN 0 4096 0.0.0.0:443 0.0.0.0:*\n"
      "LISTEN 0 4096 0.0.0.0:80 0.0.0.0:*\n"
      "LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n"
      "LISTEN 0 128 [::]:22 [::]:*\n"
      "LISTEN 0 4096 127.0.0.1:631 0.0.0.0:*\n"
      "LISTEN 0 4096 [::1]:25 [::]:*\n"
      "LISTEN 0 4096 127.0.0.53%lo:53 0.0.0.0:*\n")
SERVICE = "ActiveState=active\nSubState=running\nMainPID=812\n"
SCREEN = "ActiveState=active\nSubState=running\nTTYPath=/dev/tty2\nUser=rikuri-control\n"
ROUTE = "192.0.2.1 via 10.0.2.2 dev enp0s2 src 10.0.2.15 uid 0 \n    cache \n"


def vcs(*lines):
    """What /dev/vcs2 holds: 80 columns a row, padded with spaces, no newlines."""
    return "".join(line.ljust(80) for line in lines + ("",) * (25 - len(lines)))


TTY2 = vcs("Rikuri Node", "", "  Address:  http://10.0.2.15", "",
           "  Certificate fingerprint (SHA-256), to compare with your browser's:")
TTY2_NONE_YET = vcs("Rikuri Node", "",
                    "  Address:  none yet. Connect the node to your router with a network cable.")
POLICY_INFO = ("rikuri-node (active)\n  priority: -100\n  target: CONTINUE\n  ingress-zones: ANY\n"
               "  egress-zones: HOST\n  services: http https mdns\n  ports: \n  protocols: \n")
# The service's process and restarts, as `systemctl show -p MainPID -p NRestarts` gives them.
RUN = "MainPID=812\nNRestarts=0\n"
# 5c.2: resolved's mDNS as `resolvectl mdns` shows it, and the UDP sockets as `ss -Huln` does.
MDNS = "Global: yes\nLink 2 (enp0s2): yes\n"
UDP = ("UNCONN 0 0 0.0.0.0:5353 0.0.0.0:*\n"
       "UNCONN 0 0 [::]:5353 [::]:*\n"
       "UNCONN 0 0 10.0.2.15%enp0s2:68 0.0.0.0:*\n"
       "UNCONN 0 0 127.0.0.53%lo:53 0.0.0.0:*\n"
       "UNCONN 0 0 127.0.0.1:323 0.0.0.0:*\n")
CP_JOURNAL = ("rikuri-control-plane[812]: INFO rikuri_control_plane: claim code armed and not shown: "
              "press Enter on the claim screen at the node (Ctrl+Alt+F2) for a code to use; it replaces this one\n")
REQUIRED_OK = ("INFO greenboot::handler > required script "
               "/usr/lib/greenboot/check/required.d/50-rikuri-control-plane success!\n")


def http(status, body=b"", reason="OK"):
    return (b"HTTP/1.1 %d %s\r\ncontent-length: %d\r\n\r\n" % (status, reason.encode(), len(body))) + body


class ControlPlaneReads(unittest.TestCase):
    def test_the_exposed_ports_are_those_not_on_loopback(self):
        self.assertEqual(d.exposed_ports(SS), {22, 80, 443})
        self.assertEqual(d.exposed_ports(""), set())
        self.assertEqual(d.exposed_ports("LISTEN 0 1 192.168.1.5:8333 0.0.0.0:*\n"), {8333})
        self.assertEqual(d.exposed_ports("LISTEN 0 1 *:9735 *:*\n"), {9735})

    def test_only_ssh_and_the_control_plane_may_listen_outside(self):
        self.assertTrue(d.ports_ok({22, 80, 443}))
        for ports in ({22, 80}, {22, 443}, {22, 80, 443, 8443}, {22, 80, 443, 5355}, set()):
            with self.subTest(ports=ports):
                self.assertFalse(d.ports_ok(ports))

    def test_the_service_runs_and_its_process_is_the_users(self):
        self.assertEqual(d.main_pid(SERVICE), 812)
        self.assertIsNone(d.main_pid(SERVICE.replace("812", "0")))
        self.assertIsNone(d.main_pid("ActiveState=active\n"))
        self.assertTrue(d.service_ok(SERVICE, "rikuri-control"))
        for show, owner in ((SERVICE, "root"), (SERVICE, ""), (SERVICE.replace("running", "auto-restart"),
                                                                 "rikuri-control"),
                            (SERVICE.replace("ActiveState=active", "ActiveState=activating"), "rikuri-control")):
            with self.subTest(show=show, owner=owner):
                self.assertFalse(d.service_ok(show, owner))

    def test_the_claim_screen_holds_tty2_as_the_users(self):
        self.assertTrue(d.screen_ok(SCREEN))
        for old, new in (("tty2", "tty1"), ("User=rikuri-control", "User="), ("running", "dead"),
                         ("ActiveState=active", "ActiveState=failed")):
            with self.subTest(new=new):
                self.assertFalse(d.screen_ok(SCREEN.replace(old, new)))

    def test_the_route_source_is_the_address_the_screen_must_show(self):
        self.assertEqual(d.route_source(ROUTE), "10.0.2.15")
        for text in ("", "192.0.2.1 via 10.0.2.2 dev enp0s2 uid 0\n", "RTNETLINK answers: Network is unreachable\n",
                     "192.0.2.1 dev enp0s2 xsrc 10.0.2.15 uid 0\n",      # not the word src
                     "192.0.2.1 dev enp0s2 src 10.0.2.1534 uid 0\n"):    # not an address
            with self.subTest(text=text):
                self.assertIsNone(d.route_source(text))

    def test_the_screen_shows_exactly_the_routes_address(self):
        self.assertTrue(d.shows_address(TTY2, "10.0.2.15"))
        for screen, address in ((TTY2, "10.0.2.1"),          # a prefix of the shown one
                                (TTY2, "10.0.2.150"),        # the shown one is a prefix
                                (TTY2, None), (TTY2_NONE_YET, "10.0.2.15"), ("", "10.0.2.15"),
                                (vcs("  Address:  http://127.0.0.1"), "127.0.0.1"),
                                (vcs("  Fingerprint:  http://10.0.2.15"), "10.0.2.15"),
                                (vcs("  NoAddress:  http://10.0.2.15"), "10.0.2.15"),   # not the word Address
                                (vcs("  Address: http://10.0.2.15"), "10.0.2.15"),      # the screen writes two spaces
                                (vcs("  Address:   http://10.0.2.15"), "10.0.2.15"),
                                (vcs("  Address:  http://10a0b2c15"), "10.0.2.15")):    # dots are dots
            with self.subTest(screen=screen.strip()[:60], address=address):
                self.assertFalse(d.shows_address(screen, address))

    def test_the_firewall_policy_is_active_with_its_three_services(self):
        self.assertTrue(d.policy_active(POLICY_INFO))
        for old, new in (("(active)", ""), ("services: http https mdns", "services: https mdns"),
                         ("services: http https mdns", "services: http https"),
                         ("services: http https mdns", "services: http https mdns ssh"),
                         ("rikuri-node", "other")):
            with self.subTest(new=new):
                self.assertFalse(d.policy_active(POLICY_INFO.replace(old, new)))
        self.assertFalse(d.policy_active(""))

    def test_mdns_is_on_globally_and_on_the_guests_interface(self):
        self.assertTrue(d.mdns_on(MDNS, "enp0s2"))
        self.assertTrue(d.mdns_on(MDNS + "Link 3 (podman0): yes\n", "enp0s2\n"))
        for status, nic, why in ((MDNS.replace("Global: yes", "Global: no"), "enp0s2", "off globally"),
                                 (MDNS.replace("(enp0s2): yes", "(enp0s2): no"), "enp0s2", "off on the interface"),
                                 (MDNS.replace("(enp0s2): yes", "(enp0s2): resolve"), "enp0s2", "resolving only"),
                                 (MDNS, "enp0s3", "another interface"),
                                 (MDNS, "enp0s", "a prefix of the interface"),
                                 (MDNS, "", "no interface"),
                                 (MDNS + "Link 1 (lo): yes\n", "enp0s2", "on loopback"),
                                 ("", "enp0s2", "no answer")):
            with self.subTest(why=why):
                self.assertFalse(d.mdns_on(status, nic))

    def test_the_guests_address_is_read_without_its_prefix(self):
        self.assertEqual(d.guest_address("10.0.2.15/24\n"), "10.0.2.15")
        for text in ("", "10.0.2.15", "10.0.2/24", "fe80::1/64", "127.0.0.1/8", "10.0.2.1534/24", None):
            with self.subTest(text=text):
                self.assertIsNone(d.guest_address(text))

    def test_the_same_run_is_the_same_process_with_no_restart(self):
        self.assertTrue(d.same_run(RUN, RUN))
        for before, after, why in ((RUN, "MainPID=901\nNRestarts=1\n", "restarted"),
                                   (RUN, "MainPID=812\nNRestarts=1\n", "a restart counted"),
                                   (RUN, "MainPID=901\nNRestarts=0\n", "another process"),
                                   ("MainPID=0\nNRestarts=0\n", "MainPID=0\nNRestarts=0\n", "not running"),
                                   (RUN, "", "no answer"), ("MainPID=812\n", "MainPID=812\n", "no count")):
            with self.subTest(why=why):
                self.assertFalse(d.same_run(before, after))

    def test_mdns_listens_and_llmnr_does_not(self):
        self.assertEqual(d.exposed_ports(UDP), {5353, 68})
        self.assertTrue(d.mdns_listens(d.exposed_ports(UDP)))
        for ports in ({68}, {5353, 5355}, set(), {5355}):
            with self.subTest(ports=ports):
                self.assertFalse(d.mdns_listens(ports))
        self.assertFalse(d.mdns_listens(d.exposed_ports("UNCONN 0 0 127.0.0.1:5353 0.0.0.0:*\n")))

    def test_greenboots_required_check_passed(self):
        self.assertTrue(d.required_passed(REQUIRED_OK))
        for text in ("", REQUIRED_OK.replace("success!", "failed!"),
                     REQUIRED_OK.replace("required script", "wanted script")):
            with self.subTest(text=text):
                self.assertFalse(d.required_passed(text))

    def test_a_response_is_read_by_its_status_line(self):
        self.assertEqual(d.parse_http(http(200, b"x")), (200, b"x"))
        self.assertEqual(d.parse_http(http(421, b"", "Misdirected Request")), (421, b""))
        for raw in (b"", b"garbage", b"HTTP/1.1 abc OK\r\n\r\n"):
            with self.subTest(raw=raw):
                self.assertEqual(d.parse_http(raw), (None, b""))

    def test_the_fingerprint_is_of_the_certificate_fetched(self):
        self.assertEqual(d.pem_fingerprint(PEM_CERT), PEM_FP)

    def test_the_setup_report_is_the_unclaimed_nodes_with_that_ca(self):
        self.assertTrue(d.setup_ok(SETUP, PEM_FP))
        for body in (SETUP.replace(b'"claimed": false', b'"claimed": true'),
                     SETUP.replace(b'"armed"', b'"unarmed"'),
                     SETUP.replace(PEM_FP.encode(), b"AA:BB"),
                     b"not json", b"[]"):
            with self.subTest(body=body):
                self.assertFalse(d.setup_ok(body, PEM_FP))


class ClaimCodeInTheJournal(unittest.TestCase):
    def test_a_code_in_any_form_the_daemon_writes_is_found(self):
        self.assertTrue(d.code_kept_out(CP_JOURNAL))
        for text in ("", CP_JOURNAL + "K7QM-4XD9-TR\n", CP_JOURNAL + "code 2345-6789-AB.\n",
                     CP_JOURNAL + "claim_code=K7QM4XD9TR\n"):
            with self.subTest(text=text):
                self.assertFalse(d.code_kept_out(text))

    def test_other_dashed_words_are_not_codes(self):
        self.assertTrue(d.code_kept_out(CP_JOURNAL + "unit rikuri-control-plane.service started; "
                                                     "fingerprint AB:CD; abcd-efgh-ij\n"))


def ssl_module():
    return __import__("ssl")


class ControlPlaneDrill(d.Drill):
    """A Drill whose VM answers the control plane's commands, and whose two
    ports answer as the forwards would."""

    def __init__(self, artifacts, **over):
        super().__init__("localhost/rikuri-os:test", artifacts, artifacts)
        self.log = lambda message: None
        self.answers = {
            "systemctl show -p ActiveState -p SubState -p MainPID rikuri-control-plane.service": SERVICE,
            "stat -c %U /proc/812": "rikuri-control\n",
            "systemctl show -p ActiveState -p SubState -p TTYPath -p User rikuri-claim-screen.service": SCREEN,
            "systemctl restart rikuri-claim-screen.service": "",
            d.PROBE_ROUTE_ADD: "",
            d.PROBE_ROUTE_DEL: "",
            "ip -4 route get 192.0.2.1": ROUTE,
            "cat /dev/vcs2": TTY2,
            "ss -Htln": SS,
            "firewall-cmd --info-policy=rikuri-node": POLICY_INFO,
            "cat /proc/sys/kernel/hostname": "rikurisetup\n",
            d.NIC: "enp0s2\n",
            "resolvectl mdns": MDNS,
            "ss -Huln": UDP,
            "systemctl show -p MainPID -p NRestarts rikuri-control-plane.service": RUN,
            d.GUEST_ADDRESS: "10.0.2.15/24\n",
        }
        self.plain = over.pop("plain", http(200, PEM_CERT.encode()))
        self.with_ca = over.pop("with_ca", http(200, SETUP))
        # As another name than localhost: the node's mDNS name, or the guest's address.
        self.as_name = {"rikurisetup.local": http(200, SETUP), "10.0.2.15": http(200, SETUP)}
        self.as_name.update(over.pop("as_name", {}))
        # As the guest's address before the probe's route: the boot certificate names no address.
        self.before_route = over.pop("before_route", ssl_module().SSLCertVerificationError(1, "IP address mismatch"))
        self.routed = False
        self.tls = []
        self.before_tls = []
        self.without_ca = over.pop("without_ca", __import__("ssl").SSLCertVerificationError(1, "verify failed"))
        self.greenboot = over.pop("greenboot", REQUIRED_OK)
        self.cp_journal = over.pop("cp_journal", CP_JOURNAL)
        self.answers.update(over.pop("answers", {}))
        self.cafiles = []
        self.commands = []
        self.screen_pause = 0
        self.address_pause = 0

    def vm(self, command, check=True, timeout=300, stdin=None):
        self.commands.append(command)
        if command == d.PROBE_ROUTE_ADD:
            self.routed = True
        elif command == d.PROBE_ROUTE_DEL:
            self.routed = False
        if command in self.answers:
            answer = self.answers[command]
            return answer() if callable(answer) else answer
        raise AssertionError("unexpected VM command: %r" % command)

    def journal(self, args):
        return {"-b -u greenboot-healthcheck": self.greenboot,
                "-b -u rikuri-control-plane": self.cp_journal}.get(args, "")

    def fetch_plain(self, path):
        assert path == "/ca.crt", path
        return self.plain

    def fetch_tls(self, path, cafile, name=d.SERVER_NAME):
        assert path == "/api/setup", path
        self.tls.append((name, cafile))
        self.commands.append("TLS as " + name)
        if name != d.SERVER_NAME and name != d.NODE_NAME and not self.routed:
            assert cafile, "as %s without the node's CA" % name
            self.tls.pop()
            self.commands[-1] = "TLS before the route as " + name
            self.before_tls.append(name)
            answer = self.before_route
            if isinstance(answer, Exception):
                raise answer
            return answer
        if name != d.SERVER_NAME:
            assert cafile, "as %s without the node's CA" % name
            answer = self.as_name.get(name, ssl_module().SSLCertVerificationError(1, "IP address mismatch"))
            answer = answer() if callable(answer) else answer
            if isinstance(answer, Exception):
                raise answer
            return answer
        self.cafiles.append(cafile)
        answer = self.with_ca if cafile else self.without_ca
        if isinstance(answer, Exception):
            raise answer
        return answer


class ControlPlaneSteps(unittest.TestCase):
    CASES = ("the control plane runs as its own user", "the CA certificate over HTTP",
             "the API over HTTPS with only the node's CA", "a client without the node's CA is refused",
             "the claim screen on tty2", "the claim screen shows the node's address",
             "only SSH, 80 and 443 listen outside",
             "the firewall opens 80, 443 and mDNS", "greenboot's control plane check",
             "no claim code in the journal",
             "HTTPS as rikurisetup.local with only the node's CA",
             "the certificate follows the node's address without a restart", "the node is named rikurisetup",
             "mDNS on the node's interface", "mDNS listens on 5353, LLMNR does not")

    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def results(self, **over):
        drill = ControlPlaneDrill(self.artifacts, **over)
        drill.control_plane()
        return drill, {name: ok for name, ok, _ in drill.results}

    def test_every_case_is_expected(self):
        for case in self.CASES:
            self.assertIn(case, d.EXPECTED)

    def test_a_good_node_passes_every_case_and_keeps_the_evidence(self):
        drill, results = self.results()
        self.assertEqual(results, dict.fromkeys(self.CASES, True))
        self.assertEqual(len(drill.cafiles), 2)
        self.assertTrue(drill.cafiles[0] and os.path.isfile(drill.cafiles[0]))
        with open(drill.cafiles[0], encoding="ascii") as f:
            self.assertEqual(f.read(), PEM_CERT)
        self.assertIsNone(drill.cafiles[1], "the second client must trust only the system's CAs")
        self.assertTrue(os.path.isfile(os.path.join(self.artifacts, "02-control-plane.out")))

    def test_each_failure_fails_its_own_case(self):
        ssl = __import__("ssl")
        for case, over in (
                ("the control plane runs as its own user", {"answers": {"stat -c %U /proc/812": "root\n"}}),
                ("the API over HTTPS with only the node's CA", {"with_ca": http(421, b"{}")}),
                ("a client without the node's CA is refused", {"without_ca": http(200, SETUP)}),
                ("a client without the node's CA is refused", {"without_ca": ConnectionResetError(104, "reset")}),
                ("a client without the node's CA is refused", {"without_ca": ssl.SSLError(1, "alert handshake failure")}),
                ("the claim screen on tty2", {"answers": {
                    "systemctl show -p ActiveState -p SubState -p TTYPath -p User rikuri-claim-screen.service":
                        SCREEN.replace("running", "dead")}}),
                ("the claim screen shows the node's address", {"answers": {"cat /dev/vcs2": TTY2_NONE_YET}}),
                ("the claim screen shows the node's address", {"answers": {"cat /dev/vcs2": None}}),
                ("the claim screen shows the node's address", {"answers": {"cat /dev/vcs2": vcs()}}),
                ("only SSH, 80 and 443 listen outside", {"answers": {"ss -Htln": SS + "LISTEN 0 1 0.0.0.0:5355 0.0.0.0:*\n"}}),
                ("the firewall opens 80, 443 and mDNS", {"answers": {"firewall-cmd --info-policy=rikuri-node": ""}}),
                ("HTTPS as rikurisetup.local with only the node's CA", {"as_name": {
                    "rikurisetup.local": ssl_module().SSLCertVerificationError(1, "Hostname mismatch")}}),
                ("HTTPS as rikurisetup.local with only the node's CA", {"as_name": {
                    "rikurisetup.local": http(421, b"{}")}}),
                ("the certificate follows the node's address without a restart", {"as_name": {
                    "10.0.2.15": ssl_module().SSLCertVerificationError(1, "IP address mismatch")}}),
                ("the certificate follows the node's address without a restart", {"as_name": {
                    "10.0.2.15": ConnectionResetError(104, "reset")}}),
                ("the certificate follows the node's address without a restart",
                 {"before_route": http(200, SETUP)}),                       # named it already: no follow seen
                ("the certificate follows the node's address without a restart",
                 {"before_route": ConnectionRefusedError(111, "refused")}),  # no answer is no refusal
                ("the certificate follows the node's address without a restart",
                 {"answers": {d.GUEST_ADDRESS: ""}}),
                ("the certificate follows the node's address without a restart",
                 {"answers": {d.GUEST_ADDRESS: "10.0.2.16/24\n"}}),         # not the route's source
                ("the certificate follows the node's address without a restart", {"answers": {
                    "systemctl show -p MainPID -p NRestarts rikuri-control-plane.service":
                        (lambda runs: lambda: next(runs))(iter([RUN, "MainPID=901\nNRestarts=1\n"]))}}),
                ("the node is named rikurisetup", {"answers": {"cat /proc/sys/kernel/hostname": "localhost\n"}}),
                ("the node is named rikurisetup", {"answers": {"cat /proc/sys/kernel/hostname": None}}),
                ("mDNS on the node's interface", {"answers": {"resolvectl mdns": "Global: no\n"}}),
                ("mDNS on the node's interface", {"answers": {d.NIC: ""}}),
                ("mDNS listens on 5353, LLMNR does not", {"answers": {"ss -Huln": ""}}),
                ("mDNS listens on 5353, LLMNR does not", {"answers": {
                    "ss -Huln": UDP + "UNCONN 0 0 0.0.0.0:5355 0.0.0.0:*\n"}}),
                ("greenboot's control plane check", {"greenboot": ""}),
                ("no claim code in the journal", {"cp_journal": ""}),
                ("no claim code in the journal", {"cp_journal": CP_JOURNAL + "claim code armed: K7QM-4XD9-TR\n"}),
                ("no claim code in the journal", {"cp_journal": CP_JOURNAL + "claim_code=AAAA\n"})):
            with self.subTest(case=case, over=over):
                _, results = self.results(**over)
                self.assertFalse(results[case])
                self.assertEqual([c for c, ok in results.items() if not ok], [case])

    def test_the_screen_is_drawn_again_after_the_network_is_up_then_read(self):
        drill, _ = self.results()
        restart = drill.commands.index("systemctl restart rikuri-claim-screen.service")
        self.assertGreater(drill.commands.index("cat /dev/vcs2"), restart)
        self.assertGreater(drill.commands.index("ip -4 route get 192.0.2.1"), restart)

    def test_the_probe_gets_a_route_for_the_reads_only(self):
        # The drill's network has no default route (restrict=on), as a node
        # without its router: the screen is drawn with a host route to the probe.
        drill, _ = self.results()
        c = drill.commands
        self.assertEqual(c.count(d.PROBE_ROUTE_ADD), 1)
        self.assertEqual(c.count(d.PROBE_ROUTE_DEL), 1)
        self.assertLess(c.index(d.PROBE_ROUTE_ADD), c.index("systemctl restart rikuri-claim-screen.service"))
        self.assertLess(c.index(d.PROBE_ROUTE_ADD), c.index("ip -4 route get 192.0.2.1"))
        self.assertGreater(c.index(d.PROBE_ROUTE_DEL), max(i for i, x in enumerate(c) if x == "cat /dev/vcs2"))
        self.assertIn("192.0.2.1/32", d.PROBE_ROUTE_ADD)
        self.assertNotIn("via", d.PROBE_ROUTE_ADD)
        self.assertIn("192.0.2.1/32", d.PROBE_ROUTE_DEL)

    def test_the_probe_route_goes_to_the_guests_own_interface(self):
        # The command as the VM's root shell runs it, with a stand-in `ip`: it
        # lists the guest's address only when asked for exactly the global
        # IPv4 addresses (loopback comes first otherwise), and prints the
        # route it is asked to add.
        import subprocess
        stand_in = (
            'ip() {\n'
            '  if [ "$*" = "-o -4 addr show scope global" ]; then\n'
            '    echo "2: enp0s2    inet 10.0.2.15/24 brd 10.0.2.255 scope global dynamic noprefixroute enp0s2\\       valid_lft 86313sec preferred_lft 86313sec"\n'
            '  elif [ "$1" = -o ]; then\n'
            '    echo "1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever preferred_lft forever"\n'
            '    echo "2: enp0s2    inet 10.0.2.15/24 brd 10.0.2.255 scope global dynamic noprefixroute enp0s2\\       valid_lft 86313sec preferred_lft 86313sec"\n'
            '  else\n'
            '    echo "ip $*"\n'
            '  fi\n'
            '}\n')
        p = subprocess.run(["sh", "-c", stand_in + d.PROBE_ROUTE_ADD], capture_output=True, text=True, timeout=10)
        self.assertEqual((p.returncode, p.stdout, p.stderr), (0, "ip route replace 192.0.2.1/32 dev enp0s2\n", ""))

    def test_https_is_verified_by_the_nodes_ca_by_each_way_in(self):
        drill, _ = self.results()
        names = [name for name, _ in drill.tls]
        self.assertEqual(sorted(set(names)), ["10.0.2.15", "localhost", "rikurisetup.local"])
        for name, cafile in drill.tls:
            if name != "localhost":
                with self.subTest(name=name):
                    self.assertEqual(cafile, drill.cafiles[0], "trusting only the node's CA")

    def test_the_address_is_tried_while_the_probe_has_its_route(self):
        # The guest's address is in the certificate only while the daemon finds
        # it: with the probe's route in place, and within one look (60 s).
        drill, _ = self.results()
        c = drill.commands
        self.assertLess(c.index(d.PROBE_ROUTE_ADD), c.index("TLS as 10.0.2.15"))
        self.assertGreater(c.index(d.PROBE_ROUTE_DEL), c.index("TLS as 10.0.2.15"))
        self.assertGreaterEqual(d.ADDRESS_TRIES * 5, 2 * 60, "the tries outlast two of the daemon's looks")

    def test_the_address_is_refused_before_the_route_and_the_run_compared_around_it(self):
        # I-2 (verifier, 2026-11-10): the boot certificate must not name the
        # address, and the same process, never restarted, must serve the one that does.
        drill, results = self.results()
        self.assertTrue(results["the certificate follows the node's address without a restart"])
        c = drill.commands
        show = "systemctl show -p MainPID -p NRestarts rikuri-control-plane.service"
        self.assertEqual(drill.before_tls, ["10.0.2.15"])
        self.assertLess(c.index("TLS before the route as 10.0.2.15"), c.index(d.PROBE_ROUTE_ADD))
        self.assertLess(c.index(show), c.index(d.PROBE_ROUTE_ADD))
        self.assertEqual(c.count(show), 2)
        self.assertGreater(len(c) - 1 - c[::-1].index(show), c.index("TLS as 10.0.2.15"))

    def test_the_address_is_tried_again_until_the_daemon_has_reissued(self):
        answers = iter([ssl_module().SSLCertVerificationError(1, "IP address mismatch")] * 3 + [http(200, SETUP)])
        drill, results = self.results(as_name={"10.0.2.15": lambda: next(answers)})
        self.assertTrue(results["the certificate follows the node's address without a restart"])
        self.assertEqual(drill.commands.count("TLS as 10.0.2.15"), 4)

    def test_the_address_is_tried_a_bounded_number_of_times(self):
        drill, results = self.results(as_name={"10.0.2.15": ssl_module().SSLCertVerificationError(1, "mismatch")})
        self.assertFalse(results["the certificate follows the node's address without a restart"])
        self.assertEqual(drill.commands.count("TLS as 10.0.2.15"), d.ADDRESS_TRIES)
        self.assertEqual(drill.commands.count(d.PROBE_ROUTE_DEL), 1)

    def test_a_wrong_or_missing_route_source_fails_the_screen_and_the_address(self):
        # Moved from test_each_failure_fails_its_own_case (5c.2): the route's
        # source is now also the address HTTPS is tried as, so both cases fail.
        for route in (ROUTE.replace("10.0.2.15", "10.0.2.16"), None):
            with self.subTest(route=route):
                _, results = self.results(answers={"ip -4 route get 192.0.2.1": route})
                self.assertEqual(sorted(c for c, ok in results.items() if not ok),
                                 ["the certificate follows the node's address without a restart",
                                  "the claim screen shows the node's address"])

    def test_no_route_source_means_no_address_to_try(self):
        drill, results = self.results(answers={"ip -4 route get 192.0.2.1": None})
        self.assertFalse(results["the certificate follows the node's address without a restart"])
        self.assertNotIn("TLS as None", drill.commands)
        self.assertEqual([n for n, _ in drill.tls if n not in ("localhost", "rikurisetup.local")], [])

    def test_the_probe_route_is_removed_even_when_the_check_fails(self):
        drill, results = self.results(answers={"cat /dev/vcs2": TTY2_NONE_YET})
        self.assertFalse(results["the claim screen shows the node's address"])
        self.assertEqual(drill.commands.count(d.PROBE_ROUTE_DEL), 1)

    def test_a_screen_still_drawing_is_read_again(self):
        screens = iter([vcs(), vcs("Rikuri Node"), TTY2])
        drill, results = self.results(answers={"cat /dev/vcs2": lambda: next(screens)})
        self.assertTrue(results["the claim screen shows the node's address"])
        self.assertEqual(drill.commands.count("cat /dev/vcs2"), 3)

    def test_the_screen_is_read_a_bounded_number_of_times(self):
        drill, results = self.results(answers={"cat /dev/vcs2": TTY2_NONE_YET})
        self.assertFalse(results["the claim screen shows the node's address"])
        self.assertEqual(drill.commands.count("cat /dev/vcs2"), d.SCREEN_READS)

    def test_an_https_port_that_does_not_answer_fails_without_raising(self):
        _, results = self.results(with_ca=ConnectionRefusedError(111, "refused"),
                                  without_ca=ConnectionRefusedError(111, "refused"))
        self.assertFalse(results["the API over HTTPS with only the node's CA"])
        self.assertFalse(results["a client without the node's CA is refused"])

    def test_no_certificate_means_no_https_case_can_pass(self):
        for plain in (http(200, b"not a certificate"), http(404)):
            with self.subTest(plain=plain):
                _, results = self.results(plain=plain)
                self.assertFalse(results["the CA certificate over HTTP"])
                self.assertFalse(results["the API over HTTPS with only the node's CA"])


# PLAT-01 (docs/build-records/2026-11-10-plat01-mdns-allow-list.md): with a
# container on podman's bridge, resolved answers mDNS on the NIC only.
MDNS_BRIDGE_UP = "Global: yes\nLink 2 (enp0s2): yes\nLink 5 (podman0): no\nLink 6 (veth0): no\n"
MDNS_BRIDGE_ON = "Global: yes\nLink 2 (enp0s2): yes\nLink 5 (podman0): yes\nLink 6 (veth0): yes\n"
RAN = "Result=success\nExecMainStatus=0\nExecMainStartTimestampMonotonic=41234567\n"


class MdnsLinksReads(unittest.TestCase):
    def test_mdns_only_on_the_nic_with_the_bridge_present_and_off(self):
        self.assertTrue(d.mdns_only(MDNS_BRIDGE_UP, "enp0s2"))
        for status, nic, why in ((MDNS_BRIDGE_ON, "enp0s2", "the bridge answers"),
                                 (MDNS_BRIDGE_UP.replace("(veth0): no", "(veth0): yes"), "enp0s2", "a veth answers"),
                                 (MDNS_BRIDGE_UP.replace("Link 5 (podman0): no\n", ""), "enp0s2", "no bridge seen"),
                                 (MDNS_BRIDGE_UP.replace("(enp0s2): yes", "(enp0s2): no"), "enp0s2", "the NIC off"),
                                 (MDNS_BRIDGE_UP, "enp0s3", "another NIC"),
                                 (MDNS_BRIDGE_UP, "", "no NIC"),
                                 ("", "enp0s2", "no answer"),
                                 (MDNS_BRIDGE_UP.replace("Global: yes", "Global: no"), "enp0s2", "off globally")):
            with self.subTest(why=why):
                self.assertFalse(d.mdns_only(status, nic))

    def test_a_oneshot_ran_and_succeeded_in_this_boot(self):
        self.assertTrue(d.oneshot_ran(RAN))
        for show, why in ((RAN.replace("41234567", "0"), "never started: Result is success by default"),
                          (RAN.replace("ExecMainStatus=0", "ExecMainStatus=1"), "exited 1"),
                          (RAN.replace("Result=success", "Result=exit-code"), "failed"),
                          ("", "no answer")):
            with self.subTest(why=why):
                self.assertFalse(d.oneshot_ran(show))


class MdnsLinksDrill(d.Drill):
    def __init__(self, artifacts, **over):
        super().__init__("localhost/rikuri-os:test", artifacts, artifacts)
        self.log = lambda message: None
        self.answers = {
            "podman run -d --rm --name drill-mdns --read-only localhost/rikuri-os:test sleep 600 && echo started":
                "3f2a\nstarted\n",
            "resolvectl mdns": MDNS_BRIDGE_UP,
            d.NIC: "enp0s2\n",
            d.SHOW_MDNS_LINKS: RAN,
            d.SHOW_MDNS_BRIDGE: RAN,
            "podman stop -t 1 drill-mdns": "drill-mdns\n",
        }
        self.answers.update(over.pop("answers", {}))
        self.commands = []
        self.mdns_pause = 0

    def vm(self, command, check=True, timeout=300, stdin=None):
        self.commands.append(command)
        if command in self.answers:
            answer = self.answers[command]
            return answer() if callable(answer) else answer
        raise AssertionError("unexpected VM command: %r" % command)


class MdnsLinksSteps(unittest.TestCase):
    CASE = "mDNS only on the node's interface, with a container's bridge up"

    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def results(self, **over):
        drill = MdnsLinksDrill(self.artifacts, **over)
        drill.mdns_links()
        return drill, {name: ok for name, ok, _ in drill.results}

    def test_the_case_is_expected(self):
        self.assertIn(self.CASE, d.EXPECTED)
        self.assertEqual(d.SHOW_MDNS_BRIDGE.split()[-1], "rikuri-mdns-links@podman0.service")

    def test_a_good_node_passes_and_keeps_the_evidence(self):
        drill, results = self.results()
        self.assertEqual(results, {self.CASE: True})
        self.assertTrue(os.path.isfile(os.path.join(self.artifacts, "01c-mdns-links.out")))

    def test_the_container_is_stopped_after_the_reads_even_when_the_check_fails(self):
        for over in ({}, {"answers": {"resolvectl mdns": MDNS_BRIDGE_ON}}):
            with self.subTest(over=over):
                drill, _ = self.results(**over)
                c = drill.commands
                self.assertEqual(c.count("podman stop -t 1 drill-mdns"), 1)
                self.assertGreater(c.index("podman stop -t 1 drill-mdns"),
                                   max(i for i, x in enumerate(c) if x in ("resolvectl mdns", d.SHOW_MDNS_BRIDGE)))

    def test_each_failure_fails_the_case(self):
        for why, answers in (("the bridge answers", {"resolvectl mdns": MDNS_BRIDGE_ON}),
                             ("no container", {"podman run -d --rm --name drill-mdns --read-only "
                                               "localhost/rikuri-os:test sleep 600 && echo started": ""}),
                             ("the boot unit never ran", {d.SHOW_MDNS_LINKS: RAN.replace("41234567", "0")}),
                             ("the bridge's unit failed", {d.SHOW_MDNS_BRIDGE: RAN.replace("Result=success",
                                                                                           "Result=exit-code")}),
                             ("no NIC", {d.NIC: ""})):
            with self.subTest(why=why):
                _, results = self.results(answers=answers)
                self.assertEqual(results, {self.CASE: False})

    def test_a_bridge_still_being_set_is_read_again_a_bounded_number_of_times(self):
        reads = iter([MDNS_BRIDGE_ON, MDNS_BRIDGE_ON, MDNS_BRIDGE_UP])
        drill, results = self.results(answers={"resolvectl mdns": lambda: next(reads)})
        self.assertEqual(results, {self.CASE: True})
        self.assertEqual(drill.commands.count("resolvectl mdns"), 3)
        drill, results = self.results(answers={"resolvectl mdns": MDNS_BRIDGE_ON})
        self.assertEqual(results, {self.CASE: False})
        self.assertEqual(drill.commands.count("resolvectl mdns"), d.MDNS_READS)


# ---- 5c.3a: the setup pages ----------------------------------------------

PAGE_CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; "
            "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


def page(name, status=200, csp=PAGE_CSP, ctype="text/html; charset=utf-8", nosniff=True,
         script='<script type="module" crossorigin src="/assets/cert-1a2b3c.js"></script>'):
    headers = [("content-type", ctype)]
    if csp is not None:
        headers.append(("content-security-policy", csp))
    if nosniff:
        headers.append(("x-content-type-options", "nosniff"))
    body = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="rikuri-page" content="%s">%s</head><body><div id="app"></div></body></html>'
            % (name, script)).encode()
    head = "".join("%s: %s\r\n" % h for h in headers)
    return (b"HTTP/1.1 %d OK\r\n" % status) + head.encode() + (b"content-length: %d\r\n\r\n" % len(body)) + body


REDIRECT_SETUP = b"HTTP/1.1 308 Permanent Redirect\r\nlocation: https://127.0.0.1/setup\r\ncontent-length: 0\r\n\r\n"


class SetupPagesReads(unittest.TestCase):
    def test_the_drill_writes_the_policy_out(self):
        self.assertEqual(d.PAGE_CSP, PAGE_CSP)

    def test_a_header_is_found_whatever_its_case(self):
        raw = b"HTTP/1.1 200 OK\r\nContent-Security-Policy: a\r\nX-Other: b\r\n\r\nbody"
        self.assertEqual(d.http_header(raw, "content-security-policy"), "a")
        self.assertEqual(d.http_header(raw, "X-OTHER"), "b")
        self.assertIsNone(d.http_header(raw, "location"))
        self.assertIsNone(d.http_header(b"garbage", "location"))
        self.assertIsNone(d.http_header(b"", "location"))

    def test_a_good_page_passes(self):
        for name in ("certificate", "secure"):
            ok, detail = d.page_ok(page(name), name)
            self.assertTrue(ok, detail)

    def test_each_defect_fails(self):
        for why, raw in (
                ("not found", page("certificate", status=404)),
                ("not HTML", page("certificate", ctype="text/plain")),
                ("no policy", page("certificate", csp=None)),
                ("an inline script allowed", page("certificate", csp=PAGE_CSP.replace(
                    "script-src 'self'", "script-src 'self' 'unsafe-inline'"))),
                ("another origin allowed", page("certificate", csp=PAGE_CSP.replace(
                    "connect-src 'self'", "connect-src 'self' https://example.com"))),
                ("framing allowed", page("certificate", csp=PAGE_CSP.replace("; frame-ancestors 'none'", ""))),
                ("no nosniff", page("certificate", nosniff=False)),
                ("the other page", page("secure")),
                ("an inline script", page("certificate", script="<script>alert(1)</script>")),
                ("an outside script", page("certificate",
                                           script='<script src="https://cdn.example/x.js"></script>')),
                ("not HTTP", b"garbage"),
                ("nothing", b"")):
            with self.subTest(why=why):
                ok, detail = d.page_ok(raw, "certificate")
                self.assertFalse(ok, detail)
                self.assertTrue(detail)


class SetupPagesDrill(d.Drill):
    """A Drill whose forwarded ports answer as the node's listeners would."""

    def __init__(self, artifacts, **over):
        super().__init__("localhost/rikuri-os:test", artifacts, artifacts)
        self.log = lambda message: None
        self.plain = {"/ca.crt": http(200, PEM_CERT.encode()), "/": page("certificate"), "/setup": REDIRECT_SETUP}
        self.plain.update(over.pop("plain", {}))
        self.secure = over.pop("secure", page("secure"))
        self.requests = []
        assert not over, over

    def vm(self, command, check=True, timeout=300, stdin=None):
        raise AssertionError("the pages' checks run no VM command: %r" % command)

    def fetch_plain(self, path):
        self.requests.append(("plain", path, None))
        answer = self.plain[path]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def fetch_tls(self, path, cafile, name=d.SERVER_NAME):
        self.requests.append(("tls", path, cafile))
        assert path == "/setup", path
        assert name == d.SERVER_NAME, name
        if not cafile:
            raise ssl_module().SSLCertVerificationError(1, "verify failed")
        with open(cafile, encoding="ascii") as f:
            assert f.read() == PEM_CERT
        if isinstance(self.secure, Exception):
            raise self.secure
        return self.secure


class SetupPagesSteps(unittest.TestCase):
    CASES = ("the certificate screen over HTTP", "the secure page over HTTPS with only the node's CA",
             "the secure page never over HTTP")

    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def results(self, **over):
        drill = SetupPagesDrill(self.artifacts, **over)
        drill.setup_pages()
        return drill, {name: ok for name, ok, _ in drill.results}

    def test_every_case_is_expected(self):
        for case in self.CASES:
            self.assertIn(case, d.EXPECTED)

    def test_a_good_node_passes_every_case_and_keeps_the_evidence(self):
        drill, results = self.results()
        self.assertEqual(results, dict.fromkeys(self.CASES, True))
        self.assertIn(("plain", "/", None), drill.requests)
        tls = [r for r in drill.requests if r[0] == "tls"]
        self.assertEqual(len(tls), 1)
        self.assertTrue(tls[0][2], "the secure page is read trusting only the node's CA")
        self.assertTrue(os.path.isfile(os.path.join(self.artifacts, "02b-setup-pages.out")))

    def test_each_failure_fails_its_own_case(self):
        for case, over in (
                ("the certificate screen over HTTP", {"plain": {"/": page("certificate", status=404)}}),
                ("the certificate screen over HTTP", {"plain": {"/": page("certificate", csp=None)}}),
                ("the certificate screen over HTTP", {"plain": {"/": ConnectionResetError(104, "reset")}}),
                ("the secure page over HTTPS with only the node's CA", {"secure": page("certificate")}),
                ("the secure page over HTTPS with only the node's CA", {"secure": page("secure", status=500)}),
                ("the secure page over HTTPS with only the node's CA",
                 {"secure": ssl_module().SSLCertVerificationError(1, "verify failed")}),
                ("the secure page never over HTTP", {"plain": {"/setup": page("secure")}}),
                ("the secure page never over HTTP", {"plain": {"/setup": REDIRECT_SETUP.replace(
                    b"https://", b"http://")}}),
                ("the secure page never over HTTP", {"plain": {"/setup": REDIRECT_SETUP.replace(
                    b"/setup\r\n", b"/\r\n")}}),
                ("the secure page never over HTTP", {"plain": {"/setup": ConnectionResetError(104, "reset")}})):
            with self.subTest(case=case, over=over):
                _, results = self.results(**over)
                self.assertFalse(results[case], case)
                self.assertEqual([c for c in self.CASES if not results[c]], [case])

    def test_no_ca_certificate_fails_the_secure_page_without_a_client_that_trusts_anything(self):
        drill, results = self.results(plain={"/ca.crt": http(404, b"")})
        self.assertFalse(results["the secure page over HTTPS with only the node's CA"])
        self.assertEqual([r for r in drill.requests if r[0] == "tls"], [])



# ---- 5c.3b: the owner's pages ----------------------------------------------

REDIRECT = ("HTTP/1.1 308 Permanent Redirect\r\nlocation: https://127.0.0.1%s\r\ncontent-length: 0\r\n\r\n")
UNCLAIMED_SETUP = http(200, json.dumps({"claimed": False, "claim": "armed", "ca_fingerprint_sha256": "AA",
                                        "names": ["localhost"]}).encode())
CLAIMED_SETUP = http(200, json.dumps({"claimed": True, "claim": "done", "ca_fingerprint_sha256": "AA",
                                      "names": ["localhost"]}).encode())
CLAIM_REFUSED = http(401, b'{"error":"claim refused"}', reason="Unauthorized")


class OwnerPagesDrill(d.Drill):
    """A Drill whose forwarded ports answer as the node's listeners would."""

    def __init__(self, artifacts, **over):
        super().__init__("localhost/rikuri-os:test", artifacts, artifacts)
        self.log = lambda message: None
        self.plain = {"/ca.crt": http(200, PEM_CERT.encode())}
        for path in ("/claim", "/signin"):
            self.plain[path] = (REDIRECT % path).encode()
        self.plain.update(over.pop("plain", {}))
        self.secure = {"/claim": page("secure"), "/signin": page("secure"), "/api/setup": UNCLAIMED_SETUP}
        self.secure.update(over.pop("secure", {}))
        self.claim = over.pop("claim", CLAIM_REFUSED)
        self.requests = []
        assert not over, over

    def vm(self, command, check=True, timeout=300, stdin=None):
        raise AssertionError("the owner's pages' checks run no VM command: %r" % command)

    def fetch_plain(self, path):
        self.requests.append(("plain", "GET", path, None, None))
        answer = self.plain[path]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def _trusted(self, cafile, name):
        assert name == d.SERVER_NAME, name
        if not cafile:
            raise ssl_module().SSLCertVerificationError(1, "verify failed")
        with open(cafile, encoding="ascii") as f:
            assert f.read() == PEM_CERT

    def fetch_tls(self, path, cafile, name=d.SERVER_NAME):
        self.requests.append(("tls", "GET", path, cafile, None))
        self._trusted(cafile, name)
        answer = self.secure[path]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def post_tls(self, path, body, cafile, name=d.SERVER_NAME):
        self.requests.append(("tls", "POST", path, cafile, body))
        self._trusted(cafile, name)
        assert path == "/api/claim", path
        if isinstance(self.claim, Exception):
            raise self.claim
        return self.claim


class OwnerPagesSteps(unittest.TestCase):
    CASES = ("the owner's pages over HTTPS with only the node's CA",
             "a wrong claim code is refused and the node stays unclaimed",
             "the owner's pages never over HTTP")

    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def results(self, **over):
        drill = OwnerPagesDrill(self.artifacts, **over)
        drill.owner_pages()
        return drill, {name: ok for name, ok, _ in drill.results}

    def test_every_case_is_expected(self):
        for case in self.CASES:
            self.assertIn(case, d.EXPECTED)

    def test_a_good_node_passes_every_case_and_keeps_the_evidence(self):
        drill, results = self.results()
        self.assertEqual(results, dict.fromkeys(self.CASES, True))
        posts = [r for r in drill.requests if r[1] == "POST"]
        self.assertEqual(len(posts), 1, "one wrong claim, never more")
        self.assertTrue(posts[0][3], "the claim is sent trusting only the node's CA")
        sent = json.loads(posts[0][4])
        self.assertEqual(sent["code"], d.WRONG_CODE)
        self.assertGreaterEqual(len(sent["password"]), 12)
        evidence = os.path.join(self.artifacts, "02c-owner-pages.out")
        self.assertTrue(os.path.isfile(evidence))
        with open(evidence, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn(sent["password"], text, "the evidence never holds the password it sent")

    def test_the_wrong_code_cannot_be_a_real_one(self):
        # A real code draws from claim::ALPHABET, which has no 0, 1, I, L or O.
        self.assertRegex(d.WRONG_CODE.replace("-", ""), r"[01ILO]")

    def test_each_failure_fails_its_own_case(self):
        for case, over in (
                ("the owner's pages over HTTPS with only the node's CA", {"secure": {"/claim": page("certificate")}}),
                ("the owner's pages over HTTPS with only the node's CA", {"secure": {"/signin": page("secure", status=404)}}),
                ("the owner's pages over HTTPS with only the node's CA",
                 {"secure": {"/claim": ssl_module().SSLCertVerificationError(1, "verify failed")}}),
                ("a wrong claim code is refused and the node stays unclaimed",
                 {"claim": http(201, b'{"csrf_token":"x"}', reason="Created")}),
                ("a wrong claim code is refused and the node stays unclaimed",
                 {"claim": http(403, b'{"error":"origin is not this node"}', reason="Forbidden")}),
                ("a wrong claim code is refused and the node stays unclaimed", {"secure": {"/api/setup": CLAIMED_SETUP}}),
                ("a wrong claim code is refused and the node stays unclaimed", {"claim": ConnectionResetError(104, "reset")}),
                ("the owner's pages never over HTTP", {"plain": {"/claim": page("secure")}}),
                ("the owner's pages never over HTTP",
                 {"plain": {"/signin": (REDIRECT % "/signin").replace("https://", "http://").encode()}}),
                ("the owner's pages never over HTTP", {"plain": {"/claim": ConnectionResetError(104, "reset")}})):
            with self.subTest(case=case, over=over):
                _, results = self.results(**over)
                self.assertFalse(results[case], case)
                self.assertEqual([c for c in self.CASES if not results[c]], [case])

    def test_no_ca_certificate_sends_nothing_over_tls(self):
        drill, results = self.results(plain={"/ca.crt": http(404, b"")})
        self.assertFalse(results["the owner's pages over HTTPS with only the node's CA"])
        self.assertFalse(results["a wrong claim code is refused and the node stays unclaimed"])
        self.assertEqual([r for r in drill.requests if r[0] == "tls"], [])


class OwnerPagesPost(unittest.TestCase):
    """The drill's own POST: to the node's TLS port as the node's name, with
    an Origin the node accepts, JSON, and only the CA it was given."""

    def test_the_request_it_writes(self):
        sent = {}

        class Conn:
            def __init__(self):
                self.out = b""

            def sendall(self, data):
                self.out += data

            def recv(self, n):
                return b""

            def __enter__(self):
                return self

            def __exit__(self, *a):
                sent["raw"] = self.out
                return False

        class Context:
            def wrap_socket(self, raw, server_hostname):
                sent["sni"] = server_hostname
                return Conn()

        real_ctx, real_conn = d.ssl.create_default_context, d.socket.create_connection
        d.ssl.create_default_context = lambda cafile=None: (sent.__setitem__("cafile", cafile), Context())[1]
        d.socket.create_connection = lambda addr, timeout: (sent.__setitem__("addr", addr), Conn())[1]
        try:
            d.Drill("i", "/w", "/a").post_tls("/api/claim", b'{"code":"x"}', "/w/ca.crt")
        finally:
            d.ssl.create_default_context, d.socket.create_connection = real_ctx, real_conn
        self.assertEqual(sent["cafile"], "/w/ca.crt")
        self.assertEqual(sent["addr"], ("127.0.0.1", d.HTTPS_PORT))
        self.assertEqual(sent["sni"], d.SERVER_NAME)
        head, _, body = sent["raw"].partition(b"\r\n\r\n")
        lines = head.split(b"\r\n")
        self.assertEqual(lines[0], b"POST /api/claim HTTP/1.1")
        self.assertIn(b"Host: localhost", lines)
        self.assertIn(b"Origin: https://localhost", lines)
        self.assertIn(b"Content-Type: application/json", lines)
        self.assertIn(b"Content-Length: 12", lines)
        self.assertEqual(body, b'{"code":"x"}')


if __name__ == "__main__":
    unittest.main()
