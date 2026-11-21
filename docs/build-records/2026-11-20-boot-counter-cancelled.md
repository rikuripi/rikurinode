# Build Record — no boot counter for a staged update cancelled during the shutdown (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-20 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-counter-cancelled`, from `main` at `d738182`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `4aa8baf` (contract), `ce82d34` (red tests), `d4fd066` (the red tests' fixture), `b4c4d3f` (fix), `494329d` (repair 1), and this record |
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

### Red tests, `ce82d34`

- `test_greenboot_unapplied_update.py`:
  - `bootc()` carries the staged update's `ostree` entry, and `DEPLOY` is its path.
  - A new class, `StagedDeployment`: `SYSROOT`, the path read, and 26 malformed cases that give none (21 entries, 5 texts).
  - `Note`: the note now holds the digest and the deployment. A new test: no deployment in bootc's status notes nothing.
  - `Arm`: `make_deployment` makes the sysroot, with the deployment applied by default. The malformed-note cases gain 10 for the deployment's half. A new test: a cancelled update arms nothing (gone; the origin removed, a cancel cut short; the folder gone; a link or a folder where a file goes; unreadable).
  - **Reasons:**
    - The happy note's expectation changes from `NEW + "\n"` to `NEW + " " + DEPLOY + "\n"`, because the note now carries the deployment; `NEW + "\n"` joins the malformed notes, stricter.
    - Every `Arm` case is given the applied deployment, as ostree leaves it once it applies the update; their expectations are unchanged.
    - `bootc()`'s new `ostree` entry is ignored by every other reader.
- `test_check_image_root.py`, `BootCounter.test_the_unit_is_a_closed_world`: the `After=` cases name the new line, `local-fs.target boot.mount sysroot.mount`. A new case removes `sysroot.mount`. **Reason:** the unit's `After=` changes, and the old cases are kept for it; nothing loosened.
- `vm_drill.py`, `test_vm_drill.py`: case 2e, between 2d and 3, added to `EXPECTED` and to the order `main` keeps.
  - It stages image `a`, writes `CANCEL_DROPIN` (in `/run`, so for one boot only), which adds `ExecStop=/usr/bin/ostree admin undeploy 0` to greenboot's trigger unit after the node's `note`.
  - It reboots, holds greenboot's check, reads `boot_counter`, and requires `never_applied`.
  - A test holds the drop-in's name after every shipped drop-in of that unit. **Reason:** a new case.

### CI on `ce82d34` (red): Fail, as expected, and one fault of the red tests

- `Full gate (Ubuntu)`, [run 44864604066](https://github.com/rikuripi/rikurinode/actions/runs/44864604066): `FAILED (failures=6, errors=67)`.
  - Expected:
    - `AttributeError: module 'greenboot_unapplied_update' has no attribute 'staged_deployment'` (27) and `… 'SYSROOT'` (1);
    - `TypeError: arm() got an unexpected keyword argument` (21);
    - the note's format (`'sha2[62 chars]aaaaa\n' != 'sha2[62 chars]aaaaa ostree/deploy/default/deploy/ddddddddddd[53 chars].0\n'`, and twice `… is not None` for a status with no deployment);
    - the closed world (`'After=local-fs.target boot.mount sysroot.mount\n' not found in …`, three cases).
  - **Not expected, a fault of the red tests:** `FileExistsError: [Errno 17] File exists: '/tmp/…/sysroot/ostree/deploy/default/deploy/dddd….0'` (18). `test_a_note_not_a_digest_arms_nothing`'s subtests clear only `run/`, and `make_deployment` made the deployment's folder a second time.
- The OS image, [run 44864604079](https://github.com/rikuripi/rikurinode/actions/runs/44864604079): built and checked, and the USB install passed. The VM drill failed on case 2e alone, with the other 48 checks Pass:
  - `case 2e, an update cancelled during the shutdown | **Fail** | on the installed image: True, after one more reboot: True; 'never applied' logged: True; trigger cleared: True; no boot counter at its first boot: False (2); no boot counter left: True; a new record line: True`
  - The defect, reproduced on the real image: the cancel ran (the node stayed on its image), and `arm` set the counter for it.

### The red tests' fixture, `d4fd066`

- `make_deployment` removes the sysroot it made before, so each call is fresh.
- **Reason:** the fault above, in the fixture and not in what the tests assert; no expectation changes.
- In its own commit, before the fix, so the fix commit touches no test.

### Fix, `b4c4d3f`

- `greenboot-unapplied-update`:
  - `SYSROOT`, `STATEROOT`, `CHECKSUM` and `DEPLOYMENT`;
  - `staged_deployment` (bootc's `staged.ostree`, each field checked: a stateroot name, 64 lowercase hex, an `int`, not a `bool`, of at least 0);
  - `deployment_kept` (`lstat`: a folder and a regular `.origin`; any error is False);
  - `note` notes nothing without a deployment, and writes `<digest> <deployment>`;
  - `arm` reads the note as exactly those two parts, and after the staged-state check arms only when `deployment_kept`;
  - the docstring says so.
- `rikuri-boot-counter.service`: `After=local-fs.target boot.mount sysroot.mount`, with its comment. `check_image_root.py`: the same in `BOOT_COUNTER_KEYS`.
- Plan §4.1 (two places) and D22's row: dated clarifications.
- On the Mac: every changed Python file parses; `git diff --check` clean. The tests run in CI.

### CI on `f8cd845`: Fail (repair 1 of 2)

- `Full gate (Ubuntu)`, [run 44866156166](https://github.com/rikuripi/rikurinode/actions/runs/44866156166): `FAILED (errors=18)`, every one `AttributeError: 'str' object has no attribute 'fullmatch'` at `CHECKSUM.fullmatch(checksum)` in `staged_deployment`.
- The OS image, [run 44866156154](https://github.com/rikuripi/rikurinode/actions/runs/44866156154): the VM drill failed two checks, with 47 Pass:
  - `the new image counted from its first boot | **Fail** | three boots of the broken image, then the rollback: ['update-applied', 'clean', 'clean', 'clean', 'rolled-back']`
  - `case 1b, power cuts in a new image's trial | **Fail** | rolled back; boot_counter at each held boot: [None, None, None]; given back: []; …`
- **Cause:** the fix's new pattern `CHECKSUM` was bound again six lines on by the script's `CHECKSUM = "checksum"`, the key the boot-time check reads. So `note` raised for every staged update. Its `ExecStop=-` ignored the failure, and nothing was noted. Applied updates then got no counter, and greenboot counted as it does alone (four boots).
- That failed closed: no counter for the image the node keeps. But the rule was lost for applied updates, as the drill shows.

### Repair 1, `494329d`

- The pattern renamed `OSTREE_CHECKSUM`; nothing else changed.
- Checked on the Mac by parsing the script (`ast`): no other top-level name is bound twice.
- No test changed.
