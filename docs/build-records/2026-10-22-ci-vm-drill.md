# Build Record — Stage 1, changes 3 and 4: the OS image booted in a VM in CI, and the rollback drill

| | |
|---|---|
| **Date** | 2026-10-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/ci-vm-drill`, from `main` at `7c135cf`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS (resumed 2026-10-22 after `docs/build-records/2026-10-22-greenboot-218.md`); development runs used: 6 of 10 (runs 3 and 4 on that task's branch; run 5 the red run; run 6 after repair 1) |
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

- [x] Red: the harness's unit tests committed failing: `16dc883`.
- [x] Green: the harness and the job `91cd832`; the post-mortem and non-UTF-8 fix `a55191f`.
- [x] **Security question:** CI gains a job that runs a VM as root on the runner, with the workflow's read-only token (`permissions: contents: read`); the VM has no secrets and no outbound network (`restrict=on`, one loopback forward).

## 3. Debug

- N/A (a feature; the red run stands for the regression guard).

## 4. Verify

- [x] Development runs and the final run: 5 of 10 used; all Pass in run 4 and in pull request #29's check at `922cee4` (run 39726227170).
- [x] The red run: run 5, Fail as required (Evidence log).
- [ ] Independent verification: first pass **FAIL** on two Important findings. **I1:** case 3 waited for "Finalize Staged" anywhere in the serial log, which earlier cases had already written, so the wait ended at once and the cut was timed by a fixed 5 s sleep (the design the Spec rejected); its log line "finalize's stop seen" was unsupported; the outcome was honest (a pass needs "was never applied" and an unchanged image) but a slow runner could have failed it falsely. **I2:** reading `bootc status` accepted a missing digest, so "still on the installed image" could pass as `None == None`. Nits: the red run's ending misquoted; case 3's "recorded" satisfied by case 2b's line; a failed boot-id read let a reboot be skipped; a falsy-wait mutant; the probe step's stale name; the QEMU/OVMF pinning question to be put to the owner. Repair cycle 1 of two: red `61521a9` (4 tests failing, the falsy-wait guard passing), fix `934ec62` (120 image tests OK; mutants: offset ignored and the validation removed caught; `.get()` on the digest and kept colour codes equivalent, the escape stripping removed as dead code). Run 6, [39729386483](https://github.com/rikuripi/rikurinode/actions/runs/39729386483) on `934ec62`: **all Pass**; case 3: "the rollback trigger stopped in this shutdown (serial console); finalize is held; cutting the power"; the serial log ends `Stopped … Greenboot Rollback trigger`, `Stopping ostree-finalize-staged…`, `Job ostree-finalize-staged.service/stop running (3s / 5min 1s)`, and holds no "Finalized deployment"; each case's record check now needs a new line ("a new record line: True"). Follow-up pass: pending.

## 5. Close Out

- [ ] Gate; pull request; the stage 1 record's change list updated.

- Resumed 2026-10-22. On `stage1/greenboot-218` (this task's commits plus the #218 fix): run 3 [39713948238](https://github.com/rikuripi/rikurinode/actions/runs/39713948238) (case 1 Pass; case 2b Fail on a read-only `/boot`), run 4 [39724262070](https://github.com/rikuripi/rikurinode/actions/runs/39724262070) (**all Pass**: first boot, cases 1, 2b, 3; case 3 cut after "finalize's stop seen on the serial console"); and as a check of pull request #29 at `922cee4`, [39726227170](https://github.com/rikuripi/rikurinode/actions/runs/39726227170) (pass, 6 m 51 s).
- **Red run**, run 5, [39727276986](https://github.com/rikuripi/rikurinode/actions/runs/39727276986), on the throwaway branch `red/drill-without-unapplied-check` at `318f2be` (from `922cee4`, minus #28's drop-in and minus the drill's `needs: build`; the branch deleted afterwards): the build job's image check **refused** the image ("50-rikuri-unapplied-update.conf: missing, or not a regular file"); the drill **failed**: first boot Fail ("the check ran: False"), case 1 Pass (it does not depend on #28's check), case 2b timed out: greenboot logged "GRUB kernel fallback detected - new deployment failed to boot", rolled the healthy node back into case 1's broken image, which then failed four boots and ended stuck: "Boot counter exhausted but no next-deployment-id set - manual intervention required" (`99-post-mortem.out`; corrected after the verifier: the earlier wording quoted case 1's own, legitimate rollback line). The drill catches the absence of the fix, and the image check catches it first.

## Skipped items — visible, never silent

- (none yet)

## Evidence log

Development runs (cap 10):

1. [39707685031](https://github.com/rikuripi/rikurinode/actions/runs/39707685031), on the harness's first commit: build pass; drill: `bootc install to-disk` worked on the Ubuntu runner; **first boot: PASS** (greenboot passed, the DNS check skipped, the unapplied-update check ran; booted about 20 s after start); case 1 timed out after 1,200 s; collecting the serial log then crashed on a non-UTF-8 byte (a harness bug, fixed next).
2. [39710186883](https://github.com/rikuripi/rikurinode/actions/runs/39710186883): first boot PASS; case 1 **Fail, greenboot-rs #218 on bootc's own layout**. `bootc install to-disk` makes no `/boot` partition (BIOS boot, EFI, root: `00-install.out`); `/boot` is a read-only bind of the root (`/dev/vda3[/boot]`, `findmnt`). At shutdown the trigger unit's `ExecStop=` never ran ("Setting rollback trigger": 0 lines); the broken image failed on four boots, then greenboot logged "Boot counter exhausted but no next-deployment-id set - manual intervention required" and the node stayed on the broken update. Also seen: SELinux denials for `bootupctl` reading `/sysroot/.bootc-aleph.json` on each boot (bootupd; not this task's).

**Stopped for the owner (2026-10-22):** the fix lies in the image, outside this task's Scope.

**Owner's decision (2026-10-22):** "Fix in image first (Recommended)": pause this task; a separate task fixes #218 in the image, red-first with run 2 as its red evidence; then this task resumes.
