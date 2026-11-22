"""Tests for image/rootfs/usr/libexec/rikuri/grubenv-flush.

After a grubenv write, it writes the journal of the filesystem that holds
grubenv to its home blocks (EXT4_IOC_CHECKPOINT), so that GRUB, which ignores
ext4's journal, reads what Linux wrote even after a power cut. The open, the
call and the close are replaced: nothing reaches a real filesystem.
Record: docs/build-records/2026-11-21-grubenv-flush.md
"""
from __future__ import annotations

import contextlib
import errno
import importlib.machinery
import importlib.util
import io
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "rootfs", "usr", "libexec", "rikuri", "grubenv-flush")


def load():
    loader = importlib.machinery.SourceFileLoader("grubenv_flush", SCRIPT)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


m = load()

FD = 7


def iow(kind: str, number: int, size: int) -> int:
    """Linux's _IOW, as include/uapi/asm-generic/ioctl.h builds it (x86_64 and aarch64)."""
    return (1 << 30) | (size << 16) | (ord(kind) << 8) | number


class Fake:
    """The three calls flush() makes, recorded; any of them can fail."""

    def __init__(self, open_error=None, ioctl_error=None):
        self.calls = []
        self.open_error, self.ioctl_error = open_error, ioctl_error

    def opener(self, path, flags):
        self.calls.append(("open", path, flags))
        if self.open_error is not None:
            raise OSError(self.open_error, os.strerror(self.open_error), path)
        return FD

    def ioctl(self, fd, request, arg):
        self.calls.append(("ioctl", fd, request, arg))
        if self.ioctl_error is not None:
            raise OSError(self.ioctl_error, os.strerror(self.ioctl_error))
        return arg

    def closer(self, fd):
        self.calls.append(("close", fd))

    def flush(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = m.flush(opener=self.opener, ioctl=self.ioctl, closer=self.closer)
        return rc, out.getvalue()


class Flush(unittest.TestCase):
    def test_the_checkpoint_call_is_linux_s(self):
        # include/uapi/linux/ext4.h (v6.12): _IOW('f', 43, __u32).
        self.assertEqual(m.EXT4_IOC_CHECKPOINT, iow("f", 43, 4))
        self.assertEqual(m.EXT4_IOC_CHECKPOINT, 0x4004662B)

    def test_the_folder_is_grubenv_s(self):
        self.assertEqual(m.FOLDER, "/boot/grub2")

    def test_checkpoints_the_filesystem_that_holds_grubenv(self):
        fake = Fake()
        rc, out = fake.flush()
        self.assertEqual(rc, 0)
        self.assertEqual(fake.calls, [
            ("open", "/boot/grub2", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC),
            ("ioctl", FD, 0x4004662B, b"\x00\x00\x00\x00"),
            ("close", FD)])
        self.assertIn("written home", out)

    def test_nothing_opened_nothing_called(self):
        fake = Fake(open_error=errno.ENOENT)
        rc, out = fake.flush()
        self.assertEqual(rc, 1)
        self.assertEqual([c[0] for c in fake.calls], ["open"])
        self.assertIn("FAILED", out)
        self.assertIn("power cut", out)

    def test_a_refused_call_is_logged_and_the_folder_closed(self):
        for code in (errno.EPERM, errno.ENOTTY, errno.ENODEV, errno.EIO):
            with self.subTest(code=errno.errorcode[code]):
                fake = Fake(ioctl_error=code)
                rc, out = fake.flush()
                self.assertEqual(rc, 1)
                self.assertEqual([c[0] for c in fake.calls], ["open", "ioctl", "close"])
                self.assertIn("FAILED", out)
                self.assertIn(os.strerror(code), out)
                self.assertIn("power cut", out)


class Main(unittest.TestCase):
    def test_no_arguments_flushes(self):
        fake = Fake()
        with contextlib.redirect_stdout(io.StringIO()):
            rc = m.main([], flush=lambda: fake.flush()[0])
        self.assertEqual(rc, 0)
        self.assertEqual([c[0] for c in fake.calls], ["open", "ioctl", "close"])

    def test_its_failure_is_its_exit(self):
        fake = Fake(ioctl_error=errno.EIO)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(m.main([], flush=lambda: fake.flush()[0]), 1)

    def test_any_argument_does_nothing(self):
        fake = Fake()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = m.main(["/sysroot"], flush=lambda: fake.flush()[0])
        self.assertEqual(rc, 1)
        self.assertEqual(fake.calls, [])
        self.assertIn("nothing done", out.getvalue())


if __name__ == "__main__":
    unittest.main()
