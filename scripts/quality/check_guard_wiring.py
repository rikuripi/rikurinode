#!/usr/bin/env python3
"""Check that the AI-session guard really runs before every file and shell tool.

Reads the Claude Code settings as Claude Code does: hooks not disabled, the
exact guard command, on PreToolUse, covering every tool the guard judges, and
blocking the call if the guard times out or fails ("onFailure": "block" —
without it Claude Code lets the call through). And the OS sandbox around
every shell command (owner, 2026-10-11): on, refusing to start without
bubblewrap, no retry outside it, the hook folder write-protected, the previous
checkout's secrets unreadable, and nothing that widens it — in either file.
Round 2's verifier: a text search for "guard.py" stayed green with
"disableAllHooks": true or a command that merely mentioned the guard.

Usage: check_guard_wiring.py [settings.json …]   (default: .claude/settings.json,
and .claude/settings.local.json when present) — exit 0 wired, 1 not.
Record: docs/build-records/2026-10-10-bootstrap.md
"""
from __future__ import annotations

import json
import os
import sys

GUARD = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/guard.py"'
TOOLS = {"Bash", "Read", "Edit", "Write", "MultiEdit", "NotebookEdit", "Grep"}
# The sandbox (Claude Code's settings reference, 2026-10-11). The commands that
# may leave it: git's network commands (SSH cannot use the sandbox's proxy);
# each still passes the guard and the permission flow.
EXCLUDED_OK = {"git push *", "git fetch *", "git pull *"}
DENY_WRITE = {"./scripts/quality/hooks"}  # .git/hooks, .git/config and .claude: the sandbox's own protected paths
DENY_READ = {"/home/junc/rikuri/rikurinode/.env", "/home/junc/rikuri/rikurinode/data", "/run/rikuri"}
# each would let a sandboxed command write outside the repository, reach a
# socket (the Docker socket drives the live node) or a local port, or weaken it
WIDENING = [("filesystem", "allowWrite"), ("filesystem", "disabled"), ("network", "allowUnixSockets"),
            ("network", "allowAllUnixSockets"), ("network", "allowLocalBinding"), (None, "enableWeakerNestedSandbox"),
            (None, "enableWeakerNetworkIsolation")]


def sandbox_problems(path: str, settings: dict, full: bool) -> list:
    """`full`: the project settings must set the sandbox up; the local file may
    only leave it alone."""
    found, box = [], settings.get("sandbox")
    if (settings.get("permissions") or {}).get("additionalDirectories"):
        found.append("%s: permissions.additionalDirectories gives sandboxed commands write access outside the "
                     "repository" % path)
    if box is None:
        return found + (["%s: no sandbox — shell commands run with the session's full access" % path] if full else [])
    if not isinstance(box, dict):
        return found + ["%s: sandbox is not an object" % path]
    wanted = {"enabled": True, "failIfUnavailable": True, "allowUnsandboxedCommands": False}
    for key, value in wanted.items():
        if (full or key in box) and box.get(key) != value:
            found.append("%s: sandbox.%s must be %s" % (path, key, json.dumps(value)))
    for section, key in WIDENING:
        where = (box.get(section) or {}) if section else box
        if where.get(key):
            found.append("%s: sandbox.%s widens the sandbox" % (path, ".".join(x for x in (section, key) if x)))
    extra = set(box.get("excludedCommands") or []) - (EXCLUDED_OK if full else set())
    if extra:
        found.append("%s: sandbox.excludedCommands lets these run unsandboxed: %s" % (path, ", ".join(sorted(extra))))
    if full:
        fs = box.get("filesystem") or {}
        for want, key in ((DENY_WRITE, "denyWrite"), (DENY_READ, "denyRead")):
            missing = want - set(fs.get(key) or [])
            if missing:
                found.append("%s: sandbox.filesystem.%s lacks %s" % (path, key, ", ".join(sorted(missing))))
    return found


def problems(path: str, require_guard: bool = True) -> list:
    try:
        with open(path) as f:
            settings = json.load(f)
    except (OSError, ValueError) as e:
        return ["%s: cannot read the settings (%s)" % (path, e)]
    found = []
    if settings.get("disableAllHooks"):
        found.append("%s: disableAllHooks is set — no hook runs, the guard included" % path)
    found += sandbox_problems(path, settings, require_guard)
    if require_guard:
        covered, open_on_failure = set(), False
        for entry in (settings.get("hooks") or {}).get("PreToolUse") or []:
            guards = [h for h in entry.get("hooks") or [] if h.get("type") == "command" and h.get("command") == GUARD]
            if not guards:
                continue
            if any(h.get("onFailure") != "block" for h in guards):
                open_on_failure = True  # counts for nothing: a slow or broken guard would allow
                continue
            matcher = entry.get("matcher", "")
            covered |= TOOLS if matcher in ("", "*") else set(matcher.split("|"))
        if open_on_failure:
            found.append('%s: the guard lets a tool call through when it times out or fails — set "onFailure": '
                         '"block" (Claude Code 2.1.295 or later)' % path)
        missing = TOOLS - covered
        if missing:
            found.append("%s: the guard (%s) does not run before: %s" % (path, GUARD, ", ".join(sorted(missing))))
    return found


def main(argv: list) -> int:
    paths = argv[1:]
    found = []
    if paths:
        for p in paths:
            found += problems(p)
    else:
        found += problems(".claude/settings.json")
        if os.path.exists(".claude/settings.local.json"):  # may switch every hook, or the sandbox, off here
            found += problems(".claude/settings.local.json", require_guard=False)
    for line in found:
        print(line, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
