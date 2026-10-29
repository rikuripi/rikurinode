"""Tests for image/drill/vm_drill.py, the CI rollback drill's harness.

Only its pure parts run here: the command lines it builds (the VM's network
is restricted, KVM is required, the test key goes only onto the drill's
disk), what it reads from bootc, the drop-ins each case uses, and the
bounded wait; also the pass rule, and the two containers-range steps through
a Drill whose VM commands and journal are stand-ins. The rest of the
orchestration runs only in CI, on an x86_64 runner with KVM
(.github/workflows/image.yml, job drill); its proof is the job's runs,
including the red run. No VM, container or network here.
Records: docs/build-records/2026-10-22-ci-vm-drill.md,
docs/build-records/2026-10-24-drill-orchestration-tests.md
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
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

    def test_network_is_restricted_to_ssh_and_the_drills_registry(self):
        # 2c: one forward out, to the registry on the CI machine's loopback (cases 4 and 5).
        netdev = self.argv[self.argv.index("-netdev") + 1]
        self.assertIn("restrict=on", netdev.split(","))
        self.assertIn("hostfwd=tcp:127.0.0.1:2222-:22", netdev.split(","))
        self.assertIn("guestfwd=tcp:10.0.2.100:5000-tcp:127.0.0.1:5000", netdev.split(","))
        self.assertEqual(netdev.count("hostfwd="), 1)
        self.assertEqual(netdev.count("guestfwd="), 1)
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
    UID = ("[    5.101] h containers-subid[612]: rikuri-containers-subid: /etc/subuid: "
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

    def test_unchanged_needs_both_files(self):
        # Verifier nit 1: all() over no files is True; the length guard refuses it.
        self.assertFalse(d.subid_unchanged([], []))


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


RANGE = "drill:524288:65536\ncontainers:2147483647:2147483648\n"
ADDED = "".join("[    5.1] h containers-subid[612]: rikuri-containers-subid: %s: added "
                "containers:2147483647:2147483648\n" % f for f in d.SUBID_FILES)
WANTED_OK = ("[   10.9] h greenboot[766]:  INFO  greenboot::greenboot > wanted script "
             "/usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid success!\n")
PRESENT = ADDED.replace("added containers:2147483647:2147483648", "containers:2147483647:2147483648 is present")


class StandInDrill(d.Drill):
    """A Drill whose VM is two dicts: file contents and journal text by its
    journalctl arguments. Every journal call is recorded."""

    def __init__(self, artifacts, files, journals):
        super().__init__("localhost/rikuri-os:test", artifacts, artifacts)
        self.files, self.journals, self.journal_calls = files, journals, []
        self.log = lambda message: None

    def vm(self, command, check=True, timeout=300, stdin=None):
        if command.startswith("cat ") and command[4:] in self.files:
            return self.files[command[4:]]
        raise AssertionError("unexpected VM command: %r" % command)

    def journal(self, args):
        self.journal_calls.append(args)
        return self.journals.get(args, "")


class SkippedChecks(unittest.TestCase):
    # greenboot 0.16.4's line for each check greenboot.conf disables (D9; owner, 2026-10-24).
    def test_the_lines_the_first_boot_check_requires(self):
        self.assertEqual(d.DNS_SKIPPED, "Skipping disabled script: 01_repository_dns_check.sh")
        self.assertEqual(d.PLATFORMS_SKIPPED, "Skipping disabled script: 01_update_platforms_check.sh")


class FirstBootChecks(unittest.TestCase):
    # Verifier I1 (2026-10-24): each greenboot condition of the first-boot check is required.
    JOURNAL = ("rikuri-unapplied-update: no rollback trigger set; nothing to do\n"
               " INFO  greenboot::greenboot > Skipping disabled script: 01_repository_dns_check.sh\n"
               " INFO  greenboot::greenboot > Skipping disabled script: 01_update_platforms_check.sh\n"
               " INFO  greenboot            > greenboot health-check passed.\n")
    LINES = {"greenboot passed": "health-check passed",
             "DNS check skipped": "01_repository_dns_check.sh",
             "update-platforms check skipped": "01_update_platforms_check.sh",
             "the check ran": "rikuri-unapplied-update:"}

    def test_every_condition_is_named(self):
        self.assertEqual(list(d.first_boot_checks(self.JOURNAL)), list(self.LINES))

    def test_all_present(self):
        self.assertTrue(all(d.first_boot_checks(self.JOURNAL).values()))

    def test_each_missing_line_fails_its_condition(self):
        for name, fragment in self.LINES.items():
            with self.subTest(name=name):
                journal = "".join(l + "\n" for l in self.JOURNAL.splitlines() if fragment not in l)
                checks = d.first_boot_checks(journal)
                self.assertFalse(checks[name])
                self.assertFalse(all(checks.values()))


class WantedCheck(unittest.TestCase):
    def test_greenboots_success_line_for_the_check(self):
        self.assertTrue(d.wanted_passed(WANTED_OK))
        for text in ("", WANTED_OK.replace("success!", "failed!"), WANTED_OK.replace("50-rikuri", "51-rikuri"),
                     "wanted script /etc/greenboot/check/wanted.d/50-rikuri-containers-subid success!\n",
                     # mutant 2 (08-mutants.out): the exact line, not the path alone
                     "required script /usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid success!\n"):
            with self.subTest(text=text):
                self.assertFalse(d.wanted_passed(text))


class ContainersRangeSteps(unittest.TestCase):
    # Verifier nit 2 of docs/build-records/2026-10-24-drill-first-boot-and-finalize.md.
    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def drill(self, files=None, journal=ADDED, greenboot=WANTED_OK):
        files = dict.fromkeys(d.SUBID_FILES, RANGE) if files is None else files
        return StandInDrill(self.artifacts, files, {"-b -u rikuri-containers-subid": journal,
                                                    "-b -u greenboot-healthcheck": greenboot})

    def result(self, drill, case):
        return [ok for name, ok, _ in drill.results if name == case]

    def test_a_fresh_install_passes_and_is_kept(self):
        drill = self.drill()
        drill.subid_first_boot()
        self.assertEqual(self.result(drill, "the containers range at the first boot"), [True])
        self.assertEqual(drill.first_subid, [RANGE, RANGE])
        with open(os.path.join(self.artifacts, "01a-subid-first-boot.out"), encoding="utf-8") as f:
            kept = f.read()
        self.assertIn("/etc/subuid:\n" + RANGE, kept)
        self.assertIn(ADDED, kept)

    def test_it_reads_this_boots_journal(self):
        drill = self.drill()
        drill.subid_first_boot()
        self.assertEqual(drill.journal_calls, ["-b -u rikuri-containers-subid", "-b -u greenboot-healthcheck"])

    def test_a_range_already_there_at_the_first_boot_fails(self):
        drill = self.drill(journal=PRESENT)
        drill.subid_first_boot()
        self.assertEqual(self.result(drill, "the containers range at the first boot"), [False])

    def test_added_but_not_once_in_a_file_fails(self):
        for text in (RANGE + "containers:2147483647:2147483648\n", "drill:524288:65536\n", ""):
            with self.subTest(text=text):
                drill = self.drill(files={"/etc/subuid": RANGE, "/etc/subgid": text})
                drill.subid_first_boot()
                self.assertEqual(self.result(drill, "the containers range at the first boot"), [False])

    def test_greenboot_must_have_run_the_wanted_check(self):
        for greenboot in ("", WANTED_OK.replace("success!", "failed!"),
                          WANTED_OK.replace("wanted.d", "required.d").replace("wanted script", "required script")):
            with self.subTest(greenboot=greenboot):
                drill = self.drill(greenboot=greenboot)
                drill.subid_first_boot()
                self.assertEqual(self.result(drill, "the containers range at the first boot"), [False])

    def test_after_reboots_passes_only_unchanged(self):
        drill = self.drill()
        drill.subid_first_boot()
        drill.subid_after_reboots()
        self.assertEqual(self.result(drill, "the containers range after reboots"), [True])
        drill.files["/etc/subgid"] = RANGE + "x:1:1\n"
        drill.subid_after_reboots()
        self.assertEqual(self.result(drill, "the containers range after reboots"), [True, False])

    def test_after_reboots_without_a_first_read_fails(self):
        drill = self.drill()
        drill.subid_after_reboots()
        self.assertEqual(self.result(drill, "the containers range after reboots"), [False])


class Verdict(unittest.TestCase):
    def setUp(self):
        self.ALL = [(case, True, "") for case in sorted(d.EXPECTED)]

    def test_every_check_names_a_step(self):
        self.assertEqual(d.EXPECTED, {
            "first boot", "the containers range at the first boot", "case 1, a failing update",
            "case 2b, finalize fails", "case 3, a power cut during the update",
            "the containers range after reboots", "the containers range"})

    def test_all_passed_and_no_error_is_zero(self):
        self.assertEqual(d.verdict(self.ALL, None), 0)

    def test_a_missing_check_fails(self):
        for case in sorted(d.EXPECTED):
            with self.subTest(case=case):
                self.assertEqual(d.verdict([r for r in self.ALL if r[0] != case], None), 1)

    def test_a_failed_check_fails_even_if_it_also_passed(self):
        self.assertEqual(d.verdict(self.ALL + [("the containers range", False, "")], None), 1)
        self.assertEqual(d.verdict(self.ALL + [("an extra step", False, "")], None), 1)

    def test_an_error_fails(self):
        self.assertEqual(d.verdict(self.ALL, "timed out"), 1)


class FirstBootStandIn(StandInDrill):
    """first_boot through stand-ins: the boot wait, bootc's status and the three
    harmless commands it runs answer here; everything else as StandInDrill."""
    HARMLESS = ("getenforce", "grub2-editenv /boot/grub2/grubenv list")

    def __init__(self, artifacts, status_text, greenboot):
        super().__init__(artifacts, dict.fromkeys(d.SUBID_FILES, RANGE),
                         {"-b -u rikuri-containers-subid": ADDED, "-b -u greenboot-healthcheck": greenboot})
        self.status_text = status_text

    def wait_up(self, old_boot=None, timeout=600):
        return "boot-1"

    def status(self):
        return self.status_text

    def vm(self, command, check=True, timeout=300, stdin=None):
        if command in self.HARMLESS or command.startswith("echo 'vm-drill marker' > "):
            return ""
        return super().vm(command, check=check, timeout=timeout, stdin=stdin)


class FirstBoot(unittest.TestCase):
    # Verifier I1, repair 1 mutant 3 (06-repair1-mutants.out): first_boot itself
    # must require every condition, not only first_boot_checks name them.
    STATUS = json.dumps({"status": {"booted": {"image": {"image": {"image": "localhost/rikuri-os:ci",
                                                                   "transport": "registry"},
                                                         "imageDigest": DIGEST}},
                                    "rollback": None, "staged": None}})

    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def first_boot(self, greenboot, status=None):
        drill = FirstBootStandIn(self.artifacts, self.STATUS if status is None else status, greenboot)
        drill.first_boot()
        return [ok for name, ok, _ in drill.results if name == "first boot"]

    def test_a_good_first_boot_passes(self):
        self.assertEqual(self.first_boot(FirstBootChecks.JOURNAL + WANTED_OK), [True])

    def test_each_missing_greenboot_line_fails_it(self):
        for name, fragment in FirstBootChecks.LINES.items():
            with self.subTest(name=name):
                journal = "".join(l + "\n" for l in FirstBootChecks.JOURNAL.splitlines() if fragment not in l)
                self.assertEqual(self.first_boot(journal + WANTED_OK), [False])

    def test_an_unreadable_status_fails_it(self):
        self.assertEqual(self.first_boot(FirstBootChecks.JOURNAL + WANTED_OK, status=""), [False])


# --- 2c: the node's own update command and the signature policy -----------------

def status_json(staged=None, spec="localhost/rikuri-os:ci"):
    deployment = (lambda ref, digest: {"image": {"image": {"image": ref, "transport": "registry"},
                                                 "imageDigest": digest}})
    return json.dumps({"spec": {"image": {"image": spec, "transport": "registry"}},
                       "status": {"booted": deployment("localhost/rikuri-os:ci", DIGEST),
                                  "staged": deployment(*staged) if staged else None, "rollback": None}})


REFUSED = ("error: Switching: Pulling: Creating importer: failed to invoke method OpenImage: "
           "Source image rejected: A signature was required, but no signature exists\n")
SIGNED = (d.SIGNED_REF, d.SIGNED_DIGEST)


class PublishedPin(unittest.TestCase):
    def test_the_first_published_image_by_name_and_digest(self):
        # docs/build-records/2026-10-28-publish-signed-image.md, Status: run 40794568497.
        self.assertEqual(d.SIGNED_REF, "ghcr.io/rikuripi/rikurinode:44.20261029.1")
        self.assertEqual(d.SIGNED_DIGEST,
                         "sha256:c984d651db4f15be5dac56fcd974d230bc248536fade4ceee29323abadfdecfd")

    def test_the_signature_tag_names_the_digest(self):
        self.assertEqual(d.sig_tag("sha256:" + "b" * 64), "sha256-" + "b" * 64 + ".sig")


class MirrorFiles(unittest.TestCase):
    def test_the_conf_rewrites_only_the_images_name_to_the_forwarded_address(self):
        conf = d.mirror_conf()
        self.assertEqual(conf.count("[[registry]]"), 1)
        self.assertIn('prefix = "ghcr.io/rikuripi/rikurinode"', conf)
        self.assertIn('location = "10.0.2.100:5000/rikuripi/rikurinode"', conf)
        self.assertIn("insecure = true", conf)
        self.assertNotIn("mirror", conf)   # a mirror could fall back to ghcr.io

    def test_the_files_go_beside_the_shipped_ones_never_over_them(self):
        self.assertEqual(sorted(d.MIRROR_FILES), sorted([
            "/etc/containers/registries.conf.d/99-drill-registry.conf",
            "/etc/containers/registries.d/drill-registry.yaml"]))
        for path in d.MIRROR_FILES:
            self.assertNotIn(path, ("/etc/containers/policy.json", "/etc/containers/registries.d/rikuri.yaml"))


class SeedArgv(unittest.TestCase):
    def setUp(self):
        self.argvs = d.seed_argvs("localhost/rikuri-os:ci")

    def test_the_signed_image_and_its_signature_are_copied_by_digest_with_no_login(self):
        copies = [a for a in self.argvs if "skopeo" in a]
        self.assertEqual(len(copies), 2)
        image, sig = copies
        self.assertIn("docker://ghcr.io/rikuripi/rikurinode@" + d.SIGNED_DIGEST, image)
        self.assertEqual(image[-1], "docker://127.0.0.1:5000/rikuripi/rikurinode:44.20261029.1")
        self.assertIn("docker://ghcr.io/rikuripi/rikurinode:" + d.sig_tag(d.SIGNED_DIGEST), sig)
        self.assertEqual(sig[-1], "docker://127.0.0.1:5000/rikuripi/rikurinode:" + d.sig_tag(d.SIGNED_DIGEST))
        for a in copies:
            self.assertIn("--preserve-digests", a)
            self.assertIn("--dest-tls-verify=false", a)
            self.assertFalse([x for x in a if "authfile" in x or "creds" in x], a)
            self.assertIn("localhost/rikuri-os:ci", a)   # the image's own skopeo

    def test_the_image_under_test_goes_in_unsigned(self):
        push = [a for a in self.argvs if "push" in a]
        self.assertEqual(push, [["sudo", "podman", "push", "-q", "--tls-verify=false", "localhost/rikuri-os:ci",
                                 "docker://127.0.0.1:5000/rikuripi/rikurinode:drill-unsigned"]])


class StagedStatus(unittest.TestCase):
    def test_reads_the_staged_deployment_and_the_spec(self):
        text = status_json(staged=SIGNED, spec=d.SIGNED_REF)
        self.assertEqual(d.staged(text), SIGNED)
        self.assertEqual(d.spec_image(text), d.SIGNED_REF)

    def test_nothing_staged_or_unreadable(self):
        self.assertIsNone(d.staged(status_json()))
        self.assertIsNone(d.staged(""))
        self.assertIsNone(d.spec_image(""))


class SignatureRules(unittest.TestCase):
    def test_unsigned_refused_for_its_reason_with_nothing_staged(self):
        self.assertTrue(d.unsigned_refused(1, REFUSED, status_json()))

    def test_unsigned_accepted_or_staged_fails(self):
        self.assertFalse(d.unsigned_refused(0, "", status_json()))
        self.assertFalse(d.unsigned_refused(1, REFUSED, status_json(staged=("x", DIGEST))))
        self.assertFalse(d.unsigned_refused(1, REFUSED, ""))

    def test_unsigned_refused_for_another_reason_fails(self):
        self.assertFalse(d.unsigned_refused(1, "error: pinging container registry 10.0.2.100:5000: connection "
                                               "refused\n", status_json()))

    def test_signed_staged_with_its_digest_and_name(self):
        self.assertTrue(d.signed_staged(0, status_json(staged=SIGNED, spec=d.SIGNED_REF)))

    def test_signed_otherwise_fails(self):
        self.assertFalse(d.signed_staged(1, status_json(staged=SIGNED, spec=d.SIGNED_REF)))
        self.assertFalse(d.signed_staged(0, status_json(staged=(d.SIGNED_REF, DIGEST), spec=d.SIGNED_REF)))
        self.assertFalse(d.signed_staged(0, status_json(staged=("ghcr.io/x:1", d.SIGNED_DIGEST), spec=d.SIGNED_REF)))
        self.assertFalse(d.signed_staged(0, status_json(staged=SIGNED, spec="localhost/rikuri-os:ci")))
        self.assertFalse(d.signed_staged(0, status_json()))


class SignatureStandIn(d.Drill):
    """cases 4 and 5 through stand-ins: bootc switch answers from a dict by
    reference, bootc status is fixed, and files written to the VM are kept."""
    SHIPPED = "docker:\n  ghcr.io/rikuripi/rikurinode:\n    use-sigstore-attachments: true\n"

    def __init__(self, artifacts, answers, status_text):
        super().__init__("localhost/rikuri-os:ci", artifacts, artifacts)
        self.answers, self.status_text, self.switched, self.written = answers, status_text, [], {}
        self.log = lambda message: None

    def bootc_switch(self, ref):
        self.switched.append(ref)
        return self.answers[ref]

    def status(self):
        return self.status_text

    def write_in_vm(self, path, text):
        self.written[path] = text

    def vm(self, command, check=True, timeout=300, stdin=None):
        if command == "cat /etc/containers/registries.d/rikuri.yaml":
            return self.SHIPPED
        raise AssertionError("unexpected VM command: %r" % command)


class SignatureCases(unittest.TestCase):
    def setUp(self):
        self.artifacts = tempfile.mkdtemp(prefix="drill-artifacts-")
        self.addCleanup(shutil.rmtree, self.artifacts)

    def run_case(self, case, answer, status_text):
        ref = {"case4": d.UNSIGNED_REF, "case5": d.SIGNED_REF}[case]
        drill = SignatureStandIn(self.artifacts, {ref: answer}, status_text)
        getattr(drill, case)()
        self.assertEqual(drill.switched, [ref])
        return [(name, ok) for name, ok, _ in drill.results]

    def test_the_unsigned_reference_is_the_images_own_name(self):
        self.assertEqual(d.UNSIGNED_REF, "ghcr.io/rikuripi/rikurinode:drill-unsigned")

    def test_case4_passes_only_on_the_policys_refusal(self):
        self.assertEqual(self.run_case("case4", (1, REFUSED), status_json()),
                         [("case 4, an unsigned update refused", True)])
        self.assertEqual(self.run_case("case4", (0, ""), status_json(staged=(d.UNSIGNED_REF, DIGEST))),
                         [("case 4, an unsigned update refused", False)])

    def test_case5_passes_only_when_the_signed_image_is_staged(self):
        self.assertEqual(self.run_case("case5", (0, ""), status_json(staged=SIGNED, spec=d.SIGNED_REF)),
                         [("case 5, a signed update staged", True)])
        self.assertEqual(self.run_case("case5", (1, REFUSED), status_json()),
                         [("case 5, a signed update staged", False)])

    def test_the_mirror_files_are_written_with_the_shipped_setting_renamed(self):
        drill = SignatureStandIn(self.artifacts, {}, "")
        drill.configure_mirror()
        self.assertEqual(sorted(drill.written), sorted(d.MIRROR_FILES))
        self.assertEqual(drill.written["/etc/containers/registries.conf.d/99-drill-registry.conf"], d.mirror_conf())
        self.assertEqual(drill.written["/etc/containers/registries.d/drill-registry.yaml"],
                         "docker:\n  10.0.2.100:5000/rikuripi/rikurinode:\n    use-sigstore-attachments: true\n")

    def test_both_cases_are_required_for_a_pass(self):
        self.assertIn("case 4, an unsigned update refused", d.EXPECTED)
        self.assertIn("case 5, a signed update staged", d.EXPECTED)


if __name__ == "__main__":
    unittest.main()
