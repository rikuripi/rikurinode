"""Tests of check_image_root.py on fixture roots: a good root passes, and each
way the node could silently lose what it relies on fails. The committed
greenboot.conf is checked as shipped. Run by the full gate (step 3).
Record: docs/build-records/2026-10-12-stage1-os-image.md
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_image_root as cir  # noqa: E402

SHIPPED_CONF = os.path.join(HERE, "..", "rootfs", "etc", "greenboot", "greenboot.conf")


def pem(kind, body="AAAA\n", end=True):
    """A fake PEM block, assembled here so that no key-shaped text sits in the
    source (the pre-commit secret scan refuses it, rightly)."""
    label = kind + " KEY-----"
    text = "-----BEGIN " + label + "\n" + body
    return text + ("-----END " + label + "\n" if end else "")

OS_RELEASE = """NAME="Fedora Linux"
VERSION="44 (IoT Edition)"
ID=fedora
VERSION_ID=44
VARIANT="IoT Edition"
VARIANT_ID=iot
"""


class Root:
    """A fixture root shaped like the image: what the check reads, nothing more."""

    def __init__(self):
        self.path = tempfile.mkdtemp(prefix="image-root-")
        self.write("usr/lib/os-release", OS_RELEASE)
        self.write(cir.GREENBOOT_BIN, "#!/bin/sh\n", mode=0o755)
        self.write("usr/lib/greenboot/check/required.d/01_repository_dns_check.sh",
                   "#!/bin/sh\n", mode=0o755)
        self.write("usr/lib/greenboot/check/required.d/02_watchdog.sh", "#!/bin/sh\n", mode=0o755)
        with open(SHIPPED_CONF, encoding="utf-8") as f:
            self.write(cir.GREENBOOT_CONF, f.read())
        self.write("etc/ssh/sshd_config", "PermitRootLogin no\n")

    def write(self, rel, text, mode=0o644):
        p = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if os.path.lexists(p):
            os.remove(p)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(p, mode)

    def remove(self, rel):
        os.remove(os.path.join(self.path, rel))

    def check(self, release="44"):
        return cir.check_root(self.path, release)

    def cleanup(self):
        shutil.rmtree(self.path)


class CheckImageRoot(unittest.TestCase):
    def setUp(self):
        self.root = Root()
        self.addCleanup(self.root.cleanup)

    def assertFinds(self, fragment):
        found = self.root.check()
        self.assertTrue(any(fragment in f for f in found),
                        "expected a finding with %r, got %r" % (fragment, found))

    def test_good_root_passes(self):
        self.assertEqual(self.root.check(), [])

    def test_main_exit_codes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            self.assertEqual(cir.main([self.root.path, "--fedora", "44"]), 0)
            self.assertEqual(cir.main([self.root.path, "--fedora", "45"]), 1)
            self.assertEqual(cir.main([os.path.join(self.root.path, "nope"), "--fedora", "44"]), 2)
        self.assertIn("FAIL usr/lib/os-release: VERSION_ID is '44', expected '45'", out.getvalue())

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
        p = os.path.join(self.root.path, "usr/lib/os-release")
        os.remove(p)
        os.symlink("/usr/lib/os-release", p)
        self.assertFinds("usr/lib/os-release: missing, or not a regular file")

    # --- greenboot -----------------------------------------------------------
    def test_greenboot_not_installed(self):
        self.root.remove(cir.GREENBOOT_BIN)
        self.assertFinds("greenboot is not installed")

    def test_conf_missing(self):
        self.root.remove(cir.GREENBOOT_CONF)
        self.assertFinds("greenboot.conf: missing")

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
        p = os.path.join(self.root.path,
                         "usr/lib/greenboot/check/required.d/01_repository_dns_check.sh")
        os.remove(p)
        os.symlink("/bin/true", p)
        self.assertFinds("disabled check '01_repository_dns_check.sh' is in none of")

    def test_disabled_check_in_etc_counts(self):
        self.root.remove("usr/lib/greenboot/check/required.d/01_repository_dns_check.sh")
        self.root.write("etc/greenboot/check/required.d/01_repository_dns_check.sh", "#!/bin/sh\n")
        self.assertEqual(self.root.check(), [])

    def test_not_a_bash_array(self):
        self.root.write(cir.GREENBOOT_CONF, "GREENBOOT_MAX_BOOT_ATTEMPTS=3\n"
                        'DISABLED_HEALTHCHECKS="01_repository_dns_check.sh"\n')
        self.assertFinds("greenboot would disable nothing")

    def test_section_header(self):
        with open(SHIPPED_CONF, encoding="utf-8") as f:
            self.root.write(cir.GREENBOOT_CONF, "[greenboot]\n" + f.read())
        self.assertFinds("a [section] header")

    def test_duplicate_key(self):
        with open(SHIPPED_CONF, encoding="utf-8") as f:
            self.root.write(cir.GREENBOOT_CONF, f.read() + "DISABLED_HEALTHCHECKS=()\n")
        self.assertFinds("DISABLED_HEALTHCHECKS set twice")

    def test_unknown_key(self):
        with open(SHIPPED_CONF, encoding="utf-8") as f:
            self.root.write(cir.GREENBOOT_CONF, f.read() + "GREENBOOT_WATCHDOG_CHECK_ENABLED=false\n")
        self.assertFinds("unknown key GREENBOOT_WATCHDOG_CHECK_ENABLED")

    def test_not_key_value(self):
        with open(SHIPPED_CONF, encoding="utf-8") as f:
            self.root.write(cir.GREENBOOT_CONF, f.read() + "export X\n")
        self.assertFinds("not KEY=VALUE")

    def test_attempts_changed(self):
        self.root.write(cir.GREENBOOT_CONF, "GREENBOOT_MAX_BOOT_ATTEMPTS=1\n"
                        'DISABLED_HEALTHCHECKS=("01_repository_dns_check.sh")\n')
        self.assertFinds("GREENBOOT_MAX_BOOT_ATTEMPTS is '1', expected '3'")

    def test_attempts_missing(self):
        self.root.write(cir.GREENBOOT_CONF, 'DISABLED_HEALTHCHECKS=("01_repository_dns_check.sh")\n')
        self.assertFinds("GREENBOOT_MAX_BOOT_ATTEMPTS is not set")

    def test_shipped_conf_as_greenboot_reads_it(self):
        with open(SHIPPED_CONF, encoding="utf-8") as f:
            values, problems = cir.parse_greenboot_conf(f.read())
        self.assertEqual(problems, [])
        self.assertEqual(values, cir.GREENBOOT_EXPECTED)

    # --- nothing secret in a public image ------------------------------------
    def test_private_key_in_etc(self):
        self.root.write("etc/pki/tls/private/node.key",
                        pem("PRIVATE"))
        self.assertFinds("etc/pki/tls/private/node.key: holds a private key")

    def test_openssh_private_key_in_root_home(self):
        self.root.write("root/.ssh/id_ed25519",
                        pem("OPENSSH PRIVATE"))
        self.assertFinds("root/.ssh/id_ed25519: holds a private key")

    def test_ssh_host_key_baked_in(self):
        self.root.write("etc/ssh/ssh_host_ed25519_key", "not even a key format\n")
        self.assertFinds("etc/ssh/ssh_host_ed25519_key: an SSH host key")

    def test_public_key_is_fine(self):
        self.root.write("etc/pki/containers/rikuri.pub",
                        pem("PUBLIC"))
        self.root.write("etc/ssh/ssh_host_ed25519_key.pub", "ssh-ed25519 AAAA\n")
        self.assertEqual(self.root.check(), [])

    def test_private_key_under_usr_lib_is_not_scanned(self):
        # Fedora's own packages ship test keys under /usr; only the node's
        # writable and local trees are scanned (SECRET_DIRS).
        self.root.write("usr/lib/python3/site-packages/x/tests/key.pem",
                        pem("RSA PRIVATE", end=False))
        self.assertEqual(self.root.check(), [])

    def test_large_file_is_skipped(self):
        big = pem("PRIVATE", body="A" * (cir.SECRET_MAX_BYTES + 1))
        self.root.write("var/lib/blob", big)
        self.assertEqual(self.root.check(), [])


if __name__ == "__main__":
    unittest.main()
