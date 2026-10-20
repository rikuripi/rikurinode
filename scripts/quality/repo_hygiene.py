#!/usr/bin/env python3
"""Refuse a tracked file that does not belong in the repository.

Owner, 2026-10-10: logs stay local, never in git. Neither do runtime state,
secrets, build output, models, large blobs or unpinned container images
(BUILD-PROCEDURE.md, Phase 0: secrets hygiene, version pinning). Secrets are
the guard's own list (.claude/hooks/guard-config.json), so the two never
drift. Reads the git INDEX — what a commit would contain — so the pre-commit
hook and CI judge the same thing. Never prints a file's contents.

Usage: repo_hygiene.py [repo]   exit 0 clean, 1 offenders listed, 2 cannot check
Record: docs/build-records/2026-10-10-bootstrap.md
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys

MAX_BYTES = 1024 * 1024
GUARD_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                            ".claude", "hooks", "guard-config.json")

LOG = "log file: logs stay local, never in git"
SECRET = "secret or credential"
STATE = "runtime state: it lives on the node, outside the repository"
BUILD = "build output or dependencies"
MODEL = "model file"
ARCHIVE = "archive"

# (reason, basename globs, folder names anywhere, folder names at the root).
# Runtime folders count only at the root, as in .gitignore: a source module
# may be called data, log or backups (verifier, round 1).
RULES = [
    (LOG, ["*.log", "*.log.*", "nohup.out"], [], ["logs", "log"]),
    (STATE, ["*.db", "*.db-wal", "*.db-shm", "*.db-journal", "*.db.bak*", "*.db.old*", "*.db.[0-9]*",
             "*.db.gz", "*.sqlite", "*.sqlite3",
             "*.pid", "*.sock", "core", "core.[0-9]*", "compose.lock",
             "peers.dat", "blk*.dat", "rev*.dat", "*.ldb", "mempool.dat", "fee_estimates.dat", "anchors.dat"],
     [], ["data", "backups", "run"]),
    (BUILD, ["*.pyc"], ["node_modules", "dist", "__pycache__", ".venv"], ["target"]),
    (MODEL, ["*.gguf", "*.safetensors"], [], []),
    (ARCHIVE, ["*.tar", "*.tar.*", "*.tgz", "*.zip", "*.7z"], [], []),
]
LOCAL_PATHS = [".claude/state/*", ".claude/settings.local.json"]
TEMPLATES = ["*.example", "*.sample", "*.template", "*.pub"]
# Test inputs may be logs, data, databases or archives — never secrets.
FIXTURE_DIRS = {"fixtures", "testdata"}
FIXTURE_EXEMPT = {LOG, STATE, ARCHIVE}


def _secret_globs():
    with open(GUARD_CONFIG) as f:
        cfg = json.load(f)
    allow = [g for g in cfg["secret_allow_globs"] if g != "settings.local.json"]  # refused as local state
    return [g.lower() for g in cfg["secret_globs"]], [g.lower() for g in allow + TEMPLATES]


SECRET_GLOBS, SECRET_ALLOW = _secret_globs()


def _match(name: str, globs: list) -> bool:
    return any(fnmatch.fnmatchcase(name, g) for g in globs)


def path_problems(path: str) -> list:
    if _match(path, LOCAL_PATHS):
        return ["local agent state"]
    segs = path.split("/")
    base, dirs = segs[-1].lower(), [d.lower() for d in segs[:-1]]
    in_fixtures = bool(FIXTURE_DIRS & set(dirs))
    found = []
    if _match(base, SECRET_GLOBS) and not _match(base, SECRET_ALLOW):
        found.append(SECRET)
    for reason, globs, anywhere, at_root in RULES:
        by_name = _match(base, globs) and not (in_fixtures and reason in FIXTURE_EXEMPT)
        # a fixtures folder inside a runtime folder is still runtime data
        if by_name or set(anywhere) & set(dirs) or (dirs and dirs[0] in at_root):
            found.append(reason)
    return found


# --- image pins -----------------------------------------------------------

_YAML = re.compile(r"\.ya?ml$")
_SERVICES = re.compile(r"(?m)^services:\s*(#.*)?$")  # any compose file, whatever its name
_QUADLET = re.compile(r"\.container$")
_CONTAINERFILE = re.compile(r"(^|/)(Containerfile|Dockerfile)[^/]*$")
_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::?-([^}]*))?\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def _resolve(ref: str, known: dict):
    """Substitute variables by their defaults (or known ARG values); None if one has none."""
    missing = []

    def sub(m):
        name = m.group(1) or m.group(3)
        default = m.group(2) if m.group(1) else None
        value = default if default else known.get(name)
        if not value:
            missing.append(name)
            return ""
        return value
    out = _VAR.sub(sub, ref)
    return None if missing else out


def _unpinned(image: str, known: dict = None):
    """Why an image reference is not pinned, or None."""
    ref = _resolve(image.strip().strip("'\""), known or {})
    if ref is None:
        return "a variable without a default decides the version"
    if "@sha256:" in ref:
        return None
    name = ref.rsplit("/", 1)[-1]  # a registry's port is not a tag
    if ":" not in name:
        return "no version tag"
    tag = name.rsplit(":", 1)[1]
    if not re.search(r"\d+\.\d+", tag):  # at least major.minor: "3", "20-alpine", "lts" float
        return "'%s' is a floating tag, not a version" % tag
    return None


def pin_problems(path: str, text: str) -> list:
    found = []
    is_compose = bool(_YAML.search(path) and _SERVICES.search(text))
    if is_compose or _QUADLET.search(path):
        key = r"^\s*Image\s*=\s*(.+)$" if _QUADLET.search(path) else r"^\s*image\s*:\s*(.+?)\s*(#.*)?$"
        for n, line in enumerate(text.splitlines(), 1):
            m = re.match(key, line)
            if m:
                why = _unpinned(m.group(1))
                if why:
                    found.append("line %d: image not pinned (%s)" % (n, why))
    elif _CONTAINERFILE.search(path):
        stages, args = set(), {}
        for n, line in enumerate(text.splitlines(), 1):
            a = re.match(r"^\s*ARG\s+([A-Za-z_][A-Za-z0-9_]*)(?:=(\S+))?", line, re.I)
            if a:
                args[a.group(1)] = (a.group(2) or "").strip("'\"")
                continue
            c = re.match(r"^\s*COPY\s+.*--from=(\S+)", line, re.I)
            if c:
                ref = c.group(1)
                if ref not in stages and not ref.isdigit():
                    why = _unpinned(ref, args)
                    if why:
                        found.append("line %d: COPY --from image not pinned (%s)" % (n, why))
                continue
            m = re.match(r"^\s*FROM\s+(?:--\S+\s+)*(\S+)(?:\s+AS\s+(\S+))?", line, re.I)
            if not m:
                continue
            ref, alias = m.group(1), m.group(2)
            if ref.lower() != "scratch" and ref not in stages:
                why = _unpinned(ref, args)
                if why:
                    found.append("line %d: base image not pinned (%s)" % (n, why))
            if alias:
                stages.add(alias)
    return found


def check_file(path: str, data: bytes, size: int) -> list:
    found = path_problems(path)
    if size > MAX_BYTES:
        found.append("large file (%d bytes > %d): keep it out of git" % (size, MAX_BYTES))
    if not found:
        found = pin_problems(path, data.decode("utf-8", "replace"))
    return found


def cargo_output(paths: list) -> list:
    """(path, reason) for every path inside a `target` folder beside a tracked
    Cargo.toml: that folder is Cargo's build output, wherever the workspace
    sits. A folder named target elsewhere (a module under src/) is left alone."""
    roots = {os.path.dirname(p) for p in paths if os.path.basename(p) == "Cargo.toml"}
    found = []
    for path in paths:
        segs = path.split("/")
        for i, seg in enumerate(segs[:-1]):
            if seg == "target" and "/".join(segs[:i]) in roots:
                found.append((path, BUILD))
                break
    return found


# --- the git index ----------------------------------------------------------

def tracked(repo: str):
    """(path, size, data) for every file in the index, data only for small files."""
    ls = subprocess.run(["git", "-C", repo, "ls-files", "-s", "-z"], capture_output=True)
    if ls.returncode != 0:
        raise RuntimeError(ls.stderr.decode().strip() or "git ls-files failed")
    entries = []
    for rec in ls.stdout.split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, sha = meta.split()[:2]
        if mode == b"160000":  # submodule: not a blob
            continue
        entries.append((path.decode(), sha.decode()))
    if not entries:
        return
    batch = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], capture_output=True,
                           input="".join(sha + "\n" for _, sha in entries).encode())
    if batch.returncode != 0:
        raise RuntimeError(batch.stderr.decode().strip() or "git cat-file failed")
    out, pos = batch.stdout, 0
    for path, _ in entries:
        header_end = out.index(b"\n", pos)
        header = out[pos:header_end].split()
        if len(header) != 3:
            raise RuntimeError("git object for %s is missing" % path)
        size = int(header[2])
        data = out[header_end + 1:header_end + 1 + size]
        pos = header_end + 1 + size + 1
        yield path, size, data if size <= MAX_BYTES else b""


def main(argv: list) -> int:
    repo = argv[1] if len(argv) > 1 else "."
    try:
        offenders, paths = [], []
        for p, size, data in tracked(repo):
            paths.append(p)
            offenders.extend((p, why) for why in check_file(p, data, size))
        offenders.extend(cargo_output(paths))
    except (RuntimeError, ValueError, OSError) as e:
        print("repo-hygiene: cannot check %s: %s" % (repo, e), file=sys.stderr)
        return 2
    for path, why in offenders:
        print("%s: %s" % (path, why))
    if offenders:
        print("repo-hygiene: %d problem(s). Logs, runtime state and secrets stay on the machine; "
              "pin every image." % len(offenders), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
