"""Tests for scripts/quality/check_guard_wiring.py: the guard really runs.

Round 2's verifier: the gate's wiring step stayed green with
"disableAllHooks": true, or with a command that merely mentioned guard.py.
The check reads the settings as Claude Code does: hooks enabled, the exact
guard command, before (PreToolUse) the tools in its TOOLS; and (owner,
2026-10-11) the OS sandbox around every shell command, failing closed, with
nothing in the settings that widens it. Round 10 (verifier round 9: nine
widenings that Claude Code's settings schema documents passed): the check is
closed-world — the project file's sandbox is exactly the expected block, the
local file has none, and no permission rule, environment variable or other
hook in either file widens or bypasses it. Rounds 11 and 12 (rounds 10's and
11's verifiers): the top-level keys, the hook events, the guard hook's own
keys and its timeout (required, at most 10 s), the permission mode and the
environment are closed-world too.
Record: docs/build-records/2026-10-10-bootstrap.md
"""
import contextlib
import copy
import io
import json
import os
import signal
import stat
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import check_guard_wiring as w  # noqa: E402

CMD = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/guard.py"'
TOOLS = "Bash|Read|Edit|Write|MultiEdit|NotebookEdit|Grep"


SANDBOX = {"enabled": True, "failIfUnavailable": True, "allowUnsandboxedCommands": False,
           "excludedCommands": ["git push *", "git fetch *", "git pull *"],
           "filesystem": {"denyWrite": ["./scripts/quality/hooks"],
                          "denyRead": ["/home/junc/rikuri/rikurinode/.env", "/home/junc/rikuri/rikurinode/data",
                                       "/run/rikuri"]},
           "network": {"allowedDomains": ["github.com", "api.github.com", "*.githubusercontent.com"]}}


def settings(**kw):
    s = {"hooks": {"PreToolUse": [{"matcher": TOOLS, "hooks": [{"type": "command", "command": CMD, "timeout": 10,
                                                                 "onFailure": "block"}]}]},
         "sandbox": copy.deepcopy(SANDBOX)}
    s.update(kw)
    return s


def setin(d, path, value):
    for k in path[:-1]:
        d = d.setdefault(k, {})
    d[path[-1]] = value


def main_with(project, local):
    """The gate's default run: the project file and the local file beside it."""
    here = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".claude"))
        for name, s in (("settings.json", project), ("settings.local.json", local)):
            with open(os.path.join(d, ".claude", name), "w") as f:
                json.dump(s, f)
        try:
            os.chdir(d)
            return w.main(["check_guard_wiring.py"])
        finally:
            os.chdir(here)


def problems(s):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "settings.json")
        with open(p, "w") as f:
            json.dump(s, f)
        return w.problems(p)


