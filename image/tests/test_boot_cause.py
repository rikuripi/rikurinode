"""Tests for image/rootfs/usr/libexec/rikuri/boot-cause.

At each boot it records one cause for the boot that ended, from the shutdown
mark, the control plane's heartbeat, pstore, the watchdogs' boot status and the
booted ostree deployment; at the end of each clean shutdown it writes the mark.
The heartbeat is untrusted (the network-facing control plane writes it). The
boot step never fails its unit.
Record: docs/build-records/2026-11-19-boot-cause-record.md
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "rootfs", "usr", "libexec", "rikuri", "boot-cause")


def load():
    loader = importlib.machinery.SourceFileLoader("boot_cause", SCRIPT)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


m = load()

A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"
C = "33333333-3333-4333-8333-333333333333"
I1 = "a" * 64
I2 = "b" * 64
BOOTCSUM = "c" * 64


def entry(boot_id, at, image=I1, pstore=(), cause="clean"):
    return {"v": 1, "boot_id": boot_id, "at": at, "cause": cause, "last_alive": None, "image": image,
            "pstore": list(pstore), "evidence": []}


class Node:
    """A temporary tree with every path the script reads, as on a node."""

    def __init__(self):
        self.path = tempfile.mkdtemp(prefix="boot-cause-")
        self.state = self.p("var/lib/rikuri/boot-cause")
        self.heartbeat = self.p("var/lib/rikuri/control-plane/heartbeat")
        self.pstore = (self.p("sys/fs/pstore"), self.p("var/lib/systemd/pstore"))
        self.watchdogs = self.p("sys/class/watchdog")
        self.cmdline = self.p("proc/cmdline")
        self.sysroot = self.p("sysroot")
        self.boot_id_path = self.p("proc/boot_id")
        for d in (self.state, os.path.dirname(self.heartbeat), self.watchdogs, self.sysroot) + self.pstore:
            os.makedirs(d, exist_ok=True)
        self.deploy(I1)
        self.set_boot(A)

    def p(self, rel):
        return os.path.join(self.path, rel)

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def set_boot(self, boot_id):
        self.write(self.boot_id_path, boot_id + "\n")

    def deploy(self, commit, serial=0):
        """The booted deployment: ostree's boot link, as ostree-prepare-root follows it."""
        link = os.path.join(self.sysroot, "ostree", "boot.1", "default", BOOTCSUM, "0")
        target = os.path.join(self.sysroot, "ostree", "deploy", "default", "deploy", "%s.%d" % (commit, serial))
        os.makedirs(target, exist_ok=True)
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if os.path.lexists(link):
            os.remove(link)
        os.symlink("../../../deploy/default/deploy/%s.%d" % (commit, serial), link)
        self.write(self.cmdline, "BOOT_IMAGE=(hd0,gpt3)/boot/vmlinuz root=UUID=x rw ostree=/ostree/boot.1/default/%s/0 "
                                 "quiet\n" % BOOTCSUM)

    def boot(self, now=1000):
        return m.boot(state=self.state, heartbeat_path=self.heartbeat, pstore_dirs=self.pstore,
                      watchdogs=self.watchdogs, cmdline=self.cmdline, sysroot=self.sysroot,
                      boot_id_path=self.boot_id_path, now=lambda: now)

    def shutdown(self, now=2000):
        return m.shutdown(state=self.state, boot_id_path=self.boot_id_path, now=lambda: now)

    def history(self):
        with open(os.path.join(self.state, m.HISTORY), encoding="utf-8") as f:
            return [json.loads(line) for line in f.read().splitlines()]

    def cleanup(self):
        shutil.rmtree(self.path)


class Case(unittest.TestCase):
    def setUp(self):
        self.node = Node()
        self.addCleanup(self.node.cleanup)


