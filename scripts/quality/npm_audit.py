#!/usr/bin/env python3
"""The setup pages' audit (5c.3a): reads `npm audit --json` (scripts/quality/ui.sh)
against ui/audit-exceptions.json.

It fails on:
- any advisory that is not a recorded exception;
- an exception that no longer matches what npm reports, or whose review date
  has passed;
- an exception that is missing its package, reason, review date or record;
- a report it cannot read: empty, not JSON, npm's own error (no audit
  fetched), another report version, or totals that disagree with the
  packages listed.

A pass names every exception it allowed, so an allowed advisory is never silent.
Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md
Usage: npm_audit.py AUDIT_JSON EXCEPTIONS_JSON [--today YYYY-MM-DD]
"""
import argparse
import json
import re
import sys
from datetime import date

GHSA = re.compile(r"/(GHSA(?:-[0-9a-z]{4}){3})$")
FIELDS = ("package", "why", "review_by", "record")


def exception_problems(ghsa, entry):
    """What is wrong with one recorded exception, or []."""
    if not GHSA.search("/" + str(ghsa)):
        return ["%r is not an advisory id" % (ghsa,)]
    if not isinstance(entry, dict):
        return ["%s: not an object" % ghsa]
    problems = ["%s: no %s" % (ghsa, f) for f in FIELDS
                if not isinstance(entry.get(f), str) or not entry[f].strip()]
    if not problems:
        try:
            date.fromisoformat(entry["review_by"])
        except ValueError:
            problems.append("%s: review_by %r is not a date" % (ghsa, entry["review_by"]))
    return problems


def advisories(report):
    """({ghsa: package}, problems) of a readable npm audit report (version 2)."""
    if not isinstance(report, dict):
        return None, ["the audit report is not a JSON object: npm printed no report"]
    if "error" in report:
        return None, ["npm could not audit: %s" % json.dumps(report["error"])[:300]]
    if report.get("auditReportVersion") != 2:
        return None, ["audit report version %r, not 2" % report.get("auditReportVersion")]
    vulns = report.get("vulnerabilities")
    if not isinstance(vulns, dict):
        return None, ["the audit report lists no vulnerabilities map"]
    try:
        total = report["metadata"]["vulnerabilities"]["total"]
    except (KeyError, TypeError):
        return None, ["the audit report has no totals"]
    if total != len(vulns):
        return None, ["the audit report's total (%r) is not the %d packages it lists" % (total, len(vulns))]
    found, problems = {}, []
    for name, vuln in sorted(vulns.items()):
        via = vuln.get("via") if isinstance(vuln, dict) else None
        if not isinstance(via, list) or not via:
            problems.append("%s: reported with no cause" % name)
            continue
        for cause in via:
            if isinstance(cause, str):
                if cause not in vulns:
                    problems.append("%s: through %r, which the report does not list" % (name, cause))
            elif isinstance(cause, dict):
                m = GHSA.search(str(cause.get("url", "")))
                if not m:
                    problems.append("%s: an advisory with no GHSA id (%s)" % (name, cause.get("url")))
                else:
                    found[m.group(1)] = str(cause.get("name", name))
            else:
                problems.append("%s: a cause npm does not print: %r" % (name, cause))
    return found, problems


def check(report, exceptions, today):
    """(ok, lines): whether the audit passes, and why."""
    found, problems = advisories(report)
    if found is None:
        return False, problems
    lines = list(problems)
    if not isinstance(exceptions, dict):
        return False, lines + ["the exceptions file is not a JSON object"]
    for ghsa, entry in sorted(exceptions.items()):
        lines += exception_problems(ghsa, entry)
    allowed = []
    for ghsa, package in sorted(found.items()):
        entry = exceptions.get(ghsa)
        if not isinstance(entry, dict) or exception_problems(ghsa, entry):
            lines.append("FAIL %s in %s: an advisory with no recorded exception" % (ghsa, package))
        elif entry["package"] != package:
            lines.append("FAIL %s: reported in %s, excepted for %s" % (ghsa, package, entry["package"]))
        elif date.fromisoformat(entry["review_by"]) < today:
            lines.append("FAIL %s in %s: its exception's review date %s has passed (%s)"
                         % (ghsa, package, entry["review_by"], entry["record"]))
        else:
            allowed.append("allowed %s in %s until %s: %s (%s)"
                           % (ghsa, package, entry["review_by"], entry["why"], entry["record"]))
    for ghsa in sorted(set(exceptions) - set(found)):
        lines.append("FAIL %s: excepted, but npm no longer reports it; remove the exception" % ghsa)
    ok = not lines
    return ok, (allowed + ["npm audit: %d advisories, all recorded exceptions" % len(found)] if ok
                else lines + allowed)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report")
    ap.add_argument("exceptions")
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    a = ap.parse_args(argv)
    try:
        with open(a.exceptions, encoding="utf-8") as f:
            exceptions = json.load(f)
    except (OSError, ValueError) as e:
        print("npm_audit: the exceptions file %s: %s" % (a.exceptions, e), file=sys.stderr)
        return 1
    try:
        with open(a.report, encoding="utf-8") as f:
            report = json.load(f)
    except (OSError, ValueError) as e:
        print("npm_audit: the audit report %s cannot be read (%s): npm printed no report" % (a.report, e),
              file=sys.stderr)
        return 1
    ok, lines = check(report, exceptions, a.today)
    for line in lines:
        print(("npm_audit: " + line), file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
