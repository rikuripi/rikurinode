#!/usr/bin/env python3
"""Warn when the weekly advisory audit's last success on main is stale or unknown (TEST-05).

Lesson of the previous repository (lessons register TEST-05, 2026-09-28): its
weekly audit lived on a non-default branch and never ran once, and CI was red
for seven weeks with nothing saying so. GitHub also disables a repository's
schedules after sixty days without activity, and sends no mail about it. So
the full gate asks GitHub for the completed runs of
.github/workflows/advisory-audit.yml on main that the schedule or a dispatch
started, and warns when the latest is not a success, when the latest success
is older than eight days, when there is none, or when it cannot tell (no
token, an HTTP error, an answer of the wrong shape). It never fails the gate:
a stale audit is not the pull request's fault, and the warning is the alarm
(threat model §6, S2). A warning is one line that names its cause.

Token: GITHUB_TOKEN or GH_TOKEN (CI's token, with actions: read; the
repository is private). Repository: GITHUB_REPOSITORY, or the origin remote.
Usage: advisory_audit_age.py   exit 0 always (2 on a usage error)
Run by scripts/quality/full-gate.sh, step 10.
Record: docs/build-records/2026-10-21-weekly-advisory-audit.md
"""
from __future__ import annotations

import http.client
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping, Optional, Sequence, Tuple

WORKFLOW = "advisory-audit.yml"
BRANCH = "main"
MAX_AGE = timedelta(days=8)
COUNTED_EVENTS = ("schedule", "workflow_dispatch")
API = "https://api.github.com"
TIMEOUT = 20  # seconds
USER_AGENT = "rikurinode-advisory-audit-age/1 (scripts/quality/advisory_audit_age.py)"
WARNING = "full-gate: warning: advisory audit: "
OK = "advisory-audit: ok: "
REMOTE_RE = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")

Fetch = Callable[[str, str], Tuple[int, object]]


def parse_remote(url: str) -> Optional[str]:
    """owner/name from a GitHub remote URL (https or ssh), or None."""
    m = REMOTE_RE.search(url.strip())
    return m.group(1) if m else None


def repository(env: Mapping[str, str], cwd: Optional[str] = None) -> Optional[str]:
    """GITHUB_REPOSITORY, or the origin remote's owner/name, or None."""
    named = env.get("GITHUB_REPOSITORY")
    if named:
        return named
    try:
        done = subprocess.run(["git", "remote", "get-url", "origin"], cwd=cwd, capture_output=True,
                              text=True, timeout=10, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_remote(done.stdout)


def fetch_runs(url: str, token: str) -> Tuple[int, object]:
    """(HTTP status, JSON body or None). Raises OSError when GitHub cannot be reached, ValueError on non-JSON."""
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None


def parse_time(text: str) -> datetime:
    """GitHub's ISO 8601 time with a Z suffix, as an aware datetime (Python 3.9's fromisoformat needs +00:00)."""
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    when = datetime.fromisoformat(text)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when


def judge(payload: object, now: datetime) -> Tuple[bool, str]:
    """(ok, message) for GitHub's list of the workflow's completed runs on the branch."""
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list):
        return False, "GitHub's answer has no workflow_runs list, so the last run is unknown"
    counted = [run for run in runs if isinstance(run, dict) and run.get("event") in COUNTED_EVENTS]
    if not counted:
        return False, "no completed scheduled or dispatched run of %s on %s" % (WORKFLOW, BRANCH)
    try:
        counted.sort(key=lambda run: parse_time(str(run.get("created_at"))), reverse=True)
    except ValueError:
        return False, "a run of %s has no readable created_at" % WORKFLOW
    latest = counted[0]
    when = parse_time(str(latest.get("created_at")))
    age = now - when
    label = "%s run of %s started %s (%s)" % (latest.get("event"), WORKFLOW, when.strftime("%Y-%m-%d %H:%M UTC"),
                                             latest.get("html_url") or "no url")
    if latest.get("conclusion") != "success":
        return False, "the latest %s concluded %s" % (label, latest.get("conclusion"))
    days = age.total_seconds() / 86400
    if age > MAX_AGE:
        return False, "the latest successful %s is %.2f days old, older than the %d-day limit" % (label, days, MAX_AGE.days)
    return True, "the latest successful %s is %.2f days old" % (label, days)


def main(argv: Optional[Sequence[str]] = None, env: Optional[Mapping[str, str]] = None, fetch: Fetch = fetch_runs,
         now: Optional[datetime] = None, out=None, err=None) -> int:
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    env = os.environ if env is None else env
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        print("usage: advisory_audit_age.py   (no arguments; GITHUB_TOKEN or GH_TOKEN; GITHUB_REPOSITORY or an origin remote)",
              file=err)
        return 2
    token = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if not token:
        print(WARNING + "no token (GITHUB_TOKEN or GH_TOKEN), so the last run was not checked", file=out)
        return 0
    repo = repository(env)
    if not repo:
        print(WARNING + "the repository is unknown (GITHUB_REPOSITORY unset, no GitHub origin), so the last run was not checked",
              file=out)
        return 0
    url = "%s/repos/%s/actions/workflows/%s/runs?branch=%s&status=completed&per_page=10" % (API, repo, WORKFLOW, BRANCH)
    try:
        status, payload = fetch(url, token)
    except (OSError, ValueError, http.client.HTTPException) as e:
        print(WARNING + "cannot read the runs of %s: %s" % (WORKFLOW, e), file=out)
        return 0
    if status != 200:
        print(WARNING + "HTTP %d from GitHub listing the runs of %s (401: the token is not valid; 403 or 404: it cannot read Actions, or the repository is unknown)" % (status, WORKFLOW), file=out)
        return 0
    ok, message = judge(payload, now or datetime.now(timezone.utc))
    print((OK if ok else WARNING) + message, file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
