# Build Record — grubenv's journal written home after each write, so GRUB reads it (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-21 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/grubenv-flush`, from `main` at `5ef53bb`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at the end) |
| **Status** | IN PROGRESS |
| **Change type** | defect fix (OS image: grubenv writes; the VM drill) |

## Intent: the owner's words

- "Next" (2026-11-21), after the experiment's record (#154), whose Next was this fix.
- How to flush: **"ext4's checkpoint call"**. Which writes: **"The node's and greenboot's"**.

## The defect

- The experiment (`docs/build-records/2026-11-21-grubenv-power-cut-experiment.md`, run 44944602844):
  - after a `grub2-editenv` write, a power cut up to at least 30 s later made GRUB read grubenv as it was before the write (12 of 12);
  - `fsfreeze` of /boot right after the write closed it (2 of 2).
- **Why, read in source (data):**
  - `grub2-editenv` rewrites the file, which moves it to a new block (`filefrag` in every trial).
  - /boot is a bind mount of a folder on the root's ext4.
  - ext4 commits the change to its journal within 5 s. The metadata reaches its home block only when it is checkpointed, or written back as a dirty buffer (the kernel's 30 s expiry).
  - GRUB's ext2 driver ignores the journal; e2fsck replays it at the next boot.
  - GRUB's `08_greenboot.cfg` saves `boot_success` **at every boot**, writing in place to the blocks it found.
- **So, after a write and a cut within the window:**
  - GRUB counts from the grubenv before the write. After the give-back that is one boot fewer. After greenboot's own boot-time writes (`boot_success=1`, the counter cleared, the trigger cleared) a healthy update is counted again and can be rolled back.
  - GRUB's `save_env` then writes into the file's old block, which ext4 has freed and may have reused for another file on the root filesystem (`/var` is on it). Derived, not proven.
- To reproduce: let greenboot's check pass, cut the power a few seconds later, and read `boot_success` at the next boot before anything writes grubenv. GRUB set it to 0, so it must read 0; today it reads 1, because GRUB's write went to the old block.

## What exists (read in source, as data; nothing run)

- Linux `v6.12`:
  - `include/uapi/linux/ext4.h`: `EXT4_IOC_CHECKPOINT _IOW('f', 43, __u32)`, which is `0x4004662b` on x86_64 and aarch64;
  - `fs/ext4/ioctl.c`, `ext4_ioctl_checkpoint`:
    - requires `CAP_SYS_ADMIN`; flags 0;
    - `jbd2_journal_lock_updates`, `jbd2_journal_flush`, `jbd2_journal_unlock_updates`;
    - no write access to the mount is taken, so it works through /boot's read-only bind mount;
    - `-ENODEV` without a journal; another filesystem answers `ENOTTY`.
- greenboot-rs `v0.16.4`, `src/main.rs`, `health_check`, writes grubenv:
  - before its checks: `unset_fallback`, and, after a GRUB fallback, `unset_next_deployment_id`;
  - after a pass: `set_boot_status(true)` (`boot_success=1`, then `boot_counter` unset), and `unset_next_deployment_id` when set;
  - after a failure: `boot_success=0` and maybe `boot_counter`, then a reboot (a clean shutdown flushes the journal), or, with no rollback trigger, an error and no reboot.
- The node writes grubenv in one place, `edit_grubenv` in `greenboot-unapplied-update`:
  - the boot check's clear of the trigger, and the give-back, both at boot;
  - the arm, at shutdown.

## Design

- **A new program, `/usr/libexec/rikuri/grubenv-flush`** (Python, as the node's other checks):
  - opens `/boot/grub2`, the folder that holds grubenv, and calls `EXT4_IOC_CHECKPOINT` with flags 0;
  - any error is logged with what it leaves open, and exits 1;
  - no arguments; it never writes grubenv itself.
- **The node's writes:** `edit_grubenv` runs it after each `grub2-editenv` write, before /boot is remounted read-only again.
  - A failed flush is logged ("GRUB may read grubenv as it was before this write after a power cut in the next 30 s"). The write's own result is unchanged: the flush can't undo or redo it.
  - The flush follows every attempted write, failed ones too, since a failed write may still have changed the file.
- **greenboot's writes:** a new unit, `rikuri-grubenv-flush.service`:
  - `After=greenboot-healthcheck.service` (an order only), `Type=oneshot`, `RemainAfterExit=yes`, `WantedBy=multi-user.target`;
  - it runs the program once greenboot's check has ended, pass or fail, and its state says whether it did.
  - `check_image_root.py` holds it as a closed world (keys, overrides, its link), as it does the boot counter's.
- **The cost:** the flush holds the root filesystem's updates while it writes the journal home, typically milliseconds; on a busy node longer. That is the owner's choice over `fsfreeze`, which stops every write and could hang the node if a crash came between freeze and thaw.
- **Rejected:** `fsfreeze` (above); a plain `sync` (it would likely work through the 30 s writeback, but it isn't the explicit call and wasn't asked for); flushing in a timer (it leaves a window).
- **Left open (residual, recorded):**
  - greenboot's `unset_fallback` before its checks is flushed only when the check ends, so a cut during the checks leaves that one write to the old rule;
  - a node whose /boot is not on ext4 (the Pi's layout is not built yet) gets a logged failure, not a flush.

## Task Contract

1. **Outcome:** a power cut shortly after any grubenv write, the node's or greenboot's, no longer makes GRUB count from an old grubenv or write into a block the file has left.
2. **Scope:** high-risk (the rollback path, and a write to the root filesystem's journal; BUILD-PROCEDURE, "Risk tiers").
   - `image/rootfs/usr/libexec/rikuri/grubenv-flush` (new), with `image/tests/test_grubenv_flush.py` (new).
   - `image/rootfs/usr/libexec/rikuri/greenboot-unapplied-update` (`edit_grubenv`), with `image/tests/test_greenboot_unapplied_update.py`.
   - `image/rootfs/usr/lib/systemd/system/rikuri-grubenv-flush.service` (new) and its link in `multi-user.target.wants/`; `image/check_image_root.py` and `image/tests/test_check_image_root.py`.
   - `image/drill/vm_drill.py` and `image/tests/test_vm_drill.py`, a new case 3b:
     - a probe drop-in logs grubenv at the start of greenboot's check, made durable by a clean reboot;
     - the next boot's check passes, and the power is cut seconds after it;
     - at the boot after, the probe must read `boot_success=0` (GRUB's write reached the file), the flush unit must have run, and no flush failure may be logged since the install.
   - Plan §4.1's dated clarification and D22's row.
   - **Not included:** a change to greenboot; the residuals above; N2 and the other backlog items; the Pi.
3. **Done when:**
   - Red: the new tests committed first and seen failing in CI (the unit tests, and case 3b reading `boot_success=1`).
   - The fix in its own commit; the full gate passes in CI; the image workflow's VM drill passes, with case 3b green and cases 1, 1b, 2b, 2d, 2e and 3 as before.
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** the files above and this record. On the Mac: `ast` parse checks and `git diff --check`. The Python tests and the drill run in CI only (`safe-run.sh` cannot run on this Mac). Reading Linux's, greenboot's and GRUB's source on GitHub (done; data, nothing run). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Red tests, `404b14d`

- `test_grubenv_flush.py` (new):
  - the call is Linux's `_IOW('f', 43, __u32)` (`0x4004662b`); the folder is `/boot/grub2`;
  - it opens the folder read-only as a directory, makes the call with flags 0, and closes it;
  - a failed open makes no call; a refused call (`EPERM`, `ENOTTY`, `ENODEV`, `EIO`) is logged with what it leaves open, the folder closed, and exit 1;
  - `main` flushes with no arguments, exits with the flush's result, and does nothing given an argument.
- `test_greenboot_unapplied_update.py`:
  - **New:**
    - the program's path;
    - the clear, the arm and the give-back each followed by the flush;
    - a failed write flushed too;
    - a failed flush logged, the write's result kept and /boot restored;
    - no write, no flush (on trial, no trigger, the remount failed).
  - **Reason for the changes to existing tests:**
    - the fake runner answers the flush command (a fixture; any other command still fails a test);
    - the three read-only-/boot tests now expect the flush between the write and the remount back (`calls[-3:]` → `calls[-4:]`): that order is the new behaviour, and it pins the flush before /boot is read-only again;
    - `test_a_boot_that_counts_writes_nothing` also requires no flush: a tightening.
- `test_check_image_root.py`:
  - the `Root` fixture writes the program, the unit and its link once they ship, as it does the boot counter's;
  - a new class `GrubenvFlush`:
    - the shipped files pass, and the whole check runs it;
    - the program missing, not executable or a link; the unit missing; the link missing or elsewhere;
    - the unit is a closed world (9 cases); an override is a finding.
- `vm_drill.py`, `test_vm_drill.py`: case 3b, after case 3, with its check in `EXPECTED` and its place in `main`'s order.
  - The probe drop-in sorts before every other drop-in of greenboot's check.
  - The pure helpers (`grubenv_value`, `seconds_since`, `case3b_result`) are unit-tested: GRUB's write must have reached grubenv, the flush must have run with success, no flush failure may be logged, and the cut must come within 20 s.
  - **Reason:** a new case; nothing loosened.
- On the Mac: every changed Python file parses; `git diff --check` clean; a plain import of the drill evaluated two of its pure helpers (`seconds_since`, `case3b_result`), a smoke check only. The tests run in CI.

### CI on `404b14d` (red): Fail, as expected

- `Full gate (Ubuntu)`, [run 44948838565](https://github.com/rikuripi/rikurinode/actions/runs/44948838565): `FAILED (failures=8, errors=10)`, all in the new or changed tests:
  - `test_grubenv_flush` does not load (the program does not exist);
  - `GrubenvFlush` (image check): `check_grubenv_flush` does not exist;
  - `test_greenboot_unapplied_update`: `GRUBENV_FLUSH` does not exist; the clear, the arm and the give-back are not flushed; the three read-only-/boot tests miss the flush.
- The OS image, [run 44948838507](https://github.com/rikuripi/rikurinode/actions/runs/44948838507): built and checked; the USB install passed. The VM drill failed on case 3b alone; cases 1, 1b (`['2', '2', '1']`), 2b, 2d, 2e, 3, 4 and 5 Pass:
  - `case 3b, a power cut seconds after greenboot's grubenv write | **Fail** | GRUB's write reached grubenv: False (boot_success 1 at the check's start); the flush ran: False; no flush failure logged since the install: True; cut 13.8s after greenboot's check: True`
  - The defect, reproduced on the real image: GRUB's `save_env` after the cut did not reach grubenv, which kept greenboot's `boot_success=1`.

### Fix, `ae10134`

- `grubenv-flush` (new, 0755): `EXT4_IOC_CHECKPOINT` on `/boot/grub2`, as the Design says.
- `greenboot-unapplied-update`:
  - `GRUBENV_FLUSH`;
  - `edit_grubenv` runs it after every write, before /boot's remount back;
  - a failed flush is logged with the program's own line, and the write's result is unchanged.
- `rikuri-grubenv-flush.service` and its link in `multi-user.target.wants/`.
- `check_image_root.py`: `check_grubenv_flush`, in `check_root`.
- Plan §4.1 and D22's row: dated clarifications.
- **Clarified against the Design:** the node's failure line carries the program's own line (`default_run` captures its output), so the reason is not lost.
- On the Mac: every changed Python file parses; `git diff --check` clean. The tests run in CI.

### CI on `2ff8e33`

- `Full gate (Ubuntu)`, [run 44950453865](https://github.com/rikuripi/rikurinode/actions/runs/44950453865): success (seen by the verifier).
- The OS image, [run 44950453875](https://github.com/rikuripi/rikurinode/actions/runs/44950453875): the build and check, and the USB install, passed; the VM drill **failed on case 3b alone**; cases 1, 1b (`['2', '2', '1']`), 2b, 2d, 2e, 3, 4 and 5 Pass:
  - `case 3b, a power cut seconds after greenboot's grubenv write | **Fail** | GRUB's write reached grubenv: False (boot_success 1 at the check's start); the flush ran: True; no flush failure logged since the install: True; cut 3.8s after greenboot's check: True`
- Evidence: the run's `drill-evidence` artifact (`04-case3b.out`, `serial-4.log`, `serial-5.log`), downloaded with the owner's yes, read as data, then deleted.
  - The boot before the cut (end of `serial-4.log`): greenboot's check finished, then `rikuri-grubenv-flush.service` started and finished; nothing else started between them.
  - The boot after it (`04-case3b.out`): the probe read `boot_success=1` at 7.20 s; greenboot wrote `boot_success=1` and cleared `boot_counter` at 7.44 s; the flush logged "the journal of /boot/grub2 written home" at 7.49 s.
- **Diagnosis: Not yet proven.** The checkpoint call ran after greenboot's writes and succeeded, and GRUB's write still did not reach grubenv. Two causes fit, and they need different repairs:
  1. `EXT4_IOC_CHECKPOINT` is not enough where `fsfreeze` was (the experiment, 2 of 2). `fsfreeze` also writes back the block device's own dirty buffers (`sync_blockdev`), which the checkpoint call does not. Read in Linux v6.12, the checkpoint alone was expected to suffice.
  2. Case 3b's probe is wrong: it assumes GRUB saves `boot_success=0` at every boot (greenboot's `08_greenboot.cfg`, as read). If the image's GRUB does not, the probe reads greenboot's 1 whatever the flush does, and the red run's Fail was not evidence of the defect either. The experiment saw GRUB's write only through the counter.
- No repair made yet (none of the two used): the owner decides how to tell them apart.

### Verifier, `2ff8e33`: no Important finding; NOT YET PROVEN, and the drill then failed case 3b (round 1)

- Red to green:
  - `git diff 404b14d ae10134 -- image/tests image/drill` is empty;
  - the red gate's 18 failures are exactly the new or changed tests, and the red drill failed on case 3b alone;
  - every change to an existing test has its reason, and nothing is loosened.
- Read in source:
  - Linux `v6.12`: `0x4004662b` with 4 zero bytes is right, and `ext4_ioctl_checkpoint` takes no write access, so /boot's read-only bind mount serves;
  - greenboot-rs `v0.16.4`: every grubenv write is in the check's `ExecStart`, so `After=` alone runs the flush after them, pass or fail;
  - case 3b cannot pass falsely: the red run read 1 with the same sequence.
- **Hand mutations: Not yet proven by running**; worked through by reading. 13 mutants and variants, all caught:
  - by named tests: the flush removed, moved after the remount, or only on success; a failed flush changing the result; the call's number, flags or folder; `RemainAfterExit`; `Requires=`; the `-`; `check_grubenv_flush` dropped from `check_root`; `case3b_result`'s logic;
  - the unit's link removed from the image: not by the gate (the `Root` fixture makes the link itself, as for the boot counter), but by `check_image_root.py` on the built image and by the drill;
  - the flush removed from `edit_grubenv`: by the unit tests only. Case 3b exercises greenboot's path.
- **Important: none.** Minor:
  1. Survivors: `hit is None or` in `check_grubenv_flush` (no linked-wants-folder test, which BootCounter has; masked in `check_root` by the control plane's own check of the same folder); `flushed != 0` → `> 0` (a flush killed by a signal would go unlogged); `0 <= since` → `0 < since` (equivalent in practice).
  2. `check_grubenv_flush` re-implements `_enabled_problem` and `_unit_found` instead of calling them.
  3. Case 3b's "no flush failure logged" passes when the `journalctl` query itself fails; the node's own flush on the image is shown only by the absence of a failure line.
  4. Outside scope, for the backlog: other grubenv writers (for example Fedora's `grub2-set-bootflag`, if the image ships it), not inventoried; `default_run`'s 60 s timeout around a slow flush, untested.

### The diagnosis, from the experiment: cause 2, observed

- The owner chose **"One more experiment"**: `docs/build-records/2026-11-21-grubenv-flush-methods-experiment.md`, draft PR #156, closed unmerged.
  - [Run 44957539989](https://github.com/rikuripi/rikurinode/actions/runs/44957539989): GRUB does not save `boot_success` at a boot with no `boot_counter`, even after a clean reboot (2 of 2).
  - [Run 44958580763](https://github.com/rikuripi/rikurinode/actions/runs/44958580763), read through GRUB's countdown: after a cut 3 s after the write, the checkpoint call made GRUB read the write, 2 of 2. With no flush GRUB read the old grubenv, 2 of 2. The control read 2.
- **Corrected:**
  - the red run's case 3b Fail (run 44948838507) was **not** evidence of the defect: the probe read greenboot's 1 whatever GRUB read;
  - its Fail with the fix (run 44950453875) was not evidence against the fix;
  - the verifier's "case 3b cannot pass falsely: the red run read 1 with the same sequence" (round 1) rested on the same probe and does not hold.
  - The unit tests' red and green stand: they don't use the probe.
- **The method stays** (the checkpoint call). The repair is to case 3b alone.

### Repair 1: case 3b reads GRUB's countdown

- **Clarified against the Task Contract (2026-11-21, repair 1):** the case's design, scope item `vm_drill.py`, changes as follows. Its files and its place in the drill's order stay the same:
  - the probe drop-in, as before, made durable by a clean reboot;
  - the case first sets `boot_counter=3 boot_success=0` as the node arms it (`ARM_3B`: `remount,rw`, the write, `remount,bind,ro`), with no rollback trigger, so the node's pre-check writes nothing;
  - the clean reboot: GRUB counts to 2; greenboot's check passes and writes `boot_success=1` and unsets the counter (grubenv moves to a new block); the flush unit runs; the power is cut seconds later;
  - **Pass:** the probe at the boot before the cut read `boot_counter=2` (the control: GRUB counted the arm), and the probe after the cut reads no counter and `boot_success=1` (GRUB read greenboot's write). As before, the flush unit ran with success, no flush failure is logged, and the cut came within 20 s.
  - **Fail, the defect:** `boot_counter=1` after the cut, meaning GRUB counted from the file's old block and saved there.
  - "Done when"'s red now means case 3b reading `boot_counter 1`, not `boot_success=1`.
- **Reasons for the test changes (`vm_drill.py`, `test_vm_drill.py`):**
  - `case3b_result` takes both probes. The old reading of `boot_success` could not see GRUB's write, as observed above. This replaces a test that could not fail for the right reason; nothing is loosened. The new reading also fails an empty or partial probe after the cut, which the old one failed only by accident.
  - `Case3b`: the `boot_success=0` pass and its `boot_success=1` failure become the countdown's pass (`boot_counter` 2, then none and `boot_success` 1) and failure (`boot_counter` 1). New: a probe that did not run fails; an arm GRUB did not count fails; a cut at 0.0 s passes, which kills the verifier's `0 <= since` survivor. The flush, failure-line and timing tests are kept, written through one helper.
  - New: `test_case_3b_arms_the_counter_as_the_node_does` pins `ARM_3B`.
- **The red evidence, to be run again:** the fix's commit `ae10134` is reverted in a commit of its own on top of this one, and CI must fail case 3b with `boot_counter 1` (the unit tests fail as at `404b14d`). Then the revert is reverted, and CI must pass. Both runs count inside repair 1.
