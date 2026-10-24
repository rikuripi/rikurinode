#!/usr/bin/env python3
"""The OS image's rollback drill, in a VM: stage 1 changes 3 and 4.

    vm_drill.py --image <local image> --workdir <dir> --artifacts <dir>

Runs only on an x86_64 Linux runner with KVM, sudo, podman, QEMU and OVMF
(.github/workflows/image.yml, job drill). It installs the image with the
image's own `bootc install to-disk` onto a raw disk, boots it under QEMU, and
checks, failing on any miss:

  first boot   greenboot passes; its journal shows Fedora's DNS check skipped
               (D9); the unapplied-update check ran.
  case 1       a staged update whose required check fails rolls back by itself
               to the installed image, with a /var marker intact.
  case 2b      an update whose finalize fails leaves the node on the installed
               image, with the check's "was never applied" in the journal,
               also after one more reboot (D22, greenboot-rs #219).
  case 3       a power cut after greenboot armed its trigger and before the
               update was written does the same. The cut is deterministic: a
               drop-in in /run holds finalize's stop (greenboot's trigger stops
               first), and the VM is killed during the hold.

The VM gets a key made for this run (root, on the drill's disk only; the image
is unchanged) and a user-mode network restricted to one forwarded SSH port on
loopback: it has no outbound network. The cases are those of
docs/build-records/2026-10-21-greenboot-drill-parallels.md, run there by hand.
Evidence goes to --artifacts. Record: docs/build-records/2026-10-22-ci-vm-drill.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

OVMF_CODE = "/usr/share/OVMF/OVMF_CODE_4M.fd"
OVMF_VARS = "/usr/share/OVMF/OVMF_VARS_4M.fd"
PORT = 2222
DISK_SIZE = "20G"
POWER_CUT_AFTER_S = 30
DROPIN_DIR = "/run/systemd/system/ostree-finalize-staged.service.d"
DROPIN = DROPIN_DIR + "/99-drill.conf"
FINALIZE_FAILS = "[Service]\nExecStop=\nExecStop=/usr/bin/false\n"
FINALIZE_HOLDS = ("[Service]\nExecStop=\nExecStop=/usr/bin/sleep 240\n"
                  "ExecStop=/usr/bin/ostree admin finalize-staged\n")
MARKER = "/var/drill-marker"
NEVER_APPLIED = "was never applied"
DNS_SKIPPED = "Skipping disabled script: 01_repository_dns_check.sh"
ROLLED_BACK = "Boot counter exhausted and next-deployment-id is set - initiating rollback"
TRIGGER_STOPPED = re.compile(r"Stopped [^\n]*Greenboot Rollback trigger")
SUBID_LINE = "containers:2147483647:2147483648"
SUBID_FILES = ("/etc/subuid", "/etc/subgid")


class DrillFailure(Exception):
    pass


def qemu_argv(disk: str, vars_fd: str, serial_log: str, port: int, pidfile: str) -> list:
    return ["qemu-system-x86_64", "-enable-kvm", "-machine", "q35", "-cpu", "host",
            "-smp", "2", "-m", "4096",
            "-drive", "if=pflash,format=raw,unit=0,readonly=on,file=" + OVMF_CODE,
            "-drive", "if=pflash,format=raw,unit=1,file=" + vars_fd,
            "-drive", "if=virtio,format=raw,file=" + disk,
            "-netdev", "user,id=n0,restrict=on,hostfwd=tcp:127.0.0.1:%d-:22" % port,
            "-device", "virtio-net-pci,netdev=n0",
            "-serial", "file:" + serial_log, "-display", "none",
            "-daemonize", "-pidfile", pidfile]


def install_argv(image: str, workdir: str) -> list:
    return ["podman", "run", "--rm", "--privileged", "--pid=host",
            "--security-opt", "label=type:unconfined_t",
            "-v", "/var/lib/containers:/var/lib/containers", "-v", "/dev:/dev",
            "-v", workdir + ":/output",
            image, "bootc", "install", "to-disk", "--via-loopback", "--generic-image",
            "--skip-fetch-check", "--filesystem", "ext4",
            "--root-ssh-authorized-keys", "/output/key.pub",
            "--karg", "console=ttyS0", "--karg", "systemd.wants=sshd.service",
            "/output/disk.raw"]


def ssh_argv(key: str, port: int, command: str) -> list:
    # The VM is the one this run just started, reached on loopback; its host
    # key is new every run, so there is nothing to pin it against.
    return ["ssh", "-i", key, "-p", str(port),
            "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "PasswordAuthentication=no",
            "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=5", "-o", "LogLevel=ERROR",
            "root@127.0.0.1", command]


def _deployment(text: str, which: str):
    try:
        image = json.loads(text)["status"][which]["image"]
        ref, digest = image["image"]["image"], image["imageDigest"]
    except (ValueError, KeyError, TypeError):
        return None
    if not (isinstance(ref, str) and ref and isinstance(digest, str) and digest):
        return None
    return ref, digest


def booted(text: str):
    """(image reference, digest) of the booted deployment, or None."""
    return _deployment(text, "booted")


def rollback(text: str):
    return _deployment(text, "rollback")


def trigger_stopped(serial: str, offset: int) -> bool:
    """True once the serial console, after `offset` (its length before this
    reboot), shows greenboot's rollback trigger stopped: the trigger has run,
    and finalize, ordered after it, is next. Colour codes may sit inside the
    line; the pattern spans them."""
    return bool(TRIGGER_STOPPED.search(serial[offset:]))


def subid_once(text: str) -> bool:
    """True if a subuid or subgid file names Podman's containers range exactly once."""
    return text.splitlines().count(SUBID_LINE) == 1


