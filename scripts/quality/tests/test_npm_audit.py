"""Tests for scripts/quality/npm_audit.py, the setup pages' audit (5c.3a).

npm's own `--audit-level` can only fail on everything at a level or nothing,
so the gate reads `npm audit --json` instead: any advisory fails it unless
it is a recorded exception with a reason and a review date; an exception
that no longer matches, or whose date has passed, fails too; and a report
that cannot be read, or that npm could not fetch, fails as loudly as an
advisory. A passing run names every exception it allowed (never silent).
Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md
Run: python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'
"""
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import npm_audit  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TODAY = date(2026, 11, 11)
GHSA = "GHSA-gcqx-w48m-w2h4"

CLEAN = {"auditReportVersion": 2, "vulnerabilities": {},
         "metadata": {"vulnerabilities": {"info": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0,
                                          "total": 0}}}

# The shape npm 10 printed for the advisory CI saw (run 43085490570).
DEEPMERGE = {
    "auditReportVersion": 2,
    "vulnerabilities": {
        "deepmerge": {
            "name": "deepmerge", "severity": "low", "isDirect": False,
            "via": [{"source": 1109612, "name": "deepmerge", "dependency": "deepmerge",
                     "title": "deepmerge mergeObject() allows prototype poisoning of returned objects",
                     "url": "https://github.com/advisories/" + GHSA, "severity": "low", "range": ">=4.2.0"}],
            "effects": ["@sveltejs/vite-plugin-svelte"], "range": ">=4.2.0",
            "nodes": ["node_modules/deepmerge"], "fixAvailable": False},
        "@sveltejs/vite-plugin-svelte": {
            "name": "@sveltejs/vite-plugin-svelte", "severity": "low", "isDirect": True,
            "via": ["deepmerge"], "effects": [], "range": "*",
            "nodes": ["node_modules/@sveltejs/vite-plugin-svelte"], "fixAvailable": False},
    },
    "metadata": {"vulnerabilities": {"info": 0, "low": 2, "moderate": 0, "high": 0, "critical": 0, "total": 2}},
}

EXCEPTIONS = {GHSA: {"package": "deepmerge", "why": "build-time only; merges the plugin's own config",
                     "review_by": "2027-02-11",
                     "record": "docs/build-records/2026-11-11-5c3a-ui-pipeline.md"}}


def other_advisory(report, ghsa="GHSA-aaaa-bbbb-cccc", name="vite"):
    report = copy.deepcopy(report)
    report["vulnerabilities"][name] = {
        "name": name, "severity": "moderate", "isDirect": True,
        "via": [{"source": 1, "name": name, "dependency": name, "title": "something",
                 "url": "https://github.com/advisories/" + ghsa, "severity": "moderate", "range": "<9"}],
        "effects": [], "range": "<9", "nodes": ["node_modules/" + name], "fixAvailable": True}
    report["metadata"]["vulnerabilities"]["moderate"] += 1
    report["metadata"]["vulnerabilities"]["total"] += 1
    return report