class Wiring(unittest.TestCase):
    def test_this_repositorys_settings_pass(self):
        repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
        self.assertEqual(w.problems(os.path.join(repo, ".claude", "settings.json")), [])

    def test_the_standard_wiring_passes(self):
        self.assertEqual(problems(settings()), [])

    def test_split_entries_or_a_wildcard_pass(self):
        split = settings()
        split["hooks"]["PreToolUse"] = [
            {"matcher": "Bash|Read|Grep",
             "hooks": [{"type": "command", "command": CMD, "timeout": 10, "onFailure": "block"}]},
            {"matcher": "Edit|Write|MultiEdit|NotebookEdit",
             "hooks": [{"type": "command", "command": CMD, "timeout": 10, "onFailure": "block"}]}]
        self.assertEqual(problems(split), [])
        star = settings()
        star["hooks"]["PreToolUse"][0]["matcher"] = "*"
        self.assertEqual(problems(star), [])

    def test_all_hooks_disabled_fails(self):
        self.assertTrue(problems(settings(disableAllHooks=True)))

    def test_a_guard_that_lets_calls_through_when_it_fails_fails(self):
        # Claude Code lets a tool call through when a hook times out or
        # crashes, unless the hook says "onFailure": "block" (hooks reference,
        # 2026-10-11) — then a command too slow for the guard would pass.
        for value in (None, "continue"):
            s = settings()
            hook = s["hooks"]["PreToolUse"][0]["hooks"][0]
            hook.pop("onFailure")
            if value:
                hook["onFailure"] = value
            self.assertTrue(any("onFailure" in p for p in problems(s)), value)

    def test_a_command_that_only_mentions_the_guard_fails(self):
        s = settings()
        s["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = "echo guard.py"
        self.assertTrue(problems(s))

    def test_a_tool_left_out_fails(self):
        s = settings()
        s["hooks"]["PreToolUse"][0]["matcher"] = "Bash|Read|Edit|Write|MultiEdit|NotebookEdit"
        found = problems(s)
        self.assertTrue(any("Grep" in p for p in found), found)

    def test_the_wrong_event_fails(self):
        s = settings()
        s["hooks"] = {"PostToolUse": s["hooks"]["PreToolUse"]}
        self.assertTrue(problems(s))

    def test_the_default_run_also_reads_the_local_settings(self):
        # Round 3's verifier: a check that never read settings.local.json
        # survived every test (mutant W3).
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".claude"))
            with open(os.path.join(d, ".claude", "settings.json"), "w") as f:
                json.dump(settings(), f)
            try:
                os.chdir(d)
                self.assertEqual(w.main(["check_guard_wiring.py"]), 0)
                with open(os.path.join(d, ".claude", "settings.local.json"), "w") as f:
                    json.dump({"disableAllHooks": True}, f)
                self.assertEqual(w.main(["check_guard_wiring.py"]), 1)
            finally:
                os.chdir(here)

    def test_no_sandbox_fails(self):
        s = settings()
        del s["sandbox"]
        self.assertTrue(any("sandbox" in p for p in problems(s)), problems(s))

    def test_a_sandbox_that_is_off_or_fails_open_fails(self):
        # enabled; refuse to start without bubblewrap rather than run unsandboxed;
        # no retry outside the sandbox (its default is to allow one)
        for key, value in (("enabled", False), ("failIfUnavailable", False), ("allowUnsandboxedCommands", True)):
            s = settings()
            s["sandbox"][key] = value
            self.assertTrue(problems(s), key)
            del s["sandbox"][key]
            self.assertTrue(problems(s), "%s missing" % key)

    def test_the_hook_folder_must_be_write_protected(self):
        s = settings()
        s["sandbox"]["filesystem"]["denyWrite"] = []
        self.assertTrue(any("scripts/quality/hooks" in p for p in problems(s)), problems(s))

    def test_the_old_checkouts_secrets_must_be_unreadable(self):
        for path in SANDBOX["filesystem"]["denyRead"]:
            s = settings()
            s["sandbox"]["filesystem"]["denyRead"].remove(path)
            self.assertTrue(any(path in p for p in problems(s)), path)

    def test_nothing_may_widen_the_sandbox(self):
        # each would let sandboxed commands write outside the repository, reach a
        # socket (the Docker socket drives the live node), or run unsandboxed
        widen = [("filesystem", "allowWrite", ["/home/junc/rikuri"]), ("filesystem", "disabled", True),
                 ("network", "allowUnixSockets", ["/var/run/docker.sock"]), ("network", "allowAllUnixSockets", True),
                 ("network", "allowLocalBinding", True), (None, "excludedCommands", ["git push *", "docker *"]),
                 (None, "enableWeakerNestedSandbox", True), (None, "enableWeakerNetworkIsolation", True)]
        for section, key, value in widen:
            s = settings()
            (s["sandbox"][section] if section else s["sandbox"])[key] = value
            self.assertTrue(problems(s), key)
        s = settings(permissions={"additionalDirectories": ["/home/junc/rikuri"]})
        self.assertTrue(problems(s), "additionalDirectories")

    def test_local_settings_may_not_loosen_the_sandbox(self):
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".claude"))
            with open(os.path.join(d, ".claude", "settings.json"), "w") as f:
                json.dump(settings(), f)
            try:
                os.chdir(d)
                for local in ({"sandbox": {"enabled": False}}, {"sandbox": {"filesystem": {"allowWrite": ["/"]}}},
                              {"sandbox": {"excludedCommands": ["*"]}},
                              {"permissions": {"additionalDirectories": ["/home"]}}):
                    with open(os.path.join(d, ".claude", "settings.local.json"), "w") as f:
                        json.dump(local, f)
                    self.assertEqual(w.main(["check_guard_wiring.py"]), 1, local)
            finally:
                os.chdir(here)

    def test_documented_widenings_fail_in_either_file(self):
        # verifier round 9: each passed the check, as the project file and as
        # the local file (Claude Code 2.1.295's settings schema documents them)
        widen = [(("sandbox", "network", "allowedDomains"), ["github.com", "api.github.com", "*.githubusercontent.com",
                                                             "*"]),
                 (("sandbox", "network", "allowedDomains"), ["github.com", "example.com"]),
                 (("sandbox", "network", "httpProxyPort"), 3128), (("sandbox", "network", "socksProxyPort"), 1080),
                 (("sandbox", "filesystem", "allowRead"), ["/home/junc/rikuri/rikurinode/.env"]),
                 (("sandbox", "filesystem", "allowRead"), ["/home/junc/rikuri/rikurinode/data"]),
                 (("permissions", "allow"), ["Edit(//home/junc/rikuri/**)"]),
                 (("permissions", "allow"), ["WebFetch(domain:*)"]), (("sandbox", "ignoreViolations"), {"*": ["/"]})]
        for path, value in widen:
            with self.subTest(path=path, value=value):
                s = settings()
                setin(s, path, value)
                self.assertTrue(problems(s), "project file")
                local = {}
                setin(local, path, value)
                self.assertEqual(main_with(settings(), local), 1, "local file")

    def test_any_other_sandbox_key_fails(self):
        # closed-world: a key the check does not know may widen the sandbox
        for path in (("sandbox", "newKey"), ("sandbox", "filesystem", "newKey"), ("sandbox", "network", "newKey")):
            s = settings()
            setin(s, path, True)
            self.assertTrue(problems(s), path)
        s = settings()
        s["sandbox"]["excludedCommands"] = ["git push *"]
        self.assertTrue(problems(s), "a different list is a different sandbox")
        for value in (1, "true"):  # true, not something Claude Code may read as true
            s = settings()
            s["sandbox"]["enabled"] = value
            self.assertTrue(problems(s), value)
        self.assertTrue(problems(settings(permissions={"newKey": True})), "a permissions key the check does not know")

    def test_a_section_of_the_wrong_type_fails_without_crashing(self):
        # verifier round 9: "network": "x" crashed the check (AttributeError)
        for path, value in ((("sandbox", "network"), "x"), (("sandbox", "filesystem"), []), (("sandbox",), "on"),
                            (("permissions",), "x"), (("permissions", "allow"), "Edit"), (("env",), "x"),
                            (("hooks",), []), (("hooks", "PreToolUse"), {}),
                            # round 14's verifier: a list crashed the check (unhashable)
                            (("permissions", "defaultMode"), ["default"]),
                            (("permissions", "defaultMode"), {"default": True})):
            with self.subTest(path=path):
                s = settings()
                setin(s, path, value)
                self.assertTrue(problems(s))
                local = {}
                setin(local, path, value)
                self.assertEqual(main_with(settings(), local), 1)

    def test_the_local_file_may_not_set_the_sandbox_at_all(self):
        # even to the same values: what it may change is nothing
        self.assertEqual(main_with(settings(), {"sandbox": copy.deepcopy(SANDBOX)}), 1)
        self.assertEqual(main_with(settings(), {"permissions": {"deny": ["Bash(rm -rf *)"]}}), 0)

    def test_permission_rules_that_widen_the_sandbox_fail(self):
        # Edit(…)/Write(…) allow rules are merged into the writable paths,
        # WebFetch(domain:…) into the allowed domains (settings schema)
        for rule in ("Edit", "Edit(//home/junc/**)", "Write(/tmp/**)", "MultiEdit(**)", "NotebookEdit(**)",
                     "WebFetch", "WebFetch(domain:*)", "Read(//home/junc/rikuri/**)"):
            with self.subTest(rule=rule):
                self.assertTrue(problems(settings(permissions={"allow": [rule]})))
                self.assertEqual(main_with(settings(), {"permissions": {"allow": [rule]}}), 1)
        for ok in ({"allow": ["Bash(cargo test:*)"]}, {"deny": ["Edit(//home/junc/rikuri/rikurinode/**)"]},
                   {"ask": ["Bash(git push:*)"]}):
            self.assertEqual(problems(settings(permissions=ok)), [], ok)

    def test_environment_that_names_the_sandbox_or_hooks_fails(self):
        for env in ({"CLAUDE_CODE_DISABLE_SANDBOX": "1"}, {"SANDBOX_RUNTIME": "x"}, {"CLAUDE_CODE_HOOKS": "0"}):
            with self.subTest(env=env):
                self.assertTrue(problems(settings(env=env)))
                self.assertEqual(main_with(settings(), {"env": env}), 1)
        self.assertEqual(problems(settings(env={"RUST_LOG": "debug"})), [])

    def test_another_hook_before_tool_calls_or_permissions_fails(self):
        # a second PreToolUse hook may rewrite the input after the guard read
        # it (updatedInput); a PermissionRequest hook may answer the guard's ask
        extra = {"type": "command", "command": "python3 x.py"}
        s = settings()
        s["hooks"]["PreToolUse"][0]["hooks"].append(extra)
        self.assertTrue(problems(s))
        s = settings()
        s["hooks"]["PreToolUse"].append({"matcher": "Bash", "hooks": [extra]})
        self.assertTrue(problems(s))
        s = settings()
        s["hooks"]["PermissionRequest"] = [{"matcher": "*", "hooks": [extra]}]
        self.assertTrue(problems(s))
        guard_only = {"matcher": "Bash", "hooks": [{"type": "command", "command": CMD}]}
        for local in ({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [extra]}]}},
                      {"hooks": {"PreToolUse": [guard_only]}},  # the local file configures no hook before a call
                      {"hooks": {"PermissionRequest": [{"matcher": "*", "hooks": [extra]}]}}):
            self.assertEqual(main_with(settings(), local), 1, local)
        s = settings()
        s["hooks"]["PostToolUse"] = [{"matcher": "*", "hooks": [extra]}]
        # round 11 (round 10's verifier): hooks are closed-world too — any
        # event other than the guard's PreToolUse is refused, even one after
        # the call (it runs a command outside the sandbox and the guard)
        self.assertTrue(problems(s), "only the guard's PreToolUse hook")
        for event in ("SessionStart", "UserPromptSubmit", "Stop"):
            s = settings()
            s["hooks"][event] = [{"hooks": [extra]}]
            self.assertTrue(problems(s), event)
        self.assertEqual(main_with(settings(), {"hooks": {"Stop": [{"hooks": [extra]}]}}), 1, "the local file: no hooks")

    def test_the_guards_own_hook_entry_is_exactly_the_committed_one(self):
        # round 10's verifier, from Claude Code's settings schema: `if` runs the
        # hook only for matching calls, `once` removes it after one run, an
        # async hook's onFailure is ignored — each would pass a check that
        # read only the hook's type and command
        for key, value in (("if", "Bash(git *)"), ("once", True), ("async", True), ("asyncRewake", True),
                           ("args", ["x"]), ("shell", "sh"), ("statusMessage", "x")):
            with self.subTest(key=key):
                s = settings()
                s["hooks"]["PreToolUse"][0]["hooks"][0][key] = value
                self.assertTrue(problems(s))
        s = settings()
        s["hooks"]["PreToolUse"][0]["newKey"] = True
        self.assertTrue(problems(s), "an entry key the check does not know")
        # 0 and 2.5: round 13's verifier; 11 and 1: round 14's (no test held either bound's edge)
        for timeout in (60, "10", True, 0, 2.5, 11):
            s = settings()
            s["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] = timeout
            self.assertTrue(problems(s), timeout)
        for timeout in (1, 10):
            s = settings()
            s["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] = timeout
            self.assertEqual(problems(s), [], timeout)
        # round 11's verifier: a guard hook without a timeout passed (Claude
        # Code's default then applies, which nothing shows is 10 s or less)
        s = settings()
        del s["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"]
        self.assertTrue(problems(s), "no timeout")

    def test_a_settings_key_the_check_does_not_know_fails(self):
        # settings that run a command, load plugins (which may bring hooks) or
        # MCP servers (their tools are outside the guard's matcher): closed-world
        for key, value in (("apiKeyHelper", "/tmp/x.sh"), ("statusLine", {"type": "command", "command": "x"}),
                           ("fileSuggestion", {"type": "command", "command": "x"}), ("enabledPlugins", {"x@y": True}),
                           ("extraKnownMarketplaces", {"x": {}}), ("enableAllProjectMcpServers", True),
                           ("otelHeadersHelper", "/tmp/x.sh"), ("newKey", 1)):
            with self.subTest(key=key):
                self.assertTrue(problems(settings(**{key: value})))
                self.assertEqual(main_with(settings(), {key: value}), 1)
        self.assertEqual(problems(settings(**{"$schema": "https://json.schemastore.org/claude-code-settings.json"})),
                         [])

    def test_a_permission_mode_outside_the_list_fails(self):
        for mode in ("bypassPermissions", "dontAsk", "auto"):
            with self.subTest(mode=mode):
                self.assertTrue(problems(settings(permissions={"defaultMode": mode})))
        for mode in ("default", "manual", "acceptEdits", "plan"):  # manual: the schema's alias for default
            self.assertEqual(problems(settings(permissions={"defaultMode": mode})), [], mode)

    def test_environment_that_changes_what_a_command_runs_fails(self):
        for name in ("PATH", "LD_PRELOAD", "LD_LIBRARY_PATH", "BASH_ENV", "ENV", "ZDOTDIR", "PYTHONPATH",
                     "PYTHONSTARTUP", "SHELL", "GIT_CONFIG_GLOBAL", "GIT_EXEC_PATH", "NODE_OPTIONS"):
            with self.subTest(name=name):
                self.assertTrue(problems(settings(env={name: "/tmp/x"})))
        self.assertEqual(problems(settings(env={"RUST_LOG": "debug", "CARGO_TERM_COLOR": "always"})), [])

    def test_unreadable_settings_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "settings.json")
            with open(p, "w") as f:
                f.write("{not json")
            self.assertTrue(w.problems(p))
            self.assertTrue(w.problems(os.path.join(d, "missing.json")))

    def test_the_sandboxs_placeholder_is_no_local_settings(self):
        # Bootstrap round 18: inside Claude Code's sandbox an absent
        # settings.local.json is /dev/null, bound on a nodev mount where it
        # cannot be opened, and the gate failed at step 2. /dev/null holds no
        # settings; the check reads it as none, and says so. /dev/null itself
        # stands in for the bind: a test cannot mount one, and a symlink to it
        # is not the placeholder (below).
        with mock.patch.object(w, "LOCAL", os.devnull):
            rc, out, _ = run_with_local(lambda p: None)
            self.assertEqual(rc, 0)
            self.assertIn("no local settings", out)
            # Round 2's verifier: a placeholder that cleared or skipped the
            # project file's findings (K1, K2) passed every test; it sits
            # beside the project file in every sandboxed session.
            self.assertEqual(run_with_local(lambda p: None, project=settings(disableAllHooks=True))[0], 1)

    def test_only_dev_null_itself_is_the_placeholder(self):
        # This change's mutants: any character device (M2), or a missing path
        # (M5), read as the placeholder survived the first tests. Its
        # verifier: a symlink was followed, so a link to /dev/stdin, or inside
        # the sandbox to any path shown as /dev/null, passed unread; a block
        # device numbered like /dev/null (V1). Round 2's verifier: where
        # /dev/null is a regular file, a whiteout (character device 0:0)
        # matched it — the number is Linux's fixed 1:3 now; a path lstat
        # cannot reach (K11) is not the placeholder. By stat alone: nothing
        # is opened.
        self.assertTrue(w.is_dev_null(os.devnull))
        self.assertFalse(w.is_dev_null("/dev/zero"))
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(w.is_dev_null(os.path.join(d, "missing.json")))
            write(os.path.join(d, "file"), "")
            self.assertFalse(w.is_dev_null(os.path.join(d, "file", "below")))
            for name, target in (("null", os.devnull), ("stdin", "/dev/stdin"), ("fd0", "/proc/self/fd/0")):
                link = os.path.join(d, name)
                os.symlink(target, link)
                self.assertFalse(w.is_dev_null(link), target)
        block = types.SimpleNamespace(st_mode=stat.S_IFBLK | 0o660, st_rdev=os.makedev(1, 3))
        with mock.patch.object(w.os, "lstat", return_value=block):
            self.assertFalse(w.is_dev_null("/dev/ram3"))
        whiteout = types.SimpleNamespace(st_mode=stat.S_IFCHR, st_rdev=os.makedev(0, 0))
        regular = types.SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_rdev=os.makedev(0, 0))
        with mock.patch.object(w.os, "lstat", return_value=whiteout), \
                mock.patch.object(w.os, "stat", return_value=regular):
            self.assertFalse(w.is_dev_null("whiteout"))
        self.assertEqual(run_with_local(lambda p: None), (0, "", ""))

    def test_the_placeholder_rule_covers_the_default_local_file_only(self):
        # Its verifier's surviving mutants: explicit paths (V5) and the project
        # file (V7) excused as /dev/null too.
        self.assertEqual(w.main(["check_guard_wiring.py", os.devnull]), 1)
        with mock.patch.object(w, "PROJECT", os.devnull):
            self.assertEqual(run_with_local(lambda p: None)[0], 1)

    def test_any_other_local_file_that_is_not_settings_fails(self):
        # Nothing at the local path is excused but /dev/null itself. Round
        # 18's verifier: a check using os.path.isfile passed every test and
        # would skip a folder or a FIFO, which Claude Code may still read.
        def unreadable(p):
            if os.geteuid() == 0:
                self.skipTest("root reads a mode-000 file")
            write(p, "{}")
            os.chmod(p, 0)

        for name, make in (("empty", lambda p: write(p, "")), ("folder", os.mkdir), ("unreadable", unreadable),
                           ("symlink to /dev/null", lambda p: os.symlink(os.devnull, p))):
            with self.subTest(name=name):
                self.assertEqual(run_with_local(make)[0], 1)

    def test_the_local_file_is_read_only_as_a_regular_file(self):
        # The owner's choice (2026-10-12): a link there is followed by its
        # reader into a view this check may not share — inside the sandbox a
        # link into a folder it hides dangles, outside it reaches a real file
        # — and a FIFO with no writer stopped the check. Anything there but a
        # regular file or the placeholder fails, a link to a harmless file too
        # (the cost the owner accepted); a regular file is read as before.
        # Round 3's verifier: no test put an openable device at the path (X1),
        # and a link was refused by the open alone, with an unclear message
        # (R1).
        def loop(p):
            os.symlink(p, p)

        for name, make in (("dangling link", lambda p: os.symlink(p + ".nowhere", p)), ("link loop", loop),
                           ("link to {}", harmless_link)):
            with self.subTest(name=name):
                rc, _, err = run_with_local(make)
                self.assertEqual(rc, 1)
                self.assertIn("never through a link", err)
        with self.subTest(name="FIFO, no writer"):
            rc, _, err = run_with_local(os.mkfifo, timeout=5)
            self.assertEqual(rc, 1)
            self.assertIn("not a regular file", err)
        with self.subTest(name="a device (/dev/ptmx)"):
            # Inside a sandbox or a container /dev/ptmx is a link to
            # pts/ptmx: the device itself is where the link leads.
            device = os.path.realpath("/dev/ptmx")
            if not (os.path.exists(device) and stat.S_ISCHR(os.lstat(device).st_mode)):
                self.skipTest("no pty device here")
            with mock.patch.object(w, "LOCAL", device):
                rc, _, err = run_with_local(lambda p: None, timeout=5)
            self.assertEqual(rc, 1)
            self.assertIn("not a regular file", err)
        self.assertEqual(run_with_local(lambda p: write(p, "{}")), (0, "", ""))

    def test_a_swap_after_the_first_look_fails_closed(self):
        # The path may change between the check's first look and its read:
        # the read neither follows a link nor waits on a FIFO, and the open
        # file is checked again. Stand-ins for a swap: the first look misses
        # the link; the open file turns out to be a FIFO.
        with_link_unseen = lambda: mock.patch.object(w.os.path, "islink", return_value=False)  # noqa: E731
        self.assertEqual(run_with_local(harmless_link, during=with_link_unseen)[0], 1)
        fifo = types.SimpleNamespace(st_mode=stat.S_IFIFO | 0o644)
        opened_as_fifo = lambda: mock.patch.object(w.os, "fstat", return_value=fifo)  # noqa: E731
        self.assertEqual(run_with_local(lambda p: write(p, "{}"), during=opened_as_fifo)[0], 1)


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


def harmless_link(p):
    write(p + ".target", "{}")
    os.symlink(p + ".target", p)


def run_with_local(make, project=None, during=None, timeout=None):
    """The gate's default run, with the local settings path made by `make`,
    beside `project` (the standard settings by default), inside the context
    `during()` makes, failing if it takes more than `timeout` seconds:
    (exit status, what it printed, what it reported)."""
    def too_slow(*_):
        raise AssertionError("the check did not finish in %d s" % timeout)

    here = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".claude"))
        with open(os.path.join(d, ".claude", "settings.json"), "w") as f:
            json.dump(settings() if project is None else project, f)
        local = os.path.join(d, ".claude", "settings.local.json")
        before = signal.signal(signal.SIGALRM, too_slow)
        try:
            make(local)
            os.chdir(d)
            with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                with during() if during else contextlib.nullcontext():
                    signal.alarm(timeout or 0)
                    rc = w.main(["check_guard_wiring.py"])
            return rc, out.getvalue(), err.getvalue()
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, before)
            os.chdir(here)
            if os.path.isfile(local) and not os.path.islink(local):
                os.chmod(local, 0o600)


if __name__ == "__main__":
    unittest.main()