class Constants(unittest.TestCase):
    def test_the_paths_the_unit_and_the_control_plane_rely_on(self):
        self.assertEqual(m.STATE, "/var/lib/rikuri/boot-cause")
        self.assertEqual((m.HISTORY, m.MARK), ("history.jsonl", "shutdown"))
        self.assertEqual(m.HEARTBEAT, "/var/lib/rikuri/control-plane/heartbeat")
        self.assertEqual(m.PSTORE_DIRS, ("/sys/fs/pstore", "/var/lib/systemd/pstore"))
        self.assertEqual((m.KEEP, m.WDIOF_CARDRESET, m.HEARTBEAT_MAX), (100, 0x20, 32))


class Heartbeat(Case):
    def test_decimal_digits_read(self):
        for text, value in (("1700000000\n", 1700000000), ("42", 42), ("0\n", 0)):
            with self.subTest(text=text):
                self.node.write(self.node.heartbeat, text)
                self.assertEqual(m.read_heartbeat(self.node.heartbeat), (value, None))

    def test_anything_else_is_ignored(self):
        for text in ("", "\n", "-1\n", "1e9\n", " 17\n", "17 \n", "17\n\n", "1234567890123\n", "0x10\n",
                     "17\r\n", "١٢\n"):
            with self.subTest(text=text):
                self.node.write(self.node.heartbeat, text)
                value, why = m.read_heartbeat(self.node.heartbeat)
                self.assertIsNone(value)
                self.assertIn("ignored", why)

    def test_too_long_is_ignored_unread(self):
        self.node.write(self.node.heartbeat, "1" * 33)
        value, why = m.read_heartbeat(self.node.heartbeat)
        self.assertIsNone(value)
        self.assertIn("longer than 32 bytes", why)

    def test_a_link_is_never_followed(self):
        # The control plane's user could plant one to make root read another file.
        secret = self.node.p("etc/elsewhere")
        self.node.write(secret, "123\n")
        os.symlink(secret, self.node.heartbeat)
        value, why = m.read_heartbeat(self.node.heartbeat)
        self.assertIsNone(value)
        self.assertIn("cannot be read", why)

    def test_not_a_regular_file_is_ignored(self):
        os.mkdir(self.node.heartbeat)
        self.assertEqual(m.read_heartbeat(self.node.heartbeat)[0], None)
        os.rmdir(self.node.heartbeat)
        os.mkfifo(self.node.heartbeat)
        value, why = m.read_heartbeat(self.node.heartbeat)
        self.assertIsNone(value)
        self.assertIn("not a regular file", why)

    def test_missing(self):
        self.assertEqual(m.read_heartbeat(self.node.heartbeat), (None, "no heartbeat"))


class Mark(Case):
    def path(self):
        return os.path.join(self.node.state, m.MARK)

    def test_reads(self):
        self.node.write(self.path(), json.dumps({"boot_id": A, "at": 5}))
        self.assertEqual(m.read_mark(self.path()), ({"boot_id": A, "at": 5}, None))

    def test_missing(self):
        self.assertEqual(m.read_mark(self.path()), (None, None))

    def test_does_not_read(self):
        for text in ("{", "[]", json.dumps({"boot_id": A}), json.dumps({"boot_id": 1, "at": 5}),
                     json.dumps({"boot_id": A, "at": True}), json.dumps({"boot_id": A, "at": "5"})):
            with self.subTest(text=text):
                self.node.write(self.path(), text)
                mark, why = m.read_mark(self.path())
                self.assertIsNone(mark)
                self.assertTrue(why)

    def test_a_link_is_not_followed(self):
        other = self.node.p("elsewhere")
        self.node.write(other, json.dumps({"boot_id": A, "at": 5}))
        os.symlink(other, self.path())
        self.assertIsNone(m.read_mark(self.path())[0])


