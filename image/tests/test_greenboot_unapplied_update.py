"""Tests for image/rootfs/usr/libexec/rikuri/greenboot-unapplied-update.

The check runs before greenboot's health check and clears greenboot's rollback
trigger only when the update it names was never applied (D22; greenboot-rs
#219, reproduced in docs/build-records/2026-10-21-greenboot-drill-parallels.md).
Every other state, including anything unreadable, is left to greenboot.
Record: docs/build-records/2026-10-22-d22-unapplied-update.md
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, os.pardir, "rootfs", "usr", "libexec", "rikuri", "greenboot-unapplied-update")


def load():
    loader = importlib.machinery.SourceFileLoader("greenboot_unapplied_update", CHECK)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


m = load()

NEW = "sha256:" + "a" * 64
OLD = "sha256:" + "b" * 64
OLDER = "sha256:" + "c" * 64


def dep(digest, booted=False):
    d = {"booted": booted}
    if digest is not None:
        d["container-image-reference-digest"] = digest
    return d


class Decide(unittest.TestCase):
    def test_no_trigger_does_nothing(self):
        action, _ = m.decide(None, [dep(OLD, booted=True)])
        self.assertEqual(action, "none")

    def test_empty_trigger_does_nothing(self):
        action, _ = m.decide("", [dep(OLD, booted=True)])
        self.assertEqual(action, "none")

    def test_new_image_on_trial_is_left_to_greenboot(self):
        # Experiment case 1: the update was applied and booted; greenboot must
        # still be able to roll it back if its checks fail.
        action, _ = m.decide(NEW, [dep(NEW, booted=True), dep(OLD)])
        self.assertEqual(action, "trial")

    def test_grub_fallback_is_left_to_greenboot(self):
        # The update was applied (default, index 0) but the node booted the
        # older entry: the new image failed to boot.
        action, _ = m.decide(NEW, [dep(NEW), dep(OLD, booted=True)])
        self.assertEqual(action, "none")

    def test_update_never_applied_clears_the_trigger(self):
        # Experiment cases 2b and 3: the default deployment booted, and it is
        # not the image the trigger names.
        action, reason = m.decide(NEW, [dep(OLD, booted=True), dep(OLDER)])
        self.assertEqual(action, "clear")
        self.assertIn(NEW, reason)
        self.assertIn(OLD, reason)

    def test_never_applied_with_staged_digest_equal_to_rollback(self):
        # The staged image equals the existing rollback image: comparing digests
        # with every deployment would be fooled; the boot order is not.
        action, _ = m.decide(OLDER, [dep(OLD, booted=True), dep(OLDER)])
        self.assertEqual(action, "clear")

    def test_single_deployment_never_applied(self):
        action, _ = m.decide(NEW, [dep(OLD, booted=True)])
        self.assertEqual(action, "clear")

    def test_no_booted_deployment_is_unknown(self):
        action, _ = m.decide(NEW, [dep(OLD), dep(OLDER)])
        self.assertEqual(action, "none")

    def test_booted_without_digest_is_unknown(self):
        action, _ = m.decide(NEW, [dep(None, booted=True), dep(OLDER)])
        self.assertEqual(action, "none")

    def test_two_booted_deployments_are_unknown(self):
        action, _ = m.decide(NEW, [dep(OLD, booted=True), dep(OLDER, booted=True)])
        self.assertEqual(action, "none")

    def test_no_deployments_is_unknown(self):
        action, _ = m.decide(NEW, [])
        self.assertEqual(action, "none")

    def test_checksum_trigger_of_the_booted_deployment_is_on_trial(self):
        # Verifier I1: greenboot arms the trigger with the staged deployment's
        # ostree checksum when the booted system is not a container image.
        csum = "1" * 64
        booted = dict(dep(OLD, booted=True), checksum=csum)
        action, reason = m.decide(csum, [booted, dep(OLDER)])
        self.assertEqual(action, "trial")
        self.assertIn("on trial", reason)

    def test_trigger_that_is_not_an_image_digest_is_unknown(self):
        # The same mode after an applied update to a container image: the
        # trigger is a checksum, the booted digest differs; never clear.
        for trigger in ("1" * 64, "sha256:" + "a" * 63, "sha256:" + "A" * 64, "sha512:" + "a" * 64, NEW + "\n"):
            with self.subTest(trigger=trigger):
                action, reason = m.decide(trigger, [dict(dep(OLD, booted=True), checksum="2" * 64), dep(OLDER)])
                self.assertEqual(action, "none")
                self.assertIn("unknown", reason)

    def test_malformed_deployment_entries_are_unknown(self):
        for deployments in ([None], ["x"], [{"booted": "yes", "container-image-reference-digest": OLD}],
                            [{"booted": True, "container-image-reference-digest": 7}]):
            with self.subTest(deployments=deployments):
                action, _ = m.decide(NEW, deployments)
                self.assertEqual(action, "none")


class ParseGrubenv(unittest.TestCase):
    def test_reads_keys_and_ignores_comments_and_padding(self):
        text = ("# GRUB Environment Block\nboot_success=1\n"
                "greenboot_next_deployment_id=%s\nfallback=1\n%s" % (NEW, "#" * 300))
        env = m.parse_grubenv(text)
        self.assertEqual(env["greenboot_next_deployment_id"], NEW)
        self.assertEqual(env["boot_success"], "1")
        self.assertNotIn("#", "".join(env))

    def test_value_may_contain_equals(self):
        self.assertEqual(m.parse_grubenv("k=a=b\n")["k"], "a=b")


class Deployments(unittest.TestCase):
    def test_reads_rpm_ostree_json(self):
        doc = {"deployments": [dep(OLD, booted=True), dep(OLDER)]}
        self.assertEqual(m.deployments_from_json(json.dumps(doc)), doc["deployments"])

    def test_unreadable_json_gives_none(self):
        for text in ("", "not json", "[]", '{"deployments": 5}', "{}"):
            with self.subTest(text=text):
                self.assertIsNone(m.deployments_from_json(text))


# /proc/self/mountinfo lines: Anaconda's layout (a /boot partition, writable)
# and bootc install's (an automount, then /boot a read-only bind of the root),
# as seen in CI drill run 39713948238.
MI_RW = ("22 1 253:0 / /sysroot rw,relatime - ext4 /dev/mapper/root rw\n"
         "41 22 8:2 / /boot rw,relatime - ext4 /dev/sda2 rw,seclabel\n")
MI_RO = ("22 1 252:3 / /sysroot ro,relatime - ext4 /dev/vda3 rw\n"
         "40 22 0:39 / /boot rw,relatime - autofs systemd-1 rw,fd=84\n"
         "41 40 252:3 /boot /boot ro,relatime - ext4 /dev/vda3 rw,seclabel\n")
MI_NONE = "22 1 253:0 / / rw,relatime - ext4 /dev/mapper/root rw\n"


class BootMount(unittest.TestCase):
    def test_writable_partition(self):
        self.assertIs(m.boot_is_readonly(MI_RW), False)

    def test_read_only_bind_over_an_automount_reads_the_top_mount(self):
        self.assertIs(m.boot_is_readonly(MI_RO), True)

    def test_no_boot_mount_is_unknown(self):
        self.assertIsNone(m.boot_is_readonly(MI_NONE))
        self.assertIsNone(m.boot_is_readonly(""))
        self.assertIsNone(m.boot_is_readonly("garbage\n1 2 3\n"))


class Run(unittest.TestCase):
    """main() with the two commands replaced: no process runs in the tests."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.record = os.path.join(self.tmp.name, "lib", "rikuri", "update-not-applied")
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def runner(self, grubenv_text, status_json, unset_rc=0, rw_rc=0, ro_rc=0, set_rc=0, bootc_json=None, bootc_rc=0):
        def run(argv):
            self.calls.append(argv)
            if argv[:2] == [m.GRUB2_EDITENV, m.GRUBENV] and argv[2] == "list":
                return 0, grubenv_text
            if argv[:2] == [m.GRUB2_EDITENV, m.GRUBENV] and argv[2] == "unset":
                return unset_rc, ""
            if argv[:2] == [m.GRUB2_EDITENV, m.GRUBENV] and argv[2] == "set":
                return set_rc, ""
            if argv == [m.BOOTC, "status", "--json"] and bootc_json is not None:
                return bootc_rc, bootc_json
            if argv == [m.RPM_OSTREE, "status", "--json"]:
                return 0, status_json
            if argv == [m.MOUNT, "-o", "remount,rw", "/boot"]:
                return rw_rc, ""
            if argv == [m.MOUNT, "-o", "remount,bind,ro", "/boot"]:
                return ro_rc, ""
            raise AssertionError("unexpected command %r" % (argv,))
        return run

    def main(self, run, mountinfo=MI_RW, **kw):
        return m.main(run=run, record_path=self.record, mountinfo=lambda: mountinfo, **kw)

    def status(self, *deps):
        return json.dumps({"deployments": list(deps)})

    def test_clears_and_records_when_never_applied(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(OLD, booted=True)))
        rc = m.main(run=run, record_path=self.record, now=lambda: "2026-10-22T00:00:00Z", mountinfo=lambda: MI_RW)
        self.assertEqual(rc, 0)
        self.assertIn([m.GRUB2_EDITENV, m.GRUBENV, "unset", "greenboot_next_deployment_id", "boot_counter"], self.calls)
        with open(self.record) as f:
            line = json.loads(f.read().splitlines()[-1])
        self.assertEqual(line["not_applied"], NEW)
        self.assertEqual(line["booted"], OLD)
        self.assertEqual(line["at"], "2026-10-22T00:00:00Z")

    def test_appends_to_the_record(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(OLD, booted=True)))
        m.main(run=run, record_path=self.record, now=lambda: "t1", mountinfo=lambda: MI_RW)
        m.main(run=run, record_path=self.record, now=lambda: "t2", mountinfo=lambda: MI_RW)
        with open(self.record) as f:
            self.assertEqual(len(f.read().splitlines()), 2)

    def test_leaves_the_trigger_when_on_trial(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(NEW, booted=True), dep(OLD)))
        self.assertEqual(m.main(run=run, record_path=self.record, mountinfo=lambda: MI_RW), 0)
        self.assertFalse(any(c[2] == "unset" for c in self.calls if len(c) > 2))
        self.assertFalse(os.path.exists(self.record))

    def test_no_trigger_reads_no_deployments(self):
        run = self.runner("boot_success=1\n", "unused")
        self.assertEqual(m.main(run=run, record_path=self.record, mountinfo=lambda: MI_RW), 0)
        self.assertNotIn([m.RPM_OSTREE, "status", "--json"], self.calls)

    def test_unreadable_status_leaves_the_trigger(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, "not json")
        self.assertEqual(m.main(run=run, record_path=self.record, mountinfo=lambda: MI_RW), 0)
        self.assertFalse(any(len(c) > 2 and c[2] == "unset" for c in self.calls))

    def test_failing_grubenv_read_leaves_everything(self):
        def run(argv):
            self.calls.append(argv)
            return 1, ""
        self.assertEqual(m.main(run=run, record_path=self.record, mountinfo=lambda: MI_RW), 0)
        self.assertEqual(len(self.calls), 1)

    def test_failing_rpm_ostree_with_readable_output_leaves_the_trigger(self):
        # Verifier I2: a non-zero exit counts as unknown even if stdout parses.
        status = self.status(dep(OLD, booted=True))

        def run(argv):
            self.calls.append(argv)
            if argv[2:3] == ["list"]:
                return 0, "greenboot_next_deployment_id=%s\n" % NEW
            if argv == [m.RPM_OSTREE, "status", "--json"]:
                return 1, status
            raise AssertionError("unexpected command %r" % (argv,))
        self.assertEqual(m.main(run=run, record_path=self.record, mountinfo=lambda: MI_RW), 0)
        self.assertFalse(any(len(c) > 2 and c[2] == "unset" for c in self.calls))
        self.assertFalse(os.path.exists(self.record))

    def test_failing_grubenv_read_with_readable_output_leaves_everything(self):
        def run(argv):
            self.calls.append(argv)
            return 1, "greenboot_next_deployment_id=%s\n" % NEW
        self.assertEqual(m.main(run=run, record_path=self.record, mountinfo=lambda: MI_RW), 0)
        self.assertEqual(len(self.calls), 1)

    def test_read_only_boot_is_remounted_around_the_one_write(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(OLD, booted=True)))
        self.assertEqual(self.main(run, mountinfo=MI_RO), 0)
        tail = self.calls[-3:]
        self.assertEqual(tail, [[m.MOUNT, "-o", "remount,rw", "/boot"],
                                [m.GRUB2_EDITENV, m.GRUBENV, "unset", "greenboot_next_deployment_id", "boot_counter"],
                                [m.MOUNT, "-o", "remount,bind,ro", "/boot"]])
        self.assertTrue(os.path.exists(self.record))

    def test_writable_boot_is_not_remounted(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(OLD, booted=True)))
        self.assertEqual(self.main(run, mountinfo=MI_RW), 0)
        self.assertFalse(any(c[0] == m.MOUNT for c in self.calls))

    def test_unknown_boot_mount_is_not_remounted(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(OLD, booted=True)))
        self.assertEqual(self.main(run, mountinfo=MI_NONE), 0)
        self.assertFalse(any(c[0] == m.MOUNT for c in self.calls))

    def test_nothing_is_remounted_when_nothing_is_cleared(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(NEW, booted=True), dep(OLD)))
        self.assertEqual(self.main(run, mountinfo=MI_RO), 0)
        self.assertFalse(any(c[0] == m.MOUNT for c in self.calls))

    def test_failed_remount_leaves_the_trigger_and_says_so(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(OLD, booted=True)), rw_rc=32)
        self.assertEqual(self.main(run, mountinfo=MI_RO), 1)
        self.assertFalse(any(len(c) > 2 and c[2] == "unset" for c in self.calls))
        self.assertFalse(os.path.exists(self.record))

    def test_failed_unset_on_read_only_boot_still_restores_it(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(OLD, booted=True)), unset_rc=1)
        self.assertEqual(self.main(run, mountinfo=MI_RO), 1)
        self.assertEqual(self.calls[-1], [m.MOUNT, "-o", "remount,bind,ro", "/boot"])
        self.assertFalse(os.path.exists(self.record))

    def test_failed_unset_is_reported_and_not_recorded(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, self.status(dep(OLD, booted=True)), unset_rc=1)
        self.assertEqual(m.main(run=run, record_path=self.record, mountinfo=lambda: MI_RW), 1)
        self.assertFalse(os.path.exists(self.record))


