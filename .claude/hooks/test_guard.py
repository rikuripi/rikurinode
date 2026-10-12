"""Tests for guard.py — IDENTICAL in every full-tier repo, like guard.py.

Replays every example in this repo's guard-config.json, then the generic
cases every repo's policy must satisfy, then the failure modes (a broken
guard must ASK, never fail open).

Run: python3 -m unittest discover -s .claude/hooks -p 'test_*.py'
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

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
    # The rule rikurinode and AISecurity configure (test_marker_shapes pins it).
    RUST = dict(CFG, inline_tests=[{"glob": "*.rs", "starts_at":
                                    r"^[ \t\f\v\r​-‏⁠﻿]*#\s*\[\s*cfg\s*\(\s*(?:test|(?:any|all)\s*\((?:.*[(,]\s*)?(?<!not\()test(?=\s*[,)]).*\))\s*\)\s*\]",
                                    "guarded_lines": r"cfg(?:_attr)?\s*!?\s*\(.*\btest\b|macro_rules!\s*(?:assert\w*|debug_assert\w*|panic|unreachable|todo)\b",
                                    "attached_above": r"^[ \t\f\v\r​-‏⁠﻿]*(#\s*\[|//|/\*|\*)"}])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        os.makedirs(os.path.join(self.root, "src", "dir.rs"))
        for name, text in (("lib.rs", self.SRC), ("plain.rs", self.PLAIN), ("notes.md", self.SRC),
                           ("quoted.rs", self.QUOTED), ("support.rs", self.SUPPORT), ("doc.rs", self.DOC),
                           ("cr.rs", self.CR), ("blank.rs", "\n  \n"), ("bom.rs", "\ufeff\n"),
                           ("crlf.rs", self.CRLF), ("banner.rs", self.BANNER),
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
                             ('#[cfg(any(feature = "test-helpers", unix))]', False),
                             ("#[cfg(any(not(test), unix))]", False), ("#[cfg_attr(test, derive(Debug))]", False),
                             ("# [cfg(test)]", True), ("#[cfg (test)]", True), ("#[ cfg(test) ]", True),
                             ("\u200e#[cfg(test)]", True), ("#[cfg(not (test))]", False)):
            self.assertEqual(guard.inline_region("fn a() {}\n" + line + "\n", rx) is not None, marker, line)

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


class LineContinuation(unittest.TestCase):
    """A backslash before a newline continues the command: the shell reads one
    command, and so must the guard. Each line used to be judged alone, so
    `lncli \\⏎ sendcoins …` and `cat \\⏎ .env` got through (rikuripi/rikurinode,
    docs/build-records/2026-10-11-guard-line-continuation.md)."""

    SYN = dict(CFG, funds_patterns=[{"regex": r"\bmovemoney\s+--amt\b", "reason": "moves money", "always_ask": True},
                                    {"regex": r"\bpaynow\b.*--amt\b", "reason": "moves money", "always_ask": True}])

    def v(self, cmd: str, lock: bool = False) -> str:
        return verdict("Bash", {"command": cmd}, lock=lock, cfg=self.SYN)

    def test_the_lines_are_joined(self):
        seg = guard.split_segments
        self.assertEqual(seg("movemoney \\\n --amt 5"), ["movemoney  --amt 5"])
        self.assertEqual(seg("a \\\n b; c"), ["a  b", "c"])
        self.assertEqual(seg('echo "x \\\n y"; z'), ['echo "x  y"', "z"])  # inside double quotes too

    def test_what_the_shell_does_not_join(self):
        seg = guard.split_segments
        self.assertEqual(seg("echo 'x \\\n y'; z"), ["echo 'x \\\n y'", "z"])    # single quotes keep it
        self.assertEqual(seg("echo a\\\\\nb"), ["echo a\\\\", "b"])              # an escaped backslash
        self.assertEqual(seg("echo hi # note \\\nb"), ["echo hi # note", "b"])  # a comment ends at the newline
        # (its last backslash is its text, dropped since round 4 so the words stay readable)
        self.assertEqual(seg('echo "a\\"; b"; c'), ['echo "a\\"; b"', "c"])       # \" does not end the quote

    def test_a_continued_command_is_judged_whole(self):
        release = "ask" if CFG.get("fix_lock_release_needs_owner", True) else "allow"
        for cmd, want, lock in (("movemoney \\\n --amt 5", "ask", False),
                                ("cat \\\n .env", "deny", False),
                                ("git push \\\n --force origin x", "deny", False),
                                ("git \\\n push --force origin x", "deny", False),
                                ("git push origin \\\n main", "ask", False),
                                ("python3 .claude/hooks/guard.py fix-lock \\\n off", release, False),
                                ("echo x >> \\\n tests/test_something.py", "deny", True),
                                ("sh -c 'movemoney \\\n --amt 5'", "ask", False),
                                ('bash -c "movemoney \\\n --amt 5"', "ask", False),
                                ("echo hi # note \\\ngit push --force origin x", "deny", False)):
            self.assertEqual({"cmd": cmd, "v": self.v(cmd, lock)}, {"cmd": cmd, "v": want})

    def test_siblings(self):
        """Found sweeping for siblings: an apostrophe in a comment opened a
        "quote" that hid the next line; a continued command in a heredoc fed to
        a shell; a heredoc started on a continued line, under the fix-lock."""
        for cmd, want, lock in (("x=1 # it's fine\ngit push --force origin x", "deny", False),
                                ("# don't\ncat .env", "deny", False),
                                ("cat <<'EOF' | sh\ncat \\\n .env\nEOF", "deny", False),
                                ("python3 - \\\n <<'EOF'\nopen('tests/test_something.py','w')\nEOF", "deny", True)):
            self.assertEqual({"cmd": cmd, "v": self.v(cmd, lock)}, {"cmd": cmd, "v": want})

    def test_a_comment_starts_a_word_and_ends_at_the_newline(self):
        # Mutants that survived the tests above: a comment that never ended,
        # and a `#` inside a word (`a#b`, `$#`) read as a comment.
        for cmd in ("# note\nmovemoney \\\n --amt 5", "echo a#b; movemoney \\\n --amt 5"):
            self.assertEqual({"cmd": cmd, "v": self.v(cmd)}, {"cmd": cmd, "v": "ask"})

    def test_a_hash_inside_a_word_is_not_a_comment(self):
        # Verifier round 1 of this change: after an escaped character, a
        # command substitution or a quote, `#` is part of the word in bash and
        # zsh, so the backslash-newline after it still continues the command.
        for cmd, want in (("paynow --memo=a\\ #b \\\n --amt 5", "ask"),
                          ("paynow --memo=a\\;#b \\\n --amt 5", "ask"),
                          ("paynow --memo=a\\(#b \\\n --amt 5", "ask"),
                          ("paynow --memo=$(true)#b \\\n --amt 5", "ask"),
                          ("paynow --memo=`true`#b \\\n --amt 5", "ask"),
                          ('paynow --memo="a"#b \\\n --amt 5', "ask"),
                          ("cat a\\ #b \\\n .env", "deny"),
                          ("git -c user.name=a\\ #b \\\n push --force origin x", "deny")):
            self.assertEqual({"cmd": cmd, "v": self.v(cmd)}, {"cmd": cmd, "v": want})

    def test_a_doubled_backslash_a_tab_and_a_comment_past_a_semicolon(self):
        # Mutants that survived verifier round 1: `\\` inside double quotes is
        # one escaped backslash (the quote then ends); a TAB ends a word; a
        # comment runs to the newline, past a `;`.
        for cmd, want in (('echo "a\\\\"; cat \\\n .env', "deny"),
                          ("echo hi\t# it's\ncat .env", "deny"),
                          ("x=1 # a; it's\ncat .env", "deny")):
            self.assertEqual({"cmd": cmd, "v": self.v(cmd)}, {"cmd": cmd, "v": want})

    def test_through_the_hook(self):
        event = {"tool_name": "Bash", "tool_input": {"command": "cat \\\n .env"}, "cwd": guard.ROOT}
        proc = subprocess.run([sys.executable, guard.__file__], input=json.dumps(event),
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


class LineContinuationRound3(unittest.TestCase):
    """The continuation fix's verifier, round 2: a backslash at the very end of
    a command (zsh drops it, and so does Claude Code's Bash tool) made shlex
    fail, so `sh -c '…' \\`, `eval "…" \\` and the push check no longer saw the
    command — a force push got through. And mutants of the word-start
    tracking that no test caught (rikuripi/rikurinode,
    docs/build-records/2026-10-11-guard-line-continuation.md, round 3)."""

    SYN = LineContinuation.SYN

    def v(self, cmd: str, profile: str = "stable") -> str:
        return verdict("Bash", {"command": cmd}, cfg=self.SYN, profile=profile)

    def test_a_trailing_backslash_is_dropped_as_the_shell_does(self):
        seg = guard.split_segments
        self.assertEqual(seg("git push origin main\\"), ["git push origin main"])
        self.assertEqual(seg("git push origin main \\"), ["git push origin main"])
        self.assertEqual(seg("echo a\\\\"), ["echo a\\\\"])          # an escaped backslash stays
        self.assertEqual(seg("echo 'a\\'"), ["echo 'a\\'"])           # inside single quotes it is text

    def test_a_command_ending_in_a_backslash_is_judged(self):
        for cmd, want in (("sh -c 'git push --force origin x' \\", "deny"),
                          ('eval "git push --force origin x" \\', "deny"),
                          ("git push --force origin x\\", "deny"),
                          ("git push origin main\\", "ask"),
                          ("git -C . push origin HEAD:main\\", "ask"),
                          ("movemoney --amt 5 \\", "ask")):
            self.assertEqual({"cmd": cmd, "v": self.v(cmd)}, {"cmd": cmd, "v": want})

    def test_a_comment_after_a_redirection_or_a_lone_ampersand(self):
        # `#` after `>`, `<` or `&` starts a word, so a comment: the apostrophe in
        # it is text, and the next line is a command of its own (mutants G1, G2).
        for cmd in ("true >#'\ncat .env", "true <#'\ncat .env", "true &# it's\ncat .env"):
            self.assertEqual({"cmd": cmd, "v": self.v(cmd)}, {"cmd": cmd, "v": "deny"})

    def test_nested_substitutions_are_counted(self):
        # after `$(echo $(true))` the outer substitution has closed, so the `#`
        # that follows is part of the word, and the backslash-newline continues
        # the command (mutant G7: a flag instead of a counter)
        cmd = "paynow --memo=$(echo $(true))#b \\\n --amt 5"
        self.assertEqual({"cmd": cmd, "v": self.v(cmd)}, {"cmd": cmd, "v": "ask"})

    def test_the_length_limit_counts_the_whole_command(self):
        # 16,000 characters is the limit (mutant G4 raised it), over every line
        # (mutant G9 checked the first line only)
        self.assertEqual(verdict("Bash", {"command": "echo " + "a" * 15996}), "ask")
        self.assertEqual(verdict("Bash", {"command": "echo " + "a" * 15995}), "allow")
        self.assertEqual(verdict("Bash", {"command": "echo hi\necho " + "a" * 16100}), "ask")


class TimeBound(unittest.TestCase):
    """Claude Code lets a tool call through when its hook times out (hooks
    reference, 2026-10-11: "A timed-out command … hook doesn't block the tool
    call"). A command the guard could not judge within its time therefore
    asks, in every profile (verifier of the continuation fix: a 69 KB command
    took 14 s against a 10 s hook timeout)."""

    def test_a_command_too_long_to_check_asks_at_once(self):
        cmd = "lncli getinfo " * (guard.MAX_COMMAND_CHARS // 14 + 1)
        start = time.time()
        for profile in ("stable", "development"):
            self.assertEqual(verdict("Bash", {"command": cmd}, profile=profile), "ask", profile)
        self.assertLess(time.time() - start, 1.0)

    def test_the_slowest_command_below_the_limit_is_judged_in_time(self):
        cmd = ("lncli getinfo " * guard.MAX_COMMAND_CHARS)[:guard.MAX_COMMAND_CHARS]
        start = time.time()
        verdict("Bash", {"command": cmd})
        self.assertLess(time.time() - start, 5.0)  # the hook allows 10 s

    def test_out_of_time_the_previous_guard_is_stopped_and_the_answer_is_ask(self):
        # Round 2's verifier: eval chains took 15–23 s through the hook, past
        # its 10 s, because guard_base.py has no time budget. When the new
        # checks are out of time, the previous guard still runs, under the
        # timer: a deny it finds in time stands (round 7's test above); one it
        # cannot finish gives ask, within the overall budget.
        saved, real = guard.CHECK_TIME_BUDGET, guard.base_decide
        guard.CHECK_TIME_BUDGET = 0.0
        guard.base_decide = lambda *a, **k: time.sleep(30) or ("deny", ["never reached"])
        try:
            start = time.time()
            self.assertEqual(verdict("Bash", {"command": "eval eval git status"}), "ask")
            self.assertLess(time.time() - start, guard.OVERALL_TIME_BUDGET + 1.0)
        finally:
            guard.CHECK_TIME_BUDGET, guard.base_decide = saved, real

    def test_new_checks_out_of_time_never_allow(self):
        # even when the previous guard, finished in time, allows
        saved, real = guard.CHECK_TIME_BUDGET, guard.base_decide
        guard.CHECK_TIME_BUDGET = 0.0
        guard.base_decide = lambda *a, **k: ("allow", [])
        try:
            self.assertEqual(verdict("Bash", {"command": "ls"}), "ask")
        finally:
            guard.CHECK_TIME_BUDGET, guard.base_decide = saved, real

    def test_a_stopped_previous_guard_gives_ask_when_the_new_checks_allow_late(self):
        # The new checks finish, with allow, but late, and the previous guard
        # is stopped at the overall budget. Its answer is unknown, so the
        # result is ask, never the new checks' allow (round 3's mutant C5
        # survived the test above, where the new checks' own time-out already
        # gave ask).
        saved = guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET, guard._decide_new, guard.base_decide
        guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET = 1.0, 2.0
        guard._decide_new = lambda *a, **k: time.sleep(0.7) or ("allow", [])
        guard.base_decide = lambda *a, **k: time.sleep(30) or ("deny", ["never reached"])
        try:
            start = time.time()
            self.assertEqual(verdict("Bash", {"command": "git status"}), "ask")
            self.assertLess(time.time() - start, 4.0)
        finally:
            guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET, guard._decide_new, guard.base_decide = saved

    SLOW_SEARCH = r'''
import json, re, sys, time
sys.path.insert(0, sys.argv[1])
import guard
guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET = 1.0, 2.0
cfg = dict(guard.load_config(), profile="stable")
if sys.argv[2] == "new":   # one rule whose single search never ends
    cfg["funds_patterns"] = [{"regex": r"(a+)+$", "reason": "slow", "always_ask": True}]
else:                      # the new checks are quick; the previous guard's search never ends
    guard._decide_new = lambda *a, **k: ("allow", [])
    guard.base_decide = lambda *a, **k: re.search(r"(a+)+$", "a" * 40 + "b") or ("allow", [])
start = time.time()
d = guard.decide({"tool_name": "Bash", "tool_input": {"command": "echo " + "a" * 40 + "b"}, "cwd": guard.ROOT},
                 cfg, guard.ROOT, lock_present=False, branch_fn=lambda _c: "feature/x")
print(json.dumps([d[0], time.time() - start]))
'''

    def test_one_slow_search_is_stopped_at_the_budget(self):
        # Round 3's own probe: one policy rule took 9.8 s on a 16,000-character
        # command, and the budget was only checked between rules, so the guard
        # answered after 8.9 s (the hook has 10). A timer now stops a search
        # wherever it is: in the new checks, and in the previous guard when it
        # runs in this process. Run in a child process, so that a guard without
        # the timer fails this test instead of hanging it.
        for where in ("new", "previous"):
            try:
                proc = subprocess.run([sys.executable, "-B", "-c", self.SLOW_SEARCH, os.path.dirname(guard.__file__),
                                       where], capture_output=True, text=True, timeout=15)
            except subprocess.TimeoutExpired:
                self.fail("%s: no answer within 15 s" % where)
            got, took = json.loads(proc.stdout)
            self.assertEqual((where, got), (where, "ask"))
            self.assertLess(took, 3.0, where)

    def test_the_timer_firing_as_it_is_disarmed_is_out_of_time(self):
        # Seen once in this suite while building the timer: the timer and the
        # checks' own deadline are the same moment, it fired inside its disarm,
        # and the exception escaped decide(). Here it fires there every time.
        real, calls = guard._alarm, []

        def alarm(_seconds):
            def disarm():
                calls.append(1)
                if len(calls) == 1:
                    raise guard._OutOfTime()
            return disarm
        guard._alarm = alarm
        try:
            self.assertIsNone(guard._timed(5.0, lambda: ("allow", [])))
            self.assertEqual(len(calls), 2)  # disarmed again
        finally:
            guard._alarm = real

    def test_the_timer_is_not_an_exception_a_handler_could_swallow(self):
        # an `except Exception` between the timer and decide() would otherwise
        # end the check early and carry on as if it had finished
        self.assertTrue(issubclass(guard._OutOfTime, BaseException))
        self.assertFalse(issubclass(guard._OutOfTime, Exception))

    def test_a_timer_that_escapes_still_asks(self):
        real = guard.decide

        def escaping(*a, **k):
            raise guard._OutOfTime()
        guard.decide = escaping
        try:
            out = guard.run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}))
        finally:
            guard.decide = real
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_crafted_slow_commands_are_answered_in_time(self):
        # the shapes round 2's verifier timed at 6 to 23 s
        for cmd in (("git " * 4000)[:16000], ("eval eval eval " + "git " * 4000)[:16000],
                    ("eval " * 6 + "git " * 3980)[:15960] + "; lncli sendcoins --addr x --amt 1"):
            start = time.time()
            got = verdict("Bash", {"command": cmd})
            self.assertLess(time.time() - start, 8.0, cmd[:30])
            self.assertIn(got, ("ask", "allow"), cmd[:30])

    def test_a_long_harmless_command_below_the_limit_is_free(self):
        self.assertEqual(verdict("Bash", {"command": "echo " + "a" * (guard.MAX_COMMAND_CHARS - 5)}), "allow")


class LineContinuationRound4(unittest.TestCase):
    """The continuation fix's verifier, round 3 (rikuripi/rikurinode,
    docs/build-records/2026-10-11-guard-line-continuation.md, round 4): the
    fix made the guard looser than before in three ways bash and zsh run —
    an escaped blank at a command's end (`\\ `) became a trailing backslash
    when the segment was stripped; a comment ending in a backslash did the
    same; a `#` inside a backtick or `$(…)` was read as a comment, so the
    newline inside the substitution split the command and its text was never
    judged. And a quote in a heredoc's body swallowed the commands after it."""

    SYN = LineContinuation.SYN

    def v(self, cmd: str, profile: str = "stable") -> str:
        return verdict("Bash", {"command": cmd}, cfg=self.SYN, profile=profile)

    def test_an_escaped_blank_at_the_end_is_a_word(self):
        seg = guard.split_segments
        self.assertEqual(seg("echo a \\ "), ["echo a \\ "])
        self.assertEqual(seg("echo a \\\t"), ["echo a \\\t"])
        self.assertEqual(seg("echo a \\  "), ["echo a \\ "])           # the blank after it is not escaped
        self.assertEqual(seg("echo a \\\\ "), ["echo a \\\\"])          # an escaped backslash, then a blank
        for tail in ("\\ ", "\\\t", "\\ ;true", "\\ |cat", "\\ &&true", "\\ \ntrue"):
            for head in ("sh -c 'git push --force origin x' ", 'eval "git push --force origin x" '):
                for profile in ("stable", "development"):
                    cmd = head + tail
                    self.assertEqual({"cmd": cmd, "p": profile, "v": self.v(cmd, profile)},
                                     {"cmd": cmd, "p": profile, "v": "deny"})
        for cmd in ("sh -c 'git push origin main' \\ ", "sh -c 'movemoney --amt 5' \\ "):
            self.assertEqual({"cmd": cmd, "v": self.v(cmd)}, {"cmd": cmd, "v": "ask"})

    def test_a_comment_ending_in_a_backslash(self):
        for cmd in ('eval "cat .env" # note \\', "sh -c 'git push --force origin x' # c \\",
                    "bash -c 'cat .env' #\\", "sh -c 'git push --force origin x' # c \\\\\\"):
            for profile in ("stable", "development"):
                self.assertEqual({"cmd": cmd, "p": profile, "v": self.v(cmd, profile)},
                                 {"cmd": cmd, "p": profile, "v": "deny"})
        # the newline still ends the comment, so the next line is a command (mutant V16 of round 3)
        self.assertEqual(self.v("echo a # note \\\necho b"), "allow")
        self.assertEqual(self.v("echo a # note \\\ncat .env"), "deny")

    def test_a_hash_inside_a_substitution_is_not_a_comment(self):
        # bash reads a comment there too, but this splitter does not try: as the
        # guard before the fix, it keeps the substitution's text in one piece,
        # and judges it as a command of its own
        for cmd in ("echo `git push -f origin #'\"\nx`", "echo $(git push -f origin #'\"\nx)",
                    "x=$( true # it's\n); git push --force origin x",
                    "x=$( true # it's\n); cat .env"):  # an unclosed substitution's text, to its last character
            for profile in ("stable", "development"):
                self.assertEqual({"cmd": cmd, "p": profile, "v": self.v(cmd, profile)},
                                 {"cmd": cmd, "p": profile, "v": "deny"})
        for cmd in ("zsh -c $( true # it's\n) 'cat .env'", "sh -c `true # it's\n` 'git push --force origin x'"):
            self.assertNotEqual({"cmd": cmd, "v": self.v(cmd)}, {"cmd": cmd, "v": "allow"})

    def test_a_quote_in_a_heredoc_body_does_not_hide_what_follows(self):
        for cmd in (": # it's\n<<X\n'\nX\n(git push --force origin x)", "cat <<X\n'\nX\ngit push --force origin x",
                    "cat <<'X'\n\"\nX\ncat .env", "sh <<'X'\n'\ngit push --force origin x\nX"):
            for profile in ("stable", "development"):
                self.assertEqual({"cmd": cmd, "p": profile, "v": self.v(cmd, profile)},
                                 {"cmd": cmd, "p": profile, "v": "deny"})
        self.assertEqual(self.v("cat <<'X' > notes.md\nit's fine\nX"), "allow")

    def test_a_comment_starts_after_a_separator_or_a_parenthesis(self):
        # round 3's surviving mutants V18, V20 and V21: after `;`, `(` and `)` a
        # `#` starts a comment, so its apostrophe opens no quote
        for cmd in ("true;# it's\ncat .env", "(# it's\ncat .env\n)", "(true)# it's\ncat .env"):
            self.assertEqual({"cmd": cmd, "v": self.v(cmd)}, {"cmd": cmd, "v": "deny"})


class TimeBoundRound4(unittest.TestCase):
    """Round 3's verifier: a deny the new checks found in time became ask when
    the previous guard was then stopped; and two timer mutants survived (V2:
    a disarmed timer left running; V10: the new checks given the whole
    budget)."""

    def test_a_deny_found_in_time_stands_when_the_previous_guard_is_stopped(self):
        saved = guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET, guard.base_decide
        guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET = 1.0, 1.5
        guard.base_decide = lambda *a, **k: time.sleep(30) or ("allow", [])
        try:
            start = time.time()
            self.assertEqual(verdict("Bash", {"command": "git push --force origin x"}), "deny")
            self.assertLess(time.time() - start, 4.0)
        finally:
            guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET, guard.base_decide = saved

    def test_the_timer_is_off_once_the_guard_has_answered(self):
        import signal
        if not hasattr(signal, "setitimer"):
            self.skipTest("no interval timer on this platform")
        before = signal.getsignal(signal.SIGALRM)
        verdict("Bash", {"command": "git status"})
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        self.assertIs(signal.getsignal(signal.SIGALRM), before)

    def test_the_new_checks_have_their_own_budget(self):
        # they finish (allow) after their budget but within the overall one: out of time, so ask
        saved = guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET, guard._decide_new, guard.base_decide
        guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET = 0.3, 2.0
        guard._decide_new = lambda *a, **k: time.sleep(0.8) or ("allow", [])
        guard.base_decide = lambda *a, **k: ("allow", [])
        try:
            self.assertEqual(verdict("Bash", {"command": "git status"}), "ask")
        finally:
            guard.CHECK_TIME_BUDGET, guard.OVERALL_TIME_BUDGET, guard._decide_new, guard.base_decide = saved


class JudgedAsOneLine(unittest.TestCase):
    """Owner, 2026-10-11 ("Judge as one line"): a command continued over lines
    is judged as the same command on one line — by the new checks, and by the
    previous guard, which is given the joined text (_joined)."""

    def test_the_lines_are_joined_as_the_shell_joins_them(self):
        j = guard._joined
        self.assertEqual(j("lncli \\\n  getinfo"), "lncli   getinfo")
        self.assertEqual(j('echo "a \\\nb"'), 'echo "a b"')                    # double quotes join
        self.assertEqual(j("echo 'a \\\nb'"), "echo 'a \\\nb'")                # single quotes keep it
        self.assertEqual(j("# note \\\ngit status"), "# note \\\ngit status")  # a comment ends at the newline
        self.assertEqual(j("echo a\\\\\nb"), "echo a\\\\\nb")                  # an escaped backslash
        self.assertEqual(j("ls \\"), "ls ")                                    # a backslash that ends it

    def test_the_previous_guard_is_given_the_joined_command(self):
        seen, real = [], guard.base_decide
        guard.base_decide = lambda event, *a, **k: seen.append(event["tool_input"]["command"]) or ("allow", [])
        try:
            verdict("Bash", {"command": "lncli \\\n  getinfo"})
            verdict("Bash", {"command": "git status"})
        finally:
            guard.base_decide = real
        # joined first; then, as it allowed, line by line too (only a deny
        # found there would count: the next test)
        self.assertEqual(seen, ["lncli   getinfo", "lncli \\\n  getinfo", "git status"])

    def test_a_rule_on_a_line_end_no_longer_asks_for_a_continued_command(self):
        # a policy rule that asks when a line ends in a backslash, as the
        # previous guard read every line of a continued command
        cfg = dict(LineContinuation.SYN, funds_patterns=[{"regex": r"\\$", "reason": "continued", "always_ask": True}])
        self.assertEqual(verdict("Bash", {"command": "ls \\\n -la"}, cfg=cfg), "allow")
        # a backslash that ends a comment at the command's end continues
        # nothing: the previous guard is not given it either (round 4's
        # verifier: mutant V16 changed this verdict, untested)
        self.assertEqual(guard._joined("ls -la # note \\"), "ls -la # note ")
        self.assertEqual(verdict("Bash", {"command": "ls -la # note \\"}, cfg=cfg), "allow")

    def test_a_deny_the_previous_guard_finds_line_by_line_stands(self):
        # round 4's fuzzer and shell oracle: on one line a lone & hides the
        # push (an older hole); line by line it was denied, and still is.
        # zsh runs `{\⏎git …}` as a group.
        for cmd in ("true & \\\ngit push -f origin x", "true & \\\n git push --force origin x #",
                    "{\\\ngit push --force \\\n\torigin x; }"):
            for profile in ("stable", "development"):
                self.assertEqual({"cmd": cmd, "p": profile, "v": verdict("Bash", {"command": cmd}, profile=profile)},
                                 {"cmd": cmd, "p": profile, "v": "deny"})

    def test_an_escaped_quote_inside_a_substitution_opens_no_quote(self):
        # round 4's fuzzer: `\"` (and `'\'`) made `$(…)` look unclosed, and its
        # text kept the `)`, so the secret file's name no longer matched
        for cmd in ('echo $(head -\\"c 99 .env)', "echo $(head -'\\'c 99 .env)", 'x=$(cat \\"x .env)'):
            self.assertEqual({"cmd": cmd, "v": verdict("Bash", {"command": cmd})}, {"cmd": cmd, "v": "deny"})
        # the shell's reading comes first; the plain one, where it differs, is judged too (only adds)
        self.assertEqual(guard._substitutions('echo $(head -\\"c 99 .env)')[0], 'head -\\"c 99 .env')
        self.assertEqual(guard._substitutions("echo $(printf '%s' \")\")"), ["printf '%s' \")\""])
        cmd = "cd \"$(sh -c 'git push --force origin x' \\)\""  # an escaped `)`: the plain reading sees the push
        self.assertNotEqual(verdict("Bash", {"command": cmd}), "allow")


class LoneAmpersand(unittest.TestCase):
    """A lone `&` runs what is before it in the background and ends that
    command, as `;` does; the guard read it as part of the command, which hid
    the rest of the line (an older hole; round 4's fuzzer found it hiding force
    pushes once a continued command was judged as one line)."""

    def test_a_lone_ampersand_ends_a_command(self):
        seg = guard.split_segments
        self.assertEqual(seg("true & git status"), ["true", "git status"])
        self.assertEqual(seg("a & b & c"), ["a", "b", "c"])
        self.assertEqual(seg("true |& git status"), ["true", "git status"])        # |& is a pipe
        self.assertEqual(seg("make 2>&1 | tail"), ["make 2>&1", "tail"])           # a redirection, not a separator
        self.assertEqual(seg("make &>/dev/null; ls >&2"), ["make &>/dev/null", "ls >&2"])
        self.assertEqual(seg("cat <&3"), ["cat <&3"])
        self.assertEqual(seg("a && b"), ["a", "b"])
        self.assertEqual(seg("echo 'a & b' \"c & d\" e\\&f"), ["echo 'a & b' \"c & d\" e\\&f"])

    def test_what_follows_a_lone_ampersand_is_judged(self):
        for cmd in ("true & git push -f origin x", "sleep 1 & cat .env", "true |& git push --force origin x",
                    "true & \\\ngit push -f origin x"):
            for profile in ("stable", "development"):
                self.assertEqual({"cmd": cmd, "p": profile, "v": verdict("Bash", {"command": cmd}, profile=profile)},
                                 {"cmd": cmd, "p": profile, "v": "deny"})
        self.assertEqual(verdict("Bash", {"command": "make 2>&1 | tail -3"}), "allow")


if __name__ == "__main__":
    unittest.main()
