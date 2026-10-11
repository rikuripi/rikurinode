"""Mutants of the inline-test tripwire, against guard.py as it will be
committed. Run from the repository root inside safe-run.sh. Python runs with
-B (no bytecode cache: a same-size mutant's stale .pyc can outlive its
restore). The file is restored and checked by sha256. Round 2 adds U11-U15
and W7: the verifier's five surviving mutants and the round-1 decoding."""
import hashlib
import subprocess
import sys

GUARD_TESTS = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
G = ".claude/hooks/guard.py"
MARKER = r'r"^[ \t]*#\s*\[\s*cfg'
MUTANTS = [
    # uncovered_inline_tests (R1-R4)
    ("U1 a marker needs no rule",
     [("        if not any(reg is not None and len(reg) >= len(text) - m.start() for reg in regions):\n"
       "            out.append(rel)\n", "")]),
    ("U2 any rule counts, its glob ignored",
     [('for r in inline_rules(rel, cfg)]', 'for r in cfg.get("inline_tests", [])]')]),
    ("U3 a glob match is enough, starts_at ignored",
     [("if not any(reg is not None and len(reg) >= len(text) - m.start() for reg in regions):",
       "if not regions:")]),
    ("U4 a region anywhere is enough",
     [("reg is not None and len(reg) >= len(text) - m.start()", "reg is not None")]),
    ("U5 untracked files count",
     [('"ls-files", "-z", "--", "*.rs"', '"ls-files", "-z", "--cached", "--others", "--", "*.rs"')]),
    ("U6 git's environment passes through",
     [("capture_output=True, timeout=30, env=git_env())", "capture_output=True, timeout=30)")]),
    ("U7 a git failure is nothing found",
     [('        raise OSError("git ls-files in %s failed: %s" % (root, proc.stderr.decode(errors="replace")'
       '.strip()))', "        return []")]),
    ("U8 an unreadable file is skipped",
     [("        except (OSError, UnicodeDecodeError):\n            out.append(rel)\n            continue\n",
       "        except (OSError, UnicodeDecodeError):\n            continue\n")]),
    ("U9 the marker must start in column 0", [(MARKER, r'r"^#\s*\[\s*cfg')]),
    ("U10 a marker anywhere on a line", [(MARKER, r'r"#\s*\[\s*cfg')]),
    ("U11 a tab before the marker is not a marker", [(MARKER, r'r"^[ ]*#\s*\[\s*cfg')]),
    ("U12 no -z: git quotes unusual names",
     [('"ls-files", "-z", "--", "*.rs"', '"ls-files", "--", "*.rs"'),
      ('proc.stdout.split(b"\\0")', 'proc.stdout.split(b"\\n")')]),
    ("U13 the region need only reach the marker's end", [("len(text) - m.start()", "len(text) - m.end()")]),
    ("U14 names decoded strictly (round 1)", [("rel = os.fsdecode(raw)", "rel = raw.decode()")]),
    ("U15 names that are not ASCII skipped",
     [('for raw in filter(None, proc.stdout.split(b"\\0")):',
       'for raw in [r for r in proc.stdout.split(b"\\0") if r and r.isascii()]:')]),
    # fix-lock on (R5, R6)
    ("W1 the old message (inline tests always)",
     [('what = "test files, inline tests and baselines" if cfg.get("inline_tests") else "test files and baselines"',
       'what = "test files, inline tests and baselines"')]),
    ("W2 no warning for uncovered files", [("        if gaps:\n            more", "        if False:\n            more")]),
    ("W3 a failed check is silent",
     [('            print("WARNING: could not check for inline tests that no inline_tests rule covers: %s" % e,\n'
       '                  file=sys.stderr)\n            return 0', "            return 0")]),
    ("W4 uncovered files refuse the lock",
     [('", ".join(gaps[:10]), more), file=sys.stderr)\n        return 0',
       '", ".join(gaps[:10]), more), file=sys.stderr)\n            return 1\n        return 0')]),
    ("W5 the whole list, uncounted", [('", ".join(gaps[:10]), more)', '", ".join(gaps), "")')]),
    ("W6 a check error crashes fix-lock on",
     [('        except OSError as e:\n            print("WARNING: could not check',
       '        except ValueError as e:\n            print("WARNING: could not check')]),
    ("W7 an empty rule list claims inline tests",
     [('if cfg.get("inline_tests") else', 'if "inline_tests" in cfg else')]),
]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


orig = open(G, "rb").read()
before = sha(G)
rows = []
try:
    for name, subs in MUTANTS:
        src = orig.decode()
        for a, b in subs:
            assert src.count(a) == 1, (name, a, src.count(a))
            src = src.replace(a, b)
        with open(G, "w") as f:
            f.write(src)
        r = subprocess.run(GUARD_TESTS, capture_output=True, text=True)
        fails = sorted({line.split("(")[0].split(":", 1)[1].strip() for line in r.stderr.splitlines()
                        if line.startswith(("FAIL:", "ERROR:"))})
        rows.append("%-48s %s %s" % (name, "RED  " if r.returncode else "GREEN", ", ".join(fails)[:150]))
        with open(G, "wb") as f:
            f.write(orig)
finally:
    with open(G, "wb") as f:
        f.write(orig)
    assert sha(G) == before
print("\n".join(rows))
print("restored, sha256 checked: %s %s" % (G, before[:12]))