ID = "0f1e2d3c-4b5a-4968-8776-655443322110"
OTHER_ID = "1f1e2d3c-4b5a-4968-8776-655443322110"


def entry(cause, boot_id=ID):
    return json.dumps({"at": 2000, "boot_id": boot_id, "cause": cause, "last_alive": 1940})


def history(*causes):
    """The boot-cause history: one entry per cause, the last this boot's."""
    lines = [entry(c, boot_id="%08x-0000-4000-8000-000000000000" % i) for i, c in enumerate(causes[:-1])]
    return "\n".join(lines + [entry(causes[-1])]) + "\n"


def bootc(staged_digest):
    staged = None if staged_digest is None else {"image": {"imageDigest": staged_digest}}
    return json.dumps({"status": {"staged": staged, "booted": {"image": {"imageDigest": OLD}}}})


class MaxAttempts(unittest.TestCase):
    def test_the_maximum_is_greenboot_conf_s(self):
        conf = os.path.join(HERE, os.pardir, "rootfs", "etc", "greenboot", "greenboot.conf")
        with open(conf) as f:
            values = [line.split("=", 1)[1].strip() for line in f if line.startswith("GREENBOOT_MAX_BOOT_ATTEMPTS=")]
        self.assertEqual(values, [str(m.MAX_BOOT_ATTEMPTS)])


