"""Tests of check_image_root.py on fixture roots: a good root passes, and each
way the node could silently lose what it relies on fails. The committed
greenboot.conf is checked as shipped. Run by the full gate (step 3).
Record: docs/build-records/2026-10-12-stage1-os-image.md; its verifier round
1 found F1 (the file read differently from greenboot), F2 (a link followed),
F3 (a vacuous scan), F4 (key forms not covered) and F5 (mutants missed).
"""
import contextlib
import errno
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import check_image_root as cir  # noqa: E402

SHIPPED_CONF = os.path.join(HERE, "..", "rootfs", "etc", "greenboot", "greenboot.conf")
# D22 against greenboot-rs #219 (docs/build-records/2026-10-22-d22-unapplied-update.md).
UNAPPLIED_CHECK = "usr/libexec/rikuri/greenboot-unapplied-update"
UNAPPLIED_DROPIN = "usr/lib/systemd/system/greenboot-healthcheck.service.d/50-rikuri-unapplied-update.conf"
# greenboot-rs #218 (docs/build-records/2026-10-22-greenboot-218.md).
TRIGGER_DROPIN = "usr/lib/systemd/system/greenboot-set-rollback-trigger.service.d/50-rikuri-run-at-shutdown.conf"
# The containers range for UserNS=auto (docs/build-records/2026-10-23-containers-subid.md).
SUBID_CHECK = "usr/libexec/rikuri/containers-subid"
SUBID_UNIT = "usr/lib/systemd/system/rikuri-containers-subid.service"
SUBID_WANTS = "usr/lib/systemd/system/sysinit.target.wants/rikuri-containers-subid.service"
# greenboot's wanted check of it (docs/build-records/2026-10-24-greenboot-subid-wanted.md).
SUBID_WANTED = "usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid"


def shipped_file(rel) -> bytes:
    with open(os.path.join(HERE, "..", "rootfs", rel), "rb") as f:
        return f.read()


def shipped() -> bytes:
    with open(SHIPPED_CONF, "rb") as f:
        return f.read()


def pem(kind, body="AAAA\n", end=True, block=""):
    """A fake PEM block, assembled here so that no key-shaped text sits in the
    source (the pre-commit secret scan refuses it, rightly)."""
    label = kind + " KEY" + block + "-----"
    text = "-----BEGIN " + label + "\n" + body
    return text + ("-----END " + label + "\n" if end else "")


def age_key():
    """An age identity's secret line, assembled like pem()."""
    return "AGE-SECRET-" + "KEY-1" + "Q" * 58 + "\n"


TOR_SECRET_HEADER = b"== ed25519v1-secret: type0 ==\x00\x00\x00"

OS_RELEASE = """NAME="Fedora Linux"
VERSION="44 (IoT Edition)"
ID=fedora
VERSION_ID=44
VARIANT="IoT Edition"
VARIANT_ID=iot
"""

A = "GREENBOOT_MAX_BOOT_ATTEMPTS=3"
D = 'DISABLED_HEALTHCHECKS=("01_repository_dns_check.sh")'


def probe_cases():
    """Verifier round 1's greenboot.conf cases (verify/ini-probe/make_cases.py)
    with what greenboot 0.16.4 reads from each: its config reader, rust-ini
    0.21.3, built into a probe and run on them (verify/ini-probe/probe, 2026-10-12).
    "disabled=[]" leaves Fedora's DNS check on, against D9. The checker accepts
    only the one form both read alike, so every case here must be a finding."""
    s = shipped().decode("ascii")
    return [
        ("02-fedora-default", A + "\n\nDISABLED_HEALTHCHECKS=()\n", "disabled=[]"),
        ("03-indented-comment-space", A + "\n  # the DNS check is off (owner)\n" + D + "\n",
         "disabled=[]: the comment and the next line became one key"),
        ("04-indented-comment-tab", A + "\n\t# the DNS check is off\n" + D + "\n",
         "disabled=[]: the comment and the next line became one key"),
        ("05-indented-comment-with-colon", A + "\n  # owner: off\n" + D + "\n",
         "as shipped, by luck: the comment became a key named '# owner'"),
        ("06-shipped-comment-indented",
         s.replace("# The node's own required checks replace it.",
                   "  # The node's own required checks replace it."),
         "INI parse error, so greenboot's defaults: disabled=[]"),
        ("07-vt-after-comment", A + "\n# note\x0b" + D + "\n", "disabled=[]: the key was swallowed"),
        ("08-ff-after-value", A + "\n" + D + "\x0c# note\n", "disabled=[]"),
        ("09-x1f-trailing", A + "\n" + D + "\x1f\n", "disabled=[]"),
        ("10-crlf-shipped", s.replace("\n", "\r\n"), "as shipped"),
        ("11-spaces-inside-array", A + '\nDISABLED_HEALTHCHECKS=( "01_repository_dns_check.sh" )\n',
         "as shipped"),
        ("12-inline-comment", A + " # three\n" + D + "\n",
         "disabled as shipped; the attempts value does not parse, so its default (3)"),
        ("13-spaces-around-equals", A + '\nDISABLED_HEALTHCHECKS = ("01_repository_dns_check.sh")\n',
         "as shipped"),
        ("14-nel-after-comment", A + "\n# note\x85" + D + "\n", "disabled=[]: the key was swallowed"),
        ("15-leading-ff-before-comment", A + "\n\x0c# note\n" + D + "\n",
         "INI parse error, so greenboot's defaults: disabled=[]"),
    ]


