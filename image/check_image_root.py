#!/usr/bin/env python3
"""Check an OS image's root filesystem against what the node relies on.

    check_image_root.py <root> --fedora <release>

<root> is the image's filesystem, mounted read-only (.github/workflows/image.yml
runs this on every build). Every finding is printed; any finding fails (exit 1).
Lessons register PLAT-01: the host is defined by the image, and an image test
asserts the shipped host configuration. Its tests (tests/test_check_image_root.py)
run in the full gate on fixture roots, so no image or container runs on this
machine. Record: docs/build-records/2026-10-12-stage1-os-image.md

Paths are always read inside <root>, and a link in any component of a path ends
the read: an absolute link would point into the machine running the check, not
into the image. The key scan prints what it read per tree and which trees it
skipped (a link, absent), so an empty scan is visible in the CI log; an `etc`
with nothing read is a finding. In the image, `opt`, `usr/local` and `root` are
links into `var` (ostree's layout): they show as skipped, and their files are
reached under `var`.

greenboot.conf is accepted in one form only, the one greenboot's INI reader
(rust-ini, through the config crate) and this check read alike: printable ASCII
and newlines; a comment is `#` in column 0; a blank line is empty; a key line is
exactly `GREENBOOT_MAX_BOOT_ATTEMPTS=<digits>` or
`DISABLED_HEALTHCHECKS=("name" "name")` (or `=()`), one space between the quoted
names and no other whitespace. Anything else is a finding: greenboot reads an
indented comment, a control byte or a stray space differently (verifier round 1:
with the DNS check left on) and falls back to its defaults silently.

The key scan refuses, in etc, root, var, usr/local, opt, tmp and boot (regular
files up to SECRET_MAX_BYTES; a link is never read): a PEM private key
(`-----BEGIN … PRIVATE KEY-----`, PGP's `PRIVATE KEY BLOCK` included); an SSH
host key under etc/ssh, by name; a Tor onion service key by name
(`hs_ed25519_secret_key`) or any file with Tor's `== ed25519v1-secret` header;
an age secret key (`AGE-SECRET-KEY-1…`); a `PrivateKey =` line in a file under
etc/wireguard. Not scanned: Fedora's own files under /usr (they ship test keys);
the project's additions there are covered by the gate's secret scan.
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
# The one form of a line read alike by greenboot and this check (the docstring).
PRINTABLE_LINE = re.compile(rb"^[\x20-\x7e]*$")
KEY_LINE = re.compile(rb"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
ATTEMPTS_VALUE = re.compile(rb"^[0-9]+$")
DISABLED_VALUE = re.compile(rb'^\((?:"[A-Za-z0-9_.-]+"(?: "[A-Za-z0-9_.-]+")*)?\)$')

# Where a secret must never be: the image is published, so anything in it is
# public. Only regular files up to this size are read; the forms refused are
# in the docstring.
SECRET_DIRS = ("etc", "root", "var", "usr/local", "opt", "tmp", "boot")
SECRET_MAX_BYTES = 1 << 20
PRIVATE_KEY = re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY( BLOCK)?-----")
SSH_HOST_KEY = re.compile(r"^ssh_host_.*_key$")
TOR_HS_KEY_NAME = "hs_ed25519_secret_key"
TOR_SECRET_HEADER = b"== ed25519v1-secret"
AGE_SECRET_KEY = re.compile(rb"AGE-SECRET-KEY-1[A-Z0-9]+")
WIREGUARD_PRIVATE_KEY = re.compile(rb"(?m)^[ \t]*PrivateKey[ \t]*=[ \t]*\S")


def _lstat_in(root: str, rel: str):
    """(path, lstat) of <root>/<rel> if no component of rel is a link, else None."""
    path = root
    for part in rel.split("/"):
        path = os.path.join(path, part)
        try:
            st = os.lstat(path)
        except OSError:
            return None
        if stat.S_ISLNK(st.st_mode):
            return None
    return path, st


def _regular(root: str, rel: str):
    """The full path if <root>/<rel> is a regular file reached without links, else None."""
    hit = _lstat_in(root, rel)
    return hit[0] if hit and stat.S_ISREG(hit[1].st_mode) else None


def _dir(root: str, rel: str):
    """The full path if <root>/<rel> is a folder reached without links, else None."""
    hit = _lstat_in(root, rel)
    return hit[0] if hit and stat.S_ISDIR(hit[1].st_mode) else None


def _why_not_a_dir(root: str, rel: str) -> str:
    """Why _dir(root, rel) is None: absent, a link on the way, or not a folder."""
    path, done = root, []
    for part in rel.split("/"):
        path = os.path.join(path, part)
        done.append(part)
        try:
            st = os.lstat(path)
        except OSError:
            return "absent"
        if stat.S_ISLNK(st.st_mode):
            return "%s is a link to %s" % ("/".join(done), os.readlink(path))
    return "%s is not a folder" % rel


def _read_bytes(root: str, rel: str):
    path = _regular(root, rel)
    if path is None:
        return None
    with open(path, "rb") as f:
        return f.read()


def _read(root: str, rel: str):
    data = _read_bytes(root, rel)
    return None if data is None else data.decode("utf-8", errors="replace")


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


def parse_greenboot_conf(data: bytes):
    """(values, problems): the file read in the one form greenboot and this
    check read alike (the docstring); every other line is a problem."""
    values, problems = {}, []
    lines = data.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()  # the final newline
    for n, line in enumerate(lines, 1):
        if not PRINTABLE_LINE.match(line):
            seen = []
            for b in line:
                if not 0x20 <= b <= 0x7e and b not in seen:
                    seen.append(b)
            problems.append("line %d: %s %s outside printable ASCII; greenboot's INI reader "
                            "does not read such a line as this check does"
                            % (n, "byte" if len(seen) == 1 else "bytes",
                               " ".join("0x%02x" % b for b in seen)))
            continue
        if line == b"" or line.startswith(b"#"):
            continue  # a blank line is empty; a comment starts in column 0
        text = line.decode("ascii")
        if text.startswith("["):
            problems.append("line %d: a [section] header moves the keys after it "
                            "out of greenboot's reach" % n)
            continue
        m = KEY_LINE.match(line)
        if not m:
            problems.append("line %d: not KEY=VALUE (%r); greenboot reads only an empty line, "
                            "a comment from column 0 and KEY=VALUE as this check does" % (n, text))
            continue
        key, value = m.group(1).decode("ascii"), m.group(2)
        if key not in GREENBOOT_EXPECTED:
            problems.append("line %d: unknown key %s" % (n, key))
            continue
        if key in values:
            problems.append("line %d: %s set twice" % (n, key))
            continue
        if key == "DISABLED_HEALTHCHECKS":
            if not DISABLED_VALUE.match(value):
                problems.append('line %d: DISABLED_HEALTHCHECKS is not exactly ("name" "name" ...) '
                                "or () (%r); greenboot would disable nothing, or not what this "
                                "check reads" % (n, value.decode("ascii")))
                continue
            values[key] = [s.strip('"') for s in value[1:-1].decode("ascii").split()]
        else:
            if not ATTEMPTS_VALUE.match(value):
                problems.append("line %d: GREENBOOT_MAX_BOOT_ATTEMPTS is not digits only (%r)"
                                % (n, value.decode("ascii")))
                continue
            values[key] = value.decode("ascii")
    return values, problems


def check_greenboot(root: str) -> list:
    found = []
    if _regular(root, GREENBOOT_BIN) is None:
        found.append("%s: missing (greenboot is not installed)" % GREENBOOT_BIN)
    data = _read_bytes(root, GREENBOOT_CONF)
    if data is None:
        return found + ["%s: missing, or not a regular file" % GREENBOOT_CONF]
    values, problems = parse_greenboot_conf(data)
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


def secret_forms(rel: str, data: bytes) -> list:
    """Why a file's contents may not be in a public image, if they may not."""
    found = []
    if PRIVATE_KEY.search(data):
        found.append("%s: holds a private key (the image is public)" % rel)
    if AGE_SECRET_KEY.search(data):
        found.append("%s: holds an age secret key" % rel)
    if data.startswith(TOR_SECRET_HEADER):
        found.append("%s: a Tor ed25519 secret key (by its header)" % rel)
    if rel.startswith("etc/wireguard/") and WIREGUARD_PRIVATE_KEY.search(data):
        found.append("%s: holds a WireGuard private key" % rel)
    return found


