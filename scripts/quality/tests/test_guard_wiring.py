"""Tests for scripts/quality/check_guard_wiring.py: the guard really runs.

Round 2's verifier: the gate's wiring step stayed green with
"disableAllHooks": true, or with a command that merely mentioned guard.py.
The check reads the settings as Claude Code does: hooks enabled, the exact
guard command, before (PreToolUse) every file and shell tool; and (owner,
2026-10-11) the OS sandbox around every shell command, failing closed, with
nothing in the settings that widens it.
Record: docs/build-records/2026-10-10-bootstrap.md
"""
import copy
import json
import os
import sys
import tempfile
import unittest

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
           "network": {"allowedDomains": ["github.com", "api.github.com"]}}


def settings(**kw):
    s = {"hooks": {"PreToolUse": [{"matcher": TOOLS, "hooks": [{"type": "command", "command": CMD, "timeout": 10,
                                                                 "onFailure": "block"}]}]},
         "sandbox": copy.deepcopy(SANDBOX)}
    s.update(kw)
    return s


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
            {"matcher": "Bash|Read|Grep", "hooks": [{"type": "command", "command": CMD, "onFailure": "block"}]},
            {"matcher": "Edit|Write|MultiEdit|NotebookEdit",
             "hooks": [{"type": "command", "command": CMD, "onFailure": "block"}]}]
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
            self.assertTrue(problems(s), value)

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

    def test_unreadable_settings_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "settings.json")
            with open(p, "w") as f:
                f.write("{not json")
            self.assertTrue(w.problems(p))
            self.assertTrue(w.problems(os.path.join(d, "missing.json")))


if __name__ == "__main__":
    unittest.main()