class Root:
    """A fixture root shaped like the image: what the check reads, nothing more."""

    def __init__(self):
        self.path = tempfile.mkdtemp(prefix="image-root-")
        self.write("usr/lib/os-release", OS_RELEASE)
        self.write(cir.GREENBOOT_BIN, "#!/bin/sh\n", mode=0o755)
        self.write("usr/lib/greenboot/check/required.d/01_repository_dns_check.sh",
                   "#!/bin/sh\n", mode=0o755)
        self.write("usr/lib/greenboot/check/required.d/02_watchdog.sh", "#!/bin/sh\n", mode=0o755)
        self.write_bytes(cir.GREENBOOT_CONF, shipped())
        self.write_bytes(UNAPPLIED_CHECK, shipped_file(UNAPPLIED_CHECK), mode=0o755)
        self.write_bytes(UNAPPLIED_DROPIN, shipped_file(UNAPPLIED_DROPIN))
        if os.path.exists(os.path.join(HERE, "..", "rootfs", TRIGGER_DROPIN)):
            self.write_bytes(TRIGGER_DROPIN, shipped_file(TRIGGER_DROPIN))
        if os.path.exists(os.path.join(HERE, "..", "rootfs", SUBID_UNIT)):
            self.write_bytes(SUBID_CHECK, shipped_file(SUBID_CHECK), mode=0o755)
            self.write_bytes(SUBID_UNIT, shipped_file(SUBID_UNIT))
            self.link(SUBID_WANTS, "../rikuri-containers-subid.service")
        if os.path.exists(os.path.join(HERE, "..", "rootfs", SUBID_WANTED)):
            self.write_bytes(SUBID_WANTED, shipped_file(SUBID_WANTED), mode=0o755)
        self.write("etc/ssh/sshd_config", "PermitRootLogin no\n")

    def _fresh(self, rel):
        p = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if os.path.lexists(p):
            os.remove(p)
        return p

    def write(self, rel, text, mode=0o644):
        self.write_bytes(rel, text.encode("utf-8"), mode)

    def write_bytes(self, rel, data, mode=0o644):
        p = self._fresh(rel)
        with open(p, "wb") as f:
            f.write(data)
        os.chmod(p, mode)

    def link(self, rel, target):
        os.symlink(target, self._fresh(rel))

    def remove(self, rel):
        os.remove(os.path.join(self.path, rel))

    def check(self, release="44"):
        return cir.check_root(self.path, release)

    def check_with_notes(self, release="44"):
        """(findings, the scan's notes): what main() prints before the findings."""
        notes = []
        return cir.check_root(self.path, release, note=notes.append), notes

    def cleanup(self):
        shutil.rmtree(self.path)


