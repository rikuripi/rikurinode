#!/usr/bin/env python3
"""Check that the AI-session guard really runs before every file and shell tool.

Reads the Claude Code settings as Claude Code does: hooks not disabled, the
exact guard command, on PreToolUse, covering every tool the guard judges, and
blocking the call if the guard times out or fails ("onFailure": "block" —
without it Claude Code lets the call through). And the OS sandbox around
every shell command (owner, 2026-10-11). Closed-world (round 10, after round
9's verifier found nine documented widenings passing a check that listed the
bad keys; round 11, after round 10's verifier found the rest open): the
project file's sandbox is exactly SANDBOX below and the local file sets none;
the settings hold only the top-level keys in TOP_KEYS (others may run a
command, load a plugin that brings hooks, or start MCP servers); the only hook
is the guard's own PreToolUse entry, with exactly its keys (`if`, `once`,
`async`, … change when it runs or whether its failure blocks) and a timeout,
required, a whole number of seconds from 1 to 10; no permission rule widens the
sandbox (Edit/Write rules are merged into its writable paths, WebFetch into its
domains, Read may re-open what it hides) and the permission mode is one of
MODES (the schema's other modes — bypassPermissions, dontAsk, auto — are
refused); and the environment
holds only the names in ENV_NAMES (PATH, LD_PRELOAD, BASH_ENV, … would change
what a command runs). Round 2's verifier: a text search for "guard.py" stayed
green with "disableAllHooks": true or a command that merely mentioned the
guard.

Usage: check_guard_wiring.py [settings.json …]   (default: .claude/settings.json,
and .claude/settings.local.json when present) — exit 0 wired, 1 not.
Record: docs/build-records/2026-10-10-bootstrap.md
"""
from __future__ import annotations

import json
import os
import re
import sys

GUARD = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/guard.py"'
TOOLS = {"Bash", "Read", "Edit", "Write", "MultiEdit", "NotebookEdit", "Grep"}
# The sandbox, exactly (Claude Code's settings reference, 2026-10-11). Only
# git's network commands leave it (SSH cannot use its proxy); each still passes
# the guard and the permission flow. .git/hooks, .git/config and the named
# .claude paths are the sandbox's own protected paths; the settings add the
# hook folder, and hide the previous checkout's secrets.
SANDBOX = {
    "enabled": True,
    "failIfUnavailable": True,
    "allowUnsandboxedCommands": False,
    "excludedCommands": ["git push *", "git fetch *", "git pull *"],
    "filesystem": {
        "denyWrite": ["./scripts/quality/hooks"],
        "denyRead": ["/home/junc/rikuri/rikurinode/.env", "/home/junc/rikuri/rikurinode/data", "/run/rikuri"],
    },
    "network": {"allowedDomains": ["github.com", "api.github.com", "*.githubusercontent.com"]},
}
PERMISSION_KEYS = {"allow", "deny", "ask", "defaultMode", "disableBypassPermissionsMode"}
WIDENING_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "WebFetch", "Read"}
ENV_WORDS = re.compile(r"SANDBOX|HOOK", re.IGNORECASE)
# Round 11 (round 10's verifier, from Claude Code 2.1.296's settings schema):
# closed-world beyond the sandbox block too. The top-level keys these settings
# may hold — any other may run a command (apiKeyHelper, statusLine, …), load a
# plugin that brings hooks, or start MCP servers whose tools the guard does not
# see; the guard's hook entry, exactly (`if`, `once`, `async`, … change when
# it runs or whether its failure blocks); the permission modes in MODES (the
# schema's others are refused); the environment variables that change
# no command (PATH, LD_PRELOAD,
# BASH_ENV, … would).
TOP_KEYS = {"$schema", "hooks", "permissions", "sandbox", "env", "disableAllHooks"}
HOOK_EVENTS = {"PreToolUse"}
ENTRY_KEYS = {"matcher", "hooks"}
GUARD_HOOK_KEYS = {"type", "command", "timeout", "onFailure"}
MODES = {"default", "manual", "acceptEdits", "plan"}  # manual: the schema's alias for default
ENV_NAMES = {"RUST_LOG", "RUST_BACKTRACE", "CARGO_TERM_COLOR", "CARGO_TERM_VERBOSE", "NO_COLOR", "TZ", "LANG", "LC_ALL"}


