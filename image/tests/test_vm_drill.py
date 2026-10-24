"""Tests for image/drill/vm_drill.py, the CI rollback drill's harness.

Only its pure parts run here: the command lines it builds (the VM's network
is restricted, KVM is required, the test key goes only onto the drill's
disk), what it reads from bootc, the drop-ins each case uses, and the
bounded wait. The orchestration itself runs only in CI, on an x86_64 runner
with KVM (.github/workflows/image.yml, job drill); its proof is the job's
runs, including the red run. No VM, container or network here.
Record: docs/build-records/2026-10-22-ci-vm-drill.md
"""
from __future__ import annotations

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "drill"))
import vm_drill as d  # noqa: E402

DIGEST = "sha256:" + "a" * 64


class QemuArgv(unittest.TestCase):
    def setUp(self):
        self.argv = d.qemu_argv(disk="/w/disk.raw", vars_fd="/w/vars.fd", serial_log="/w/serial.log",
                                port=2222, pidfile="/w/qemu.pid")

    def test_requires_kvm(self):
        self.assertIn("-enable-kvm", self.argv)

    def test_network_is_restricted_to_one_loopback_ssh_forward(self):
        netdev = self.argv[self.argv.index("-netdev") + 1]
        self.assertIn("restrict=on", netdev.split(","))
        self.assertIn("hostfwd=tcp:127.0.0.1:2222-:22", netdev.split(","))
        self.assertEqual(netdev.count("hostfwd="), 1)
        self.assertEqual(self.argv.count("-netdev"), 1)

    def test_uefi_code_is_read_only_and_vars_are_the_runs_own_copy(self):
        drives = [self.argv[i + 1] for i, a in enumerate(self.argv) if a == "-drive"]
        code = [x for x in drives if d.OVMF_CODE in x]
        self.assertEqual(len(code), 1)
        self.assertIn("readonly=on", code[0])
        self.assertTrue(any("file=/w/vars.fd" in x and "readonly" not in x for x in drives))

    def test_boots_the_drill_disk_and_logs_the_serial_console(self):
        joined = " ".join(self.argv)
        self.assertIn("file=/w/disk.raw", joined)
        self.assertIn("file:/w/serial.log", joined)
        self.assertIn("-daemonize", self.argv)
        self.assertEqual(self.argv[self.argv.index("-pidfile") + 1], "/w/qemu.pid")
        self.assertEqual(self.argv[self.argv.index("-display") + 1], "none")


class InstallArgv(unittest.TestCase):
    def setUp(self):
        self.argv = d.install_argv(image="localhost/rikuri-os:ci", workdir="/w")

    def test_installs_the_image_with_its_own_bootc(self):
        i = self.argv.index("localhost/rikuri-os:ci")
        self.assertEqual(self.argv[i + 1:i + 4], ["bootc", "install", "to-disk"])
        self.assertIn("--via-loopback", self.argv)
        self.assertEqual(self.argv[-1], "/output/disk.raw")

    def test_the_test_key_and_kernel_arguments_go_onto_the_disk_only(self):
        self.assertEqual(self.argv[self.argv.index("--root-ssh-authorized-keys") + 1], "/output/key.pub")
        kargs = [self.argv[i + 1] for i, a in enumerate(self.argv) if a == "--karg"]
        self.assertEqual(sorted(kargs), ["console=ttyS0", "systemd.wants=sshd.service"])
        self.assertIn("/w:/output", self.argv)


class SshArgv(unittest.TestCase):
    def test_key_only_batch_mode_to_the_forwarded_port(self):
        argv = d.ssh_argv(key="/w/key", port=2222, command="true")
        self.assertEqual(argv[0], "ssh")
        for opt in ("BatchMode=yes", "IdentitiesOnly=yes", "PasswordAuthentication=no"):
            self.assertIn(opt, argv)
        self.assertEqual(argv[argv.index("-i") + 1], "/w/key")
        self.assertEqual(argv[argv.index("-p") + 1], "2222")
        self.assertEqual(argv[-2:], ["root@127.0.0.1", "true"])
        self.assertTrue(any(a.startswith("ConnectTimeout=") for a in argv))


