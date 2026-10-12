"""Round 3 mutants of the continuation fix (C5 pinned by a test after mut-cont6.out): each must turn a test red. Run from
the repository root inside safe-run.sh with Python -B; every file is restored
and checked by sha256."""
import hashlib
import subprocess
import sys

GUARD = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
REGEN = [sys.executable, "-B", "scripts/quality/guard_policy.py"]
G, GP, CFG = ".claude/hooks/guard.py", "scripts/quality/guard_policy.py", ".claude/hooks/guard-config.json"
M = [
    ("C1 a trailing backslash kept", G, 'if c == "\\\\" and quote != "\'" and not comment and i + 1 == len(cmd):',
     'if False:'),
    ("C2 no budget check between rules", G, '''    for p in cfg["funds_patterns"]:
        _tick()
        if re.search(p["regex"], seg):''', '''    for p in cfg["funds_patterns"]:
        if re.search(p["regex"], seg):'''),
    ("C3 the previous guard always inline", G, 'and hasattr(os, "fork"):', 'and False:'),
    ("C4 a looser overall budget", G, "OVERALL_TIME_BUDGET = 7.0", "OVERALL_TIME_BUDGET = 30.0"),
    ("C5 a stopped child counts as allow", G, '''        if got is None:
            return ("ask", ["this command is too complex for the guard to check within its time — owner approves"])''',
     '''        if got is None:
            got = (("allow", []), [])'''),
    ("C6 the child's answer ignored", G, "        base, base_relaxed = got", "        base, base_relaxed = (\"allow\", []), []"),
    ("P1 \\\\n with no indentation", GP, r'r"\\n[ \t]*" + SUDO + r"(?:\S*/)?" + CONTINUED', r'r"\\n" + SUDO + r"(?:\S*/)?" + CONTINUED'),
]


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


files = (G, GP, CFG)
orig = {p: open(p, "rb").read() for p in files}
before = {p: sha(p) for p in files}
for name, path, a, b in M:
    assert orig[path].decode().count(a) == 1, (name, orig[path].decode().count(a))
if "--check" in sys.argv:
    print(len(M), "mutants apply")
    sys.exit(0)
ONLY = [a for a in sys.argv[1:] if not a.startswith("--")]
try:
    for name, path, a, b in M:
        if ONLY and name.split()[0] not in ONLY:
            continue
        src = orig[path].decode().replace(a, b)
        compile(src, path, "exec")
        open(path, "w").write(src)
        if path == GP:
            subprocess.run(REGEN, check=True)
        r = subprocess.run(GUARD, capture_output=True, text=True, timeout=900)
        fails = sorted({l.split("(")[0].split(":", 1)[1].strip() for l in r.stderr.splitlines()
                        if l.startswith(("FAIL:", "ERROR:"))})
        print("%-40s %s %s" % (name, "RED  " if r.returncode else "GREEN", ", ".join(fails)), flush=True)
        for p in files:
            open(p, "wb").write(orig[p])
finally:
    for p in files:
        open(p, "wb").write(orig[p])
    assert {p: sha(p) for p in files} == before
print("restored, sha256 checked")
