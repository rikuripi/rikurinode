"""Tests for image/rootfs/usr/libexec/rikuri/mdns-links.

The node's mDNS name is answered only on interfaces with hardware behind
them: the allow-list is derived at each run from /sys/class/net (a link with
a `device` entry; loopback never), every other link resolved knows has mDNS
turned off, an empty list is refused, and resolved's state is read back.
Record: docs/build-records/2026-11-10-plat01-mdns-allow-list.md
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRAM = os.path.join(HERE, os.pardir, "rootfs", "usr", "libexec", "rikuri", "mdns-links")


def load():
    loader = importlib.machinery.SourceFileLoader("mdns_links", PROGRAM)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


m = load()


class Sysfs:
    """A stand-in /sys/class/net: each link a folder, a hardware one with a
    `device` link, as the kernel makes them."""

    def __init__(self, test, physical=(), virtual=()):
        self.path = tempfile.mkdtemp(prefix="sysfs-net-")
        test.addCleanup(shutil.rmtree, self.path)
        os.makedirs(os.path.join(self.path, "lo"))
        for name in physical:
            self.add(name, True)
        for name in virtual:
            self.add(name, False)

    def add(self, name, hardware):
        os.makedirs(os.path.join(self.path, name))
        if hardware:
            os.symlink("../../../devices/pci0000:00/0000:00:02.0", os.path.join(self.path, name, "device"))


class Resolved:
    """A stand-in resolvectl: it knows each link of `known`, keeps what is set,
    and answers `resolvectl mdns` as resolved 259 does."""

    def __init__(self, known, unknown_for=0, refuse=()):
        self.state = dict(known)
        self.calls = []
        self.unknown_for = unknown_for     # tries a new link is not yet known to resolved
        self.refuse = set(refuse)

    def __call__(self, argv):
        self.calls.append(list(argv))
        assert argv[0] == "/usr/bin/resolvectl", argv
        if argv[1:] == ["mdns"]:
            lines = ["Global: yes"] + ["Link %d (%s): %s" % (n, name, value)
                                       for n, (name, value) in enumerate(self.state.items(), 2)]
            return 0, "\n".join(lines) + "\n"
        if len(argv) == 3 and argv[1] == "mdns":
            name = argv[2]
            if name not in self.state:
                return 1, "Failed to resolve interface \"%s\": No such device\n" % name
            return 0, "Link %d (%s): %s\n" % (list(self.state).index(name) + 2, name, self.state[name])
        if len(argv) == 4 and argv[1] == "mdns" and argv[3] == "no":
            name = argv[2]
            if self.unknown_for:
                self.unknown_for -= 1
                return 1, "Failed to set mDNS configuration: Link %s not known\n" % name
            if name in self.refuse:
                return 1, "Failed to set mDNS configuration: Access denied\n"
            self.state[name] = "no"
            return 0, ""
        raise AssertionError("unexpected resolvectl call: %r" % argv)


def run(test, sysfs, resolved, argv=()):
    out = io.StringIO()
    code = m.main(list(argv), sysfs=sysfs.path, run=resolved, sleep=lambda s: None, out=out)
    return code, out.getvalue()


class Shipped(unittest.TestCase):
    def test_it_is_executable_python_in_isolated_mode(self):
        self.assertTrue(os.stat(PROGRAM).st_mode & 0o111)
        with open(PROGRAM, encoding="ascii") as f:
            self.assertEqual(f.readline(), "#!/usr/bin/python3 -I\n")

    def test_it_asks_resolved_by_its_full_path(self):
        self.assertEqual(m.RESOLVECTL, "/usr/bin/resolvectl")
        self.assertEqual(m.SYSFS, "/sys/class/net")


class AllowList(unittest.TestCase):
    def test_only_links_with_hardware_are_allowed(self):
        sysfs = Sysfs(self, physical=("enp1s0", "wlan0", "end0"),
                      virtual=("podman0", "veth0", "veth1", "br-3f2a9c", "tailscale0", "wg0"))
        self.assertEqual(m.allowed(sysfs.path), ["end0", "enp1s0", "wlan0"])

    def test_loopback_is_never_allowed(self):
        sysfs = Sysfs(self, physical=("enp1s0",))
        os.symlink("../../../devices/virtual", os.path.join(sysfs.path, "lo", "device"))
        self.assertEqual(m.allowed(sysfs.path), ["enp1s0"])

    def test_a_bridge_of_any_name_is_not_allowed(self):
        # The old node's lesson: a deny-list never names the next bridge. A
        # name chosen to look physical is still not hardware.
        for name in ("enp9s0", "eth0", "end1", "br-0a1b2c", "podman7", "docker0", "x"):
            with self.subTest(name=name):
                sysfs = Sysfs(self, physical=("enp1s0",), virtual=(name,))
                self.assertEqual(m.allowed(sysfs.path), ["enp1s0"])

    def test_the_others_are_every_link_but_the_allowed_and_loopback(self):
        sysfs = Sysfs(self, physical=("enp1s0",), virtual=("podman0", "veth0", "br-9e"))
        self.assertEqual(m.others(sysfs.path, ["enp1s0"]), ["br-9e", "podman0", "veth0"])


class FullRun(unittest.TestCase):
    def test_every_other_link_is_turned_off_and_the_nic_kept(self):
        sysfs = Sysfs(self, physical=("enp1s0",), virtual=("podman0", "veth0", "br-77"))
        resolved = Resolved({"enp1s0": "yes", "podman0": "yes", "veth0": "yes", "br-77": "yes"})
        code, out = run(self, sysfs, resolved)
        self.assertEqual(code, 0, out)
        self.assertEqual(resolved.state, {"enp1s0": "yes", "podman0": "no", "veth0": "no", "br-77": "no"})
        self.assertNotIn(["/usr/bin/resolvectl", "mdns", "enp1s0", "no"], resolved.calls)
        self.assertIn("allowed: enp1s0", out)

    def test_an_empty_allow_list_is_refused_and_nothing_is_changed(self):
        sysfs = Sysfs(self, virtual=("podman0", "veth0"))
        resolved = Resolved({"podman0": "yes", "veth0": "yes"})
        code, out = run(self, sysfs, resolved)
        self.assertEqual(code, 1)
        self.assertIn("refusing", out)
        self.assertEqual(resolved.calls, [])

    def test_a_link_still_answering_outside_the_list_fails_the_run(self):
        sysfs = Sysfs(self, physical=("enp1s0",), virtual=("podman0",))
        resolved = Resolved({"enp1s0": "yes", "podman0": "yes"}, refuse={"podman0"})
        code, out = run(self, sysfs, resolved)
        self.assertEqual(code, 1)
        self.assertIn("podman0", out)
        self.assertIn("answers mDNS outside the allow-list", out)

    def test_a_link_resolved_lists_but_sysfs_no_longer_has_is_read_back_too(self):
        # A link that went away between the two reads is not the node's: if
        # resolved still answers on it, the run fails rather than pass quietly.
        sysfs = Sysfs(self, physical=("enp1s0",))
        resolved = Resolved({"enp1s0": "yes", "veth3": "yes"})
        code, out = run(self, sysfs, resolved)
        self.assertEqual(code, 1)
        self.assertIn("veth3", out)

    def test_a_link_not_yet_known_to_resolved_is_tried_again(self):
        sysfs = Sysfs(self, physical=("enp1s0",), virtual=("podman0",))
        resolved = Resolved({"enp1s0": "yes", "podman0": "yes"}, unknown_for=2)
        code, out = run(self, sysfs, resolved)
        self.assertEqual(code, 0, out)
        self.assertEqual(resolved.state["podman0"], "no")
        self.assertEqual(resolved.calls.count(["/usr/bin/resolvectl", "mdns", "podman0", "no"]), 3)

    def test_the_tries_are_bounded(self):
        sysfs = Sysfs(self, physical=("enp1s0",), virtual=("podman0",))
        resolved = Resolved({"enp1s0": "yes", "podman0": "yes"}, unknown_for=99)
        code, out = run(self, sysfs, resolved)
        self.assertEqual(code, 1)
        self.assertEqual(resolved.calls.count(["/usr/bin/resolvectl", "mdns", "podman0", "no"]), m.TRIES)

    def test_a_link_already_off_is_left_off(self):
        sysfs = Sysfs(self, physical=("enp1s0",), virtual=("podman0",))
        resolved = Resolved({"enp1s0": "yes", "podman0": "no"})
        code, out = run(self, sysfs, resolved)
        self.assertEqual((code, resolved.state["podman0"]), (0, "no"), out)

    def test_the_nic_answering_off_is_not_a_failure_of_this_program(self):
        # The allow-list says where mDNS may answer, not that it must: a NIC
        # without a cable, or one resolved does not yet run mDNS on, passes.
        sysfs = Sysfs(self, physical=("enp1s0",), virtual=("podman0",))
        resolved = Resolved({"enp1s0": "no", "podman0": "yes"})
        code, out = run(self, sysfs, resolved)
        self.assertEqual(code, 0, out)


class OneLink(unittest.TestCase):
    """As udev starts it for a new link: `mdns-links <link>`."""

    def test_a_new_virtual_link_is_turned_off_and_only_it_is_read_back(self):
        sysfs = Sysfs(self, physical=("enp1s0",), virtual=("podman0", "veth4"))
        resolved = Resolved({"enp1s0": "yes", "podman0": "yes", "veth4": "yes"})
        code, out = run(self, sysfs, resolved, ["veth4"])
        self.assertEqual(code, 0, out)
        self.assertEqual(resolved.state, {"enp1s0": "yes", "podman0": "yes", "veth4": "no"})
        self.assertIn(["/usr/bin/resolvectl", "mdns", "veth4"], resolved.calls)
        self.assertNotIn(["/usr/bin/resolvectl", "mdns"], resolved.calls)

    def test_a_new_physical_link_is_left_as_it_is(self):
        sysfs = Sysfs(self, physical=("enp1s0", "wlan0"))
        resolved = Resolved({"enp1s0": "yes", "wlan0": "yes"})
        code, out = run(self, sysfs, resolved, ["wlan0"])
        self.assertEqual(code, 0, out)
        self.assertEqual(resolved.calls, [])

    def test_loopback_is_left_as_it_is(self):
        sysfs = Sysfs(self, physical=("enp1s0",))
        resolved = Resolved({"enp1s0": "yes"})
        code, out = run(self, sysfs, resolved, ["lo"])
        self.assertEqual((code, resolved.calls), (0, []), out)

    def test_a_link_gone_before_it_ran_is_nothing_to_do(self):
        sysfs = Sysfs(self, physical=("enp1s0",))
        resolved = Resolved({"enp1s0": "yes"})
        code, out = run(self, sysfs, resolved, ["veth9"])
        self.assertEqual((code, resolved.calls), (0, []), out)
        self.assertIn("veth9", out)

    def test_a_name_that_is_not_an_interface_name_is_refused(self):
        sysfs = Sysfs(self, physical=("enp1s0",))
        resolved = Resolved({"enp1s0": "yes"})
        for name in ("", "..", "a/b", "-x", "x y", "a" * 16, "veth\n0"):
            with self.subTest(name=name):
                code, out = run(self, sysfs, resolved, [name])
                self.assertEqual(code, 2)
        self.assertEqual(resolved.calls, [])

    def test_more_than_one_argument_is_refused(self):
        sysfs = Sysfs(self, physical=("enp1s0",))
        code, out = run(self, sysfs, Resolved({"enp1s0": "yes"}), ["veth0", "veth1"])
        self.assertEqual(code, 2)

    def test_a_new_link_answering_after_its_turn_fails(self):
        sysfs = Sysfs(self, physical=("enp1s0",), virtual=("veth4",))
        resolved = Resolved({"enp1s0": "yes", "veth4": "yes"}, refuse={"veth4"})
        code, out = run(self, sysfs, resolved, ["veth4"])
        self.assertEqual(code, 1)

    def test_an_empty_allow_list_is_refused_for_one_link_too(self):
        sysfs = Sysfs(self, virtual=("veth4",))
        resolved = Resolved({"veth4": "yes"})
        code, out = run(self, sysfs, resolved, ["veth4"])
        self.assertEqual((code, resolved.calls), (1, []))


class ReadBack(unittest.TestCase):
    def test_the_links_answering_are_read_from_resolvectl(self):
        text = "Global: yes\nLink 2 (enp1s0): yes\nLink 5 (podman0): no\nLink 6 (veth0): yes\n"
        self.assertEqual(m.answering(text), ["enp1s0", "veth0"])
        self.assertEqual(m.answering("Global: yes\n"), [])
        self.assertEqual(m.answering("Link 2 (enp1s0): resolve\n"), [])

    def test_a_status_it_cannot_read_is_not_an_empty_one(self):
        for text in ("", "Global: yes\nLink two (x): yes\n", "Failed to get global data: Connection refused\n"):
            with self.subTest(text=text):
                self.assertIsNone(m.answering(text))


if __name__ == "__main__":
    unittest.main()
