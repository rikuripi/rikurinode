#!/usr/bin/env python3
"""The node's USB installer: stage 1 change 5a.

    rikuri_install.py                                  install (the stick's unit runs this)
    rikuri_install.py configure --console C --target T --root R
                                                       write the stick's files (its build)

On the live system of the USB stick, on its one console, with no network: it
finds the machine's one internal disk, names it (model, size, serial), and
erases it only when the person types ERASE and presses Enter. Then it installs
the node image the stick carries, read-only, with the image's own `bootc
install to-disk`, under the fixed name `TARGET` the node updates from, and
writes the node's entry into the firmware. Every refusal, and a failed
install, erases nothing more and waits for Enter to power off. It never
chooses between disks: zero or several internal disks, or a stick it cannot
find, end the same way.

`configure` runs once, in the stick's build (image/installer/Containerfile):
the console (tty1, the screen, for the published stick; ttyS0 for CI's test),
the kernel line image-builder puts on the stick, and the target name.
Tests: image/tests/test_installer.py; in a VM: image/drill/install_test.py.
Record: docs/build-records/2026-10-29-install-media.md
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

CONF = "/usr/lib/rikuri-installer/installer.json"
STICK_STORE = "/var/lib/containers/storage"
WORK_STORE = "/run/containers/storage"
STORAGE_CONF = "/etc/containers/storage.conf"
LIVE = "/run/initramfs/live"
LABEL = "RIKURI-NODE"
REPO = "ghcr.io/rikuripi/rikurinode"
CONSOLES = {"tty1": ("console=tty0 quiet", []), "ttyS0": ("console=ttyS0", ["console=ttyS0"])}
CONFIRM = "ERASE"
RESTART_AFTER_S = 15

TITLE = "Rikuri Node installer"
ERASE_THIS = "This disk will be erased, and everything on it lost:"
PROMPT = "Type ERASE and press Enter to erase it and install Rikuri Node. Anything else stops: "
NOTHING_ERASED = "Nothing was erased."
NO_DISK = "No internal disk was found to install on. Nothing was erased."
SEVERAL_DISKS = ("This machine has more than one internal disk, and the installer does not choose between "
                 "them. Nothing was erased. Disconnect every disk but the one for the node, then start again. Found:")
NO_STICK = "The installer cannot tell which disk is this USB stick, so it erases none. Nothing was erased."
DAMAGED = "This USB stick is damaged or incomplete. Nothing was erased. Write the stick again from the downloaded file."
INSTALLING = "Installing. This takes a few minutes; do not power off."
FAILED = ("The install failed. The disk may be partly erased; nothing else was changed. "
          "Power off, then start again from the stick.")
INSTALLED = "Rikuri Node is installed. Remove the USB stick now. The machine restarts in 15 seconds."
POWER_OFF = "Press Enter to power off."


def _flag(value) -> bool:
    """lsblk's RM and RO: booleans, or "0"/"1" before util-linux 2.37."""
    return value is True or value == 1 or value == "1"


def _walk(dev):
    yield dev
    for child in dev.get("children") or []:
        yield from _walk(child)


def boot_disk(tree: dict, source: str):
    """The whole disk that holds the live medium (`source`, a device path), or None."""
    if not source:
        return None
    for dev in tree.get("blockdevices", []):
        if any(d.get("path") == source for d in _walk(dev)):
            return dev.get("name")
    return None


def candidates(tree: dict, boot: str) -> list:
    """The internal disks the node may be installed on: whole disks, not removable,
    read-only, USB, zram or the stick."""
    out = []
    for dev in tree.get("blockdevices", []):
        name = dev.get("name") or ""
        if (dev.get("type") != "disk" or _flag(dev.get("rm")) or _flag(dev.get("ro")) or dev.get("tran") == "usb"
                or name.startswith("zram") or name == boot or not dev.get("size")):
            continue
        out.append(dev)
    return out


