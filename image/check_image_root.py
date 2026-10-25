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
with nothing read is a finding. In the image, `opt`, `usr/local` and `root`
should be links into `var` (ostree's layout) and show as skipped, their files
reached under `var`: CI's log on the real root shows whether they do.

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

A Quadlet health command is accepted in one form only, the exec form: a JSON
array of strings whose first is an absolute path, in printable ASCII. Podman
runs any other form through /bin/sh -c, which a shell-less image lacks, so the
unit never becomes ready and nothing says why. Every file in the unit folders
is read, and a link, a continuation line or a health option in PodmanArgs= is a
finding (docs/build-records/2026-10-25-healthcmd-exec-form.md).
"""
from __future__ import annotations

import argparse
import json
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
    "DISABLED_HEALTHCHECKS": ["01_repository_dns_check.sh", "01_update_platforms_check.sh"],
}
# D22 against greenboot-rs #219: before greenboot reads its rollback trigger, a
# check clears it when the update it names was never applied. The drop-in must
# run it with "-", so a failure of the check leaves greenboot's own behaviour.
# Record: docs/build-records/2026-10-22-d22-unapplied-update.md
UNAPPLIED_CHECK = "usr/libexec/rikuri/greenboot-unapplied-update"
UNAPPLIED_DROPIN = "usr/lib/systemd/system/greenboot-healthcheck.service.d/50-rikuri-unapplied-update.conf"
UNAPPLIED_EXEC = "ExecStartPre=-/" + UNAPPLIED_CHECK
# greenboot-rs #218: the rollback trigger runs at every shutdown only when its
# unit conflicts with and precedes final.target, whatever the /boot layout.
# Record: docs/build-records/2026-10-22-greenboot-218.md
TRIGGER_DROPIN = "usr/lib/systemd/system/greenboot-set-rollback-trigger.service.d/50-rikuri-run-at-shutdown.conf"
TRIGGER_LINES = ("Conflicts=final.target", "Before=final.target")
# Podman's containers range for UserNS=auto, kept at every boot
# (docs/build-records/2026-10-23-containers-subid.md).
SUBID_CHECK = "usr/libexec/rikuri/containers-subid"
SUBID_UNIT = "usr/lib/systemd/system/rikuri-containers-subid.service"
SUBID_WANTS = "usr/lib/systemd/system/sysinit.target.wants/rikuri-containers-subid.service"
# The unit as a closed world: systemd lets a later line replace a value, add a
# command or reset a list, so each key appears once, with this value (None: any),
# in its section, and nothing else does
# (docs/build-records/2026-10-24-subid-unit-checker-gaps.md).
SUBID_KEYS = {"[Unit]": {"Description": None, "DefaultDependencies": "no", "After": "local-fs.target",
                         "Before": "sysinit.target shutdown.target", "Conflicts": "shutdown.target"},
              "[Service]": {"Type": "oneshot", "RemainAfterExit": "yes", "ExecStart": "/" + SUBID_CHECK},
              "[Install]": {"WantedBy": "sysinit.target"}}
UNIT_KEY_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)=(.*)$")
# Each would override the unit on a node. systemd.unit(5), probed in systemd 259
# (docs/build-records/evidence/2026-10-24-subid-unit-checker-gaps/05-*): every unit
# folder an image can ship, a drop-in folder for the name and for each of its dash
# prefixes, and, outside /usr/lib (where the unit and Fedora's own every-service
# drop-ins live), the unit itself (a copy, or a link to /dev/null that masks it)
# and service.d.
SUBID_UNIT_DIRS = ("etc/systemd/system.control", "etc/systemd/system", "etc/systemd/system.attached",
                   "usr/local/lib/systemd/system", "usr/lib/systemd/system")


def _subid_overrides() -> tuple:
    name = os.path.basename(SUBID_UNIT)
    words = name[:-len(".service")].split("-")
    dropins = [name + ".d"] + ["-".join(words[:n]) + "-.service.d" for n in range(len(words) - 1, 0, -1)]
    paths = []
    for d in SUBID_UNIT_DIRS:
        paths += [d + "/" + x for x in dropins]
        if d != os.path.dirname(SUBID_UNIT):
            paths += [d + "/" + name, d + "/service.d"]
    return tuple(paths)


SUBID_OVERRIDES = _subid_overrides()
SUBID_TARGETS = ("../rikuri-containers-subid.service", "/" + SUBID_UNIT)
# greenboot's wanted check of it: logged at every boot, never a rollback, since
# no image can repair /etc (docs/build-records/2026-10-24-greenboot-subid-wanted.md).
SUBID_WANTED = "usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid"
# The one form of a line read alike by greenboot and this check (the docstring).
PRINTABLE_LINE = re.compile(rb"^[\x20-\x7e]*$")
# Quadlet's rootful unit folders an image can ship (podman-systemd.unit(5); /run is not in one).
QUADLET_DIRS = ("etc/containers/systemd", "usr/share/containers/systemd")
QUADLET_KEY_LINE = re.compile(r"^\s*([A-Za-z]+)\s*=(.*)$")
QUADLET_HEALTH_KEYS = ("healthcmd", "healthstartupcmd")
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


def check_unapplied_update(root: str) -> list:
    found = []
    path = _regular(root, UNAPPLIED_CHECK)
    if path is None:
        found.append("%s: missing, or not a regular file (an update never applied would roll "
                     "the node back, greenboot-rs #219)" % UNAPPLIED_CHECK)
    elif not os.lstat(path).st_mode & 0o111:
        found.append("%s: not executable" % UNAPPLIED_CHECK)
    text = _read(root, UNAPPLIED_DROPIN)
    if text is None:
        return found + ["%s: missing, or not a regular file" % UNAPPLIED_DROPIN]
    section, runs = None, False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line
        elif section == "[Service]" and line == UNAPPLIED_EXEC:
            runs = True
    if not runs:
        found.append("%s: does not run the check as greenboot's pre-step (expected the line %r "
                     "under [Service])" % (UNAPPLIED_DROPIN, UNAPPLIED_EXEC))
    return found


def check_trigger_at_shutdown(root: str) -> list:
    text = _read(root, TRIGGER_DROPIN)
    if text is None:
        return ["%s: missing, or not a regular file (on a layout without a /boot partition a broken "
                "update would never roll back, greenboot-rs #218)" % TRIGGER_DROPIN]
    section, seen = None, set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line
        elif section == "[Unit]" and line in TRIGGER_LINES:
            seen.add(line)
    missing = [line for line in TRIGGER_LINES if line not in seen]
    if missing:
        return ["%s: does not order greenboot's rollback trigger against shutdown (missing under "
                "[Unit]: %s)" % (TRIGGER_DROPIN, ", ".join(missing))]
    return []


def subid_unit_problems(data: bytes) -> list:
    """Why the unit is not exactly SUBID_KEYS, in the one line form read alike by
    systemd and this check; [] when it is."""
    problems, sections, seen, section = [], set(), set(), None
    for n, raw in enumerate(data.split(b"\n"), 1):
        if not PRINTABLE_LINE.match(raw):
            problems.append("line %d: outside printable ASCII" % n)
            continue
        line = raw.decode("ascii")
        if line == "" or line[0] in "#;":
            continue
        if line.endswith("\\"):
            problems.append("line %d: a continuation line" % n)
            continue
        if line in SUBID_KEYS:
            if line in sections:
                problems.append("line %d: %s a second time" % (n, line))
            sections.add(line)
            section = line
            continue
        m = UNIT_KEY_LINE.match(line)
        if not m:
            problems.append("line %d: not a section, a comment in column 0, or KEY=VALUE (%r)" % (n, line))
            continue
        key, value = m.groups()
        keys = SUBID_KEYS.get(section, {})
        if key not in keys:
            problems.append("line %d: %s= does not belong in %s" % (n, key, section or "no section"))
        elif (section, key) in seen:
            problems.append("line %d: %s= a second time; systemd would replace, add to or reset it" % (n, key))
        elif keys[key] is not None and value != keys[key]:
            problems.append("line %d: %s=%s, expected %s=%s" % (n, key, value, key, keys[key]))
        elif keys[key] is None and not value:
            problems.append("line %d: %s= is empty" % (n, key))
        seen.add((section, key))
    missing = ["%s=%s under %s" % (key, value or "...", section) for section, keys in SUBID_KEYS.items()
               for key, value in keys.items() if (section, key) not in seen]
    if missing:
        problems.append("does not run the check once, before sysinit.target, and stay active "
                        "(missing: %s)" % "; ".join(missing))
    return problems


def _override_problem(root: str, rel: str):
    """Why <root>/<rel> would override the unit, or None when nothing is there.
    A link on the way is a finding itself: on a node it may lead to a folder
    the checker's machine does not have (lexists alone would follow it here)."""
    path, parts = root, rel.split("/")
    for n, part in enumerate(parts, 1):
        path = os.path.join(path, part)
        if not os.path.lexists(path):
            return None
        if n < len(parts) and os.path.islink(path):
            return "reached through a link at %s; the image must not ship it" % "/".join(parts[:n])
    return "overrides the unit on every node; the image must not ship it"


def check_containers_subid(root: str) -> list:
    found = []
    path = _regular(root, SUBID_CHECK)
    if path is None:
        found.append("%s: missing, or not a regular file (containers with UserNS=auto would not "
                     "start)" % SUBID_CHECK)
    elif not os.lstat(path).st_mode & 0o111:
        found.append("%s: not executable" % SUBID_CHECK)
    data = _read_bytes(root, SUBID_UNIT)
    if data is None:
        found.append("%s: missing, or not a regular file" % SUBID_UNIT)
    else:
        found += ["%s: %s" % (SUBID_UNIT, p) for p in subid_unit_problems(data)]
    for rel in SUBID_OVERRIDES:
        problem = _override_problem(root, rel)
        if problem:
            found.append("%s: %s" % (rel, problem))
    wants = os.path.join(root, SUBID_WANTS)
    hit = _lstat_in(root, os.path.dirname(SUBID_WANTS))
    if hit is None or not os.path.islink(wants):
        found.append("%s: not a link, so the unit is not enabled" % SUBID_WANTS)
    elif os.readlink(wants) not in SUBID_TARGETS:
        found.append("%s: points to %s, not to the unit" % (SUBID_WANTS, os.readlink(wants)))
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


def check_subid_wanted(root: str) -> list:
    found = []
    path = _regular(root, SUBID_WANTED)
    if path is None:
        found.append("%s: missing, or not a regular file (a failed containers range would pass "
                     "greenboot in silence)" % SUBID_WANTED)
    elif not os.lstat(path).st_mode & 0o111:
        found.append("%s: not executable" % SUBID_WANTED)
    name = os.path.basename(SUBID_WANTED)
    for d in CHECK_DIRS:
        rel = d + "/" + name
        # lexists, not _lstat_in: greenboot follows a link, so a link there is a required check too.
        if d.endswith("/required.d") and os.path.lexists(os.path.join(root, rel)):
            found.append("%s: a required check; a failure would roll the node back, and no image "
                         "can repair /etc" % rel)
    return found


def _exec_form(line: bytes, value: str) -> bool:
    if not PRINTABLE_LINE.match(line):
        return False
    try:
        argv = json.loads(value)
    except ValueError:
        return False
    return (isinstance(argv, list) and len(argv) > 0 and all(isinstance(a, str) for a in argv)
            and argv[0].startswith("/"))


def quadlet_health_problems(data: bytes) -> list:
    """Each line of a file in Quadlet's folders that would let Podman run a health
    command through a shell, or that this one-line reading cannot vouch for."""
    problems = []
    for n, line in enumerate(data.split(b"\n"), 1):
        text = line.decode("utf-8", errors="replace").rstrip("\r")
        if text.rstrip().endswith("\\"):
            problems.append("line %d: a continuation line; Quadlet joins it to the next, and this "
                            "check reads one line at a time" % n)
            continue
        if text.lstrip()[:1] in ("", "#", ";", "["):
            continue
        m = QUADLET_KEY_LINE.match(text)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        if key.lower() in QUADLET_HEALTH_KEYS and not _exec_form(line, value):
            problems.append("line %d: %s= is not the exec form (a JSON array whose first item is an "
                            "absolute path); Podman would run it through /bin/sh -c, which a "
                            "shell-less image lacks" % (n, key))
        elif key.lower() == "podmanargs" and "health" in value.lower():
            problems.append("line %d: PodmanArgs= sets a health option; set it with HealthCmd= or "
                            "HealthStartupCmd= in the exec form" % n)
    return problems


def check_quadlet_health(root: str) -> list:
    found = []
    for d in QUADLET_DIRS:
        path, parts = root, d.split("/")
        for k, part in enumerate(parts, 1):
            path = os.path.join(path, part)
            if not os.path.lexists(path):
                break
            if os.path.islink(path):
                found.append("%s: a link; Quadlet follows it, and the image must not ship one in its unit "
                             "folders" % d if k == len(parts) else
                             "%s: reached through a link at %s" % (d, "/".join(parts[:k])))
                break
        else:
            if not os.path.isdir(path):
                found.append("%s: not a folder" % d)
                continue
            for top, dirs, files in os.walk(path):
                for name in sorted(dirs + files):
                    full = os.path.join(top, name)
                    rel = os.path.relpath(full, root).replace(os.sep, "/")
                    st = os.lstat(full)
                    if stat.S_ISLNK(st.st_mode):
                        found.append("%s: a link; Quadlet follows it, and the image must not ship one in "
                                     "its unit folders" % rel)
                    elif stat.S_ISREG(st.st_mode):
                        with open(full, "rb") as f:
                            found += ["%s: %s" % (rel, p) for p in quadlet_health_problems(f.read())]
                    elif not stat.S_ISDIR(st.st_mode):
                        found.append("%s: not a regular file" % rel)
    return found


def check_root(root: str, release: str, note=lambda line: None) -> list:
    return (check_os_release(root, release) + check_greenboot(root) + check_unapplied_update(root)
            + check_trigger_at_shutdown(root) + check_containers_subid(root) + check_subid_wanted(root)
            + check_quadlet_health(root) + check_no_private_keys(root, note))


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
