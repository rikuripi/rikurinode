# Build Record — the boot counter armed only once the update is applied (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-20 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-counter-unapplied-clear`, from `main` at `b1f80dc`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | this contract; then the red tests, the fix and the record |
| **Status** | IN PROGRESS |
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
- **Arm after finalize.** A new unit, `rikuri-boot-counter.service`, ordered like `rikuri-boot-cause` (`DefaultDependencies=no`, `Before=final.target ostree-finalize-staged.service`, `Conflicts=final.target`, `RequiresMountsFor=/boot`, `PrivateMounts=yes`), stops after finalize. Its `ExecStop=-…greenboot-unapplied-update arm` arms `boot_counter=3 boot_success=0` only when: the note names a digest, the trigger still names it, and `ostree-finalize-staged.service` was started this boot and has stopped successfully (`ActiveState=inactive`, `Result=success`, an inactive time after its active time).
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
