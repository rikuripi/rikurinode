#!/usr/bin/env python3
"""Ask OSV about every locked crate and every pinned action; never call an error clean.

Lesson of the previous repository (lessons register SEC-06, 2026-09-28): its
audit read RustSec only while GitHub listed advisories it lacked, and it
printed "clean" and exited 0 with cargo missing from PATH. OSV merges RustSec
and GitHub's advisory database, so this is the second reader beside
cargo-deny, and its exit code tells clean (0), findings (1) and
could-not-audit (2) apart: an error, an unreadable input or an answer of the
wrong shape is never clean.

What it reads: control-plane/Cargo.lock (every [[package]] with a registry
source; workspace crates have none and are not asked; a crate from another
source is named and not asked, because OSV knows crates.io's versions, not a
git commit's), and every `uses:` in .github/workflows, which must be pinned
to a 40-hex commit with its version in the comment (`# vX.Y.Z`), because the
"GitHub Actions" ecosystem's advisories name versions, not commits. OSV
evaluates a crate's version itself; for the "GitHub Actions" ecosystem it
answers nothing to a version query (probe of 2026-10-21), so each action is
asked by package and its ranges are evaluated here.

The allow-list is cargo-deny's own: the ids in control-plane/deny.toml's
[advisories] ignore list, matched by id or by any alias (RUSTSEC, GHSA, CVE),
so both readers share one list with one reason per entry; an entry that
matches nothing is printed.

Usage: osv_audit.py [repo]   exit 0 clean, 1 findings, 2 could not audit
Run weekly by .github/workflows/advisory-audit.yml.
Record: docs/build-records/2026-10-21-weekly-advisory-audit.md
"""
from __future__ import annotations

import glob
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

OSV = "https://api.osv.dev/v1"
BATCH = 1000  # OSV's limit of queries per querybatch call
TIMEOUT = 30  # seconds per request
USER_AGENT = "rikurinode-osv-audit/1 (scripts/quality/osv_audit.py)"
LOCKFILE = os.path.join("control-plane", "Cargo.lock")
DENY = os.path.join("control-plane", "deny.toml")
WORKFLOWS = os.path.join(".github", "workflows")
CRATES = "crates.io"
ACTIONS = "GitHub Actions"
DEFAULT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")

