"""Tests for scripts/quality/advisory_audit_age.py, the gate's stale-audit warning (TEST-05).

Every way the check can fail to see must print a warning that names its
cause and still exit 0 (the gate never fails on it); a fresh success prints
one ok line; the eight-day limit holds at both sides; a failed latest run
warns even when an older success exists; only scheduled and dispatched runs
count. No network: the fetcher is a fake.
Record: docs/build-records/2026-10-21-weekly-advisory-audit.md
Run: python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'
"""
import http.client
import io
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import advisory_audit_age as age  # noqa: E402

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
ENV = {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "rikuripi/rikurinode"}


def run_at(days_ago, event="schedule", conclusion="success", url="https://github.com/x/y/actions/runs/1"):
    when = NOW - timedelta(days=days_ago)
    return {"event": event, "conclusion": conclusion, "html_url": url,
            "created_at": when.strftime("%Y-%m-%dT%H:%M:%SZ")}


class Fake:
    def __init__(self, status=200, payload=None, raises=None):
        self.status, self.payload, self.raises = status, payload, raises
        self.calls = []

    def __call__(self, url, token):
        self.calls.append((url, token))
        if self.raises is not None:
            raise self.raises
        return self.status, self.payload


def check(fake, env=ENV, argv=()):
    out, err = io.StringIO(), io.StringIO()
    rc = age.main(list(argv), env=env, fetch=fake, now=NOW, out=out, err=err)
    return rc, out.getvalue(), err.getvalue()


class Warnings(unittest.TestCase):
    def assertWarns_(self, result, cause):
        rc, out, err = result
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith(age.WARNING), out)
        self.assertIn(cause, out)
        self.assertEqual(out.count("\n"), 1, out)

    def test_no_token_warns_and_asks_nothing(self):
        fake = Fake()
        self.assertWarns_(check(fake, env={}), "no token")
        self.assertEqual(fake.calls, [])

    def test_gh_token_counts_too(self):
        fake = Fake(payload={"workflow_runs": [run_at(1)]})
        rc, out, _ = check(fake, env={"GH_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"})
        self.assertTrue(out.startswith(age.OK), out)
        self.assertEqual(fake.calls[0][1], "t")
        self.assertIn("/repos/o/r/actions/workflows/advisory-audit.yml/runs?branch=main&status=completed", fake.calls[0][0])

    def test_unknown_repository_warns(self):
        with tempfile.TemporaryDirectory() as folder:
            cwd = os.getcwd()
            os.chdir(folder)
            try:
                self.assertWarns_(check(Fake(), env={"GITHUB_TOKEN": "t"}), "repository is unknown")
            finally:
                os.chdir(cwd)

    def test_http_403_and_404_warn_with_the_status(self):
        self.assertWarns_(check(Fake(status=403)), "HTTP 403")
        self.assertWarns_(check(Fake(status=404)), "HTTP 404")

    def test_unreachable_and_non_json_warn(self):
        self.assertWarns_(check(Fake(raises=OSError("no route"))), "cannot read the runs")
        self.assertWarns_(check(Fake(raises=ValueError("Expecting value"))), "cannot read the runs")
        self.assertWarns_(check(Fake(raises=http.client.IncompleteRead(b""))), "cannot read the runs")

    def test_an_answer_of_the_wrong_shape_warns(self):
        self.assertWarns_(check(Fake(payload=["x"])), "no workflow_runs list")
        self.assertWarns_(check(Fake(payload={"workflow_runs": [{"event": "schedule", "created_at": "soon"}]})), "readable created_at")

    def test_no_counted_run_warns(self):
        self.assertWarns_(check(Fake(payload={"workflow_runs": []})), "no completed scheduled or dispatched run")
        self.assertWarns_(check(Fake(payload={"workflow_runs": [run_at(1, event="pull_request")]})),
                          "no completed scheduled or dispatched run")

    def test_nine_days_warns_seven_and_eight_do_not(self):
        self.assertWarns_(check(Fake(payload={"workflow_runs": [run_at(9)]})), "9.00 days old, older than the 8-day limit")
        for days in (7, 8):
            rc, out, _ = check(Fake(payload={"workflow_runs": [run_at(days)]}))
            self.assertEqual(rc, 0)
            self.assertTrue(out.startswith(age.OK), out)
            self.assertIn("%d.00 days old" % days, out)
        self.assertWarns_(check(Fake(payload={"workflow_runs": [run_at(8.01)]})), "8.01 days old, older than the 8-day limit")

    def test_a_failed_latest_run_warns_despite_an_older_success(self):
        payload = {"workflow_runs": [run_at(3, conclusion="success"), run_at(1, conclusion="failure")]}
        self.assertWarns_(check(Fake(payload=payload)), "concluded failure")

    def test_any_conclusion_but_success_warns(self):
        # Verifier's AGE4 (2026-10-21): only "failure" was tested; the audit has timeout-minutes, so timed_out is real.
        for conclusion in ("cancelled", "timed_out", "startup_failure", "skipped", "action_required", None):
            payload = {"workflow_runs": [run_at(3), run_at(1, conclusion=conclusion)]}
            self.assertWarns_(check(Fake(payload=payload)), "concluded %s" % conclusion)

    def test_a_dispatched_success_counts_and_a_pull_request_run_does_not(self):
        payload = {"workflow_runs": [run_at(0.5, event="pull_request", conclusion="failure"), run_at(2, event="workflow_dispatch")]}
        rc, out, _ = check(Fake(payload=payload))
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith(age.OK), out)
        self.assertIn("workflow_dispatch run", out)
        self.assertIn("2.00 days old", out)

    def test_usage_error_is_2(self):
        rc, out, err = check(Fake(), argv=["x"])
        self.assertEqual((rc, out), (2, ""))
        self.assertIn("usage", err)


class Remotes(unittest.TestCase):
    def test_https_and_ssh_forms(self):
        self.assertEqual(age.parse_remote("https://github.com/rikuripi/rikurinode.git\n"), "rikuripi/rikurinode")
        self.assertEqual(age.parse_remote("https://github.com/rikuripi/rikurinode"), "rikuripi/rikurinode")
        self.assertEqual(age.parse_remote("git@github.com:rikuripi/rikurinode.git"), "rikuripi/rikurinode")
        self.assertIsNone(age.parse_remote("https://example.com/rikuripi/rikurinode.git"))
        self.assertIsNone(age.parse_remote(""))

    def test_this_checkout_reads_its_origin(self):
        # Whatever the clone's origin is (a fork too; verifier's nit 3), repository() reads it the way parse_remote does.
        cwd = os.path.dirname(HERE)
        done = subprocess.run(["git", "remote", "get-url", "origin"], cwd=cwd, capture_output=True, text=True)
        if done.returncode != 0:
            self.skipTest("no origin remote here")
        self.assertEqual(age.repository({}, cwd=cwd), age.parse_remote(done.stdout))
        self.assertEqual(age.repository({"GITHUB_REPOSITORY": "o/r"}, cwd=cwd), "o/r")


class Times(unittest.TestCase):
    def test_z_suffix_and_offset(self):
        self.assertEqual(age.parse_time("2026-10-21T08:00:00Z"), datetime(2026, 10, 21, 8, tzinfo=timezone.utc))
        self.assertEqual(age.parse_time("2026-10-21T08:00:00+00:00"), datetime(2026, 10, 21, 8, tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            age.parse_time("soon")


if __name__ == "__main__":
    unittest.main()
