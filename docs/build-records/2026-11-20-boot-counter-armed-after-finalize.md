# Build Record — the boot counter armed only once the update is applied (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-20 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-counter-unapplied-clear`, from `main` at `b1f80dc` (#142, merged as `7b3d2c8`); the repair on `stage1/boot-counter-mutants`, from `main` at `7b3d2c8`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `3fcc6d3` (contract), `a36542f` (red tests), `42726ee` (fix), `5fe1dfd` (record); the repair: `c7069cc` (tests), `c33681a` (record) (#143); this close-out |
| **Status** | DONE |
| **Change type** | defect fix (OS image: where greenboot's counter is armed; the VM drill) |

## Intent: the owner's words

- "Next" (2026-11-20), after the rollback rule's close-out (#141), whose Next was this fix.
- Asked how (clear the counter at the start of boot, arm it only after the update is applied, or accept the risk): **"Arm after it applies"**.

## The defect

- The rollback rule (`docs/build-records/2026-11-20-boot-cause-rollback-rule.md`, its verifier's N1): `greenboot-unapplied-update arm` sets `boot_counter=3 boot_success=0` in greenboot's trigger unit's stop, which runs **before** ostree's finalize applies the staged update.
- When finalize then fails, or the power is cut during it (the drill's cases 2b and 3), the node boots its unchanged image with the counter set. GRUB counts that image's boots down until the node's pre-check in `greenboot-healthcheck` clears the counter with the trigger. If the unchanged image fails to reach that pre-check three boots in a row, GRUB boots the previous deployment: against plan §4.1, "an update that was never applied never rolls the running image back".
- To reproduce: hold `greenboot-healthcheck` before the pre-check at the first boot after a failed finalize, and read `boot_counter`: 2 today (armed 3, one boot counted); it must be unset.

## What exists

- `greenboot-set-rollback-trigger.service` stops before `ostree-finalize-staged.service` (its `After=`), and greenboot's own drop-in from the node adds `ExecStop=-…greenboot-unapplied-update arm` after greenboot's.
- `rikuri-boot-cause.service` already stops **after** finalize (`Before=ostree-finalize-staged.service`, `Conflicts=final.target`): the pattern to follow.
- `ostree-finalize-staged.service` is a oneshot with `RemainAfterExit=yes`, started at boot only when an update is staged; its `ExecStop` applies the update. A failed stop leaves it `failed` with a `Result` other than `success`.

## Design

- **Note before finalize.** The existing step after greenboot's own (renamed `note`) makes the same checks as before (a trigger, a staged digest, the two equal), and writes the digest to `/run/rikuri-boot-counter/staged` instead of arming.
- **Arm after finalize.** A new unit, `rikuri-boot-counter.service`, ordered like `rikuri-boot-cause` (`DefaultDependencies=no`, `Before=final.target ostree-finalize-staged.service`, `Conflicts=final.target`, `PrivateMounts=yes`; on `/boot`'s mount, see the clarification below), stops after finalize. Its `ExecStop=-…greenboot-unapplied-update arm` arms `boot_counter=3 boot_success=0` only when: the note names a digest, the trigger still names it, and `ostree-finalize-staged.service` was started this boot and has stopped successfully (`ActiveState=inactive`, `Result=success`, an inactive time after its active time).
- **Every other state arms nothing**, which is greenboot as it was before the rule: a finalize that failed, a power cut during it (the arm never runs), nothing noted, a note for another digest, anything unreadable. A power cut between finalize and the arm leaves the new image counted from its first failed check, as greenboot counts.
- The pre-check's clear (trigger and counter together) stays, for a counter left by any other path.

## Task Contract

1. **Outcome:** an update that never applied never leaves greenboot's counter running against the image the node kept, so it can never roll that image back.
2. **Scope:** high-risk (the rollback path; BUILD-PROCEDURE, "Risk tiers").
   - `image/rootfs/usr/libexec/rikuri/greenboot-unapplied-update` (`note`, and `arm` after finalize) and its tests.
   - `image/rootfs/usr/lib/systemd/system/greenboot-set-rollback-trigger.service.d/50-rikuri-run-at-shutdown.conf` (`arm` becomes `note`); the new `image/rootfs/usr/lib/systemd/system/rikuri-boot-counter.service` and its `sysinit.target.wants` link; `image/check_image_root.py` and its tests.
   - `image/drill/vm_drill.py` and `image/tests/test_vm_drill.py`: cases 2b and 3 read `boot_counter` at the unchanged image's first boot, held before the pre-check, and require it unset; cases 1 and 1b stay Pass.
   - Plan §4.1's dated clarification and D22's row; `greenboot.conf`'s comment if it names where the counter is armed.
   - **Not included:** the give-back (N2), the mutant nits (N3), the kernel's panic setting, the hardware watchdog, any control plane change.
3. **Done when:**
   - Red: the new and changed tests committed first, seen failing in CI (the unit tests, the image checker's, and the drill's cases 2b and 3 with `boot_counter` set at the first boot).
   - The fix in its own commit; the full gate passes in CI; the image workflow's VM drill passes: cases 2b and 3 with no counter at the first boot and none left, cases 1 and 1b as before (three boots; 2, 2, 1).
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** the files above and this record. On the Mac: `ast` parse checks and `git diff --check`; the Python tests and the drill run in CI only (`safe-run.sh` cannot run on this Mac). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Red tests, `a36542f`

- `test_greenboot_unapplied_update.py`: the old `Arm` class (arm at greenboot's trigger) replaced by `Note` (the staged update noted in `/run`, nothing armed, `/boot` not remounted), `Finalized` (finalize started in this boot and stopped successfully, and 14 states that are not), and `Arm` (armed after finalize, only for the noted update the trigger names; a failed finalize, one that never ran or has not stopped, an unreadable `systemctl`, nothing noted, a malformed note, another trigger: nothing armed). **Reason:** the old `Arm` tests asserted the defect (arming before finalize); each of their cases has its counterpart in `Note` or the new `Arm`, as strict.
- `test_check_image_root.py`: the trigger drop-in test now asks for the `note` line and finds an `arm` line there (stricter); a new class `BootCounter` for the unit, its link and its overrides, the unit a closed world.
- `vm_drill.py`, `test_vm_drill.py`: cases 2b and 3 hold greenboot's check before the node's pre-check at the unchanged image's first boot (`HOLD_FIRST_DROPIN`, `10-` before the node's `50-`, held by the same flag as case 1b) and read `boot_counter`; `never_applied` requires it unset. A test holds the drop-in's name before every shipped drop-in.

### CI on `a36542f` (red): Fail, as expected

- `Full gate (Ubuntu)`, [run 44819244715](https://github.com/rikuripi/rikurinode/actions/runs/44819244715): `FAILED (failures=3, errors=48)`: every `Note`, `Finalized`, new `Arm` and `BootCounter` test errors (`module 'greenboot_unapplied_update' has no attribute 'note'`, `… 'finalized'`, `module 'check_image_root' has no attribute 'check_boot_counter'`); `test_trigger_dropin_must_note_the_staged_update` fails, its cases "armed before finalize (N1)" and "armed there as well" included.
- The OS image, [run 44819244785](https://github.com/rikuripi/rikurinode/actions/runs/44819244785): the image built and checked, the USB install passed; the VM drill failed on exactly the two new conditions, the defect reproduced on the real image:
  - `case 2b, finalize fails | **Fail** | … no boot counter at its first boot: False (2); no boot counter left: True; …`
  - `case 3, a power cut during the update | **Fail** | … no boot counter at its first boot: False (3); no boot counter left: True; …`
  - Case 3 reads 3, not 2: GRUB did not count that boot down after the power cut. Not this task's question; the counter is set at all, which is the defect.

### Fix, `42726ee`

- `greenboot-unapplied-update`: `note` (the old `arm`'s checks, writing the digest to `/run/rikuri-boot-counter/staged`); `finalized` (`systemctl show`'s four keys, each once: `inactive`, `success`, started in this boot and stopped after); `arm` (the note read strictly, the trigger still naming it, `finalized`, then `boot_counter=3 boot_success=0` with `/boot` remounted around the write). The modes `note` and `arm`.
- The trigger's drop-in calls `note`; the new `rikuri-boot-counter.service` (`ExecStart=/usr/bin/true`, `ExecStop=-… arm`) and its `sysinit.target.wants` link; `check_image_root.py`'s `check_boot_counter`, and the drop-in check finds an `arm` there.
- Plan §4.1 and D22's row: dated clarifications.
- **Clarified against the Design:** the unit is ordered `After=local-fs.target boot.mount`, not `RequiresMountsFor=/boot`. A `Requires=` on `/boot` could pull in the EFI partition's generated mount, the failure the image masks `boot.automount` for (bootc #2402); an order alone stops the unit before `/boot` is unmounted without starting anything. **Test change, with its reason:** `BootCounter.test_the_unit_is_a_closed_world`'s case for `/boot` now removes `boot.mount` from `After=`, and a new case finds `RequiresMountsFor=/boot` (stricter).
- On the Mac: every changed Python file parses; `git diff --check` clean. The tests run in CI.

### CI on `5fe1dfd`: Pass

- `Full gate (Ubuntu)`, [run 44823160006](https://github.com/rikuripi/rikurinode/actions/runs/44823160006): `Ran 677 tests … OK`, all 11 steps passed.
- The OS image, [run 44823159989](https://github.com/rikuripi/rikurinode/actions/runs/44823159989): built and checked, the USB install passed, and the VM drill passed:
  - `case 1, a failing update | Pass | rolled back: True; marker intact: True`
  - `case 1b, power cuts in a new image's trial | Pass | … boot_counter at each held boot: ['2', '2', '1']; given back: [[1, 2]]; …`
  - `case 2b, finalize fails | Pass | … no boot counter at its first boot: True (None); no boot counter left: True; …`
  - `case 3, a power cut during the update | Pass | … no boot counter at its first boot: True (None); no boot counter left: True; …`
  - cases 4 and 5 Pass.
- The owner merged #142 as `7b3d2c8` (2026-11-20, 22:00 UTC) while the verifier was running.

### Verifier, `5fe1dfd`: FAIL (round 1)

- Gate, red-to-green and drill evidence: Pass. The red checks are untouched by the fix, every test change has its reason, and the scope holds.
- At the real entry point, the drill's journal shows `noted update …` and, after finalize, `armed boot_counter=3 for update … applied`. The serial console shows `Stopped ostree-finalize-staged` before `Stopping rikuri-boot-counter`, and `/boot` unmounted after both.
- Its questions:
  - nothing on a path this node uses arms the counter for an update not applied;
  - the stop order is right, since `Before=` reverses at stop and `After=boot.mount` holds `/boot`;
  - `systemctl show` answers at that point, over PID 1's private socket.
- **Hand mutations: Not yet proven by running**; worked through by reading. 25 mutants: 21 caught (the CI drill catches the `__main__` dispatch and the drill's own checks), 4 survivors, none equivalent.
- **Important** (REVIEW.md: a surviving mutant in a high-risk refusal or validation check). None can be reached on a node today:
  1. (I1) `finalized`'s refusal of a key given twice: `Result=exit-code` then `Result=success` would pass.
  2. (I2) `finalized`'s refusal of a key not asked for.
  3. (I3) `arm`'s refusal of a note without its newline: `NEW+"x"` would arm.
  4. (I4) `check_boot_counter`'s refusal of a `sysinit.target.wants` folder that is a link.
- **Minor**, for the backlog:
  1. A staged deployment locked for download only: ostree's finalize then exits 0 without applying it, and `arm` would set the counter (N1 again). `note` should refuse a `downloadOnly` staged deployment. Nothing here stages that way today; this must be settled before the control plane stages updates.
  2. Applied updates left with no counter, as greenboot counted before the rule: finalize applying and then failing a later step; an `isolate` to a target outside `sysinit.target`; a failed `systemctl show` or grubenv write (logged).
  3. The drill's `counter_held_first` reads an unreadable grubenv as "unset".
  4. `__main__`'s dispatch has no unit test; the drill covers it.

### Repair 1 of 2 (the owner: "Repair PR from main")

- `test_greenboot_unapplied_update.py`, `Finalized.test_anything_else_is_not`: two cases, "a key twice, its last value passing" (I1) and "a key not asked for" (I2). `Arm.test_a_note_not_a_digest_arms_nothing`: the note `NEW + "x"` (I3).
- `test_check_image_root.py`, `BootCounter.test_a_linked_wants_folder`: the folder replaced by a link to a copy of itself (I4).
- **Reason for each test change:** each adds a case for a refusal the merged code already makes, so a mutant of that refusal no longer survives (stricter; nothing loosened). The round-2 pass found I2's mutant equivalent (below); its case stays, as a valid refusal. No code changes. These are not a red commit: the defect is the missing test, not the code.
- On the Mac: both test files parse; `git diff --check` clean. The tests run in CI.

### CI on `c33681a`: Pass

- `Full gate (Ubuntu)`, [run 44846126056](https://github.com/rikuripi/rikurinode/actions/runs/44846126056): `Ran 678 tests … OK` (677 and `test_a_linked_wants_folder`; the new subtests sit in methods that passed).
- The OS image, [run 44846125959](https://github.com/rikuripi/rikurinode/actions/runs/44846125959): all four jobs passed; the drill's cases 1, 1b, 2b, 3, 4 and 5 Pass.
- The owner merged #143.

### Verifier, the corrections only: PASS (round 2)

- Scope: only the two test files and this record; nothing loosened, every reason given.
- **By reading, not run:** I1, I3 and I4 are now killed by the new cases. I2 is an **equivalent** mutant: an unknown key still fails the later check that all four keys are present, so no input tells it apart (round 1's "none equivalent" corrected). No untested refusal is left.
- No new Important finding.

## Outcome

- **DONE.** An update ostree did not apply no longer sets greenboot's counter against the image the node keeps: shown on the real image by the drill's cases 2b and 3 (no counter at the first boot), with cases 1 and 1b still rolled back after three boots.
- **Backlog, not started:** a staged deployment locked for download only (finalize exits 0 without applying it, and `arm` would set the counter) must be refused by `note` before the control plane stages updates; round 1's other minor findings (2 to 4) above.
