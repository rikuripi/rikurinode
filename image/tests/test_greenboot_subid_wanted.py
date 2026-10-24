"""Tests for image/rootfs/usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid.

greenboot runs the check at every boot as a wanted check: a failure is logged
with the check's own line and the boot still counts as good, because no image
can repair /etc. The check passes only when rikuri-containers-subid, a
RemainAfterExit oneshot, ran and succeeded in this boot.
Record: docs/build-records/2026-10-24-greenboot-subid-wanted.md
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import os
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, os.pardir, "rootfs", "usr", "lib", "greenboot", "check", "wanted.d",
                     "50-rikuri-containers-subid")


def load():
    loader = importlib.machinery.SourceFileLoader("greenboot_subid_wanted", CHECK)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


m = load()

GOOD = "ActiveState=active\nResult=success\n"


class Shipped(unittest.TestCase):
    def test_it_is_executable_python_in_isolated_mode(self):
        self.assertTrue(os.stat(CHECK).st_mode & 0o111)
        with open(CHECK, encoding="ascii") as f:
            self.assertEqual(f.readline(), "#!/usr/bin/python3 -I\n")

    def test_it_asks_systemd_by_absolute_path_with_fixed_arguments(self):
        self.assertEqual(m.ARGV, ["/usr/bin/systemctl", "show", "-p", "ActiveState", "-p", "Result",
                                  "rikuri-containers-subid.service"])


class Verdict(unittest.TestCase):
    def test_ran_and_succeeded(self):
        for text in (GOOD, "Result=success\nActiveState=active\n", "ActiveState=active\nResult=success"):
            with self.subTest(text=text):
                self.assertEqual(m.verdict(text), (True, None))

    def test_anything_else_fails_with_a_plain_reason(self):
        for text in ("Result=success\n",                          # a oneshot that never ran
                     "ActiveState=inactive\nResult=success\n",
                     "ActiveState=failed\nResult=exit-code\n",
                     "ActiveState=activating\nResult=success\n",
                     "ActiveState=active\nResult=exit-code\n",
                     "ActiveState=active \nResult=success\n",
                     "ActiveState=active\nResult=success-ish\n",
                     ""):
            with self.subTest(text=text):
                ok, reason = m.verdict(text)
                self.assertFalse(ok)
                self.assertIn("rikuri-containers-subid", reason)
                self.assertIn("UserNS=auto", reason)
                self.assertIn("journalctl -b -u rikuri-containers-subid", reason)

    def test_the_reason_names_the_state_seen(self):
        ok, reason = m.verdict("ActiveState=failed\nResult=exit-code\n")
        self.assertIn("ActiveState=failed", reason)
        self.assertIn("Result=exit-code", reason)


class Main(unittest.TestCase):
    def run_main(self, run):
        out = io.StringIO()
        return m.main(run=run, out=out), out.getvalue()

    def test_success_is_zero_and_quiet(self):
        calls = []

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, GOOD, "")
        code, out = self.run_main(run)
        self.assertEqual((code, out), (0, ""))
        self.assertEqual(calls[0][0], m.ARGV)
        self.assertFalse(calls[0][1].get("shell", False))
        self.assertIn("timeout", calls[0][1])

    def test_a_failed_unit_is_one_with_its_line(self):
        def run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, "ActiveState=failed\nResult=exit-code\n", "")
        code, out = self.run_main(run)
        self.assertEqual(code, 1)
        self.assertIn("ActiveState=failed", out)

    def test_systemctl_that_cannot_answer_is_one(self):
        def nonzero(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, GOOD, "Failed to connect to bus")

        def raises(exc):
            def run(argv, **kwargs):
                raise exc
            return run
        for run in (nonzero, raises(OSError("no systemctl")), raises(subprocess.TimeoutExpired("systemctl", 30))):
            with self.subTest(run=run):
                code, out = self.run_main(run)
                self.assertEqual(code, 1)
                self.assertIn("rikuri-containers-subid", out)


if __name__ == "__main__":
    unittest.main()