def describe(dev: dict) -> str:
    model = (dev.get("model") or "").strip() or "unknown model"
    serial = (dev.get("serial") or "").strip()
    return "%s, %d GB, %s (%s)" % (model, round(int(dev["size"]) / 1e9),
                                   "serial " + serial if serial else "no serial", dev["path"])


def confirmed(answer) -> bool:
    return isinstance(answer, str) and answer.strip() == CONFIRM


def _check_target(target):
    if not isinstance(target, str) or not target.startswith(REPO + ":"):
        raise ValueError("the target must be %s:<fixed tag>" % REPO)
    # A tag without a number floats: latest, stable, edge (AGENTS.md, "Never in git").
    tag = target[len(REPO) + 1:]
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,127}", tag) or not re.search(r"[0-9]", tag):
        raise ValueError("the target's tag must be a fixed one, with a number: %r" % tag)


def load_conf(text: str):
    """(target, kargs) from the stick's installer.json; ValueError if it is not one this build writes."""
    conf = json.loads(text)
    target, kargs = conf["target"], conf["kargs"]
    _check_target(target)
    if not (isinstance(kargs, list) and kargs in ([], ["console=ttyS0"])):
        raise ValueError("kargs: %r" % (kargs,))
    return target, kargs


def storage_conf() -> str:
    # Probe 6d: podman refuses a store on the live system's overlayfs; its own store
    # goes in memory and the stick's is read beside it, read-only.
    return ('[storage]\ndriver = "overlay"\ngraphroot = "%s"\nrunroot = "/run/containers/runroot"\n\n'
            '[storage.options]\nadditionalimagestores = ["%s"]\n' % (WORK_STORE, STICK_STORE))


def image_ids(text: str) -> list:
    return [i["Id"] for i in json.loads(text)]


def install_argv(image_id: str, target: str, kargs: list, disk: str) -> list:
    # No --generic-image: bootupd writes the node's entry into the firmware, or the
    # disk alone falls to the firmware's shell (probe 6d, run 2).
    argv = ["podman", "run", "--rm", "--privileged", "--pid=host", "--network=none",
            "--security-opt", "label=disable",
            "-v", "/dev:/dev", "-v", "/run/containers:/run/containers",
            "-v", STICK_STORE + ":" + STICK_STORE + ":ro", "-v", STORAGE_CONF + ":" + STORAGE_CONF + ":ro",
            "-v", "/sys/firmware/efi/efivars:/sys/firmware/efi/efivars",
            image_id, "bootc", "install", "to-disk", "--skip-fetch-check", "--wipe", "--filesystem", "ext4",
            "--target-imgref", target]
    for karg in kargs:
        argv += ["--karg", karg]
    return argv + [disk]


def _stop(m, *lines) -> None:
    for line in lines:
        m.say(line)
    m.say(POWER_OFF)
    m.wait_enter()
    m.poweroff()


def run(m) -> int:
    """The install, on machine `m` (System on the stick; a stand-in in the tests)."""
    m.say(TITLE)
    try:
        target, kargs = load_conf(m.conf())
        m.write_storage_conf(storage_conf())
        ids = image_ids(m.images())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        ids = None
    if not ids or len(ids) != 1:
        _stop(m, DAMAGED)
        return 2
    try:
        tree = json.loads(m.lsblk())
        boot = boot_disk(tree, m.live_source())
    except (OSError, ValueError, subprocess.SubprocessError):
        boot = None
    if boot is None:
        _stop(m, NO_STICK)
        return 3
    disks = candidates(tree, boot)
    if not disks:
        _stop(m, NO_DISK)
        return 4
    if len(disks) > 1:
        _stop(m, SEVERAL_DISKS, *["  " + describe(d) for d in disks])
        return 5
    m.say(ERASE_THIS)
    m.say("  " + describe(disks[0]))
    if not confirmed(m.ask(PROMPT)):
        _stop(m, NOTHING_ERASED)
        return 6
    m.say(INSTALLING)
    if m.install(install_argv(ids[0], target, kargs, disks[0]["path"])) != 0:
        _stop(m, FAILED)
        return 7
    m.say(INSTALLED)
    m.sleep(RESTART_AFTER_S)
    m.reboot()
    return 0


