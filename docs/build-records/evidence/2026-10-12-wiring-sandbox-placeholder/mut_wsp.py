"""Mutants of check_guard_wiring.py's placeholder fix, run against the repository's
own test_guard_wiring.py: each version is loaded in memory as the module the
tests import; nothing on disk changes. Run from the repository root.
Record: docs/build-records/2026-10-12-wiring-sandbox-placeholder.md (mutants.out
came from an earlier version of this runner, mutants2.out from one that read the
old check from HEAD; mutants3.out from round 2's list, mutants4.out from round
3's; this one names its commits)."""
import contextlib
import importlib.util
import os
import subprocess
import sys
import unittest

SRC_PATH = "scripts/quality/check_guard_wiring.py"
SRC = open(SRC_PATH).read()
OLD = [("M0 before this change (17a19d5)", "17a19d5"), ("M0b the first fix, stat (5c06300)", "5c06300"),
       ("M0c round 2, lstat (8cfb268)", "8cfb268"), ("M0d the fix under the lock (62c102b)", "62c102b")]
IS_NULL = "return stat.S_ISCHR(here.st_mode) and here.st_rdev == DEV_NULL"
NOTE = "print(\"%s is /dev/null (the sandbox's placeholder): no local settings\" % LOCAL)"
FLAGS = "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK"
MUTANTS = [
    ("M1 isfile for lexists", "elif os.path.lexists(LOCAL):", "elif os.path.isfile(LOCAL):"),
    ("M2 any character device", IS_NULL, "return stat.S_ISCHR(here.st_mode)"),
    ("M3 everything is /dev/null", IS_NULL, "return True"),
    ("M4 silent fallback", NOTE, "pass"),
    ("M5 a missing path is /dev/null", "    except OSError:\n        return False", "    except OSError:\n        return True"),
    ("M6 placeholder still read", "if is_dev_null(LOCAL):", "if False:"),
    ("V1 rdev only, no S_ISCHR", IS_NULL, "return here.st_rdev == DEV_NULL"),
    ("V2 stat follows links", "here = os.lstat(path)", "here = os.stat(path)"),
    ("K1 placeholder clears the project's findings", "if is_dev_null(LOCAL):\n",
     "if is_dev_null(LOCAL):\n            found = []\n"),
    ("K2 placeholder returns before the project check", "        found += problems(PROJECT)\n",
     "        if is_dev_null(LOCAL):\n            return 0\n        found += problems(PROJECT)\n"),
    ("K10 the note names only the path", NOTE, "print(LOCAL)"),
    ("K11 only FileNotFoundError excused", "    except OSError:\n        return False",
     "    except FileNotFoundError:\n        return False"),
    ("W1 the number read from /dev/null", IS_NULL,
     "return stat.S_ISCHR(here.st_mode) and here.st_rdev == os.stat(os.devnull).st_rdev"),
    ("R1 no link check before opening", "    if os.path.islink(path):\n", "    if False:\n"),
    ("R2 the open follows links", FLAGS, "os.O_RDONLY | os.O_NONBLOCK"),
    ("R3 the open waits on a FIFO", FLAGS, "os.O_RDONLY | os.O_NOFOLLOW"),
    ("R4 no regular-file check on the open file", "if not stat.S_ISREG(mode):", "if False:"),
    ("R5 exists for lexists", "elif os.path.lexists(LOCAL):", "elif os.path.exists(LOCAL):"),
    ("R6 read again by path, not the open file", "return problems(path, require_guard=False, opened=f)",
     "return problems(path, require_guard=False)"),
    ("X1 not regular narrowed to FIFO or folder", "if not stat.S_ISREG(mode):",
     "if stat.S_ISFIFO(mode) or stat.S_ISDIR(mode):"),
    ("X2 a Permission-denied open excused",
     "        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)\n    except OSError as e:",
     "        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)\n    except PermissionError:\n"
     "        return []\n    except OSError as e:"),
    ("V4 the note on stderr", NOTE, NOTE[:-1] + ", file=sys.stderr)"),
    ("V5 explicit paths excused too", "            found += problems(p)\n",
     "            found += [] if is_dev_null(p) else problems(p)\n"),
    ("V7 the project file excused too", "found += problems(PROJECT)",
     "found += [] if is_dev_null(PROJECT) else problems(PROJECT)"),
]


def run(src):
    spec = importlib.util.spec_from_loader("check_guard_wiring", loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(src, SRC_PATH, "exec"), mod.__dict__)
    sys.modules["check_guard_wiring"] = mod
    sys.modules.pop("test_guard_wiring", None)
    suite = unittest.defaultTestLoader.discover("scripts/quality/tests", pattern="test_guard_wiring.py")
    with open(os.devnull, "w") as null, contextlib.redirect_stderr(null), contextlib.redirect_stdout(null):
        result = unittest.TextTestRunner(stream=null, verbosity=0).run(suite)
    bad = [t.id().replace("test_guard_wiring.Wiring.", "") for t, _ in result.failures + result.errors]
    return result.testsRun, len(result.skipped), bad


def show(name, bad):
    print("%-36s %s %d failing%s%s" % (name, "RED     " if bad else "SURVIVED", len(bad), ": " if bad else "",
                                      "; ".join(bad[:3]) + (" …" if len(bad) > 3 else "")))


runs, skips, bad = run(SRC)
print("baseline: %d tests, %d skipped, %d failing %s" % (runs, skips, len(bad), bad))
for name, commit in OLD:
    show(name, run(subprocess.run(["git", "show", "%s:%s" % (commit, SRC_PATH)], capture_output=True, text=True,
                                  check=True).stdout)[2])
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, (name, SRC.count(old))
    show(name, run(SRC.replace(old, new))[2])
