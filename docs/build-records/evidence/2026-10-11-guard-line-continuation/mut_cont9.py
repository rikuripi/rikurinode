"""Round 3 mutants of the continuation fix, on the final design (a timer, no
child process): each must turn a test red. Run from the repository root inside
safe-run.sh with Python -B; every file is restored and checked by sha256.
Earlier sets: mut_cont6.py (C5 survived), mut_cont8.py (C2, C3, T3 survived:
the timer made the per-rule check and the child process redundant, and both
were removed)."""
import hashlib
import subprocess
import sys

GUARD = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
REGEN = [sys.executable, "-B", "scripts/quality/guard_policy.py"]
G, GP, CFG = ".claude/hooks/guard.py", "scripts/quality/guard_policy.py", ".claude/hooks/guard-config.json"
M = [
    ("C1 a trailing backslash kept", G, 'if c == "\\\\" and quote != "\'" and not comment and i + 1 == len(cmd):',
     'if False:'),
    ("C4 a looser overall budget", G, "OVERALL_TIME_BUDGET = 7.0", "OVERALL_TIME_BUDGET = 30.0"),
    ("C5 the previous guard's time-out gives the new checks' answer", G, """    if got is None:
        return TOO_SLOW
    chosen, chosen_relaxed = got""", """    if got is None:
        got = (new, new_relaxed)
    chosen, chosen_relaxed = got"""),
    ("C6 the previous guard's answer ignored", G,
     "        base = base_decide(event, cfg, root, lock_present=lock_present, branch_fn=branch_fn, relaxed=base_relaxed)",
     "        base = (\"allow\", [])"),
    ("N1 out-of-time new checks allow", G, "        new, new_relaxed = TOO_SLOW, []", "        new, new_relaxed = (\"allow\", []), []"),
    ("P1 \\\\n with no indentation", GP, r'r"\\n[ \t]*" + SUDO + r"(?:\S*/)?" + CONTINUED', r'r"\\n" + SUDO + r"(?:\S*/)?" + CONTINUED'),
    ("T1 no timer on the new checks", G, "        new = _timed(_DEADLINE_ALL - time.time(), lambda: _decide_new(",
     "        new = (lambda f: f())(lambda: _decide_new("),
    ("T2 no timer on the previous guard", G,
     "    got = _timed(_DEADLINE_ALL - CHECK_TIME_BUDGET + OVERALL_TIME_BUDGET - time.time(), finish)",
     "    got = finish()"),
    ("T3 the timer's exception an Exception", G, "class _OutOfTime(BaseException):", "class _OutOfTime(Exception):"),
    ("T4 a timer firing in its disarm escapes", G, """    except _OutOfTime:
        disarm()
        return None""", """    except ZeroDivisionError:
        disarm()
        return None"""),
    ("T5 no backstop in run_hook", G, "    except _OutOfTime:  # decide() catches", "    except ZeroDivisionError:  # decide() catches"),
    ("T6 the new checks' timer ten times later", G, "        new = _timed(_DEADLINE_ALL - time.time(), lambda",
     "        new = _timed(_DEADLINE_ALL - time.time() + 9 * CHECK_TIME_BUDGET, lambda"),
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
