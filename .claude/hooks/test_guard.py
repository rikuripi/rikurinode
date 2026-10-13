"""Tests for guard.py — IDENTICAL in every full-tier repo, like guard.py.

Replays every example in this repo's guard-config.json, then the generic
cases every repo's policy must satisfy, then the failure modes (a broken
guard must ASK, never fail open).

Run: python3 -m unittest discover -s .claude/hooks -p 'test_*.py'
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guard  # noqa: E402

CFG = guard.load_config()


def verdict(tool: str, tool_input: dict, lock: bool = False, branch: str = "feature/x",
            cwd: str = "", profile: str = "stable", cfg: dict | None = None) -> str:
    """The guard's decision under a given profile. Tests name the profile they
    describe; the repo's own setting is whatever its owner chose today."""
    event = {"tool_name": tool, "tool_input": tool_input,
             "cwd": os.path.join(guard.ROOT, cwd)}
    return guard.decide(event, dict(cfg or CFG, profile=profile), guard.ROOT, lock_present=lock,
                        branch_fn=lambda _cwd: branch)[0]


class ConfigExamples(unittest.TestCase):
    def test_every_example(self):
        self.assertGreater(len(CFG["examples"]), 10, "policy without worked examples is untested")
        for ex in CFG["examples"]:
            args = (ex["tool"], ex["input"], ex.get("lock", False), ex.get("branch", "feature/x"),
                    ex.get("cwd", ""))
            with self.subTest(ex=ex, profile="stable"):
                self.assertEqual(verdict(*args, profile="stable"), ex["expect"])
            # Development relaxes every ask EXCEPT money moves and secrets, so
            # an example that must keep asking says so explicitly (expect_dev).
            want_dev = ex.get("expect_dev", "allow" if ex["expect"] == "ask" else ex["expect"])
            with self.subTest(ex=ex, profile="development"):
                self.assertEqual(verdict(*args, profile="development"), want_dev)


class GenericPolicy(unittest.TestCase):
    """Cases every full-tier repo's guard-config.json must satisfy."""

    def test_secrets(self):
        self.assertEqual(verdict("Read", {"file_path": ".env"}), "deny")
        self.assertEqual(verdict("Read", {"file_path": "sub/dir/.env.local"}), "deny")
        self.assertEqual(verdict("Read", {"file_path": ".env.example"}), "allow")
        self.assertEqual(verdict("Read", {"file_path": "~/.ssh/id_ed25519"}), "deny")
        self.assertEqual(verdict("Read", {"file_path": "~/.ssh/id_ed25519.pub"}), "allow")
        self.assertEqual(verdict("Bash", {"command": "cat .env"}), "deny")
        self.assertEqual(verdict("Bash", {"command": "head -3 < .env"}), "deny")
        self.assertEqual(verdict("Bash", {"command": "grep -rn '.env' src"}), "allow")

    def test_git(self):
        self.assertEqual(verdict("Bash", {"command": "git log --oneline -5"}), "allow")
        self.assertEqual(verdict("Bash", {"command": "git push -u origin feature/x"}), "allow")
        self.assertEqual(verdict("Bash", {"command": "git push origin main"}), "ask")
        self.assertEqual(verdict("Bash", {"command": "git push"}, branch="main"), "ask")
        self.assertEqual(verdict("Bash", {"command": "git -C /tmp push --force"}), "deny")
        self.assertEqual(verdict("Bash", {"command": "git push --all"}), "ask")
        self.assertEqual(verdict("Bash", {"command": "git fetch && git push -fu origin x"}), "deny")

    def test_guard_protects_itself(self):
        # The permission settings are protected in every repo.
        self.assertEqual(verdict("Edit", {"file_path": ".claude/settings.json"}), "ask")
        self.assertEqual(verdict("Bash", {"command": "echo '{}' > .claude/settings.json"}), "ask")
        self.assertEqual(verdict("Read", {"file_path": ".claude/hooks/guard.py"}), "allow")
        # The guard's own files follow this repo's policy: protected unless the
        # owner chose otherwise (rikurinode, 2026-09-26).
        for p in (".claude/hooks/guard.py", ".claude/hooks/guard-config.json"):
            want = "ask" if guard.matches(p, CFG["protected_globs"]) else "allow"
            self.assertEqual(verdict("Edit", {"file_path": p}), want, p)

    def test_fix_lock(self):
        t = {"file_path": "tests/test_something.py"}
        self.assertEqual(verdict("Edit", t, lock=False), "allow")
        self.assertEqual(verdict("Edit", t, lock=True), "deny")
        self.assertEqual(verdict("Bash", {"command": "echo x >> tests/test_something.py"}, lock=True), "deny")
        self.assertEqual(verdict("Bash", {"command": "git checkout -- tests/test_something.py"}, lock=True), "deny")
        self.assertEqual(verdict("Bash", {"command": "cat tests/test_something.py"}, lock=True), "allow")
        # engaging is free; releasing is the owner's call unless this repo's
        # owner chose otherwise (fix_lock_release_needs_owner: false)
        self.assertEqual(verdict("Bash", {"command": "python3 .claude/hooks/guard.py fix-lock on docs/build-records/x.md"}), "allow")
        release = "ask" if CFG.get("fix_lock_release_needs_owner", True) else "allow"
        self.assertEqual(verdict("Bash", {"command": "python3 .claude/hooks/guard.py fix-lock off"}), release)
        self.assertEqual(verdict("Bash", {"command": "rm -f .claude/state/fix-lock"}), "ask")
        self.assertEqual(verdict("Write", {"file_path": ".claude/state/fix-lock"}), "allow")
        self.assertEqual(verdict("Edit", {"file_path": ".claude/state/fix-lock"}), "ask")

    def test_tracked_inline_tests_have_a_rule(self):
        # Class tripwire (2026-10-11): Rikuri-PI gained Rust on 2026-10-05 with
        # no `inline_tests` rule, so a fix-lock left its #[cfg(test)] tests
        # editable while `fix-lock on` called them read-only. Each repository
        # opts in through its own config; this checks it again on every run,
        # from the files git tracks here (InlineTestCoverage has the cases).
        gaps = guard.uncovered_inline_tests(guard.ROOT, CFG)
        self.assertEqual(gaps, [], "tracked .rs files keep Rust tests (a #[cfg(test)] or #![cfg(test)] line, or a "
                         "test module declared under cfg(test)) that the fix-lock does not cover: no inline_tests "
                         "rule in guard-config.json covers them, or the guard cannot follow the test module's "
                         "declaration (rikurinode's and AISecurity's rules are the model): " + ", ".join(gaps))

    def test_inline_rules_find_a_tests_only_file(self):
        # Owner, 2026-10-11 (2(a)): a file can hold nothing but tests, switched
        # on by the inner attribute `#![cfg(test)]` at its top. Every rule this
        # repository has for .rs files must find them, with the attributes and
        # doc comments above (an added `#![cfg(any())]` switches the file off).
        text = InlineTests.INNER
        for r in CFG.get("inline_tests", []):
            if r["glob"].endswith(".rs"):
                self.assertEqual(guard.inline_region(text, r["starts_at"], r.get("attached_above", "")), text, r)

    def test_inline_rules_take_linear_time(self):
        # Verifier round 2, F1: `#\s*!?\s*\[` (and guarded_lines' `\s*!?\s*\(`)
        # took time growing with the square of a run of spaces — 1.3 s for
        # 40,000 inside one regex call, where no deadline can stop it — so a
        # crafted file or edit held the hook past its 10 s limit. Every pattern
        # of this repository's rules must stay fast on such text.
        import re
        import time
        texts = ("#" + " " * 40000, "# !" + " " * 40000, "cfg" + " " * 40000, "cfg_attr !" + " " * 40000,
                 "#[cfg(any(" + ", " * 20000, "//" + " " * 40000)
        for r in CFG.get("inline_tests", []):
            for key in ("starts_at", "attached_above", "guarded_lines"):
                for text in texts:
                    t0 = time.time()
                    re.search(r.get(key, ""), text, re.M)
                    self.assertLess(time.time() - t0, 0.25, (key, text[:12]))

    def test_the_guard_blocks_when_it_fails(self):
        # Owner, 2026-10-12 (verifier rounds 2 and 3): Claude Code lets a tool
        # call through when its hook fails or runs out of time, unless the
        # hook says "onFailure": "block" (Claude Code 2.1.295 or later). A
        # stalled guard must close the gate, not open it.
        with open(os.path.join(guard.ROOT, ".claude", "settings.json")) as f:
            settings = json.load(f)
        hooks = [h for group in settings.get("hooks", {}).get("PreToolUse", []) for h in group.get("hooks", [])
                 if "guard.py" in h.get("command", "")]
        self.assertTrue(hooks, "the guard is not wired as a PreToolUse hook in .claude/settings.json")
        for h in hooks:
            self.assertEqual(h.get("onFailure"), "block", h)

    def test_strictest_wins(self):
        self.assertEqual(verdict("Bash", {"command": "git push origin main; cat .env"}), "deny")

    def test_unknown_tools_pass(self):
        self.assertEqual(verdict("WebSearch", {"query": ".env"}), "allow")
        self.assertEqual(verdict("Bash", {"command": ""}), "allow")


class Profiles(unittest.TestCase):
    """Owner, 2026-09-27: one switch between 'stable' (every gate asks) and
    'development' (only money moves and secrets ask; denies never change)."""

    SYN = dict(CFG, funds_patterns=[
        {"regex": r"\bmovemoney\b", "reason": "moves money", "always_ask": True},
        {"regex": r"\brestartthing\b", "reason": "restarts a thing"},
    ])

    def v(self, tool, tin, profile, **kw):
        return verdict(tool, tin, profile=profile, cfg=self.SYN, **kw)

    def test_absent_profile_is_stable(self):
        cfg = dict(self.SYN)
        cfg.pop("profile", None)
        event = {"tool_name": "Bash", "tool_input": {"command": "restartthing"}, "cwd": guard.ROOT}
        self.assertEqual(guard.decide(event, cfg, guard.ROOT, lock_present=False)[0], "ask")

    def test_development_keeps_only_money_and_secret_asks(self):
        for profile, other in (("stable", "ask"), ("development", "allow")):
            self.assertEqual(self.v("Bash", {"command": "movemoney now"}, profile), "ask", profile)
            self.assertEqual(self.v("Bash", {"command": "restartthing now"}, profile), other, profile)
            self.assertEqual(self.v("Edit", {"file_path": ".claude/settings.json"}, profile), other, profile)
            self.assertEqual(self.v("Bash", {"command": "git push origin main"}, profile), other, profile)
            self.assertEqual(self.v("Bash", {"command": "rm -f .env"}, profile), "ask", profile)
            self.assertEqual(self.v("Write", {"file_path": ".env"}, profile), "ask", profile)

    def test_development_never_changes_a_deny(self):
        d = "development"
        self.assertEqual(self.v("Read", {"file_path": ".env"}, d), "deny")
        self.assertEqual(self.v("Bash", {"command": "cat .env"}, d), "deny")
        self.assertEqual(self.v("Bash", {"command": "git push --force origin x"}, d), "deny")
        self.assertEqual(self.v("Edit", {"file_path": "tests/test_x.py"}, d, lock=True), "deny")
        self.assertEqual(self.v("Bash", {"command": "restartthing; cat .env"}, d), "deny")

    def test_loosening_asks_tightening_is_free(self):
        loosen = {"command": "python3 .claude/hooks/guard.py profile development"}
        tighten = {"command": "python3 .claude/hooks/guard.py profile stable"}
        self.assertEqual(self.v("Bash", loosen, "stable"), "ask")
        self.assertEqual(self.v("Bash", loosen, "development"), "allow")
        self.assertEqual(self.v("Bash", tighten, "stable"), "allow")
        self.assertEqual(self.v("Bash", tighten, "development"), "allow")

    def _cfg_file(self, root: str, profile: str | None) -> str:
        cfg = json.loads(json.dumps(self.SYN))
        cfg.pop("fix_lock_preflight", None)
        cfg.pop("profile", None)
        path = os.path.join(root, "guard-config.json")
        with open(path, "w") as f:
            text = json.dumps(cfg, indent=2)
            if profile is not None:
                text = text.replace("{\n", '{\n  "profile": "%s",\n' % profile, 1)
            f.write(text + "\n")
        return path

    def test_every_relaxed_ask_is_logged(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._cfg_file(root, "development")
            event = {"tool_name": "Bash", "tool_input": {"command": "restartthing now"}, "cwd": root}
            self.assertIsNone(guard.run_hook(json.dumps(event), path, root))
            with open(os.path.join(root, guard.RELAXED_LOG_REL)) as f:
                rows = [json.loads(line) for line in f]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["what"], "restartthing now")
            self.assertIn("restarts a thing", rows[0]["why"][0])
            self.assertTrue(rows[0]["at"])

    def test_profile_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._cfg_file(root, None)
            with open(path) as f:
                before = json.load(f)
            self.assertEqual(guard.profile_cli([], root, path), 0)
            self.assertEqual(guard.profile_cli(["development"], root, path), 0)
            after = guard.load_config(path)
            self.assertEqual(after["profile"], "development")
            self.assertEqual({k: v for k, v in after.items() if k != "profile"}, before)
            self.assertEqual(guard.profile_cli(["stable"], root, path), 0)
            self.assertEqual(guard.load_config(path)["profile"], "stable")
            self.assertEqual(guard.profile_cli(["loose"], root, path), 2)
            with open(os.path.join(root, guard.PROFILE_LOG_REL)) as f:
                rows = [json.loads(line) for line in f]
            self.assertEqual([(r["from"], r["to"]) for r in rows],
                             [("stable", "development"), ("development", "stable")])

    def test_config_validation(self):
        with tempfile.TemporaryDirectory() as root:
            for bad in ({"profile": "loose"},
                        {"funds_patterns": [{"regex": "x", "reason": "r", "always_ask": "yes"}]}):
                path = self._cfg_file(root, None)
                with open(path) as f:
                    cfg = json.load(f)
                cfg.update(bad)
                with open(path, "w") as f:
                    json.dump(cfg, f)
                with self.assertRaises(ValueError, msg=str(bad)):
                    guard.load_config(path)


