# Build Record — Stage 1 change 5a: install media, built and installed in CI

| | |
|---|---|
| **Date** | 2026-10-29 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/install-media`, from `main` at `1738748`; the probe on the throwaway branch `probe/installer-iso` (this task's, deleted after); worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | Probe 6d DONE; 5a's design, tests and code wait for the owner's go-ahead |
| **Change type** | feature (the node's install path) |

## Task Contract

1. **Outcome:** CI builds a USB installer for the node from its OS image and proves, in a VM, that it asks once, erases only after that answer, installs the node offline, and that the installed node boots alone and passes its health checks, set to update from `ghcr.io/rikuripi/rikurinode` under a fixed name.
2. **Scope:** stage 1 change 5, first of three steps (owner, 2026-10-29: "5a: media in CI first (Recommended)"; 5b the install on the N150, by the owner; 5c the first-boot setup page).
   - **The installer environment**, `image/installer/`: a Containerfile for a live system (image-builder's `generic-iso` contract: dracut's `dmsquash-live`, the ISO tools, `iso.yaml`), and the install unit and script. The script, on the console:
     - finds the target: exactly one internal disk (not removable, not the boot medium); zero or several → it says so, erases nothing, and waits for power-off;
     - shows that disk's model, size and serial, and erases it only when the owner types `ERASE` and presses Enter; any other answer erases nothing;
     - runs `bootc install to-disk` from the image carried on the stick (`containers-storage:`), with the target name `ghcr.io/rikuripi/rikurinode:<fixed tag>`, then says to remove the stick and restarts.
   - **The ISO**, built by `image-builder` (`ghcr.io/osbuild/image-builder-cli:v87.0.0` by digest), with the node image embedded (`--bootc-installer-payload-ref`).
   - **CI:** a job in `image.yml` builds the ISO from the image under test and runs the install test (below); `publish.yml` builds it from the published, signed digest and keeps it as the run's artifact with its SHA-256, for 5b. Harness `image/drill/install_test.py`, tests in `image/tests/`, workflow tests in `scripts/quality/tests/test_workflows.py`.
   - **Docs:** a runbook for 5b (`docs/runbooks/install-node.md`: write the stick, install on the N150), the stage 1 record's change list, ADR 0006's install-media point (a dated clarification), README's status line.
   - Risk tier: **high-risk** (it erases a disk; it is the node's first trusted image).
   - **Owner choices** (2026-10-29, AskUserQuestion): "Ask once, then erase (Recommended)"; "USB installer with the image inside (Recommended)"; the N150 is ready, so 5b's owner steps are written in this task.
   - **Not included:** the install on the N150 (5b, the owner's, after this merges and a publish); the setup page and sign-in (5c, with the control plane); the bound container images (ADR 0006; none exist yet); Secure Boot enrolment beyond what Fedora's shim gives; publishing the ISO anywhere but the run's artifact; aarch64.
3. **Done when:**
   - **Probe 6** (below) answers its four questions in CI, recorded keep, simplify or drop;
   - tests committed failing first, then pass in `rikuri-drill`; a hand mutant of each new rule (the disk choice, the answer, the target name) turns them red;
   - on the pull request: `Full gate (Ubuntu)` and the image workflow pass, its install test showing:
     - with two disks, the installer refuses and both disks are unchanged;
     - answered `no`, the disk is unchanged;
     - answered `ERASE`, it installs; the installed disk, with the stick removed, boots and greenboot passes; `bootc status` (read from the installed disk, see 0b) names `ghcr.io/rikuripi/rikurinode:<tag>` and the embedded digest;
   - one `verifier` pass has no Important finding.
4. **Authority:**
   - the owner's "Ok next" (2026-10-29) and the choices above;
   - edit the files in Scope; the workflow edits and the new job are this task's, named here;
   - the probe: a temporary workflow on `probe/installer-iso`, pushed and then deleted by this task; no secret; the runner reads `registry.fedoraproject.org`, `ghcr.io` and Fedora's package mirrors;
   - `rikuri-drill` for unit tests; nothing runs on a real disk of this machine or the live node's;
   - push this branch and open the pull request as a **draft** until the verifier and CI pass; no merge;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; the probe at most 5 CI runs and 2 hours; development CI runs at most 6; time budget 6 hours.

## Follow-up task: probe 6d (owner, 2026-10-29: "Yes, start")

1. **Outcome:** know whether the stick can install the node offline, and the installed node boot alone with SELinux enforcing, so 5a can resume.
2. **Scope:** the probe branch `probe/installer-iso` only: its installer Containerfile, install script and workflow. Routine (a throwaway experiment in CI; nothing merges). Not included: 5a's design, tests or code; any change on `main`.
3. **Done when:** a probe run's serial logs show `bootc install to-disk` from the embedded image succeeding, and the installed disk booting alone with greenboot passing, SELinux enforcing, the files labelled, and its origin naming `ghcr.io/rikuripi/rikurinode:probe`. Keep, simplify or drop each storage method tried.
4. **Authority:** push the probe branch; CI on it; no secret; the runner reads `registry.fedoraproject.org`, `ghcr.io` and Fedora's and Ubuntu's package mirrors. No independent check (an experiment; 5a's verifier covers what it becomes).
5. **Limits:** at most 3 CI runs and 90 minutes; then keep, simplify or drop, and stop. Storage methods, tried in order inside one run, each named on the serial console: (A) podman's store on `/run`, with the stick's image as a read-only `additionalimagestores` entry; (C) `fuse-overlayfs` as the `mount_program`; (B) the image copied into memory as an OCI layout, with `--source-imgref`. If 3 runs pass no method, the owner chooses between image-builder v88 and Anaconda.

## 0b. Spec

- [x] **Facts** (2026-10-29):
  - `image-builder`'s docs (`doc/20-advanced/20-bootc/10-isos.md`, osbuild/image-builder `main`): `generic-iso` builds a live ISO from a bootable container; the container must carry a kernel and an initramfs with `dmsquash-live`, shim and grub EFI binaries, and `podman`, `mksquashfs`, `xorriso`, `implantisomd5`, `grub2-mkimage`, `python`; `--bootc-installer-payload-ref` copies a container into the live system's `/var/lib/containers/storage`, for an offline install from `containers-storage:`. `bootc-installer` and `anaconda-iso` are older types ("You should prefer using `generic-iso`"). Licence Apache-2.0. It runs as a privileged container.
  - `ghcr.io/osbuild/image-builder-cli`: versioned tags `v81.0.0` to `v88.0.0`; `v87.0.0` (2026-10-14) is index `sha256:df3f4e525945c868d8014b859cd4f1d2efd8d749e40d8e3b9b9e6a05ca3b95b0`. v88.0.0 (2026-10-27) is under two weeks old.
  - ADR 0006: "Anaconda does not support bound images, so the install path provides them another way … a `bootc install` from a live environment that carries the images". A live ISO running `bootc install to-disk` is that path.
  - The node image's base is `registry.fedoraproject.org/fedora-iot@sha256:29d16f4c…`; whether `dnf` installs packages in a build on it is not known (probe 6a).
- [x] **Probe 6** (CI, `probe/installer-iso`): (a) does `dnf install` of the live and ISO tools work on the pinned Fedora IoT base, or is a pinned `fedora-bootc:44` base needed; (b) does `image-builder` v87 build a `generic-iso` from it with the node image embedded; (c) does the ISO boot in QEMU (UEFI, as a USB stick) to a unit on the serial console; (d) does `bootc install to-disk` from the embedded image succeed, and does the installed disk boot alone and pass greenboot. Keep, simplify or drop.
  - **6a: Pass, keep.** `dnf install dracut-live squashfs-tools xorriso isomd5sum grub2-efi-x64-cdboot python3` works on the pinned IoT base; no second base is needed.
  - **6b: Pass, keep.** v87 builds the ISO with the node image embedded. In v87 the type is `bootc-generic-iso` (`generic-iso` from v88).
  - **6c: Pass, keep, with two rules learnt.** The stick boots under OVMF as `usb-storage` and starts the install unit (`RIKURI-PROBE-READY` on the serial console). (1) v87 copies a grub entry's `linux:` line as written and fills no `${…}` (`pkg/distro/iso_config.go` at `v87.0.0`); the line must spell out `root=live:CDLABEL=<label> rd.live.image`. (2) The squashfs carries no SELinux labels, so the live system needs `selinux=0` (as v87's example); the installed node is unaffected, since `bootc install` labels the target from the image's policy, but this is **not yet proven** (6d not reached).
  - **6d: Fail, not proven.** `podman` in the live system refused its storage: `'overlay' is not supported over overlayfs, a mount_program is required`. The live root is an overlayfs (dmsquash-live), and the embedded image is in `/var/lib/containers/storage` on it.
  - **Stopped** as agreed with the owner (2026-10-29: "Allow 45 more minutes (Recommended)", one more run, then BLOCKED on failure). Used: 4 of 5 runs; about 115 minutes against 120 plus the 45 allowed.
- [x] **Probe 6d** (follow-up task, 3 of 3 runs, about 45 of 90 minutes): **Pass.** Run 3 installed offline from the stick, and the disk booted alone, with the firmware settings the install left, through the entry bootupd registered (`Boot0004 "Fedora" … \EFI\fedora\shimx64.efi`, first in `BootOrder`). greenboot passed (`Finished greenboot-healthcheck.service`, `Reached target greenboot-success.target`), SELinux enforcing (`enforcing=1`), 0 `avc: denied`, files labelled (`/usr/bin/bash` `shell_exec_t`, `/etc/passwd` `passwd_file_t`), origin `ostree-unverified-registry:ghcr.io/rikuripi/rikurinode:probe`. The fresh-settings boot was not needed, so it did not run. Not shown: the listing of the installed disk's EFI partition (the step printed nothing; the boot itself proves the loader is there).
  - **Keep, method A:** podman's store at `/run/containers/storage`, with the stick's `/var/lib/containers/storage` as a read-only `additionalimagestores` entry, and `storage.conf` and both stores mounted into the install container. **Dropped:** C (`fuse-overlayfs`) and B (an OCI copy in memory) were never needed.
  - **Keep, install as on the machine:** no `--generic-image`, with `/sys/firmware/efi/efivars` mounted, so bootupd registers the firmware entry (`efibootmgr --create … --label Fedora`). With `--generic-image` (run 2) the disk alone fell to the UEFI shell. The CI drill keeps `--generic-image`: its disk is an image booted with fresh firmware settings.
  - **Keep, the installer owns its console:** run 1's script output was lost when `serial-getty@ttyS0` started and hung the console up. The real installer masks the getty on the console it uses, and its lines also go to the kernel log.
- [ ] **Design:** next, when the owner says go. Rules from the probe: the stick's kernel line spelled out (`root=live:CDLABEL=<label> rd.live.image selinux=0 rd.emergency=poweroff`); type `bootc-generic-iso` under v87; method A storage; install without `--generic-image`, `--wipe` only after `ERASE`; no getty on the installer's console.

## Evidence log

| Run | Commit | Result | Learnt |
|---|---|---|---|
| [40941949152](https://github.com/rikuripi/rikurinode/actions/runs/40941949152) | `86ebc4c` | 6a pass; 6b fail: `invalid image type: generic-iso` | v87's name is `bootc-generic-iso` |
| [40942926290](https://github.com/rikuripi/rikurinode/actions/runs/40942926290) | `f9153cd` | 6b pass; 6c fail: `Timed out waiting for device … /dev/gpt-auto-root`, emergency shell | no `root=` on the kernel line: v87 fills no `${…}` |
| [40959595876](https://github.com/rikuripi/rikurinode/actions/runs/40959595876) | `9ddfb63` | 6c fail: the live root mounted, then `Failed to allocate manager object: Permission denied` | unlabeled squashfs under enforcing SELinux |
| [40967675517](https://github.com/rikuripi/rikurinode/actions/runs/40967675517) | `214a0ef` | 6c pass (`RIKURI-PROBE-READY`); 6d fail: `'overlay' is not supported over overlayfs, a mount_program is required`, rc 125 | podman's storage cannot sit on the live overlayfs root |

| 6d [40970729268](https://github.com/rikuripi/rikurinode/actions/runs/40970729268) | `81c3397` | A, C and B ran; the disk stayed blank; every line after about 17 s lost | `serial-getty@ttyS0` hung the console up |
| 6d [40975514330](https://github.com/rikuripi/rikurinode/actions/runs/40975514330) | `9a62f55` | A installed (`Installation complete!`); the disk alone fell to `Shell>` | `--generic-image` writes no firmware entry |
| 6d [40979140488](https://github.com/rikuripi/rikurinode/actions/runs/40979140488) | `82de360` | **pass:** installed (A, with firmware entry); booted alone, greenboot passed, SELinux enforcing | (above) |

Serial logs: each run's artifact `probe6`.

## Verify

## Close Out

**Probe 6d DONE** (2026-10-29): the stick installs offline, and the installed node boots alone and passes its health checks. 5a resumes at its Design when the owner says go; its limits stand, with the probe's runs counted separately as the follow-up task's.

Earlier, **BLOCKED** (2026-10-29): probe 6d did not pass within the probe's limits, so the design, tests and implementation were not started. No pull request. The probe branch `probe/installer-iso` is kept, unmerged, as the evidence and the starting point for the next task; this task deletes it when the owner says so.

Proposed next task (not started): probe 6d alone, at most 3 CI runs. Put podman's own store on a tmpfs (`graphroot` under `/run`) and read the embedded image as an `additionalimagestores` entry. Only a store's upper layer must not sit on overlayfs; lower layers may. The alternative is `fuse-overlayfs` as the `mount_program`. Then prove that the installed disk boots alone, with SELinux enforcing and greenboot passing.
