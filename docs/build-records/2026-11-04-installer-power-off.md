# Build Record — the installer powers off after an install, instead of restarting

| | |
|---|---|
| **Date** | 2026-11-04 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/installer-power-off`, from `main` at `1c5301f`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature (the installer's last step) |

## Task Contract

1. **Outcome:** after an install, the machine powers off and says to remove the USB stick and press the power button. It no longer restarts into the stick by mistake, the way the N150 did on 2026-11-03 (#62), and the person needs no firmware setting.
2. **Scope:** stage 1, the USB installer (owner, 2026-11-03: "I'm find with A. The node will likely be headless with access via another computer's browser…"; 2026-11-04: "go").
   - `image/installer/rikuri_install.py`: after a good install, it shows the new `INSTALLED` message, waits 15 seconds so it can be read, then powers off. `System.reboot` goes, since nothing calls it any more. Refusals and a failed install are unchanged: they still wait for Enter, then power off.
   - `image/drill/install_test.py`: the stick's VM loses `-no-reboot`, so only a power-off ends it. A restart would boot the stick again, and the case would fail within its 120 s. The VM of the disk alone keeps `-no-reboot`.
   - Tests: `image/tests/test_installer.py` and `image/tests/test_install_test.py`, changed in the red commit (reasons below).
   - Knowledge layer: `docs/runbooks/install-node.md`, steps 6 and 7 and the Report line.
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