class InlineTests(unittest.TestCase):
    """Lesson gate (2026-09-28): Rust keeps most unit tests inside the source
    file (`#[cfg(test)] mod tests`). The fix-lock covered test FILES only, so
    the test proving a fix stayed editable during the fix. A repo names its
    inline-test markers in `inline_tests`: from a file's first marker to its
    end is test code, read-only under the lock like any test file."""

    SRC = ("pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n\n"
           "#[cfg(test)]\nmod tests {\n    use super::*;\n\n"
           "    #[test]\n    fn adds() {\n        assert_eq!(add(2, 2), 4);\n    }\n}\n")
    PLAIN = "pub fn sub(a: i32, b: i32) -> i32 {\n    a - b\n}\n"
    QUOTED = ('pub fn f() {}\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n'
              '        assert!(true, "holds");\n    }\n}\n')
    # A test-only helper module (cfg(any(test, feature))) above the tests is test
    # code too; cfg(not(test)) marks production code and is not a marker.
    SUPPORT = ('#[cfg(not(test))]\npub fn real() -> u8 {\n    1\n}\n\n'
               '#[cfg(any(test, feature = "test-helpers"))]\npub mod test_support {\n'
               '    pub fn fake() -> u8 {\n        2\n    }\n}\n\n#[cfg(test)]\nmod tests {}\n')
    # A comment directly above the marker (as in two real files).
    DOC = ("pub fn f() {}\n\n/// note ZQX\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n"
           "        assert!(true);\n    }\n}\n")
    # A lone CR planted above the code, and the same two lines inside the tests.
    CR = 'pub fn f() {} // L1\rL2\n\n#[cfg(test)]\nmod tests {\n    const S: &str = "L1\nL2";\n}\n'
    BANNER = "pub fn f() {}\n\n// ====\n// Tests\n// ====\n#[cfg(test)]\nmod tests {}\n"
    CRLF = "pub fn f() {} // Z\r\n#[cfg(test)]\r\nmod tests {\r\n    fn t() { assert!(true); }\r\n}\r\n"
    # A tests-only file switched on by an inner attribute (2026-10-11).
    INNER = ("//! Tests only.\n#![allow(unused)]\n#![cfg(test)]\n\nuse super::*;\n\n"
             "#[test]\nfn adds() {\n    assert_eq!(add(2, 2), 4);\n}\n")
    # The rule Rikuri-PI configures (test_marker_shapes pins it): rikurinode's and AISecurity's,
    # which since 2026-10-11 (owner, 2(a)) takes the inner attribute `#![cfg(test)]` too, written
    # `#\s*(?:!\s*)?\[`: `#\s*!?\s*\[` took time growing with the square of a run of
    # spaces (verifier round 2, F1), as did guarded_lines' `\s*!?\s*\(`.
    RUST = dict(CFG, inline_tests=[{"glob": "*.rs", "starts_at":
                                    r"^[ \t\f\v\r​-‏⁠﻿]*#\s*(?:!\s*)?\[\s*cfg\s*\(\s*(?:test|(?:any|all)\s*\((?:.*[(,]\s*)?(?<!not\()test(?=\s*[,)]).*\))\s*\)\s*\]",
                                    "guarded_lines": r"cfg(?:_attr)?\s*(?:!\s*)?\(.*\btest\b|macro_rules!\s*(?:assert\w*|debug_assert\w*|panic|unreachable|todo)\b",
                                    "attached_above": r"^[ \t\f\v\r​-‏⁠﻿]*(#\s*(?:!\s*)?\[|//|/\*|\*)"}])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        os.makedirs(os.path.join(self.root, "src", "dir.rs"))
        for name, text in (("lib.rs", self.SRC), ("plain.rs", self.PLAIN), ("notes.md", self.SRC),
                           ("quoted.rs", self.QUOTED), ("support.rs", self.SUPPORT), ("doc.rs", self.DOC),
                           ("cr.rs", self.CR), ("blank.rs", "\n  \n"), ("bom.rs", "\ufeff\n"),
                           ("crlf.rs", self.CRLF), ("banner.rs", self.BANNER), ("inner.rs", self.INNER),
                           ("lfa.rs", "pub fn f() {} // Z\n#[cfg(test)]\nmod tests {}\n"),
                           ("join.rs", "pub fn f() {}\n// cfg!( Z\ntest) marker\n"),
                           ("allow.rs", "pub fn f() {} // Z\n#[allow(unused)]\n#[cfg(test)]\nmod tests {}\n")):
            with open(os.path.join(self.root, "src", name), "w", newline="") as f:
                f.write(text)
        with open(os.path.join(self.root, "src", "bytes.rs"), "wb") as f:
            f.write(b"pub fn f() {}\n// \xff\n#[cfg(test)]\nmod tests {}\n")

    def tearDown(self):
        self._tmp.cleanup()

    def v(self, tool, tin, lock=True, profile="stable", cfg=None):
        event = {"tool_name": tool, "tool_input": tin, "cwd": self.root}
        return guard.decide(event, dict(cfg or self.RUST, profile=profile), self.root,
                            lock_present=lock, branch_fn=lambda _cwd: "feature/x")[0]

    @staticmethod
    def edit(old, new, path="src/lib.rs", **kw):
        return dict({"file_path": path, "old_string": old, "new_string": new}, **kw)

    def test_edit_inside_the_tests(self):
        change = self.edit("assert_eq!(add(2, 2), 4);", "assert_eq!(add(2, 2), 5);")
        self.assertEqual(self.v("Edit", change), "deny")
        self.assertEqual(self.v("Edit", change, lock=False), "allow")
        self.assertEqual(self.v("Edit", dict(change, file_path=os.path.join(self.root, "src/lib.rs"))), "deny")

    def test_edit_above_the_tests_is_the_fix(self):
        self.assertEqual(self.v("Edit", self.edit("    a + b\n", "    b + a\n")), "allow")
        # New code inserted just above the tests leaves them byte-identical.
        above = self.edit("}\n\n#[cfg(test)]", "}\n\npub fn two() -> i32 {\n    2\n}\n\n#[cfg(test)]")
        self.assertEqual(self.v("Edit", above), "allow")

    def test_edit_reaching_into_the_tests(self):
        self.assertEqual(self.v("Edit", self.edit("#[cfg(test)]\nmod tests {\n    use super::*;",
                                                  "#[cfg(test)]\nmod tests {\n    use super::add;")), "deny")
        self.assertEqual(self.v("Edit", self.edit("add(", "sum(", replace_all=True)), "deny")
        # Removing the marker, or adding a second test module above it, changes the tests too.
        self.assertEqual(self.v("Edit", self.edit("#[cfg(test)]\n", "")), "deny")
        self.assertEqual(self.v("Edit", self.edit("}\n\n#[cfg(test)]",
                                                  "}\n\n#[cfg(test)]\nmod more {}\n\n#[cfg(test)]")), "deny")

    def test_multiedit_applies_every_edit(self):
        fix = {"old_string": "    a + b\n", "new_string": "    b + a\n"}
        cheat = {"old_string": "(add(2, 2), 4)", "new_string": "(add(2, 2), 5)"}
        self.assertEqual(self.v("MultiEdit", {"file_path": "src/lib.rs", "edits": [fix]}), "allow")
        self.assertEqual(self.v("MultiEdit", {"file_path": "src/lib.rs", "edits": [fix, cheat]}), "deny")

    def test_write(self):
        fixed = self.SRC.replace("    a + b\n", "    b + a\n")
        self.assertEqual(self.v("Write", {"file_path": "src/lib.rs", "content": fixed}), "allow")
        self.assertEqual(self.v("Write", {"file_path": "src/lib.rs", "content": fixed.replace(", 4)", ", 5)")}),
                         "deny")
        self.assertEqual(self.v("Write", {"file_path": "src/lib.rs", "content": fixed.split("#[cfg")[0]}),
                         "deny")
        # A new file: production code is free, a new test module is a new test.
        self.assertEqual(self.v("Write", {"file_path": "src/new.rs", "content": self.PLAIN}), "allow")
        self.assertEqual(self.v("Write", {"file_path": "src/new.rs", "content": self.SRC}), "deny")
        # Edit with an empty old_string creates a file, the same as Write.
        self.assertEqual(self.v("Edit", self.edit("", self.PLAIN, path="src/new.rs")), "allow")
        self.assertEqual(self.v("Edit", self.edit("", self.SRC, path="src/new.rs")), "deny")

    def test_adding_tests_to_a_file_without_any(self):
        self.assertEqual(self.v("Edit", self.edit("    a - b\n}\n", "    a - b\n}\n\n#[cfg(test)]\nmod tests {}\n",
                                                  path="src/plain.rs")), "deny")
        self.assertEqual(self.v("Edit", self.edit("    a - b\n", "    b - a\n", path="src/plain.rs")), "allow")

    def test_only_the_configured_files(self):
        # Same text in a file the glob does not name: not Rust, not inline tests.
        self.assertEqual(self.v("Edit", self.edit(", 4)", ", 5)", path="src/notes.md")), "allow")
        # A repo that does not opt in keeps today's behaviour.
        plain = {k: v for k, v in self.RUST.items() if k != "inline_tests"}
        self.assertEqual(self.v("Edit", self.edit(", 4)", ", 5)"), cfg=plain), "allow")

    def test_an_edit_must_match_exactly(self):
        # Verifier, 2026-09-28: the Edit tool also matches loosely (curly quotes
        # straightened, \\uXXXX escapes decoded), so an old_string the guard
        # finds nowhere can still land inside the tests. Under the lock, a
        # covered file takes exact edits only.
        for path, old in (("src/quoted.rs", "assert!(true, \u201cholds\u201d);"),
                          ("src/lib.rs", "assert_eq!(add(2, 2), 4)\\u003b"),
                          ("src/plain.rs", "    a \u2212 b\n")):
            change = self.edit(old, "let _ = 0;", path=path)
            self.assertEqual(self.v("Edit", change), "deny", old)
            self.assertEqual(self.v("Edit", change, lock=False), "allow", old)
        fix = {"old_string": "    a + b\n", "new_string": "    b + a\n"}
        loose = {"old_string": "(add(2, 2), 4)\\u003b", "new_string": "(add(2, 2), 5);"}
        self.assertEqual(self.v("MultiEdit", {"file_path": "src/lib.rs", "edits": [fix, loose]}), "deny")

    def test_marker_shapes(self):
        rx = self.RUST["inline_tests"][0]["starts_at"]
        for line, marker in (("#[cfg(test)]", True), ('#[cfg(any(test, feature = "test-helpers"))]', True),
                             ("    #[cfg(all(test, unix))]", True), ("#[cfg(all(unix, test))]", True),
                             ("#[cfg(not(test))]", False), ('#[cfg(feature = "x")]', False),
                             ("#![cfg(test)]", True), ("# ! [ cfg(test) ]", True), ("#![cfg(all(test, unix))]", True),
                             ("#![cfg(not(test))]", False), ("#!cfg(test)", False), ("#!![cfg(test)]", False),
                             ('#[cfg(any(feature = "test-helpers", unix))]', False),
                             ("#[cfg(any(not(test), unix))]", False), ("#[cfg_attr(test, derive(Debug))]", False),
                             ("# [cfg(test)]", True), ("#[cfg (test)]", True), ("#[ cfg(test) ]", True),
                             ("\u200e#[cfg(test)]", True), ("#[cfg(not (test))]", False)):
            self.assertEqual(guard.inline_region("fn a() {}\n" + line + "\n", rx) is not None, marker, line)

    @classmethod
    def before_inner(cls) -> dict:
        """The rule as it stood before 2026-10-11: `#[` only, never `#![`."""
        return dict(cls.RUST, inline_tests=[{k: v.replace(r"#\s*(?:!\s*)?\[", r"#\s*\[") for k, v in r.items()}
                                            for r in cls.RUST["inline_tests"]])

    def test_a_file_that_starts_cfg_test_is_tests(self):
        # Verifier, 2026-10-11 (owner's choice 2(a)): `#![cfg(test)]` makes the
        # whole file test code. The rule knew only `#[`, so an edit inside the
        # file passed under the lock, and so did an inner attribute added
        # above it, which switches the whole file off.
        change = self.edit("(add(2, 2), 4)", "(add(2, 2), 5)", path="src/inner.rs")
        self.assertEqual(self.v("Edit", change), "deny")
        self.assertEqual(self.v("Edit", change, lock=False), "allow")
        self.assertEqual(self.v("Edit", change, cfg=self.before_inner()), "allow")
        for above in ("#![cfg(any())]\n", "# ! [cfg(any())]\n", "#![cfg_attr(all(), cfg(any()))]\n"):
            off = self.edit("#![cfg(test)]\n", above + "#![cfg(test)]\n", path="src/inner.rs")
            self.assertEqual(self.v("Edit", off), "deny", above)
            self.assertEqual(self.v("Edit", off, lock=False), "allow", above)
        self.assertEqual(self.v("Edit", self.edit("#![allow(unused)]\n", "", path="src/inner.rs")), "deny")
        self.assertEqual(self.v("Write", {"file_path": "src/inner.rs", "content": self.INNER.replace(", 4)", ", 5)")}),
                         "deny")
        self.assertEqual(self.v("Bash", {"command": "sed -i 's/4/5/' src/inner.rs"}), "deny")

    def test_the_edit_tool_is_modelled_exactly(self):
        # Verifier round two, 2026-09-28. (A) Deleting text (new_string "")
        # also removes the newline after it, which can pull the marker onto
        # the line above and hide every test below it from the lock.
        self.assertEqual(self.v("Edit", self.edit(" ZQX", "", path="src/doc.rs")), "deny")
        self.assertEqual(self.v("Edit", self.edit("pub fn f() {}", "", path="src/doc.rs")), "allow")
        # (B) The tool splits lines on \\n only; a lone \\r is not a line break.
        self.assertEqual(self.v("Edit", self.edit("L1\nL2", "X", path="src/cr.rs")), "deny")
        # (C) An empty old_string replaces a whitespace-only file entirely.
        self.assertEqual(self.v("Edit", self.edit("", self.SRC, path="src/blank.rs")), "deny")
        self.assertEqual(self.v("Edit", self.edit("", self.PLAIN, path="src/blank.rs")), "allow")
        # (D) Text that is not UTF-8 cannot be checked (rustc rejects it anyway).
        self.assertEqual(self.v("Edit", self.edit("pub fn f() {}", "pub fn g() {}", path="src/bytes.rs")), "deny")
        for path in ("src/doc.rs", "src/cr.rs", "src/blank.rs", "src/bytes.rs"):
            self.assertEqual(self.v("Edit", self.edit("", "x", path=path), lock=False), "allow")

    def test_lines_attached_above_the_marker(self):
        # Verifier round three: `#[cfg(any())]` added above the marker switches
        # the whole module off, even across blank lines. Attributes and
        # comments directly above it belong to it.
        self.assertEqual(self.v("Edit", self.edit("}\n\n#[cfg(test)]", "}\n\n#[cfg(any())]\n#[cfg(test)]")), "deny")
        self.assertEqual(self.v("Edit", self.edit("}\n\n#[cfg(test)]", "}\n#[cfg(any())]\n\n#[cfg(test)]")), "deny")
        self.assertEqual(self.v("Edit", self.edit(" ZQX", " ZQY", path="src/doc.rs")), "deny")
        # Every line of a stacked banner, other attribute spellings, block comments.
        self.assertEqual(self.v("Edit", self.edit("\n\n// ====\n", "\n\n// ==\n", path="src/banner.rs")), "deny")
        for above in ("# [cfg(any())]", "#\t[cfg(any())]", "/* note */", "/** doc */", "\u200e#[cfg(any())]"):
            self.assertEqual(self.v("Edit", self.edit("}\n\n#[cfg(test)]", "}\n\n%s\n#[cfg(test)]" % above)),
                             "deny", above)
        # Code above them, and the blank lines between, are not the tests.
        self.assertEqual(self.v("Edit", self.edit("pub fn f() {}\n", "pub fn f() {}\n\n\n", path="src/doc.rs")), "allow")
        self.assertEqual(self.v("Edit", self.edit("}\n\n#[cfg(test)]",
                                                  "}\n\n#[inline]\npub fn two() -> i32 {\n    2\n}\n\n#[cfg(test)]")), "allow")
        self.assertEqual(self.v("Edit", self.edit("}\n\n#[cfg(test)]", "}\n\n#[cfg(any())]\n#[cfg(test)]"),
                                lock=False), "allow")

    def test_an_empty_old_string_is_judged_both_ways(self):
        # Verifier round three: the tool calls a file blank by JS trim() (U+FEFF
        # included), Python's strip() doesn't. Rather than model that, both
        # outcomes, "replaced" and "unchanged", must leave the tests alone.
        self.assertEqual(self.v("Edit", self.edit("", self.SRC, path="src/bom.rs")), "deny")
        self.assertEqual(self.v("Edit", self.edit("", self.PLAIN, path="src/bom.rs")), "allow")

    def test_crlf_is_folded_as_the_tool_does(self):
        # An LF old_string matches a CRLF file, and a deletion there still
        # takes the line break with it (route A on a CRLF file).
        self.assertEqual(self.v("Edit", self.edit("pub fn f() {} // Z\n", "pub fn g() {} // Z\n", path="src/crlf.rs")),
                         "allow")
        self.assertEqual(self.v("Edit", self.edit(" // Z", "", path="src/crlf.rs")), "deny")
        # The same deletion on an LF file (route A where the line above is code).
        self.assertEqual(self.v("Edit", self.edit(" // Z", "", path="src/lfa.rs")), "deny")
        # ...and where the joined line is an attached attribute, not a guarded
        # line, so only the region check sees the second outcome.
        self.assertEqual(self.v("Edit", self.edit(" // Z", "", path="src/allow.rs")), "deny")

    def test_production_code_may_not_start_behaving_differently_under_test(self):
        # Verifier round five (class G): production code that acts differently
        # only in the test build turns a failing inline test green without
        # touching it (a tests/* integration test is built without cfg(test)
        # and would still fail). Under the lock such lines may not change.
        for old, new in (("    a + b\n", "    if cfg!(test) { return 4; }\n    a + b\n"),
                         ("pub fn add", "#[cfg(not(test))]\npub fn add"),
                         ("pub fn add", "#[cfg(not(not(test)))]\npub fn add"),
                         ("pub fn add", "#[cfg_attr(test, allow(unused))]\npub fn add"),
                         ("pub fn add", "macro_rules! assert_eq { ($($t:tt)*) => {} }\npub fn add")):
            self.assertEqual(self.v("Edit", self.edit(old, new)), "deny", new)
            self.assertEqual(self.v("Edit", self.edit(old, new), lock=False), "allow", new)
        # In a file with no tests at all, and a second copy of an existing line.
        self.assertEqual(self.v("Edit", self.edit("pub fn sub", "#[cfg(not(test))]\npub fn sub", path="src/plain.rs")),
                         "deny")
        self.assertEqual(self.v("Edit", self.edit("pub fn real() -> u8 {", "pub fn real2() -> u8 { 1 }\n#[cfg(not(test))]\n"
                                                  "pub fn real() -> u8 {", path="src/support.rs")), "deny")
        # A deletion that joins two lines into one (the tool's newline swallow).
        self.assertEqual(self.v("Edit", self.edit(" Z", "", path="src/join.rs")), "deny")
        # A rule without guarded_lines guards nothing.
        rule = {k: v for k, v in self.RUST["inline_tests"][0].items() if k != "guarded_lines"}
        self.assertEqual(self.v("Edit", self.edit("pub fn sub", "#[cfg(not(test))]\npub fn sub", path="src/plain.rs"),
                                cfg=dict(self.RUST, inline_tests=[rule])), "allow")
        # Removing one changes what the tests exercise, too.
        self.assertEqual(self.v("Edit", self.edit("#[cfg(not(test))]\n", "", path="src/support.rs")), "deny")
        # Ordinary production edits stay open.
        self.assertEqual(self.v("Edit", self.edit("    a + b\n", "    let s = a + b;\n    s\n")), "allow")

    def test_a_test_edit_is_named_as_one(self):
        # The marker line itself matches guarded_lines; the deny must still say
        # "this changes the tests", the message that tells the session what to do.
        event = {"tool_name": "Edit", "tool_input": self.edit("#[cfg(test)]\nmod tests {", "mod tests {"),
                 "cwd": self.root}
        reasons = guard.decide(event, dict(self.RUST, profile="stable"), self.root, lock_present=True,
                               branch_fn=lambda _cwd: "feature/x")[1]
        self.assertTrue(any("changes the tests inside" in r for r in reasons), reasons)

    def test_test_helper_modules_are_tests(self):
        self.assertEqual(self.v("Edit", self.edit("        2\n", "        3\n", path="src/support.rs")), "deny")
        self.assertEqual(self.v("Edit", self.edit("    1\n", "    9\n", path="src/support.rs")), "allow")

    def test_shell_writes_to_rust_files(self):
        # Verifier, 2026-09-28: a check that reads the file on disk misses `cd`,
        # globs and new files, so a shell write to ANY covered file is refused
        # by name under the lock, the way tests/* is. Edit and Write stay open.
        for cmd in ("sed -i 's/4/5/' src/lib.rs", "rm src/lib.rs", "git checkout -- src/lib.rs",
                    "echo '// x' >> src/lib.rs", "cp /tmp/other.rs src/lib.rs",
                    "sed -i 's/a - b/b - a/' src/plain.rs", "printf '#[cfg(test)] mod t {}' >> src/plain.rs",
                    "cp src/lib.rs src/copy.rs", "cd src && sed -i 's/4/5/' lib.rs",
                    "sed -i 's/4/5/' src/*.rs", "sed -i 's/4/5/' src/lib.r?",
                    "sed -i 's/4/5/' src/{lib,plain}.rs", "sed -i 's/4/5/' src/lib.{rs,bak}"):
            self.assertEqual(self.v("Bash", {"command": cmd}), "deny", cmd)
            self.assertEqual(self.v("Bash", {"command": cmd}, lock=False), "allow", cmd)
        for cmd in ("cat src/lib.rs", "sed -i 's/a/b/' src/notes.md", "cargo test -p x"):
            self.assertEqual(self.v("Bash", {"command": cmd}), "allow", cmd)

    def test_inline_code_writes_to_rust_files(self):
        # The 2026-10-04 gap (rikurinode, electrs_phase.rs): a python heredoc
        # wrote a Rust file under the lock and passed, while `sed -i` on the
        # same file was refused — interpreter writes were checked against test
        # FILES only. Now refused like a shell write; Edit/Write stay open.
        for cmd in ("python3 - <<'EOF'\np='src/lib.rs'\ns=open(p).read()\nopen(p,'w').write(s.replace('4','5'))\nEOF",
                    "python3 -c \"open('src/lib.rs','w').write('')\"",
                    "node -e \"require('fs').writeFileSync('src/plain.rs', '')\"",
                    "cd src && python3 - <<'EOF'\nopen('lib.rs','a').write('x')\nEOF",
                    "python3 - <<'EOF'\nfrom pathlib import Path\nPath('src/new.rs').write_text('fn x() {}')\nEOF",
                    # unresolvable target: strict, any covered path in the code counts
                    "python3 - \"$f\" <<'EOF'\nimport sys\nopen(sys.argv[1],'w').write(open('src/lib.rs').read())\nEOF"):
            self.assertEqual({"cmd": cmd, "v": self.v("Bash", {"command": cmd})}, {"cmd": cmd, "v": "deny"})
            self.assertEqual({"cmd": cmd, "v": self.v("Bash", {"command": cmd}, lock=False)},
                             {"cmd": cmd, "v": "allow"})
        for cmd in ("python3 -c \"print(open('src/lib.rs').read())\"",
                    "python3 - <<'EOF'\nopen('docs/notes.md','w').write('see src/lib.rs')\nEOF",
                    "node -e \"require('fs').writeFileSync('src/notes.md', '// src/lib.rs')\""):
            self.assertEqual({"cmd": cmd, "v": self.v("Bash", {"command": cmd})}, {"cmd": cmd, "v": "allow"})

    def test_lock_bypasses_found_by_the_verifier(self):
        # Verifier, 2026-10-05: shapes that still wrote a covered file under the
        # lock — a path built from pieces, a path passed as an argument,
        # bundled/long in-place flags, perl's paren-less open. (A script FILE
        # run by path is out of scope: the guard judges commands and never
        # reads the files a command runs — verifier round 2: reading them
        # leaked secret-file contents into reasons and blew the time budget.)
        denied = (
            "python3 - <<'EOF'\nd='src'\nopen(f'{d}/lib.rs','w').write('')\nEOF",
            "python3 - <<'EOF'\nd='src'\nopen(d + '/lib.rs','w').write('')\nEOF",
            "node -e \"const d='src'; require('fs').writeFileSync(`${d}/lib.rs`, '')\"",
            "python3 -c \"import sys; open(sys.argv[1],'w').write('')\" src/lib.rs",
            "python3 - src/lib.rs <<'EOF'\nimport sys\nopen(sys.argv[1],'w').write('')\nEOF",
            "sed -Ei 's/4/5/' src/lib.rs", "sed --in-place=.bak 's/4/5/' src/lib.rs",
            "perl -pi -e 's/4/5/' src/lib.rs", "awk -i inplace '{print}' src/lib.rs",
            "perl -e 'open F, \">src/lib.rs\"; print F 1'",
            # the same holes for a test FILE (built path)
            "python3 - <<'EOF'\nd='tests'\nopen(f'{d}/test_x.py','w').write('')\nEOF",
        )
        for cmd in denied:
            self.assertEqual({"cmd": cmd, "v": self.v("Bash", {"command": cmd})}, {"cmd": cmd, "v": "deny"})
            self.assertEqual({"cmd": cmd, "v": self.v("Bash", {"command": cmd}, lock=False)},
                             {"cmd": cmd, "v": "allow"})
        for cmd in ("perl -ne 'print' src/lib.rs", "sed -n '1,5p' src/lib.rs",
                    "python3 - <<'EOF'\nopen('/tmp/x.md','w').write('d/lib.rs')\nEOF",
                    # code that writes nothing: a read-only loop over the files
                    "python3 - <<'EOF'\nimport glob\nfor f in sorted(glob.glob('src/*.rs')):\n"
                    "    print(f, len(open(f).read()))\nEOF",
                    # verifier round 2: perl READS ('<' modes) are not writes
                    "perl -e 'open(F, \"<src/lib.rs\"); print <F>'",
                    "perl -e 'open my $fh, \"<\", \"src/lib.rs\"; print <$fh>'",
                    # ... and an argument belongs to its own interpreter run only
                    "python3 -c \"import subprocess; subprocess.run(['true'])\" && python3 -m mytool src/lib.rs"):
            self.assertEqual({"cmd": cmd, "v": self.v("Bash", {"command": cmd})}, {"cmd": cmd, "v": "allow"})

    def test_huge_inline_code_stays_inside_the_time_budget(self):
        # Verifier round 2, 2026-10-05: the write scanner never checked the
        # guard's deadline; unbalanced `open(` calls made it quadratic (a 40 KB
        # script: 25 s, past the hook's 10 s timeout). Too slow = ask, in time.
        import time
        code = "\n".join("open('/tmp/x%d.md', 'w'" % i for i in range(4000))
        cmd = "python3 - <<'EOF'\n" + code + "\nEOF"
        t0 = time.time()
        v = self.v("Bash", {"command": cmd})
        self.assertLess(time.time() - t0, 8.0)
        self.assertIn(v, ("ask", "deny"))

    def test_the_guards_own_commands_run_under_the_lock(self):
        # Verifier, 2026-10-05: scanning script FILES read guard.py itself (full
        # of test paths and writes), so `guard.py fix-lock off` was refused under
        # the lock. The repo's tracked scripts are not ad-hoc edits.
        for cmd in ("python3 .claude/hooks/guard.py fix-lock off", "python3 .claude/hooks/guard.py fix-lock status",
                    "python3 .claude/hooks/guard.py profile stable"):
            self.assertNotEqual({"cmd": cmd, "v": verdict("Bash", {"command": cmd}, lock=True)},
                                {"cmd": cmd, "v": "deny"})

    def test_denies_hold_in_development(self):
        self.assertEqual(self.v("Edit", self.edit(", 4)", ", 5)"), profile="development"), "deny")
        self.assertEqual(self.v("Bash", {"command": "rm src/lib.rs"}, profile="development"), "deny")

    def test_a_file_that_cannot_be_read_is_refused(self):
        self.assertEqual(self.v("Edit", self.edit("x", "y", path="src/dir.rs")), "deny")
        self.assertEqual(self.v("Bash", {"command": "rm -r src/dir.rs"}), "deny")
        self.assertEqual(self.v("Bash", {"command": "rm -r src/dir.rs"}, lock=False), "allow")

    def test_config_validation(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "guard-config.json")
            for bad in ("*.rs", [{"glob": "", "starts_at": "x"}], [{"glob": "*.rs"}],
                        [{"glob": "*.rs", "starts_at": "("}], ["*.rs"],
                        [{"glob": "*.rs", "starts_at": "x", "attached_above": 3}],
                        [{"glob": "*.rs", "starts_at": "x", "attached_above": "("}],
                        [{"glob": "*.rs", "starts_at": "x", "guarded_lines": 3}],
                        [{"glob": "*.rs", "starts_at": "x", "guarded_lines": "("}]):
                with open(path, "w") as f:
                    json.dump(dict(CFG, inline_tests=bad), f)
                with self.assertRaises(ValueError, msg=repr(bad)):
                    guard.load_config(path)
            with open(path, "w") as f:
                json.dump(self.RUST, f)
            self.assertEqual(guard.load_config(path)["inline_tests"], self.RUST["inline_tests"])


