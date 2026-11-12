#!/usr/bin/env python3
"""The OS image's rollback drill, in a VM: stage 1 changes 3 and 4.

    vm_drill.py --image <local image> --workdir <dir> --artifacts <dir> --registry <registry>

Runs only on an x86_64 Linux runner with KVM, sudo, podman, QEMU and OVMF
(.github/workflows/image.yml, job drill). It installs the image with the
image's own `bootc install to-disk` onto a raw disk, boots it under QEMU, and
checks, failing on any miss:

  first boot   greenboot passes; its journal shows Fedora's DNS check (D9) and
               update-platforms check (owner, 2026-10-24) skipped; the
               unapplied-update check ran.
  case 1       a staged update whose required check fails rolls back by itself
               to the installed image, with a /var marker intact.
  case 2b      an update whose finalize fails leaves the node on the installed
               image, with the check's "was never applied" in the journal,
               also after one more reboot (D22, greenboot-rs #219).
  case 3       a power cut after greenboot armed its trigger and before the
               update was written does the same. The cut is deterministic: a
               drop-in in /run holds finalize's stop (greenboot's trigger stops
               first), and the VM is killed during the hold.
  containers range
               rikuri-containers-subid added Podman's range to /etc/subuid and
               /etc/subgid in the first boot, and greenboot's wanted check of
               it passed; after the cases both files read
               as they did then; last, a --userns=auto container starts
               (docs/build-records/2026-10-24-drill-first-boot-and-finalize.md).
  case 4       the node's own `bootc switch` refuses an unsigned image named
               ghcr.io/rikuripi/rikurinode, for the policy's reason ("no
               signature exists"), and stages nothing.
  case 5       it stages the first published image (2b), signed with the
               project's key: bootc status names exactly that name and digest.
               Cases 4 and 5 run last; the staged update meets no reboot
               (docs/build-records/2026-10-29-node-refuses-unsigned.md).

The VM gets a key made for this run (root, on the drill's disk only; the image
is unchanged) and a user-mode network restricted to one forwarded SSH port on
loopback and one forward out, to a registry (--registry, distribution's
release) on the CI machine's loopback: it has no other network. Into that
registry go the published image with its signature (copied from ghcr.io by
the CI machine) and the image under test, unsigned. In the VM, two files
beside the shipped ones read the image's name from it; the policy and keys
are the image's own. The cases are those of
docs/build-records/2026-10-21-greenboot-drill-parallels.md, run there by hand.
Evidence goes to --artifacts. Record: docs/build-records/2026-10-22-ci-vm-drill.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import socket
import ssl
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I leaves this folder out
import signature_policy as sp  # noqa: E402

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
PLATFORMS_SKIPPED = "Skipping disabled script: 01_update_platforms_check.sh"
ROLLED_BACK = "Boot counter exhausted and next-deployment-id is set - initiating rollback"
BROKEN = "localhost/rikuri-os:broken"
# The journal of the boot that shut down: finalize's stop, ostree's own error,
# and when the EFI partition's automount on /boot went (the race, in
# docs/build-records/2026-11-11-case1-finalize-race.md).
FINALIZE_JOURNAL = "-b -1 -u ostree-finalize-staged.service -u boot.automount"
# ostree itself: not rpm-ostree, not ostree-prepare-root.
OSTREE_ERROR = re.compile(r"(?<![\w-])ostree\[\d+\]: (error: .*)$", re.M)
# The image masks the EFI partition's automount on /boot, so that ostree's /boot
# is the only one (docs/build-records/2026-11-11-boot-automount-mask.md).
SHOW_BOOT_AUTOMOUNT = "systemctl show -p LoadState -p ActiveState boot.automount"
BOOT_FSTYPES = "findmnt -n -o FSTYPE /boot"
TRIGGER_STOPPED = re.compile(r"Stopped [^\n]*Greenboot Rollback trigger")
SUBID_LINE = "containers:2147483647:2147483648"
SUBID_FILES = ("/etc/subuid", "/etc/subgid")
SUBID_WANTED = "/usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid"
# 2c: the drill's registry, on the CI machine at sp.REG, is this address in the VM (one guestfwd).
MIRROR_IN_VM = "10.0.2.100:5000"
MIRROR_REPO = MIRROR_IN_VM + "/rikuripi/rikurinode"
MIRROR_CONF = "/etc/containers/registries.conf.d/99-drill-registry.conf"
MIRROR_REGISTRIES_D = "/etc/containers/registries.d/drill-registry.yaml"
MIRROR_FILES = (MIRROR_CONF, MIRROR_REGISTRIES_D)
# The first published image, signed with the project's key (2b, run 40794568497).
SIGNED_REF = sp.IMAGE_REPO + ":44.20261029.1"
SIGNED_DIGEST = "sha256:c984d651db4f15be5dac56fcd974d230bc248536fade4ceee29323abadfdecfd"
UNSIGNED_REF = sp.IMAGE_REPO + ":drill-unsigned"
# bootc's image proxy answers OpenImage with the policy's own reason, without skopeo's
# "Source image rejected: " (CI run 40933775613, repair 2).
BOOTC_REFUSED = "failed to invoke method OpenImage: " + sp.NO_SIGNATURE


# 5c.1: the control plane's two ports, forwarded to the CI machine's loopback only
# (docs/build-records/2026-11-06-5c1-control-plane-on-node.md).
HTTP_PORT = 8080
HTTPS_PORT = 8443
CP_USER = "rikuri-control"
SERVER_NAME = "localhost"
# 5c.2: the name mDNS answers and the certificate carries; the hostname behind it.
NODE_NAME = "rikurisetup.local"
NODE_HOSTNAME = "rikurisetup"
ALLOWED_PORTS = frozenset({22, 80, 443})
CP_REQUIRED = "/usr/lib/greenboot/check/required.d/50-rikuri-control-plane"
SHOW_CP = "systemctl show -p ActiveState -p SubState -p MainPID rikuri-control-plane.service"
SHOW_SCREEN = "systemctl show -p ActiveState -p SubState -p TTYPath -p User rikuri-claim-screen.service"
POLICY_INFO = "firewall-cmd --info-policy=rikuri-node"
RESTART_SCREEN = "systemctl restart rikuri-claim-screen.service"
# The route to TEST-NET-1, as console::lan_address asks for it: its source is the address the screen must show.
PROBE_ROUTE = "ip -4 route get 192.0.2.1"
TTY2_TEXT = "cat /dev/vcs2"
# The interface of the guest's global IPv4 address, the one PROBE_ROUTE_ADD routes on.
NIC = "ip -o -4 addr show scope global | awk '{print $2; exit}'"
# The drill's network (restrict=on) has no default route, as a node without its
# router: a host route to the probe, on the interface of the guest's address,
# lets the screen find that address. No gateway is assumed; nothing is sent.
PROBE_ROUTE_ADD = ("dev=$(" + NIC + ") && "
                   "ip route replace 192.0.2.1/32 dev \"$dev\"")
PROBE_ROUTE_DEL = "ip route del 192.0.2.1/32"
SCREEN_READS = 10
# The daemon looks at its address every 60 s (address::EVERY): the certificate
# names the guest's address within a minute of the probe's route, so 30 tries
# 5 s apart wait well past one look.
ADDRESS_TRIES = 30
HOSTNAME_CMD = "cat /proc/sys/kernel/hostname"   # the kernel's name now, runtime truth
MDNS_STATUS = "resolvectl mdns"
UDP_LISTEN = "ss -Huln"
# The guest's global IPv4 address with its prefix, read before the probe has a route.
GUEST_ADDRESS = "ip -o -4 addr show scope global | awk '{print $4; exit}'"
# The service's process and its restarts, compared around the follow.
SHOW_CP_RUN = "systemctl show -p MainPID -p NRestarts rikuri-control-plane.service"
MDNS_PORT = 5353
# PLAT-01 (docs/build-records/2026-11-10-plat01-mdns-allow-list.md): a container
# on podman's default network brings its bridge and a veth up; the allow-list's
# units must leave mDNS on the NIC only.
MDNS_CONTAINER = "drill-mdns"
MDNS_RUN = "podman run -d --rm --name " + MDNS_CONTAINER + " --read-only %s sleep 600 && echo started"
MDNS_STOP = "podman stop -t 1 " + MDNS_CONTAINER
BRIDGE = "podman0"
_ONESHOT = "systemctl show -p Result -p ExecMainStatus -p ExecMainStartTimestampMonotonic "
SHOW_MDNS_LINKS = _ONESHOT + "rikuri-mdns-links.service"
SHOW_MDNS_BRIDGE = _ONESHOT + "rikuri-mdns-links@" + BRIDGE + ".service"
MDNS_READS = 10
LLMNR_PORT = 5355
MAX_BYTES = 64 * 1024


class DrillFailure(Exception):
    pass


def qemu_argv(disk: str, vars_fd: str, serial_log: str, port: int, pidfile: str) -> list:
    return ["qemu-system-x86_64", "-enable-kvm", "-machine", "q35", "-cpu", "host",
            "-smp", "2", "-m", "4096",
            "-drive", "if=pflash,format=raw,unit=0,readonly=on,file=" + OVMF_CODE,
            "-drive", "if=pflash,format=raw,unit=1,file=" + vars_fd,
            "-drive", "if=virtio,format=raw,file=" + disk,
            # guestfwd's cmd: starts nc for each connection; a tcp: target would be
            # connected once, at QEMU's start, before the registry runs (CI run 40932208792).
            # 5c.1: and the control plane's 80 and 443, reached from the CI machine as a LAN browser would.
            "-netdev", "user,id=n0,restrict=on,hostfwd=tcp:127.0.0.1:%d-:22,hostfwd=tcp:127.0.0.1:%d-:80,"
            "hostfwd=tcp:127.0.0.1:%d-:443,guestfwd=tcp:%s-cmd:nc -N %s"
            % (port, HTTP_PORT, HTTPS_PORT, MIRROR_IN_VM, sp.REG.replace(":", " ")),
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


def staged(text: str):
    """(image reference, digest) of the staged deployment, or None."""
    return _deployment(text, "staged")


def case1_outcome(text: str, installed_digest: str):
    """Case 1 after its switch to the broken image: "rolled back" (greenboot
    did, and the installed image is booted), "never applied" (the installed
    image is booted with nothing staged and no rollback: the update was
    dropped at shutdown), or None while there is still something to wait for."""
    now = booted(text)
    if not now or now[1] != installed_digest:
        return None
    back = rollback(text)
    if back and back[0] == BROKEN:
        return "rolled back"
    if back is None and staged(text) is None:
        return "never applied"
    return None


def boot_automount_masked(show, fstypes) -> bool:
    """boot.automount is masked and not running, and /boot is one ext4 mount:
    ostree's bind of /sysroot/boot, with no autofs and no EFI partition there.
    ext4 because the drill installs with --filesystem ext4 (install_argv); a
    node's own filesystem may differ."""
    if show is None or fstypes is None:
        return False
    props = dict(line.split("=", 1) for line in show.splitlines() if "=" in line)
    return (props.get("LoadState") == "masked" and props.get("ActiveState") == "inactive"
            and fstypes.split() == ["ext4"])


