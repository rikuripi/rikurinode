"""Bootstrap round 12 mutants: each must turn a test red — the guard hook's
timeout required, and `manual` (the schema's alias for `default`) allowed.
Run from the root of a scratch copy of the tree (never the worktree) inside
safe-run.sh, with Python -B. Every file is restored and checked by sha256."""
import hashlib
import subprocess
import sys

GUARD = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
QUALITY = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "scripts/quality/tests", "-p", "test_*.py"]
REGEN = [sys.executable, "-B", "scripts/quality/guard_policy.py"]
GP, WI, CFG = "scripts/quality/guard_policy.py", "scripts/quality/check_guard_wiring.py", ".claude/hooks/guard-config.json"
M = [
    ("W9 a guard hook without a timeout passes", WI, 'timeout = h.get("timeout")  # missing',
     'timeout = h.get("timeout", 10)  # missing'),
    ("W10 manual refused", WI, 'MODES = {"default", "manual", "acceptEdits", "plan"}', 'MODES = {"default", "acceptEdits", "plan"}'),
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
