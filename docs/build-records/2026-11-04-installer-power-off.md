# Build Record — the installer powers off after an install, instead of restarting

| | |
|---|---|
| **Date** | 2026-11-04 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/installer-power-off`, from `main` at `1c5301f`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `e4f754c` (#64's close-out), `d18591a` (red), `795ca8a` (fix); merged as `f7afa22` (#65) |
| **Status** | DONE |
| **Change type** | feature (the installer's last step) |

## Task Contract

1. **Outcome:** after an install, the machine powers off and says to remove the USB stick and press the power button. It no longer restarts into the stick by mistake, the way the N150 did on 2026-11-03 (#62), and the person needs no firmware setting.
2. **Scope:** stage 1, the USB installer (owner, 2026-11-03: "I'm find with A. The node will likely be headless with access via another computer's browser…"; 2026-11-04: "go").
   - `image/installer/rikuri_install.py`: after a good install, it shows the new `INSTALLED` message, waits 15 seconds so it can be read, then powers off. `System.reboot` goes, since nothing calls it any more. Refusals and a failed install are unchanged: they still wait for Enter, then power off.
   - `image/drill/install_test.py`: the stick's VM loses `-no-reboot`, so only a power-off ends it. A restart would boot the stick again, and the case would fail within its 120 s. The VM of the disk alone keeps `-no-reboot`.
   - Tests: `image/tests/test_installer.py` and `image/tests/test_install_test.py`, changed in the red commit (reasons below).
   - Knowledge layer: `docs/runbooks/install-node.md`, steps 6 to 8 (a new step 8) and the Report line.
   - Risk tier: **routine**. The change comes after the erase and the install, and touches neither, nor anything about disks, keys or the node. An independent check is still required, because it is code.
   - **Not included:**
     - the headless install the owner described (no screen or keyboard, then the node's address in a browser): that is the browser installer in the backlog, and needs ADR 0006's physical-presence proof;
     - local `https://`;
     - the Pi;
     - a publish, and the N150's reinstall (the owner's, after this merges).
3. **Done when:**
   - the unit tests show a good install ending with `sleep 15` then `poweroff`, and never `reboot`;
   - CI's install test passes its erase case with the stick's VM run without `-no-reboot` (the VM ends by itself), and then the disk alone starts the node and greenboot passes, as before;
   - `Full gate (Ubuntu)` and the OS image workflow pass on the PR;
   - one `verifier` pass has no Important finding.
4. **Authority:** the owner's words above; this branch; a draft PR; no merge. The first commit closes out #64's record (owner, 2026-11-04, by accepting the proposal in the report).
5. **Limits:** one task; two repair cycles; two review rounds; development CI at most 3 runs.

## Evidence log

- **#64's close-out** goes first, in its own commit (`e4f754c`).
- **Test changes, and why** (each one follows the owner's new behaviour; none loosens a check):
  - `test_installer.py`, `test_erase_installs_on_the_one_disk_then_restarts` becomes `…_then_powers_off`. Its events change from `["sleep 15", "reboot"]` to `["sleep 15", "poweroff"]`. It now also requires `INSTALLED` to be the last line shown, so nothing after it can hide it.
  - New: `test_the_installed_message_says_what_to_do` (installed; powers off in 15 seconds; remove the USB stick; press the power button), and `test_the_stick_never_restarts_the_machine` (`System` has no `reboot`).
  - `test_install_test.py`, `test_kvm_uefi_and_no_network`: `assertIn("-no-reboot")` becomes `assertNotIn` for the stick's VM. This makes the VM check stricter: with `-no-reboot`, a restart ended the VM just as a power-off did, so the erase case could not tell them apart. New: `test_the_disk_alone_still_ends_at_a_restart`.
- **Red** (rikuri-drill, `safe-run.sh`, against the unchanged code): `test_installer.py` `Ran 52 tests` `FAILED (failures=5)`. The failures: `Lists differ: ['sleep 15', 'reboot'] != ['sleep 15', 'poweroff']`; the message missing "powers off in 15 seconds", "remove the USB stick" and "press the power button"; `System.reboot` present. `test_install_test.py` `Ran 29 tests` `FAILED (failures=1)`: `'-no-reboot' unexpectedly found`.
- **Fix** (its own commit):
  - `rikuri_install.py`: `POWER_OFF_AFTER_S = 15`. After a good install it shows `INSTALLED` ("Rikuri Node is installed. This machine powers off in 15 seconds. Then remove the USB stick and press the power button to start the node."), waits, then calls `poweroff()`. `System.reboot` is removed.
  - `install_test.py`: the stick's VM runs without `-no-reboot`; the docstring and the erase case's comment say why.
  - Runbook `install-node.md`: steps 6 to 8 (wait for the power-off, take the stick out, press the power button; what to do if the stick was left in, or the firmware finds no boot device), and the Report line.
- **Green** (rikuri-drill, `safe-run.sh`): `image/tests` `Ran 373 tests` `OK`; `.claude/hooks` `Ran 91 tests` `OK`; `scripts/quality/tests` `Ran 156 tests`, with the same 7 `git` errors as before, since rikuri-drill has no `git` (Not yet proven locally; CI's gate). `git diff --check`: clean. No test changed after the red commit.
- **Hand mutants: 11 of 11 red** (`test_install*.py`): a restart again; no wait; a wait of 0; a wait for Enter; no power-off; the old message; no "press the power button"; a line shown after `INSTALLED`; `-no-reboot` back on the stick's VM; `-no-reboot` gone from the disk alone's VM; `System.reboot` back.
- **Not yet proven:** that the stick's VM, run without `-no-reboot`, ends by itself after the erase case in CI, and that the N150 powers off (the owner's reinstall, after a publish).

## Close-out

- **CI on `795ca8a`:** [Full gate](https://github.com/rikuripi/rikurinode/actions/runs/41767934591) passed. [OS image](https://github.com/rikuripi/rikurinode/actions/runs/41767934590): all four jobs passed. The install test: `case wrong number: pass`, `case no: pass`, `case erase: pass`, with the stick's VM run without `-no-reboot`. Its erase console shows the new `INSTALLED` line, "[  OK  ] Stopped rikuri-installer.service" and "reboot: Power down". That was 1 CI run of the 3 allowed.
- **Verifier, one pass** (on `795ca8a`): no Important finding. NOT YET PROVEN until CI, then PASS when CI passed. It reran red (`Ran 81 tests` `FAILED (failures=6)` on `d18591a`) and green (`Ran 373 tests` `OK`). It tried 12 mutants of its own: 6 were killed and 6 survived, all Minor. Nits, for the backlog:
  - N-1: nothing checks that `INSTALLED` is shown before the 15 s wait rather than after it (the unit fake keeps `said` and `events` apart);
  - N-2: the unit test looks for the literal `-no-reboot`, so `-action reboot=shutdown` (the same flag) or `-no-shutdown` passes it; CI would time out on the second;
  - N-3: the comment "a restart would boot the stick again" may not hold in the VM (bootupd's "Fedora" entry), but the case still fails;
  - N-4: the Scope named steps 6 and 7; corrected above.
- **Merged** by the owner as `f7afa22` (#65, 2026-11-04T03:44:24Z). This close-out lands with the next task's PR (`docs/build-records/2026-11-04-installer-visible-failure.md`).
- **After the merge:** the stick published from `f7afa22` failed on the N150 before its first line, which is the next task's incident. The power-off itself has not yet been seen on the N150.