class CheckImageRoot(unittest.TestCase):
    def setUp(self):
        self.root = Root()
        self.addCleanup(self.root.cleanup)

    def assertFinds(self, fragment, found=None):
        if found is None:
            found = self.root.check()
        self.assertTrue(any(fragment in f for f in found),
                        "expected a finding with %r, got %r" % (fragment, found))

    def outside_with_key(self, sub=""):
        """A folder outside the root, standing for the machine that runs the
        check, holding a private key the check must never reach."""
        outside = tempfile.mkdtemp(prefix="outside-")
        self.addCleanup(shutil.rmtree, outside)
        p = os.path.join(outside, sub, "host-only.key")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(pem("PRIVATE"))
        return outside

    def test_good_root_passes(self):
        self.assertEqual(self.root.check(), [])

    def test_main_exit_codes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            self.assertEqual(cir.main([self.root.path, "--fedora", "44"]), 0)
            self.assertEqual(cir.main([self.root.path, "--fedora", "45"]), 1)
            self.assertEqual(cir.main([os.path.join(self.root.path, "nope"), "--fedora", "44"]), 2)
        self.assertIn("FAIL usr/lib/os-release: VERSION_ID is '44', expected '45'", out.getvalue())
        # F3: the scan says what it read, so an empty scan is visible in the CI log.
        self.assertIn("scan etc: 2 file(s) read", out.getvalue())

    # --- the release ---------------------------------------------------------
    def test_wrong_release(self):
        self.assertTrue(any("VERSION_ID is '44', expected '45'" in f
                            for f in self.root.check(release="45")))

    def test_generic_bootc_base_is_not_iot(self):
        self.root.write("usr/lib/os-release", OS_RELEASE.replace("VARIANT_ID=iot\n", ""))
        self.assertFinds("VARIANT_ID is None, expected 'iot'")

    def test_not_fedora(self):
        self.root.write("usr/lib/os-release", OS_RELEASE.replace("ID=fedora", "ID=centos"))
        self.assertFinds("ID is 'centos', expected 'fedora'")

    def test_os_release_missing(self):
        self.root.remove("usr/lib/os-release")
        self.assertFinds("usr/lib/os-release: missing")

    def test_os_release_link_is_not_followed(self):
        # An absolute link would read the machine running the check.
        self.root.link("usr/lib/os-release", "/usr/lib/os-release")
        self.assertFinds("usr/lib/os-release: missing, or not a regular file")

    # --- greenboot -----------------------------------------------------------
    def test_greenboot_not_installed(self):
        self.root.remove(cir.GREENBOOT_BIN)
        self.assertFinds("greenboot is not installed")

    def test_conf_missing(self):
        self.root.remove(cir.GREENBOOT_CONF)
        self.assertFinds("greenboot.conf: missing")

    def test_a_folder_where_a_file_is_expected(self):
        # F5 (P1): a folder (or a device, a FIFO) is not a regular file.
        for rel, fragment in ((cir.GREENBOOT_BIN, "greenboot is not installed"),
                              ("usr/lib/os-release", "usr/lib/os-release: missing, or not a regular file")):
            with self.subTest(path=rel):
                self.root.remove(rel)
                os.makedirs(os.path.join(self.root.path, rel))
                self.assertFinds(fragment)

    # --- the check that keeps an unapplied update from rolling a node back --
    def test_unapplied_check_missing(self):
        self.root.remove(UNAPPLIED_CHECK)
        self.assertFinds(UNAPPLIED_CHECK + ": missing")

    def test_unapplied_check_not_executable(self):
        self.root.write_bytes(UNAPPLIED_CHECK, shipped_file(UNAPPLIED_CHECK), mode=0o644)
        self.assertFinds(UNAPPLIED_CHECK + ": not executable")

    def test_unapplied_check_as_link_does_not_count(self):
        self.root.link(UNAPPLIED_CHECK, "/bin/true")
        self.assertFinds(UNAPPLIED_CHECK + ": missing")

    def test_dropin_missing(self):
        self.root.remove(UNAPPLIED_DROPIN)
        self.assertFinds(UNAPPLIED_DROPIN + ": missing")

    def test_dropin_must_run_the_check(self):
        for text, why in (("[Service]\n", "no ExecStartPre"),
                          ("[Service]\nExecStartPre=/usr/libexec/rikuri/greenboot-unapplied-update\n",
                           "without '-', a crash of the check would fail greenboot"),
                          ("[Unit]\nExecStartPre=-/usr/libexec/rikuri/greenboot-unapplied-update\n",
                           "outside [Service]"),
                          ("[Service]\nExecStartPre=-/usr/libexec/rikuri/other\n", "another program")):
            with self.subTest(why=why):
                self.root.write(UNAPPLIED_DROPIN, text)
                self.assertFinds(UNAPPLIED_DROPIN + ": does not run")

    # --- the rollback trigger runs at every shutdown (#218) -----------------
    def test_trigger_dropin_missing(self):
        self.root.remove(TRIGGER_DROPIN)
        self.assertFinds(TRIGGER_DROPIN + ": missing")

    def test_trigger_dropin_as_link_does_not_count(self):
        self.root.link(TRIGGER_DROPIN, "/dev/null")
        self.assertFinds(TRIGGER_DROPIN + ": missing")

    def test_trigger_dropin_must_conflict_with_and_precede_final_target(self):
        for text, why in (("[Unit]\nConflicts=final.target\n", "no Before="),
                          ("[Unit]\nBefore=final.target\n", "no Conflicts="),
                          ("[Service]\nConflicts=final.target\nBefore=final.target\n", "outside [Unit]"),
                          ("[Unit]\nConflicts=shutdown.target\nBefore=shutdown.target\n", "another target"),
                          ("[Unit]\n# Conflicts=final.target\n# Before=final.target\n", "commented out")):
            with self.subTest(why=why):
                self.root.write(TRIGGER_DROPIN, text)
                self.assertFinds(TRIGGER_DROPIN + ": does not order")

    # --- the containers range is kept at every boot (UserNS=auto) ------------
    def test_shipped_subid_files_pass(self):
        self.assertEqual(cir.check_containers_subid(self.root.path), [])

    def test_subid_check_missing_or_not_executable(self):
        self.root.remove(SUBID_CHECK)
        self.assertFinds(SUBID_CHECK + ": missing")
        self.root.write_bytes(SUBID_CHECK, shipped_file(SUBID_CHECK), mode=0o644)
        self.assertFinds(SUBID_CHECK + ": not executable")
        self.root.link(SUBID_CHECK, "/bin/true")
        self.assertFinds(SUBID_CHECK + ": missing")

    def test_subid_wanted_check_must_be_there_and_executable(self):
        # Verified against the shipped file: the fixture copies it when it exists.
        self.assertEqual(cir.check_subid_wanted(self.root.path), [])
        self.root.remove(SUBID_WANTED)
        self.assertFinds(SUBID_WANTED + ": missing")
        self.root.write_bytes(SUBID_WANTED, shipped_file(SUBID_WANTED), mode=0o644)
        self.assertFinds(SUBID_WANTED + ": not executable")
        self.root.link(SUBID_WANTED, "/bin/true")
        self.assertFinds(SUBID_WANTED + ": missing")

    def test_subid_wanted_check_must_not_be_required(self):
        for d in ("usr/lib/greenboot/check/required.d", "etc/greenboot/check/required.d"):
            with self.subTest(d=d):
                rel = d + "/50-rikuri-containers-subid"
                self.root.write_bytes(rel, shipped_file(SUBID_WANTED), mode=0o755)
                self.assertFinds(rel + ": a required check")
                self.root.remove(rel)

    def test_subid_wanted_check_linked_into_required_is_still_required(self):
        # Verifier nit 1 (2026-10-24): greenboot follows a link, so a link there runs it as required.
        for d in ("usr/lib/greenboot/check/required.d", "etc/greenboot/check/required.d"):
            with self.subTest(d=d):
                rel = d + "/50-rikuri-containers-subid"
                self.root.link(rel, "../wanted.d/50-rikuri-containers-subid")
                self.assertFinds(rel + ": a required check")
                self.root.remove(rel)

    def test_subid_wanted_check_must_not_be_disabled(self):
        conf = shipped().decode("ascii")
        line = 'DISABLED_HEALTHCHECKS=("01_repository_dns_check.sh")'
        self.assertIn(line, conf.splitlines())
        self.root.write(cir.GREENBOOT_CONF, conf.replace(
            line, 'DISABLED_HEALTHCHECKS=("01_repository_dns_check.sh" "50-rikuri-containers-subid")'))
        # Already a finding: the list is pinned to Fedora's DNS check alone.
        self.assertFinds("DISABLED_HEALTHCHECKS is ['01_repository_dns_check.sh', '50-rikuri-containers-subid'], "
                         "expected ['01_repository_dns_check.sh']")

    def test_subid_unit_missing(self):
        self.root.remove(SUBID_UNIT)
        self.assertFinds(SUBID_UNIT + ": missing")

    def test_subid_unit_must_run_the_check_before_sysinit(self):
        good = shipped_file(SUBID_UNIT).decode("ascii")
        for text, why in ((good.replace("ExecStart=/usr/libexec/rikuri/containers-subid", "ExecStart=/bin/true"),
                           "another command"),
                          (good.replace("Before=sysinit.target", "Before=multi-user.target"), "too late"),
                          (good.replace("DefaultDependencies=no", "DefaultDependencies=yes"),
                           "default dependencies (ordered after sysinit.target)"),
                          (good.replace("[Unit]", "[Install]", 1), "outside [Unit]")):
            with self.subTest(why=why):
                self.assertNotEqual(text, good)
                self.root.write(SUBID_UNIT, text)
                self.assertFinds(SUBID_UNIT + ": ")

    def test_subid_unit_must_be_enabled(self):
        self.root.remove(SUBID_WANTS)
        self.assertFinds(SUBID_WANTS + ": not a link")
        for target, why in (("/dev/null", "masked"), ("../other.service", "another unit")):
            with self.subTest(why=why):
                self.root.link(SUBID_WANTS, target)
                self.assertFinds(SUBID_WANTS + ": ")
        self.root.write(SUBID_WANTS, "[Unit]\n")
        self.assertFinds(SUBID_WANTS + ": not a link")
        self.root.link(SUBID_WANTS, "/usr/lib/systemd/system/rikuri-containers-subid.service")
        self.assertEqual(cir.check_containers_subid(self.root.path), [])

    def test_subid_wants_reached_through_a_link_does_not_count(self):
        # Verifier I1: a link on the way to the .wants folder points outside the image.
        wants_dir = os.path.dirname(os.path.join(self.root.path, SUBID_WANTS))
        outside = tempfile.mkdtemp(prefix="outside-")
        self.addCleanup(shutil.rmtree, outside)
        os.symlink("../rikuri-containers-subid.service", os.path.join(outside, os.path.basename(SUBID_WANTS)))
        shutil.rmtree(wants_dir)
        os.symlink(outside, wants_dir)
        self.assertFinds(SUBID_WANTS + ": not a link")

    # --- greenboot.conf in the one form greenboot and the check read alike (F1)
    def test_shipped_conf_parses_to_the_expected_values(self):
        # The checker's own reading of the shipped file. greenboot's reading of
        # it is proven in change 3, by its journal ("Skipping disabled script").
        values, problems = cir.parse_greenboot_conf(shipped())
        self.assertEqual(problems, [])
        self.assertEqual(values, cir.GREENBOOT_EXPECTED)

    def test_every_probe_case_but_the_shipped_file_is_a_finding(self):
        for name, text, greenboot in probe_cases():
            with self.subTest(case=name):
                self.root.write_bytes(cir.GREENBOOT_CONF, text.encode("utf-8"))
                found = [f for f in self.root.check() if f.startswith(cir.GREENBOOT_CONF + ": ")]
                self.assertTrue(found, "%s passed with no finding; greenboot reads it as %s"
                                % (name, greenboot))

    def test_a_comment_starts_in_column_0(self):
        self.root.write(cir.GREENBOOT_CONF, A + "\n  # off\n" + D + "\n")
        self.assertFinds("line 2: not KEY=VALUE")

    def test_a_byte_outside_printable_ascii(self):
        # Each is a line break, a space or nothing to one reader and not the
        # other; the line is named with its bytes, in the order they appear.
        for tail, bytes_ in ((b"# note\x0b", "byte 0x0b"), (b"# note\r", "byte 0x0d"),
                             (b"\t# note", "byte 0x09"), ("# note\x85".encode("utf-8"), "bytes 0xc2 0x85")):
            with self.subTest(bytes=bytes_):
                self.root.write_bytes(cir.GREENBOOT_CONF,
                                      A.encode() + b"\n" + tail + b"\n" + D.encode() + b"\n")
                self.assertFinds("line 2: %s outside printable ASCII" % bytes_)

    def test_a_blank_line_is_exactly_empty(self):
        self.root.write(cir.GREENBOOT_CONF, A + "\n \n" + D + "\n")
        self.assertFinds("line 2: not KEY=VALUE")

    def test_attempts_is_digits_only(self):
        for value in ("3 ", " 3", "3 # three", "three", ""):
            with self.subTest(value=value):
                self.root.write(cir.GREENBOOT_CONF, "GREENBOOT_MAX_BOOT_ATTEMPTS=" + value + "\n" + D + "\n")
                self.assertFinds("GREENBOOT_MAX_BOOT_ATTEMPTS is not digits only")

    def test_disabled_is_exactly_the_quoted_names_in_parentheses(self):
        for value in ('( "a.sh" )', '("a.sh"  "b.sh")', '("a.sh" )', "('a.sh')", "(a.sh)",
                      '("a.sh")x', '("a b.sh")', '("")', '"a.sh"'):
            with self.subTest(value=value):
                self.root.write(cir.GREENBOOT_CONF, A + "\nDISABLED_HEALTHCHECKS=" + value + "\n")
                self.assertFinds("DISABLED_HEALTHCHECKS is not exactly")

    def test_disabled_two_names(self):
        values, problems = cir.parse_greenboot_conf(
            (A + '\nDISABLED_HEALTHCHECKS=("a.sh" "b-2_x.sh")\n').encode())
        self.assertEqual(problems, [])
        self.assertEqual(values["DISABLED_HEALTHCHECKS"], ["a.sh", "b-2_x.sh"])

    def test_conf_without_a_final_newline_is_read(self):
        self.root.write_bytes(cir.GREENBOOT_CONF, shipped().rstrip(b"\n"))
        self.assertEqual(self.root.check(), [])

    def test_fedora_default_conf_keeps_dns_check(self):
        self.root.write(cir.GREENBOOT_CONF,
                        "GREENBOOT_MAX_BOOT_ATTEMPTS=3\nDISABLED_HEALTHCHECKS=()\n")
        self.assertFinds("DISABLED_HEALTHCHECKS is [], expected ['01_repository_dns_check.sh']")

    def test_typo_in_disabled_name(self):
        self.root.write(cir.GREENBOOT_CONF, "GREENBOOT_MAX_BOOT_ATTEMPTS=3\n"
                        'DISABLED_HEALTHCHECKS=("01_repository_dns_checks.sh")\n')
        self.assertFinds("expected ['01_repository_dns_check.sh']")
        self.assertFinds("disabled check '01_repository_dns_checks.sh' is in none of")

    def test_disabled_name_absent_from_image(self):
        self.root.remove("usr/lib/greenboot/check/required.d/01_repository_dns_check.sh")
        self.assertFinds("disabled check '01_repository_dns_check.sh' is in none of")

    def test_disabled_check_as_link_does_not_count(self):
        self.root.link("usr/lib/greenboot/check/required.d/01_repository_dns_check.sh", "/bin/true")
        self.assertFinds("disabled check '01_repository_dns_check.sh' is in none of")

    def test_disabled_check_in_etc_counts(self):
        self.root.remove("usr/lib/greenboot/check/required.d/01_repository_dns_check.sh")
        self.root.write("etc/greenboot/check/required.d/01_repository_dns_check.sh", "#!/bin/sh\n")
        self.assertEqual(self.root.check(), [])

    def test_not_a_bash_array(self):
        self.root.write(cir.GREENBOOT_CONF, "GREENBOOT_MAX_BOOT_ATTEMPTS=3\n"
                        'DISABLED_HEALTHCHECKS="01_repository_dns_check.sh"\n')
        self.assertFinds("DISABLED_HEALTHCHECKS is not exactly")

    def test_section_header(self):
        self.root.write_bytes(cir.GREENBOOT_CONF, b"[greenboot]\n" + shipped())
        self.assertFinds("a [section] header")

    def test_duplicate_key(self):
        self.root.write_bytes(cir.GREENBOOT_CONF, shipped() + b"DISABLED_HEALTHCHECKS=()\n")
        self.assertFinds("DISABLED_HEALTHCHECKS set twice")

    def test_duplicate_key_with_the_same_value(self):
        # F5: only here does allowing a duplicate change the verdict, not the message.
        self.root.write_bytes(cir.GREENBOOT_CONF, shipped() + D.encode() + b"\n")
        self.assertFinds("DISABLED_HEALTHCHECKS set twice")

    def test_unknown_key(self):
        self.root.write_bytes(cir.GREENBOOT_CONF, shipped() + b"GREENBOOT_WATCHDOG_CHECK_ENABLED=false\n")
        self.assertFinds("unknown key GREENBOOT_WATCHDOG_CHECK_ENABLED")

    def test_not_key_value(self):
        self.root.write_bytes(cir.GREENBOOT_CONF, shipped() + b"export X\n")
        self.assertFinds("not KEY=VALUE")

    def test_attempts_changed(self):
        self.root.write(cir.GREENBOOT_CONF, "GREENBOOT_MAX_BOOT_ATTEMPTS=1\n"
                        'DISABLED_HEALTHCHECKS=("01_repository_dns_check.sh")\n')
        self.assertFinds("GREENBOOT_MAX_BOOT_ATTEMPTS is '1', expected '3'")

    def test_attempts_missing(self):
        self.root.write(cir.GREENBOOT_CONF, 'DISABLED_HEALTHCHECKS=("01_repository_dns_check.sh")\n')
        self.assertFinds("GREENBOOT_MAX_BOOT_ATTEMPTS is not set")

    def test_disabled_missing(self):
        # F5 (P7): the DNS check stays on when the key is simply absent.
        self.root.write(cir.GREENBOOT_CONF, A + "\n")
        self.assertFinds("DISABLED_HEALTHCHECKS is not set")

    # --- nothing secret in a public image: the forms refused (F4) -------------
    def test_private_key_in_etc(self):
        self.root.write("etc/pki/tls/private/node.key", pem("PRIVATE"))
        self.assertFinds("etc/pki/tls/private/node.key: holds a private key")

    def test_openssh_private_key_in_root_home(self):
        self.root.write("root/.ssh/id_ed25519", pem("OPENSSH PRIVATE"))
        self.assertFinds("root/.ssh/id_ed25519: holds a private key")

    def test_pgp_private_key_block(self):
        self.root.write("root/.gnupg/secring.asc", pem("PGP PRIVATE", block=" BLOCK"))
        self.assertFinds("root/.gnupg/secring.asc: holds a private key")

    def test_age_secret_key(self):
        self.root.write("root/.config/sops/age/keys.txt", "# created: today\n" + age_key())
        self.assertFinds("root/.config/sops/age/keys.txt: holds an age secret key")

    def test_tor_onion_service_key_by_name(self):
        self.root.write("var/lib/tor/node/hs_ed25519_secret_key", "")
        self.assertFinds("var/lib/tor/node/hs_ed25519_secret_key: a Tor onion service's secret key (by its name)")

    def test_tor_ed25519_secret_key_by_header(self):
        self.root.write_bytes("etc/tor/keys/renamed", TOR_SECRET_HEADER + b"\x00" * 64)
        self.assertFinds("etc/tor/keys/renamed: a Tor ed25519 secret key (by its header)")

    def test_wireguard_private_key(self):
        self.root.write("etc/wireguard/wg0.conf",
                        "[Interface]\nPrivateKey = " + "A" * 43 + "=\nAddress = 10.0.0.2/32\n")
        self.assertFinds("etc/wireguard/wg0.conf: holds a WireGuard private key")

    def test_wireguard_public_key_only_is_fine(self):
        self.root.write("etc/wireguard/wg0.conf", "[Peer]\nPublicKey = " + "A" * 43 + "=\n")
        self.assertEqual(self.root.check(), [])

    def test_ssh_host_key_baked_in(self):
        self.root.write("etc/ssh/ssh_host_ed25519_key", "not even a key format\n")
        self.assertFinds("etc/ssh/ssh_host_ed25519_key: an SSH host key")

    def test_public_key_is_fine(self):
        self.root.write("etc/pki/containers/rikuri.pub", pem("PUBLIC"))
        self.root.write("etc/ssh/ssh_host_ed25519_key.pub", "ssh-ed25519 AAAA\n")
        self.assertEqual(self.root.check(), [])

    def test_every_scanned_tree(self):
        # F4 adds tmp and boot; F5 (P4, P5) proves each tree is really scanned.
        self.assertEqual(cir.SECRET_DIRS, ("etc", "root", "var", "usr/local", "opt", "tmp", "boot"))
        for top in cir.SECRET_DIRS:
            with self.subTest(tree=top):
                root = Root()
                self.addCleanup(root.cleanup)
                root.write(top + "/leak/x.key", pem("PRIVATE"))
                self.assertFinds(top + "/leak/x.key: holds a private key", root.check())

    def test_private_key_under_usr_lib_is_not_scanned(self):
        # Fedora's own packages ship test keys under /usr; only the node's
        # writable and local trees are scanned (SECRET_DIRS).
        self.root.write("usr/lib/python3/site-packages/x/tests/key.pem", pem("RSA PRIVATE", end=False))
        self.assertEqual(self.root.check(), [])

    def test_large_file_is_skipped_and_said(self):
        big = pem("PRIVATE", body="A" * (cir.SECRET_MAX_BYTES + 1))
        self.root.write("var/lib/blob", big)
        found, notes = self.root.check_with_notes()
        self.assertEqual(found, [])
        self.assertIn("scan var: 0 file(s) read, 1 over the size cap", "\n".join(notes))

    def test_key_in_a_file_under_the_size_cap_is_found(self):
        # F5 (P6): a cap lowered to 1 KiB would hide this one.
        self.root.write("var/lib/blob", pem("PRIVATE", body="A" * (64 << 10)))
        self.assertFinds("var/lib/blob: holds a private key")

    def test_unreadable_file_is_a_finding(self):
        # F5 (P9). The refusal is injected: inside the test-safety layer the
        # tests run as a mapped root, which reads a mode-000 file, while CI's
        # runner does not; a real unreadable file would depend on who runs it.
        self.root.write("etc/locked", "x\n")
        real_open = open

        def refusing(path, *args, **kwargs):
            if str(path).endswith("/etc/locked"):
                raise PermissionError(errno.EACCES, "Permission denied", path)
            return real_open(path, *args, **kwargs)

        with mock.patch.object(cir, "open", refusing, create=True):
            found = self.root.check()
        self.assertFinds("etc/locked: cannot be read (Permission denied)", found)

    # --- links: nothing outside the root is read (F2) --------------------------
    def test_a_linked_top_folder_is_skipped(self):
        # F5 (P2): the key behind the link would be found if the link were followed.
        outside = self.outside_with_key()
        self.root.link("opt", outside)
        found, notes = self.root.check_with_notes()
        self.assertEqual([f for f in found if "host-only" in f], [])
        self.assertIn("scan opt: skipped (opt is a link to %s)" % outside, notes)

    def test_a_link_in_a_top_folders_path_is_skipped(self):
        # The verifier's probe (verify/linkprobe/usr_link.py): usr linked out
        # of the root, and usr/local reached through it.
        outside = self.outside_with_key(sub="local")
        shutil.rmtree(os.path.join(self.root.path, "usr"))
        self.root.link("usr", outside)
        found, notes = self.root.check_with_notes()
        self.assertEqual([f for f in found if "host-only" in f], [])
        self.assertIn("scan usr/local: skipped (usr is a link to %s)" % outside, notes)

    def test_a_linked_file_in_a_scanned_tree_is_not_read(self):
        # F5 (P3): neither a link to a key outside the root nor a dangling one.
        outside = self.outside_with_key()
        self.root.link("etc/pki/leak.key", os.path.join(outside, "host-only.key"))
        self.root.link("etc/pki/dangling.key", "/nonexistent/key")
        self.assertEqual(self.root.check(), [])

    def test_ostree_layout_is_scanned_through_var(self):
        # In the image, opt, usr/local and root are links into var (ostree's
        # layout); they are skipped as links and their files are reached under var.
        self.root.write("var/opt/app/x.key", pem("PRIVATE"))
        self.root.link("opt", "var/opt")
        found, notes = self.root.check_with_notes()
        self.assertEqual([f for f in found if "x.key" in f],
                         ["var/opt/app/x.key: holds a private key (the image is public)"])
        self.assertIn("scan opt: skipped (opt is a link to var/opt)", notes)

    # --- the scan is not vacuous (F3) ------------------------------------------
    def test_scan_report_names_every_tree(self):
        found, notes = self.root.check_with_notes()
        self.assertEqual(found, [])
        self.assertEqual([n.split(":")[0] for n in notes], ["scan " + t for t in cir.SECRET_DIRS])
        self.assertIn("scan etc: 2 file(s) read", notes)
        self.assertIn("scan var: skipped (absent)", notes)

    def test_etc_without_a_regular_file_is_a_finding(self):
        shutil.rmtree(os.path.join(self.root.path, "etc"))
        self.assertFinds("etc: skipped (absent)")
        os.makedirs(os.path.join(self.root.path, "etc/empty"))
        self.assertFinds("etc: no regular file was read")


if __name__ == "__main__":
    unittest.main()