def unit_ran(show: str) -> bool:
    """`systemctl show -p ActiveState -p Result` of a RemainAfterExit oneshot:
    True only if it ran and succeeded (Result=success alone is also a unit
    that never ran; verifier round 1, nit 3)."""
    lines = show.splitlines()
    return "ActiveState=active" in lines and "Result=success" in lines


def container_started(output: str) -> bool:
    return "started" in output.splitlines()


def containerfile_broken(base: str) -> str:
    return ("FROM %s\n"
            "RUN printf '#!/bin/bash\\necho \"drill: deliberate required-check failure\" >&2\\nexit 1\\n' "
            "> /etc/greenboot/check/required.d/99-drill-fail.sh "
            "&& chmod 0755 /etc/greenboot/check/required.d/99-drill-fail.sh\n"
            "LABEL rikuri.drill=broken\n" % base)


def containerfile_label(base: str, label: str) -> str:
    return "FROM %s\nLABEL rikuri.drill=%s\n" % (base, label)


def wait_until(predicate, timeout: float, interval: float = 5, clock=time.monotonic,
               sleep=time.sleep, what: str = "the condition"):
    start = clock()
    while True:
        value = predicate()
        if value:
            return value
        if clock() - start >= timeout:
            raise DrillFailure("timed out after %ds waiting for %s" % (timeout, what))
        sleep(interval)