ID_RE = re.compile(r"\b(RUSTSEC-\d{4}-\d{4}|GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}|CVE-\d{4}-\d{4,})\b")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)\s*(#.*)?$")
PIN_RE = re.compile(r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/[^@\s]*)?@([0-9a-f]{40})$")
VERSION_COMMENT_RE = re.compile(r"^#\s*v?(\d+(?:\.\d+)*)(?:\s|$)")
VERSION_RE = re.compile(r"^[vV]?(\d+(?:\.\d+)*)$")

Fetch = Callable[..., object]
Finding = Tuple[str, str, str, str]  # kind, name, version, advisory id


class CannotAudit(Exception):
    """A part of the audit could not be done. It is reported, never passed off as clean (SEC-06)."""


def fetch_json(url: str, body: Optional[dict] = None) -> object:
    """One HTTPS request to OSV (GET without a body, POST with one): its JSON answer, or CannotAudit."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
    except urllib.error.HTTPError as e:
        raise CannotAudit("HTTP %d from %s" % (e.code, url))
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        raise CannotAudit("cannot reach %s: %s" % (url, e))
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise CannotAudit("not JSON from %s" % url)


def locked_crates(lock_text: str) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str, str]]]:
    """Cargo.lock's packages: the registry ones as (name, version), the other sourced ones with their source."""
    registry: List[Tuple[str, str]] = []
    other: List[Tuple[str, str, str]] = []
    for block in re.split(r"(?m)^\[\[package\]\][ \t]*$", lock_text)[1:]:
        name = re.search(r'(?m)^name = "([^"]+)"', block)
        version = re.search(r'(?m)^version = "([^"]+)"', block)
        source = re.search(r'(?m)^source = "([^"]+)"', block)
        if not name or not version:
            raise CannotAudit("a [[package]] block in %s has no name or version" % LOCKFILE)
        if source is None:
            continue  # a workspace crate: unpublished, nothing to ask
        if source.group(1).startswith("registry+"):
            registry.append((name.group(1), version.group(1)))
        else:
            other.append((name.group(1), version.group(1), source.group(1)))
    return registry, other


def pinned_actions(paths: Iterable[str]) -> List[Tuple[str, str, str]]:
    """Every `uses:` as (action, version, file:line); refuses one not pinned to a commit with its version named."""
    found: List[Tuple[str, str, str]] = []
    for path in sorted(paths):
        with open(path, encoding="utf-8") as f:
            for number, line in enumerate(f, 1):
                m = USES_RE.match(line.rstrip("\n"))
                if not m:
                    continue
                reference, comment = m.group(1), m.group(2) or ""
                where = "%s:%d" % (path, number)
                pin = PIN_RE.match(reference)
                if not pin:
                    raise CannotAudit("%s: `uses: %s` is not pinned to a 40-hex commit" % (where, reference))
                version = VERSION_COMMENT_RE.match(comment)
                if not version:
                    raise CannotAudit("%s: `uses: %s` names no version in its comment (# vX.Y.Z)" % (where, reference))
                found.append((pin.group(1), version.group(1), where))
    return found


def version_tuple(text: str) -> Tuple[int, ...]:
    """A dotted numeric version, with or without a leading v, as a comparable tuple."""
    m = VERSION_RE.match(str(text).strip())
    if not m:
        raise CannotAudit("cannot compare version %r" % text)
    return tuple(int(part) for part in m.group(1).split("."))


def _in_range(events: Sequence[dict], wanted: Tuple[int, ...]) -> bool:
    """OSV's events in order: introduced opens an interval, fixed (exclusive) or last_affected (inclusive) closes it."""
    start: Optional[Tuple[int, ...]] = None
    for event in events:
        if "introduced" in event:
            start = version_tuple(event["introduced"])
        elif "fixed" in event:
            if start is not None and start <= wanted < version_tuple(event["fixed"]):
                return True
            start = None
        elif "last_affected" in event:
            if start is not None and start <= wanted <= version_tuple(event["last_affected"]):
                return True
            start = None
    return start is not None and start <= wanted


def affects(vuln: dict, action: str, version: str) -> bool:
    """Whether an OSV record names this action's version, by its ECOSYSTEM or SEMVER ranges or its version list."""
    wanted = version_tuple(version)
    hit = False
    for entry in vuln.get("affected", []) or []:
        package = entry.get("package", {}) or {}
        if package.get("ecosystem") != ACTIONS or str(package.get("name") or "").lower() != action.lower():
            continue
        evaluable = False
        for listed in entry.get("versions", []) or []:
            evaluable = True
            if VERSION_RE.match(str(listed).strip()) and version_tuple(listed) == wanted:
                hit = True
        for rng in entry.get("ranges", []) or []:
            if rng.get("type") not in ("ECOSYSTEM", "SEMVER"):
                continue  # a GIT range names commits, which a version cannot be placed in
            evaluable = True
            if _in_range(rng.get("events", []) or [], wanted):
                hit = True
        if not evaluable:
            raise CannotAudit("%s names %s without a version range this script can evaluate" % (vuln.get("id"), action))
    return hit


def ignored_ids(deny_text: str) -> List[str]:
    """The advisory ids inside deny.toml's [advisories] ignore list, in order, without duplicates."""
    section = re.search(r"(?ms)^\[advisories\][ \t]*$(.*?)(?=^\[|\Z)", deny_text)
    if not section:
        return []
    text = section.group(1)
    opening = re.search(r"(?m)^ignore\s*=\s*\[", text)
    if not opening:
        return []
    depth, i = 1, opening.end()
    while i < len(text) and depth:
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
        i += 1
    if depth:
        raise CannotAudit("%s: the ignore list's bracket is not closed" % DENY)
    body = re.sub(r"#[^\n]*", "", text[opening.end():i - 1])
    ids: List[str] = []
    for found in ID_RE.findall(body):
        if found not in ids:
            ids.append(found)
    return ids


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise CannotAudit("cannot read %s: %s" % (path, e))


def _id_of(vuln: object) -> str:
    vuln_id = vuln.get("id") if isinstance(vuln, dict) else None
    if not isinstance(vuln_id, str) or not vuln_id:
        raise CannotAudit("an advisory in OSV's answer has no id")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", vuln_id):
        raise CannotAudit("an advisory id of an unexpected form: %r" % vuln_id)
    return vuln_id


def audit(root: str, fetch: Fetch, out) -> Dict[str, int]:
    """Ask OSV and print each finding; the counts for the summary. Raises CannotAudit."""
    registry, other = locked_crates(_read(os.path.join(root, LOCKFILE)))
    workflow_files = glob.glob(os.path.join(root, WORKFLOWS, "*.yml")) + glob.glob(os.path.join(root, WORKFLOWS, "*.yaml"))
    if not workflow_files:
        raise CannotAudit("no workflow file under %s: the actions were read by nothing" % WORKFLOWS)
    actions = pinned_actions(workflow_files)
    ignore = ignored_ids(_read(os.path.join(root, DENY)))
    for name, version, source in other:
        print("osv-audit: not on crates.io, not asked: %s %s (%s)" % (name, version, source), file=out)

    found: List[Finding] = []
    for start in range(0, len(registry), BATCH):
        chunk = registry[start:start + BATCH]
        queries = [{"package": {"name": name, "ecosystem": CRATES}, "version": version} for name, version in chunk]
        answer = fetch(OSV + "/querybatch", {"queries": queries})
        results = answer.get("results") if isinstance(answer, dict) else None
        if not isinstance(results, list) or len(results) != len(chunk):
            raise CannotAudit("querybatch answered %s results for %d queries"
                              % (len(results) if isinstance(results, list) else "no", len(chunk)))
        for (name, version), result in zip(chunk, results):
            if not isinstance(result, dict):
                raise CannotAudit("querybatch's result for %s %s is not an object" % (name, version))
            if result.get("next_page_token"):
                raise CannotAudit("more than one page of advisories for %s %s" % (name, version))
            for vuln in result.get("vulns", []) or []:
                found.append(("crate", name, version, _id_of(vuln)))
    names = sorted({name for name, _version, _where in actions})
    records: Dict[str, List[dict]] = {}
    for name in names:  # one query per action; every pinned version of it is then placed in the ranges
        answer = fetch(OSV + "/query", {"package": {"name": name, "ecosystem": ACTIONS}})
        if not isinstance(answer, dict):
            raise CannotAudit("query's answer for %s is not an object" % name)
        records[name] = list(answer.get("vulns", []) or [])
        for vuln in records[name]:
            if not isinstance(vuln, dict):
                raise CannotAudit("an advisory for %s is not an object" % name)
    for name, version in sorted({(name, version) for name, version, _where in actions}):
        for vuln in records[name]:
            if affects(vuln, name, version):
                found.append(("action", name, version, _id_of(vuln)))

    reported = ignored = 0
    matched: List[str] = []
    for kind, name, version, vuln_id in sorted(set(found)):
        detail = fetch(OSV + "/vulns/" + vuln_id)
        if not isinstance(detail, dict):
            raise CannotAudit("the record of %s is not an object" % vuln_id)
        aliases = [str(a) for a in detail.get("aliases", []) or []]
        summary = str(detail.get("summary") or "").strip()
        line = "%s %s %s: %s (%s)%s" % (kind, name, version, vuln_id, ", ".join(aliases) or "no alias",
                                        ": " + summary if summary else "")
        hits = [entry for entry in ignore if entry == vuln_id or entry in aliases]
        if hits:
            ignored += 1
            matched.extend(hit for hit in hits if hit not in matched)
            print("osv-audit: ignored by deny.toml (%s): %s" % (", ".join(hits), line), file=out)
        else:
            reported += 1
            print("osv-audit: FINDING: %s" % line, file=out)
    for entry in ignore:
        if entry not in matched:
            print("osv-audit: ignore entry matched nothing: %s" % entry, file=out)
    return {"crates": len(registry), "actions": len(names), "pins": len(actions), "not_asked": len(other),
            "findings": reported, "ignored": ignored}


def main(argv: Optional[Sequence[str]] = None, fetch: Fetch = fetch_json, out=None, err=None) -> int:
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) > 1 or any(arg.startswith("-") for arg in argv):
        print("usage: osv_audit.py [repo]   exit 0 clean, 1 findings, 2 could not audit", file=err)
        return 2
    root = os.path.abspath(argv[0] if argv else DEFAULT_ROOT)
    try:
        counts = audit(root, fetch, out)
    except CannotAudit as e:
        print("osv-audit: could not audit: %s" % e, file=err)
        return 2
    verdict = "FINDINGS" if counts["findings"] else "clean"
    print("osv-audit: asked OSV about %d crates and %d actions (%d pins): %d findings, %d ignored, %d not asked -> %s"
          % (counts["crates"], counts["actions"], counts["pins"], counts["findings"], counts["ignored"],
             counts["not_asked"], verdict), file=out)
    return 1 if counts["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
