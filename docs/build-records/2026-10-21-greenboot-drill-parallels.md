# Build Record — Experiment: does the stock rollback work for the node's image? (greenboot drill in Parallels)

| | |
|---|---|
| **Date** | 2026-10-21 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/greenboot-drill-parallels`, stacked on `docs/d22-boot-cause-and-ups` (pull request not yet opened; this record cites D22's rule), in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | Experiment run, question answered (1 h 45 min of the 4 h budget); verifier FAIL (whitespace), repaired, follow-up PASS; COMPLETE; VM kept by the owner for later tests |
| **Change type** | experiment (stage 1, before change 4; evidence only, no image or CI change) |

## Task Contract

1. **Outcome:** the project knows, from observed boots rather than bug reports, whether the stock greenboot rollback works for the node's own image, so the fix that follows (D22's rule, change 4) is built against real behaviour.
2. **Scope:** one experiment answering one question (below) in a disposable Parallels VM on the owner's Mac (Apple M2, macOS 26.6). Risk tier: **high-risk** (the rollback path); no code. Files: this record and its evidence folder `docs/build-records/evidence/2026-10-21-greenboot-drill-parallels/`. **Not included:** any change to `image/`, CI, greenboot units or drop-ins; the boot-cause record; x86_64; the N150; option C (the CI VM job, its own task after this one); the owner's other VMs (`Ubuntu 24.04`, `Windows 11`), which are not touched.
3. **Done when:** each case of the procedure has run and its outputs are kept in the evidence folder, with Pass, Fail or Not yet proven per case; the record states which of greenboot-rs #217, #218 and #219 occurred on this layout and names the fix task; the VM, its key and the settings exceptions are removed or their removal is handed to the owner; one `verifier` pass over the conclusions has no Important finding.
4. **Authority:**
   - The owner approved `prlctl` for the experiment's VM ("prlctl is fine. The VM is there for experiment.", 2026-10-21) and turned the session's Bash sandbox off (2026-10-21). With the sandbox off, the boundary is this contract: only the VM `rikuri-drill`, its throwaway key, the files below, and the network destinations named here.
   - Network: the Fedora mirrors (the installer and its CHECKSUM) and `registry.fedoraproject.org` (the base image, pulled inside the VM). Then the VM is moved to Parallels' host-only network for the drill, and that isolation is checked.
   - Downloads: each one asked first, with name, source and size.
   - The VM's login: a key made only for it (`~/.ssh/rikuri-drill`, never read by the agent) and a `drill` user whose password the owner sets in the installer.
   - Git: commit on this branch; push and pull request only on the owner's word. Independent check required.
5. **Limits:** one experiment; time budget 4 hours of wall time from VM creation, then stop and report what was seen; two repair cycles; two review rounds. It ends in keep, simplify or drop (AGENTS.md §6); the procedure is kept as input to option C, the VM is discarded.

**The question:** on Fedora IoT 44 aarch64, installed by Anaconda (its default layout, with a separate `/boot`) and switched to the node's own image, (1) does a staged update that fails a required health check roll back by itself, with `/var` intact, and (2) does an update that fails to apply at shutdown roll the healthy running image back?

## 0. Intent

- [x] **Problem, in the owner's words:** "Can you run the greenboot work in ubuntu 26.04 from Parallel?", then "Ok A, then C." (2026-10-21): option A, the node's image booted directly as a Parallels VM, then C, the CI VM job.
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** a disposable VM on the owner's Mac; no node, no repository code.
- [x] **Open questions:** whether the aarch64 installer boots under Parallels on Apple Silicon (step 2 shows it; if not, the experiment stops as BLOCKED); whether the pinned base digest has an arm64 build of 44.20261012.0 (step 4 shows it; if not, the nearest 44 arm64 digest is used and recorded).
- [x] **Owner approved the intent:** the messages above, and "Yes, you can write it." for this record.

## 0b. Spec

- [x] **Requirements:** reproduce before fixing (AGENTS.md §5); a disposable environment with no secrets, least access, and network denied except named destinations, checked rather than assumed (AGENTS.md §2); the node's own Containerfile, unchanged, as the image under test.
- [x] **Design:** build the image inside the VM with `podman build --from <arm64 base>` (overrides `FROM` without editing the repository), switch the host to it from local container storage, then stage deliberately bad or blocked updates. Rejected: Ubuntu in Parallels with nested QEMU (no nested virtualization on the M2: emulation only); the existing Ubuntu VM (runs Docker and Kubernetes networking, not disposable).
- [x] **Policy applied:** an experiment answers one stated question and never becomes production code by itself (AGENTS.md §6); an aarch64 build for testing only does not change D1 ("aarch64: waits for D1", stage 1 record).
- [x] **Flagged concerns:** Anaconda's layout differs from change 5's install media, so a Pass here does not prove the N150; the first switch from the stock install (greenboot of the April ISO) to the node's image may meet #217, and is recorded, not counted.

## 1. Plan — the procedure

Each step records its commands' outputs in the evidence folder (`NN-<step>.out`).

1. **Installer.** On the Mac, in a new empty folder in the scratchpad: download `Fedora-IoT-ostree-44-20260427.0.aarch64.iso` (2,343,327,744 bytes) and `Fedora-IoT-44-aarch64-20260427.0-CHECKSUM` from `https://download.fedoraproject.org/pub/alt/iot/44/IoT/aarch64/iso/`; check the CHECKSUM's signature against `https://fedoraproject.org/fedora.gpg` where `gpgv` is available, and the ISO's SHA-256 against both the CHECKSUM and the download page (`621912a5fe82dfee1bcd330d6fdacda9b5dc77a31cc31a270c7ff2e6877c7196`).
2. **VM.** `prlctl create rikuri-drill`, 2 CPUs, 4096 MB, a 32 GB disk, the ISO attached, Parallels' shared network. The owner installs in the Parallels window: automatic partitioning, user `drill` (administrator) with the throwaway public key, no root password. Record `lsblk -f`, `findmnt /boot`, `rpm -q greenboot bootc rpm-ostree ostree grub2-common`, `bootc status`, `rpm-ostree status`, `grub2-editenv list`.
3. **Access.** The owner adds the `rikuri-drill` SSH alias (IP from Parallels' DHCP leases, matched by the VM's MAC). Check `ssh rikuri-drill true`.
4. **The node's image.** Copy `image/` to the VM. Find the arm64 manifest of the pinned base (`skopeo inspect --raw` or `podman manifest inspect` on the digest in `image/Containerfile`). `sudo podman build --from registry.fedoraproject.org/fedora-iot@<arm64 digest> -t localhost/rikuri-os:good image/`, then `sudo bootc switch --transport containers-storage localhost/rikuri-os:good` (fallback: `rpm-ostree rebase ostree-unverified-image:containers-storage:localhost/rikuri-os:good`), reboot, record versions and `journalctl -b -u greenboot-healthcheck`. Write `/var/drill-marker`.
5. **Isolation.** Move the VM to Parallels' host-only network. Check: `curl -m5 https://registry.fedoraproject.org` fails, and the shared network's addresses (`10.211.55.1`, `10.211.55.9`) do not answer. Pass required before step 6.
6. **Case 1 — a failing update (#218).** Build `localhost/rikuri-os:broken` from `:good` plus a required check that always fails (`/etc/greenboot/check/required.d/99-drill-fail.sh`, `exit 1`). `bootc switch` to it; before rebooting, record `systemctl status greenboot-set-rollback-trigger.service` and its ordering (`systemctl show -p Conflicts,Before,After,DefaultDependencies`). Reboot and let it run. Per boot record `grub2-editenv list`; at the end `bootc status`, `journalctl -b -1 -u 'greenboot*'` and the marker. **Pass:** back on `:good` by itself within the configured three attempts, marker intact. **Fail:** stays on `:broken`, or loops.
7. **Case 2 — an update that fails to apply (#219).** From `:good`, build `:good2` (one changed label) and `bootc switch` to it. Make finalizing fail: fill the filesystem that holds `/boot` (one `fallocate`d file, leaving about 28 KiB), record `df /boot`, reboot. Afterwards record `bootc status`, `grub2-editenv list` and greenboot's journal, then remove the file. **Pass** (D22's rule): the host stays on `:good`. **Fail:** it is rolled back to the deployment before `:good`.
8. **Case 3 — a power cut during an update (D22), if time allows.** Stage `:good2` again and `prlctl stop rikuri-drill --kill` during the reboot's finalize; then the same records. Not part of the question; Not yet proven if skipped.
9. **Close.** Conclusions per case; the fix task named; `prlctl delete rikuri-drill`, the throwaway key and the `excludedCommands` entries removed by the owner or handed over in the close-out.

- [x] **One sentence:** reproduce greenboot's rollback behaviour for the node's image in a disposable VM before any fix is written.
- [x] **Blast radius:** one new VM on the owner's Mac; this record and its evidence; nothing irreversible outside the VM.
- [x] **Current behaviour characterized:** from the bug reports and the unit file only (plan §2, 2026-10-21); none observed.
- [x] **Risks:** the ISO does not boot under Parallels (then BLOCKED); no arm64 base of 44.20261012.0; `bootc switch` refused on the rpm-ostree install (then the fallback); filling `/boot` breaks the VM beyond repair (acceptable: it is disposable). Riskiest: confusing the experiment VM with the owner's other VMs; every `prlctl` call names `rikuri-drill`.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- N/A (no code). The images built in the VM are test artefacts, never published.

## 3. Debug

- N/A (this experiment is the reproduction a later fix needs).

## 4. Verify

- [x] Each case's outputs kept, with its verdict (Results, below; files in the evidence folder).
- [x] Independent verification: first pass **FAIL** on one Important finding (I1: trailing whitespace in six evidence files, which the full gate's whitespace step would reject); every conclusion found supported. Repaired in cycle 1 of two, with nits N1 to N5 and the three backlog nits. Follow-up pass **PASS** (corrections only; no new Important finding; two wording leftovers fixed after it).

## 5. Close Out

- [x] Conclusions and the fix task recorded (Results and Conclusion, below); **keep** the procedure as input to option C.
- [x] VM, key and settings exceptions handed to the owner, who keeps them for later tests (Skipped items).
- [x] The DNS gap in isolation (step 5) ratified by the owner (2026-10-21, "2. DNS OK").
- [x] Committed; pushed on the owner's word (2026-10-21, "3. Push now"); D22's pull request #27 had merged meanwhile (`01cbdce`), so this branch's pull request targets `main`.

## Results

Run 2026-10-21 in `rikuri-drill` (Parallels 27.0.3 on the owner's M2, macOS 26.6), driven over SSH with a throwaway key; the VM's host key (`SHA256:NtVMqX12NYeujT0KNVRasNSCtiVoLgh3+SqVUFD5938`) checked on its console by the owner.

| Step or case | Result | Evidence |
|---|---|---|
| 1 Installer | **Pass.** CHECKSUM signed by "Fedora (44)" (gpgv: good signature, key `36F612DC…6D9F90A6`); ISO SHA-256 `621912a5…7c7196` matches the CHECKSUM and the download page | `01-installer-and-vm.out` |
| 2 Install | **Pass.** Boots under Parallels on Apple Silicon. Anaconda's default layout: `/boot` its own ext4 partition (`sda2`, 2 GB), EFI on `sda1`, root on LVM. Stock: greenboot 0.16.2, bootc 1.12.1, rpm-ostree 2026.1, ostree 2025.7. Stock 0.16.2's trigger unit has `Conflicts=shutdown.target`, which 0.16.4 dropped | `02-stock-install.out` |
| 4 The node's image | **Pass, with a deviation.** The pinned base digest is a single amd64 image (44.20261012.0); Fedora keeps no dated tags, so today's `44` arm64 build was used, pinned by digest (`sha256:d862d94f…`, 44.20261021.0). The unchanged `image/` builds in 3 min 29 s; `bootc container lint`: 14 checks passed. The image carries greenboot 0.16.4, bootc 1.17.1, ostree 2026.4, with the #218 unit verbatim. `bootc switch` from local storage worked on the Anaconda install | `04-*.out` |
| 5 Isolation | **Pass for connections, one gap.** On host-only: IPv4 to the registry, the internet, the shared network and the owner's Ubuntu VM all refused, and IPv6 to `fedoraproject.org` refused (only a private IPv6 address, no route out). Gap: DNS lookups still answered by Parallels' resolver on the Mac (`10.37.129.1`). Accepted for this VM, which holds no secret | `05-isolation.out` |
| Case 1, a failing update (#218) | **Pass.** At shutdown the trigger armed (`greenboot_next_deployment_id=<broken>`, `fallback=1`); `:broken` failed its required check on four boots (the first sets `boot_counter=3`, three more count it down), then greenboot ran `bootc rollback`; the node returned to `:good` by itself, `/var/drill-marker` intact. **#218 not reproduced on this layout** (a layout without a separate `/boot` was not run): the trigger has `RequiresMountsFor=/boot` (an implied `Requires=boot.mount`) and `After=boot.mount`, and `boot.mount` stops at shutdown (`Conflicts=umount.target`), so the trigger is stopped first and its `ExecStop=` runs | `06-case1-*.out` |
| Case 2a, `/boot` full | **Not a failure path here.** With 24 KiB free, applying still succeeded ("bootfs is sufficient for calculated new size: 0 bytes"): every image in the drill shares one kernel. A full `/boot` breaks only an update that brings a new kernel | `07-case2-*.out` |
| Case 2b, an update that fails to apply (#219) | **Fail against D22's rule; #219 reproduced.** The trigger armed for `:good4`, then finalizing failed (a drop-in in `/run` making its `ExecStop` exit 1); the healthy `:good3` booted unchanged, greenboot logged "GRUB kernel fallback detected - new deployment failed to boot" and queued `bootc rollback`; at the next reboot the healthy node was **downgraded to `:good2`** | `07-case2b-*.out` |
| Case 3, a power cut during an update (D22) | **Cut after applying: Pass** (the node booted the new image; nothing rolled back). **Cut after the trigger armed and before the deployment was written (1.6 s into the reboot): Fail**, the same mechanism as #219. Inferred, because the killed boot's journal lost its last seconds: at the next boot greenboot read `expected deployment sha256:a8e9…` (the image just staged) from `grubenv`, which that boot had cleared at 8.26 s, so the trigger ran during the cut-short shutdown; no deployment of that image exists. The update did not persist, and greenboot queued a rollback of the healthy `:good4` to `:good2` | `08-case3*.out` |

Not proven here: #217 (the first update from the stock 0.16.2 install was a good image, so whether 0.16.2's trigger is honoured by 0.16.4 was not tested); #220 (no software mirror); x86_64 and the N150's own layout; a new kernel in the update.

## Conclusion

- **Keep** the procedure; it is the input to option C (the CI VM job), which should run the same cases on x86_64.
- On Anaconda's layout, greenboot 0.16.4 **does** roll back a failing update by itself (case 1). #218 was not reproduced with a separate `/boot`; a layout without one was not run. Change 5's install media should keep `/boot` separate, or carry a fix for #218.
- greenboot **does not** satisfy D22's rule: an update that was never applied, by a failed finalize or a power cut after the trigger armed and before the deployment was written, makes it roll a healthy node back to the release before (cases 2b and 3). The downgrade lands at the next reboot, which on a node may be days later.
- One wording to correct in the fix task: a failing update runs **four** boots before the rollback, not three (plan §4.1, "If a required check fails three boots in a row", and the comment in `image/rootfs/etc/greenboot/greenboot.conf`). The design must also not be fooled when a staged digest equals an existing, non-booted deployment.
- **The fix task (not started):** stage 1, the D22 rule against #219, in the image. Its shape, for that task's own design: at boot, before greenboot's fallback check, compare `greenboot_next_deployment_id` with the deployments that exist; if the expected one was never written (the update was not applied), clear the trigger and record "update not applied" as the boot's cause, instead of treating it as a GRUB fallback. Its proof: cases 2b and 3 of this procedure turn from Fail to Pass while case 1 stays Pass, red first (AGENTS.md §5); this record is the red run.

**Deviations from the Plan:** case 2 used `:good2` to `:good4` and a `/run` drop-in to make finalizing fail, after the full `/boot` of the Plan did not (case 2a), so that a wrong rollback would land on a good image; case 3 staged `:good4`, then `:good3`; step 3's `ssh … true` check and case 1's per-boot `grub2-editenv` records were not kept as files (the counter values are greenboot's own journal lines); the Plan's "within the configured three attempts" is answered by four boots (Conclusion). Claims without a file: the pinned digest being amd64-only and Fedora keeping no dated tags were seen in the session's `skopeo` output and not saved; `image/` was copied with `scp` from `b3cf4ff` and not hashed in the VM; IPv6 was tested against `fedoraproject.org` only. The VM's clock is 13 hours off (its "UTC" times are real UTC minus 13 h); order and durations are unaffected.

**Evidence files edited:** trailing blanks were stripped from six `.out` files (17 lines) so the repository's whitespace check passes (verifier finding I1); no other byte changed.

## Skipped items — visible, never silent

- Case 3 is timing-dependent: two cuts, one landed after applying, one during. Repeated cuts were not run.
- The VM, its key, the passwordless `sudo` and the `excludedCommands` entries are kept, and the session's sandbox stays off: the owner's decision (2026-10-21, "1. Keep rikuri-drill … 4. leave it for now. Takes a while to setup. We may be doing a lot more test along the way as we build."). Reactivate: remove them when the owner says testing is done.

## Evidence log

- 2026-10-21: the installer's size from the mirror (`curl -I`, redirected to `mirror.fcix.net`): `Content-Length: 2343327744`; the directory also lists `Fedora-IoT-44-aarch64-20260427.0-CHECKSUM`.
- 2026-10-21: the owner turned the Bash sandbox off for the session and approved `prlctl` for this VM; the VM's `drill` user was given passwordless `sudo` (`/etc/sudoers.d/90-drill`) by the owner, in this VM only.
- 2026-10-21: `prlctl list -a -f` before the experiment: `Ubuntu 24.04` (running, 10.211.55.9) and `Windows 11` (stopped); neither is used.