class TestModuleFiles(unittest.TestCase):
    """Verifier, 2026-10-11 (owner's choice 1(a)): a test module can live in a
    file of its own, declared from its parent with `#[cfg(test)] mod tests;`.
    That file holds no marker, so the lock left it editable. The guard follows
    `mod x;` declarations made under cfg(test), the way rustc finds their
    files; a production `mod x;` stays editable wherever it sits."""

    # In src/outer.rs every brace, quote and `mod x;` inside a comment, string
    # or character literal would misplace `deep`, `pathy`, `inner_prod` or
    # `late` if the scanner read it as code.
    OUTER = ('pub fn f() {}\n\n#[cfg(test)]\nmod tests {\n    // { a brace in a comment\n    /* { } } */\n'
             '    const S: &str = "{ mod quoted; }}";\n    const R: &str = r#"}" mod raw; {"#;\n'
             '    const B: &[u8] = b"}";\n    const C: char = \'{\';\n    const Q: char = \'"\';\n'
             '    const E: char = \'\\\'\';\n    fn life<\'a>(x: &\'a str) -> &\'a str {\n        x\n    }\n'
             '    struct W<\'a> {\n        s: &\'a str,\n    }\n    const D: &str = "a \\" } b";\n'
             '    const CS: &CStr = c"}";\n    const CR: &CStr = cr#"} {"#;\n\n'
             '    mod deep;\n\n    #[path = "x/y.rs"]\n    mod pathy;\n}\n\nmod inner_prod;\n\n#[cfg(test)]\nmod late;\n')
    FILES = {
        "src/lib.rs": ('pub mod plain;\npub mod outer;\npub mod fixtures;\nmod whole;\n\n#[cfg(test)]\nmod tests;\n\n'
                       '#[cfg(test)]\n#[path = "support_tests.rs"]\nmod support;\n\n'
                       '#[cfg(any(test, feature = "fuzz"))]\npub mod helpers;\n\n#[cfg(test)]\nmod checks;\n'),
        "src/plain.rs": "pub fn two() -> u8 {\n    2\n}\n",
        "src/fixtures.rs": "pub const REAL: u8 = 1;\n",
        "src/helpers.rs": "pub fn fake() -> u8 {\n    3\n}\n",
        "src/support_tests.rs": "#[test]\nfn s() {\n    assert!(true);\n}\n\nmod sup_child;\n",
        "src/sup_child.rs": "pub fn c() {}\n",
        "src/odd.rs": "pub fn o() {}\n\n#[cfg(test)]\nmod /* a comment */ odd_tests;\n",
        "src/odd/odd_tests.rs": "#[test]\nfn o() {}\n",
        "src/tests.rs": "use super::*;\n\nmod fixtures;\n\n#[test]\nfn t() {\n    assert_eq!(plain::two(), 2);\n}\n",
        "src/tests/fixtures.rs": "pub const X: u8 = 1;\n",
        "src/outer.rs": OUTER,
        "src/outer/inner_prod.rs": "pub fn p() {}\n",
        "src/outer/late.rs": "#[test]\nfn l() {}\n",
        "src/outer/tests/deep.rs": "#[test]\nfn d() {}\n",
        "src/outer/tests/x/y.rs": "#[test]\nfn y() {}\n",
        "src/bin/tool.rs": "fn main() {}\n\n#[cfg(test)]\nmod tool_tests;\n",
        "src/bin/tool_tests.rs": "#[test]\nfn t() {}\n",
        "src/kw.rs": "pub fn k() {}\n\n#[cfg(test)]\nmod r#type;\n",
        "src/kw/type.rs": "#[test]\nfn t() {}\n",
        "src/whole.rs": "#![cfg(test)]\n\nmod sub;\n\n#[test]\nfn w() {}\n",
        "src/whole/sub.rs": "pub fn s() {}\n",
        "src/dirmod/mod.rs": "pub fn d() {}\n\n#[cfg(test)]\nmod t;\n",
        "src/dirmod/t.rs": "#[test]\nfn t() {}\n",
        "src/missing.rs": "pub fn m() {}\n\n#[cfg(test)]\nmod gone;\n",
        "src/visible.rs": "pub(crate) fn v() {}\n\n#[cfg(test)]\npub(crate) mod shared;\n",
        "src/visible/shared.rs": "pub fn s() {}\n",
        # Listed before src/lib.rs, which declares it: one pass over the files
        # would miss src/checks/helpers2.rs (verifier round 2, its mutant O6).
        "src/checks.rs": "mod helpers2;\n\n#[test]\nfn c() {}\n",
        "src/checks/helpers2.rs": "pub fn h() {}\n",
    }
    TESTS = ("src/tests.rs", "src/tests/fixtures.rs", "src/support_tests.rs", "src/helpers.rs",
             "src/outer/tests/deep.rs", "src/outer/tests/x/y.rs", "src/outer/late.rs", "src/bin/tool_tests.rs",
             "src/kw/type.rs", "src/whole/sub.rs", "src/dirmod/t.rs", "src/visible/shared.rs",
             "src/sup_child.rs", "src/odd/odd_tests.rs", "src/checks.rs", "src/checks/helpers2.rs")
    CODE = ("src/plain.rs", "src/outer/inner_prod.rs", "src/lib.rs", "src/outer.rs", "src/bin/tool.rs",
            "src/kw.rs", "src/dirmod/mod.rs", "src/visible.rs", "src/odd.rs")
    # No test_globs: each repository's own (`*/tests/*`, `*/fixtures/*`) would
    # deny some of these paths by name and hide what this class checks.
    RUST = dict(InlineTests.RUST, test_globs=[])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        for name, text in self.FILES.items():
            os.makedirs(os.path.join(self.root, os.path.dirname(name)), exist_ok=True)
            with open(os.path.join(self.root, name), "w", newline="") as f:
                f.write(text)
        # A file that is not UTF-8 beside them declares nothing rustc could compile.
        with open(os.path.join(self.root, "src", "bytes.rs"), "wb") as f:
            f.write(b"// \xff\n#[cfg(test)]\nmod plain;\n")

    def tearDown(self):
        self._tmp.cleanup()

    def v(self, tool, tin, lock=True, cfg=None):
        event = {"tool_name": tool, "tool_input": tin, "cwd": self.root}
        return guard.decide(event, dict(cfg or self.RUST, profile="stable"), self.root,
                            lock_present=lock, branch_fn=lambda _cwd: "feature/x")[0]

    def changes(self, path):
        """An Edit, a MultiEdit and a Write that each add a comment at the top
        of `path`, above its first line: never inside a test region, never
        attached to a marker, so only a test module refuses them."""
        first = self.FILES[path].split("\n")[0] + "\n"
        return (("Edit", {"file_path": path, "old_string": first, "new_string": "// x\n" + first}),
                ("MultiEdit", {"file_path": path, "edits": [{"old_string": first, "new_string": "// x\n" + first}]}),
                ("Write", {"file_path": path, "content": "// x\n" + self.FILES[path]}))

    def test_a_test_module_file_is_read_only(self):
        for path in self.TESTS:
            for tool, tin in self.changes(path):
                self.assertEqual(self.v(tool, tin), "deny", (tool, path))
                self.assertEqual(self.v(tool, tin, lock=False), "allow", (tool, path))

    def test_production_modules_stay_open(self):
        # src/outer/inner_prod.rs is declared below a test module.
        for path in self.CODE:
            for tool, tin in self.changes(path):
                self.assertEqual(self.v(tool, tin), "allow", (tool, path))

    def test_both_places_of_a_test_module_are_locked(self):
        # Verifier round 1, D3; owner's choice "Lock both places" (2026-10-11).
        # rustc reads `mod x;` in src/bin/tool.rs from src/bin/tool/ when the
        # file is a module and from src/bin/ when it is a crate root (or was
        # loaded by #[path]); the guard cannot tell which. Choosing by which
        # file exists let a locked session write a decoy in one place and
        # unlock the other. Both places are read-only now, existing or not —
        # and so is a production file there that shares a test module's name
        # (src/fixtures.rs, beside src/tests.rs's `mod fixtures;`).
        for path in ("src/bin/tool/tool_tests.rs", "src/bin/tool/tool_tests/mod.rs", "src/fixtures.rs",
                     "src/support_tests/sup_child.rs"):
            self.assertEqual(self.v("Write", {"file_path": path, "content": "pub fn d() {}\n"}), "deny", path)
            self.assertEqual(self.v("Write", {"file_path": path, "content": "pub fn d() {}\n"}, lock=False),
                             "allow", path)
        # A decoy already in one place does not unlock the other.
        os.makedirs(os.path.join(self.root, "src", "bin", "tool"))
        with open(os.path.join(self.root, "src", "bin", "tool", "tool_tests.rs"), "w") as f:
            f.write("pub fn d() {}\n")
        self.assertEqual(self.v("Edit", self.changes("src/bin/tool_tests.rs")[0][1]), "deny")

    def test_the_declaration_of_a_test_file_is_locked_in_its_parent(self):
        # Verifier round 1, D4: src/whole.rs is tests from its first line
        # (`#![cfg(test)]`). Deleting `mod whole;` from src/lib.rs, or adding
        # `#[cfg(any())]` above it, switched every test in it off.
        for old, new in (("mod whole;\n", ""), ("mod whole;\n", "#[cfg(any())]\nmod whole;\n"),
                         ("mod whole;\n", "#[cfg(feature = \"never\")]\nmod whole;\n"),
                         ("mod whole;\n", "mod other;\n")):
            change = {"file_path": "src/lib.rs", "old_string": old, "new_string": new}
            self.assertEqual(self.v("Edit", change), "deny", new)
            self.assertEqual(self.v("Edit", change, lock=False), "allow", new)
        # The same changes to a production module's declaration are the fix's
        # business — also for src/outer.rs, which holds tests below its code:
        # they stay locked inside it, and switching the file off takes its
        # code with it (a limit the record lists).
        for old, new in (("pub mod plain;\n", ""), ("pub mod plain;\n", "#[cfg(any())]\npub mod plain;\n"),
                         ("pub mod outer;\n", "#[cfg(any())]\npub mod outer;\n")):
            self.assertEqual(self.v("Edit", {"file_path": "src/lib.rs", "old_string": old, "new_string": new}),
                             "allow", new)
        # Verifier round 2, F2: a blank line, a comment or another inner
        # attribute above `#![cfg(test)]` leaves the tests' region as it was,
        # so it may be written — and must not unlock the declaration.
        drop = {"file_path": "src/lib.rs", "old_string": "mod whole;\n", "new_string": ""}
        for top in ("\n", " \t\n", "/* a\n plain line\n*/\n", "#![allow(unused)]\n", "// a note\n", "\ufeff"):
            with open(os.path.join(self.root, "src", "whole.rs"), "w") as f:
                f.write(top + self.FILES["src/whole.rs"])
            self.assertEqual(self.v("Edit", drop), "deny", repr(top))
        # Verifier round 3, I4: an item written above `#![cfg(test)]` (rustc
        # then rejects the file) made it look partly code, and its declaration
        # could go. Every inner attribute outside a block counts.
        for top in ("use std::fmt;\n\n", "fn _x() {}\n\n", "/* { */\n"):
            with open(os.path.join(self.root, "src", "whole.rs"), "w") as f:
                f.write(top + self.FILES["src/whole.rs"])
            self.assertEqual(self.v("Edit", drop), "deny", repr(top))
        # The module file's own rules say whether it is all tests: a rule that
        # names only src/lib.rs leaves src/whole.rs unlocked (the tripwire
        # names it), and its declaration with it.
        lib_only = dict(self.RUST, inline_tests=[dict(self.RUST["inline_tests"][0], glob="lib.rs")])
        self.assertEqual(self.v("Edit", drop, cfg=lib_only), "allow")
        # An outer `#[cfg(test)]` on a file's first item is that item's, not the
        # file's, and so is an inner one inside a block: src/plain.rs stays
        # production code, its declaration open.
        for body in ("#[cfg(test)]\nfn t() {}\n", "mod inner {\n    #![cfg(test)]\n}\n"):
            with open(os.path.join(self.root, "src", "plain.rs"), "w") as f:
                f.write(body + self.FILES["src/plain.rs"])
            self.assertEqual(self.v("Edit", {"file_path": "src/lib.rs", "old_string": "pub mod plain;\n",
                                             "new_string": ""}), "allow", body)

    def test_a_crafted_attribute_cannot_stall_the_hook(self):
        # Verifier round 2, F1: `#` and 120,000 spaces in a file above every
        # folder made a locked edit take 13.6 s; one MultiEdit adding such a
        # comment above the tests took 27 s — inside single regex calls.
        import time
        with open(os.path.join(self.root, "zz.rs"), "w") as f:
            f.write("mod x; #" + " " * 120000)
        crafted = {"file_path": "src/outer.rs", "edits": [
            {"old_string": "pub fn f() {}\n", "new_string": "/*\n#" + " " * 120000 + "\n*/\npub fn f() {}\n"},
            {"old_string": "#[cfg(test)]\nmod late;\n", "new_string": "mod late;\n"}]}
        t0 = time.time()
        self.assertEqual(self.v("Edit", self.changes("src/tests.rs")[0][1]), "deny")
        self.assertEqual(self.v("Edit", self.changes("src/plain.rs")[0][1]), "allow")
        self.assertEqual(self.v("MultiEdit", crafted), "deny")
        self.assertLess(time.time() - t0, 4.0)

    def test_many_attributes_and_declarations_cannot_stall_the_hook(self):
        # Verifier round 3, I1: one allowed locked Write of a production file
        # with 2,000 inner attributes and 2,000 `mod` lines made every later
        # locked edit take 13 s — each declaration carried and matched all
        # 2,000 attributes, again on every pass.
        import time
        for attr in ("#![allow(unused)]\n", "#![allow(unused_%d)]\n"):
            with open(os.path.join(self.root, "zz.rs"), "w") as f:
                f.write("".join(attr.replace("%d", str(i)) for i in range(2000))
                        + "".join("mod a%06d;\n" % i for i in range(2000)))
            t0 = time.time()
            self.assertEqual(self.v("Edit", self.changes("src/tests.rs")[0][1]), "deny", attr)
            self.assertEqual(self.v("Edit", self.changes("src/plain.rs")[0][1]), "allow", attr)
            self.assertLess(time.time() - t0, 4.0, attr)

    def test_past_256_attributes_a_declaration_counts_as_test_code(self):
        # The cap that keeps I1 bounded errs on the safe side: with more than
        # 256 distinct attributes in its scope, a declaration is test code.
        os.makedirs(os.path.join(self.root, "src", "many"))
        with open(os.path.join(self.root, "src", "many", "m.rs"), "w") as f:
            f.write("pub fn m() {}\n")
        change = {"file_path": "src/many/m.rs", "old_string": "pub fn m() {}\n", "new_string": "pub fn n() {}\n"}
        for count, verdict in ((256, "allow"), (257, "deny")):
            with open(os.path.join(self.root, "src", "many.rs"), "w") as f:
                f.write("".join("#![allow(lint_%d)]\n" % i for i in range(count)) + "mod m;\n")
            self.assertEqual(self.v("Edit", change), verdict, count)
        # A repeated attribute counts once; those of a closed block, or of an
        # item already declared, leave the scope.
        before = ("#![allow(same)]\n" * 300, "".join("#[allow(x_%d)]\n" % i for i in range(200)) + "fn f() {}\n",
                  "".join("#[allow(x_%d)]\n" % i for i in range(200)) + "use x;\n")
        for text in before:
            with open(os.path.join(self.root, "src", "many.rs"), "w") as f:
                f.write(text + "".join("#![allow(y_%d)]\n" % i for i in range(100)) + "mod m;\n")
            self.assertEqual(self.v("Edit", change), "allow", text[:30])

    def test_the_scanners_keep_to_their_deadline(self):
        # R12: past the deadline the scans stop (the hook then asks), however
        # few declarations a file holds (verifier round 6's mutant E9).
        for scan, text in ((guard.rust_file_modules, "mod a;\n" * 3), (guard.rust_file_attrs, "#![cfg(test)]\n")):
            with self.assertRaises(guard._TooSlow):
                scan(text, 0.0)

    def test_the_scanner_takes_linear_time(self):
        import time
        for text in ("#" + " " * 60000, "#!" + " " * 60000, "mod" + " " * 60000, "mod x" + " " * 60000):
            t0 = time.time()
            guard.rust_file_modules(text)
            self.assertLess(time.time() - t0, 0.5, text[:6])
        t0 = time.time()
        guard.RUST_INLINE_TEST.search("#" + " " * 60000)
        guard.RUST_PATH.match("#" + " " * 60000)
        self.assertLess(time.time() - t0, 0.5)

    def test_a_crafted_file_cannot_stall_the_hook(self):
        # Verifier round 1, D1: an opener never closed (`/*`, `r#"`) made the
        # scanner re-read the rest of the file for each one; 40,000 of them in
        # a file above every folder took 16 s, past the hook's 10 s limit. An
        # unclosed comment or string now runs to the end of the file, as
        # rustc reads it.
        import time
        with open(os.path.join(self.root, "zz.rs"), "w") as f:
            f.write("mod x;\n" + "/* " * 40000)
        with open(os.path.join(self.root, "src", "yy.rs"), "w") as f:
            f.write("mod y;\n" + 'r#" ' * 40000)
        t0 = time.time()
        self.assertEqual(self.v("Edit", self.changes("src/tests.rs")[0][1]), "deny")
        self.assertEqual(self.v("Edit", self.changes("src/plain.rs")[0][1]), "allow")
        self.assertLess(time.time() - t0, 4.0)

    def test_a_check_that_runs_out_of_time_asks(self):
        # The lookup keeps to the guard's time budget; past it the owner decides.
        with mock.patch.object(guard, "CHECK_TIME_BUDGET", -1.0):
            self.assertEqual(self.v("Edit", self.changes("src/plain.rs")[0][1]), "ask")

    def test_a_test_module_that_does_not_exist_yet(self):
        # `#[cfg(test)] mod gone;` with no file: writing one creates a test
        # module, in any place it could be.
        for path in ("src/missing/gone.rs", "src/missing/gone/mod.rs", "src/gone.rs", "src/gone/mod.rs"):
            self.assertEqual(self.v("Write", {"file_path": path, "content": "#[test]\nfn g() {}\n"}), "deny", path)
        self.assertEqual(self.v("Write", {"file_path": "src/missing/other.rs", "content": "pub fn o() {}\n"}), "allow")

    def test_the_deny_names_the_declaring_file(self):
        event = {"tool_name": "Edit", "tool_input": self.changes("src/tests/fixtures.rs")[0][1], "cwd": self.root}
        reasons = guard.decide(event, dict(self.RUST, profile="stable"), self.root, lock_present=True,
                               branch_fn=lambda _cwd: "feature/x")[1]
        self.assertTrue(any("src/tests/fixtures.rs" in r and "src/tests.rs" in r and "test module" in r
                            for r in reasons), reasons)

    def test_the_repositorys_rules_decide(self):
        tests = self.changes("src/tests.rs")[0][1]
        helpers = self.changes("src/helpers.rs")[0][1]
        # No rule: the repository has not opted in.
        plain = {k: v for k, v in self.RUST.items() if k != "inline_tests"}
        self.assertEqual(self.v("Edit", tests, cfg=plain), "allow")
        # A rule that knows only `#[cfg(test)]` does not see cfg(any(test, …)).
        exact = dict(self.RUST, inline_tests=[dict(self.RUST["inline_tests"][0], starts_at=r"^#\[cfg\(test\)\]")])
        self.assertEqual(self.v("Edit", tests, cfg=exact), "deny")
        self.assertEqual(self.v("Edit", helpers, cfg=exact), "allow")
        # Only files the rule's glob names are checked.
        bins = dict(self.RUST, inline_tests=[dict(self.RUST["inline_tests"][0], glob="src/bin/*.rs")])
        self.assertEqual(self.v("Edit", self.changes("src/bin/tool_tests.rs")[0][1], cfg=bins), "deny")
        self.assertEqual(self.v("Edit", tests, cfg=bins), "allow")
        # The declaring file's rules read its declaration: a rule naming only
        # the module's file does not.
        child = dict(self.RUST, inline_tests=[dict(self.RUST["inline_tests"][0], glob="tests.rs")])
        self.assertEqual(self.v("Edit", tests, cfg=child), "allow")

    def test_a_folder_that_cannot_be_listed_is_refused(self):
        # Under the lock the guard reads the folders above a file to know
        # whether it is a test module; when it cannot, it refuses.
        change = self.changes("src/plain.rs")[0][1]
        with mock.patch.object(guard.os, "listdir", side_effect=PermissionError(13, "Permission denied")):
            self.assertEqual(self.v("Edit", change), "deny")
            self.assertEqual(self.v("Edit", change, lock=False), "allow")

    def test_shell_writes_are_refused_as_before(self):
        for cmd in ("sed -i 's/1/2/' src/tests/fixtures.rs", "rm src/outer/tests/deep.rs",
                    "echo '// x' >> src/kw/type.rs"):
            self.assertEqual(self.v("Bash", {"command": cmd}), "deny", cmd)
            self.assertEqual(self.v("Bash", {"command": cmd}, lock=False), "allow", cmd)

    def test_the_scanner(self):
        mods = guard.rust_file_modules(self.OUTER)
        self.assertEqual([(n, inline, path) for n, inline, path, _attrs in mods],
                         [("deep", ["tests"], None), ("pathy", ["tests"], "x/y.rs"), ("inner_prod", [], None),
                          ("late", [], None)])
        attrs = {n: a for n, _i, _p, a in mods}
        self.assertEqual(attrs["deep"], ["#[cfg(test)]"])
        self.assertEqual(attrs["pathy"], ["#[cfg(test)]", '#[path = "x/y.rs"]'])
        self.assertEqual(attrs["inner_prod"], [])
        self.assertEqual(attrs["late"], ["#[cfg(test)]"])
        # Inner attributes apply to their file or module; outer ones to the next item only.
        text = ('#![cfg(test)]\n#[cfg(test)]\nuse x;\nmod a;\n#[path = "q"]\nmod m {\n    #![allow(x)]\n    mod b;\n}\n'
                '#[cfg(test)]\nfn f() {\n    mod c;\n}\npub(in crate::x) mod d;\nmod r#e;\nmod \u00e9t\u00e9;\npremod z;\n')
        self.assertEqual(guard.rust_file_modules(text),
                         [("a", [], None, ["#![cfg(test)]"]), ("b", ["q"], None, ["#![cfg(test)]", '#[path = "q"]',
                                                                                    "#![allow(x)]"]),
                          ("c", [], None, ["#![cfg(test)]", "#[cfg(test)]"]), ("d", [], None, ["#![cfg(test)]"]),
                          ("e", [], None, ["#![cfg(test)]"]), ("\u00e9t\u00e9", [], None, ["#![cfg(test)]"])])

    def test_a_modules_inner_path_names_its_folder(self):
        # Corpus probe, 2026-10-11 (cargo-mutants' fixture of the Rust
        # reference): an inline module can name its folder from inside, with
        # `#![path]`. Inside a function it names nothing.
        text = ('mod n {\n    #![path = "r"]\n    mod g;\n    fn h() {\n        #![path = "s"]\n'
                '        #[path = "q.rs"]\n        mod q;\n    }\n    mod k;\n}\n')
        self.assertEqual(guard.rust_file_modules(text),
                         [("g", ["r"], None, ['#![path = "r"]']),
                          ("q", ["r"], "q.rs", ['#![path = "r"]', '#![path = "s"]', '#[path = "q.rs"]']),
                          ("k", ["r"], None, ['#![path = "r"]'])])
        # Verifier round 2 (its mutants O5, OM9a): `# [ path = "…" ]` is a path
        # too, and an inline module's #[path] counts wherever it sits among its
        # attributes.
        self.assertEqual(guard.rust_file_modules('# [ path = "p.rs" ]\n#[cfg(test)]\nmod t;\n'),
                         [("t", [], "p.rs", ['# [ path = "p.rs" ]', "#[cfg(test)]"])])
        self.assertEqual([m[:2] for m in guard.rust_file_modules('#[path = "q2"]\n#[allow(x)]\nmod m2 {\n    mod b2;\n}\n')],
                         [("b2", ["q2"])])
        # An attribute runs to its own closing bracket, past brackets inside it.
        self.assertEqual(guard.rust_file_modules("#[x([1])]\n#[cfg(test)]\nmod y;\n"),
                         [("y", [], None, ["#[x([1])]", "#[cfg(test)]"])])

    def test_a_declaration_as_rustc_reads_it(self):
        # Verifier round 1, D2: rustc reads each of these as `mod tests;` —
        # comments and Rust's own whitespace (U+200E, U+200F, U+2028, U+0085,
        # which Python's \s does not take) may sit between its words.
        for text in ("#[cfg(test)]\nmod /* c */ tests;\n", "#[cfg(test)]\nmod tests /* c */;\n",
                     "#[cfg(test)]\nmod // c\ntests;\n", "#[cfg(test)]\nmod\u200etests\u200f;\n",
                     "#[cfg(test)]\nmod\u2028tests\x85;\n", "#[cfg(test)] /* c */ mod tests;\n"):
            self.assertEqual(guard.rust_file_modules(text), [("tests", [], None, ["#[cfg(test)]"])], repr(text))
        # Not declarations: a macro's pattern (its expansion is unknown here), a
        # word that starts with `mod`, a space rustc does not skip (U+00A0).
        for text in ("macro_rules! m {\n    ($n:ident) => {\n        mod $n;\n    };\n}\n", "modtests;\n",
                     "mod\u00a0tests;\n", "let r#mod = 1;\n"):
            self.assertEqual(guard.rust_file_modules(text), [], repr(text))

    def test_comments_and_strings_end_where_rustc_ends_them(self):
        # Verifier round 1, D5 and D7: block comments nest; a comment or a raw
        # string ends at its own first closer, not the file's last; C strings
        # are strings; a #[path] may come before or after the cfg.
        self.assertEqual([m[0] for m in guard.rust_file_modules(
            "/* outer /* inner */ mod hidden; */\n#[cfg(test)]\nmod shown;\n")], ["shown"])
        self.assertEqual([m[0] for m in guard.rust_file_modules(
            "/* a */\n#[cfg(test)]\nmod x;\n/* b */\nconst A: &str = r\"a\";\n#[cfg(test)]\nmod y;\n"
            "const B: &str = r\"b\";\nconst C: &CStr = c\"mod z; {\";\nconst D: &CStr = cr\"mod w; }\";\n")],
            ["x", "y"])
        self.assertEqual(guard.rust_file_modules('#[path = "p.rs"]\n#[cfg(test)]\nmod t;\n'),
                         [("t", [], "p.rs", ['#[path = "p.rs"]', "#[cfg(test)]"])])
        # Never closed: the rest of the file is the comment or the string.
        self.assertEqual(guard.rust_file_modules("mod a;\n/* never closed\nmod b;\n"), [("a", [], None, [])])
        self.assertEqual(guard.rust_file_modules('mod a;\nconst S: &str = r#"never closed\nmod b;\n'),
                         [("a", [], None, [])])
        self.assertEqual(guard.rust_file_modules('mod a;\nconst S: &str = "never closed\nmod b;\n'),
                         [("a", [], None, [])])

    def test_where_a_module_file_is_looked_for(self):
        self.assertEqual(guard.module_files("src/lib.rs", "x", [], None), [["src/x.rs", "src/x/mod.rs"]])
        self.assertEqual(guard.module_files("a/main.rs", "x", [], None), [["a/x.rs", "a/x/mod.rs"]])
        self.assertEqual(guard.module_files("src/m/mod.rs", "x", ["i"], None), [["src/m/i/x.rs", "src/m/i/x/mod.rs"]])
        self.assertEqual(guard.module_files("src/foo.rs", "x", [], None),
                         [["src/foo/x.rs", "src/foo/x/mod.rs"], ["src/x.rs", "src/x/mod.rs"]])
        self.assertEqual(guard.module_files("src/foo.rs", "x", [], "t.rs"), [["src/t.rs"]])
        self.assertEqual(guard.module_files("src/foo.rs", "x", ["a", "b"], "t.rs"), [["src/foo/a/b/t.rs"], ["src/a/b/t.rs"]])
        self.assertEqual(guard.module_files("src/a/foo.rs", "x", [], "../b/t.rs"), [["src/b/t.rs"]])
        # Outside the repository: nothing the lock could protect.
        self.assertEqual(guard.module_files("lib.rs", "x", [], "../out.rs"), [])
        self.assertEqual(guard.module_files("lib.rs", "x", [], "/etc/x.rs"), [])


