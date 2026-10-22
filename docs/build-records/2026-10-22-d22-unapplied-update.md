# Build Record — Stage 1: an update that was never applied never rolls the node back (D22 against greenboot-rs #219)

| | |
|---|---|
| **Date** | 2026-10-22 (local; the session started 2026-10-21) |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/d22-unapplied-update`, stacked on `stage1/greenboot-drill-parallels` (pushed, no pull request yet), in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `6ca7817` (red), `cb1eb4a` (the check and drop-in), `502b79b` (checker red), `dd4e556` (checker, wording), `171bc97` (repair 1 red), `c611d6b` (repair 1), and the commit that adds this record and its evidence |
| **Status** | Built and verified (verifier FAIL, repaired in cycle 1, follow-up PASS); COMPLETE; pushed and opened as pull request #28 on the owner's word (2026-10-22, "Commit and push, open PR"); CI `Full gate (Ubuntu)` pass (1 m 51 s, run 39706630221) and `Build and check the OS image` pass (57 s, run 39706630307); merged by the owner as `7c135cf` (2026-10-22T01:38:16Z) |
| **Change type** | fix (stage 1, the rollback path; before change 4) |

## Task Contract

1. **Outcome:** a node whose update failed to apply, by a failed finalize or a power cut at the wrong moment, stays on its healthy image instead of being rolled back to the release before, and says why.
2. **Scope:** `image/` only, plus the documents this change directly affects. A check run before greenboot's health check (`image/rootfs/usr/libexec/rikuri/greenboot-unapplied-update`, Python 3, standard library) and the drop-in that runs it (`image/rootfs/usr/lib/systemd/system/greenboot-healthcheck.service.d/50-rikuri-unapplied-update.conf`); `image/check_image_root.py` asserts both; unit tests in `image/tests/`; plan §4.1's and `greenboot.conf`'s "three boots" wording corrected to what was observed. Risk tier: **high-risk** (the rollback path). **Not included:** staging the update again (D22's "staged again once" needs the control plane, which does not exist yet; this change leaves a record for it); the rest of the boot-cause record; UPS support; #217, #218 and #220; CI (option C, its own task); x86_64 and the N150 (CI builds the image for x86_64 on the pull request; booting it there is change 3).
3. **Done when:**
   - unit tests of the decision cover every case of the table below, are committed failing first (red), then pass;
   - the image checker fails without either new file and passes with both (its own tests, red first for the new assertions);
   - in `rikuri-drill`, on the node's image rebuilt with this change: case 1 of the experiment (a failing update) still rolls back by itself, case 2b (finalize fails) no longer rolls the healthy node back, and case 3 (a power cut after the trigger armed, before the deployment was written) no longer does, if the timing can be hit; the journal shows the check's reason each time;
   - `scripts/quality/full-gate.sh` passes, or, on this Mac where `safe-run.sh` refuses, the image tests and the documentation checks pass and CI's full gate and the OS image workflow pass on the pull request;
   - one `verifier` pass has no Important finding.
4. **Authority:** edit the files in Scope and this record and its evidence; build and boot images in `rikuri-drill` as in the experiment (the owner's decisions of 2026-10-21: the VM, its key, passwordless `sudo` in it, `prlctl`, the session's sandbox off, the DNS gap accepted); commit on this branch; push and pull request on the owner's word ("You can start Next.", 2026-10-21, authorizes the task, not the push). Independent check required.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 4 hours of wall time. Fix-lock not engaged (opt-in, AGENTS.md §6); the experiment's record is the red run for the behaviour, and the unit tests get their own red commit.

## 0. Intent

- [x] **Problem, in the owner's words:** "You can start Next." (2026-10-21), the Next of the experiment: "A stage 1 task to implement D22's rule against #219 in the image."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** the OS image's boot path; every future node.
- [x] **Open questions:** none blocking. Whether greenboot upstream fixes #219 is watched; this change is removed when it does (Skipped items).
- [x] **Owner approved the intent:** the message above.

## 0b. Spec

- [x] **Requirements (plan §4.1, D22):** "An update that was never applied, for any cause …, never rolls the running image back"; "After the new image has booted and until its checks pass, … a failed check counts against it"; "An unknown cause counts against the update"; "The record informs greenboot and never replaces its boot counter".
- [x] **Design:** before greenboot's health check runs, read `greenboot_next_deployment_id` from `grubenv` and the deployments from `rpm-ostree status --json` (index 0 is the default; one is marked booted). Decide:

  | State at boot | Meaning | Action |
  |---|---|---|
  | no `greenboot_next_deployment_id` | no update in flight | nothing |
  | booted image's digest equals it | the new image booted and is on trial (experiment case 1) | nothing: greenboot counts and may roll back |
  | booted deployment is not the default | GRUB fell back: the new image failed to boot | nothing: greenboot rolls back |
  | booted deployment is the default, and its digest differs | the update was never applied (cases 2b and 3) | unset `greenboot_next_deployment_id`; log the reason; record it in `/var/lib/rikuri/update-not-applied` |
  | anything unreadable or ambiguous (no booted deployment, no digest, a command failing) | unknown | nothing: greenboot's behaviour, which counts it against the update |
  | the trigger is the booted deployment's ostree checksum | greenboot armed it in its rpm-ostree mode (the booted system was not a container image) and the update is on trial | nothing (added in repair 1) |
  | the trigger is not of the form `sha256:<64 lowercase hex>` | a form the check cannot compare | nothing: unknown (added in repair 1) |

  The drop-in runs it as `ExecStartPre=-…`, so a crash of the check leaves greenboot's own behaviour. Rejected: ordering the trigger after finalize (a power cut between the two would leave an applied update unarmed: "manual intervention required", worse than a wrong rollback); comparing digests with every deployment (fooled when the staged image equals an existing non-booted one, verifier nit of the experiment); patching greenboot (its source is upstream's; a fix there is the long-term answer).
- [x] **Policy applied:** roll back software, never data (unchanged: only the trigger is cleared); nothing important fails silently (the reason is logged and recorded); D21's ban on spawning processes binds the control plane, not this boot-time check, which calls two fixed commands with fixed arguments and no shell.
- [x] **Flagged concerns:** the check reads `grubenv` before greenboot does, in the same boot: `ExecStartPre` guarantees the order. SELinux must let the check write `grubenv` and `/var/lib/rikuri`: proven in the VM or not at all.

## 1. Plan

- [x] **One sentence:** clear greenboot's rollback trigger at boot when the update it names was never applied.
- [x] **Blast radius:** the image's boot path; greenboot's decision in one case only; nothing irreversible (the change is a file in the image, undone by the next image).
- [x] **Current behaviour characterized:** `docs/build-records/2026-10-21-greenboot-drill-parallels.md`, cases 1, 2b and 3 (Pass, Fail, Fail).
- [x] **Files and order:** this record; failing unit tests (red commit); the check and the drop-in; the checker's assertions with failing tests first; the wording; the VM proof; the gate's parts that run here; the verifier.
- [x] **Risks:** clearing the trigger when the new image is on trial would disable rollback for a broken update (case 1 must stay Pass); SELinux denies the write (then the check logs and greenboot behaves as before: no harm, no fix); `rpm-ostree status --json` changes shape (the check then decides "unknown"). Riskiest: the first.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] Red: the decision's unit tests committed failing: `6ca7817` (`FileNotFoundError` on the missing check).
- [x] Green: the check and the drop-in, `cb1eb4a` (77 image tests OK); the checker's red tests `502b79b` (5 new tests, 8 cases failing, 54 passing), green `dd4e556`; the wording in the same commit.
- [x] **Security question:** the check runs as root at boot and writes `grubenv`; it takes no input from the network or a user, runs no shell, and calls `rpm-ostree` and `grub2-editenv` by absolute path with fixed arguments.

## 3. Debug

- [x] **Reproduced before fixing:** the experiment's cases 2b and 3 (Fail), `docs/build-records/evidence/2026-10-21-greenboot-drill-parallels/07-case2b-*.out` and `08-case3b-run.out`.
- [x] Failing test seen failing: `6ca7817` (the check) and `502b79b` (the checker); the behaviour's red run is the experiment.
- [x] **Root cause, as a class:** a rollback trigger armed before the change it guards is applied, and read later without checking that the change happened. greenboot compares digests only, so "never applied" looks like "failed to boot".
- [x] Swept for siblings: other places that arm before acting are the plan's boot-cause record and ADR 0014's "attempts recorded before acting"; both carry the same need, a record of completion, noted here for their tasks. ADR 0006 line 35 says "three failed boots" too (Skipped items).

## 4. Verify

- [x] Unit tests and the checker's tests: `image/tests` 82 OK. Mutants, each caught: the on-trial check removed (2 failures), the fallback check removed (1), two booted deployments accepted (1), a failed unset reported as success (1); in the checker, any section or prefix accepted (2), the executable bit ignored (1).
- [x] The VM proof, in `rikuri-drill` on the node's image rebuilt from `dd4e556` (`:fix`, arm64 base `sha256:d862d94f…`, 44.20261021.0; `bootc container lint` 14 passed; `check_image_root.py` on the built root: 0 findings), SELinux enforcing:

  | Case | Before (experiment) | Now | Evidence |
  |---|---|---|---|
  | First boot of `:fix` | | check: "on trial; greenboot decides"; health check passed | `02-booted-fix.out` |
  | 1, a failing update | Pass | **Pass**: four boots of `:fix-broken`, the check "on trial" on each; greenboot rolled back to `:fix`; `/var` marker intact | `03-case1.out` |
  | 2b, finalize fails | Fail (downgraded) | **Pass**: "was never applied … booted unchanged", trigger cleared, record written (`var_lib_t`); no rollback; still `:fix` after one more reboot | `04-case2b.out` |
  | 3, power cut 1.6 s into the reboot | Fail (downgraded) | **Pass**: "was never applied", cleared; health check passed; still `:fix` after one more reboot; the record holds two lines; 0 AVC denials | `05-case3.out` |
- [x] Independent verification: first pass **FAIL** on two Important findings. **I1:** greenboot 0.16.4 (`src/lib/handler.rs`) arms the trigger with the staged ostree `checksum` when `status.booted.image` is null; the check compared image digests only, so after an *applied* update in that mode it would clear the trigger and a broken update would never roll back. **I2:** the "a command failing" row had no test that a mutant could fail (two survivors). Repair cycle 1 of two: red `171bc97` (the I1 tests failing, 6 cases; the I2 tests guarding), fix `c611d6b` (86 image tests OK; mutants caught: digest form not required 5, uppercase accepted 1, both rc checks 1 each, the checksum on-trial branch 1 after its test also asserted the reason, a change to that test made after the red commit and recorded here). The VM proof re-run on `:fix2` built from `c611d6b` (the check's SHA-256 `1cb2a2d6…` equal on the Mac and in the VM; checker 0 findings): case 1 **Pass** (four boots, "on trial" each, rolled back to `:fix2`), case 2b **Pass** ("was never applied", cleared, still `:fix2` after one more reboot); `06-repair1-build.out`, `07-repair1-case1.out`, `08-repair1-case2b.out`. Case 3 was not repeated: its path in the check is the one case 2b runs. Follow-up pass **PASS** (corrections only): every trigger form greenboot 0.16.4 writes (bootc digest, rpm-ostree checksum, none) is compared correctly or left alone; I2's mutants killed; the test change after the red commit confirmed a tightening.

## 5. Close Out

- [x] Gate: CI on #28: `Full gate (Ubuntu)` pass, run 39706630221; the OS image build and check (x86_64) pass, run 39706630307. Locally, `full-gate.sh` stops at step 1 on this Mac (`shellcheck 0.11.0 required, found 'none'`). Its steps run by hand: 2 guard wiring, policy, tests: exit 0; 3 image tests: OK; 3 quality tools' tests: `FAILED (failures=15)`, the same 15 on `origin/main` without this change (Linux-only `safe_run` and guard-wiring placeholder tests); 4 hygiene: exit 0; 6 whitespace, tracked and working tree: exit 0. Not run here: 1, 5 (shell lint), 7 (secret scan), 8 to 10 (Rust). CI's full gate and the OS image workflow on the pull request are the reference.
- [x] Review, commit, push and pull request #28 on the owner's word; merged by the owner as `7c135cf`.

## Skipped items — visible, never silent

- Staging the update again after "not applied" (D22): waits for the control plane; this change leaves `/var/lib/rikuri/update-not-applied` for it.
- Running the tests writes `__pycache__/` next to the check (`SourceFileLoader`); git ignores it, but a *local* `podman build` of `image/` copies it into the image (`:fix2` carried one, never loaded). CI builds without running the tests, so its images are clean. Backlog: stop the tests writing bytecode, or have the checker flag `__pycache__`. Deleted locally after the runs.
- The rpm-ostree mode (a booted system that is not a container image) is covered by unit tests only; the VM ran container images throughout.
- Backlog nits from the verifier: the check does not remount a read-only `/boot` (the unset then fails and is logged: #219 stays, the safe direction); the unit sets no `TimeoutStartSec` of its own; registry-transport digests unproven; a broken update whose rollback left greenboot's variables uncleared would be recorded as "not applied", which the control plane must not re-stage on that basis alone; the checker misses a later drop-in that empties `ExecStartPre=` and an empty executable file.
- ADR 0006 (line 35, "three failed boots return the previous image") has the same wording as the plan did; an accepted ADR changes only by a dated clarification, the owner's call.
- Remove this check when greenboot fixes #219 upstream; the experiment's cases 2b and 3 are the test that shows it.

## Evidence log

- `docs/build-records/evidence/2026-10-22-d22-unapplied-update/`: `01-build-fix.out` (the repository commit, the `image/` files' SHA-256 on the Mac and in the VM, the build, the check of the built root), `02` to `05` (the cases); `06` to `08` (repair 1: the rebuild of `:fix2` and cases 1 and 2b on it).