def finalize_error(journal: str) -> str:
    """ostree's own error lines in a journal, or "" when it has none."""
    return "; ".join(OSTREE_ERROR.findall(journal))


def spec_image(text: str):
    """The image bootc's spec names (what the node follows), or None."""
    try:
        ref = json.loads(text)["spec"]["image"]["image"]
    except (ValueError, KeyError, TypeError):
        return None
    return ref if isinstance(ref, str) and ref else None


def sig_tag(digest: str) -> str:
    """The tag cosign's older format keeps a digest's signature under."""
    return digest.replace(":", "-") + ".sig"


def mirror_conf() -> str:
    """The VM reads the image's name from the drill's registry: a rewrite, never a mirror."""
    return '[[registry]]\nprefix = "%s"\nlocation = "%s"\ninsecure = true\n' % (sp.IMAGE_REPO, MIRROR_REPO)


def seed_argvs(image: str) -> list:
    """Fill the drill's registry: the signed image and its signature, by digest and with no login,
    and the image under test, unsigned. The copies only carry bytes (digests kept); the VM checks."""
    def copy(src, dst):
        return sp.podman_run(image, [], "skopeo", "copy", "-q", "--insecure-policy", "--remove-signatures",
                             "--preserve-digests", "--dest-tls-verify=false", src, dst)
    sig = sig_tag(SIGNED_DIGEST)
    return [copy("docker://%s@%s" % (sp.IMAGE_REPO, SIGNED_DIGEST),
                 "docker://%s:%s" % (sp.LOCAL_REPO, SIGNED_REF.rsplit(":", 1)[1])),
            copy("docker://%s:%s" % (sp.IMAGE_REPO, sig), "docker://%s:%s" % (sp.LOCAL_REPO, sig)),
            ["sudo", "podman", "push", "-q", "--tls-verify=false", image,
             "docker://%s:%s" % (sp.LOCAL_REPO, UNSIGNED_REF.rsplit(":", 1)[1])]]


def unsigned_refused(returncode: int, output: str, status: str) -> bool:
    """Refused for the policy's reason, as the proxy's answer to opening the image,
    and nothing staged in a status that reads."""
    return (returncode != 0 and BOOTC_REFUSED in output and booted(status) is not None
            and staged(status) is None)


