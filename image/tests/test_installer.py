"""Tests for image/installer/rikuri_install.py, the node's USB installer.

Its rules run here, through a stand-in for the machine: which disk it may
erase (exactly one internal disk, never the stick, a removable, read-only or
USB disk, or zram), the one answer that erases it (`ERASE`), the command that
installs (from the stick's read-only store, offline, with the firmware entry
written: no `--generic-image`), and that every refusal and every failure
erases nothing and waits for power-off. Also what `configure` writes into the
stick at build time (its console, its kernel line, the target name) and what
it refuses, and the installer's Containerfile. The install itself runs only in
CI (image/drill/install_test.py, .github/workflows/image.yml, job install).
No VM, container, disk or network here.
Record: docs/build-records/2026-10-29-install-media.md
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALLER = os.path.join(HERE, os.pardir, "installer")
sys.path.insert(0, INSTALLER)
import rikuri_install as ri  # noqa: E402

TARGET = "ghcr.io/rikuripi/rikurinode:44.20261030.1"
IMAGE_ID = "f" * 64


def disk(name, size=1_000_204_886_016, rm=False, ro=False, tran="nvme", model="Samsung SSD 980 1TB",
         serial="S64ANS0T", type_="disk", children=None):
    d = {"name": name, "path": "/dev/" + name, "type": type_, "rm": rm, "ro": ro, "size": size,
         "model": model, "serial": serial, "tran": tran}
    if children:
        d["children"] = children
    return d


def part(name):
    return {"name": name, "path": "/dev/" + name, "type": "part", "rm": False, "ro": False, "size": 1,
            "model": None, "serial": None, "tran": None}


STICK = disk("sda", size=32_000_000_000, rm=True, ro=False, tran="usb", model="SanDisk 3.2Gen1",
             serial="0401", children=[part("sda1"), part("sda2")])
NVME = disk("nvme0n1", children=[part("nvme0n1p1")])
SATA = disk("sdb", tran="sata", model="CT1000MX500SSD1", serial="2201E5F")
ZRAM = disk("zram0", size=8_000_000_000, tran=None, model=None, serial=None)
LOOP = disk("loop0", type_="loop", tran=None)
DVD = disk("sr0", type_="rom", rm=True, ro=True, tran="sata")


def lsblk(*devices):
    return json.dumps({"blockdevices": list(devices)})


def images(*ids):
    return json.dumps([{"Id": i, "Names": ["ghcr.io/rikuripi/rikurinode@sha256:" + "b" * 64]} for i in ids])


CONF = json.dumps({"target": TARGET, "kargs": []})


class Machine:
    """A stand-in for the live system: what it reports, what it is told to do."""

    def __init__(self, devices=(STICK, NVME, ZRAM, LOOP), live="/dev/sda1", answer="ERASE",
                 imgs=(IMAGE_ID,), install_rc=0, conf=CONF):
        self.devices, self.live, self.answer, self.imgs = devices, live, answer, imgs
        self.install_rc, self.conf_text = install_rc, conf
        self.said, self.installs, self.events, self.storage = [], [], [], None
        self.asked = []

    def conf(self):
        return self.conf_text

    def write_storage_conf(self, text):
        self.storage = text

    def images(self):
        return images(*self.imgs)

    def lsblk(self):
        return lsblk(*self.devices)

    def live_source(self):
        return self.live

    def say(self, text):
        self.said.append(text)

    def ask(self, prompt):
        self.asked.append(prompt)
        return self.answer

    def wait_enter(self):
        self.events.append("enter")

    def install(self, argv):
        self.installs.append(argv)
        return self.install_rc

    def sleep(self, seconds):
        self.events.append("sleep %d" % seconds)

    def reboot(self):
        self.events.append("reboot")

    def poweroff(self):
        self.events.append("poweroff")

    def text(self):
        return "\n".join(self.said)


class Candidates(unittest.TestCase):
    def names(self, *devices, boot="sda"):
        return [x["name"] for x in ri.candidates(json.loads(lsblk(*devices)), boot)]

    def test_the_one_internal_disk(self):
        self.assertEqual(self.names(STICK, NVME, ZRAM, LOOP, DVD), ["nvme0n1"])

    def test_never_the_stick_even_if_it_looks_internal(self):
        fixed = disk("sda", rm=False, tran="sata", children=[part("sda1")])
        self.assertEqual(self.names(fixed, NVME, boot="sda"), ["nvme0n1"])

    def test_never_removable_read_only_usb_or_zram(self):
        self.assertEqual(self.names(disk("sdc", rm=True, tran="sata"), disk("sdd", ro=True),
                                    disk("sde", tran="usb"), ZRAM, boot="sda"), [])

    def test_lsblk_flags_as_strings_too(self):
        # util-linux before 2.37 writes "0"/"1"; both forms mean the same.
        old = dict(NVME, rm="1")
        self.assertEqual(self.names(old, boot="sda"), [])
        self.assertEqual(self.names(dict(NVME, rm="0", ro="0"), boot="sda"), ["nvme0n1"])

    def test_never_a_disk_with_no_size(self):
        # A card reader's empty slot, a missing medium: lsblk lists it with size 0.
        self.assertEqual(self.names(disk("sdf", size=0), disk("sdg", size=None), boot="sda"), [])
        self.assertEqual(self.names(disk("sdf", size=0), NVME, boot="sda"), ["nvme0n1"])

    def test_two_internal_disks_are_both_candidates(self):
        self.assertEqual(self.names(STICK, NVME, SATA), ["nvme0n1", "sdb"])


class BootDisk(unittest.TestCase):
    def test_the_disk_that_holds_the_live_medium(self):
        tree = json.loads(lsblk(STICK, NVME))
        self.assertEqual(ri.boot_disk(tree, "/dev/sda1"), "sda")
        self.assertEqual(ri.boot_disk(tree, "/dev/sda"), "sda")

    def test_unknown_when_nothing_holds_it(self):
        tree = json.loads(lsblk(STICK, NVME))
        self.assertIsNone(ri.boot_disk(tree, "/dev/sr0"))
        self.assertIsNone(ri.boot_disk(tree, ""))


class Describe(unittest.TestCase):
    def test_model_size_in_gb_serial_and_path(self):
        self.assertEqual(ri.describe(NVME), "Samsung SSD 980 1TB, 1000 GB, serial S64ANS0T (/dev/nvme0n1)")

    def test_missing_model_and_serial_are_said(self):
        self.assertEqual(ri.describe(disk("vda", size=21_474_836_480, model=None, serial=None, tran=None)),
                         "unknown model, 21 GB, no serial (/dev/vda)")


class Confirmed(unittest.TestCase):
    def test_only_erase_exactly(self):
        for answer in ("ERASE", "ERASE\n", "  ERASE  "):
            self.assertTrue(ri.confirmed(answer), repr(answer))
        for answer in ("", "\n", "erase", "Erase", "ERASE!", "yes", "y", "ERASE ERASE", "E RASE", None):
            self.assertFalse(ri.confirmed(answer), repr(answer))


class InstallArgv(unittest.TestCase):
    def setUp(self):
        self.argv = ri.install_argv(IMAGE_ID, TARGET, ["console=ttyS0"], "/dev/nvme0n1")

    def test_runs_the_sticks_image_offline_with_the_firmware_entry(self):
        a = self.argv
        self.assertEqual(a[:3], ["podman", "run", "--rm"])
        self.assertIn("--network=none", a)
        self.assertIn("--privileged", a)
        i = a.index(IMAGE_ID)
        self.assertEqual(a[i + 1:i + 4], ["bootc", "install", "to-disk"])
        self.assertNotIn("--generic-image", a)   # probe 6d: the disk alone fell to the UEFI shell
        self.assertIn("/sys/firmware/efi/efivars:/sys/firmware/efi/efivars", a)
        self.assertIn("--wipe", a)
        self.assertIn("--skip-fetch-check", a)
        self.assertEqual(a[a.index("--target-imgref") + 1], TARGET)
        self.assertEqual(a[a.index("--karg") + 1], "console=ttyS0")
        self.assertEqual(a[-1], "/dev/nvme0n1")

    def test_the_sticks_store_is_read_only(self):
        mounts = [self.argv[i + 1] for i, x in enumerate(self.argv) if x == "-v"]
        self.assertIn(ri.STICK_STORE + ":" + ri.STICK_STORE + ":ro", mounts)
        self.assertIn(ri.STORAGE_CONF + ":" + ri.STORAGE_CONF + ":ro", mounts)
        self.assertIn("/run/containers:/run/containers", mounts)

    def test_the_container_sees_the_hosts_processes_and_is_not_confined(self):
        # bootc install to-disk needs both, on a live system with SELinux off.
        self.assertIn("--pid=host", self.argv)
        self.assertEqual(self.argv[self.argv.index("--security-opt") + 1], "label=disable")

    def test_no_kargs_on_the_stick(self):
        self.assertNotIn("--karg", ri.install_argv(IMAGE_ID, TARGET, [], "/dev/nvme0n1"))


class StorageConf(unittest.TestCase):
    def test_podmans_store_in_memory_the_sticks_read_only_beside_it(self):
        text = ri.storage_conf()
        self.assertIn('graphroot = "/run/containers/storage"', text)
        self.assertIn('additionalimagestores = ["/var/lib/containers/storage"]', text)
        self.assertIn('driver = "overlay"', text)


class Run(unittest.TestCase):
    def test_erase_installs_on_the_one_disk_then_restarts(self):
        m = Machine()
        self.assertEqual(ri.run(m), 0)
        self.assertEqual(len(m.installs), 1)
        self.assertEqual(m.installs[0], ri.install_argv(IMAGE_ID, TARGET, [], "/dev/nvme0n1"))
        self.assertIn(ri.describe(NVME), m.text())
        self.assertIn(ri.INSTALLED, m.text())
        self.assertEqual(m.events, ["sleep 15", "reboot"])
        self.assertEqual(m.storage, ri.storage_conf())

    def test_it_asks_once_after_naming_the_disk(self):
        m = Machine()
        ri.run(m)
        self.assertEqual(m.asked, [ri.PROMPT])
        self.assertLess(m.said.index(next(s for s in m.said if ri.describe(NVME) in s)), len(m.said))

    def refused(self, m, message, installs=0):
        rc = ri.run(m)
        self.assertNotEqual(rc, 0)
        self.assertEqual(len(m.installs), installs, "nothing erased, or only by the one failed install")
        self.assertIn(message, m.text())
        self.assertIn(ri.POWER_OFF, m.text())
        self.assertEqual(m.events[-2:], ["enter", "poweroff"])
        self.assertNotIn("reboot", m.events)
        return rc

    def test_any_other_answer_erases_nothing(self):
        for answer in ("", "no", "erase", "ERASE!"):
            m = Machine(answer=answer)
            self.refused(m, ri.NOTHING_ERASED)

    def test_no_internal_disk(self):
        m = Machine(devices=(STICK, ZRAM))
        self.refused(m, ri.NO_DISK)
        self.assertEqual(m.asked, [])

    def test_several_internal_disks_are_named_and_none_erased(self):
        m = Machine(devices=(STICK, NVME, SATA))
        self.refused(m, ri.SEVERAL_DISKS)
        self.assertIn(ri.describe(NVME), m.text())
        self.assertIn(ri.describe(SATA), m.text())
        self.assertEqual(m.asked, [])

    def test_the_stick_cannot_be_found(self):
        m = Machine(live="/dev/sr0")
        self.refused(m, ri.NO_STICK)
        self.assertEqual(m.asked, [])

    def test_not_exactly_one_image_on_the_stick(self):
        for imgs in ((), (IMAGE_ID, "e" * 64)):
            m = Machine(imgs=imgs)
            self.refused(m, ri.DAMAGED)
            self.assertEqual(m.asked, [])

    def test_a_bad_config_is_a_damaged_stick(self):
        for conf in ("", "{", json.dumps({"target": "quay.io/x/y:1", "kargs": []}),
                     json.dumps({"target": TARGET, "kargs": ["init=/bin/sh"]}),
                     json.dumps({"kargs": []}), json.dumps({"target": TARGET}),   # a key missing
                     "[]", "null", '"text"',                                      # not an object
                     json.dumps({"target": 5, "kargs": []}), json.dumps({"target": None, "kargs": []})):
            m = Machine(conf=conf)
            self.refused(m, ri.DAMAGED)

    def test_a_tool_that_fails_is_a_refusal_not_a_crash(self):
        fail = subprocess.CalledProcessError(1, "tool")
        for method, message in (("images", ri.DAMAGED), ("write_storage_conf", ri.DAMAGED), ("conf", ri.DAMAGED),
                                ("lsblk", ri.NO_STICK), ("live_source", ri.NO_STICK)):
            for error in (fail, OSError("gone")):
                m = Machine()
                def raises(*_, error=error):
                    raise error
                setattr(m, method, raises)
                self.refused(m, message)
                self.assertEqual(m.asked, [])

    def test_output_it_cannot_read_is_a_refusal_not_a_crash(self):
        m = Machine()
        m.lsblk = lambda: "not json"
        self.refused(m, ri.NO_STICK)
        m = Machine()
        m.images = lambda: "not json"
        self.refused(m, ri.DAMAGED)

    def test_a_failed_install_says_so_and_waits(self):
        m = Machine(install_rc=1)
        self.refused(m, ri.FAILED, installs=1)


class LoadConf(unittest.TestCase):
    def test_target_and_kargs(self):
        self.assertEqual(ri.load_conf(json.dumps({"target": TARGET, "kargs": ["console=ttyS0"]})),
                         (TARGET, ["console=ttyS0"]))

    def test_refuses_another_repository_or_a_moving_name(self):
        # Same length as the repository, so only the name check refuses them (mutant "target: any repo").
        for target in ("quay.io/rikuripi/rikurinode:44.1", "ghcr.io/rikuripi/rikurinodf:44.1",
                       "ghcr.io/rikuripi/other:1", "ghcr.io/rikuripi/rikurinode", "ghcr.io/rikuripi/rikurinode:",
                       "ghcr.io/rikuripi/rikurinode:a b", "docker://ghcr.io/rikuripi/rikurinode:1",
                       "ghcr.io/rikuripi/rikurinode:latest",
                       "ghcr.io/rikuripi/rikurinodeX1", "ghcr.io/rikuripi/rikurinode1:44.1"):   # another repository
            with self.assertRaises(ValueError, msg=target):
                ri.load_conf(json.dumps({"target": target, "kargs": []}))

    def tag(self, tag):
        return ri.load_conf(json.dumps({"target": ri.REPO + ":" + tag, "kargs": []}))

    def test_a_tag_without_a_number_floats(self):
        # AGENTS.md, "Never in git": latest, stable, lts and other tags without a number float.
        for tag in ("latest", "stable", "lts", "Latest", "edge", "main", "install-test", "rc", "_", "a.b-c"):
            with self.assertRaises(ValueError, msg=tag):
                self.tag(tag)

    def test_fixed_tags_are_accepted(self):
        for tag in ("44.20261030.1", "44", "install-test-1", "v1", "_1", "1" * 128):
            self.assertEqual(self.tag(tag)[0], ri.REPO + ":" + tag)

    def test_a_tag_is_what_a_registry_accepts(self):
        for tag in (".1", "-1", "1/2", "1@2", "1:2", "1 2", "1" * 129, "1\n", "\u0661"):   # the last: a non-ASCII digit
            with self.assertRaises(ValueError, msg=tag):
                self.tag(tag)

    def test_refuses_any_karg_but_the_serial_console(self):
        for kargs in (["init=/bin/sh"], ["console=ttyS0", "console=ttyS0"], "console=ttyS0"):
            with self.assertRaises(ValueError, msg=kargs):
                ri.load_conf(json.dumps({"target": TARGET, "kargs": kargs}))


class Configure(unittest.TestCase):
    def files(self, console, target=TARGET):
        root = tempfile.mkdtemp()
        ri.configure(console, target, root)
        out = {}
        for dirpath, _, names in os.walk(root):
            for n in names:
                p = os.path.join(dirpath, n)
                with open(p, encoding="utf-8") as f:
                    out[os.path.relpath(p, root)] = f.read()
        return out

    def test_the_published_stick_uses_the_screen_and_adds_no_karg(self):
        f = self.files("tty1")
        iso = f["usr/lib/image-builder/bootc/iso.yaml"]
        self.assertIn('label: "RIKURI-NODE"', iso)
        line = re.search(r'linux: "([^"]+)"', iso).group(1)
        self.assertEqual(line.split(), ["/images/pxeboot/vmlinuz", "root=live:CDLABEL=RIKURI-NODE", "rd.live.image",
                                        "selinux=0", "rd.emergency=poweroff", "console=tty0", "quiet"])
        self.assertIn('initrd: "/images/pxeboot/initrd.img"', iso)
        self.assertNotIn("${", iso)   # probe 6: v87 fills no ${...}
        self.assertIn("TTYPath=/dev/tty1", f["usr/lib/systemd/system/rikuri-installer.service"])
        self.assertEqual(json.loads(f["usr/lib/rikuri-installer/installer.json"]), {"target": TARGET, "kargs": []})

    def test_cis_stick_uses_the_serial_console(self):
        f = self.files("ttyS0")
        line = re.search(r'linux: "([^"]+)"', f["usr/lib/image-builder/bootc/iso.yaml"]).group(1)
        self.assertEqual(line.split()[-1], "console=ttyS0")
        self.assertNotIn("quiet", line)
        self.assertIn("TTYPath=/dev/ttyS0", f["usr/lib/systemd/system/rikuri-installer.service"])
        self.assertEqual(json.loads(f["usr/lib/rikuri-installer/installer.json"])["kargs"], ["console=ttyS0"])

    def test_the_unit_owns_its_console(self):
        unit = self.files("tty1")["usr/lib/systemd/system/rikuri-installer.service"]
        self.assertIn("StandardInput=tty", unit)
        self.assertIn("StandardOutput=tty", unit)
        self.assertIn("TTYReset=yes", unit)
        self.assertIn("TTYVHangup=yes", unit)
        self.assertIn("ExecStart=/usr/bin/python3 -I /usr/lib/rikuri-installer/rikuri_install.py", unit)
        self.assertIn("WantedBy=multi-user.target", unit)

    def test_refuses_another_console_or_target(self):
        for console in ("tty2", "ttyS1", "", "tty1 quiet"):
            with self.assertRaises(ValueError, msg=console):
                ri.configure(console, TARGET, tempfile.mkdtemp())
        with self.assertRaises(ValueError):
            ri.configure("tty1", "ghcr.io/rikuripi/rikurinode:latest", tempfile.mkdtemp())


class Containerfile(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(INSTALLER, "Containerfile"), encoding="utf-8") as f:
            self.text = f.read()
        with open(os.path.join(HERE, os.pardir, "Containerfile"), encoding="utf-8") as f:
            self.node = f.read()

    def test_the_nodes_own_pinned_base(self):
        base = re.findall(r"(?m)^FROM (\S+)", self.text)
        self.assertEqual(base, re.findall(r"(?m)^FROM (\S+)", self.node))
        self.assertRegex(base[0], r"@sha256:[0-9a-f]{64}$")

    def test_the_live_module_and_the_iso_tools(self):
        for pkg in ("dracut-live", "squashfs-tools", "xorriso", "isomd5sum", "grub2-efi-x64-cdboot", "python3"):
            self.assertRegex(self.text, r"dnf install [^\n]*\b%s\b" % re.escape(pkg))
        self.assertIn("dmsquash-live", self.text)

    def test_configured_from_the_build_arguments(self):
        self.assertIn("ARG CONSOLE", self.text)
        self.assertIn("ARG TARGET", self.text)
        self.assertIn('rikuri_install.py configure --console "$CONSOLE" --target "$TARGET" --root /', self.text)
        self.assertIn("systemctl enable rikuri-installer.service", self.text)

    def test_no_logins_and_no_network_on_the_stick(self):
        mask = " ".join(re.findall(r"systemctl mask ([^\n&|]+)", self.text))
        for unit in ("getty@tty1.service", "autovt@tty1.service", "serial-getty@ttyS0.service",
                     "sshd.service", "sshd.socket", "NetworkManager.service"):
            self.assertIn(unit, mask.split(), unit)


if __name__ == "__main__":
    unittest.main()