class StagedDigest(unittest.TestCase):
    def test_reads_bootc_status_as_greenboot_does(self):
        self.assertEqual(m.staged_digest(bootc(NEW)), NEW)

    def test_nothing_staged_or_unreadable_is_none(self):
        for text in (bootc(None), "", "not json", "[]", '{"status": null}', '{"status": {"staged": {"image": 5}}}',
                     json.dumps({"status": {"staged": {"image": {"imageDigest": "sha256:short"}}}}),
                     json.dumps({"status": {"staged": {"image": {"imageDigest": 7}}}})):
            with self.subTest(text=text):
                self.assertIsNone(m.staged_digest(text))


class Arm(unittest.TestCase):
    """arm(), at the shutdown greenboot sets its trigger in."""

    # Run's fixtures, not its tests.
    setUp, tearDown, runner, status = Run.setUp, Run.tearDown, Run.runner, Run.status

    def arm(self, run, mountinfo=MI_RW):
        return m.arm(run=run, mountinfo=lambda: mountinfo)

    def sets(self):
        return [c for c in self.calls if len(c) > 2 and c[2] == "set"]

    def test_arms_the_counter_for_the_staged_update(self):
        run = self.runner("greenboot_next_deployment_id=%s\nboot_success=1\n" % NEW, "unused", bootc_json=bootc(NEW))
        self.assertEqual(self.arm(run), 0)
        self.assertEqual(self.sets(), [[m.GRUB2_EDITENV, m.GRUBENV, "set", "boot_counter=3", "boot_success=0"]])

    def test_read_only_boot_is_remounted_around_the_arm(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, "unused", bootc_json=bootc(NEW))
        self.assertEqual(self.arm(run, MI_RO), 0)
        self.assertEqual(self.calls[-3:], [[m.MOUNT, "-o", "remount,rw", "/boot"],
                                           [m.GRUB2_EDITENV, m.GRUBENV, "set", "boot_counter=3", "boot_success=0"],
                                           [m.MOUNT, "-o", "remount,bind,ro", "/boot"]])

    def test_a_restart_during_the_trial_arms_nothing(self):
        # Nothing staged: the trigger is the update on trial; a reset would let it retry for ever.
        run = self.runner("greenboot_next_deployment_id=%s\nboot_counter=1\n" % NEW, "unused", bootc_json=bootc(None))
        self.assertEqual(self.arm(run), 0)
        self.assertEqual(self.sets(), [])

    def test_no_trigger_arms_nothing_and_reads_no_status(self):
        run = self.runner("boot_success=1\n", "unused", bootc_json=bootc(NEW))
        self.assertEqual(self.arm(run), 0)
        self.assertEqual(self.sets(), [])
        self.assertNotIn([m.BOOTC, "status", "--json"], self.calls)

    def test_a_trigger_for_another_update_arms_nothing(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % OLDER, "unused", bootc_json=bootc(NEW))
        self.assertEqual(self.arm(run), 0)
        self.assertEqual(self.sets(), [])

    def test_unreadable_status_arms_nothing(self):
        for json_text, rc in (("not json", 0), (bootc(NEW), 1)):
            with self.subTest(rc=rc):
                self.calls.clear()
                run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, "unused", bootc_json=json_text, bootc_rc=rc)
                self.assertEqual(self.arm(run), 0)
                self.assertEqual(self.sets(), [])

    def test_unreadable_grubenv_arms_nothing(self):
        def run(argv):
            self.calls.append(argv)
            return 1, "greenboot_next_deployment_id=%s\n" % NEW
        self.assertEqual(m.arm(run=run, mountinfo=lambda: MI_RW), 1)
        self.assertEqual(len(self.calls), 1)

    def test_a_failed_arm_says_so(self):
        run = self.runner("greenboot_next_deployment_id=%s\n" % NEW, "unused", bootc_json=bootc(NEW), set_rc=1)
        self.assertEqual(self.arm(run, MI_RO), 1)
        self.assertEqual(self.calls[-1], [m.MOUNT, "-o", "remount,bind,ro", "/boot"])


