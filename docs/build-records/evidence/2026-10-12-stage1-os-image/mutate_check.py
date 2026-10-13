"""Mutation run for image/tests/check_image_root.py (TEST-02: a check counts
only after it has been seen to fail). Each mutant weakens one check in a copy
of the checker; the tests must fail on every one.
    python3 mutate_check.py <repo root>      (run inside scripts/quality/safe-run.sh)
Record: docs/build-records/2026-10-12-stage1-os-image.md
"""
import os
import shutil
import subprocess
import sys
import tempfile

MUTANTS = [
    ("VARIANT_ID not checked", '("VARIANT_ID", "iot"), ', ""),
    ("links followed", "            st = os.lstat(path)\n        except OSError:\n            return None",
     "            st = os.stat(path)\n        except OSError:\n            return None"),
    ("[section] allowed", 'if line.startswith("["):', "if False:"),
    ("not KEY=VALUE allowed", "        if not m:\n            problems.append(\"line %d: not KEY=VALUE",
     "        if False:\n            problems.append(\"line %d: not KEY=VALUE"),
    ("unknown key allowed", "if key not in GREENBOOT_EXPECTED:", "if False:"),
    ("duplicate key allowed", "if key in values:", "if False:"),
    ("bash-array form not required", 'if not (value.startswith("(") and value.endswith(")")):', "if False:"),
    ("expected values not compared", "values[key] != want", "False"),
    ("missing key not reported", "elif key not in values and not problems:", "elif False:"),
    ("disabled names not looked up", 'for name in values.get("DISABLED_HEALTHCHECKS") or []:', "for name in []:"),
    ("SSH host key allowed", 'if rel.startswith("etc/ssh/") and SSH_HOST_KEY.match(name):', "if False:"),
    ("private key not matched", 'PRIVATE KEY-----")', 'PRIVATE KEY-----X")'),
    ("exit 0 on findings", "return 1 if found else 0", "return 0"),
    ("greenboot binary not required", "if _regular(root, GREENBOOT_BIN) is None:", "if False:"),
]


def main():
    repo = os.path.abspath(sys.argv[1])
    src = os.path.join(repo, "image")
    caught = 0
    for name, old, new in MUTANTS:
        tmp = tempfile.mkdtemp(prefix="mut-")
        try:
            shutil.copytree(src, os.path.join(tmp, "image"))
            path = os.path.join(tmp, "image", "tests", "check_image_root.py")
            text = open(path).read()
            if text.count(old) != 1:
                print("BROKEN  %-32s (pattern found %d times)" % (name, text.count(old)))
                continue
            open(path, "w").write(text.replace(old, new))
            r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s",
                                os.path.join(tmp, "image", "tests"), "-p", "test_*.py"],
                               capture_output=True, text=True)
            status = "CAUGHT" if r.returncode != 0 else "MISSED"
            caught += r.returncode != 0
            print("%-7s %s" % (status, name))
        finally:
            shutil.rmtree(tmp)
    print("%d of %d mutants caught" % (caught, len(MUTANTS)))
    return 0 if caught == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
