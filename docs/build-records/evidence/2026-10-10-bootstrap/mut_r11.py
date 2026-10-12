"""Bootstrap round 11 mutants: each must turn a test red. The policy mutants
remove one form AGENTS.md lists that round 10's verifier found held by no test
(round 11 added claims for them); the wiring mutants undo one part of the
closed-world settings check. Run from the root of a scratch copy of the tree
(never the worktree) inside safe-run.sh, with Python -B. Every file is
restored and checked by sha256. A wiring mutant runs only the quality tests."""
import hashlib
import subprocess
import sys

GUARD = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
QUALITY = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "scripts/quality/tests", "-p", "test_*.py"]
REGEN = [sys.executable, "-B", "scripts/quality/guard_policy.py"]
GP, WI, CFG = "scripts/quality/guard_policy.py", "scripts/quality/check_guard_wiring.py", ".claude/hooks/guard-config.json"
M = [
    ("P1 a commit message from --file or -t a read", GP, r'''(?:-[A-Za-z]*[Ft]|--(?:fi|te)\w*))|git\s+grep\b"''',
     r'''(?:-[A-Za-z]*F))|git\s+grep\b"'''),
    ("P2 --symbolic-link in full a read", GP, r'''r"|(?:cp|install)\b(?![^|;&]*\s(?:-[A-Za-z]*[ls]|--(?:l|sy|st)\w*))"''',
     r'''r"|(?:cp|install)\b(?![^|;&]*\s(?:-[A-Za-z]*[ls]|--(?:l|sym\b|st)\w*))"'''),
    ("P3 rsync -T a read", GP, r'''r"|rsync\b(?![^|;&]*\s(?:-[A-Za-z]*[eT]|''', r'''r"|rsync\b(?![^|;&]*\s(?:-[A-Za-z]*e|'''),
    ("P4 rsync's temp, backup, partial, batch dirs a read", GP, r'''|log-f|te|backup-d|partial-d|write-b|only-w"''',
     r'''|log-f"'''),
    ("P5 rsync --copy-dest/--compare-dest a read", GP, r'''r"|copy-d|compare-d)\w*))"''', r'''r")\w*))"'''),
    ("P6 scp -F/-J a read", GP, r'''r"|scp\b(?![^|;&]*\s-[A-Za-z]*[SoFJ]))")''', r'''r"|scp\b(?![^|;&]*\s-[A-Za-z]*[So]))")'''),
    ("P7 nerdctl not a node tool", GP, r'''|docker|podman|nerdctl|lncli|bitcoin-cli''', r'''|docker|podman|lncli|bitcoin-cli'''),
    ("P8 podman-compose not a node tool", GP, r'''(?:docker-compose|podman-compose|docker|''', r'''(?:docker-compose|docker|'''),
    ("W1 any top-level key", WI, 'for k in sorted(set(settings) - TOP_KEYS)]', 'for k in []]'),
    ("W2 any hook event", WI, 'for event in sorted(set(hooks) - HOOK_EVENTS - {"PermissionRequest"}):', 'for event in []:'),
    ("W3 any PreToolUse entry key", WI, 'if isinstance(entry, dict) and set(entry) - ENTRY_KEYS:', 'if False:'),
    ("W4 any key on the guard's hook", WI, '            if extra:  # `if`', '            if False:  # `if`'),
    ("W5 a timeout up to 600 s", WI, 'not 1 <= timeout <= 10', 'not 1 <= timeout <= 600'),
    ("W6 a timeout of true", WI, 'if isinstance(timeout, bool) or not isinstance', 'if not isinstance'),
    ("W7 any permission mode", WI, 'if "defaultMode" in perms and perms["defaultMode"] not in MODES:', 'if False:'),
    ("W8 any environment variable", WI, 'if k not in ENV_NAMES and not ENV_WORDS.search(k)])', 'if False])'),
]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


files = (GP, WI, CFG)
orig = {p: open(p, "rb").read() for p in files}
before = {p: sha(p) for p in files}
for name, path, a, b in M:
    assert orig[path].decode().count(a) == 1, (name, orig[path].decode().count(a))
if "--check" in sys.argv[1:]:
    print(len(M), "mutants apply")
    sys.exit(0)
try:
    for name, path, a, b in M:
        src = orig[path].decode().replace(a, b)
        compile(src, path, "exec")
        with open(path, "w") as f:
            f.write(src)
        if path == GP:
            subprocess.run(REGEN, check=True)
            g = subprocess.run(GUARD, capture_output=True, text=True)
        else:
            g = subprocess.CompletedProcess([], 0, "", "")
        q = subprocess.run(QUALITY, capture_output=True, text=True, timeout=600)
        fails = sorted({l.split("(")[0].split(":", 1)[1].strip() for l in (g.stderr + q.stderr).splitlines()
                        if l.startswith(("FAIL:", "ERROR:"))})
        red = g.returncode or q.returncode
        print("%-50s %s %s" % (name, "RED  " if red else "GREEN", ", ".join(fails)), flush=True)
        for p in files:
            with open(p, "wb") as f:
                f.write(orig[p])
finally:
    for p in files:
        with open(p, "wb") as f:
            f.write(orig[p])
    assert {p: sha(p) for p in files} == before
print("restored, sha256 checked:", ", ".join("%s %s" % (p, before[p][:12]) for p in sorted(files)))
