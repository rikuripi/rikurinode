"""Tests that hold the CI workflows together with the audit and the gate.

Every action is pinned to a commit with its version named (the audit refuses
otherwise, SEC-06); the cargo-deny install lines are the same in ci.yml and
advisory-audit.yml, so the two cannot drift apart; the audit runs on a
schedule and on demand with a read-only token and runs both readers; ci.yml's
token has exactly the two read permissions the gate needs; the gate runs the
stale-audit warning as its last step (TEST-05). Reads the repository's own
files; no network.
Record: docs/build-records/2026-10-21-weekly-advisory-audit.md
Run: python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'
"""
import glob
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import osv_audit as oa  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
WORKFLOWS = sorted(glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml")))
CI = os.path.join(ROOT, ".github", "workflows", "ci.yml")
AUDIT = os.path.join(ROOT, ".github", "workflows", "advisory-audit.yml")
GATE = os.path.join(ROOT, "scripts", "quality", "full-gate.sh")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def block(text, key):
    """The lines indented under a top-level `key:`, stripped, without comments or blanks."""
    lines, inside = [], False
    for line in text.splitlines():
        if re.match(r"^[A-Za-z_]+:", line):
            inside = line.startswith(key + ":")
            continue
        if inside and line.strip() and not line.strip().startswith("#"):
            lines.append(re.sub(r"\s+#.*$", "", line.strip()))
    return lines


def cargo_deny_lines(text):
    """The install lines that name the cargo-deny archive and its checksum (not the other tools')."""
    return [line.strip() for line in text.splitlines()
            if "cargo-deny" in line and (line.strip().startswith("https://") or re.match(r'^\s*echo "[0-9a-f]{64}\s', line))]


class Pins(unittest.TestCase):
    def test_every_action_is_pinned_with_its_version_named(self):
        found = oa.pinned_actions(WORKFLOWS)
        self.assertGreaterEqual(len(found), 3, found)
        for name, version, where in found:
            self.assertRegex(name, r"^[\w.-]+/[\w.-]+$", where)
            self.assertRegex(version, r"^\d+(\.\d+)*$", where)
        self.assertIn("actions/checkout", [name for name, _, _ in found])


class Audit(unittest.TestCase):
    def test_cargo_deny_install_lines_are_identical_to_ci(self):
        in_ci, in_audit = cargo_deny_lines(read(CI)), cargo_deny_lines(read(AUDIT))
        self.assertTrue(in_ci, "ci.yml installs cargo-deny by a checksummed archive")
        self.assertTrue(any(re.match(r'^echo "[0-9a-f]{64}\s', line) for line in in_ci), in_ci)
        self.assertEqual(in_ci, in_audit)

    def test_scheduled_on_demand_and_on_its_own_inputs(self):
        on = block(read(AUDIT), "on")
        self.assertIn("schedule:", on)
        self.assertTrue(any(re.match(r"^- cron: '\d+ \d+ \* \* \d'$", line) for line in on), on)
        self.assertIn("workflow_dispatch:", on)
        self.assertIn("pull_request:", on)
        for path in (".github/workflows/advisory-audit.yml", "control-plane/Cargo.lock", "control-plane/deny.toml",
                     "scripts/quality/osv_audit.py"):
            self.assertIn("- " + path, on)

    def test_read_only_token_and_pinned_runner(self):
        text = read(AUDIT)
        self.assertEqual(block(text, "permissions"), ["contents: read"])
        self.assertIn("runs-on: ubuntu-24.04", text)
        self.assertIn("persist-credentials: false", text)

    def test_runs_both_readers(self):
        text = read(AUDIT)
        self.assertIn("deny --manifest-path control-plane/Cargo.toml --locked check advisories", text)
        self.assertIn("python3 scripts/quality/osv_audit.py", text)


class Ci(unittest.TestCase):
    def test_token_permissions_are_exactly_the_two_reads(self):
        self.assertEqual(sorted(block(read(CI), "permissions")), ["actions: read", "contents: read"])

    def test_the_gate_step_gets_the_token(self):
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", read(CI))


class Gate(unittest.TestCase):
    def test_runs_the_stale_audit_warning_last(self):
        text = read(GATE)
        self.assertIn('step "10/10', text)
        self.assertIn("python3 scripts/quality/advisory_audit_age.py", text)
        self.assertIn("all 10 steps passed", text)
        self.assertLess(text.index("advisory_audit_age.py"), text.index("all 10 steps passed"))


if __name__ == "__main__":
    unittest.main()