class History(Case):
    def test_lines_that_do_not_read_are_counted_and_skipped(self):
        path = os.path.join(self.node.state, m.HISTORY)
        lines = [json.dumps(entry(A, 1)), "not json", json.dumps({"boot_id": B}), json.dumps(entry(B, 2)),
                 json.dumps(dict(entry(C, 3), image=7)), json.dumps(dict(entry(C, 3), pstore="x")),
                 json.dumps(dict(entry(C, 3), at=True)), ""]
        self.node.write(path, "\n".join(lines))
        entries, bad = m.read_history(path)
        self.assertEqual([e["boot_id"] for e in entries], [A, B])
        self.assertEqual(bad, 5)

    def test_missing_is_empty(self):
        self.assertEqual(m.read_history(os.path.join(self.node.state, m.HISTORY)), ([], 0))


class Evidence(Case):
    def test_pstore_lists_both_folders(self):
        self.node.write(os.path.join(self.node.pstore[0], "dmesg-efi-1"), "x")
        os.makedirs(os.path.join(self.node.pstore[1], "1700000000"))
        self.assertEqual(m.list_pstore(self.node.pstore),
                         [self.node.pstore[0] + "/dmesg-efi-1", self.node.pstore[1] + "/1700000000"])
        self.assertEqual(m.list_pstore((self.node.p("missing"),)), [])

    def test_card_reset_bit(self):
        for name, status in (("watchdog0", "32\n"), ("watchdog1", "0\n"), ("watchdog2", "33\n"),
                             ("watchdog3", "x\n"), ("watchdog4", "16\n")):
            self.node.write(os.path.join(self.node.watchdogs, name, "bootstatus"), status)
        os.makedirs(os.path.join(self.node.watchdogs, "watchdog5"))
        self.assertEqual(m.card_resets(self.node.watchdogs), ["watchdog0", "watchdog2"])
        self.assertEqual(m.card_resets(self.node.p("missing")), [])

    def cmdline(self):
        with open(self.node.cmdline, encoding="utf-8") as f:
            return f.read()

    def test_booted_deployment_from_the_ostree_link(self):
        self.assertEqual(m.booted_deployment(self.cmdline(), self.node.sysroot), I1)
        self.node.deploy(I2, serial=1)
        self.assertEqual(m.booted_deployment(self.cmdline(), self.node.sysroot), I2)

    def test_booted_deployment_unknown(self):
        good = self.cmdline()
        arg = "ostree=/ostree/boot.1/default/%s/0" % BOOTCSUM
        for text, why in (("quiet\n", "no ostree= argument"), (good + " " + arg, "two"),
                          (good.replace(arg, "ostree=/ostree/boot.1/default/../../x/0"), "not the form"),
                          (good.replace(arg, "ostree=/ostree/boot.2/default/%s/0" % BOOTCSUM), "boot.2")):
            with self.subTest(why=why):
                self.assertIsNone(m.booted_deployment(text, self.node.sysroot))
        link = os.path.join(self.node.sysroot, "ostree", "boot.1", "default", BOOTCSUM, "0")
        os.remove(link)
        os.symlink(self.node.p("elsewhere"), link)
        self.assertIsNone(m.booted_deployment(good, self.node.sysroot), "outside /sysroot")
        os.remove(link)
        os.symlink("../../../deploy/default/deploy/not-a-commit.0", link)
        self.assertIsNone(m.booted_deployment(good, self.node.sysroot), "not a deployment")
        os.remove(link)
        self.assertIsNone(m.booted_deployment(good, self.node.sysroot), "no link")


