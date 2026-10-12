"""Tests for scripts/quality/check_guard_wiring.py: the guard really runs.

Round 2's verifier: the gate's wiring step stayed green with
"disableAllHooks": true, or with a command that merely mentioned guard.py.
The check reads the settings as Claude Code does: hooks enabled, the exact
guard command, before (PreToolUse) every file and shell tool; and (owner,
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


if __name__ == "__main__":
    unittest.main()