class System:
    """The live system on the stick."""

    def conf(self):
        with open(CONF, encoding="utf-8") as f:
            return f.read()

    def write_storage_conf(self, text):
        os.makedirs(WORK_STORE, exist_ok=True)
        os.makedirs(os.path.dirname(STORAGE_CONF), exist_ok=True)
        with open(STORAGE_CONF, "w", encoding="utf-8") as f:
            f.write(text)

    def images(self):
        return subprocess.run(["podman", "images", "--format", "json"], check=True, capture_output=True,
                              text=True).stdout

    def lsblk(self):
        return subprocess.run(["lsblk", "-J", "-b", "-o", "NAME,PATH,TYPE,RM,RO,SIZE,MODEL,SERIAL,TRAN"],
                              check=True, capture_output=True, text=True).stdout

    def live_source(self):
        r = subprocess.run(["findmnt", "-n", "-o", "SOURCE", LIVE], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""

    def say(self, text):
        print(text, flush=True)

    def ask(self, prompt):
        print(prompt, end="", flush=True)
        return sys.stdin.readline()

    def wait_enter(self):
        sys.stdin.readline()

    def install(self, argv):
        return subprocess.call(argv)

    def sleep(self, seconds):
        time.sleep(seconds)

    def reboot(self):
        subprocess.call(["systemctl", "reboot"])

    def poweroff(self):
        subprocess.call(["systemctl", "poweroff"])


def iso_yaml(console: str) -> str:
    # Probe 6: v87 copies the line as written (no ${...}); the squashfs carries no
    # SELinux labels (the installed node's are written by bootc from its policy).
    line = "/images/pxeboot/vmlinuz root=live:CDLABEL=%s rd.live.image selinux=0 rd.emergency=poweroff %s" % (
        LABEL, CONSOLES[console][0])
    return ('label: "%s"\ngrub2:\n  timeout: 1\n  entries:\n    - name: "Install Rikuri Node"\n'
            '      linux: "%s"\n      initrd: "/images/pxeboot/initrd.img"\n' % (LABEL, line))


def unit(console: str) -> str:
    # Probe 6d, run 1: a getty on the same console hangs it up; the stick masks them.
    return ("[Unit]\nDescription=%s\nAfter=multi-user.target\n\n[Service]\nType=oneshot\n"
            "ExecStart=/usr/bin/python3 -I /usr/lib/rikuri-installer/rikuri_install.py\n"
            "StandardInput=tty\nStandardOutput=tty\nStandardError=tty\nTTYPath=/dev/%s\n"
            "TTYReset=yes\nTTYVHangup=yes\n\n[Install]\nWantedBy=multi-user.target\n" % (TITLE, console))


def configure(console: str, target: str, root: str) -> None:
    if console not in CONSOLES:
        raise ValueError("the console must be one of %s" % ", ".join(sorted(CONSOLES)))
    _check_target(target)
    files = {
        "usr/lib/image-builder/bootc/iso.yaml": iso_yaml(console),
        "usr/lib/systemd/system/rikuri-installer.service": unit(console),
        CONF.lstrip("/"): json.dumps({"target": target, "kargs": CONSOLES[console][1]}) + "\n",
    }
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def main(argv) -> int:
    if argv[:1] == ["configure"]:
        import argparse
        p = argparse.ArgumentParser(prog="rikuri_install.py configure")
        p.add_argument("--console", required=True)
        p.add_argument("--target", required=True)
        p.add_argument("--root", required=True)
        a = p.parse_args(argv[1:])
        configure(a.console, a.target, a.root)
        return 0
    subprocess.call(["dmesg", "-n", "1"])   # kernel messages off the console while it asks
    return run(System())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
