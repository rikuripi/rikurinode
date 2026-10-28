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
# The signature policy for the node's OS image (docs/build-records/2026-10-25-signature-policy.md).
POLICY = "etc/containers/policy.json"
REGISTRIES_D_FILE = "etc/containers/registries.d/rikuri.yaml"
MAIN_PUB = "usr/share/rikuri/signing/rikuri-main.pub"
SPARE_PUB = "usr/share/rikuri/signing/rikuri-spare.pub"
SIGNATURE_FILES = (POLICY, REGISTRIES_D_FILE, MAIN_PUB, SPARE_PUB)


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
D = 'DISABLED_HEALTHCHECKS=("01_repository_dns_check.sh" "01_update_platforms_check.sh")'


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
        ("11-spaces-inside-array", A + '\nDISABLED_HEALTHCHECKS=( "01_repository_dns_check.sh" "01_update_platforms_check.sh" )\n',
         "as shipped"),
        ("12-inline-comment", A + " # three\n" + D + "\n",
         "disabled as shipped; the attempts value does not parse, so its default (3)"),
        ("13-spaces-around-equals", A + '\nDISABLED_HEALTHCHECKS = ("01_repository_dns_check.sh" "01_update_platforms_check.sh")\n',
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
        self.write("usr/lib/greenboot/check/wanted.d/01_update_platforms_check.sh", "#!/bin/sh\n", mode=0o755)
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
        for rel in SIGNATURE_FILES:
            self.write_bytes(rel, shipped_file(rel))
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
        self.assertIn("scan etc: 4 file(s) read", out.getvalue())

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
        line = D
        self.assertIn(line, conf.splitlines())
        self.root.write(cir.GREENBOOT_CONF, conf.replace(
            line, 'DISABLED_HEALTHCHECKS=("01_repository_dns_check.sh" "01_update_platforms_check.sh" '
                  '"50-rikuri-containers-subid")'))
        # Already a finding: the list is pinned to its two names.
        self.assertFinds("DISABLED_HEALTHCHECKS is ['01_repository_dns_check.sh', '01_update_platforms_check.sh', "
                         "'50-rikuri-containers-subid'], expected ['01_repository_dns_check.sh', "
                         "'01_update_platforms_check.sh']")

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

    def test_subid_unit_is_a_closed_world(self):
        # docs/build-records/2026-10-24-subid-unit-checker-gaps.md: systemd lets a later line
        # replace, add to or reset an earlier one, so each line's presence is not enough.
        good = shipped_file(SUBID_UNIT).decode("ascii")
        cases = (
            ("RemainAfterExit=yes\n", "RemainAfterExit=yes\nRemainAfterExit=no\n", "a later value replaces it"),
            ("ExecStart=/usr/libexec/rikuri/containers-subid\n",
             "ExecStart=/usr/libexec/rikuri/containers-subid\nExecStart=/bin/false\n", "a second command"),
            ("Before=sysinit.target shutdown.target\n", "Before=sysinit.target shutdown.target\nBefore=\n",
             "an empty value resets the list"),
            ("RemainAfterExit=yes\n", "", "RemainAfterExit missing: inactive after success"),
            ("Conflicts=shutdown.target\n", "", "Conflicts missing"),
            ("After=local-fs.target\n", "", "After missing"),
            ("After=local-fs.target", "After=network.target", "another After value"),
            ("Type=oneshot\n", "Type=oneshot\nExecStartPre=/bin/true\n", "a key the unit does not have"),
            ("DefaultDependencies=no\n", "DefaultDependencies=no\nConditionPathExists=/nope\n",
             "a condition that would skip it"),
            ("Type=oneshot", "Type = oneshot", "spaces around ="),
            ("Description=Podman's containers range in /etc/subuid and /etc/subgid", "Description=",
             "an empty Description (verifier nit 2)"),
            ("ExecStart=/usr/libexec/rikuri/containers-subid\n",
             "ExecStart=/usr/libexec/rikuri/containers-subid \\\n  --other\n", "a continuation line"),
            ("Description=Podman's", "Description=Podman\u2019s", "a byte outside printable ASCII"),
            ("WantedBy=sysinit.target", "WantedBy=multi-user.target", "enabled for another target"),
            ("RemainAfterExit=yes\n", "", "moved to [Install]"),
            ("[Install]\n", "[Install]\n# a note\n  ; indented\n", "an indented comment"),
            # Mutants 1 and 5 (03-mutants.out) survived the cases above:
            ("ExecStart=/usr/libexec/rikuri/containers-subid\n",
             "ExecStart=/usr/libexec/rikuri/containers-subid\nExecStart=/usr/libexec/rikuri/containers-subid\n",
             "the same command twice: systemd runs it twice"),
            ("Description=Podman's containers range in /etc/subuid and /etc/subgid\n",
             "Description=Podman's containers range in /etc/subuid and /etc/subgid \\\n",
             "a continuation that swallows DefaultDependencies=no into the description"),
        )
        for old, new, why in cases:
            with self.subTest(why=why):
                self.assertIn(old, good)
                text = good.replace(old, new, 1)
                if why == "moved to [Install]":
                    text += "RemainAfterExit=yes\n"
                self.root.write_bytes(SUBID_UNIT, text.encode("utf-8"))
                self.assertFinds(SUBID_UNIT + ": ", cir.check_containers_subid(self.root.path))
        for extra, why in (("\n[Unit]\nAfter=local-fs.target\n", "a section twice"),
                           ("\n[Install]\n", "an empty section twice (mutant 4)"),
                           ("\n[X-Rikuri]\nKey=value\n", "an unknown section")):
            with self.subTest(why=why):
                self.root.write(SUBID_UNIT, good + extra)
                self.assertFinds(SUBID_UNIT + ": ", cir.check_containers_subid(self.root.path))

    def test_subid_unit_comments_blank_lines_and_description_are_free(self):
        good = shipped_file(SUBID_UNIT).decode("ascii")
        text = ("; a note\n\n" + good.replace("Description=Podman's containers range in /etc/subuid and /etc/subgid",
                                                "Description=Another description")
                + "\n# the end\n")
        self.root.write(SUBID_UNIT, text)
        self.assertEqual(cir.check_containers_subid(self.root.path), [])

    # Repair 1 (verifier I1, evidence 05): systemd reads a drop-in folder for every
    # dash prefix of the name, in every unit folder an image can ship.
    UNIT_DIRS = ("etc/systemd/system.control", "etc/systemd/system", "etc/systemd/system.attached",
                 "usr/local/lib/systemd/system", "usr/lib/systemd/system")
    DROPINS = ("rikuri-containers-subid.service.d", "rikuri-containers-.service.d", "rikuri-.service.d")

    def expected_overrides(self):
        paths = set()
        for d in self.UNIT_DIRS:
            paths.update(d + "/" + name for name in self.DROPINS)
            if d != "usr/lib/systemd/system":    # the unit itself, and Fedora's service.d, live there
                paths.update((d + "/rikuri-containers-subid.service", d + "/service.d"))
        return paths

    def test_subid_overrides_are_every_path_systemd_reads(self):
        self.assertEqual(set(cir.SUBID_OVERRIDES), self.expected_overrides())

    def test_each_override_path_is_a_finding(self):
        for rel in sorted(self.expected_overrides()):
            with self.subTest(rel=rel):
                full = os.path.join(self.root.path, rel)
                try:
                    self.root.write(rel + "/50-x.conf" if rel.endswith(".d") else rel, "[Service]\nRemainAfterExit=no\n")
                    self.assertFinds(rel + ": overrides the unit", cir.check_containers_subid(self.root.path))
                finally:
                    if os.path.isdir(full):
                        shutil.rmtree(full)
                    elif os.path.lexists(full):
                        os.remove(full)
        self.assertEqual(cir.check_containers_subid(self.root.path), [])

    def test_a_link_on_the_way_to_an_override_path_is_a_finding(self):
        # Verifier nit 3: lexists followed a linked folder on the way into the checker's machine.
        outside = tempfile.mkdtemp(prefix="outside-")
        self.addCleanup(shutil.rmtree, outside)
        os.makedirs(os.path.join(self.root.path, "etc"), exist_ok=True)
        self.root.link("etc/systemd", outside)
        self.assertFinds("etc/systemd/system/rikuri-containers-subid.service.d: reached through a link",
                         cir.check_containers_subid(self.root.path))

    def test_a_link_at_any_folder_on_the_way_is_a_finding(self):
        # Verifier follow-up I2: a link at the first folder (etc) or at the last one before
        # the name (the unit folder itself) passed a weakened walk; each position is a case.
        outside = tempfile.mkdtemp(prefix="outside-")
        self.addCleanup(shutil.rmtree, outside)
        for linked, rel in (("etc", "etc/systemd/system/rikuri-containers-subid.service.d"),
                            ("etc/systemd", "etc/systemd/system/rikuri-containers-subid.service.d"),
                            ("etc/systemd/system", "etc/systemd/system/rikuri-containers-subid.service.d"),
                            ("usr/local/lib/systemd/system", "usr/local/lib/systemd/system/rikuri-.service.d")):
            with self.subTest(linked=linked):
                full = os.path.join(self.root.path, linked)
                try:
                    if os.path.isdir(full) and not os.path.islink(full):
                        shutil.rmtree(full)
                    self.root.link(linked, outside)
                    self.assertFinds("%s: reached through a link at %s" % (rel, linked),
                                     cir.check_containers_subid(self.root.path))
                finally:
                    if os.path.lexists(full):
                        os.remove(full)

    def test_subid_overrides_in_the_image_are_findings(self):
        for rel, kind in (("usr/lib/systemd/system/rikuri-containers-subid.service.d", "folder"),
                          ("usr/lib/systemd/system/rikuri-.service.d", "folder"),
                          ("etc/systemd/system/rikuri-containers-subid.service", "mask"),
                          ("etc/systemd/system/rikuri-containers-subid.service", "copy"),
                          ("etc/systemd/system/rikuri-containers-subid.service.d", "folder"),
                          ("etc/systemd/system/rikuri-.service.d", "folder"),
                          ("etc/systemd/system/rikuri-containers-subid.service.d", "link"),
                          # Mutant 9: a link whose target the checker's machine lacks, a node may have.
                          ("etc/systemd/system/rikuri-.service.d", "dangling")):
            with self.subTest(rel=rel, kind=kind):
                full = os.path.join(self.root.path, rel)
                try:
                    if kind == "folder":
                        self.root.write(rel + "/50-x.conf", "[Service]\nRemainAfterExit=no\n")
                    elif kind == "mask":
                        self.root.link(rel, "/dev/null")
                    elif kind == "link":
                        self.root.link(rel, "/tmp")
                    elif kind == "dangling":
                        self.root.link(rel, "/nonexistent-on-the-checker/rikuri.service.d")
                    else:
                        self.root.write_bytes(rel, shipped_file(SUBID_UNIT))
                    self.assertFinds(rel + ": overrides the unit", cir.check_containers_subid(self.root.path))
                finally:
                    if os.path.isdir(full) and not os.path.islink(full):
                        shutil.rmtree(full)
                    elif os.path.lexists(full):
                        os.remove(full)
        self.assertEqual(cir.check_containers_subid(self.root.path), [])

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
        self.assertFinds("DISABLED_HEALTHCHECKS is [], expected ['01_repository_dns_check.sh', "
                         "'01_update_platforms_check.sh']")

    def test_typo_in_disabled_name(self):
        self.root.write(cir.GREENBOOT_CONF, "GREENBOOT_MAX_BOOT_ATTEMPTS=3\n"
                        'DISABLED_HEALTHCHECKS=("01_repository_dns_checks.sh")\n')
        self.assertFinds("expected ['01_repository_dns_check.sh', '01_update_platforms_check.sh']")
        self.assertFinds("disabled check '01_repository_dns_checks.sh' is in none of")

    def test_disabled_name_absent_from_image(self):
        self.root.remove("usr/lib/greenboot/check/required.d/01_repository_dns_check.sh")
        self.assertFinds("disabled check '01_repository_dns_check.sh' is in none of")

    def test_each_disabled_name_is_pinned(self):
        # Owner, 2026-10-24: Fedora's update-platforms check is off, like the DNS check (D9).
        for value, got in (('("01_repository_dns_check.sh")', "['01_repository_dns_check.sh']"),
                           ('("01_update_platforms_check.sh")', "['01_update_platforms_check.sh']"),
                           ('("01_update_platforms_check.sh" "01_repository_dns_check.sh")',
                            "['01_update_platforms_check.sh', '01_repository_dns_check.sh']")):
            with self.subTest(value=value):
                self.root.write(cir.GREENBOOT_CONF, A + "\nDISABLED_HEALTHCHECKS=" + value + "\n")
                self.assertFinds("DISABLED_HEALTHCHECKS is %s, expected ['01_repository_dns_check.sh', "
                                 "'01_update_platforms_check.sh']" % got)

    def test_disabled_platforms_check_absent_from_image(self):
        self.root.remove("usr/lib/greenboot/check/wanted.d/01_update_platforms_check.sh")
        self.assertFinds("disabled check '01_update_platforms_check.sh' is in none of")

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
        self.root.write(cir.GREENBOOT_CONF, "GREENBOOT_MAX_BOOT_ATTEMPTS=1\n" + D + "\n")
        self.assertFinds("GREENBOOT_MAX_BOOT_ATTEMPTS is '1', expected '3'")

    def test_attempts_missing(self):
        self.root.write(cir.GREENBOOT_CONF, D + "\n")
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
        self.assertIn("scan etc: 4 file(s) read", notes)
        self.assertIn("scan var: skipped (absent)", notes)

    def test_etc_without_a_regular_file_is_a_finding(self):
        shutil.rmtree(os.path.join(self.root.path, "etc"))
        self.assertFinds("etc: skipped (absent)")
        os.makedirs(os.path.join(self.root.path, "etc/empty"))
        self.assertFinds("etc: no regular file was read")



class QuadletHealth(unittest.TestCase):
    """Every health command a Quadlet unit in the image sets is the exec form
    (docs/build-records/2026-10-25-healthcmd-exec-form.md; probed in evidence 01 to 04)."""

    setUp = CheckImageRoot.setUp
    assertFinds = CheckImageRoot.assertFinds

    UNIT = "etc/containers/systemd/svc.container"
    EXEC = '["/standin", "probe"]'

    def unit(self, lines, rel=None):
        self.root.write(rel or self.UNIT, "[Container]\nImage=localhost/svc:1.0\n" + lines + "\n")

    def problems(self):
        return cir.check_quadlet_health(self.root.path)

    def test_the_checks_run_on_the_image(self):
        self.unit("HealthCmd=/standin probe")
        self.assertFinds(self.UNIT + ": line 3: HealthCmd= is not the exec form")

    def test_no_unit_folders_no_finding(self):
        self.assertEqual(self.problems(), [])

    def test_exec_forms_pass(self):
        for line in ('HealthCmd=["/standin", "probe"]',
                     'HealthCmd=   ["/standin","probe"]   ',      # probe hc05, hc16, hc17: Podman reads CMD
                     'HealthCmd = ["/standin", "probe"]',          # hc10: Quadlet reads the key
                     'HealthStartupCmd=["/standin", "startup"]',
                     '# HealthCmd=/standin probe',                 # a comment
                     '; HealthCmd=/standin probe',
                     'PodmanArgs=--memory=1g',
                     'Environment=HEALTH=1'):
            with self.subTest(line=line):
                self.unit(line)
                self.assertEqual(self.problems(), [])

    def test_forms_podman_runs_through_a_shell_or_never_runs_are_findings(self):
        for line, why in (('HealthCmd=/standin probe', "a plain string: CMD-SHELL (hc14)"),
                          ('HealthCmd=["CMD-SHELL", "/standin probe"]', "CMD-SHELL in the array (hc02)"),
                          ('HealthCmd=["CMD", "/standin", "probe"]', "exec, but not the one form (hc03)"),
                          # Repair 1 (verifier I1, probe hr01): Podman takes the exec form only with
                          # two items or more. This case moved here from test_exec_forms_pass.
                          ('HealthCmd=["/standin"]', "one item: CMD-SHELL (hr01)"),
                          ('HealthStartupCmd=["/standin"]', "one item, the startup check"),
                          # Repair 1 (verifier I2): systemd expands these in ExecStart after Quadlet.
                          ('HealthCmd=["/standin", "%i"]', "a specifier"),
                          ('HealthCmd=["/standin", "${X}"]', "a variable"),
                          ('HealthCmd=["/standin", "$X"]', "a bare variable"),
                          ('HealthCmd=["/standin", "pro\\u0062e"]', "a JSON escape"),
                          ('HealthCmd=["/standin", "pro\\"be"]', "a quote inside an item"),
                          ('HealthCmd=["/standin", "probe now"]', "a space inside an item"),
                          ('HealthCmd=[/standin, probe]', "not JSON: CMD-SHELL (hc04)"),
                          ('HealthCmd="[\\"/standin\\", \\"probe\\"]"', "quoted: CMD-SHELL (hc07)"),
                          ('HealthCmd=["/standin", "probe"] # trailing', "a trailing comment: CMD-SHELL (hc15)"),
                          ('HealthCmd=none', "disabled (hc06)"),
                          ('HealthCmd=["NONE"]', "disabled (hc13)"),
                          ('HealthCmd=[]', "refused by Podman (hc12)"),
                          ('HealthCmd=', "empty"),
                          ('HealthCmd=[""]', "an empty item"),
                          ('HealthCmd=["standin", "probe"]', "not an absolute path"),
                          ('HealthCmd=["/standin", 1]', "not all strings"),
                          ('HealthCmd={"cmd": "/standin"}', "not an array"),
                          ('HealthCmd="/standin"', "a JSON string, not an array"),
                          ('healthcmd=/standin probe', "the key in another case (hc11)"),
                          ('HealthStartupCmd=/standin startup', "the startup check: CMD-SHELL (hs01)")):
            with self.subTest(why=why):
                self.unit(line)
                key = line.split("=")[0].strip()
                self.assertFinds("%s: line 3: %s= is not the exec form" % (self.UNIT, key), self.problems())

    def test_a_later_shell_form_is_a_finding(self):
        # Probe hc09: the last HealthCmd= wins.
        self.unit('HealthCmd=["/standin", "probe"]\nHealthCmd=/standin probe')
        self.assertEqual(self.problems(), [self.UNIT + ": line 4: HealthCmd= is not the exec form "
                                           "(a JSON array whose first item is an absolute path); Podman "
                                           "would run it through /bin/sh -c, which a shell-less image lacks"])

    def test_health_options_through_podman_args_are_findings(self):
        # Probes hs02 to hs04: PodmanArgs= hands Podman its own --health-cmd, and it wins.
        for line in ('PodmanArgs=--health-cmd=/standin\\x20probe',
                     'PodmanArgs=--health-cmd "/standin probe"',
                     'PodmanArgs=--memory=1g --health-startup-cmd "/standin startup"',
                     'PodmanArgs = --HEALTH-CMD x'):
            with self.subTest(line=line):
                self.unit(line)
                self.assertFinds(self.UNIT + ": line 3: PodmanArgs= sets a health option", self.problems())

    def test_health_options_hidden_in_podman_args_are_findings(self):
        # Repair 1 (verifier I3, probes hr04, hr05): Quadlet unescapes and unquotes PodmanArgs=,
        # and systemd expands % and $ in it.
        for line in ('PodmanArgs=--\\x68ealth-cmd=/standin\\x20probe',
                     'PodmanArgs=--hea""lth-cmd "/standin probe"',
                     "PodmanArgs=--hea''lth-cmd x",
                     'PodmanArgs=--%i=x',
                     'PodmanArgs=--${H}=x'):
            with self.subTest(line=line):
                self.unit(line)
                self.assertFinds(self.UNIT + ": line 3: PodmanArgs= sets a health option", self.problems())

    def test_a_byte_outside_printable_ascii_anywhere_is_a_finding(self):
        # Repair 1 (verifier I3, probes hr02, hr03): Quadlet trims 0xA0 before '=' as a space.
        for data in (b"[Container]\nHealthCmd\xa0=/standin probe\n",
                     b"[Container]\nPodmanArgs\x85=--health-cmd=/standin\n",
                     b"[Container]\nDescription=caf\xc3\xa9\n",
                     b"[Container]\nEnvironment=A=1\r\n",
                     b"[Container]\nEnvironment=A=\t1\n"):
            with self.subTest(data=data):
                self.root.write_bytes(self.UNIT, data)
                self.assertFinds(self.UNIT + ": line 2: outside printable ASCII", self.problems())

    def test_a_fifo_in_a_unit_folder_is_a_finding(self):
        # Repair 1 (verifier I4): the non-regular-file rule had no test.
        os.makedirs(os.path.join(self.root.path, "etc/containers/systemd"))
        os.mkfifo(os.path.join(self.root.path, "etc/containers/systemd/svc.container"))
        self.assertFinds(self.UNIT + ": not a regular file", self.problems())

    def test_a_continuation_line_is_a_finding(self):
        # Probe hc08: Quadlet joins it to the next line.
        for line in ('HealthCmd=["/standin", \\\n  "probe"]', 'Environment=A=1 \\\n  B=2', '# a comment \\'):
            with self.subTest(line=line):
                self.unit(line)
                self.assertFinds(self.UNIT + ": line 3: a continuation line", self.problems())

    def test_a_health_line_outside_printable_ascii_is_a_finding(self):
        self.root.write_bytes(self.UNIT, b'[Container]\nHealthCmd=["/standin", "pr\xc3\xb6be"]\n')
        self.assertFinds(self.UNIT + ": line 2: HealthCmd= is not the exec form", self.problems())
        self.root.write_bytes(self.UNIT, b'[Container]\nHealthCmd=["/standin",\t"probe"]\n')
        self.assertFinds(self.UNIT + ": line 2: HealthCmd= is not the exec form", self.problems())

    def test_every_file_quadlet_reads_is_checked(self):
        # Evidence 01, 04: both folders, their subfolders, every drop-in level, users/.
        for rel in ("etc/containers/systemd/svc.container",
                    "usr/share/containers/systemd/svc.container",
                    "etc/containers/systemd/sub/svc.container",
                    "etc/containers/systemd/svc.container.d/50-health.conf",
                    "etc/containers/systemd/svc-.container.d/50-health.conf",
                    "etc/containers/systemd/container.d/50-health.conf",
                    "usr/share/containers/systemd/container.d/50-health.conf",
                    "etc/containers/systemd/users/svc.container",
                    "etc/containers/systemd/svc@.container"):
            with self.subTest(rel=rel):
                full = os.path.join(self.root.path, rel)
                try:
                    self.root.write(rel, "[Container]\nHealthCmd=/standin probe\n")
                    self.assertFinds(rel + ": line 2: HealthCmd= is not the exec form", self.problems())
                finally:
                    os.remove(full)
        self.assertEqual(self.problems(), [])

    def test_links_in_or_on_the_way_to_the_unit_folders_are_findings(self):
        # Probe 02: Quadlet reads a linked file and a linked folder; the checker would not see
        # what a link reaches on a node.
        outside = tempfile.mkdtemp(prefix="outside-")
        self.addCleanup(shutil.rmtree, outside)
        for linked, fragment in (("etc/containers/systemd/svc.container", "etc/containers/systemd/svc.container: a link"),
                                 ("etc/containers/systemd/linked", "etc/containers/systemd/linked: a link"),
                                 ("usr/share/containers/systemd", "usr/share/containers/systemd: a link"),
                                 ("etc/containers", "etc/containers/systemd: reached through a link at etc/containers"),
                                 ("etc", "etc/containers/systemd: reached through a link at etc")):
            with self.subTest(linked=linked):
                full = os.path.join(self.root.path, linked)
                try:
                    if os.path.isdir(full) and not os.path.islink(full):
                        shutil.rmtree(full)
                    self.root.link(linked, outside)
                    self.assertFinds(fragment, self.problems())
                finally:
                    if os.path.lexists(full):
                        os.remove(full)
        self.assertEqual(self.problems(), [])

    def test_a_unit_folder_that_is_a_file_is_a_finding(self):
        self.root.write("usr/share/containers/systemd", "not a folder\n")
        self.assertFinds("usr/share/containers/systemd: not a folder", self.problems())


# Fedora IoT 44's own file (evidence 2026-10-25-signature-policy/01-probe.out): any image, signed or not.
FEDORA_POLICY = """{
    "default": [
        {
            "type": "insecureAcceptAnything"
        }
    ],
    "transports":
        {
            "docker-daemon":
                {
                    "": [{"type":"insecureAcceptAnything"}]
                }
        }
}
"""


class SignaturePolicy(unittest.TestCase):
    """The node refuses an OS image this project did not sign: the policy, the
    registries.d file that makes containers/image look for the signature, and the
    two public keys, exactly as shipped (docs/build-records/2026-10-25-signature-policy.md;
    the policy's behaviour probed in evidence 03 and 04, and proven in CI)."""

    setUp = CheckImageRoot.setUp
    assertFinds = CheckImageRoot.assertFinds

    def problems(self):
        return cir.check_signature_policy(self.root.path)

    def policy_text(self):
        return shipped_file(POLICY).decode("ascii")

    def test_the_shipped_files_pass(self):
        self.assertEqual(self.problems(), [])

    def test_the_check_runs_on_the_image(self):
        self.root.write(POLICY, FEDORA_POLICY)
        self.assertFinds(POLICY + ": not the signature policy")

    def test_each_file_missing_is_a_finding(self):
        for rel in SIGNATURE_FILES:
            with self.subTest(rel=rel):
                self.root.remove(rel)
                try:
                    self.assertFinds(rel + ": missing, or not a regular file", self.problems())
                finally:
                    self.root.write_bytes(rel, shipped_file(rel))

    def test_each_file_as_a_link_does_not_count(self):
        for rel in SIGNATURE_FILES:
            with self.subTest(rel=rel):
                copy = rel + ".real"
                self.root.write_bytes(copy, shipped_file(rel))
                self.root.link(rel, os.path.basename(copy))
                try:
                    self.assertFinds(rel + ": missing, or not a regular file", self.problems())
                finally:
                    self.root.remove(copy)
                    self.root.write_bytes(rel, shipped_file(rel))

    def test_fedoras_default_policy_is_a_finding(self):
        self.root.write(POLICY, FEDORA_POLICY)
        self.assertFinds(POLICY + ": not the signature policy", self.problems())

    def test_every_change_to_the_policy_is_a_finding(self):
        s = self.policy_text()
        mutants = {
            "the spare key dropped": s.replace(',\n                        "/usr/share/rikuri/signing/rikuri-spare.pub"', ""),
            "another key path": s.replace("rikuri-spare.pub", "rikuri-other.pub"),
            "a wider scope": s.replace('"ghcr.io/rikuripi/rikurinode"', '"ghcr.io/rikuripi"'),
            "another scope": s.replace("ghcr.io/rikuripi/rikurinode", "ghcr.io/rikuripi/rikurinod"),
            "accept anything for the image": s.replace('"type": "sigstoreSigned"', '"type": "insecureAcceptAnything"'),
            "signedBy (GPG) instead": s.replace("sigstoreSigned", "signedBy"),
            "another identity rule": s.replace("matchRepository", "matchRepoDigestOrExact"),
            "a reject default": s.replace('"insecureAcceptAnything"\n        }\n    ],', '"reject"\n        }\n    ],', 1),
            "a second key, Default (containers/image refuses an unknown key)": s.replace('    "default"', '    "Default": [{"type": "insecureAcceptAnything"}],\n    "default"', 1),
            "default twice": s.replace('    "transports"', '    "default": [{"type": "insecureAcceptAnything"}],\n    "transports"', 1),
            "a second requirement": s.replace('            ]\n        },\n        "docker-daemon"',
                                              '            , {"type": "insecureAcceptAnything"}]\n        },\n        "docker-daemon"', 1),
            "another transport": s.replace('"docker-daemon"', '"oci"'),
            "not JSON": s + "}",
            "a byte-order mark": "\ufeff" + s,
            "a byte outside printable ASCII": s.replace("matchRepository", "matchRepository\u00a0"),
        }
        for name, text in mutants.items():
            with self.subTest(mutant=name):
                self.assertNotEqual(text, s)
                self.root.write(POLICY, text)
                self.assertFinds(POLICY + ": ", self.problems())

    def test_whitespace_and_order_are_free(self):
        import json
        data = json.loads(self.policy_text())
        self.root.write(POLICY, json.dumps(dict(reversed(list(data.items())))))
        self.assertEqual(self.problems(), [])

    def test_every_change_to_the_registries_d_file_is_a_finding(self):
        s = shipped_file(REGISTRIES_D_FILE).decode("ascii")
        mutants = {
            "attachments off": s.replace("use-sigstore-attachments: true", "use-sigstore-attachments: false"),
            "attachments gone": s.replace("    use-sigstore-attachments: true\n", ""),
            "another scope": s.replace("ghcr.io/rikuripi/rikurinode", "ghcr.io/rikuripi"),
            "a lookaside too": s + "    lookaside: https://example.invalid/sigstore\n",
            "default-docker instead": s.replace("docker:\n  ghcr.io/rikuripi/rikurinode:", "default-docker:"),
            "a tab": s.replace("    use-sigstore", "\tuse-sigstore"),
            "an indented comment": s + "  # a note\n",
            "a byte outside printable ASCII": s.replace("true", "true\u00a0"),
            # YAML may read NEL as a line break, so the comment's tail would be a key.
            "a NEL in a comment": s + "# note\u0085    lookaside: https://example.invalid/\n",
        }
        for name, text in mutants.items():
            with self.subTest(mutant=name):
                self.assertNotEqual(text, s)
                self.root.write(REGISTRIES_D_FILE, text)
                self.assertFinds(REGISTRIES_D_FILE + ": ", self.problems())

    def test_comments_and_blank_lines_in_the_registries_d_file_are_free(self):
        s = shipped_file(REGISTRIES_D_FILE).decode("ascii")
        self.root.write(REGISTRIES_D_FILE, "# another note\n\n" + s + "\n# the end\n")
        self.assertEqual(self.problems(), [])

    def test_another_registries_d_file_naming_the_image_is_a_finding(self):
        # containers/image fails every pull of a scope two files configure.
        self.root.write("etc/containers/registries.d/other.yaml",
                        "docker:\n  ghcr.io/rikuripi/rikurinode:\n    lookaside: https://example.invalid/\n")
        self.assertFinds("etc/containers/registries.d/other.yaml: names ghcr.io/rikuripi", self.problems())

    def test_fedoras_own_registries_d_files_are_free(self):
        self.root.write("etc/containers/registries.d/default.yaml", "default-docker:\n")
        self.root.write("etc/containers/registries.d/registry.redhat.io.yaml",
                        "docker:\n     registry.redhat.io:\n         lookaside: https://registry.redhat.io/containers/sigstore\n")
        self.assertEqual(self.problems(), [])

    def test_a_link_in_the_registries_d_folder_is_a_finding(self):
        self.root.link("etc/containers/registries.d/linked.yaml", "/elsewhere/linked.yaml")
        self.assertFinds("etc/containers/registries.d/linked.yaml: a link", self.problems())

    def test_a_changed_key_is_a_finding(self):
        main, spare = shipped_file(MAIN_PUB), shipped_file(SPARE_PUB)
        for rel, data in ((MAIN_PUB, spare), (SPARE_PUB, main), (MAIN_PUB, main + b"\n")):
            with self.subTest(rel=rel, data=data[-8:]):
                self.root.write_bytes(rel, data)
                try:
                    self.assertFinds(rel + ": not the key", self.problems())
                finally:
                    self.root.write_bytes(rel, shipped_file(rel))

    def test_the_shipped_keys_are_the_owners(self):
        # The fingerprints in the Build Record (owner steps, 2026-10-28).
        import hashlib
        self.assertEqual(hashlib.sha256(shipped_file(MAIN_PUB)).hexdigest(),
                         "605548bfcc3a4d6f0a85b17ef7ccb8af20507ddbd22d1473b84a769d4a990c0d")
        self.assertEqual(hashlib.sha256(shipped_file(SPARE_PUB)).hexdigest(),
                         "49dc526a92bceec51a81fda2e99b17546d1f142f1d4ccc84e76c513424fc0ba8")

    def test_roots_own_containers_config_is_a_finding(self):
        # containers/image reads $HOME/.config/containers/policy.json instead of
        # /etc's when it exists (evidence 04, case 10), and bootc runs as root.
        for rel in ("var/roothome/.config/containers/policy.json",
                    "var/roothome/.config/containers/registries.d/x.yaml",
                    "root/.config/containers/policy.json"):
            with self.subTest(rel=rel):
                self.root.write(rel, "{}\n")
                try:
                    self.assertFinds(rel.split("/.config/")[0] + "/.config/containers: ", self.problems())
                finally:
                    shutil.rmtree(os.path.join(self.root.path, rel.split("/")[0]))

    def test_root_as_ostrees_link_into_var_is_free(self):
        for target in ("var/roothome", "/var/roothome"):
            with self.subTest(target=target):
                self.root.link("root", target)
                try:
                    self.assertEqual(self.problems(), [])
                finally:
                    self.root.remove("root")

    def test_root_as_another_link_is_a_finding(self):
        self.root.link("root", "/elsewhere")
        self.assertFinds("root: a link to /elsewhere", self.problems())


if __name__ == "__main__":
    unittest.main()