class GiveBack(unittest.TestCase):
    """give_back(): the rule for a boot of an update on trial."""

    def test_a_first_power_cut_in_a_row_is_given_back(self):
        for counter, want in (("0", 1), ("1", 2), ("2", 3)):
            with self.subTest(counter=counter):
                new, reason = m.give_back(counter, history("update-applied", "power-cut"), ID + "\n")
                self.assertEqual(new, want)
                self.assertIn("given back", reason)

    def test_a_second_power_cut_in_a_row_counts(self):
        new, reason = m.give_back("1", history("update-applied", "power-cut", "power-cut"), ID)
        self.assertIsNone(new)
        self.assertIn("second power cut", reason)

    def test_a_power_cut_after_another_cause_is_given_back(self):
        for before in ("clean", "kernel-crash", "unknown", "update-applied"):
            with self.subTest(before=before):
                self.assertEqual(m.give_back("1", history(before, "power-cut"), ID)[0], 2)

    def test_every_other_cause_counts(self):
        for cause in ("clean", "kernel-crash", "watchdog", "unknown", "update-applied", "rolled-back", "first-boot"):
            with self.subTest(cause=cause):
                new, reason = m.give_back("1", history("update-applied", cause), ID)
                self.assertIsNone(new)
                self.assertIn("counts", reason)

    def test_never_above_the_maximum(self):
        self.assertIsNone(m.give_back("3", history("update-applied", "power-cut"), ID)[0])
        self.assertIsNone(m.give_back("9", history("update-applied", "power-cut"), ID)[0])

    def test_no_counter_or_grub_s_rollback_gives_nothing(self):
        for counter in (None, "-1", "-2"):
            with self.subTest(counter=counter):
                self.assertIsNone(m.give_back(counter, history("update-applied", "power-cut"), ID)[0])

    def test_anything_unreadable_counts(self):
        good = history("update-applied", "power-cut")
        for counter, hist, boot_id, why in (
                ("x", good, ID, "a counter not a number"),
                ("1.5", good, ID, "a counter not whole"),
                ("", good, ID, "an empty counter"),
                ("1", good, "", "no boot id"),
                ("1", good, ID.upper(), "a boot id of another form"),
                ("1", good, OTHER_ID, "this boot not recorded"),
                ("1", entry("power-cut") + "\n", ID, "one entry only"),
                ("1", "", ID, "no history"),
                ("1", good.replace("power-cut", "power-cut\""), ID, "the last line not JSON"),
                ("1", "[1]\n" + entry("power-cut") + "\n", ID, "the entry before not an object"),
                ("1", history("update-applied", "power-cut").replace('"cause": "update-applied"', '"cause": 5'), ID,
                 "the cause before not a word"),
                ("1", entry("update-applied") + "\n" + json.dumps({"boot_id": ID, "cause": None}) + "\n", ID,
                 "this boot's cause not a word")):
            with self.subTest(why=why):
                self.assertIsNone(m.give_back(counter, hist, boot_id)[0])


