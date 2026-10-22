# Build Record — Stage 1: an update that was never applied never rolls the node back (D22 against greenboot-rs #219)

| | |
|---|---|
| **Date** | 2026-10-22 (local; the session started 2026-10-21) |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/d22-unapplied-update`, stacked on `stage1/greenboot-drill-parallels` (pushed, no pull request yet), in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
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

- [ ] Red: the decision's unit tests committed failing.
- [ ] Green: the check and the drop-in; the checker; the wording.
- [ ] **Security question:** the check runs as root at boot and writes `grubenv`; it takes no input from the network or a user, runs no shell, and calls `rpm-ostree` and `grub2-editenv` by absolute path with fixed arguments.

## 3. Debug

- [x] **Reproduced before fixing:** the experiment's cases 2b and 3 (Fail), `docs/build-records/evidence/2026-10-21-greenboot-drill-parallels/07-case2b-*.out` and `08-case3b-run.out`.
- [ ] Failing test seen failing: (red commit hash).
- [x] **Root cause, as a class:** a rollback trigger armed before the change it guards is applied, and read later without checking that the change happened. greenboot compares digests only, so "never applied" looks like "failed to boot".
- [ ] Swept for siblings: (other places that arm before acting: the plan's boot-cause record and ADR 0014's "attempts recorded before acting" carry the same need, a record of completion; noted for their tasks).

## 4. Verify

- [ ] Unit tests and the checker's tests.
- [ ] The VM proof (cases 1, 2b, 3).
- [ ] Independent verification.

## 5. Close Out

- [ ] Gate; review; commit; push and pull request on the owner's word.

## Skipped items — visible, never silent

- Staging the update again after "not applied" (D22): waits for the control plane; this change leaves `/var/lib/rikuri/update-not-applied` for it.
- Remove this check when greenboot fixes #219 upstream; the experiment's cases 2b and 3 are the test that shows it.

## Evidence log