def signed_staged(returncode: int, status: str) -> bool:
    """Staged with exactly the published digest, under the name the spec follows."""
    return returncode == 0 and staged(status) == (SIGNED_REF, SIGNED_DIGEST) and spec_image(status) == SIGNED_REF


def trigger_stopped(serial: str, offset: int) -> bool:
    """True once the serial console, after `offset` (its length before this
    reboot), shows greenboot's rollback trigger stopped: the trigger has run,
    and finalize, ordered after it, is next. Colour codes may sit inside the
    line; the pattern spans them."""
    return bool(TRIGGER_STOPPED.search(serial[offset:]))


def first_boot_checks(journal: str) -> dict:
    """What the first-boot check requires of greenboot's journal, by name, in the
    order the check reports them; the boot passes only if each is True."""
    return {"greenboot passed": "health-check passed" in journal,
            "DNS check skipped": DNS_SKIPPED in journal,
            "update-platforms check skipped": PLATFORMS_SKIPPED in journal,
            "the check ran": "rikuri-unapplied-update:" in journal}


def subid_once(text: str) -> bool:
    """True if a subuid or subgid file names Podman's containers range exactly once."""
    return text.splitlines().count(SUBID_LINE) == 1


def subid_added(journal: str) -> bool:
    """True if rikuri-containers-subid's journal says it added the range to both
    files, each on a line of its own (an "added ..., but syncing its folder
    failed" line does not count)."""
    return all(re.search(r"%s: added %s$" % (re.escape(f), re.escape(SUBID_LINE)), journal, re.M)
               for f in SUBID_FILES)


def wanted_passed(journal: str) -> bool:
    """True if greenboot's journal says the image's wanted check of the range succeeded."""
    return ("wanted script %s success!" % SUBID_WANTED) in journal


def subid_unchanged(first: list, now: list) -> bool:
    """True if both files read now as they did at the first boot, with the range once."""
    return len(now) == len(first) == len(SUBID_FILES) and now == first and all(subid_once(t) for t in now)


def unit_ran(show: str) -> bool:
    """`systemctl show -p ActiveState -p Result` of a RemainAfterExit oneshot:
    True only if it ran and succeeded (Result=success alone is also a unit
    that never ran; verifier round 1, nit 3)."""
    lines = show.splitlines()
    return "ActiveState=active" in lines and "Result=success" in lines


def exposed_ports(ss: str) -> set:
    """The TCP ports `ss -Htln` shows listening on anything but loopback."""
    ports = set()
    for line in ss.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        host, _, port = fields[3].rpartition(":")
        host = host.split("%", 1)[0].strip("[]")
        if not port.isdigit() or host.startswith("127.") or host == "::1":
            continue
        ports.add(int(port))
    return ports


def ports_ok(ports: set) -> bool:
    """True if SSH, 80 and 443 listen outside loopback, and nothing else does."""
    return ports == ALLOWED_PORTS


def _show(text: str) -> dict:
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def main_pid(show: str):
    pid = _show(show).get("MainPID", "")
    return int(pid) if pid.isdigit() and int(pid) > 0 else None


def service_ok(show: str, owner: str) -> bool:
    """The service runs, and its process belongs to the control plane's user."""
    v = _show(show)
    return v.get("ActiveState") == "active" and v.get("SubState") == "running" and owner == CP_USER


def screen_ok(show: str) -> bool:
    """The claim screen runs on tty2 as the control plane's user."""
    v = _show(show)
    return (v.get("ActiveState") == "active" and v.get("SubState") == "running"
            and v.get("TTYPath") == "/dev/tty2" and v.get("User") == CP_USER)


def route_source(route: str):
    """The source address of `ip -4 route get`, or None if it names none."""
    m = re.search(r"\bsrc (\d{1,3}(?:\.\d{1,3}){3})(?!\S)", route or "")
    return m.group(1) if m else None


def shows_address(screen: str, address) -> bool:
    """tty2's text shows `Address:  http://<address>` and nothing longer, for an address not on loopback."""
    if not address or address.startswith("127."):
        return False
    return re.search(r"\bAddress:  http://%s(?!\S)" % re.escape(address), screen or "") is not None


def policy_active(info: str) -> bool:
    """`firewall-cmd --info-policy=rikuri-node`: active, with exactly http, https and mdns."""
    lines = [line.strip() for line in info.splitlines()]
    return bool(lines) and lines[0] == "rikuri-node (active)" and "services: http https mdns" in lines


def mdns_on(status: str, nic: str) -> bool:
    """`resolvectl mdns`: on globally and on the guest's interface, and on no
    loopback link (resolved lists none)."""
    lines = [line.strip() for line in (status or "").splitlines()]
    nic = (nic or "").strip()
    return (bool(nic) and "Global: yes" in lines
            and any(re.fullmatch(r"Link \d+ \(%s\): yes" % re.escape(nic), line) for line in lines)
            and not any(re.fullmatch(r"Link \d+ \(lo\): .*", line) and not line.endswith(": no")
                        for line in lines))


def guest_address(text):
    """The address of `ip -o -4 addr` 's `10.0.2.15/24`, or None if it is not one, or is loopback."""
    m = re.fullmatch(r"(\d{1,3}(?:\.\d{1,3}){3})/\d{1,2}", (text or "").strip())
    return m.group(1) if m and not m.group(1).startswith("127.") else None


def same_run(before: str, after: str) -> bool:
    """The same running process, with the same restart count, in both `systemctl show`s."""
    b, a = _show(before), _show(after)
    return (main_pid(before) is not None and main_pid(before) == main_pid(after)
            and b.get("NRestarts", "").isdigit() and b.get("NRestarts") == a.get("NRestarts"))


def mdns_only(status: str, nic: str) -> bool:
    """`resolvectl mdns` with the bridge up: on globally, `yes` on the NIC and on
    no other link, and the bridge listed and off."""
    lines = [line.strip() for line in (status or "").splitlines()]
    nic = (nic or "").strip()
    links = dict(m.groups() for m in (re.fullmatch(r"Link \d+ \((\S+)\): (\S+)", line) for line in lines) if m)
    return (bool(nic) and "Global: yes" in lines and links.get(nic) == "yes"
            and links.get(BRIDGE) == "no" and [n for n, v in links.items() if v == "yes"] == [nic])


def oneshot_ran(show: str) -> bool:
    """A oneshot unit started in this boot and exited 0 (Result is `success`
    by default, so the start time must be set too)."""
    v = _show(show)
    return (v.get("Result") == "success" and v.get("ExecMainStatus") == "0"
            and v.get("ExecMainStartTimestampMonotonic", "0") not in ("", "0"))


