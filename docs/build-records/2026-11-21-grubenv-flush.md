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

### Red tests

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