class RunOnTrial(unittest.TestCase):
    """main() while the update booted is on trial."""

    # Run's fixtures, not its tests.
    setUp, tearDown, runner, status = Run.setUp, Run.tearDown, Run.runner, Run.status

    def trial(self, grubenv_extra, hist, set_rc=0, mountinfo=MI_RW, boot_id=ID):
        run = self.runner("greenboot_next_deployment_id=%s\n%s" % (NEW, grubenv_extra),
                          self.status(dep(NEW, booted=True), dep(OLD)), set_rc=set_rc)
        self.given = os.path.join(self.tmp.name, "lib", "rikuri", "boot-count-given-back")
        self.reads = []

        def read(what, text):
            def f():
                self.reads.append(what)
                return text
            return f
        return m.main(run=run, record_path=self.record, now=lambda: "2026-11-20T00:00:00Z",
                      mountinfo=lambda: mountinfo, given_back_path=self.given,
                      history=read("history", hist), boot_id=read("boot id", boot_id))

    def sets(self):
        return [c for c in self.calls if len(c) > 2 and c[2] == "set"]

    def test_a_first_power_cut_is_given_back_and_recorded(self):
        self.assertEqual(self.trial("boot_counter=1\n", history("update-applied", "power-cut")), 0)
        self.assertEqual(self.sets(), [[m.GRUB2_EDITENV, m.GRUBENV, "set", "boot_counter=2"]])
        with open(self.given) as f:
            line = json.loads(f.read())
        self.assertEqual((line["update"], line["boot_counter"], line["at"]), (NEW, [1, 2], "2026-11-20T00:00:00Z"))
        self.assertFalse(os.path.exists(self.record))
        self.assertFalse(any(len(c) > 2 and c[2] == "unset" for c in self.calls))

    def test_read_only_boot_is_remounted_around_the_give_back(self):
        self.assertEqual(self.trial("boot_counter=0\n", history("update-applied", "power-cut"), mountinfo=MI_RO), 0)
        self.assertEqual(self.calls[-3:], [[m.MOUNT, "-o", "remount,rw", "/boot"],
                                           [m.GRUB2_EDITENV, m.GRUBENV, "set", "boot_counter=1"],
                                           [m.MOUNT, "-o", "remount,bind,ro", "/boot"]])

    def test_a_boot_that_counts_writes_nothing(self):
        self.assertEqual(self.trial("boot_counter=1\n", history("update-applied", "clean")), 0)
        self.assertEqual(self.sets(), [])
        self.assertFalse(os.path.exists(self.given))
        self.assertFalse(any(c[0] == m.MOUNT for c in self.calls))

    def test_no_counter_reads_no_history(self):
        self.assertEqual(self.trial("", history("update-applied", "power-cut")), 0)
        self.assertEqual((self.sets(), self.reads), ([], []))

    def test_a_failed_give_back_is_reported_and_not_recorded(self):
        self.assertEqual(self.trial("boot_counter=1\n", history("update-applied", "power-cut"), set_rc=1), 1)
        self.assertFalse(os.path.exists(self.given))

    def test_a_record_that_cannot_be_written_is_reported(self):
        os.makedirs(os.path.join(self.tmp.name, "lib", "rikuri", "boot-count-given-back"))
        self.assertEqual(self.trial("boot_counter=1\n", history("update-applied", "power-cut")), 1)
        self.assertEqual(len(self.sets()), 1)

    def test_never_applied_gives_nothing_back(self):
        run = self.runner("greenboot_next_deployment_id=%s\nboot_counter=1\n" % NEW, self.status(dep(OLD, booted=True)))
        given = os.path.join(self.tmp.name, "given")
        self.assertEqual(m.main(run=run, record_path=self.record, mountinfo=lambda: MI_RW, given_back_path=given,
                                history=lambda: history("update-applied", "power-cut"), boot_id=lambda: ID), 0)
        self.assertEqual(self.sets(), [])
        self.assertFalse(os.path.exists(given))


if __name__ == "__main__":
    unittest.main()
