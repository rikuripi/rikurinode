"""Tests for image/drill/install_test.py, CI's install test of the USB installer.

Only its pure parts run here: the VM it starts (the stick as a removable USB
disk, read-only; no network; UEFI with the run's own firmware settings; the
console on a socket the test types into, and logged), when a disk counts as
unchanged, and what it reads from the serial log and the installed disk
(greenboot passed, the firmware started the node's own entry, the origin, the
manifest digest). The VM runs only in CI (.github/workflows/image.yml, job
install). No VM, disk or network here.
Record: docs/build-records/2026-10-29-install-media.md
"""
from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "drill"))
import install_test as it  # noqa: E402

DIGEST = "sha256:" + "c" * 64
TARGET = "ghcr.io/rikuripi/rikurinode:install-test"


class StickArgv(unittest.TestCase):
    def setUp(self):
        self.argv = it.stick_argv("/w/node.iso", ["/w/a.raw", "/w/b.raw"], "/w/vars.fd", "/w/con.sock", "/w/con.log")

    def test_kvm_uefi_and_no_network(self):
        a = self.argv
        self.assertIn("-enable-kvm", a)
        self.assertEqual(a[a.index("-nic") + 1], "none")
        self.assertIn("-no-reboot", a)
        drives = [a[i + 1] for i, x in enumerate(a) if x == "-drive"]
        self.assertTrue(any(it.OVMF_CODE in x and "readonly=on" in x for x in drives))
        self.assertTrue(any("file=/w/vars.fd" in x and "readonly" not in x for x in drives))

    def test_the_stick_is_a_removable_read_only_usb_disk(self):
        a = self.argv
        drives = [a[i + 1] for i, x in enumerate(a) if x == "-drive"]
        stick = [x for x in drives if "/w/node.iso" in x]
        self.assertEqual(len(stick), 1)
        self.assertIn("readonly=on", stick[0])
        devices = [a[i + 1] for i, x in enumerate(a) if x == "-device"]
        self.assertIn("qemu-xhci", devices)
        self.assertTrue(any(d.startswith("usb-storage,") and "removable=on" in d for d in devices))

    def test_each_target_disk_is_a_virtio_disk(self):
        drives = [self.argv[i + 1] for i, x in enumerate(self.argv) if x == "-drive"]
        for path in ("/w/a.raw", "/w/b.raw"):
            self.assertIn("if=virtio,format=raw,file=" + path, drives)

    def test_the_console_is_a_socket_the_test_types_into_and_a_log(self):
        a = self.argv
        chardev = a[a.index("-chardev") + 1].split(",")
        self.assertEqual(chardev[0], "socket")
        self.assertIn("path=/w/con.sock", chardev)
        self.assertIn("server=on", chardev)
        self.assertIn("wait=off", chardev)
        self.assertIn("logfile=/w/con.log", chardev)
        self.assertEqual(a[a.index("-serial") + 1], "chardev:" + chardev[1].split("=")[1])


class DiskArgv(unittest.TestCase):
    def test_the_disk_alone_no_stick_same_firmware_settings(self):
        a = it.disk_argv("/w/a.raw", "/w/vars.fd", "/w/boot.log")
        self.assertNotIn("usb-storage", " ".join(a))
        self.assertIn("if=virtio,format=raw,file=/w/a.raw", a)
        self.assertTrue(any("file=/w/vars.fd" in x for x in a))
        self.assertEqual(a[a.index("-nic") + 1], "none")
        self.assertEqual(a[a.index("-serial") + 1], "file:/w/boot.log")


class Unchanged(unittest.TestCase):
    def test_a_sparse_disk_with_no_block_written(self):
        self.assertTrue(it.unchanged(0))
        self.assertFalse(it.unchanged(8))


class Serial(unittest.TestCase):
    def test_greenboot_passed(self):
        line = "[\x1b[0;32m  OK  \x1b[0m] Reached target \x1b[0;1;39mgreenboot-success.t…\x1b[0meenBoot Healthcheck Success Target."
        self.assertTrue(it.greenboot_passed("boot\n" + line + "\n"))
        self.assertTrue(it.greenboot_passed("systemd[1]: Reached target greenboot-success.target - GreenBoot\n"))
        self.assertFalse(it.greenboot_passed("Starting greenboot-healthcheck.service\n"))
        self.assertFalse(it.greenboot_passed(line + "\n[FAILED] Failed to start greenboot-healthcheck.service\n"))

    def test_the_firmware_started_the_nodes_entry(self):
        ok = 'BdsDxe: starting Boot0004 "Fedora" from HD(2,GPT,2C35,0x1000,0x100000)/\\EFI\\fedora\\shimx64.efi\n'
        self.assertTrue(it.started_fedora_entry(ok))
        self.assertFalse(it.started_fedora_entry('BdsDxe: starting Boot0003 "EFI Internal Shell" from Fv(7C)\n'))
        self.assertFalse(it.started_fedora_entry(
            'BdsDxe: starting Boot0002 "UEFI Misc Device" from PciRoot(0x0)/Pci(0x3,0x0)\n'))


class FromTheDisk(unittest.TestCase):
    def test_origin_reference(self):
        text = "[origin]\ncontainer-image-reference=ostree-unverified-registry:%s\n" % TARGET
        self.assertEqual(it.origin_ref(text), "ostree-unverified-registry:" + TARGET)
        self.assertIsNone(it.origin_ref("[origin]\n"))

    def test_manifest_digest_from_ostree_show(self):
        self.assertEqual(it.manifest_digest("'%s'\n" % DIGEST), DIGEST)
        self.assertIsNone(it.manifest_digest("error: No such metadata key\n"))
        self.assertIsNone(it.manifest_digest("'sha256:short'\n"))

    def test_commit_of_a_deployment(self):
        name = "a7b03c9be64412ab4e3d5602049e4f145377bbf064579e967e17c9c2bb7e44c4.0.origin"
        self.assertEqual(it.commit_of(name), name.split(".")[0])
        self.assertIsNone(it.commit_of("notacommit.0.origin"))


class Prompts(unittest.TestCase):
    def test_the_test_waits_for_the_installers_own_words(self):
        sys.path.insert(0, os.path.join(HERE, os.pardir, "installer"))
        import rikuri_install as ri
        self.assertIs(it.ri, ri)
        for text in (ri.PROMPT, ri.SEVERAL_DISKS, ri.NOTHING_ERASED, ri.INSTALLED, ri.POWER_OFF):
            self.assertTrue(text.strip())


if __name__ == "__main__":
    unittest.main()