class Classify(unittest.TestCase):
    def cause(self, history, mark=None, heartbeat=None, pstore=(), watchdogs=(), image=I1):
        return m.classify(history, mark, heartbeat, list(pstore), list(watchdogs), image)

    def test_first_boot(self):
        self.assertEqual(self.cause([])[:2], ("first-boot", None))

    def test_no_record_but_a_trace_is_unknown(self):
        self.assertEqual(self.cause([], heartbeat=5)[0], "unknown")
        self.assertEqual(self.cause([], mark={"boot_id": A, "at": 5})[0], "unknown")

    def test_clean(self):
        cause, alive, evidence = self.cause([entry(A, 100)], mark={"boot_id": A, "at": 900}, heartbeat=850)
        self.assertEqual((cause, alive), ("clean", 900))
        self.assertIn("shut down cleanly at 900", evidence[-1])

    def test_power_cut_dated_by_the_heartbeat(self):
        cause, alive, evidence = self.cause([entry(A, 100)], heartbeat=850)
        self.assertEqual((cause, alive), ("power-cut", 850))
        self.assertIn("after the last heartbeat at 850", evidence[-1])
        self.assertEqual(self.cause([entry(A, 100)], heartbeat=100)[:2], ("power-cut", 100))

    def test_no_heartbeat_from_the_last_boot_is_unknown(self):
        self.assertEqual(self.cause([entry(A, 100)])[:2], ("unknown", None))
        cause, alive, evidence = self.cause([entry(A, 100)], heartbeat=99)
        self.assertEqual((cause, alive), ("unknown", None))
        self.assertIn("older than the last boot", evidence[0])

    def test_a_mark_naming_another_boot_is_unknown(self):
        cause, alive, evidence = self.cause([entry(A, 100)], mark={"boot_id": B, "at": 900}, heartbeat=850)
        self.assertEqual((cause, alive), ("unknown", None))
        self.assertIn("names boot %s" % B, evidence[0])

    def test_update_applied(self):
        cause, alive, evidence = self.cause([entry(A, 100, I1)], mark={"boot_id": A, "at": 900}, image=I2)
        self.assertEqual((cause, alive), ("update-applied", 900))
        self.assertIn("changed from %s to %s" % (I1, I2), evidence[-1])

    def test_rolled_back(self):
        history = [entry(A, 1, I1), entry(B, 2, I1), entry(C, 3, I2), entry(C + "x", 4, I2)]
        self.assertEqual(self.cause(history, image=I1)[0], "rolled-back")
        self.assertEqual(self.cause(history, image="d" * 64)[0], "update-applied")
        self.assertEqual(self.cause([entry(A, 1, I1), entry(B, 2, I2)], image=I1)[0], "rolled-back")

    def test_an_unreadable_deployment_is_no_change(self):
        cause, _, evidence = self.cause([entry(A, 100, I1)], mark={"boot_id": A, "at": 900}, image=None)
        self.assertEqual(cause, "clean")
        self.assertIn("the booted deployment cannot be read", evidence)
        self.assertEqual(self.cause([entry(A, 100, None)], mark={"boot_id": A, "at": 900}, image=I2)[0], "clean")

    def test_a_new_pstore_record_is_a_crash_first(self):
        last = entry(A, 100, I1, pstore=["/sys/fs/pstore/old"])
        cause, alive, evidence = self.cause([last], heartbeat=850, pstore=["/sys/fs/pstore/old", "/x/new"],
                                            watchdogs=["watchdog0"], image=I2)
        self.assertEqual((cause, alive), ("kernel-crash", 850))
        self.assertIn("/x/new", evidence[-1])
        self.assertEqual(self.cause([last], heartbeat=850, pstore=["/sys/fs/pstore/old"])[0], "power-cut")

    def test_a_watchdog_reset_comes_before_an_image_change(self):
        cause, _, evidence = self.cause([entry(A, 100)], heartbeat=850, watchdogs=["watchdog0"], image=I2)
        self.assertEqual(cause, "watchdog")
        self.assertIn("watchdog0", evidence[-1])

    def test_every_cause_is_named(self):
        self.assertEqual(set(m.CAUSES), {"kernel-crash", "watchdog", "rolled-back", "update-applied", "clean",
                                         "power-cut", "unknown", "first-boot"})


