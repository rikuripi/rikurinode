#!/usr/bin/env python3
"""CI's install test of the node's USB installer: stage 1 change 5a.

    sudo install_test.py --iso <stick.iso> --target <name> --digest <sha256:…> --workdir <dir> --artifacts <dir>

Runs only on an x86_64 Linux runner with KVM, QEMU, OVMF and ostree, as root
(.github/workflows/image.yml, job install). It boots the ISO under UEFI as a
removable, read-only USB stick, with no network, and types at the installer
through the VM's serial console (a socket it reads all the time, and logs), waiting
for the installer's own words (imported from rikuri_install.py). It fails on
any miss:

  two disks   two blank disks: the installer refuses and names both; Enter
              powers off; neither disk has a block written.
  no          one blank disk, answered `no`: "Nothing was erased"; Enter
              powers off; the disk has no block written.
  erase       one blank disk, answered `ERASE`: installed, and the VM restarts
              (QEMU exits on it). Then the disk alone, with the firmware
              settings the install left (as on the machine once the stick is
              pulled): the firmware starts the node's own entry ("Fedora") and
              greenboot passes. Last, read from the disk: the origin names the
              target, and the deployment's manifest digest is the embedded
              image's (--digest).

The stick is built with CONSOLE=ttyS0 for this test; the published one uses
the screen. Evidence (the consoles' logs, what was read) goes to --artifacts.
Record: docs/build-records/2026-10-29-install-media.md
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "installer"))   # python3 -I leaves these out
import rikuri_install as ri  # noqa: E402

OVMF_CODE = "/usr/share/OVMF/OVMF_CODE_4M.fd"
OVMF_VARS = "/usr/share/OVMF/OVMF_VARS_4M.fd"
DISK_SIZE = 20 * 1024 ** 3
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
GREENBOOT_OK = re.compile(r"Reached target\s+greenboot-success\.t")
GREENBOOT_FAILED = re.compile(r"Failed to start\s+greenboot-healthcheck|greenboot-healthcheck\.service: Failed")
FEDORA_ENTRY = re.compile(r'BdsDxe: starting Boot[0-9A-F]{4} "Fedora" from HD\(')
MARK = 40   # the first characters of an installer line; a kernel line may split the rest


def _common(vars_fd: str) -> list:
    return ["qemu-system-x86_64", "-enable-kvm", "-machine", "q35", "-cpu", "host", "-smp", "2", "-m", "8192",
            "-drive", "if=pflash,format=raw,unit=0,readonly=on,file=" + OVMF_CODE,
            "-drive", "if=pflash,format=raw,unit=1,file=" + vars_fd]


def stick_argv(iso: str, disks: list, vars_fd: str, sock: str) -> list:
    argv = _common(vars_fd) + [
        "-device", "qemu-xhci",
        "-drive", "if=none,id=stick,format=raw,readonly=on,file=" + iso,
        "-device", "usb-storage,drive=stick,removable=on"]
    for disk in disks:
        argv += ["-drive", "if=virtio,format=raw,file=" + disk]
    return argv + ["-nic", "none", "-display", "none",
                   "-chardev", "socket,id=con,path=%s,server=on,wait=off" % sock,
                   "-serial", "chardev:con", "-no-reboot"]


def disk_argv(disk: str, vars_fd: str, log: str) -> list:
    return _common(vars_fd) + ["-drive", "if=virtio,format=raw,file=" + disk,
                               "-nic", "none", "-display", "none", "-serial", "file:" + log, "-no-reboot"]


def unchanged(blocks: int) -> bool:
    """A disk made sparse is unchanged while no block of it is allocated."""
    return blocks == 0


def clean(text: str) -> str:
    return ANSI.sub("", text.replace("\r", ""))


def greenboot_passed(serial: str) -> bool:
    text = clean(serial)
    return bool(GREENBOOT_OK.search(text)) and not GREENBOOT_FAILED.search(text)


def started_fedora_entry(serial: str) -> bool:
    return bool(FEDORA_ENTRY.search(clean(serial)))


def origin_ref(text: str):
    m = re.search(r"(?m)^container-image-reference=(\S+)$", text)
    return m.group(1) if m else None


def manifest_digest(text: str):
    m = re.search(r"'(sha256:[0-9a-f]{64})'", text)
    return m.group(1) if m else None


def commit_of(name: str):
    m = re.fullmatch(r"([0-9a-f]{64})\.\d+\.origin", name)
    return m.group(1) if m else None


class Failed(Exception):
    pass


class Console:
    """The VM's serial console: typed into through its socket. A reader drains the socket
    all the time and writes the log itself: unread, the socket fills and the guest stalls
    on its console writes, and QEMU's own log of it repeats characters (CI run 83)."""

    def __init__(self, sock: str, log: str, proc):
        self.log, self.proc, self.conn = log, proc, None
        deadline = time.time() + 30
        while self.conn is None:
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(sock)
                self.conn = s
            except OSError:
                if time.time() > deadline:
                    raise Failed("the VM's console socket did not open")
                time.sleep(0.5)
        self.read, self.lock = bytearray(), threading.Lock()
        self.reader = threading.Thread(target=self._drain, daemon=True)
        self.reader.start()

    def _drain(self):
        with open(self.log, "wb") as f:
            while True:
                try:
                    data = self.conn.recv(65536)
                except OSError:
                    return
                if not data:
                    return
                f.write(data)
                f.flush()
                with self.lock:
                    self.read += data

    def text(self) -> str:
        with self.lock:
            data = bytes(self.read)
        return clean(data.decode("utf-8", errors="replace"))

    def wait_for(self, line: str, timeout: int, after: int = 0) -> int:
        """Wait until the installer's `line` appears after offset `after`; its end offset."""
        mark = line[:MARK]
        deadline = time.time() + timeout
        while time.time() < deadline:
            text = self.text()
            i = text.find(mark, after)
            if i >= 0:
                return i + len(mark)
            if self.proc.poll() is not None:
                raise Failed("the VM ended before the installer said %r" % mark)
            time.sleep(1)
        raise Failed("no %r on the console within %d s" % (mark, timeout))

    def send(self, line: str) -> None:
        self.conn.sendall((line + "\r").encode())

    def close(self):
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.conn.close()
        self.reader.join(10)