class Drill:
    def __init__(self, image: str, workdir: str, artifacts: str):
        self.image, self.workdir, self.artifacts = image, workdir, artifacts
        self.key = os.path.join(workdir, "key")
        self.disk = os.path.join(workdir, "disk.raw")
        self.vars = os.path.join(workdir, "vars.fd")
        self.pidfile = os.path.join(workdir, "qemu.pid")
        self.starts = 0
        self.installed = None
        self.results = []

    # --- plumbing ------------------------------------------------------------
    def log(self, message: str) -> None:
        print("vm-drill: " + message, flush=True)

    def run(self, argv, check=True, timeout=600, stdin=None, sudo=False):
        argv = (["sudo", "-n"] if sudo else []) + argv
        p = subprocess.run(argv, stdin=stdin, capture_output=True, text=True, errors="replace",
                           timeout=timeout, check=False)
        if check and p.returncode != 0:
            raise DrillFailure("%s exited %d: %s" % (argv[:4], p.returncode, (p.stderr or p.stdout)[-2000:]))
        return p

    def vm(self, command: str, check=True, timeout=300, stdin=None):
        p = self.run(ssh_argv(self.key, PORT, command), check=check, timeout=timeout, stdin=stdin)
        return p.stdout if p.returncode == 0 else None

    def keep(self, name: str, text: str) -> None:
        with open(os.path.join(self.artifacts, name), "w", encoding="utf-8") as f:
            f.write(text or "")

    def boot_id(self):
        try:
            out = self.vm("cat /proc/sys/kernel/random/boot_id", check=False, timeout=20)
        except subprocess.TimeoutExpired:
            return None
        return out.strip() if out else None

    def status(self) -> str:
        return self.vm("bootc status --format json") or ""

    def start_vm(self) -> None:
        self.starts += 1
        serial = os.path.join(self.workdir, "serial-%d.log" % self.starts)
        self.run(qemu_argv(self.disk, self.vars, serial, PORT, self.pidfile), sudo=True)
        self.log("VM started (%s)" % os.path.basename(serial))

    def kill_vm(self) -> None:
        pid = self.run(["cat", self.pidfile], sudo=True).stdout.strip()
        self.run(["kill", "-9", pid], sudo=True)
        wait_until(lambda: self.run(["kill", "-0", pid], check=False, sudo=True).returncode != 0,
                   timeout=60, interval=1, what="QEMU to die")
        self.log("VM killed: power cut")

    def wait_up(self, old_boot=None, timeout=600):
        """Wait for a boot other than old_boot to answer, then for greenboot to finish."""
        bid = wait_until(lambda: (lambda b: b if b and b != old_boot else None)(self.boot_id()),
                         timeout=timeout, what="the VM to boot and answer on SSH")
        wait_until(lambda: (self.vm("systemctl is-active greenboot-healthcheck.service", check=False)
                            or "").strip() == "active",
                   timeout=300, what="greenboot's health check to finish")
        return bid

    def reboot(self) -> str:
        old = self.boot_id()
        if not old:
            raise DrillFailure("cannot read the boot id before rebooting")
        self.vm("systemctl reboot", check=False, timeout=30)
        return old

    def journal(self, args: str) -> str:
        return self.vm("journalctl --no-pager -o short-monotonic " + args, check=False, timeout=120) or ""

    def check(self, case: str, ok: bool, detail: str) -> None:
        self.results.append((case, ok, detail))
        self.log("%s %s: %s" % ("PASS" if ok else "FAIL", case, detail))

    def booted_digest(self):
        b = booted(self.status())
        return b[1] if b else None

    # --- the drill -----------------------------------------------------------
    def install(self) -> None:
        self.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "vm-drill", "-f", self.key])
        self.run(["truncate", "-s", DISK_SIZE, self.disk], sudo=True)
        self.log("installing %s with bootc install to-disk" % self.image)
        p = self.run(install_argv(self.image, self.workdir), sudo=True, timeout=1800)
        self.keep("00-install.out", p.stdout + p.stderr)
        self.run(["cp", OVMF_VARS, self.vars], sudo=True)
        self.start_vm()

    def first_boot(self) -> None:
        self.wait_up(timeout=900)
        status = self.status()
        self.installed = booted(status)
        self.keep("01-first-boot.out", "\n".join([
            status, self.vm("getenforce", check=False) or "", self.vm("grub2-editenv /boot/grub2/grubenv list",
                                                                      check=False) or "",
            self.journal("-b -u greenboot-healthcheck")]))
        journal = self.journal("-b -u greenboot-healthcheck")
        self.check("first boot", self.installed is not None and "health-check passed" in journal
                   and DNS_SKIPPED in journal and "rikuri-unapplied-update:" in journal,
                   "booted %s; greenboot passed: %s; DNS check skipped: %s; the check ran: %s"
                   % (self.installed, "health-check passed" in journal, DNS_SKIPPED in journal,
                      "rikuri-unapplied-update:" in journal))
        self.vm("echo 'vm-drill marker' > %s && sync" % MARKER)

    def load_variants(self) -> None:
        archive = os.path.join(self.workdir, "image.tar")
        self.run(["podman", "save", "--format", "oci-archive", "-o", archive, self.image], sudo=True, timeout=1800)
        self.run(["chmod", "0644", archive], sudo=True)
        with open(archive, "rb") as f:
            self.vm("podman load", stdin=f, timeout=1800)
        for name, text in (("broken", containerfile_broken(self.image)),
                           ("a", containerfile_label(self.image, "a")),
                           ("b", containerfile_label(self.image, "b"))):
            self.write_in_vm("/root/drill/%s/Containerfile" % name, text)
            self.vm("podman build --network=none -t localhost/rikuri-os:%s /root/drill/%s" % (name, name),
                    timeout=1800)
        self.log("variants built in the VM: broken, a, b")

    def subid_files(self) -> list:
        return [self.vm("cat %s" % f, check=False) or "" for f in SUBID_FILES]

    def userns_auto(self) -> None:
        """The containers range is in place (added at the first boot), the
        unit ran and succeeded in this boot, and a container with its own
        range of user IDs starts."""
        files = self.subid_files()
        unit = self.vm("systemctl show -p ActiveState -p Result rikuri-containers-subid.service", check=False) or ""
        journal = self.journal("-u rikuri-containers-subid")    # every boot: "added" is the first one's
        run = self.vm("podman run --rm --userns=auto --network=none --read-only %s /usr/bin/true && echo started"
                      % self.image, check=False) or ""
        self.keep("01b-userns-auto.out", "\n".join(SUBID_FILES[i] + ":\n" + files[i] for i in range(2))
                  + "\n" + unit + "\n" + journal + "\n" + run)
        once = all(subid_once(text) for text in files)
        self.check("the containers range", once and unit_ran(unit) and container_started(run),
                   "the range once in both files: %s; the unit ran and succeeded: %s; a --userns=auto container "
                   "started: %s" % (once, unit_ran(unit), container_started(run)))

    def subid_after_reboots(self) -> None:
        """Every boot since the first left the files as they were: still the range once."""
        files = self.subid_files()
        self.keep("05-subid-after-reboots.out", "\n".join(files))
        self.check("the containers range after reboots", all(subid_once(text) for text in files),
                   "the range still once in both files after every case's reboots: %s"
                   % all(subid_once(text) for text in files))

    def switch(self, name: str) -> None:
        self.vm("bootc switch --transport containers-storage localhost/rikuri-os:%s" % name, timeout=900)

    def case1(self) -> None:
        self.switch("broken")
        old = self.reboot()
        # Four boots of the broken image, then greenboot's rollback and a boot of the installed image.
        wait_until(lambda: (lambda s: booted(s) and booted(s)[1] == self.installed[1]
                            and (rollback(s) or ("", ""))[0] == "localhost/rikuri-os:broken")(self.status_quiet()),
                   timeout=600, interval=10, what="the broken update to roll back")
        self.wait_up(old_boot=old)
        everything = self.journal("--grep 'greenboot|rikuri-unapplied-update|bootc'")
        self.keep("02-case1.out", self.journal("--list-boots") + "\n" + everything + "\n" + self.status())
        marker = (self.vm("cat %s" % MARKER, check=False) or "").strip()
        self.check("case 1, a failing update", ROLLED_BACK in everything and marker == "vm-drill marker",
                   "rolled back: %s; marker intact: %s" % (ROLLED_BACK in everything, marker == "vm-drill marker"))

    def status_quiet(self) -> str:
        try:
            return self.vm("bootc status --format json", check=False, timeout=30) or ""
        except subprocess.TimeoutExpired:
            return ""

    def record_lines(self) -> int:
        return len((self.vm("cat /var/lib/rikuri/update-not-applied", check=False) or "").splitlines())

    def never_applied(self, case: str, name: str, lines_before: int) -> None:
        digest = self.booted_digest()
        journal = self.journal("-b")
        grubenv = self.vm("grub2-editenv /boot/grub2/grubenv list", check=False) or ""
        record = self.vm("cat /var/lib/rikuri/update-not-applied", check=False) or ""
        stays = digest is not None and digest == self.installed[1]
        new_line = len(record.splitlines()) > lines_before
        self.keep("%s-boot.out" % name, "\n".join([self.status(), grubenv, record, journal]))
        old = self.reboot()
        self.wait_up(old_boot=old)
        after = self.booted_digest()
        still = after is not None and after == self.installed[1]
        self.check(case, stays and still and NEVER_APPLIED in journal
                   and "greenboot_next_deployment_id" not in grubenv and new_line,
                   "on the installed image: %s, after one more reboot: %s; 'never applied' logged: %s; "
                   "trigger cleared: %s; a new record line: %s" % (stays, still, NEVER_APPLIED in journal,
                                                                   "greenboot_next_deployment_id" not in grubenv,
                                                                   new_line))

    def write_in_vm(self, path: str, text: str) -> None:
        p = subprocess.run(ssh_argv(self.key, PORT, "mkdir -p %s && cat > %s" % (os.path.dirname(path), path)),
                           input=text, capture_output=True, text=True, errors="replace", timeout=60, check=False)
        if p.returncode != 0:
            raise DrillFailure("writing %s in the VM: %s" % (path, p.stderr))

    def set_dropin(self, text: str) -> None:
        self.write_in_vm(DROPIN, text)
        self.vm("systemctl daemon-reload")

    def case2b(self) -> None:
        lines = self.record_lines()
        self.switch("a")
        self.set_dropin(FINALIZE_FAILS)
        old = self.reboot()
        self.wait_up(old_boot=old)
        self.never_applied("case 2b, finalize fails", "03-case2b", lines)

    def serial_text(self) -> str:
        serial = os.path.join(self.workdir, "serial-%d.log" % self.starts)
        return self.run(["cat", serial], check=False, sudo=True).stdout or ""

    def case3(self) -> None:
        lines = self.record_lines()
        self.switch("b")
        self.set_dropin(FINALIZE_HOLDS)
        offset = len(self.serial_text())
        self.reboot()
        # Deterministic: the trigger has stopped in this shutdown, and finalize,
        # ordered after it, is held by the drop-in's sleep; cut within the hold.
        wait_until(lambda: trigger_stopped(self.serial_text(), offset), timeout=POWER_CUT_AFTER_S * 4,
                   interval=1, what="greenboot's rollback trigger to stop in this shutdown")
        time.sleep(2)
        self.log("the rollback trigger stopped in this shutdown (serial console); finalize is held; "
                 "cutting the power")
        self.kill_vm()
        self.start_vm()
        self.wait_up(timeout=900)
        self.never_applied("case 3, a power cut during the update", "04-case3", lines)

    def post_mortem(self) -> None:
        """What the VM can still say after a failure: every boot's greenboot and check lines."""
        try:
            text = "\n".join([self.journal("--list-boots"), self.status_quiet(),
                              self.vm("grub2-editenv /boot/grub2/grubenv list", check=False, timeout=30) or "",
                              self.vm("findmnt /boot; lsblk -f", check=False, timeout=30) or "",
                              self.journal("--grep 'greenboot|rikuri-unapplied-update|bootc|finalize'"),
                              # ostree's own lines name why finalizing failed (they lack "finalize").
                              self.journal("-u ostree-finalize-staged.service -u ostree-finalize-staged-hold.service")])
        except (DrillFailure, subprocess.TimeoutExpired, OSError) as e:
            text = "the VM did not answer: %s" % e
        self.keep("99-post-mortem.out", text)

    def collect(self) -> None:
        for i in range(1, self.starts + 1):
            serial = os.path.join(self.workdir, "serial-%d.log" % i)
            self.keep("serial-%d.log" % i, self.run(["cat", serial], check=False, sudo=True).stdout)

    def summary(self) -> str:
        lines = ["### Rollback drill (x86_64, KVM)", "", "| Case | Result | Detail |", "|---|---|---|"]
        for case, ok, detail in self.results:
            lines.append("| %s | %s | %s |" % (case, "Pass" if ok else "**Fail**", detail))
        return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--image", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--artifacts", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.artifacts, exist_ok=True)
    drill = Drill(a.image, a.workdir, a.artifacts)
    error = None
    try:
        drill.install()
        drill.first_boot()
        drill.load_variants()
        for case in (drill.case1, drill.case2b, drill.case3):
            case()
        # After the cases, so that a --userns=auto run (which may add ID-mapped
        # layers to the storage bootc switch reads) cannot touch them; run 2
        # (40057729110) saw case 1's update fail to finalize with it before.
        drill.subid_after_reboots()
        drill.userns_auto()
    except (DrillFailure, subprocess.TimeoutExpired) as e:
        error = str(e)
        drill.check("drill", False, error)
        drill.post_mortem()
    finally:
        try:
            drill.collect()
        except (DrillFailure, subprocess.TimeoutExpired, OSError) as e:
            drill.log("collecting the serial logs failed: %s" % e)
    text = drill.summary()
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
    expected = {"first boot", "case 1, a failing update", "case 2b, finalize fails",
                "case 3, a power cut during the update", "the containers range",
                "the containers range after reboots"}
    passed = {case for case, ok, _ in drill.results if ok}
    return 0 if error is None and expected <= passed and all(ok for _, ok, _ in drill.results) else 1


if __name__ == "__main__":
    sys.exit(main())
