"""Tests for scripts/quality/guard_policy.py, the source of the guard's policy.

The policy (.claude/hooks/guard-config.json) is written by the generator, and
the full gate refuses a policy edited by hand: the two cannot drift. Every
rule must be exercised by at least one worked example, or nothing replays it.
Record: docs/build-records/2026-10-10-bootstrap.md
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, ".claude", "hooks"))
import guard  # noqa: E402
import guard_policy as gp  # noqa: E402


class Generator(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.config = os.path.join(self.dir, "guard-config.json")
        shutil.copy(gp.CONFIG, self.config)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def edit(self, change):
        with open(self.config) as f:
            cfg = json.load(f)
        change(cfg)
        with open(self.config, "w") as f:
            json.dump(cfg, f)

    def test_the_committed_policy_is_what_the_generator_writes(self):
        self.assertEqual(gp.main(["guard_policy.py", "--check"]), 0)

    def test_a_policy_edited_by_hand_is_refused_and_named(self):
        def loosen(cfg):
            cfg["funds_patterns"][0]["always_ask"] = False
            cfg["secret_globs"].remove("wallet.db")
        self.edit(loosen)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(gp.main(["guard_policy.py", "--check"], self.config), 1)
        self.assertIn("funds_patterns, secret_globs", err.getvalue())

    def test_writing_restores_the_rules_and_keeps_the_examples(self):
        def drift(cfg):
            cfg["funds_patterns"].pop()
            cfg["examples"].append({"tool": "Bash", "input": {"command": "true"}, "expect": "allow"})
        self.edit(drift)
        self.assertEqual(gp.main(["guard_policy.py"], self.config), 0)
        self.assertEqual(gp.main(["guard_policy.py", "--check"], self.config), 0)
        with open(self.config) as f:
            cfg = json.load(f)
        self.assertEqual(len(cfg["funds_patterns"]), len(gp.RULES))
        self.assertEqual(cfg["examples"][-1]["input"], {"command": "true"})


class EveryRuleHasAnExample(unittest.TestCase):
    def test_each_rule_matches_a_worked_example(self):
        with open(gp.CONFIG) as f:
            cfg = json.load(f)
        segments = [seg for ex in cfg["examples"] if ex["tool"] == "Bash" and ex["expect"] != "allow"
                    for seg in guard.split_segments(ex["input"]["command"])]
        for n, rule in enumerate(gp.RULES):
            with self.subTest(rule=n, reason=rule["reason"][:60]):
                self.assertTrue(any(re.search(rule["regex"], s) for s in segments),
                                "no worked example exercises this rule")


if __name__ == "__main__":
    unittest.main()
