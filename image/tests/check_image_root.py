#!/usr/bin/env python3
"""Check an OS image's root filesystem against what the node relies on.

    check_image_root.py <root> --fedora <release>

<root> is the image's filesystem, mounted read-only (.github/workflows/image.yml
runs this on every build). Every finding is printed; any finding fails (exit 1).
Lessons register PLAT-01: the host is defined by the image, and an image test
asserts the shipped host configuration. Its tests (test_check_image_root.py) run
in the full gate on fixture roots, so no image or container runs on this machine.
Record: docs/build-records/2026-10-12-stage1-os-image.md

Paths are always read inside <root>: a link is never followed, since an absolute
one would point into the machine running the check, not into the image.
"""
from __future__ import annotations

import argparse
import os
import re
import stat
import sys

GREENBOOT_BIN = "usr/libexec/greenboot/greenboot"
GREENBOOT_CONF = "etc/greenboot/greenboot.conf"
CHECK_DIRS = ("usr/lib/greenboot/check/required.d", "usr/lib/greenboot/check/wanted.d",
              "etc/greenboot/check/required.d", "etc/greenboot/check/wanted.d")

# The values the node relies on (owner, 2026-10-12). greenboot reads the file
# as INI and uses its defaults, silently, when it cannot; so the file is
# closed-world: only these keys, once each, outside any [section].
GREENBOOT_EXPECTED = {
    "GREENBOOT_MAX_BOOT_ATTEMPTS": "3",
    "DISABLED_HEALTHCHECKS": ["01_repository_dns_check.sh"],
}

# Where a private key must never be: the image is published, so anything in it
# is public. Only regular files up to this size are read.
SECRET_DIRS = ("etc", "root", "var", "usr/local", "opt")
SECRET_MAX_BYTES = 1 << 20
PRIVATE_KEY = re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
SSH_HOST_KEY = re.compile(r"^ssh_host_.*_key$")


def _regular(root: str, rel: str):
    """The full path if <root>/<rel> is a regular file reached without links, else None."""
    path = root
    for part in rel.split("/"):
        path = os.path.join(path, part)
        try:
            st = os.lstat(path)
        except OSError:
            return None
        if stat.S_ISLNK(st.st_mode):
            return None
    return path if stat.S_ISREG(st.st_mode) else None


def _read(root: str, rel: str):
    path = _regular(root, rel)
    if path is None:
        return None
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def check_os_release(root: str, release: str) -> list:
    text = _read(root, "usr/lib/os-release")
    if text is None:
        return ["usr/lib/os-release: missing, or not a regular file"]
    fields = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"')
    found = []
    for key, want in (("ID", "fedora"), ("VARIANT_ID", "iot"), ("VERSION_ID", release)):
        if fields.get(key) != want:
            found.append("usr/lib/os-release: %s is %r, expected %r"
                         % (key, fields.get(key), want))
    return found


def parse_greenboot_conf(text: str):
    """(values, problems): the file read the way the node relies on it."""
    values, problems = {}, []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("["):
            problems.append("line %d: a [section] header moves the keys after it "
                            "out of greenboot's reach" % n)
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if not m:
            problems.append("line %d: not KEY=VALUE (%r)" % (n, line))
            continue
        key, value = m.group(1), m.group(2).strip()
        if key not in GREENBOOT_EXPECTED:
            problems.append("line %d: unknown key %s" % (n, key))
            continue
        if key in values:
            problems.append("line %d: %s set twice" % (n, key))
            continue
        if key == "DISABLED_HEALTHCHECKS":
            # greenboot's own reading: "( "a" "b" )", split on spaces, quotes
            # trimmed; anything else is an empty list, with only a warning.
            if not (value.startswith("(") and value.endswith(")")):
                problems.append("line %d: DISABLED_HEALTHCHECKS is not ( \"name\" ... ); "
                                "greenboot would disable nothing" % n)
                continue
            value = [s.strip('"') for s in value[1:-1].split() if s.strip('"')]
        values[key] = value
    return values, problems


def check_greenboot(root: str) -> list:
    found = []
    if _regular(root, GREENBOOT_BIN) is None:
        found.append("%s: missing (greenboot is not installed)" % GREENBOOT_BIN)
    text = _read(root, GREENBOOT_CONF)
    if text is None:
        return found + ["%s: missing, or not a regular file" % GREENBOOT_CONF]
    values, problems = parse_greenboot_conf(text)
    found += ["%s: %s" % (GREENBOOT_CONF, p) for p in problems]
    for key, want in GREENBOOT_EXPECTED.items():
        if key in values and values[key] != want:
            found.append("%s: %s is %r, expected %r" % (GREENBOOT_CONF, key, values[key], want))
        elif key not in values and not problems:
            found.append("%s: %s is not set" % (GREENBOOT_CONF, key))
    # greenboot only warns about a disabled name it cannot find: a typo would
    # leave the check running. Each name must be a check the image has.
    for name in values.get("DISABLED_HEALTHCHECKS") or []:
        if not any(_regular(root, d + "/" + name) for d in CHECK_DIRS):
            found.append("%s: disabled check %r is in none of %s"
                         % (GREENBOOT_CONF, name, ", ".join(CHECK_DIRS)))
    return found


def check_no_private_keys(root: str) -> list:
    found = []
    for top in SECRET_DIRS:
        base = os.path.join(root, top)
        if _regular(root, top) is not None or not os.path.isdir(base) or os.path.islink(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames
                                 if not os.path.islink(os.path.join(dirpath, d)))
            for name in sorted(filenames):
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, root)
                try:
                    st = os.lstat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                if rel.startswith("etc/ssh/") and SSH_HOST_KEY.match(name):
                    found.append("%s: an SSH host key in the image (every node would share it)"
                                 % rel)
                    continue
                if st.st_size > SECRET_MAX_BYTES:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError as e:
                    found.append("%s: cannot be read (%s)" % (rel, e.strerror))
                    continue
                if PRIVATE_KEY.search(data):
                    found.append("%s: holds a private key (the image is public)" % rel)
    return found


def check_root(root: str, release: str) -> list:
    return (check_os_release(root, release) + check_greenboot(root)
            + check_no_private_keys(root))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root")
    ap.add_argument("--fedora", required=True, help="the Fedora release the image must be")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print("check_image_root: %s is not a folder" % args.root, file=sys.stderr)
        return 2
    found = check_root(args.root, args.fedora)
    for f in found:
        print("FAIL " + f)
    print("check_image_root: %d finding(s) in %s (Fedora %s expected)"
          % (len(found), args.root, args.fedora))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