class Booted(unittest.TestCase):
    def status(self, booted, rollback=None, staged=None):
        def entry(ref, digest):
            return None if ref is None else {"image": {"image": {"image": ref, "transport": "containers-storage"},
                                                       "imageDigest": digest}}
        return json.dumps({"status": {"booted": entry(*booted), "rollback": entry(*rollback) if rollback else None,
                                      "staged": entry(*staged) if staged else None}})

    def test_reads_the_booted_image_and_digest(self):
        text = self.status(("localhost/rikuri-os:ci", DIGEST), rollback=("localhost/rikuri-os:broken", "sha256:" + "b" * 64))
        self.assertEqual(d.booted(text), ("localhost/rikuri-os:ci", DIGEST))
        self.assertEqual(d.rollback(text), ("localhost/rikuri-os:broken", "sha256:" + "b" * 64))

    def test_unreadable_status_gives_none(self):
        # Verifier I2: a status without a digest must not read as (ref, None),
        # or "still on the installed image" becomes None == None.
        no_digest = json.dumps({"status": {"booted": {"image": {"image": {"image": "localhost/rikuri-os:ci"}}}}})
        null_image = json.dumps({"status": {"booted": {"image": None}}})
        bad_digest = json.dumps({"status": {"booted": {"image": {"image": {"image": "x"}, "imageDigest": 5}}}})
        no_ref = json.dumps({"status": {"booted": {"image": {"image": {}, "imageDigest": DIGEST}}}})
        for text in ("", "nope", "{}", '{"status": {"booted": null}}', '{"status": 3}',
                     no_digest, null_image, bad_digest, no_ref):
            with self.subTest(text=text):
                self.assertIsNone(d.booted(text))
                self.assertIsNone(d.rollback(text))


class CaseInputs(unittest.TestCase):
    def test_broken_variant_fails_a_required_check(self):
        text = d.containerfile_broken("localhost/rikuri-os:ci")
        self.assertTrue(text.startswith("FROM localhost/rikuri-os:ci\n"))
        self.assertIn("/etc/greenboot/check/required.d/", text)
        self.assertIn("exit 1", text)

    def test_label_variant_changes_only_a_label(self):
        text = d.containerfile_label("localhost/rikuri-os:ci", "a")
        self.assertEqual(text, "FROM localhost/rikuri-os:ci\nLABEL rikuri.drill=a\n")

    def test_failing_finalize_dropin_replaces_the_stop_command(self):
        self.assertEqual(d.FINALIZE_FAILS, "[Service]\nExecStop=\nExecStop=/usr/bin/false\n")

    def test_holding_finalize_dropin_keeps_finalize_after_the_hold(self):
        lines = d.FINALIZE_HOLDS.splitlines()
        self.assertEqual(lines[:2], ["[Service]", "ExecStop="])
        self.assertTrue(lines[2].startswith("ExecStop=/usr/bin/sleep "))
        self.assertEqual(lines[3], "ExecStop=/usr/bin/ostree admin finalize-staged")
        hold = int(lines[2].rsplit(" ", 1)[1])
        self.assertGreater(hold, d.POWER_CUT_AFTER_S * 4)

    def test_dropins_live_in_run_only(self):
        self.assertTrue(d.DROPIN.startswith("/run/systemd/system/ostree-finalize-staged.service.d/"))


class SerialConsole(unittest.TestCase):
    """Verifier I1: case 3 cuts the power only once the trigger has stopped
    in *this* shutdown, read from the serial log after the reboot's offset."""
    EARLIER = ("[  OK  ] Stopped greenboot-set-rollback-trigger.service - Greenboot Rollback trigger.\r\n"
               "         Stopping ostree-finalize-staged.service - OSTree Finalize Staged Deployment...\r\n")
    NOW = ("\x1b[0;32m  OK  \x1b[0m] Stopped \x1b[0;1;39mgreenboot-set-rollback-trigger.service\x1b[0m"
           " - Greenboot Rollback trigger.\r\n")

    def test_earlier_shutdowns_before_the_offset_do_not_count(self):
        text = self.EARLIER + "boot again\r\n"
        self.assertFalse(d.trigger_stopped(text, offset=len(text)))
        self.assertFalse(d.trigger_stopped(text + "Starting something\r\n", offset=len(text)))

    def test_the_trigger_stopping_after_the_offset_counts(self):
        text = self.EARLIER + "boot again\r\n"
        self.assertTrue(d.trigger_stopped(text + self.NOW, offset=len(text)))

    def test_the_trigger_still_stopping_does_not_count(self):
        # Follow-up nit: "Stopping" means the trigger is still running.
        text = "x" * 10
        self.assertFalse(d.trigger_stopped(text + "         Stopping greenboot-set-rollback-trigger.service - "
                                                  "Greenboot Rollback trigger...\r\n", offset=len(text)))

    def test_finalize_alone_does_not_count(self):
        text = "x" * 10
        self.assertFalse(d.trigger_stopped(text + "Stopping ostree-finalize-staged.service - OSTree Finalize "
                                                  "Staged Deployment...\r\n", offset=len(text)))