class InlineTestCoverage(unittest.TestCase):
    """The class tripwire behind GenericPolicy.test_tracked_inline_tests_have_a_rule
    (2026-10-11), in scratch git repositories. A tracked .rs file holding
    `#[cfg(test)]` is covered only when an `inline_tests` rule's glob names it
    AND its starts_at finds the tests from the file's first marker on; and
    `fix-lock on` says only what it really makes read-only."""

    SRC = InlineTests.SRC
    RULES = InlineTests.RUST["inline_tests"]
    PLAIN = InlineTests.PLAIN

    def repo(self, files: dict, untracked: dict | None = None) -> str:
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        for name, text in {**files, **(untracked or {})}.items():
            path = os.path.join(root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(text if isinstance(text, bytes) else text.encode())
        env = guard.git_env()
        subprocess.run(["git", "init", "-q", root], check=True, env=env)
        if files:
            subprocess.run(["git", "-C", root, "add", "--", *files], check=True, env=env)
        return root

    def cfg(self, rules: list | None) -> dict:
        cfg = json.loads(json.dumps(CFG))
        cfg.pop("fix_lock_preflight", None)
        cfg.pop("inline_tests", None)
        if rules is not None:
            cfg["inline_tests"] = rules
        return cfg

    def gaps(self, root: str, rules: list | None) -> list:
        return guard.uncovered_inline_tests(root, self.cfg(rules))

    def test_a_tracked_file_with_inline_tests_needs_a_rule(self):
        root = self.repo({"src/lib.rs": self.SRC, "src/plain.rs": self.PLAIN})
        self.assertEqual(self.gaps(root, None), ["src/lib.rs"])
        self.assertEqual(self.gaps(root, []), ["src/lib.rs"])
        self.assertEqual(self.gaps(root, self.RULES), [])

    def test_every_tracked_folder_counts(self):
        root = self.repo({"a/b/c/deep.rs": self.SRC, "top.rs": self.SRC})
        self.assertEqual(sorted(self.gaps(root, None)), ["a/b/c/deep.rs", "top.rs"])

    def test_the_rule_must_name_the_file(self):
        root = self.repo({"src/lib.rs": self.SRC, "crates/x/lib.rs": self.SRC})
        self.assertEqual(self.gaps(root, [dict(self.RULES[0], glob="crates/*.rs")]), ["src/lib.rs"])

    def test_the_rule_must_find_the_tests(self):
        root = self.repo({"src/lib.rs": self.SRC})
        self.assertEqual(self.gaps(root, [dict(self.RULES[0], starts_at=r"^#\[test_only\]")]), ["src/lib.rs"])
        # A region starting inside the marker leaves its `#[` outside.
        self.assertEqual(self.gaps(root, [dict(self.RULES[0], starts_at=r"cfg\(test\)")]), ["src/lib.rs"])
        # A rule that finds only a LATER block leaves the first one editable.
        two = ("pub fn f() {}\n\n#[cfg(test)]\nfn helper() -> u8 {\n    1\n}\n\n"
               "pub fn g() {}\n\n#[cfg(test)]\nmod tests {}\n")
        root = self.repo({"src/two.rs": two})
        late = {"glob": "*.rs", "starts_at": r"^#\[cfg\(test\)\]\nmod tests"}
        self.assertEqual(self.gaps(root, [late]), ["src/two.rs"])
        self.assertEqual(self.gaps(root, self.RULES), [])
        self.assertEqual(self.gaps(root, [late, self.RULES[0]]), [], "one covering rule is enough")

    def test_only_real_markers_count(self):
        root = self.repo({"src/not.rs": "#[cfg(not(test))]\npub fn f() {}\n",
                          "src/comment.rs": "// #[cfg(test)] lives in lib.rs\npub fn f() {}\n",
                          "src/text.rs": 'const S: &str = "#[cfg(test)]";\n',
                          "src/spaced.rs": "pub fn f() {}\n\n  #[ cfg ( test ) ]\nmod tests {}\n",
                          "src/tabbed.rs": "pub fn f() {}\n\n\t#[cfg(test)]\nmod tests {}\n"})
        self.assertEqual(self.gaps(root, None), ["src/spaced.rs", "src/tabbed.rs"])
        self.assertEqual(self.gaps(root, self.RULES), [])

    def test_a_name_git_would_quote_is_checked(self):
        # Without -z, git quotes such names and the file would not be found.
        root = self.repo({"src/café.rs": self.SRC})
        self.assertEqual(self.gaps(root, None), ["src/café.rs"])
        self.assertEqual(self.gaps(root, self.RULES), [])

    def test_a_name_that_is_not_utf8_is_checked(self):
        # Verifier, 2026-10-11: such a name crashed `fix-lock on` (exit 1,
        # traceback) after the lock was written.
        root = self.repo({})
        raw = b"src/caf\xe9.rs"
        try:
            os.makedirs(os.path.join(os.fsencode(root), b"src"))
            with open(os.path.join(os.fsencode(root), raw), "wb") as f:
                f.write(self.SRC.encode())
        except OSError as e:  # macOS (APFS) refuses names that are not UTF-8
            self.skipTest("this filesystem refuses a name that is not UTF-8: %s" % e)
        subprocess.run([b"git", b"-C", os.fsencode(root), b"add", b"--", raw], check=True, env=guard.git_env())
        self.assertEqual(self.gaps(root, None), [os.fsdecode(raw)])
        self.assertEqual(self.gaps(root, self.RULES), [])
        rc, out, err = self.on(root, None)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(root, guard.LOCK_REL)))
        self.assertIn("NOT read-only", err)

    def test_untracked_files_do_not_count(self):
        root = self.repo({"src/plain.rs": self.PLAIN}, untracked={"scratch/probe.rs": self.SRC})
        self.assertEqual(self.gaps(root, None), [])

    def test_a_file_that_cannot_be_read_counts(self):
        root = self.repo({"src/latin1.rs": b"// caf\xe9\npub fn f() {}\n"})
        self.assertEqual(self.gaps(root, self.RULES), ["src/latin1.rs"])

    def test_git_failure_is_an_error_not_nothing_found(self):
        root = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        with open(os.path.join(root, "lib.rs"), "w") as f:
            f.write(self.SRC)
        # Not a repository, even when TMPDIR sits inside one.
        with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": os.path.dirname(root)}):
            with self.assertRaises(OSError):
                guard.uncovered_inline_tests(root, self.cfg(None))

    def test_a_git_hook_environment_does_not_redirect_the_listing(self):
        # A git hook exports GIT_DIR and GIT_INDEX_FILE; `git -C root` would
        # then list another repository's files.
        root = self.repo({"src/lib.rs": self.SRC})
        other = self.repo({"README.md": "x\n"})
        with mock.patch.dict(os.environ, {"GIT_DIR": os.path.join(other, ".git"), "GIT_WORK_TREE": other,
                                          "GIT_INDEX_FILE": os.path.join(other, ".git", "index")}):
            self.assertEqual(self.gaps(root, None), ["src/lib.rs"])

    def on(self, root: str, rules: list | None) -> tuple:
        """`fix-lock on` with this config: (exit code, stdout, stderr)."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "guard-config.json")
        with open(path, "w") as f:
            json.dump(self.cfg(rules), f)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = guard.fix_lock_cli(["on", "docs/build-records/x.md"], root, path)
        return rc, out.getvalue(), err.getvalue()

    def test_fix_lock_on_says_what_it_covers(self):
        root = self.repo({"src/plain.rs": self.PLAIN})
        rc, out, err = self.on(root, None)
        self.assertEqual(rc, 0)
        self.assertIn("test files and baselines are now read-only", out)
        self.assertNotIn("inline tests", out + err)
        rc, out, err = self.on(root, [])
        self.assertEqual(rc, 0)
        self.assertIn("test files and baselines are now read-only", out)
        rc, out, err = self.on(root, self.RULES)
        self.assertEqual(rc, 0)
        self.assertIn("test files, inline tests and baselines are now read-only", out)
        self.assertEqual(err, "")

    def test_fix_lock_on_names_inline_tests_it_does_not_cover(self):
        # Owner, 2026-10-11: engage, say so and name them (not refuse).
        root = self.repo({"src/lib.rs": self.SRC, "src/plain.rs": self.PLAIN})
        rc, out, err = self.on(root, None)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(root, guard.LOCK_REL)))
        self.assertIn("test files and baselines are now read-only", out)
        self.assertIn("NOT read-only", err)
        self.assertIn("src/lib.rs", err)
        self.assertNotIn("src/plain.rs", err)
        rc, out, err = self.on(root, [dict(self.RULES[0], glob="crates/*.rs")])
        self.assertEqual(rc, 0)
        self.assertIn("NOT read-only", err)
        self.assertIn("src/lib.rs", err)

    def test_a_long_gap_list_is_cut_but_counted(self):
        root = self.repo({"src/m%02d.rs" % i: self.SRC for i in range(14)})
        rc, out, err = self.on(root, None)
        self.assertEqual(rc, 0)
        self.assertIn("14 tracked files", err)
        self.assertIn("src/m09.rs", err)
        self.assertNotIn("src/m10.rs", err)
        self.assertIn("and 4 more", err)

    def test_fix_lock_on_says_when_it_cannot_check(self):
        root = self.repo({})
        with mock.patch.object(guard, "uncovered_inline_tests", side_effect=OSError("git is missing")):
            rc, out, err = self.on(root, self.RULES)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(root, guard.LOCK_REL)))
        self.assertIn("could not check", err)
        self.assertIn("git is missing", err)

    # The two layouts of 2026-10-11 (owner's choices 1(a) and 2(a)).
    DECLARES = "pub fn f() {}\n\n#[cfg(test)]\nmod tests;\n"
    TESTS_ONLY = "use super::*;\n\n#[test]\nfn t() {\n    f();\n}\n"

    def test_a_file_that_starts_cfg_test_needs_a_rule(self):
        root = self.repo({"src/inner.rs": InlineTests.INNER,
                          "src/not.rs": "#![cfg(not(test))]\npub fn f() {}\n"})
        self.assertEqual(self.gaps(root, None), ["src/inner.rs"])
        self.assertEqual(self.gaps(root, InlineTests.before_inner()["inline_tests"]), ["src/inner.rs"])
        self.assertEqual(self.gaps(root, self.RULES), [])

    def test_a_test_module_file_needs_a_rule(self):
        root = self.repo({"src/lib.rs": self.DECLARES, "src/tests.rs": self.TESTS_ONLY})
        self.assertEqual(self.gaps(root, None), ["src/lib.rs", "src/tests.rs"])
        self.assertEqual(self.gaps(root, self.RULES), [])
        # A rule that names the parent only: a shell write to the module would pass.
        self.assertEqual(self.gaps(root, [dict(self.RULES[0], glob="lib.rs")]), ["src/tests.rs"])
        # A rule that does not recognise the declaration.
        self.assertEqual(self.gaps(root, [dict(self.RULES[0], starts_at=r"^#\[cfg\(test\)\]\nmod tests \{")]),
                         ["src/lib.rs", "src/tests.rs"])

    def test_a_test_module_inside_a_test_module(self):
        root = self.repo({"src/lib.rs": self.DECLARES, "src/tests.rs": "mod fixtures;\n",
                          "src/tests/fixtures.rs": "pub const X: u8 = 1;\n"})
        self.assertEqual(self.gaps(root, None), ["src/lib.rs", "src/tests.rs", "src/tests/fixtures.rs"])
        self.assertEqual(self.gaps(root, self.RULES), [])
        self.assertEqual(self.gaps(root, [dict(self.RULES[0], glob="[lt]*.rs")]), ["src/tests/fixtures.rs"])

    def test_a_test_module_the_lock_cannot_follow_is_named(self):
        # rustc follows a #[path] out of the declaring file's folder; the lock
        # looks only in the module's own folder and those above it.
        root = self.repo({"src/a/foo.rs": 'pub fn f() {}\n\n#[cfg(test)]\n#[path = "../b/t.rs"]\nmod t;\n',
                          "src/b/t.rs": self.TESTS_ONLY})
        self.assertEqual(self.gaps(root, self.RULES), ["src/b/t.rs"])

    def test_a_test_module_with_no_file_is_named(self):
        root = self.repo({"src/lib.rs": self.DECLARES})
        self.assertEqual(self.gaps(root, self.RULES), ["src/lib.rs"])

    def test_a_crafted_file_cannot_stall_the_tripwire(self):
        # Verifier round 2, M9: one tracked file of `#` and spaces made the
        # tripwire take 9 s (its marker took time growing with the square of
        # a run of spaces).
        import time
        root = self.repo({"src/lib.rs": self.DECLARES, "src/tests.rs": self.TESTS_ONLY,
                          "zz.rs": "mod x; #" + " " * 120000 + "\n#" + " " * 120000 + "\n"})
        t0 = time.time()
        self.assertEqual(self.gaps(root, self.RULES), [])
        self.assertLess(time.time() - t0, 4.0)

    def test_a_production_module_is_not_named(self):
        root = self.repo({"src/lib.rs": "#[cfg(not(test))]\npub mod plain;\n\n#[cfg(test)]\nmod tests;\n",
                          "src/plain.rs": self.PLAIN, "src/tests.rs": self.TESTS_ONLY})
        self.assertEqual(self.gaps(root, self.RULES), [])
        self.assertEqual(self.gaps(root, None), ["src/lib.rs", "src/tests.rs"])

    def test_a_test_module_the_check_cannot_read_is_named(self):
        root = self.repo({"src/lib.rs": self.DECLARES, "src/tests.rs": self.TESTS_ONLY})
        with mock.patch.object(guard, "test_module_parent", side_effect=OSError("a folder cannot be listed")):
            self.assertEqual(self.gaps(root, self.RULES), ["src/tests.rs"])

    def test_an_untracked_test_module_does_not_count(self):
        root = self.repo({"src/lib.rs": self.DECLARES}, untracked={"src/tests.rs": self.TESTS_ONLY})
        self.assertEqual(self.gaps(root, self.RULES), [])
        self.assertEqual(self.gaps(root, None), ["src/lib.rs"])

    def test_fix_lock_on_names_a_test_module_it_does_not_cover(self):
        root = self.repo({"src/lib.rs": self.DECLARES, "src/tests.rs": self.TESTS_ONLY})
        rc, out, err = self.on(root, [dict(self.RULES[0], glob="lib.rs")])
        self.assertEqual(rc, 0)
        self.assertIn("NOT read-only", err)
        self.assertIn("test module", err)
        self.assertIn("src/tests.rs", err)
        self.assertNotIn("src/lib.rs", err)


class FailureModes(unittest.TestCase):
    def test_bad_config_asks(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write('{"secret_globs": []}')
        try:
            out = guard.run_hook(json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x"}}), f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("NOT being checked", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_garbage_stdin_asks(self):
        out = guard.run_hook("not json")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_allow_is_silent(self):
        self.assertIsNone(guard.run_hook(json.dumps({"tool_name": "Read", "tool_input": {"file_path": "README.md"},
                                                      "cwd": guard.ROOT})))

    def test_real_process_contract(self):
        """End to end through the interpreter, the way Claude Code invokes it."""
        event = {"tool_name": "Read", "tool_input": {"file_path": ".env"}, "cwd": guard.ROOT}
        proc = subprocess.run([sys.executable, guard.__file__], input=json.dumps(event),
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_fix_lock_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            # An explicit config without preflight: the repo's own may carry
            # checks that only run in the real repo root.
            cfg = self._cfg_with(root, None)
            self.assertEqual(guard.fix_lock_cli(["on", "docs/build-records/x.md"], root, cfg), 0)
            lock = os.path.join(root, guard.LOCK_REL)
            with open(lock) as f:
                self.assertEqual(json.load(f)["record"], "docs/build-records/x.md")
            self.assertEqual(guard.fix_lock_cli(["off"], root), 0)
            self.assertFalse(os.path.exists(lock))
            self.assertEqual(guard.fix_lock_cli(["bogus"], root), 2)

    # Lesson gate (2026-09-25): twice a ratchet breach was found only AFTER the
    # lock was engaged, and fixing the test then cost the owner a release. A
    # repo can name checks that must pass before the lock may engage.
    def _cfg_with(self, root: str, preflight) -> str:
        cfg = json.loads(json.dumps(CFG))
        cfg.pop("fix_lock_preflight", None)
        if preflight is not None:
            cfg["fix_lock_preflight"] = preflight
        path = os.path.join(root, "guard-config.json")
        with open(path, "w") as f:
            json.dump(cfg, f)
        return path

    def test_fix_lock_preflight_failing_refuses(self):
        with tempfile.TemporaryDirectory() as root:
            cfg = self._cfg_with(root, [[sys.executable, "-c", "import sys; sys.exit(3)"]])
            self.assertEqual(guard.fix_lock_cli(["on", "docs/build-records/x.md"], root, cfg), 1)
            self.assertFalse(os.path.exists(os.path.join(root, guard.LOCK_REL)))

    def test_fix_lock_preflight_runs_in_repo_root_and_passes(self):
        with tempfile.TemporaryDirectory() as root:
            marker = os.path.join(root, "ran-here")
            cfg = self._cfg_with(root, [[sys.executable, "-c", "open('ran-here','w').close()"]])
            self.assertEqual(guard.fix_lock_cli(["on", "docs/build-records/x.md"], root, cfg), 0)
            self.assertTrue(os.path.exists(marker))
            self.assertTrue(os.path.exists(os.path.join(root, guard.LOCK_REL)))

    def test_fix_lock_without_preflight_is_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            cfg = self._cfg_with(root, None)
            self.assertEqual(guard.fix_lock_cli(["on", "docs/build-records/x.md"], root, cfg), 0)

    # Owner, 2026-09-26: a release may be free, but never invisible.
    def test_every_release_is_logged(self):
        with tempfile.TemporaryDirectory() as root:
            cfg = self._cfg_with(root, None)
            guard.fix_lock_cli(["on", "docs/build-records/a.md"], root, cfg)
            guard.fix_lock_cli(["off"], root, cfg)
            guard.fix_lock_cli(["on", "docs/build-records/b.md"], root, cfg)
            guard.fix_lock_cli(["off"], root, cfg)
            with open(os.path.join(root, guard.LOCK_LOG_REL)) as f:
                rows = [json.loads(line) for line in f]
            self.assertEqual([r["record"] for r in rows], ["docs/build-records/a.md", "docs/build-records/b.md"])
            self.assertTrue(all(r.get("engaged_since") and r.get("released_at") for r in rows))

    def test_release_policy_must_be_a_boolean(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._cfg_with(root, None)
            with open(path) as f:
                cfg = json.load(f)
            cfg["fix_lock_release_needs_owner"] = "no"
            with open(path, "w") as f:
                json.dump(cfg, f)
            with self.assertRaises(ValueError):
                guard.load_config(path)

    def test_fix_lock_malformed_preflight_refuses(self):
        with tempfile.TemporaryDirectory() as root:
            cfg = self._cfg_with(root, "node scripts/quality-ratchet.mjs")  # a string, not argv lists
            self.assertNotEqual(guard.fix_lock_cli(["on", "docs/build-records/x.md"], root, cfg), 0)
            self.assertFalse(os.path.exists(os.path.join(root, guard.LOCK_REL)))
            with self.assertRaises(ValueError):
                guard.load_config(cfg)


class PerSessionLock(unittest.TestCase):
    """Owner, 2026-10-03: "Let's not share fix-lock." Two sessions worked one
    repo; one session's lock blocked the other's test writes, `on` overwrote
    another record's lock and `off` released anyone's. A lock now binds only
    the session that took it; the old global file (taken outside any session,
    e.g. from the owner's terminal) still binds everyone."""

    TEST = "tests/test_something.py"

    def _cfg(self, root: str) -> str:
        cfg = json.loads(json.dumps(CFG))
        cfg.pop("fix_lock_preflight", None)
        path = os.path.join(root, "guard-config.json")
        with open(path, "w") as f:
            json.dump(cfg, f)
        return path

    def _edit(self, root: str, session) -> str:
        event = {"tool_name": "Edit", "tool_input": {"file_path": self.TEST}, "cwd": root}
        if session is not None:
            event["session_id"] = session
        return guard.decide(event, dict(CFG, profile="stable"), root, branch_fn=lambda _c: "feature/x")[0]

    def test_a_lock_binds_only_its_own_session(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(guard.fix_lock_cli(["on", "docs/build-records/a.md"], root, self._cfg(root),
                                                session="sess-A"), 0)
            self.assertFalse(os.path.exists(os.path.join(root, guard.LOCK_REL)))
            self.assertEqual(self._edit(root, "sess-A"), "deny")
            self.assertEqual(self._edit(root, "sess-B"), "allow")
            self.assertEqual(self._edit(root, None), "allow")

    def test_the_global_lock_still_binds_everyone(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(guard.fix_lock_cli(["on", "docs/build-records/owner.md"], root, self._cfg(root)), 0)
            for s in ("sess-A", "sess-B", None):
                self.assertEqual(self._edit(root, s), "deny")

    def test_on_never_touches_another_sessions_lock_and_off_only_releases_your_own(self):
        with tempfile.TemporaryDirectory() as root:
            cfg = self._cfg(root)
            guard.fix_lock_cli(["on", "docs/build-records/a.md"], root, cfg, session="sess-A")
            guard.fix_lock_cli(["on", "docs/build-records/b.md"], root, cfg, session="sess-B")
            guard.fix_lock_cli(["on", "docs/build-records/owner.md"], root, cfg)  # global
            with open(guard.session_lock_path(root, "sess-A")) as f:
                self.assertEqual(json.load(f)["record"], "docs/build-records/a.md")
            self.assertEqual(guard.fix_lock_cli(["off"], root, cfg, session="sess-B"), 0)
            self.assertFalse(os.path.exists(guard.session_lock_path(root, "sess-B")))
            self.assertTrue(os.path.exists(guard.session_lock_path(root, "sess-A")))
            self.assertTrue(os.path.exists(os.path.join(root, guard.LOCK_REL)))
            # releasing someone else's is explicit
            self.assertEqual(guard.fix_lock_cli(["off", "--session", "sess-A"], root, cfg, session="sess-B"), 0)
            self.assertFalse(os.path.exists(guard.session_lock_path(root, "sess-A")))
            self.assertEqual(guard.fix_lock_cli(["off", "--global"], root, cfg, session="sess-B"), 0)
            self.assertFalse(os.path.exists(os.path.join(root, guard.LOCK_REL)))

    def test_every_release_is_logged_with_its_session(self):
        with tempfile.TemporaryDirectory() as root:
            cfg = self._cfg(root)
            guard.fix_lock_cli(["on", "docs/build-records/a.md"], root, cfg, session="sess-A")
            guard.fix_lock_cli(["off"], root, cfg, session="sess-A")
            with open(os.path.join(root, guard.LOCK_LOG_REL)) as f:
                entry = json.loads(f.read().splitlines()[-1])
            self.assertEqual((entry["record"], entry["session"]), ("docs/build-records/a.md", "sess-A"))
            self.assertIn("released_at", entry)

    def test_status_lists_every_lock_and_marks_yours(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as root:
            cfg = self._cfg(root)
            guard.fix_lock_cli(["on", "docs/build-records/a.md"], root, cfg, session="sess-A")
            guard.fix_lock_cli(["on", "docs/build-records/b.md"], root, cfg, session="sess-B")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(guard.fix_lock_cli(["status"], root, cfg, session="sess-A"), 0)
            out = buf.getvalue()
            self.assertIn("docs/build-records/a.md", out)
            self.assertIn("docs/build-records/b.md", out)
            self.assertIn("this session", out)

    def test_a_session_id_cannot_escape_the_lock_directory(self):
        with tempfile.TemporaryDirectory() as root:
            path = guard.session_lock_path(root, "../../etc/x")
            self.assertTrue(os.path.realpath(path).startswith(os.path.realpath(
                os.path.join(root, guard.LOCK_DIR_REL)) + os.sep))

    def test_releasing_someone_elses_lock_always_asks(self):
        for cmd in ("python3 .claude/hooks/guard.py fix-lock off --session abc",
                    "python3 .claude/hooks/guard.py fix-lock off --global"):
            for profile in ("stable", "development"):
                self.assertEqual(verdict("Bash", {"command": cmd}, profile=profile), "ask")

    def test_lock_files_are_guarded_like_the_global_one(self):
        self.assertEqual(verdict("Bash", {"command": "rm -f .claude/state/fix-locks/sess-A.json"}), "ask")
        self.assertEqual(verdict("Edit", {"file_path": ".claude/state/fix-locks/sess-A.json"}), "ask")

    # The 2026-10-03 hole: a python3 heredoc with a relative path wrote a test
    # file while a lock was engaged — only shell write targets were checked.
    def test_inline_code_cannot_write_a_locked_test(self):
        writes = [
            "python3 - <<'EOF'\nopen('tests/test_something.py', 'a').write('x')\nEOF",
            "python3 -c \"open('tests/test_something.py','w').write('')\"",
            "node -e \"require('fs').writeFileSync('tests/test_something.py', '')\"",
            "python3 <<EOF\nfrom pathlib import Path\nPath('tests/test_something.py').write_text('')\nEOF",
            # Live drill, 2026-10-03: the interpreter was not the first word.
            "cd . && python3 - <<'EOF'\nopen('tests/test_something.py', 'w').write('// drill')\nEOF",
            "echo go | python3 -c \"open('tests/test_something.py','w')\"",
        ]
        for cmd in writes:
            self.assertEqual({"cmd": cmd, "v": verdict("Bash", {"command": cmd}, lock=True)},
                             {"cmd": cmd, "v": "deny"})
            self.assertEqual(verdict("Bash", {"command": cmd}, lock=False), "allow")

    def test_running_or_reading_a_test_is_still_fine_while_locked(self):
        for cmd in ("python3 -m pytest tests/test_something.py",
                    "node --test tests/test_something.py",
                    "python3 -c \"print(open('tests/test_something.py').read())\"",
                    # False positive seen 2026-10-03: inline code writes a SOURCE
                    # file, a later command runs the tests by path.
                    "python3 - <<'EOF'\nopen('src/app.py', 'w').write('x')\nEOF\npython3 -m pytest tests/test_something.py",
                    "cd . && python3 - <<'EOF'\nopen('src/app.py','w')\nEOF\nnpx jest tests/test_something.py"):
            self.assertEqual({"cmd": cmd, "v": verdict("Bash", {"command": cmd}, lock=True)},
                             {"cmd": cmd, "v": "allow"})


class InlineWriteTargets(unittest.TestCase):
    """False positive (2026-10-03/04, three times): inline code that writes a
    NON-test file was denied because its text mentioned a test path. Now the
    tripwire looks at what the code writes: resolvable targets that are not
    tests pass; an unresolvable target keeps the strict rule."""

    def _v(self, cmd: str) -> str:
        return verdict("Bash", {"command": cmd}, lock=True)

    def test_a_resolvable_non_test_target_passes_even_if_the_text_names_a_test(self):
        for cmd in (
            "python3 - <<'EOF'\np='docs/build-records/x.md'\nopen(p,'w').write('see tests/test_something.py')\nEOF",
            "python3 - <<'EOF'\nopen('src/app.py','w').write('# tests/test_something.py')\nEOF",
            "node -e \"require('fs').writeFileSync('src/app.js', '// tests/test_something.py')\"",
            "python3 - <<'EOF'\nfrom pathlib import Path\nPath('docs/a.md').write_text('tests/test_something.py')\nEOF",
        ):
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "allow"})

    def test_the_2026_10_03_hole_is_still_denied(self):
        for cmd in (
            "python3 - <<'EOF'\np='tests/test_something.py'\ns=open(p).read()\nopen(p,'w').write(s+'x')\nEOF",
            "python3 - <<'EOF'\nconst = 1\nT = \"tests/test_something.py\"\nopen(T, 'a').write('x')\nEOF",
            "node -e \"const f='tests/test_something.py'; require('fs').writeFileSync(f, '')\"",
        ):
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_an_unresolvable_target_keeps_the_strict_rule(self):
        for cmd in (
            "python3 - \"$f\" <<'EOF'\nimport sys\nopen(sys.argv[1],'w').write('tests/test_something.py')\nEOF",
            "python3 - <<'EOF'\nimport os\nopen(os.path.join('tests','x.py'),'w').write('tests/test_something.py')\nEOF",
        ):
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "deny"})