def mdns_listens(ports: set) -> bool:
    """UDP: mDNS's 5353 bound outside loopback, LLMNR's 5355 not."""
    return MDNS_PORT in ports and LLMNR_PORT not in ports


def required_passed(journal: str) -> bool:
    """True if greenboot's journal says the control plane's required check succeeded."""
    return ("required script %s success!" % CP_REQUIRED) in journal


CODE_NOT_SHOWN = "claim code armed and not shown"
# A code as claim::Code::formatted() writes it: ten symbols of the alphabet, in groups of 4, 4 and 2.
CLAIM_CODE = re.compile(r"\b[A-HJKMNP-Z2-9]{4}-[A-HJKMNP-Z2-9]{4}-[A-HJKMNP-Z2-9]{2}\b")


def code_kept_out(journal: str) -> bool:
    """The control plane's journal of this boot: it armed a code at its first
    start and wrote no code there (the journal is kept on disk)."""
    return CODE_NOT_SHOWN in journal and not CLAIM_CODE.search(journal) and "claim_code" not in journal


def parse_http(raw: bytes):
    """(status, body) of an HTTP/1.1 response, or (None, b"") if it is not one."""
    head, _, body = raw.partition(b"\r\n\r\n")
    status = head.split(b"\r\n", 1)[0].split(b" ")
    if len(status) < 2 or not status[0].startswith(b"HTTP/") or not status[1].isdigit():
        return None, b""
    return int(status[1]), body


# 5c.3a: the setup pages' policy, as the control plane sends it (src/ui.rs).
PAGE_CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; "
            "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
SETUP_REDIRECT = "https://127.0.0.1/setup"   # the plain listener's answer to /setup, as fetch_plain asks
# 5c.3b: the owner's pages, and a claim code no node can show: a real code
# draws only from claim::ALPHABET, which has no 0, 1, I, L or O.
OWNER_PAGES = ("/claim", "/signin")
# 5c.4a, repair 1: the node's name as the hub reads it, as the service's user
# inside the service's own mount namespace (its sandbox: ProtectSystem=strict,
# ProcSubset=pid). A file the service cannot see there would fail this.
NAME_IN_SANDBOX = ('pid="$(systemctl show -p MainPID --value rikuri-control-plane.service)" && '
                   'nsenter --target "$pid" --mount --setuid "$(id -u %s)" --setgid "$(id -g %s)" '
                   'cat /etc/hostname' % (CP_USER, CP_USER))
WRONG_CODE = "0000-0000-00"


def http_header(raw: bytes, name: str):
    """The value of header `name` (any case) in an HTTP/1.1 response, or None."""
    head, sep, _ = raw.partition(b"\r\n\r\n")
    if not sep:
        return None
    for line in head.split(b"\r\n")[1:]:
        key, colon, value = line.partition(b":")
        if colon and key.strip().lower() == name.lower().encode():
            return value.strip().decode("latin-1")
    return None


def page_ok(raw: bytes, page: str):
    """(ok, detail): `raw` is the setup page `page` ("certificate" or "secure"),
    as HTML, under the pages' policy, with nosniff, and every script a file of
    the node's own build (no inline or outside script)."""
    status, body = parse_http(raw)
    problems = []
    if status != 200:
        problems.append("status %s" % status)
    ctype = http_header(raw, "content-type")
    if ctype != "text/html; charset=utf-8":
        problems.append("content-type %r" % ctype)
    csp = http_header(raw, "content-security-policy")
    if csp != PAGE_CSP:
        problems.append("policy %r" % csp)
    if http_header(raw, "x-content-type-options") != "nosniff":
        problems.append("no nosniff")
    text = body.decode("utf-8", "replace")
    if '<meta name="rikuri-page" content="%s">' % page not in text:
        problems.append("not the %s page" % page)
    for script in re.findall(r"<script\b[^>]*>", text):
        if ' src="/assets/' not in script:
            problems.append("a script that is not the node's file: %s" % script)
    return not problems, ("%s page: %s" % (page, "; ".join(problems) if problems else "200, policy, nosniff, "
                                           "scripts from /assets/ only"))


def pem_fingerprint(pem: str) -> str:
    """The certificate's SHA-256 as the control plane reports it: colon-separated upper-case hex."""
    return ":".join("%02X" % b for b in hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).digest())


def setup_ok(body: bytes, fingerprint: str) -> bool:
    """The first boot's setup report: not claimed, a code armed at the first start, and this CA."""
    try:
        report = json.loads(body)
    except ValueError:
        return False
    return (isinstance(report, dict) and report.get("claimed") is False and report.get("claim") == "armed"
            and report.get("ca_fingerprint_sha256") == fingerprint)


def _read_all(conn) -> bytes:
    chunks, size = [], 0
    while size < MAX_BYTES:
        chunk = conn.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
    return b"".join(chunks)


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


# Every check main runs; the drill passes only if each of them passed.
EXPECTED = frozenset({"first boot", "the containers range at the first boot", "case 1, a failing update",
                      "case 2b, finalize fails", "case 3, a power cut during the update",
                      "the containers range after reboots", "the containers range",
                      "case 4, an unsigned update refused", "case 5, a signed update staged",
                      "the control plane runs as its own user", "the CA certificate over HTTP",
                      "the API over HTTPS with only the node's CA", "a client without the node's CA is refused",
                      "the claim screen on tty2", "the claim screen shows the node's address",
                      "only SSH, 80 and 443 listen outside", "the firewall opens 80, 443 and mDNS",
                      "greenboot's control plane check",
                      "HTTPS as rikurisetup.local with only the node's CA",
                      "the certificate follows the node's address without a restart", "the node is named rikurisetup",
                      "mDNS on the node's interface", "mDNS listens on 5353, LLMNR does not",
                      "mDNS only on the node's interface, with a container's bridge up",
                      "no claim code in the journal",
                      "the certificate screen over HTTP", "the secure page over HTTPS with only the node's CA",
                      "the secure page never over HTTP",
                      "the owner's pages over HTTPS with only the node's CA",
                      "a wrong claim code is refused and the node stays unclaimed",
                      "the owner's pages never over HTTP",
                      "the SetupHub over HTTPS only, with only the node's CA",
                      "the hub refuses a browser without a session",
                      "the control plane reads the node's name in its sandbox",
                      "the EFI partition's automount on /boot is masked"})