def check_no_private_keys(root: str, note=lambda line: None) -> list:
    """Findings; `note` gets one line per tree: what was read, or why it was skipped."""
    found = []
    for top in SECRET_DIRS:
        base = _dir(root, top)
        if base is None:
            why = _why_not_a_dir(root, top)
            note("scan %s: skipped (%s)" % (top, why))
            if top == "etc":
                found.append("etc: skipped (%s); the key scan is vacuous" % why)
            continue
        read = over = 0
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
                if name == TOR_HS_KEY_NAME:
                    found.append("%s: a Tor onion service's secret key (by its name)" % rel)
                    continue
                if st.st_size > SECRET_MAX_BYTES:
                    over += 1
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError as e:
                    found.append("%s: cannot be read (%s)" % (rel, e.strerror))
                    continue
                read += 1
                found += secret_forms(rel, data)
        note("scan %s: %d file(s) read%s" % (top, read, ", %d over the size cap (%d bytes) not read"
                                              % (over, SECRET_MAX_BYTES) if over else ""))
        if top == "etc" and read == 0:
            found.append("etc: no regular file was read; the key scan is vacuous")
    return found


def check_root(root: str, release: str, note=lambda line: None) -> list:
    return (check_os_release(root, release) + check_greenboot(root)
            + check_no_private_keys(root, note))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root")
    ap.add_argument("--fedora", required=True, help="the Fedora release the image must be")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print("check_image_root: %s is not a folder" % args.root, file=sys.stderr)
        return 2
    found = check_root(args.root, args.fedora, note=print)
    for f in found:
        print("FAIL " + f)
    print("check_image_root: %d finding(s) in %s (Fedora %s expected)"
          % (len(found), args.root, args.fedora))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
