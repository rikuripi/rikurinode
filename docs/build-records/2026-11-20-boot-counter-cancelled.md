# Build Record — no boot counter for a staged update cancelled during the shutdown (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-20 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-counter-cancelled`, from `main` at `d738182`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | this contract; the red tests; the fix; the record |
| **Status** | IN PROGRESS |
| **Change type** | defect fix (OS image: when greenboot's counter is armed; its unit's order; the VM drill) |

## Intent: the owner's words

- "Next" (2026-11-20), after the download-only fix's close-out (#146), whose Next was this gap.
- Asked how (check the deployment; accept the risk with a rule; check the bootloader entry): **"Check the deployment"**.

## The defect

- The download-only fix's verifier, Minor 1 (`docs/build-records/2026-11-20-boot-counter-download-only.md`): `arm` reads "applied" from ostree's staged state being gone after a successful finalize. A cancel of the staged update also removes it, and finalize then has nothing to do and succeeds. So an update cancelled after `note` and before finalize gets the counter set against the image the node keeps: N1 again.
- **The window is real.** greenboot's trigger unit, where `note` runs, has `DefaultDependencies=no` and is ordered only `After=ostree-finalize-staged.service rpm-ostreed.service`. `ostree-finalize-staged.service` is `Before=basic.target`, so it stops only once every ordinary service has stopped. Between the two, services can still be stopping and an admin's command can still run: `ostree admin undeploy`, `rpm-ostree cleanup -p`, or `bootc rollback`.
- Nothing on the node does that today. The control plane will stage updates, so it must be closed first.
- To reproduce: stage an update, and cancel it in that window (`ostree admin undeploy 0`, after `note`). Reboot, hold `greenboot-healthcheck` before the node's pre-check, and read `boot_counter`: 2 today; it must be unset.

## What exists (read in source, as data; nothing run)

- ostree `v2026.4`, `src/libostree/ostree-sysroot-deploy.c`, `_ostree_sysroot_write_deployments_internal`:
  - a new deployment list whose first entry is not the staged deployment drops it (`removed_staged`);
  - dropping it unlinks `/run/ostree/staged-deployment`, then calls `_ostree_sysroot_rmrf_deployment` and removes the lock file.
  - `src/ostree/ot-admin-builtin-undeploy.c`: `ostree admin undeploy 0` removes index 0 of the list, the staged deployment, and writes the rest.
- ostree `v2026.4`, `src/libostree/ostree-sysroot-cleanup.c`, `_ostree_sysroot_rmrf_deployment` removes, in this order:
  1. the backing folder;
  2. the deployment's `.origin` file;
  3. the deployment's folder, `ostree/deploy/<stateroot>/deploy/<checksum>.<serial>` (`ostree_sysroot_get_deployment_dirpath`).
- The origin file is written when the update is staged (`ostree_sysroot_stage_tree_with_options`) and again when finalize applies it (`sysroot_finalize_deployment`). A deployment ostree applied keeps both.
- bootc `v1.17.1`, `crates/lib/src/status.rs`: each entry of `bootc status --json` carries `ostree: {stateroot, checksum, deploySerial}`, from the deployment itself.

## Design

- **Check the deployment** (the owner's choice).
  - `note` records the staged update's deployment alongside its digest. That is `status.staged.ostree` from `bootc status --json`, checked strictly (a stateroot name, a 64-hex checksum, a serial), written as `<digest> ostree/deploy/<stateroot>/deploy/<checksum>.<serial>`.
  - `arm`, besides its checks today, requires that deployment to exist under `/sysroot`: its folder a folder and its `.origin` a regular file, each by `lstat`.
  - A cancel removes the origin before the folder, so a cancel cut short still arms nothing. Anything unreadable or malformed arms nothing.
- **Order.** `arm` now reads `/sysroot`. `rikuri-boot-counter.service` gains `sysroot.mount` in `After=`, as it has `boot.mount`: an order alone, which starts nothing.
- **Fails closed.** No `ostree` entry in bootc's status, or a stateroot or checksum not of the expected form: nothing is noted. A path ostree no longer uses: nothing is armed. greenboot then counts as it did before the rule.
- **Rejected:** a recorded rule with no code (the owner chose the check), and reading the bootloader's entries (more parsing on the rollback path, for the same answer).

## Task Contract

1. **Outcome:** a staged update cancelled during the shutdown never leaves greenboot's counter running against the image the node kept.
2. **Scope:** high-risk (the rollback path; BUILD-PROCEDURE, "Risk tiers").
   - `image/rootfs/usr/libexec/rikuri/greenboot-unapplied-update` (`note`, `arm`) and `image/tests/test_greenboot_unapplied_update.py`.
   - `image/rootfs/usr/lib/systemd/system/rikuri-boot-counter.service` (`After=`), with `image/check_image_root.py`'s closed world for it and `image/tests/test_check_image_root.py`.
   - `image/drill/vm_drill.py` and `image/tests/test_vm_drill.py`: a new case 2e.
     - It stages image `a` and adds a drop-in to greenboot's trigger unit, in `/run` so that it lasts this boot only. The drop-in's `ExecStop` runs `ostree admin undeploy 0` after the node's `note`.
     - It reboots, reads `boot_counter` with greenboot held before the pre-check, and requires `never_applied` as cases 2b, 2d and 3 do.
   - Plan §4.1's dated clarifications and D22's row.
   - **Not included:** the give-back (N2), the earlier minor findings, the control plane, and the log message's untested branches.
3. **Done when:**
   - Red: the new and changed tests committed first and seen failing in CI. That covers the unit tests, the image checker's tests, and the drill's case 2e with `boot_counter` set at the first boot.
   - The fix in its own commit.
   - The full gate passes in CI.
   - The VM drill passes: case 2e with no counter at the first boot and none left, and cases 1, 1b, 2b, 2d and 3 as before.
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** the files above and this record. On the Mac: `ast` parse checks and `git diff --check`. The Python tests and the drill run in CI only (`safe-run.sh` cannot run on this Mac). Reading ostree's, bootc's and greenboot's source on GitHub (done; data, nothing run). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log
