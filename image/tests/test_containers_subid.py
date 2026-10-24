"""Tests for image/rootfs/usr/libexec/rikuri/containers-subid.

At every boot, before any ordinary service, the check makes sure /etc/subuid
and /etc/subgid name Podman's `containers` range, which rootful Podman needs
for UserNS=auto. It adds the line only when no `containers` entry exists and
the range overlaps nothing; a file it cannot read or parse, or an overlap, is
left alone and fails the unit. The write replaces the whole file at once.
Record: docs/build-records/2026-10-23-containers-subid.md
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import stat
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, os.pardir, "rootfs", "usr", "libexec", "rikuri", "containers-subid")


def load():
    loader = importlib.machinery.SourceFileLoader("containers_subid", CHECK)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


m = load()

LINE = "containers:2147483647:2147483648\n"
DRILL = "drill:524288:65536\n"


class Constants(unittest.TestCase):
    def test_the_range_is_podmans_documented_one(self):
        self.assertEqual((m.NAME, m.START, m.COUNT), ("containers", 2147483647, 2147483648))
        self.assertEqual(m.LINE, LINE.rstrip("\n"))
        self.assertEqual(m.FILES, ("subuid", "subgid"))


class Parse(unittest.TestCase):
    def test_entries_in_order(self):
        self.assertEqual(m.parse(DRILL + "\nb:1:2"), [("drill", 524288, 65536), ("b", 1, 2)])
        self.assertEqual(m.parse(""), [])
        self.assertEqual(m.parse("zero:0:1\n"), [("zero", 0, 1)])

    def test_anything_else_is_unreadable(self):
        for text in ("drill:524288\n", "drill:524288:65536:1\n", ":1:2\n", "a:x:2\n", "a:1:\n",
                     "a:-1:2\n", "a:1:0\n", "# a comment\n", " a:1:2\n", "a:1:2 \n", "a:+1:2\n",
                     # verifier nit 2: shadow-utils reads numbers in base 0 (017777777777 is octal)
                     "x:017777777777:1\n", "x:1:010\n", "x:0x10:1\n",
                     # verifier nit 1: line ends shadow-utils does not split on
                     "a:1:2\r\n", "a:1:2\x0cb:3:4\n"):
            with self.subTest(text=text):
                self.assertIsNone(m.parse(text))


class Decide(unittest.TestCase):
    def test_no_entry_and_no_overlap_adds(self):
        for entries in ([], [("drill", 524288, 65536)], [("low", 0, 2147483647)],
                        [("top", 4294967295, 1)]):    # verifier I2: the range's upper end
            with self.subTest(entries=entries):
                self.assertEqual(m.decide(entries)[0], "add")

    def test_the_exact_range_is_present(self):
        self.assertEqual(m.decide([("drill", 524288, 65536), ("containers", 2147483647, 2147483648)])[0],
                         "present")

    def test_another_containers_range_is_left_as_chosen(self):
        action, reason = m.decide([("containers", 1000000, 65536)])
        self.assertEqual(action, "present")
        self.assertIn("1000000", reason)

    def test_an_overlap_refuses(self):
        for entries in ([("x", 3000000000, 10)], [("x", 0, 2147483648)], [("x", 4294967294, 1)],
                        [("x", 2147483647, 1)]):
            with self.subTest(entries=entries):
                action, reason = m.decide(entries)
                self.assertEqual(action, "refuse")
                self.assertIn("x", reason)


class Ensure(unittest.TestCase):
    def setUp(self):
        self.etc = tempfile.mkdtemp(prefix="etc-")
        self.addCleanup(shutil.rmtree, self.etc)
        self.lines = []

    def path(self, name="subuid"):
        return os.path.join(self.etc, name)

    def put(self, text, name="subuid", mode=0o644):
        with open(self.path(name), "w", encoding="ascii") as f:
            f.write(text)
        os.chmod(self.path(name), mode)

    def read(self, name="subuid"):
        with open(self.path(name), encoding="ascii") as f:
            return f.read()

    def ensure(self, name="subuid"):
        return m.ensure(self.path(name), log=self.lines.append)

    def test_adds_beside_the_installs_user(self):
        self.put(DRILL)
        self.assertEqual(self.ensure(), 0)
        self.assertEqual(self.read(), DRILL + LINE)
        self.assertEqual(stat.S_IMODE(os.stat(self.path()).st_mode), 0o644)
        self.assertTrue(any("added" in line for line in self.lines))

    def test_a_missing_final_newline_is_kept_apart(self):
        self.put(DRILL.rstrip("\n"))
        self.assertEqual(self.ensure(), 0)
        self.assertEqual(self.read(), DRILL + LINE)

    def test_an_empty_or_absent_file_gets_the_line(self):
        self.put("")
        self.assertEqual(self.ensure(), 0)
        self.assertEqual(self.read(), LINE)
        self.assertEqual(self.ensure("subgid"), 0)
        self.assertEqual(self.read("subgid"), LINE)
        self.assertEqual(stat.S_IMODE(os.stat(self.path("subgid")).st_mode), 0o644)

    def test_present_is_left_untouched(self):
        self.put(DRILL + LINE)
        before = os.stat(self.path())
        self.assertEqual(self.ensure(), 0)
        self.assertEqual(self.read(), DRILL + LINE)
        self.assertEqual(os.stat(self.path()).st_ino, before.st_ino)

    def test_a_second_run_changes_nothing(self):
        self.put(DRILL)
        self.ensure()
        once = self.read()
        self.assertEqual(self.ensure(), 0)
        self.assertEqual(self.read(), once)

    def test_an_unparsable_file_is_left_alone_and_fails(self):
        self.put("# keep\n" + DRILL)
        self.assertEqual(self.ensure(), 1)
        self.assertEqual(self.read(), "# keep\n" + DRILL)
        self.assertTrue(any("left as it is" in line for line in self.lines))

    def test_windows_line_ends_are_left_alone_and_fail(self):
        # Verifier nit 1: read in text mode, "\r\n" became "\n" and the file was
        # rewritten; shadow-utils cannot read such a line, so it is left as it is.
        with open(self.path(), "wb") as f:
            f.write(DRILL.replace("\n", "\r\n").encode("ascii"))
        self.assertEqual(self.ensure(), 1)
        with open(self.path(), "rb") as f:
            self.assertEqual(f.read(), DRILL.replace("\n", "\r\n").encode("ascii"))

    def test_a_failed_folder_sync_after_the_rename_is_not_reported_as_kept(self):
        # Verifier nit 5: the new file is already in place when the folder's fsync fails.
        self.put(DRILL)

        def broken_sync(path):
            raise OSError("I/O error")
        self.assertEqual(m.ensure(self.path(), log=self.lines.append, sync_dir=broken_sync), 0)
        self.assertEqual(self.read(), DRILL + LINE)
        self.assertFalse(any("old file is kept" in line for line in self.lines))
        self.assertTrue(any("added" in line and "folder" in line for line in self.lines))

    def test_an_overlap_is_left_alone_and_fails(self):
        self.put("big:2000000000:300000000\n")
        self.assertEqual(self.ensure(), 1)
        self.assertEqual(self.read(), "big:2000000000:300000000\n")
        self.assertTrue(any("overlap" in line for line in self.lines))

    def test_an_unreadable_path_fails(self):
        os.mkdir(self.path())
        self.assertEqual(self.ensure(), 1)
        self.assertTrue(os.path.isdir(self.path()))

    def test_a_leftover_from_a_cut_is_replaced(self):
        self.put(DRILL)
        with open(self.path() + m.TMP_SUFFIX, "w", encoding="ascii") as f:
            f.write("contai")
        self.assertEqual(self.ensure(), 0)
        self.assertEqual(self.read(), DRILL + LINE)
        self.assertFalse(os.path.exists(self.path() + m.TMP_SUFFIX))

    def test_a_failed_write_keeps_the_old_file(self):
        self.put(DRILL)

        def broken_replace(src, dst):
            raise OSError("no space left")
        self.assertEqual(m.ensure(self.path(), log=self.lines.append, replace=broken_replace), 1)
        self.assertEqual(self.read(), DRILL)
        self.assertFalse(os.path.exists(self.path() + m.TMP_SUFFIX))
        self.assertTrue(any("FAILED" in line for line in self.lines))


class Main(unittest.TestCase):
    def setUp(self):
        self.etc = tempfile.mkdtemp(prefix="etc-")
        self.addCleanup(shutil.rmtree, self.etc)
        self.lines = []

    def put(self, name, text):
        with open(os.path.join(self.etc, name), "w", encoding="ascii") as f:
            f.write(text)

    def read(self, name):
        with open(os.path.join(self.etc, name), encoding="ascii") as f:
            return f.read()

    def test_both_files(self):
        self.put("subuid", DRILL)
        self.put("subgid", DRILL)
        self.assertEqual(m.main(etc=self.etc, log=self.lines.append), 0)
        self.assertEqual(self.read("subuid"), DRILL + LINE)
        self.assertEqual(self.read("subgid"), DRILL + LINE)

    def test_one_refusal_fails_but_the_other_file_is_still_done(self):
        self.put("subuid", "big:2000000000:300000000\n")
        self.put("subgid", DRILL)
        self.assertEqual(m.main(etc=self.etc, log=self.lines.append), 1)
        self.assertEqual(self.read("subuid"), "big:2000000000:300000000\n")
        self.assertEqual(self.read("subgid"), DRILL + LINE)


if __name__ == "__main__":
    unittest.main()