def _differences(where: str, want, got) -> list:
    """What differs between the expected and the found value, by key; lists
    compare as sets of their items, and true is not 1."""
    if isinstance(want, dict):
        if not isinstance(got, dict):
            return ["%s must be an object" % where]
        out = []
        for key in sorted(set(want) | set(got)):
            if key not in got:
                out.append("%s.%s is missing (want %s)" % (where, key, json.dumps(want[key])))
            elif key not in want:
                out.append("%s.%s is not part of this repository's sandbox" % (where, key))
            else:
                out += _differences("%s.%s" % (where, key), want[key], got[key])
        return out
    if isinstance(want, list):
        if not isinstance(got, list):
            return ["%s must be a list" % where]
        have = {json.dumps(x, sort_keys=True) for x in got}
        need = {json.dumps(x, sort_keys=True) for x in want}
        out = []
        if need - have:
            out.append("%s lacks %s" % (where, ", ".join(sorted(need - have))))
        if have - need:
            out.append("%s adds %s" % (where, ", ".join(sorted(have - need))))
        return out
    if json.dumps(want) != json.dumps(got):
        return ["%s must be %s" % (where, json.dumps(want))]
    return []


def sandbox_problems(path: str, settings: dict, full: bool) -> list:
    """`full`: the project file, which must set the sandbox up exactly; the
    local file may not set it at all."""
    if "sandbox" not in settings:
        return ["%s: no sandbox — shell commands run with the session's full access" % path] if full else []
    if not full:
        return ["%s: the local settings may not set the sandbox (only .claude/settings.json does)" % path]
    return ["%s: %s" % (path, d) for d in _differences("sandbox", SANDBOX, settings["sandbox"])]


def permission_problems(path: str, settings: dict) -> list:
    perms = settings.get("permissions")
    if perms is None:
        return []
    if not isinstance(perms, dict):
        return ["%s: permissions must be an object" % path]
    found = []
    if "additionalDirectories" in perms:
        found.append("%s: permissions.additionalDirectories gives sandboxed commands write access outside the "
                     "repository" % path)
    for key in sorted(set(perms) - PERMISSION_KEYS - {"additionalDirectories"}):
        found.append("%s: permissions.%s is not one this check knows to leave the sandbox alone" % (path, key))
    if "defaultMode" in perms and perms["defaultMode"] not in MODES:
        found.append("%s: permissions.defaultMode %s is not one this check allows (allowed: %s)"
                     % (path, json.dumps(perms["defaultMode"]), ", ".join(sorted(MODES))))
    for key in ("allow", "deny", "ask"):
        rules = perms.get(key, [])
        if not isinstance(rules, list) or not all(isinstance(r, str) for r in rules):
            found.append("%s: permissions.%s must be a list of rules" % (path, key))
            continue
        if key == "allow":
            for r in rules:
                if r.split("(", 1)[0].strip() in WIDENING_TOOLS:
                    found.append("%s: permissions.allow %s widens the sandbox (merged into its writable paths, "
                                 "readable paths or domains)" % (path, r))
    return found


def env_problems(path: str, settings: dict) -> list:
    env = settings.get("env")
    if env is None:
        return []
    if not isinstance(env, dict):
        return ["%s: env must be an object" % path]
    return (["%s: env.%s names the sandbox or hooks" % (path, k) for k in sorted(env) if ENV_WORDS.search(k)]
            + ["%s: env.%s is not one this check knows to change no command (allowed: %s)"
               % (path, k, ", ".join(sorted(ENV_NAMES))) for k in sorted(env)
               if k not in ENV_NAMES and not ENV_WORDS.search(k)])