class BootAndShutdown(Case):
    def test_first_boot_then_clean_then_power_cut(self):
        self.assertEqual(self.node.boot(now=1000), 0)
        first = self.node.history()
        self.assertEqual(len(first), 1)
        self.assertEqual((first[0]["boot_id"], first[0]["cause"], first[0]["image"], first[0]["at"]),
                         (A, "first-boot", I1, 1000))
        self.assertEqual(first[0]["evidence"], ["no record of an earlier boot"])

        self.assertEqual(self.node.shutdown(now=1500), 0)
        self.assertTrue(os.path.exists(os.path.join(self.node.state, m.MARK)))
        self.node.set_boot(B)
        self.node.boot(now=2000)
        second = self.node.history()[-1]
        self.assertEqual((second["boot_id"], second["cause"], second["last_alive"]), (B, "clean", 1500))
        self.assertFalse(os.path.exists(os.path.join(self.node.state, m.MARK)), "the mark is consumed")

        self.node.write(self.node.heartbeat, "2600\n")
        self.node.set_boot(C)
        self.node.boot(now=3000)
        third = self.node.history()[-1]
        self.assertEqual((third["cause"], third["last_alive"]), ("power-cut", 2600))

    def test_an_update_applied_at_a_clean_shutdown(self):
        self.node.boot()
        self.node.shutdown()
        self.node.set_boot(B)
        self.node.deploy(I2, serial=1)
        self.node.boot(now=3000)
        self.assertEqual(self.node.history()[-1]["cause"], "update-applied")
        self.assertEqual(self.node.history()[-1]["image"], I2)

    def test_twice_in_one_boot_records_once_and_drops_the_mark(self):
        self.node.boot()
        self.node.shutdown()                    # a manual stop of the unit, not a shutdown
        self.node.boot(now=1100)
        self.assertEqual(len(self.node.history()), 1)
        self.assertFalse(os.path.exists(os.path.join(self.node.state, m.MARK)))

    def test_no_boot_id_records_nothing(self):
        self.node.write(self.node.boot_id_path, "not a boot id\n")
        self.assertEqual(self.node.boot(), 0)
        self.assertFalse(os.path.exists(os.path.join(self.node.state, m.HISTORY)))
        self.assertEqual(self.node.shutdown(), 0)
        self.assertFalse(os.path.exists(os.path.join(self.node.state, m.MARK)))

    def test_keeps_the_last_hundred(self):
        for n in range(105):
            self.node.set_boot("%08d-0000-4000-8000-000000000000" % n)
            self.node.boot(now=1000 + n)
        history = self.node.history()
        self.assertEqual(len(history), 100)
        self.assertEqual(history[0]["at"], 1005)
        self.assertEqual(history[-1]["at"], 1104)

    def test_files_are_readable_by_the_control_plane_and_replaced_whole(self):
        self.node.boot()
        self.node.shutdown()
        for name in (m.HISTORY, m.MARK):
            path = os.path.join(self.node.state, name)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o644)
            self.assertFalse(os.path.exists(path + ".tmp"))

    def test_unreadable_lines_are_noted(self):
        self.node.boot()
        with open(os.path.join(self.node.state, m.HISTORY), "a", encoding="utf-8") as f:
            f.write("garbage\n")
        self.node.set_boot(B)
        self.node.boot(now=2000)
        last = self.node.history()[-1]
        self.assertIn("1 history line(s) did not read", last["evidence"])
        self.assertIn("no heartbeat", last["evidence"])

    def test_the_mark_is_json_naming_the_boot(self):
        self.node.shutdown(now=1234)
        with open(os.path.join(self.node.state, m.MARK), encoding="ascii") as f:
            self.assertEqual(json.loads(f.read()), {"boot_id": A, "at": 1234})


class Main(unittest.TestCase):
    def test_usage(self):
        for argv in ([], ["boot", "x"], ["other"]):
            with self.subTest(argv=argv):
                self.assertEqual(m.main(argv), 2)

    def test_the_boot_step_never_fails_its_unit(self):
        real = m.boot

        def broken():
            raise RuntimeError("boom")
        m.boot = broken
        try:
            self.assertEqual(m.main(["boot"]), 0)
        finally:
            m.boot = real

    def test_a_failed_mark_is_reported(self):
        real = m.shutdown

        def broken():
            raise OSError(30, "Read-only file system")
        m.shutdown = broken
        try:
            self.assertEqual(m.main(["shutdown"]), 1)
        finally:
            m.shutdown = real


if __name__ == "__main__":
    unittest.main()
