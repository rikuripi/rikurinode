"""Mutation run for image/check_image_root.py (TEST-02: a check counts
only after it has been seen to fail). Each mutant weakens one check in a copy
of the checker; the tests must fail on every one, and a mutant that could
only change a message is not in the set: allowing a `[section]` line leaves
it "not KEY=VALUE", a finding either way (verifier round 1). The set holds
the round's proposed mutants P1 to P9 and one per form the fix round added.
    python3 mutate_check.py <repo root>      (run inside scripts/quality/safe-run.sh)
Record: docs/build-records/2026-10-12-stage1-os-image.md
"""
import os
import shutil
import subprocess
import sys
import tempfile

DIRS = 'SECRET_DIRS = ("etc", "root", "var", "usr/local", "opt", "tmp", "boot")'
ABSENT = "elif key not in values and not problems:"
MUTANTS = [
    ("VARIANT_ID not checked", '("VARIANT_ID", "iot"), ', ""),
    ("links followed", "            st = os.lstat(path)\n        except OSError:\n            return None",
     "            st = os.stat(path)\n        except OSError:\n            return None"),
    ("P1 any file type accepted as regular",
     "return hit[0] if hit and stat.S_ISREG(hit[1].st_mode) else None", "return hit[0] if hit else None"),
    ("control bytes allowed", "        if not PRINTABLE_LINE.match(line):", "        if False:"),
    ("indented comment allowed", 'line.startswith(b"#")', 'line.lstrip().startswith(b"#")'),
    ("padded blank line allowed", 'if line == b"" or', 'if line.strip() == b"" or'),
    ("P8 not KEY=VALUE silently skipped",
     '            problems.append("line %d: not KEY=VALUE (%r); greenboot reads only an empty line, "',
     '            _ = ("line %d: not KEY=VALUE (%r); greenboot reads only an empty line, "'),
    ("unknown key allowed", "if key not in GREENBOOT_EXPECTED:", "if False:"),
    ("duplicate key allowed", "if key in values:", "if False:"),
    ("DISABLED_HEALTHCHECKS form not checked", "if not DISABLED_VALUE.match(value):", "if False:"),
    ("GREENBOOT_MAX_BOOT_ATTEMPTS form not checked", "if not ATTEMPTS_VALUE.match(value):", "if False:"),
    ("expected values not compared", "values[key] != want", "False"),
    ("missing key not reported", ABSENT, "elif False:"),
    ("P7 DISABLED_HEALTHCHECKS absence not reported", ABSENT,
     'elif key not in values and not problems and key != "DISABLED_HEALTHCHECKS":'),
    ("disabled names not looked up", 'for name in values.get("DISABLED_HEALTHCHECKS") or []:', "for name in []:"),
    ("greenboot binary not required", "if _regular(root, GREENBOOT_BIN) is None:", "if False:"),
    ("P2 top folder reached through a link walked", "        base = _dir(root, top)",
     "        base = os.path.join(root, top) if os.path.isdir(os.path.join(root, top)) else None"),
    ("P3 linked file in a scanned tree read",
     "                if not stat.S_ISREG(st.st_mode):\n                    continue\n",
     "                if False:\n                    continue\n"),
    ("P4 var not scanned", DIRS, 'SECRET_DIRS = ("etc", "root", "usr/local", "opt", "tmp", "boot")'),
    ("P5 usr/local and opt not scanned", DIRS, 'SECRET_DIRS = ("etc", "root", "var", "tmp", "boot")'),
    ("tmp and boot not scanned", DIRS, 'SECRET_DIRS = ("etc", "root", "var", "usr/local", "opt")'),
    ("P6 size cap 1 KiB", "SECRET_MAX_BYTES = 1 << 20", "SECRET_MAX_BYTES = 1 << 10"),
    ("P9 unreadable file not reported",
     '                    found.append("%s: cannot be read (%s)" % (rel, e.strerror))\n',
     "                    pass\n"),
    ("absent etc not reported", '            if top == "etc":\n', "            if False:\n"),
    ("empty etc not reported", '        if top == "etc" and read == 0:', "        if False:"),
    ("SSH host key allowed", 'if rel.startswith("etc/ssh/") and SSH_HOST_KEY.match(name):', "if False:"),
    ("Tor key name allowed", "if name == TOR_HS_KEY_NAME:", "if False:"),
    ("PEM private key not matched", 'PRIVATE KEY( BLOCK)?-----")', 'PRIVATE KEY( BLOCK)?-----X")'),
    ("PGP key block not matched", "PRIVATE KEY( BLOCK)?-----", "PRIVATE KEY-----"),
    ("age key not matched", 'rb"AGE-SECRET-KEY-1[A-Z0-9]+"', 'rb"AGE-SECRET-KEY-1X[A-Z0-9]+"'),
    ("Tor header not matched", "if data.startswith(TOR_SECRET_HEADER):", "if False:"),
    ("WireGuard key not matched",
     'if rel.startswith("etc/wireguard/") and WIREGUARD_PRIVATE_KEY.search(data):', "if False:"),
    ("exit 0 on findings", "return 1 if found else 0", "return 0"),
]


def main():
    repo = os.path.abspath(sys.argv[1])
    src = os.path.join(repo, "image")
    caught = 0
    for name, old, new in MUTANTS:
        tmp = tempfile.mkdtemp(prefix="mut-")
        try:
            shutil.copytree(src, os.path.join(tmp, "image"))
            path = os.path.join(tmp, "image", "check_image_root.py")
            text = open(path).read()
            if text.count(old) != 1:
                print("BROKEN  %-46s (pattern found %d times)" % (name, text.count(old)))
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
