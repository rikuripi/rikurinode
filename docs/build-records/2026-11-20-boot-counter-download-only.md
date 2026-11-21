# Build Record — no boot counter for an update staged download-only (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-20 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-counter-download-only`, from `main` at `b66bd8b`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `e5bb7b7` (contract), `f49aa52` (red tests), `13b57cc` (fix), `a327822` (record) (#145); this close-out |
| **Status** | DONE |
| **Change type** | defect fix (OS image: when greenboot's counter is armed; the VM drill) |

## Intent: the owner's words

- "Next" (2026-11-20), after the N1 fix's close-out (#144), whose Next was this fix.
- Asked which check refuses it (ostree's own trace, bootc's `downloadOnly` field, or both): **"ostree's own trace"**.

## The defect

- The N1 fix (`docs/build-records/2026-11-20-boot-counter-armed-after-finalize.md`, its verifier's minor finding 1): `arm` sets `boot_counter=3 boot_success=0` when `ostree-finalize-staged.service` stopped with `Result=success`.
- An update staged with `bootc switch --download-only` or `bootc upgrade --download-only` (bootc 1.17.1, the image's) is locked for finalization. greenboot 0.16.4 still sets its trigger for it (it reads the staged deployment, locked or not). ostree 2026.4's finalize then logs "Not finalizing; deployment is locked for finalization" and returns success without applying it. So `arm` sets the counter for an update never applied, and the node's unchanged image is counted: N1 again.
- Nothing in the repository stages that way today. It must be closed before the control plane stages updates.
- To reproduce: stage an update download-only, reboot, hold `greenboot-healthcheck` before the node's pre-check, and read `boot_counter`: 2 today; it must be unset.

## What exists (read in source, as data; nothing run)

- ostree `v2026.4`, `src/libostree/ostree-sysroot-deploy.c`, `_ostree_sysroot_finalize_impl_staged_deployment`:
  - locked when the staged state's `locked` key is true (bootc's `--download-only`) **or** `/run/ostree/staged-deployment-locked` exists;
  - locked: "Not finalizing; …" and `return TRUE`;
  - otherwise it unlinks `/run/ostree/staged-deployment` **before** writing the deployment ("Unlink the staged state now"), then "Finalized deployment".
  - The file is written only by staging, `ostree_sysroot_deployment_set_kargs_in_place` and `ostree_sysroot_change_finalization` (the lock toggle), none run at shutdown (the last added at the close-out, from the verifier's Minor 2).
- bootc `v1.17.1`, `crates/lib/src/status.rs`: `download_only = deployment.is_staged() && deployment.is_finalization_locked()`. That is the `locked` key alone, and misses the lock file.
- greenboot-rs `v0.16.4`, `src/lib/handler.rs`: the trigger names the staged deployment from `bootc status`, with no check of its lock.

## Design

- **ostree's own trace** (the owner's choice). A finalize that applies the update first removes `/run/ostree/staged-deployment`; a locked one leaves it.
  - `note` notes the update only when that file is there, a regular file reached by `lstat`.
  - `arm` arms only when, besides the checks it makes now, that file is gone: `lstat` fails with `ENOENT`. Any other error is unknown, and nothing is armed.
- **Fails closed.** The path is ostree's own, not a public interface. If ostree ever moves it, `note` finds nothing and notes nothing, and greenboot counts as it did before the rule. It never arms for an update not applied.
- **Rejected:** bootc's `downloadOnly` field, which misses the lock file. Both together add a check that ostree's trace already covers.

## Task Contract

1. **Outcome:** an update staged download-only never leaves greenboot's counter running against the image the node kept.
2. **Scope:** high-risk (the rollback path; BUILD-PROCEDURE, "Risk tiers").
   - `image/rootfs/usr/libexec/rikuri/greenboot-unapplied-update` (`note` and `arm`) and `image/tests/test_greenboot_unapplied_update.py`.
   - `image/drill/vm_drill.py` and `image/tests/test_vm_drill.py`: a new case 2d stages an update with `bootc switch --download-only`, reboots, reads `boot_counter` held before the pre-check, and requires it unset, with the update never applied.
   - Plan §4.1's dated clarification and D22's row, if they name when the counter is armed.
   - **Not included:** the give-back (N2), the other minor findings of the N1 fix, the record line the pre-check appends for a download-only update (the control plane, not built yet, decides what to do with it), any control plane change.
3. **Done when:**
   - Red: the new tests committed first and seen failing in CI (the unit tests, and the drill's case 2d with `boot_counter` set at the first boot).
   - The fix in its own commit; the full gate passes in CI; the image workflow's VM drill passes, with case 2d showing no counter at the first boot and none left, and cases 1, 1b, 2b and 3 as before.
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** the files above and this record. On the Mac: `ast` parse checks and `git diff --check`. The Python tests and the drill run in CI only (`safe-run.sh` cannot run on this Mac). Reading ostree's, bootc's and greenboot's source on GitHub (done; data, nothing run). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Red tests, `f49aa52`

- `test_greenboot_unapplied_update.py`: a helper makes ostree's staged state under the test's folder (a regular file; gone; a folder; a link; unreadable, `ENOTDIR`).
  - `Note` passes it, as a file, to every case. New: the path is ostree's (`test_the_staged_state_is_ostree_s`), and nothing is noted when it is gone, a folder, a link or unreadable.
  - `Arm` passes it, gone, to every case. New: nothing is armed while ostree kept the staged state (file, folder or link), or when it is unreadable.
  - **Reason for the change to the existing cases:** `note` and `arm` now read a path, and each case says what is there: staged before finalize and gone after, as ostree leaves it when it applies the update. Their expectations are unchanged.
- `vm_drill.py`, `test_vm_drill.py`: case 2d, between 2b and 3. It stages image `a` with `bootc switch --download-only`, requires `bootc status` to say `downloadOnly` (else the drill fails), holds greenboot's check at the next boot, reads `boot_counter`, and requires `never_applied` as cases 2b and 3 do. `staged_download_only` is unit-tested. The check's name is added to `EXPECTED`, and `drill.case2d()` to the order `main` keeps. **Reason:** a new case; nothing loosened.

### CI on `f49aa52` (red): Fail, as expected

- `Full gate (Ubuntu)`, [run 44850813932](https://github.com/rikuripi/rikurinode/actions/runs/44850813932): `FAILED (errors=35)`. 34 `TypeError: note()/arm() got an unexpected keyword argument 'staged_state'`, and `AttributeError: module 'greenboot_unapplied_update' has no attribute 'STAGED_STATE'`. No failure elsewhere.
- The OS image, [run 44850813997](https://github.com/rikuripi/rikurinode/actions/runs/44850813997): built and checked, and the USB install passed. The VM drill failed on case 2d alone, with the other 47 checks Pass:
  - `case 2d, an update downloaded only | **Fail** | on the installed image: True, after one more reboot: True; 'never applied' logged: True; trigger cleared: True; no boot counter at its first boot: False (2); no boot counter left: True; a new record line: True`
  - The defect, reproduced on the real image: greenboot set its trigger for the locked update, finalize returned success, and `arm` set the counter for an update never applied.

### Fix, `13b57cc`

- `greenboot-unapplied-update`:
  - `STAGED_STATE`, ostree's path, and `ostree_staged` (`lstat`: a regular file is "staged", `ENOENT` is "gone", anything else is unknown).
  - `note` notes only when it is "staged".
  - `arm`, after `finalized`, arms only when it is "gone".
  - The docstring says so.
- **Clarified against the Design:** the helper is `ostree_staged`, and the keyword is `staged_state`, as the red tests name it.
- Plan §4.1 (two places) and D22's row: dated clarifications.
- On the Mac: every changed Python file parses; `git diff --check` clean. The tests run in CI.

### CI on `a327822`: Pass

- `Full gate (Ubuntu)`, [run 44860615708](https://github.com/rikuripi/rikurinode/actions/runs/44860615708): success; `Ran 683 tests … OK`.
- The OS image, [run 44860615691](https://github.com/rikuripi/rikurinode/actions/runs/44860615691): all four jobs passed; the VM drill's 48 checks Pass, among them:
  - `case 2d, an update downloaded only | Pass | … no boot counter at its first boot: True (None); no boot counter left: True; …`
  - case 1 rolled back; case 1b `['2', '2', '1']`; cases 2b and 3 with no counter at the first boot.
- The owner merged #145.

### Verifier, `a327822`: PASS (round 1)

- Red-to-green: the red commit's 35 errors are the cases the fix makes pass; `git diff f49aa52 a327822 -- image/tests image/drill` is empty; every reason given; the scope holds.
- Read in ostree `v2026.4`'s source: a locked finalize returns before it removes the staged state; any failure after the removal fails the unit. The check fails closed if the path moves (nothing noted) or ostree stops removing it (nothing armed). `/run/ostree` is the same tmpfs in every unit's mount namespace; `note` runs before finalize and `arm` after.
- **Hand mutations: Not yet proven by running**; worked through by reading. 17 mutants plus 2 variants:
  - All caught by named tests, three of them by the drill alone: the two default paths (case 2d, case 1b) and case 2d staged without `--download-only` (its precondition).
  - Two survivors: the staged-state check moved before `finalized` (equivalent: every refusal returns 0 with no write, and the one write follows every check), and the log text's two branches swapped (a log line only).
- **Important: none.** Minor:
  1. **A cancelled staged update.** ostree also removes the staged state when a staged deployment is cancelled (`ostree-sysroot-deploy.c`, the write of deployments without it), and finalize then returns success with nothing to do. A cancel between `note` and finalize, at the end of a shutdown, would arm the counter for an update not applied. The plan's wording ("removed only when finalize applies") was corrected at the close-out; the gap is for the backlog.
  2. The list of writers of the staged state missed the lock toggle: corrected above. The result is unaffected.
  3. The log message's branches have no test (a log line only).

## Outcome

- **DONE.** An update staged download-only no longer sets greenboot's counter against the image the node kept: shown on the real image by the drill's case 2d, red then green, with cases 1, 1b, 2b and 3 as before.
- **Backlog, not started:** Minor 1, a staged update cancelled during the shutdown. A candidate check: `note` also records the staged deployment's checksum, and `arm` requires the booted-next deployment to be it.