class Check(unittest.TestCase):
    def ok(self, report, exceptions=None, today=TODAY):
        return npm_audit.check(report, EXCEPTIONS if exceptions is None else exceptions, today)

    def test_a_clean_report_passes_with_no_exceptions(self):
        ok, lines = self.ok(CLEAN, {})
        self.assertTrue(ok, lines)

    def test_the_recorded_exception_passes_and_is_named(self):
        ok, lines = self.ok(DEEPMERGE)
        self.assertTrue(ok, lines)
        text = "\n".join(lines)
        self.assertIn(GHSA, text)
        self.assertIn("2027-02-11", text)

    def test_an_advisory_with_no_exception_fails_and_is_named(self):
        ok, lines = self.ok(DEEPMERGE, {})
        self.assertFalse(ok)
        self.assertIn(GHSA, "\n".join(lines))

    def test_a_second_advisory_fails_even_beside_the_exception(self):
        ok, lines = self.ok(other_advisory(DEEPMERGE))
        self.assertFalse(ok)
        self.assertIn("GHSA-aaaa-bbbb-cccc", "\n".join(lines))

    def test_an_exception_no_longer_reported_fails(self):
        ok, lines = self.ok(CLEAN)
        self.assertFalse(ok)
        self.assertIn(GHSA, "\n".join(lines))

    def test_an_exception_past_its_review_date_fails(self):
        ok, _ = self.ok(DEEPMERGE, today=date(2027, 2, 11))
        self.assertTrue(ok, "the review date itself still passes")
        ok, lines = self.ok(DEEPMERGE, today=date(2027, 2, 12))
        self.assertFalse(ok)
        self.assertIn("2027-02-11", "\n".join(lines))

    def test_an_exception_for_another_package_does_not_match(self):
        wrong = {GHSA: dict(EXCEPTIONS[GHSA], package="lodash")}
        ok, _ = self.ok(DEEPMERGE, wrong)
        self.assertFalse(ok)

    def test_an_exception_needs_every_field(self):
        for field in ("package", "why", "review_by", "record"):
            with self.subTest(field=field):
                partial = {GHSA: {k: v for k, v in EXCEPTIONS[GHSA].items() if k != field}}
                ok, _ = self.ok(DEEPMERGE, partial)
                self.assertFalse(ok)
        ok, _ = self.ok(DEEPMERGE, {GHSA: dict(EXCEPTIONS[GHSA], review_by="soon")})
        self.assertFalse(ok)
        ok, _ = self.ok(DEEPMERGE, {GHSA: dict(EXCEPTIONS[GHSA], why=" ")})
        self.assertFalse(ok)

    def test_an_advisory_without_an_id_fails(self):
        report = copy.deepcopy(DEEPMERGE)
        report["vulnerabilities"]["deepmerge"]["via"][0]["url"] = "https://example.com/x"
        ok, _ = self.ok(report)
        self.assertFalse(ok)

    def test_a_package_pointing_at_nothing_reported_fails(self):
        report = copy.deepcopy(DEEPMERGE)
        report["vulnerabilities"]["@sveltejs/vite-plugin-svelte"]["via"] = ["not-in-the-report"]
        ok, _ = self.ok(report)
        self.assertFalse(ok)

    def test_what_cannot_be_read_fails(self):
        for why, report in (
                ("nothing", None),
                ("not an object", []),
                ("npm could not fetch the audit", {"error": {"code": "ENOAUDIT", "summary": "no audit"}}),
                ("another version", dict(CLEAN, auditReportVersion=1)),
                ("no vulnerabilities map", {"auditReportVersion": 2, "metadata": CLEAN["metadata"]}),
                ("no totals", {"auditReportVersion": 2, "vulnerabilities": {}}),
                ("totals that disagree", dict(copy.deepcopy(DEEPMERGE), metadata=CLEAN["metadata"]))):
            with self.subTest(why=why):
                ok, lines = self.ok(report, {})
                self.assertFalse(ok)
                self.assertTrue(lines)


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="npm-audit-")
        self.addCleanup(shutil.rmtree, self.dir)

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def run_main(self, report_text, exceptions=EXCEPTIONS):
        report = self.write("audit.json", report_text)
        allowed = self.write("exceptions.json", json.dumps(exceptions))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = npm_audit.main([report, allowed, "--today", TODAY.isoformat()])
        return code, out.getvalue() + err.getvalue()

    def test_pass_and_fail_exit_codes(self):
        code, text = self.run_main(json.dumps(DEEPMERGE))
        self.assertEqual(code, 0, text)
        self.assertIn(GHSA, text)
        code, text = self.run_main(json.dumps(DEEPMERGE), {})
        self.assertEqual(code, 1, text)

    def test_an_empty_or_broken_report_fails(self):
        for text in ("", "{", "null"):
            with self.subTest(text=text):
                code, _ = self.run_main(text)
                self.assertEqual(code, 1)

    def test_a_missing_report_fails(self):
        allowed = self.write("exceptions.json", json.dumps(EXCEPTIONS))
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = npm_audit.main([os.path.join(self.dir, "nope.json"), allowed])
        self.assertEqual(code, 1)


class TheRepositorysExceptions(unittest.TestCase):
    def test_each_names_the_record_that_gives_its_reason(self):
        with open(os.path.join(ROOT, "ui", "audit-exceptions.json"), encoding="utf-8") as f:
            exceptions = json.load(f)
        self.assertEqual(set(exceptions), {GHSA}, "a new exception is an owner decision, recorded")
        for ghsa, entry in exceptions.items():
            with self.subTest(ghsa=ghsa):
                self.assertEqual(npm_audit.exception_problems(ghsa, entry), [])
                with open(os.path.join(ROOT, entry["record"]), encoding="utf-8") as f:
                    self.assertIn(ghsa, f.read())


if __name__ == "__main__":
    unittest.main()