class SecretSearches(unittest.TestCase):
    """Owner, 2026-10-04: "should not be allowed to search or look into .env
    without permission." A recursive search over a tree holding a secret file
    read it without asking (`grep -r X .` names no secret file), while
    `grep -r --exclude='*.env' X .` — which would NOT read it — was denied."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        os.makedirs(os.path.join(self.root, "src"))
        os.makedirs(os.path.join(self.root, "app", "deep"))
        for rel in ("src/a.py", "app/deep/b.py"):
            with open(os.path.join(self.root, rel), "w") as f:
                f.write("x = 1\n")
        with open(os.path.join(self.root, "app", "deep", ".env"), "w") as f:
            f.write("SECRET=1\n")

    def tearDown(self):
        self._tmp.cleanup()

    def _v(self, cmd: str, profile: str = "stable") -> str:
        event = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": self.root}
        return guard.decide(event, dict(CFG, profile=profile), self.root, lock_present=False,
                            branch_fn=lambda _c: "feature/x")[0]

    # rg and ag skip hidden files unless told (--hidden, -uu); .env is hidden.
    def test_a_recursive_search_over_a_tree_with_a_secret_asks_in_every_profile(self):
        for cmd in ("grep -r x .", "grep -rn x", "grep -Rl x app", "egrep -r 'x|y' .",
                    "grep --recursive x .", "grep -d recurse x .", "rg --hidden x", "rg -uu x app",
                    "ag --hidden x .", "find . -type f -exec grep -l x {} +",
                    "cd app && grep -r x ."):
            for profile in ("stable", "development"):
                self.assertEqual({"cmd": cmd, "p": profile, "v": self._v(cmd, profile)},
                                 {"cmd": cmd, "p": profile, "v": "ask"})

    def test_searches_that_cannot_reach_a_secret_pass(self):
        for cmd in ("grep -r x src", "grep x app/deep/b.py", "git grep x",
                    "grep -r --exclude='*.env' x .", "grep -r --exclude=.env x .",
                    "grep -r --exclude-dir=deep x .", "rg -g '!*.env' x", "rg --glob '!.env' x app",
                    "find src -name '*.py' -exec grep -l x {} +"):
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "allow"})

    def test_excluding_secrets_is_never_itself_refused(self):
        cmd = "grep -rn --exclude='*.env' --exclude='*.key' x src"
        self.assertEqual(self._v(cmd), "allow")

    def test_a_tree_too_big_to_walk_counts_as_holding_secrets(self):
        old = guard.SECRET_WALK_BUDGET
        guard.SECRET_WALK_BUDGET = 0  # src/ holds one file: any walk is "too big"
        try:
            self.assertEqual(self._v("grep -r x src"), "ask")
        finally:
            guard.SECRET_WALK_BUDGET = old


class GuardRound2(SecretSearches):
    """Verifier round 1 of the 2026-10-04 guard record: regressions against the
    previous guard (it denied these) plus old gaps. Every row was shown to get
    through on a temp root holding app/deep/.env."""

    def _lock(self, cmd: str) -> str:
        return verdict("Bash", {"command": cmd}, lock=True)

    def _at(self, cmd: str, sub: str) -> str:
        event = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": os.path.join(self.root, sub)}
        return guard.decide(event, dict(CFG, profile="stable"), self.root, lock_present=False,
                            branch_fn=lambda _c: "feature/x")[0]

    def test_regressions_reading_a_secret(self):
        self.assertEqual(self._v("grep -T DUMMY app/deep/.env"), "deny")  # -T takes no value
        for cmd in ("grep -r --exclude='*.env' --include='.env' x .",   # last matching filter wins
                    "grep -r --exclude=.env --include='*' x ."):
            # the previous guard denies these; the new guard may not loosen that (round 6)
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_regressions_writing_a_locked_test(self):
        for cmd in ('python3 <<< "open(\'tests/x.py\',\'w\')"',
                    "python3 -c \"open(mode='w', file='tests/x.py')\"",
                    "python3 -c \"open('a' and 'tests/x.py','w')\"",
                    "python3 -c \"open('a.md' if 0 else 'tests/x.py','w')\"",
                    "python3 - <<'EOF'\np='a.md'\nfor p in ['tests/x.py']: open(p,'w')\nEOF",
                    "python3 - <<'EOF'\np='a.md'\np, q = 'tests/x.py', 1\nopen(p,'w')\nEOF",
                    "python3 - <<'EOF'\np='a.md'\n(p := 'tests/x.py')\nopen(p,'w')\nEOF",
                    "python3 - <<'EOF'\np='a.md'\nglobals()['p']='tests/x.py'\nopen(p,'w')\nEOF"):
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_searches_that_slipped_past(self):
        os.symlink(os.path.join(self.root, "app", "deep"), os.path.join(self.root, "lnk"))
        for cmd in ("timeout 5 grep -r x .", "nice -n 5 grep -r x .", "env -i grep -r x .",
                    "stdbuf -oL grep -r x .", "eval \"grep -r x .\"", "busybox grep -r x .",
                    "rgrep x .", "grep --recu x .", "grep --directories=rec x .", "grep -d rec x .",
                    "grep -rC2 x .", "grep -rm1 x .", "grep -r --color x app", "grep -r -T x app",
                    "rg --hidden -g '!.env' -g '*' x", "rg --hidden --iglob '*.ENV' x",
                    "find -L app -type f -exec cat {} +", "find . -type f -exec sh -c 'cat \"$1\"' _ {} \\;",
                    "find . -type f -exec perl -ne print {} +", "grep -R x lnk",
                    "grep -r x $DIR", "grep -r x \"$(echo app)\"",
                    "git grep --untracked x", "git grep --no-index x .", "grep x app/deep"):
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "ask"})
        self.assertEqual(self._at("cd ../app && grep -r x .", "src"), "ask")

    def test_inline_writes_that_slipped_past(self):
        for cmd in ("perl -e 'open(my $f, \">\", \"tests/x.py\")'",
                    "python3 -Bc \"open('tests/x.py','w')\"",
                    "node -pe \"require('fs').writeFileSync('tests/x.py','')\"",
                    "python3 - <<\\EOF\nopen('tests/x.py','w')\nEOF",
                    "cat <<'EOF' | python3\nopen('tests/x.py','w')\nEOF",
                    "echo \"open('tests/x.py','w')\" | python3",
                    "bash -c \"python3 -c \\\"open('tests/x.py','w')\\\"\"",
                    "python3 - <<'EOF'\nd='tests'\nopen(f'{d}/x.py','w')\nEOF",
                    "python3 - <<'EOF'\nimport os\nos.replace('a.py','tests/x.py')\nEOF",
                    "python3 - <<'EOF'\nfrom pathlib import Path\nPath('tests/x.py').touch()\nEOF",
                    "node -e \"require('fs').renameSync('a','tests/x.py')\"",
                    "node -e \"require('fs').cpSync('a','tests/x.py')\"",
                    "cat <<EOF\nhello\nEOF\npython3 - <<EOF\nopen('tests/x.py','w')\nEOF"):
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})

    # Verifier round 2: regressions again (HEAD denied these), the strict-unless-
    # straight-line rule for inline code, more bypasses, and two false positives.
    def test_round2_regressions(self):
        for cmd in ("rg --ignore-file=app/deep/.env x src",          # reads the file (errors print lines)
                    "grep -r --exclude-from=app/deep/.env x src",
                    "grep --exclude-from=app/deep/.env x src/a.py"):
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "deny"})
        for cmd in ("python3 -c \"open(**{'file':'tests/x.py','mode':'w'}).write('')\"",
                    "python3 - <<'EOF'\np='a.md'\ndef f(p):\n    open(p,'w')\nf('tests/x.py')\nEOF",
                    "python3 - <<'EOF'\np='a.md'\nmatch 'tests/x.py':\n    case p:\n        open(p,'w')\nEOF",
                    "python3 - <<'EOF'\np='a.md'\ng=lambda p: open(p,'w')\ng('tests/x.py')\nEOF",
                    "node -e \"const p='a.md'; ['tests/x.js'].forEach(p => require('fs').writeFileSync(p,''))\"",
                    "node -e \"let p='a.md'; for (p of ['tests/x.js']) require('fs').writeFileSync(p,'')\"",
                    "node -e \"require('fs').openSync('tests/x.js','w')\"",
                    "python3 -c \"import subprocess; subprocess.run(['cp','a','tests/x.py'])\"",
                    "python3 - <<'EOF'\nopen('a.md','w')\n  EOF\nopen('tests/x.py','w')\nEOF",
                    "cd tests && python3 -c \"open('x.py','w')\"",
                    "npx tsx -e \"require('fs').writeFileSync('tests/x.js','')\""):
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_round2_bypasses(self):
        for cmd in ("rg --hidden -g '**/.env' x", "rg --hidden -g '{.env,zz}' x", "rg -nuu x", "rg -n. x",
                    "grep -r x {app,zz}", "cd -- app && grep -r x .", "cd -P app && grep -r x .",
                    "pushd app && grep -r x .", "( cd app && grep -r x . )",
                    "git -C app grep --untracked x", "git --no-pager grep --no-index x .",
                    "setsid grep -r x .", "watch -n1 grep -r x .", "su -c 'grep -r x .'",
                    "find . -type d -name deep -exec grep -r x {} +"):
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "ask"})
        for cmd in ("cat app/deep/.e*", "grep x app/deep/.*",
                    "find . -name a.py -exec sh -c 'cat app/deep/.env' \\;"):
            self.assertNotEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "allow"})

    def test_round2_false_positives(self):
        # the everyday record edit: read a .md, replace text, write it back
        cmd = ("python3 - <<'EOF'\np='docs/build-records/r.md'\nt=open(p).read()\n"
               "open(p,'w').write(t.replace('a','tests/test_something.py'))\nEOF")
        self.assertEqual(self._lock(cmd), "allow")
        # Verifier round 3: treating heredoc bodies as data hid money moves run
        # by ssh / docker exec / subprocess — bodies stay commands, as before.
        self.assertEqual(self._v("cat > notes.md <<'EOF'\ngrep x app/deep/.env\nEOF"), "deny")
        # but a heredoc fed to a shell IS commands
        self.assertEqual(self._v("bash <<'EOF'\ncat app/deep/.env\nEOF"), "deny")

    # Verifier round 3 (19 regressions). Rule since: never drop a check the
    # previous guard made; only the inline false positive and secret-excluding
    # searches got more lenient.
    def test_round3_money_and_secrets_in_heredocs_still_ask(self):
        # every repo has secrets; not every repo's examples include a money move
        must = ["cat .env"] + [ex["input"]["command"] for ex in CFG["examples"]
                               if ex["tool"] == "Bash" and ex.get("expect_dev") in ("ask", "deny")]
        for c in must:
            forms = ["docker exec -i box sh <<'EOF'\n%s\nEOF" % c,
                     "ssh node2 <<'EOF'\n%s\nEOF" % c,
                     "x=$(cat <<'EOF'\n%s\nEOF\n); eval \"$x\"" % c,
                     "cat > /tmp/run.sh <<'EOF'\n%s\nEOF\nbash /tmp/run.sh" % c]
            if c != "cat .env":  # a read inside a code string is a known limit (old guard too)
                forms.append("python3 - <<'EOF'\nimport subprocess\nsubprocess.run(%r, shell=True)\nEOF" % c)
            for wrapped in forms:
                for profile in ("stable", "development"):
                    v = verdict("Bash", {"command": wrapped}, profile=profile)
                    self.assertNotEqual({"cmd": wrapped, "p": profile, "v": v},
                                        {"cmd": wrapped, "p": profile, "v": "allow"})
        for cmd in ("tee >(sh) <<'EOF'\ncat app/deep/.env\nEOF", "ssh localhost <<'EOF'\ncat app/deep/.env\nEOF",
                    "uv run --env-file app/deep/.env python3 x.py", "uv run --env-file=app/deep/.env python3 x.py"):
            self.assertNotEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "allow"})

    def test_round3_inline_tricks_are_strict(self):
        for cmd in ("python3 - <<'EOF'\np = 'a.md'\n# `\ndef f(p): open(p, 'w').write('x')\n# `\nf('tests/x.py')\nEOF",
                    "node -e \"let p='a.md'; // `\nfunction f(p){require('fs').writeFileSync(p,'')}\n// `\nf('tests/x.js')\"",
                    "python3 - <<'EOF'\np = 'a.md'\nx = p = 'tests/x.py'\nopen(p,'w')\nEOF",
                    "python3 - <<'EOF'\nimport sys\np = 'a.md'\nsys.modules[__name__].p = 'tests/x.py'\nopen(p,'w')\nEOF",
                    "node -e \"var p='a.md'; globalThis.p = 'tests/x.js'; require('fs').writeFileSync(p,'')\"",
                    "python3 - <<'EOF'\np = 'a.md'\nｐ = 'tests/x.py'\nopen(p,'w')\nEOF",
                    "node -e \"var p='a.md'; \\u0070 = 'tests/x.js'; require('fs').writeFileSync(p,'')\""):
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})

    # Verifier round 4: a `cd` that may not take effect dropped checks on the
    # original paths, and the inline leniency trusted operations it did not know.
    def test_round4_cd_never_drops_a_check(self):
        for pre in ("cd nonexistent_zz; ", "cd docs || true; ", "cd docs && cd - && ",
                    "if false; then cd docs; fi; ", "cd \"$OLDPWD\"; ", "pushd docs && popd && "):
            cmd = pre + "echo '{}' > .claude/settings.local.json"
            self.assertEqual({"cmd": cmd, "v": verdict("Bash", {"command": cmd})}, {"cmd": cmd, "v": "ask"})
            cmd = pre + "echo x > tests/test_something.py"
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})
            cmd = pre + "python3 -c \"open('tests/test_something.py','w')\""
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_round4_inline_lenient_only_for_known_harmless_calls(self):
        md = "open('docs/r.md','w').write('see tests/test_x.py')\n"
        for extra in ("import os\ngetattr(os, 'remove')('tests/x.py')\n",
                      "p = 'docs/r.md'\nfrom helpers import p\nopen(p,'w')\n",
                      "import shutil\nshutil.rmtree('tests')\n", "import os\nos.rmdir('tests')\n",
                      "import os\nos.makedirs('tests/new')\n", "import os\nos.chmod('tests/x.py', 0)\n",
                      "import urllib.request\nurllib.request.urlretrieve('http://x', 'tests/x.py')\n"):
            cmd = "python3 - <<'EOF'\n" + md + extra + "EOF"
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})
        for extra in ("require('fs').rmSync('tests', {recursive: true})", "require('fs').mkdirSync('tests/n')",
                      "require('fs').linkSync('docs/r.md', 'tests/x.test.js')"):
            cmd = "node -e \"require('fs').writeFileSync('docs/r.md','see tests/x'); %s\"" % extra
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})
        # still lenient: the everyday record edit with ordinary helpers
        ok = ("python3 - <<'EOF'\nimport re, json\np = 'docs/build-records/r.md'\nt = open(p).read()\n"
              "t = re.sub('a', 'tests/test_something.py', t).strip()\nopen(p, 'w').write(t + '\\n')\nEOF")
        self.assertEqual(self._lock(ok), "allow")

    def test_round4_shared_gaps_closed(self):
        for cmd in ("(cat .env)", "x=$(cat .env)", "echo `cat .env`", "sh <<< 'cat .env'",
                    "echo 'cat .env' | sh"):
            self.assertEqual({"cmd": cmd, "v": verdict("Bash", {"command": cmd})}, {"cmd": cmd, "v": "deny"})
        for cmd in ("rm -rf tests", "mv tests /tmp/x", "git checkout -- tests"):
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})

    # Verifier round 5. Structural answer: the previous guard ships unchanged as
    # guard_base.py and its decision always counts; the new code only adds,
    # except two narrow, proven overrides (harmless inline code; a search
    # filter's value).
    def test_round5_the_previous_guard_always_counts(self):
        import guard_base  # noqa: F401  (must exist beside guard.py)
        real = guard.base_decide
        try:
            guard.base_decide = lambda *a, **k: ("deny", ["previous guard says no"])
            self.assertEqual(verdict("Bash", {"command": "ls"}), "deny")
        finally:
            guard.base_decide = real

    def test_round5_cd_segment_itself_is_checked(self):
        musts = [ex["input"]["command"] for ex in CFG["examples"]
                 if ex["tool"] == "Bash" and ex.get("expect_dev") in ("ask", "deny")]
        for c in musts:
            for form in ('cd "$(%s)"', "cd `%s`", 'pushd "$(%s)"'):
                cmd = form % c
                for profile in ("stable", "development"):
                    self.assertNotEqual({"cmd": cmd, "v": verdict("Bash", {"command": cmd}, profile=profile)},
                                        {"cmd": cmd, "v": "allow"})
        self.assertNotEqual(verdict("Bash", {"command": "cd . > .env"}), "allow")
        self.assertEqual(verdict("Bash", {"command": "cd . > .claude/settings.local.json"}), "ask")
        for cmd in ("cd . > tests/test_x.py", "pushd . > tests/test_x.py"):
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_round5_inline_arguments_aliases_and_second_calls(self):
        md = "open('docs/r.md','w').write('x')\n"
        for cmd in ("python3 - tests/test_x.py <<'EOF'\nimport sys\nopen(sys.argv[1],'w').write('x')\nEOF",
                    "node -e \"require('fs').writeFileSync(process.argv[1],'x')\" tests/x.test.js",
                    "python3 - <<'EOF'\n" + md + "read = open\nread('tests/test_x.py','w').write('x')\nEOF",
                    "python3 - <<'EOF'\n" + md + "strip = open\nstrip('tests/test_x.py','a')\nEOF",
                    "python3 - <<'EOF'\nfrom pathlib import Path\n" + md
                    + "write = Path('tests/test_x.py').write_text\nwrite('x')\nEOF",
                    "python3 - <<'EOF'\nfrom helpers import myopen\nmyopen('tests/test_x.py','w')\nEOF",
                    "python3 -c \"open('docs/r.md','w').write('x')\" && "
                    "python3 -c \"__import__('os').makedirs('tests/new')\"",
                    "node -e \"require('fs').writeFileSync('docs/r.md','x')\" && "
                    "node -e \"require('fs').mkdirSync('tests/newdir')\""):
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_round5_many_cds_and_searches_stay_fast(self):
        import time
        cds = " && ".join("cd /usr/share" for _ in range(10))
        cmd = cds + " && " + " && ".join("grep -r x ." for _ in range(8))
        t = time.time()
        self._v(cmd)
        self.assertLess(time.time() - t, 4.0)

    # Verifier round 6: the inline override lifted real test writes ($VAR
    # expansion, a `cd` the guard cannot follow), and nesting ran past the
    # hook's 10 s. The override now needs a command that is ONLY python/node
    # calls, with no `$` or backtick anywhere.
    def test_round6_inline_override_only_for_pure_interpreter_commands(self):
        for cmd in ("T=tes\"ts\"/test_x.py; python3 -c \"open('$T','w').write('see tests/test_x.py')\"",
                    "T=tests/test_x.py; python3 - <<EOF\nopen('$T','w').write('see tests/test_x.py')\nEOF",
                    "T=tests/x.test.js; node -e \"require('fs').writeFileSync('$T','see tests/x')\"",
                    "D=tests; cd $D && python3 -c \"open('helper.py','w').write('see tests/test_x.py')\"",
                    "cd $(echo tests) && python3 -c \"open('helper.py','w').write('see tests/test_x.py')\"",
                    "builtin cd tests && python3 -c \"open('helper.py','w').write('see tests/test_x.py')\"",
                    "eval cd tests && python3 -c \"open('helper.py','w').write('see tests/test_x.py')\"",
                    "g() { cd tests; }; g; python3 -c \"open('helper.py','w').write('see tests/test_x.py')\""):
            self.assertEqual({"cmd": cmd, "v": self._lock(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_round6_include_filters_name_the_file_read(self):
        for cmd in ("grep -r --include='.env' x .", "grep -r --exclude='*.env' --include='.env' x .",
                    "grep -r --exclude=.env --include='*' x ."):
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_round6_deep_nesting_stays_inside_the_hook_timeout(self):
        import shlex
        import time
        dirs = ["/usr/share", "/usr/lib", "/usr/include", "/usr/src", "/var/lib", "/usr/bin", "/etc", "/opt",
                "/usr/libexec", "/usr/local"]
        cds = "; ".join("cd " + d for d in dirs)  # ten different folders per level
        c = cds + "; cat ." + "env"  # verifier round 6's no-search case, with a secret read at the core
        for _ in range(5):
            c = cds + "; true; sh -c " + shlex.quote(c)
        t = time.time()
        v = self._v(c)
        self.assertLess(time.time() - t, 6.0)
        self.assertNotEqual(v, "allow")

    # Verifier round 7: after the new checks time out, NO override may lift
    # the previous guard's decision (override (2) still could).
    def test_round7_no_override_after_a_timeout(self):
        real_new, real_base = guard._decide_new, guard.base_decide

        def slow(*a, **k):
            raise guard._TooSlow()
        try:
            guard._decide_new = slow
            guard.base_decide = lambda *a, **k: ("deny", ["`grep` would print secret file *.env into the transcript"])
            self.assertEqual(self._v("grep -r --exclude='*.env' x src"), "deny")
        finally:
            guard._decide_new, guard.base_decide = real_new, real_base

    def test_false_positives_that_should_pass(self):
        for cmd in ("find . -name '*.md' -exec grep -l foo {} +",  # -name is a filter
                    "rg foo",                                      # rg skips hidden files (.env)
                    "rg foo app"):
            self.assertEqual({"cmd": cmd, "v": self._v(cmd)}, {"cmd": cmd, "v": "allow"})


if __name__ == "__main__":
    unittest.main()
