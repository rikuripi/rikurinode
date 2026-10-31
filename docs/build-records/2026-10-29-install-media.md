# Build Record — Stage 1 change 5a: install media, built and installed in CI

| | |
|---|---|
| **Date** | 2026-10-29 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/install-media`, from `main` at `1738748`; the probe on the throwaway branch `probe/installer-iso` (this task's, deleted after); worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | PR #55, merge `daf3d6f`: `c053b48`, `6bfbe66`, `a0f599e`, `ffa9050`, `cfffa95`, `2ee78c1`, `3997799`, `cc25634`, `3cb7e26`, `62f0449`, `6cdaa84`. Repair 2, PR #56, branch `stage1/install-media-repair2`: `f5b22c3`, `0245775`, `cdb88c2`, and the follow-up task's |
| **Status** | IN PROGRESS: repair 2 (owner, 2026-10-31). 5a merged on 2026-10-30, before its verifier pass |
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

## Repair 2: the verifier's findings (owner, 2026-10-31: "Repair 2 in one PR (Recommended)", "Require a number (Recommended)")

5a merged as PR #55 before its verifier pass; the pass then failed on 10 surviving mutants. This is 5a's last repair and last review round.

1. **Outcome:** the installer's tests hold every rule its record claims, and a node can only be set to follow a numbered name.
2. **Scope:** routine in size, high-risk by component.
   - `image/installer/rikuri_install.py`: the tag must hold a number (replaces the list of floating names);
   - `image/tests/`, `image/drill/install_test.py` (its final checks made testable), `scripts/quality/tests/test_workflows.py`;
   - `.github/workflows/image.yml`: CI's test name becomes `install-test-1`, because `install-test` no longer passes;
   - the nits: ADR 0006's sentence, the publish runbook's fourth job, and this record finished (5a's close-out is folded in).
   - **Not included:** 5b; any other installer behaviour.
3. **Done when:** the findings' mutants (I1 to I4) and the harness's checks turn the tests red, with the results recorded; `Full gate (Ubuntu)` and the OS image workflow's install test pass on the PR; the follow-up verifier pass over the corrections has no Important finding. A new Important finding there goes to the owner.
4. **Authority:** the owner's answers above; this branch; a pull request, draft until CI and the verifier pass; no merge. An independent check is required.
5. **Limits:** one repair (the second of two) and one review round (the second of two); development CI's remaining 4 runs.

## Follow-up task: the tag rule's last tests (owner, 2026-10-31: "Small follow-up task (Recommended)")

Verifier pass 2 failed on two new surviving mutants on the changed tag line; 5a's repairs and reviews were used up, so the owner authorized this task.

1. **Outcome:** the tests hold the tag rule's characters and that the number may be anywhere in the tag.
2. **Scope:** routine in size, high-risk by component. `image/tests/test_installer.py`; this record's slips; one sentence of `docs/runbooks/publish-os-image.md`. **Not included:** any change to the installer's code. N5 (valid JSON from `lsblk` that is not an object crashes rather than refuses; it erases nothing, and real `lsblk` does not write it) goes to the backlog.
3. **Done when:** mutants A1 (each form) and A2 turn the tests red, with a passing baseline first; `Full gate (Ubuntu)` and the OS image workflow pass on PR #56; one verifier pass over these lines has no Important finding.
4. **Authority:** the owner's answer above; push this branch, PR #56 stays a draft until then; no merge. An independent check is required.
5. **Limits:** one task; this one verifier pass; two repair cycles; the remaining development CI runs.

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
- [x] **Design** (2026-10-29, after probe 6; the owner's "Yes, resume"):
  - **`image/installer/`:** `Containerfile` (the node's own pinned base, the probe's packages, dracut's `dmsquash-live`), `rikuri_install.py` (the installer and its build-time `configure`, which writes the unit: no `rikuri-installer.service.in` was needed).
  - **Build arguments:** `CONSOLE` (`tty1` for the published stick, the N150's screen; `ttyS0` for CI's install test, the only difference) and `TARGET` (`ghcr.io/rikuripi/rikurinode:<tag>`). `configure` refuses any other value and writes three files:
    - `iso.yaml`: label `RIKURI-NODE`, one entry, `root=live:CDLABEL=RIKURI-NODE rd.live.image selinux=0 rd.emergency=poweroff` plus `console=tty0 quiet` or `console=ttyS0`;
    - the unit, on that console only;
    - `installer.json`: the target, and `console=ttyS0` as the installed node's only karg in CI, none on the stick.
  - **The stick has no logins and no network:** the gettys on tty1 and ttyS0 masked (`getty@`, `autovt@`, `serial-getty@`); `sshd` and NetworkManager masked; greenboot and bootloader-update masked (no use on a live system); the install container runs with `--network=none`.
  - **The installer** (on the console; every refusal erases nothing and ends with "press Enter to power off"):
    1. podman's store goes on `/run`, with the stick's store read-only beside it (method A). There must be exactly one image on the stick, or it stops: the stick is damaged.
    2. The stick is the disk holding `/run/initramfs/live`. If it cannot be found, it stops, because it cannot tell the stick from the target.
    3. The internal disks: `lsblk` whole disks that are not removable, read-only, USB, `zram` or the stick. If there is not exactly one, it stops and names what it found.
    4. It shows that disk's model, size (GB) and serial, and asks: type `ERASE` and press Enter. An exact `ERASE` (surrounding spaces ignored, case kept) goes on; anything else erases nothing.
    5. `podman run --rm --privileged --pid=host --network=none --security-opt label=disable` with `/dev`, both stores, `storage.conf` and `efivars`, then `bootc install to-disk --skip-fetch-check --wipe --filesystem ext4 --target-imgref <TARGET>` on the disk, without `--generic-image`, so the firmware gets the node's entry (probe 6d).
    6. On success: remove the stick; it restarts in 15 s. On failure: say so, and wait for power-off.
  - **`image/drill/install_test.py`** (CI, `sudo`): boots the ISO as a removable USB stick under OVMF, typing at the installer through QEMU's serial socket, with the prompts imported from `rikuri_install.py`:
    1. **two blank disks:** the refusal; Enter powers off; both disks unchanged (no block allocated);
    2. **one disk, `no`:** "Nothing was erased"; the disk unchanged;
    3. **one disk, `ERASE`:** installed; then the disk alone, with the firmware settings the install left: OVMF starts `"Fedora"` and greenboot reaches `greenboot-success.target`. Then, read from the disk, the origin is `ostree-unverified-registry:<TARGET>` and the deployment's `ostree.manifest-digest` is the embedded image's digest.
  - **`image.yml`:** a job `install` (after `changes`, like build and drill) builds the node image and the installer (`CONSOLE=ttyS0`, `TARGET=…:install-test`, `install-test-1` since repair 2) and the ISO with image-builder v87 by digest, then runs the test and keeps its evidence.
  - **`publish.yml`:** a job `iso` after `anonymous`, with a read-only token and no login. It pulls the signed digest anonymously, builds the stick (`CONSOLE=tty1`, `TARGET=<published tag>`), and keeps `rikuri-node-<tag>.iso` and its `.sha256` as the run's artifact (90 days). Not proven in CI: the screen console (5b, on the N150).
  - **Not changed:** the drill keeps `--generic-image` (a disk image booted with fresh firmware settings).

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

**5a, development CI on PR #55** (at most 6 runs; repairs at most 2):

| Run | Commit | Result | Learnt |
|---|---|---|---|
| OS image [40988971165](https://github.com/rikuripi/rikurinode/actions/runs/40988971165) (#83); CI and the guard workflow passed | `cc25634` | **Fail**, all three cases, though the installer said the right words in each: two disks `no 'This machine has more than one internal ' on the console within 900 s`; no `the VM did not end within 180 s`; erase `Installation complete!`, then `the VM did not end within 120 s` | The harness, not the installer: it drained the console socket only while waiting for words, so the socket filled while it waited for the VM to end, and both shutdowns stop mid-line. QEMU's chardev log repeated characters (`interrnal`, `Boott0000`), so the refusal never matched. |

**Repair 1** (of 2): a red commit `62f0449`, then the fix. The console's reader drains the socket all the time and writes the log itself; QEMU's `logfile=` is gone. In rikuri-drill, red: the guest's write `TimeoutError: timed out`, and `FileNotFoundError` for the log. Green: 15 harness tests, 334 image tests.
Test changes after the red commit, with reasons:
- the chardev test now asserts no `logfile=`, where it asserted one: the test writes the log;
- `stick_argv` loses its unused `log` argument, so its test's call drops it.

**Run 2 of 6:** on `6cdaa84`, [CI](https://github.com/rikuripi/rikurinode/actions/runs/41006542621) (`Full gate (Ubuntu)`), [OS image](https://github.com/rikuripi/rikurinode/actions/runs/41006542638) and the guard workflow (41006542744) all pass. The install test, artifact `install-evidence`:
- two disks: refused, both named, `/dev/vda` and `/dev/vdb`; both disks unwritten;
- `no`: `Nothing was erased.`; the disk unwritten;
- `ERASE`: installed; the disk alone starts `"Fedora" from HD(…`, reaches `greenboot-success`; read from the disk, the origin is `ostree-unverified-registry:ghcr.io/rikuripi/rikurinode:install-test` and the digest `sha256:6a564de0…fe30`;
- none of the repeats seen in run 83 (`interrnal`, `Boott`, `trimmm`, `Netwoork`) in any log. That `grep` is what was checked; it is not a proof of every character.

**Earlier evidence, recorded here late** (verifier's nits):
- The red run of `2ee78c1` was not recorded: it was red by construction, `rikuri_install` did not exist yet.
- `3997799` changed two tests after that red commit: `Run.refused` asserted no install at all, which contradicted its own failed-install case, so it now takes the number expected; and `LoadConf` gained two names the length of the repository's, because the hand mutant that dropped the repository check survived the shorter ones.
- Hand mutants before merge: 22 of 22 red.

**Repair 2** (of 2; contract above). A red commit, then the fix:
- Red in rikuri-drill: `test_a_tag_without_a_number_floats`, the workflow test of CI's name, and four tests of `check_disk`, which did not exist yet. The other new tests passed at once: they hold rules that were right but unheld.
- Test changes after a red commit, with reasons: `TARGET` and the workflow test follow the new number rule; the digest test only gets stricter; two tests added (`answered_no` with a written disk, `erase` needing a written disk), and the helper `written_disk` drawn out of `test_a_disk_written_fails`, which asserts the same.
- Green in rikuri-drill: 41 installer, 26 harness and 26 workflow tests; 352 image tests.
- **Hand mutants: 53 of 53 red**, against a baseline of 67 passing: the 21 earlier ones still apply (the 22nd, the list of floating names, went with the list), and 32 new ones, among them I1, I2 (a tag without a number, the first character, the length, a target not a string), I3, I4 (each error dropped from each of the two catches), `--pid=host`, `label=disable`, `TTYVHangup`, `TTYReset`, and each of the harness's checks.
- Not unit-tested, and proven by CI's run alone: `Test.alone` (the firmware's entry and greenboot on the disk alone) and the mounting in `read_disk`.

## Verify

**Pass 1** (`verifier`, over merged `1738748..6cdaa84`, after the owner's merge): **FAIL.** The installer's safety held: no way found to erase without the exact `ERASE`, to pick the stick or a USB or removable disk, to choose among disks, or to name another repository. It failed on 10 surviving mutants in validation and refusal checks:
- **I1:** the repository check without its colon.
- **I2:** `stable` and `lts`, the first character and the length of a tag; and tags with no number accepted.
- **I3:** a disk with no size.
- **I4:** four error paths that would crash instead of refusing and powering off.

Nits: the harness's own checks untested; this record unfinished; ADR 0006's "any answer" overstated; the reasons for `3997799` only in its commit; **publish.yml's job `iso` has never run, so it is Not yet proven** (the first publish after this merge, 5b's first step, is what proves it).
Repair 2 answers each of them but that last, which only a publish can.

**Pass 2** (over the corrections, `daf3d6f..cdb88c2`): **FAIL.** Pass 1's findings are all corrected: each named mutant is red, 53 of 53 re-run, no test loosened, the number rule breaks no user of a target. Two new mutants survive on the changed line, Important by REVIEW.md's letter, neither touching the disk or the answer:
- **A1:** the tag's characters not held to ASCII (`\w` accepted `é1` and `1é`).
- **A2:** the number anywhere not held (`[0-9]$` passed).

Per AGENTS.md §5 this went to the owner, not a third round. Its nits: the record's "43 installer" (41 ran, corrected above); the publish runbook's re-run sentence; the record's slips, corrected above. Noted, not changed: the code comment cites AGENTS.md's rule, which asks for major.minor or a digest, while `44`, `v1` and `_1` pass, as the owner's "Require a number" chose.

**The follow-up task's evidence:** the new cases pass on the unchanged code, so no red commit: they hold a rule already right, and the mutants are the proof. In rikuri-drill, baseline 67 passing (`image/tests`, all pass with `.github` copied); **hand mutants 58 of 58 red**: the 53 above, A1 in three forms (both classes, the first, the rest), A2 as "ends in a digit" and "starts with a digit". Test changes: cases added only.

**Pass 3:** to come, over the follow-up task's lines only.

## Close Out

**Probe 6d DONE** (2026-10-29): the stick installs offline, and the installed node boots alone and passes its health checks. 5a resumes at its Design when the owner says go; its limits stand, with the probe's runs counted separately as the follow-up task's.

Earlier, **BLOCKED** (2026-10-29): probe 6d did not pass within the probe's limits, so the design, tests and implementation were not started. No pull request. The probe branch `probe/installer-iso` is kept, unmerged, as the evidence and the starting point for the next task; this task deletes it when the owner says so.

Proposed next task (not started): probe 6d alone, at most 3 CI runs. Put podman's own store on a tmpfs (`graphroot` under `/run`) and read the embedded image as an `additionalimagestores` entry. Only a store's upper layer must not sit on overlayfs; lower layers may. The alternative is `fuse-overlayfs` as the `mount_program`. Then prove that the installed disk boots alone, with SELinux enforcing and greenboot passing.
