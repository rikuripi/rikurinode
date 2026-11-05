# Build Record — the stick keeps Fedora 45's kmscon off the installer's screen

| | |
|---|---|
| **Date** | 2026-11-04 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/installer-kmscon`, from `main` at `a1339e5`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | incident: the fix |

## Incident: root cause

- **Seen** (the previous task, `docs/build-records/2026-11-04-installer-visible-failure.md`): on the N150, the installer unit `Main process exited, code=killed, status=1/HUP`. Something hung up `tty1` as the installer started.
- **The cause** (CI's own boot log of the same Fedora 45 stick: #65's install evidence, `no-console.log`, OS image [run 41767934590](https://github.com/rikuripi/rikurinode/actions/runs/41767934590)). Just before `Starting rikuri-installer.service`, it shows:

  ```
  [  OK  ] Started kmsconvt@tty1.service - KMS System Console on tty1.
  [  OK  ] Reached target getty.target - Login Prompts.
  ```

  Fedora 45 puts kmscon on the screen's console (`kmsconvt@tty1.service`, pulled by `getty.target`) in place of `getty@tty1`. The stick masks `getty@tty1.service` and `autovt@tty1.service` (probe 6d, run 1: a login on the installer's console hangs it up), but not kmscon. kmscon takes `tty1` and hangs up the installer, which then gets SIGHUP.
- **Why CI passed:** CI's stick runs the installer on `ttyS0`, so kmscon on `tty1` hurts nothing there. Fedora 44 had no kmscon. The N150 (`tty1`, Fedora 45) is the only place the two meet.
- **Root cause (class):** a list of names that Fedora no longer uses. The stick's mask list named the 44-era console services; nothing checked what actually starts on the installer's console.

## Task Contract

1. **Outcome:** the installer has the N150's screen to itself on Fedora 45, so the install runs to the disk list and `ERASE`.
2. **Scope:** stage 1, the USB installer (owner, 2026-11-04: "go").
   - `image/installer/Containerfile`: mask `kmsconvt@tty1.service` too, beside `getty@tty1` and `autovt@tty1`.
   - `image/drill/install_test.py`: each case fails if the stick's console log shows a login service started on `tty1` (`kmsconvt@`, `getty@` or `autovt@`). CI's log shows one today, so this check turns red on `main` and green with the fix, in a real boot.
   - Tests: `image/tests/test_installer.py` (the mask list) and `image/tests/test_install_test.py` (the new check).
   - The record close-out of #66 goes first (`2bb1682`).
   - Risk tier: **routine**. It changes only what may use the stick's console, not the erase or the install. The installed node keeps Fedora's kmscon login on its screen.
   - **Not included:** the nits from #65 and #66 (backlog); the N150's reinstall (the owner's, after this merges).
3. **Done when:**
   - the unit tests require the mask and the console check, red first;
   - CI's install test passes all three cases with the new check, which shows in a real boot that no login starts on `tty1`;
   - `Full gate (Ubuntu)` and the OS image workflow pass on the PR;
   - one `verifier` pass has no Important finding.
   - Not in this task: the N150's install (the owner's).
4. **Authority:** the owner's word above; this branch; a draft PR; no merge.
5. **Limits:** one task; two repair cycles; two review rounds; development CI at most 3 runs.

## Evidence log

- **Test changes, and why:**
  - `test_installer.py`, `test_no_logins_and_no_network_on_the_stick`: `kmsconvt@tty1.service` is added to the units that must be masked. The check is stricter; nothing is removed.
  - `test_install_test.py` (additions only):
    - `ScreenLogins`: `screen_logins()` finds `kmsconvt@`, `getty@` and `autovt@tty1.service` started, using CI's real line as the sample, and nothing else (`getty.target`, the installer, logind, kmscon on `tty2`);
    - `TheCases.test_every_case_fails_if_a_login_took_the_screen`: each of the three cases fails, naming `kmsconvt@tty1.service`.
- **Red** (rikuri-drill, `safe-run.sh`, against `main`):
  - `test_installer.py` `Ran 68 tests` `FAILED (failures=1)`: `'kmsconvt@tty1.service' not found in ['getty@tty1.service', 'autovt@tty1.service', …]`.
  - `test_install_test.py` `Ran 32 tests` `FAILED (failures=3, errors=2)`: `no attribute 'screen_logins'` (×2); `Failed not raised` (wrong_number, answered_no); and for erase, `does not match "the disk is empty after the install"`.