class Test:
    def __init__(self, a):
        self.a = a
        os.makedirs(a.workdir, exist_ok=True)
        os.makedirs(a.artifacts, exist_ok=True)
        self.results = []

    def log(self, msg):
        print("[install-test] " + msg, flush=True)

    def disk(self, name):
        path = os.path.join(self.a.workdir, name + ".raw")
        with open(path, "wb") as f:
            f.truncate(DISK_SIZE)
        return path

    def vars(self, name):
        path = os.path.join(self.a.workdir, name + "-vars.fd")
        shutil.copyfile(OVMF_VARS, path)
        return path

    def boot_stick(self, name, disks, vars_fd):
        sock = os.path.join(self.a.workdir, name + ".sock")
        log = os.path.join(self.a.artifacts, name + "-console.log")
        proc = subprocess.Popen(stick_argv(self.a.iso, disks, vars_fd, sock))
        return proc, Console(sock, log, proc)

    def ended(self, proc, timeout):
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise Failed("the VM did not end within %d s" % timeout)

    def untouched(self, *disks):
        for disk in disks:
            blocks = os.stat(disk).st_blocks
            if not unchanged(blocks):
                raise Failed("%s was written: %d blocks" % (os.path.basename(disk), blocks))

    def case(self, name, fn):
        self.log("case %s" % name)
        try:
            fn()
            self.results.append((name, "pass", ""))
            self.log("case %s: pass" % name)
        except Failed as e:
            self.results.append((name, "FAIL", str(e)))
            self.log("case %s: FAIL: %s" % (name, e))
        finally:
            subprocess.call(["pkill", "-f", "qemu-system-x86_64"])

    def two_disks(self):
        a, b = self.disk("two-a"), self.disk("two-b")
        proc, con = self.boot_stick("two-disks", [a, b], self.vars("two"))
        at = con.wait_for(ri.SEVERAL_DISKS, 900)
        text = con.text()
        if text.count("unknown model, 21 GB") < 2:
            raise Failed("the refusal does not name both disks")
        con.wait_for(ri.POWER_OFF, 60, at)
        if ri.PROMPT[:MARK] in con.text():
            raise Failed("it asked to erase")
        con.send("")
        self.ended(proc, 180)
        self.untouched(a, b)

    def answered_no(self):
        a = self.disk("no")
        proc, con = self.boot_stick("no", [a], self.vars("no"))
        at = con.wait_for(ri.PROMPT, 900)
        con.send("no")
        at = con.wait_for(ri.NOTHING_ERASED, 60, at)
        con.wait_for(ri.POWER_OFF, 60, at)
        con.send("")
        self.ended(proc, 180)
        self.untouched(a)

    def erase(self):
        a, v = self.disk("erase"), self.vars("erase")
        proc, con = self.boot_stick("erase", [a], v)
        at = con.wait_for(ri.PROMPT, 900)
        con.send(ri.CONFIRM)
        con.wait_for(ri.INSTALLED, 1800, at)
        self.ended(proc, 120)   # it restarts, and -no-reboot ends the VM
        if unchanged(os.stat(a).st_blocks):
            raise Failed("the disk is empty after the install")
        self.alone(a, v)
        self.read_disk(a)

    def alone(self, disk, vars_fd):
        log = os.path.join(self.a.artifacts, "erase-alone-console.log")
        proc = subprocess.Popen(disk_argv(disk, vars_fd, log))
        deadline = time.time() + 900
        text = ""
        while time.time() < deadline and proc.poll() is None:
            time.sleep(5)
            with open(log, encoding="utf-8", errors="replace") as f:
                text = f.read()
            if greenboot_passed(text) or "Shell>" in text or GREENBOOT_FAILED.search(clean(text)):
                break
        proc.kill()
        proc.wait()
        if not started_fedora_entry(text):
            raise Failed("the firmware did not start the node's entry \"Fedora\"")
        if not greenboot_passed(text):
            raise Failed("greenboot did not pass on the disk alone")

    def read_disk(self, disk):
        loop = subprocess.run(["losetup", "-fP", "--show", disk], check=True, capture_output=True,
                              text=True).stdout.strip()
        mnt = os.path.join(self.a.workdir, "root")
        os.makedirs(mnt, exist_ok=True)
        found = {}
        try:
            subprocess.call(["udevadm", "settle"])
            for p in sorted(glob.glob(loop + "p*")):
                if subprocess.call(["mount", "-o", "ro", p, mnt], stderr=subprocess.DEVNULL) != 0:
                    continue
                try:
                    origins = glob.glob(os.path.join(mnt, "ostree/deploy/*/deploy/*.origin"))
                    if len(origins) == 1:
                        with open(origins[0], encoding="utf-8") as f:
                            found["origin"] = f.read()
                        commit = commit_of(os.path.basename(origins[0]))
                        r = subprocess.run(["ostree", "--repo=" + os.path.join(mnt, "ostree/repo"), "show",
                                            "--print-metadata-key=ostree.manifest-digest", commit or "-"],
                                           capture_output=True, text=True)
                        found["digest"] = r.stdout + r.stderr
                    elif origins:
                        found["origins"] = origins
                finally:
                    subprocess.call(["umount", mnt])
        finally:
            subprocess.call(["losetup", "-d", loop])
        with open(os.path.join(self.a.artifacts, "erase-read-from-disk.json"), "w", encoding="utf-8") as f:
            json.dump(found, f, indent=2)
        if "origins" in found or "origin" not in found:
            raise Failed("not exactly one deployment on the disk: %r" % found)
        want = "ostree-unverified-registry:" + self.a.target
        if origin_ref(found["origin"]) != want:
            raise Failed("the origin is %r, not %r" % (origin_ref(found["origin"]), want))
        if manifest_digest(found["digest"]) != self.a.digest:
            raise Failed("the deployment's digest is %r, not %r" % (found["digest"].strip(), self.a.digest))

    def main(self):
        self.case("two disks", self.two_disks)
        self.case("no", self.answered_no)
        self.case("erase", self.erase)
        with open(os.path.join(self.a.artifacts, "results.json"), "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        lines = ["### Install test"] + ["- %s: %s %s" % r for r in self.results]
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        print("\n".join(lines))
        return 0 if all(r[1] == "pass" for r in self.results) else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--iso", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--digest", required=True)
    p.add_argument("--workdir", required=True)
    p.add_argument("--artifacts", required=True)
    return Test(p.parse_args(argv)).main()


if __name__ == "__main__":
    sys.exit(main())
