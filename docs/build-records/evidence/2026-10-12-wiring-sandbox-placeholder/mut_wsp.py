"""Mutants of check_guard_wiring.py's placeholder fix, run against the repository's
own test_guard_wiring.py: each mutant is loaded in memory as the module the
tests import; nothing on disk changes. Run from the repository root."""
import contextlib
import importlib.util
import os
import sys
import unittest

SRC_PATH = "scripts/quality/check_guard_wiring.py"
SRC = open(SRC_PATH).read()
MUTANTS = [
    ("M1 isfile for exists", "elif os.path.exists(local):", "elif os.path.isfile(local):"),
    ("M2 any character device",
     "return stat.S_ISCHR(here.st_mode) and here.st_rdev == null.st_rdev", "return stat.S_ISCHR(here.st_mode)"),
    ("M3 everything is /dev/null",
     "return stat.S_ISCHR(here.st_mode) and here.st_rdev == null.st_rdev", "return True"),
    ("M4 silent fallback",
     "print(\"%s is /dev/null (the sandbox's placeholder for a missing file): no local settings\" % local)",
     "pass"),
    ("M5 a missing path is /dev/null", "    except OSError:\n        return False", "    except OSError:\n        return True"),
    ("M6 placeholder still read", "if is_dev_null(local):", "if False:"),
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


runs, skips, bad = run(SRC)
print("baseline: %d tests, %d skipped, %d failing %s" % (runs, skips, len(bad), bad))
import subprocess  # noqa: E402
OLD = subprocess.run(["git", "show", "HEAD:" + SRC_PATH], capture_output=True, text=True, check=True).stdout
runs, skips, bad = run(OLD)
print("%-32s %s  %d failing: %s" % ("M0 the old check (HEAD)", "RED     " if bad else "SURVIVED", len(bad),
                                    "; ".join(bad)))
for name, old, new in MUTANTS:
    assert SRC.count(old) == 1, (name, SRC.count(old))
    runs, skips, bad = run(SRC.replace(old, new))
    print("%-32s %s  %d failing: %s%s" % (name, "RED     " if bad else "SURVIVED", len(bad), "; ".join(bad[:3]),
                                          " …" if len(bad) > 3 else ""))
