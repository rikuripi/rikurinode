# Build Record — Stage 1, changes 3 and 4: the OS image booted in a VM in CI, and the rollback drill

| | |
|---|---|
| **Date** | 2026-10-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/ci-vm-drill`, from `main` at `7c135cf`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature (CI; a control change, authorized as its own task) |

## Task Contract

1. **Outcome:** every change to the OS image, and every week, CI boots the node's real x86_64 image in a VM and proves that it comes up healthy, that a broken update rolls back by itself, and that an update never applied (failed, or cut off by a power loss) leaves the node on its healthy image.
2. **Scope:** stage 1 changes 3 and 4 (`docs/build-records/2026-10-12-stage1-os-image.md` §1), in one task by the owner's choice. Files: a `drill` job in `.github/workflows/image.yml` (plus a weekly schedule); the harness `image/drill/vm_drill.py` (Python 3, standard library) and its unit tests in `image/tests/`; the docs this directly affects (the stage 1 record's change list, the workflow's header). Risk tier: **high-risk** (CI is a control; the rollback path). **Not included:** making the job a required check (the owner's choice once stable, stage 1 record); signing and publishing (change 2); install media and the N150 (changes 5 and 6); aarch64; any change to `image/rootfs`, the gate or other workflows.
3. **Done when:**
   - the `drill` job, on this task's pull request, passes on x86_64 with KVM: the first boot is healthy and its journal shows the DNS check skipped (change 3); case 1 (a failing update) rolls back by itself with a `/var` marker intact; case 2b (finalize fails) and case 3 (a power cut after the rollback trigger is armed and before the update is written) leave the node on its healthy image, with the unapplied-update check's reason in the journal (change 4);
   - a **red run** shows the drill fails when the fix of #28 is absent (the image built without `greenboot-unapplied-update`'s drop-in): case 2b or 3 must fail;
   - the harness's unit tests pass in the gate (`image/tests`), and `Full gate (Ubuntu)` passes on the pull request;
   - one `verifier` pass has no Important finding.
4. **Authority:** edit the files in Scope; **push this task's branch repeatedly to run the job in CI** (the harness can only run on an x86_64 KVM runner, which this Mac is not), and push one temporary branch for the red run, deleted after its run is recorded; open the pull request (the owner's "Next" of 2026-10-22, after choosing option C, `bootc install` and all three cases); no merge. CI minutes: each run is estimated at 20 to 30 minutes against D8's 2,000 a month; development runs are counted in the Evidence log. The VM gets no secrets: a key made per run, a user-mode network restricted to the forwarded SSH port. Independent check required.
5. **Limits:** one task; two repair cycles after verification; two review rounds; time budget 6 hours of wall time; development runs of the job capped at 10 (stop and report if exceeded).

## 0. Intent

- [x] **Problem, in the owner's words:** "Ok A, then C." (2026-10-21); "Next" (2026-10-22); the two choices answered 2026-10-22: "bootc install (Recommended)", "Boot + all 3 cases (Recommended)".
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** CI for every image change; no node.
- [x] **Open questions:** whether `bootc install to-disk` runs from an Ubuntu runner without SELinux (first CI run shows); whether the image's sshd starts without being enabled (a kernel argument asks systemd for it).
- [x] **Owner approved the intent:** the messages above.

## 0b. Spec

- [x] **Requirements:** the same cases as `docs/build-records/2026-10-21-greenboot-drill-parallels.md` and `2026-10-22-d22-unapplied-update.md`, on x86_64, automated, with Pass or Fail per case and the evidence kept as a workflow artifact.
- [x] **Design:**
  - Build the image as the `build` job does; install it to a raw disk with the image's own `bootc install to-disk --via-loopback`, adding a per-run SSH key for root and the kernel arguments `console=ttyS0` and `systemd.wants=sshd.service` (test-only, on the drill's disk; the image is unchanged).
  - Boot with `qemu-system-x86_64` and KVM, UEFI firmware (OVMF), a user-mode network with `restrict=on` and one forwarded port (SSH on loopback).
  - Load the image into the VM's container storage once (`podman save` over SSH) and build the test variants inside the VM, as in the experiment.
  - Case 3's power cut is made deterministic: a drop-in in `/run` holds `ostree-finalize-staged`'s stop (`sleep`) after greenboot's trigger has run, and the harness kills QEMU during the hold.
  - Rejected: `bcvk` and `image-builder` (new third-party tools needing the adoption inspection; the owner chose `bootc install`); timing a power cut by sleep alone (the experiment's first attempt missed).
- [x] **Policy applied:** pinning: actions by commit as the workflow tests require; QEMU and OVMF come from the runner's Ubuntu 24.04 archive, as `podman` already does in this workflow, their versions printed in each run's summary (a known gap: the archive's packages move with security updates; owner may overturn); untrusted content: the VM runs only this repository's image; it has no secrets and no outbound network.
- [x] **Flagged concerns:** root SSH by key exists only on the drill's disk, never in the image (D11 unchanged); `StrictHostKeyChecking` is off for the loopback-forwarded VM the job itself just started (its host key is new each run).

## 1. Plan

- [x] **One sentence:** a CI job that installs the image into a KVM VM and runs the first-boot check and cases 1, 2b and 3, failing on any miss.
- [x] **Blast radius:** CI only; no node; minutes against D8.
- [x] **Current behaviour characterized:** `image.yml` builds and checks the image and probes for KVM; no VM boots (stage 1 record, change 1).
- [x] **Files and order:** this record; the harness's pure parts with failing tests first; the harness; the job; development runs; the red run; the verifier; the pull request.
- [x] **Risks:** `bootc install` on a non-SELinux host mislabels files (the first boot would fail: seen in the first run); the runner's disk (the image twice, plus the VM disk); flaky timing (every wait is a bounded poll on a condition, never a bare sleep, except the deliberate power-cut hold). Riskiest: a drill that passes without testing what it claims, hence the red run.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [ ] Red: the harness's unit tests committed failing.
- [ ] Green: the harness and the job.
- [ ] **Security question:** CI gains a job that runs a VM as root on the runner, with a read-only token; the VM has no secrets and no outbound network.

## 3. Debug

- N/A (a feature; the red run stands for the regression guard).

## 4. Verify

- [ ] Development runs and the final run.
- [ ] The red run.
- [ ] Independent verification.

## 5. Close Out

- [ ] Gate; pull request; the stage 1 record's change list updated.

## Skipped items — visible, never silent

- (none yet)

## Evidence log
