# Build Record — the installer shows why it stopped (incident: a silent failure on the N150)

| | |
|---|---|
| **Date** | 2026-11-04 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/installer-visible-failure`, from `main` at `f7afa22`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | incident: diagnosis (making a failure visible) |

## Incident

- **Seen** (owner, 2026-11-04): the stick from publish [run 41770737396](https://github.com/rikuripi/rikurinode/actions/runs/41770737396) (`f7afa22`; its `.iso` checked `OK`), booted on the N150. The owner's photo and video show GRUB's "Booting \`Install Rikuri Node'", a blank screen, then about 2 s later **"[FAILED] Failed to start rikuri-installer.service - Rikuri Node installer."** The installer's title, disk list and questions never appeared in any frame (frames every 0.5 s). Nothing was erased: the installer erases only after `ERASE`.
- **Not seen in CI:** on the same `main` (#65's [OS image run 41767934590](https://github.com/rikuripi/rikurinode/actions/runs/41767934590), install evidence), every case ends "[  OK  ] Stopped rikuri-installer.service" and "reboot: Power down". CI's stick uses the serial console and QEMU's disks; the published one uses the screen (`tty1`) and the N150's disks.
- **What is known:** the unit failed before either of the installer's power-offs, so the program either was not started or ended on an error it does not catch. The unit's `TTYReset` and `TTYVHangup` reset the screen when it ends, and the console is quiet, so nothing told the person why. This breaks AGENTS.md, "Nothing important fails silently". The cause is **not yet known**.
- **The owner's decision** (2026-11-04, "go"): make the failure visible first; the cause's fix follows from what the screen then shows, as its own task.

## Task Contract

1. **Outcome:** when the installer stops on anything it did not expect, the screen says so, shows the error, and keeps it there, so the next boot of the stick names the cause.
2. **Scope:** stage 1, the USB installer.
   - `image/installer/rikuri_install.py`:
     - an unexpected error in the installer is kept in `/run/rikuri-installer/error.txt` and shown with `UNEXPECTED`; then, as at every stop, Enter powers off;
     - a second unit, `rikuri-installer-failed.service`, started by the installer unit's `OnFailure=`, writes on the same console the error file and the installer unit's own log (`journalctl -b -u rikuri-installer.service`), which holds systemd's reason when the program was never started;
     - `configure` writes both units.
   - Tests: `image/tests/test_installer.py`.
   - Knowledge layer: `docs/runbooks/install-node.md`, "When it stops".
   - Risk tier: **routine**. Nothing changes before or in the erase and the install, and no expected stop changes.
   - **Not included:** the cause's fix (the next task, after the N150 shows it); N5 (lsblk returning a non-object), except that it is now shown instead of being silent; CI's install test (it cannot produce an unexpected error); the record close-out of #65, which goes first in this branch.
3. **Done when:**
   - unit tests show an unexpected error (for example `lsblk` returning a list) ending in `UNEXPECTED`, the error's line, Enter, and a power-off, with the error kept; a failure while showing it never raises; the units hold `OnFailure=` and the show-failure unit, on both consoles;
   - `Full gate (Ubuntu)` and the OS image workflow pass on the PR (the install test unchanged);
   - one `verifier` pass has no Important finding.
   - Not in this task: the N150 showing the error (the owner's, after a publish).
4. **Authority:** the owner's words above; this branch; a draft PR; no merge. The sandbox refused the video in the Photos temporary folder; the owner copied it to the scratchpad.
5. **Limits:** one task; two repair cycles; two review rounds; development CI at most 3 runs.

## Evidence log

- **#65's close-out** goes first, in its own commit (`cb7f8c0`).
- **Red** (rikuri-drill, `safe-run.sh`, against `main`'s installer): `test_installer.py` `Ran 66 tests` `FAILED (failures=2, errors=20)`:
  - the errors: `no attribute 'guarded'`, `'UNEXPECTED'`, `'SHOW_FAILURE'`, `'HOLD_POWER'`, `'show_failure'`, `'unit_journal'`, `'read_error'` and `'ERROR_FILE'`;
  - the failures: `'\nOnFailure=rikuri-installer-failed.service\n' not found` in the unit, on `tty1` and on `ttyS0`.
  - Test changes: only additions (two classes, one `Configure` test, and `Machine.record_error` with its list), and no existing assertion changed.
- **Fix** (its own commit):
  - `rikuri_install.py`:
    - `guarded(m)` runs the install. On an error it does not expect, it keeps the traceback in `ERROR_FILE` (`System.record_error`) first, then shows `UNEXPECTED` and the error's last line, then `POWER_OFF`, Enter, and power-off. If keeping or showing fails, it carries on, and it returns 8 without raising. `main` runs `guarded(System())`.
    - `show-failure` prints `show_failure(read_error(), unit_journal())`: the message, the kept error (or `NO_ERROR_FILE`), the last `JOURNAL_LINES` (20) lines of `journalctl -b -o cat --no-pager -u rikuri-installer.service`, and `HOLD_POWER`.
    - `unit()` gains `OnFailure=rikuri-installer-failed.service`; `failed_unit()` writes on the same console, reads nothing, keeps the screen, and has no `[Install]`. `configure` writes it.
  - Runbook `install-node.md`, "When it stops": what the new message means, and what to do.
- **A test added after the red commit, and why:** `test_it_is_kept_before_it_waits_for_enter`. The mutant that shows the error before keeping it survived every test, because the red tests checked only that the error was kept. The order matters: on a screen that waits for Enter, the error must already be kept, in case no one presses it. The new test fails on that mutant (`Ran 67 tests` `FAILED (failures=1)`) and passes on the fix. No other test changed.
- **Green** (rikuri-drill, `safe-run.sh`): `image/tests` `Ran 388 tests` `OK`; `.claude/hooks` `Ran 91 tests` `OK`; `scripts/quality/tests` `Ran 156 tests`, with only the 7 known `git` errors (Not yet proven locally; CI's gate). `git diff --check`: clean.
- **Hand mutants: 18 of 18 red** (17 at first, then the one survivor above, after the added test). The mutants:
  - `main` unguarded; no record; a failure to record not caught; no error line; the show not caught; a return of 0; the show before the record;
  - no `OnFailure=`; the failed unit not written; the failed unit resetting the screen;
  - the whole journal shown; no `NO_ERROR_FILE`; no `HOLD_POWER`; the other unit's journal; `unit_journal` or `read_error` raising; `show-failure` printing nothing; the catch narrowed to `OSError`.
- **Not yet proven:** that `OnFailure=` starts and shows on the live system (CI's install test produces no failure), and what the N150 then shows (the owner's boot of a stick published from this change).

## Verifier, round 1, and a repair before merge

- **Verifier, one pass** (on `ac02c47`): **PASS, no Important finding.** The full gate and the OS image workflow were not yet seen. It reran red and green; ran the real entry point in rikuri-drill (an unexpected error kept and shown; `show-failure` printing it); and ran `systemd-analyze verify` on both units with no warning. It tried 17 mutants: 8 killed, 9 survived (one nit, at the routine tier). Its nits:
  1. the survivors: `OnFailure=` moved into `[Service]` (systemd ignores it there); the writer and the reader of the error file not tested together; the failed unit's output setting not pinned;
  2. wording: `UNEXPECTED` says nothing about an erase that had begun, and the runbook's "Every stop below erases nothing" now precedes a paragraph that allows one;
  3. **the failed unit used the same `TTYPath=/dev/tty1`.** If the N150's fault is the installer unit's TTY setup, the failed unit may fail the same way, and the failure stays silent;
  4. the exit code can be 120, not 8 (Python's flush at shutdown); `dmesg -n 1` runs outside `guarded`; an expected stop whose `systemctl poweroff` fails would show the failed unit's "unexpected error" text;
  5. a long traceback plus 20 log lines can scroll the heading off a 25-row screen.
- **Repaired before merge, because nit 3 defeats the task's own outcome** (the next boot must name the cause), with nits 1 and 2 that guard it. Nits 4 and 5, and the verifier's backlog note (`describe()` prints the model and serial raw), go to the backlog.
- **Test changes after the fix commit, and why:**
  - `test_a_failed_installer_starts_the_unit_that_shows_why`: `StandardOutput=tty` and `TTYPath=/dev/<console>` become `StandardOutput=journal+console` and `StandardError=journal+console`, with `TTYPath` and `DefaultDependencies` now required absent. This follows nit 3: `/dev/console` needs no TTY set up for the unit. It also now requires `OnFailure=` to come before `[Service]`, in `[Unit]` (nit 1).
  - `Unexpected.test_the_message_says_what_to_do` also requires "may be partly erased" (nit 2).
  - New: `test_the_kept_error_is_the_one_shown`, `System.record_error` then `read_error` in a temporary folder (nit 1). It passes on the fix, because the code was already right.
- **Red** (against `ac02c47`): `test_installer.py` `Ran 68 tests` `FAILED (failures=3)`: `'StandardOutput=journal+console\n' not found` (tty1 and ttyS0) and `'may be partly erased' not found`.