def verdict(results, error) -> int:
    """0 only if nothing raised, every expected check passed, and no check failed."""
    passed = {case for case, ok, _ in results if ok}
    return 0 if error is None and EXPECTED <= passed and all(ok for _, ok, _ in results) else 1


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
        self.first_subid = []
        self.registry = None
        self.screen_pause = 2   # seconds between reads of tty2, while the screen draws
        self.address_pause = 5  # seconds between tries as the guest's address, while the daemon looks again
        self.mdns_pause = 2     # seconds between reads of resolved's mDNS, while udev's unit runs
        self.case1_poll = 10    # seconds between reads of bootc's status, while case 1's boots run

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
        checks = first_boot_checks(journal)
        self.check("first boot", self.installed is not None and all(checks.values()),
                   "booted %s; %s" % (self.installed, "; ".join("%s: %s" % kv for kv in checks.items())))
        self.vm("echo 'vm-drill marker' > %s && sync" % MARKER)
        self.subid_first_boot()

    def boot_automount(self) -> None:
        """The image's mask holds on the running node: systemd loads
        boot.automount as masked and never starts it, and /boot is ostree's
        alone, so no automount can go before ostree finalizes an update."""
        show = self.vm(SHOW_BOOT_AUTOMOUNT, check=False)
        fstypes = self.vm(BOOT_FSTYPES, check=False)
        self.keep("01d-boot-automount.out", "\n".join([show or "(no answer)", fstypes or "(no answer)"]))
        props = dict(line.split("=", 1) for line in (show or "").splitlines() if "=" in line)
        self.check("the EFI partition's automount on /boot is masked", boot_automount_masked(show, fstypes),
                   "boot.automount: LoadState=%s; ActiveState=%s; /boot: %s"
                   % (props.get("LoadState"), props.get("ActiveState"), ", ".join((fstypes or "").split())))

    def subid_first_boot(self) -> None:
        """A fresh install gets the range at its first boot: the unit added it to
        both files in this boot, each file names it once, and greenboot's
        wanted check of it succeeded."""
        self.first_subid = self.subid_files()
        journal = self.journal("-b -u rikuri-containers-subid")
        greenboot = self.journal("-b -u greenboot-healthcheck")
        self.keep("01a-subid-first-boot.out", "\n".join(
            SUBID_FILES[i] + ":\n" + self.first_subid[i] for i in range(2)) + "\n" + journal + "\n" + greenboot)
        once = all(subid_once(text) for text in self.first_subid)
        self.check("the containers range at the first boot", once and subid_added(journal) and wanted_passed(greenboot),
                   "added in boot 1 to both files: %s; the range once in both: %s; greenboot's wanted check "
                   "passed: %s" % (subid_added(journal), once, wanted_passed(greenboot)))

    def fetch_plain(self, path: str) -> bytes:
        """One plain HTTP request to the VM's 80, through its forward."""
        with socket.create_connection(("127.0.0.1", HTTP_PORT), timeout=10) as conn:
            conn.sendall(b"GET %s HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n" % path.encode())
            return _read_all(conn)

    def fetch_tls(self, path: str, cafile, name: str = SERVER_NAME):
        """One HTTPS request to the VM's 443, through its forward, as `name`
        (a host name, or an IP address that must be in the certificate as
        one): trusting only `cafile`, or with None the system's CAs alone."""
        context = ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()
        with socket.create_connection(("127.0.0.1", HTTPS_PORT), timeout=10) as raw:
            with context.wrap_socket(raw, server_hostname=name) as conn:
                conn.sendall(b"GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n"
                             % (path.encode(), name.encode()))
                return _read_all(conn)

    def post_tls(self, path: str, body: bytes, cafile, name: str = SERVER_NAME):
        """One HTTPS POST of a JSON `body` to the VM's 443, as `name`, with
        the Origin a browser on the node's page sends, trusting only `cafile`."""
        context = ssl.create_default_context(cafile=cafile)
        raw = socket.create_connection(("127.0.0.1", HTTPS_PORT), timeout=10)
        # wrap_socket takes the socket over (it detaches `raw`, and closes it
        # if the handshake fails), so only the TLS socket needs closing.
        with context.wrap_socket(raw, server_hostname=name) as conn:
            conn.sendall(b"POST %s HTTP/1.1\r\nHost: %s\r\nOrigin: https://%s\r\n"
                         b"Content-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
                         % (path.encode(), name.encode(), name.encode(), len(body)) + body)
            return _read_all(conn)

    def refused_as(self, cafile, name: str):
        """Whether HTTPS as `name`, trusting only the node's CA, is refused for
        its certificate (not merely unanswered), and what happened."""
        try:
            answer = self.fetch_tls("/api/setup", cafile, name)
            return False, "as %s, answered: %r" % (name, answer[:60])
        except ssl.SSLCertVerificationError as e:
            return True, "as %s, refused: %s" % (name, e)
        except OSError as e:
            return False, "as %s, no answer, so no refusal seen (%s)" % (name, e)

    def setup_as(self, cafile, fingerprint, name: str):
        """Whether /api/setup answers as `name`, trusting only the node's CA, and what it said."""
        try:
            status, body = parse_http(self.fetch_tls("/api/setup", cafile, name))
        except OSError as e:     # ssl's errors, a refused certificate among them, are OSErrors
            return False, "no answer as %s (%s)" % (name, e)
        return (status == 200 and setup_ok(body, fingerprint),
                "as %s: %s %s" % (name, status, body[:120].decode("utf-8", "replace")))

    def node_cafile(self, name: str):
        """The node's CA, fetched in the clear from /ca.crt and written to
        `name` in the workdir, so each check that trusts it stands alone:
        (the file's path, or None, and what /ca.crt answered)."""
        try:
            status, body = parse_http(self.fetch_plain("/ca.crt"))
            if status == 200:
                pem = body.decode("ascii")
                pem_fingerprint(pem)   # refuses what is not a certificate
                cafile = os.path.join(self.workdir, name)
                with open(cafile, "w", encoding="ascii") as f:
                    f.write(pem)
                return cafile, status
        except (OSError, ValueError) as e:
            return None, "no answer (%s)" % e
        return None, status

    def setup_pages(self) -> None:
        """5c.3a, from outside the VM: the certificate screen in the clear at /,
        the secure page over HTTPS at /setup trusting only the node's CA (read
        from /ca.crt here, so this check stands alone), and /setup in the clear
        only a redirect to HTTPS."""
        lines = []
        try:
            ok, detail = page_ok(self.fetch_plain("/"), "certificate")
        except OSError as e:
            ok, detail = False, "no answer (%s)" % e
        self.check("the certificate screen over HTTP", ok, "GET http://127.0.0.1:%d/: %s" % (HTTP_PORT, detail))
        lines.append("GET / (plain): %s" % detail)

        cafile, status = self.node_cafile("node-ca-pages.crt")
        if cafile:
            try:
                ok, detail = page_ok(self.fetch_tls("/setup", cafile), "secure")
            except OSError as e:     # a refused certificate among them
                ok, detail = False, "no answer (%s)" % e
        else:
            ok, detail = False, "no CA certificate to trust (/ca.crt: %s)" % status
        self.check("the secure page over HTTPS with only the node's CA", ok,
                   "GET https://localhost:%d/setup: %s" % (HTTPS_PORT, detail))
        lines.append("GET /setup (TLS): %s" % detail)

        try:
            raw = self.fetch_plain("/setup")
            status, _ = parse_http(raw)
            location = http_header(raw, "location")
            ok = status == 308 and location == SETUP_REDIRECT
            detail = "%s to %s" % (status, location)
        except OSError as e:
            ok, detail = False, "no answer (%s)" % e
        self.check("the secure page never over HTTP", ok,
                   "GET http://127.0.0.1:%d/setup: %s (wanted 308 to %s)" % (HTTP_PORT, detail, SETUP_REDIRECT))
        lines.append("GET /setup (plain): %s" % detail)
        self.keep("02b-setup-pages.out", "\n".join(lines))

    def owner_pages(self) -> None:
        """5c.3b, from outside the VM: the claim and sign-in pages over HTTPS
        trusting only the node's CA, and in the clear only a redirect to it; one
        claim with a code no node can show, refused, and the node still
        unclaimed after it. The password it sends is random and never kept."""
        lines = []
        cafile, status = self.node_cafile("node-ca-owner.crt")
        no_ca = "no CA certificate to trust (/ca.crt: %s)" % status

        details = []
        ok = cafile is not None
        for path in OWNER_PAGES if cafile else ():
            try:
                good, detail = page_ok(self.fetch_tls(path, cafile), "secure")
            except OSError as e:     # a refused certificate among them
                good, detail = False, "no answer (%s)" % e
            ok = ok and good
            details.append("%s: %s" % (path, detail))
        detail = "; ".join(details) if cafile else no_ca
        self.check("the owner's pages over HTTPS with only the node's CA", ok,
                   "GET https://localhost:%d%s: %s" % (HTTPS_PORT, "|".join(OWNER_PAGES), detail))
        lines.append("GET %s (TLS): %s" % (" ".join(OWNER_PAGES), detail))

        if cafile:
            password = secrets.token_urlsafe(24)
            request = json.dumps({"code": WRONG_CODE, "password": password}).encode()
            try:
                status, body = parse_http(self.post_tls("/api/claim", request, cafile))
                try:
                    reply = json.loads(body)
                except ValueError:
                    reply = None
                refused = status == 401 and reply == {"error": "claim refused"}
                answer = "%s %s" % (status, body[:120].decode("utf-8", "replace"))
                status, body = parse_http(self.fetch_tls("/api/setup", cafile))
                try:
                    claimed = json.loads(body).get("claimed") if status == 200 else None
                except (ValueError, AttributeError):
                    claimed = None
                ok = refused and claimed is False
                detail = "POST /api/claim with %s: %s %s; then /api/setup claimed: %s" % (
                    WRONG_CODE, "refused" if refused else "not refused as wanted", answer, claimed)
            except OSError as e:
                ok, detail = False, "no answer (%s)" % e
            del password, request
        else:
            ok, detail = False, no_ca
        self.check("a wrong claim code is refused and the node stays unclaimed", ok, detail)
        lines.append(detail)

        details = []
        ok = True
        for path in OWNER_PAGES:
            want = "https://127.0.0.1" + path
            try:
                raw = self.fetch_plain(path)
                status, _ = parse_http(raw)
                location = http_header(raw, "location")
                good = status == 308 and location == want
                details.append("%s: %s to %s" % (path, status, location))
            except OSError as e:
                good = False
                details.append("%s: no answer (%s)" % (path, e))
            ok = ok and good
        detail = "; ".join(details)
        self.check("the owner's pages never over HTTP", ok,
                   "GET http://127.0.0.1:%d: %s (wanted 308 to https://127.0.0.1 and the same path)" % (HTTP_PORT, detail))
        lines.append("GET %s (plain): %s" % (" ".join(OWNER_PAGES), detail))
        self.keep("02c-owner-pages.out", "\n".join(lines))

    def setup_hub(self) -> None:
        """5c.4a, changing nothing: /home is the secure page over HTTPS
        trusting only the node's CA, and in the clear only a redirect to it
        (the page's shell, served since 5c.3b); GET /api/hub without a session
        is refused as the API refuses one; and, in the VM, the service can read
        the name the hub reports inside its sandbox. What the hub lists needs
        a claim, which the drill cannot make (it would have to press Enter on
        tty2): the tests cover that."""
        lines = []
        cafile, status = self.node_cafile("node-ca-hub.crt")
        no_ca = "no CA certificate to trust (/ca.crt: %s)" % status

        if cafile:
            try:
                ok, detail = page_ok(self.fetch_tls("/home", cafile), "secure")
            except OSError as e:     # a refused certificate among them
                ok, detail = False, "no answer (%s)" % e
            detail = "GET https://localhost:%d/home: %s" % (HTTPS_PORT, detail)
        else:
            ok, detail = False, no_ca
        try:
            raw = self.fetch_plain("/home")
            location = http_header(raw, "location")
            status, _ = parse_http(raw)
            plain_ok = status == 308 and location == "https://127.0.0.1/home"
            plain = "%s to %s" % (status, location)
        except OSError as e:
            plain_ok, plain = False, "no answer (%s)" % e
        detail += "; GET http://127.0.0.1:%d/home: %s (wanted 308 to https://127.0.0.1/home)" % (HTTP_PORT, plain)
        self.check("the SetupHub over HTTPS only, with only the node's CA", ok and plain_ok, detail)
        lines.append(detail)

        if cafile:
            try:
                status, body = parse_http(self.fetch_tls("/api/hub", cafile))
                ok = status == 401 and body == b'{"error":"sign-in required"}'
                detail = "GET /api/hub without a session: %s %s" % (status, body[:120].decode("utf-8", "replace"))
            except OSError as e:
                ok, detail = False, "no answer (%s)" % e
        else:
            ok, detail = False, no_ca
        self.check("the hub refuses a browser without a session", ok, detail)
        lines.append(detail)

        name = self.vm(NAME_IN_SANDBOX, check=False)
        first = next((line.strip() for line in (name or "").splitlines()
                      if line.strip() and not line.strip().startswith("#")), None)
        detail = "/etc/hostname as %s in the service's mount namespace: %s" % (
            CP_USER, repr(first) if name is not None else "not read")
        self.check("the control plane reads the node's name in its sandbox", first == "rikurisetup", detail)
        lines.append(detail)
        self.keep("02d-setup-hub.out", "\n".join(lines))

    def control_plane(self) -> None:
        """5c.1, at the first boot: the service runs as its own user; from outside
        the VM, the CA certificate comes over HTTP and the API answers over HTTPS
        trusting only that CA, while a client without it is refused; the claim
        screen holds tty2 and, drawn again now that the network is up, shows
        the address the route to TEST-NET-1 leaves from (what
        console::lan_address asks); only SSH, 80 and 443 listen outside
        loopback; the firewall policy is active; greenboot's required check
        passed. 5c.2: the node is named rikurisetup and resolved answers mDNS
        on its interface, on UDP 5353 (LLMNR's 5355 stays closed); HTTPS is
        verified by the node's CA as rikurisetup.local; as the guest's address
        it is refused before the probe's route and verified after it, with the
        same service process and no restart between."""
        show = self.vm(SHOW_CP, check=False) or ""
        pid = main_pid(show)
        owner = (self.vm("stat -c %%U /proc/%d" % pid, check=False) or "").strip() if pid else ""
        self.check("the control plane runs as its own user", service_ok(show, owner),
                   "%s; its process's user: %s" % ("; ".join(show.split()), owner or "none"))

        try:
            status, body = parse_http(self.fetch_plain("/ca.crt"))
            pem = body.decode("ascii")
            fingerprint = pem_fingerprint(pem) if status == 200 else None
        except (OSError, ValueError) as e:
            status, pem, fingerprint = "no answer (%s)" % e, "", None
        self.check("the CA certificate over HTTP", fingerprint is not None,
                   "GET http://127.0.0.1:%d/ca.crt: %s; fingerprint %s" % (HTTP_PORT, status, fingerprint))

        setup = None
        if fingerprint:
            cafile = os.path.join(self.workdir, "node-ca.crt")   # kept: the drill's workdir is the run's own
            with open(cafile, "w", encoding="ascii") as f:
                f.write(pem)
            try:
                status, setup = parse_http(self.fetch_tls("/api/setup", cafile))
                detail = "%s %s" % (status, setup[:300].decode("utf-8", "replace"))
            except OSError as e:
                status, detail = None, "no answer (%s)" % e
        else:
            status, detail = None, "no CA certificate to trust"
        self.check("the API over HTTPS with only the node's CA",
                   status == 200 and setup_ok(setup, fingerprint),
                   "GET https://localhost:%d/api/setup: %s" % (HTTPS_PORT, detail))

        try:
            answer = self.fetch_tls("/api/setup", None)
            refused, detail = False, "answered: %r" % answer[:60]
        except ssl.SSLCertVerificationError as e:
            refused, detail = True, "refused: %s" % e
        except OSError as e:
            refused, detail = False, "no answer, so no refusal seen (%s)" % e
        self.check("a client without the node's CA is refused", refused, detail)
        by_name, detail = self.setup_as(cafile, fingerprint, NODE_NAME) if fingerprint else (False, "no CA certificate")
        self.check("HTTPS as rikurisetup.local with only the node's CA", by_name, detail)

        screen = self.vm(SHOW_SCREEN, check=False) or ""
        self.check("the claim screen on tty2", screen_ok(screen), "; ".join(screen.split()))
        # The unit is not ordered after the network: drawn at boot, the screen may
        # say "none yet" (the runbook's "press Enter to look again"). This SSH
        # session proves the network is up; with the probe's route in place,
        # draw it again, then read it.
        # Before the route the daemon has found no address, so its certificate
        # names none: HTTPS as the guest's address is refused. The same process,
        # never restarted, must serve the certificate that names it.
        guest = guest_address(self.vm(GUEST_ADDRESS, check=False))
        run_before = self.vm(SHOW_CP_RUN, check=False) or ""
        if fingerprint and guest:
            refused_before, before_detail = self.refused_as(cafile, guest)
        else:
            refused_before, before_detail = False, "no CA certificate, or no guest address: %s" % guest
        self.vm(PROBE_ROUTE_ADD, check=False)
        try:
            self.vm(RESTART_SCREEN, check=False)
            source = route_source(self.vm(PROBE_ROUTE, check=False))
            tty2 = ""
            for read in range(SCREEN_READS):
                if read:
                    time.sleep(self.screen_pause)
                tty2 = self.vm(TTY2_TEXT, check=False) or ""
                if shows_address(tty2, source):
                    break
            by_address, address_detail = False, "no CA certificate, or no address: %s" % source
            if fingerprint and source:
                for attempt in range(ADDRESS_TRIES):
                    if attempt:
                        time.sleep(self.address_pause)
                    by_address, address_detail = self.setup_as(cafile, fingerprint, source)
                    if by_address:
                        break
        finally:
            self.vm(PROBE_ROUTE_DEL, check=False)
        shown = re.search(r"Address:  .*?(?=\s{2,}|$)", tty2)
        self.check("the claim screen shows the node's address", shows_address(tty2, source),
                   "tty2 shows %r; the route's source: %s" % (shown.group(0) if shown else "no address line", source))
        run_after = self.vm(SHOW_CP_RUN, check=False) or ""
        follows = refused_before and by_address and source == guest and same_run(run_before, run_after)
        address_detail = "before the route %s; the route's source %s, the guest's %s; after: %s; the service %s -> %s" % (
            before_detail, source, guest, address_detail, "; ".join(run_before.split()), "; ".join(run_after.split()))
        self.check("the certificate follows the node's address without a restart", follows, address_detail)
        hostname = (self.vm(HOSTNAME_CMD, check=False) or "").strip()
        self.check("the node is named rikurisetup", hostname == NODE_HOSTNAME, "hostname: %r" % hostname)
        nic = (self.vm(NIC, check=False) or "").strip()
        mdns = self.vm(MDNS_STATUS, check=False) or ""
        self.check("mDNS on the node's interface", mdns_on(mdns, nic),
                   "interface %r; %s" % (nic, "; ".join(line.strip() for line in mdns.splitlines()[:8])))
        udp = self.vm(UDP_LISTEN, check=False) or ""
        udp_ports = exposed_ports(udp)
        self.check("mDNS listens on 5353, LLMNR does not", mdns_listens(udp_ports),
                   "UDP bound outside loopback: %s" % sorted(udp_ports))
        ss = self.vm("ss -Htln", check=False) or ""
        exposed = exposed_ports(ss)
        self.check("only SSH, 80 and 443 listen outside", ports_ok(exposed),
                   "listening outside loopback: %s" % sorted(exposed))
        policy = self.vm(POLICY_INFO, check=False) or ""
        self.check("the firewall opens 80, 443 and mDNS", policy_active(policy),
                   "; ".join(line.strip() for line in policy.splitlines()[:6]) or "no policy reported")
        greenboot = self.journal("-b -u greenboot-healthcheck")
        self.check("greenboot's control plane check", required_passed(greenboot),
                   "required script %s success!: %s" % (CP_REQUIRED, required_passed(greenboot)))
        journal = self.journal("-b -u rikuri-control-plane")
        self.check("no claim code in the journal", code_kept_out(journal),
                   "%r in the service's journal: %s; a code there: %s"
                   % (CODE_NOT_SHOWN, CODE_NOT_SHOWN in journal, bool(CLAIM_CODE.search(journal))))
        self.keep("02-control-plane.out", "\n\n".join([show, screen, tty2, address_detail, hostname, nic, mdns, udp,
                                                       ss, policy, pem, greenboot, journal]))

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

    def mdns_links(self) -> None:
        """PLAT-01: with a container's bridge and veth up, resolved answers
        mDNS on the NIC only; the unit run when resolved started and the one
        udev started for the bridge both succeeded."""
        run = self.vm(MDNS_RUN % self.image, check=False) or ""
        status = unit = bridge = nic = ""
        try:
            nic = (self.vm(NIC, check=False) or "").strip()
            for read in range(MDNS_READS):
                if read:
                    time.sleep(self.mdns_pause)
                status = self.vm(MDNS_STATUS, check=False) or ""
                if mdns_only(status, nic):
                    break
            unit = self.vm(SHOW_MDNS_LINKS, check=False) or ""
            bridge = self.vm(SHOW_MDNS_BRIDGE, check=False) or ""
        finally:
            self.vm(MDNS_STOP, check=False)
        self.keep("01c-mdns-links.out", "\n".join([run, nic, status, unit, bridge]))
        self.check("mDNS only on the node's interface, with a container's bridge up",
                   container_started(run) and mdns_only(status, nic) and oneshot_ran(unit) and oneshot_ran(bridge),
                   "a container started: %s; interface %r; %s; at resolved's start: %s; for %s: %s"
                   % (container_started(run), nic, "; ".join(line.strip() for line in status.splitlines()[:8]),
                      "; ".join(unit.split()), BRIDGE, "; ".join(bridge.split())))

    def subid_after_reboots(self) -> None:
        """Every boot since the first left the files as they were then."""
        files = self.subid_files()
        self.keep("05-subid-after-reboots.out", "\n".join(files))
        same = subid_unchanged(self.first_subid, files)
        self.check("the containers range after reboots", same,
                   "both files as at the first boot, with the range once, after every case's reboots: %s" % same)

    def switch(self, name: str) -> None:
        self.vm("bootc switch --transport containers-storage localhost/rikuri-os:%s" % name, timeout=900)

    def case1(self) -> None:
        self.switch("broken")
        old = self.reboot()
        # Four boots of the broken image, then greenboot's rollback and a boot
        # of the installed image; or, when finalize fails at the shutdown, the
        # installed image at once with the update dropped.
        outcome = wait_until(lambda: case1_outcome(self.status_quiet(), self.installed[1]),
                             timeout=600, interval=self.case1_poll, what="the broken update to roll back or be dropped")
        self.wait_up(old_boot=old)
        everything = self.journal("--grep 'greenboot|rikuri-unapplied-update|bootc'")
        if outcome == "never applied":
            finalize = self.journal(FINALIZE_JOURNAL)
            self.keep("02-case1.out", "\n".join([self.journal("--list-boots"), everything, finalize, self.status()]))
            self.check("case 1, a failing update", False,
                       "never applied: the update was dropped at shutdown, not rolled back; "
                       "'never applied' logged: %s; ostree-finalize-staged: %s"
                       % (NEVER_APPLIED in everything, finalize_error(finalize) or "no error line kept"))
            return
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

    # --- 2c: the node's own update command and the signature policy --------
    def serve_registry(self, binary: str) -> None:
        try:
            self.registry = sp.start_registry(binary, os.path.join(self.workdir, "registry"))
        except RuntimeError as e:
            raise DrillFailure(str(e))
        for argv in seed_argvs(self.image):
            self.run(argv, timeout=1800)
        self.log("the drill's registry holds %s, its signature, and %s" % (SIGNED_REF, UNSIGNED_REF))

    def stop_registry(self) -> None:
        if self.registry is not None:
            self.registry.terminate()
            self.registry.wait(timeout=30)

    def configure_mirror(self) -> None:
        try:
            registries_d = sp.ci_registries_d(self.vm("cat " + sp.REGISTRIES_D_FILE) or "", MIRROR_REPO)
        except ValueError as e:
            raise DrillFailure(str(e))
        self.write_in_vm(MIRROR_CONF, mirror_conf())
        self.write_in_vm(MIRROR_REGISTRIES_D, registries_d)

    def bootc_switch(self, ref: str):
        p = self.run(ssh_argv(self.key, PORT, "bootc switch " + ref), check=False, timeout=1800)
        return p.returncode, p.stdout + p.stderr

    def case4(self) -> None:
        rc, out = self.bootc_switch(UNSIGNED_REF)
        status = self.status()
        self.keep("06-case4.out", "bootc switch %s: exit %d\n%s\n%s" % (UNSIGNED_REF, rc, out, status))
        last = (out.strip().splitlines() or [""])[-1].replace("|", "/")
        self.check("case 4, an unsigned update refused", unsigned_refused(rc, out, status),
                   "bootc switch exit %d: %s; staged: %s" % (rc, last[-300:], staged(status)))

    def case5(self) -> None:
        rc, out = self.bootc_switch(SIGNED_REF)
        status = self.status()
        self.keep("07-case5.out", "bootc switch %s: exit %d\n%s\n%s" % (SIGNED_REF, rc, out, status))
        self.check("case 5, a signed update staged", signed_staged(rc, status),
                   "bootc switch exit %d; staged: %s; the spec follows: %s" % (rc, staged(status), spec_image(status)))

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
    ap.add_argument("--registry", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.artifacts, exist_ok=True)
    drill = Drill(a.image, a.workdir, a.artifacts)
    error = None
    try:
        drill.install()
        drill.first_boot()
        drill.boot_automount()
        drill.control_plane()
        drill.setup_pages()
        drill.owner_pages()
        drill.setup_hub()
        drill.load_variants()
        for case in (drill.case1, drill.case2b, drill.case3):
            case()
        # After the cases, so that a --userns=auto run (which may add ID-mapped
        # layers to the storage bootc switch reads) cannot touch them; run 2
        # (40057729110) saw case 1's update fail to finalize with it before.
        drill.subid_after_reboots()
        drill.userns_auto()
        drill.mdns_links()
        # Last: the signed update stays staged, and no reboot follows.
        drill.serve_registry(a.registry)
        drill.configure_mirror()
        drill.case4()
        drill.case5()
    except (DrillFailure, subprocess.TimeoutExpired) as e:
        error = str(e)
        drill.check("drill", False, error)
        drill.post_mortem()
    finally:
        drill.stop_registry()
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
    return verdict(drill.results, error)


if __name__ == "__main__":
    sys.exit(main())