class ContainersRange(unittest.TestCase):
    def test_the_range_exactly_once(self):
        self.assertTrue(d.subid_once("drill:524288:65536\ncontainers:2147483647:2147483648\n"))
        for text in ("", "drill:524288:65536\n", "containers:2147483647:2147483648\n" * 2,
                     "containers:2147483647:2147483647\n", " containers:2147483647:2147483648\n"):
            with self.subTest(text=text):
                self.assertFalse(d.subid_once(text))


class ContainersRangeFirstBoot(unittest.TestCase):
    # Build Record 2026-10-24-drill-first-boot-and-finalize, item (a).
    UID = ("[    5.101] h rikuri-containers-subid[612]: rikuri-containers-subid: /etc/subuid: "
           "added containers:2147483647:2147483648\n")
    GID = UID.replace("subuid", "subgid")

    def test_added_for_both_files(self):
        self.assertTrue(d.subid_added(self.UID + self.GID))

    def test_anything_less_is_not_added(self):
        unsynced = self.GID.rstrip("\n") + ", but syncing its folder failed (EIO); a power cut now may undo it\n"
        present = self.UID.replace("added containers:2147483647:2147483648",
                                   "containers:2147483647:2147483648 is present")
        for text in ("", self.UID, self.GID, self.UID + unsynced, present + self.GID,
                     self.UID + self.GID.replace("2147483648", "65536")):
            with self.subTest(text=text):
                self.assertFalse(d.subid_added(text))

    def test_unchanged_since_the_first_boot(self):
        first = ["drill:524288:65536\ncontainers:2147483647:2147483648\n"] * 2
        self.assertTrue(d.subid_unchanged(first, list(first)))
        for now in ([first[0], first[1] + "x:1:1\n"], [first[0]], [first[0], ""]):
            with self.subTest(now=now):
                self.assertFalse(d.subid_unchanged(first, now))

    def test_unchanged_still_needs_the_range(self):
        self.assertFalse(d.subid_unchanged(["drill:524288:65536\n"] * 2, ["drill:524288:65536\n"] * 2))


class UnitAndContainer(unittest.TestCase):
    # Verifier nit 3: Result=success alone is also a unit that never ran.
    def test_the_unit_ran_and_succeeded(self):
        self.assertTrue(d.unit_ran("ActiveState=active\nResult=success\n"))
        for text in ("Result=success\n", "ActiveState=inactive\nResult=success\n",
                     "ActiveState=active\nResult=exit-code\n", ""):
            with self.subTest(text=text):
                self.assertFalse(d.unit_ran(text))

    def test_the_container_started_line_exactly(self):
        self.assertTrue(d.container_started("started\n"))
        for text in ("", "Error: not started\n", "started later\n"):
            with self.subTest(text=text):
                self.assertFalse(d.container_started(text))


class WaitUntil(unittest.TestCase):
    def test_false_or_empty_values_keep_waiting(self):
        values = iter([False, "", 0, [], "done"])
        clock = iter(range(100))
        self.assertEqual(d.wait_until(lambda: next(values), timeout=50, interval=1,
                                      clock=lambda: next(clock), sleep=lambda s: None), "done")

    def test_returns_the_first_true_value(self):
        values = iter([None, None, "ok"])
        clock = iter(range(100))
        self.assertEqual(d.wait_until(lambda: next(values), timeout=50, interval=1,
                                      clock=lambda: next(clock), sleep=lambda s: None), "ok")

    def test_raises_after_the_timeout(self):
        clock = iter(range(0, 1000, 10))
        with self.assertRaises(d.DrillFailure):
            d.wait_until(lambda: None, timeout=30, interval=1, clock=lambda: next(clock),
                         sleep=lambda s: None, what="the VM to answer")


if __name__ == "__main__":
    unittest.main()
