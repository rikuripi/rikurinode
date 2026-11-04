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
