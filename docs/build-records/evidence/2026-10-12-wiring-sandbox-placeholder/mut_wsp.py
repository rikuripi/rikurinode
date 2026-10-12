"""Mutants of check_guard_wiring.py's placeholder fix, run against the repository's
own test_guard_wiring.py: each version is loaded in memory as the module the
tests import; nothing on disk changes. Run from the repository root.
Record: docs/build-records/2026-10-12-wiring-sandbox-placeholder.md (mutants.out
came from an earlier version of this runner, mutants2.out from one that read the
old check from HEAD; this one names its commits)."""
import contextlib
import importlib.util
import os
import subprocess
import sys
import unittest

SRC_PATH = "scripts/quality/check_guard_wiring.py"
SRC = open(SRC_PATH).read()
OLD = [("M0 before this change (17a19d5)", "17a19d5"), ("M0b the first fix, stat (5c06300)", "5c06300")]
MUTANTS = [
    ("M1 isfile for exists", "elif os.path.exists(LOCAL):", "elif os.path.isfile(LOCAL):"),
    ("M2 any character device",
     "return stat.S_ISCHR(here.st_mode) and here.st_rdev == null.st_rdev", "return stat.S_ISCHR(here.st_mode)"),
    ("M3 everything is /dev/null",
     "return stat.S_ISCHR(here.st_mode) and here.st_rdev == null.st_rdev", "return True"),
    ("M4 silent fallback",
     "print(\"%s is /dev/null (the sandbox's placeholder): no local settings\" % LOCAL)", "pass"),
    ("M5 a missing path is /dev/null", "    except OSError:\n        return False", "    except OSError:\n        return True"),
    ("M6 placeholder still read", "if is_dev_null(LOCAL):", "if False:"),
    ("V1 rdev only, no S_ISCHR",
     "return stat.S_ISCHR(here.st_mode) and here.st_rdev == null.st_rdev", "return here.st_rdev == null.st_rdev"),
    ("V2 stat follows links", "here, null = os.lstat(path), os.stat(os.devnull)",
     "here, null = os.stat(path), os.stat(os.devnull)"),
    ("V4 the note on stderr",
     "print(\"%s is /dev/null (the sandbox's placeholder): no local settings\" % LOCAL)",
     "print(\"%s is /dev/null (the sandbox's placeholder): no local settings\" % LOCAL, file=sys.stderr)"),
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