def hook_problems(path: str, settings: dict, full: bool) -> tuple:
    """(problems, the tools the guard covers, whether a guard entry fails open)."""
    hooks = settings.get("hooks")
    if hooks is None:
        return [], set(), False
    if not isinstance(hooks, dict):
        return ["%s: hooks must be an object" % path], set(), False
    found, covered, open_on_failure = [], set(), False
    if hooks.get("PermissionRequest"):
        found.append("%s: a PermissionRequest hook could answer the guard's ask" % path)
    for event in sorted(set(hooks) - HOOK_EVENTS - {"PermissionRequest"}):
        found.append("%s: a %s hook runs a command outside the guard and the sandbox: only the guard's PreToolUse "
                     "hook is wired here" % (path, event))
    entries = hooks.get("PreToolUse")
    if entries is None:
        return found, covered, open_on_failure
    if not isinstance(entries, list):
        return found + ["%s: hooks.PreToolUse must be a list" % path], covered, open_on_failure
    if not full and entries:
        return found + ["%s: the local settings may not add a PreToolUse hook" % path], covered, open_on_failure
    for entry in entries:
        if isinstance(entry, dict) and set(entry) - ENTRY_KEYS:
            found.append("%s: a PreToolUse entry has keys the check does not know: %s"
                         % (path, ", ".join(sorted(set(entry) - ENTRY_KEYS))))
        inner = entry.get("hooks") if isinstance(entry, dict) else None
        if not isinstance(inner, list):
            found.append("%s: a PreToolUse entry has no list of hooks" % path)
            continue
        others = [h for h in inner if not (isinstance(h, dict) and h.get("type") == "command"
                                           and h.get("command") == GUARD)]
        if others:
            found.append("%s: another PreToolUse hook (%s) could change a tool call after the guard judged it"
                         % (path, ", ".join(json.dumps(h)[:60] for h in others)))
        guards = [h for h in inner if h not in others]
        if not guards:
            continue
        for h in guards:
            extra = sorted(set(h) - GUARD_HOOK_KEYS)
            if extra:  # `if`, `once`, `async`, … change when the guard runs, or whether its failure blocks
                found.append("%s: the guard's hook has keys the check does not know: %s" % (path, ", ".join(extra)))
            timeout = h.get("timeout")  # missing: Claude Code's own default, not shown to be 10 s or less
            if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 10:
                found.append("%s: the guard's timeout must be a whole number of seconds from 1 to 10 (it is %s)"
                             % (path, json.dumps(timeout)))
        if any(h.get("onFailure") != "block" for h in guards):
            open_on_failure = True  # counts for nothing: a slow or broken guard would allow
            continue
        matcher = entry.get("matcher", "")
        if not isinstance(matcher, str):
            found.append("%s: a PreToolUse matcher must be text" % path)
            continue
        covered |= TOOLS if matcher in ("", "*") else set(matcher.split("|"))
    return found, covered, open_on_failure


def problems(path: str, require_guard: bool = True) -> list:
    try:
        with open(path) as f:
            settings = json.load(f)
    except (OSError, ValueError) as e:
        return ["%s: cannot read the settings (%s)" % (path, e)]
    if not isinstance(settings, dict):
        return ["%s: the settings must be an object" % path]
    found = ["%s: %s is not a settings key this check knows to leave the guard and the sandbox alone" % (path, k)
             for k in sorted(set(settings) - TOP_KEYS)]
    if settings.get("disableAllHooks"):
        found.append("%s: disableAllHooks is set — no hook runs, the guard included" % path)
    found += sandbox_problems(path, settings, require_guard)
    found += permission_problems(path, settings)
    found += env_problems(path, settings)
    hook_found, covered, open_on_failure = hook_problems(path, settings, require_guard)
    found += hook_found
    if require_guard:
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
