# Build Record — An update is no longer dropped at shutdown: the EFI partition's automount on /boot is masked

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-automount-mask`, from `stage1/case1-finalize-evidence` at `a2613c7` (PR #87, not yet merged: its case 1 is this fix's proof); worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | fix |

## Why

`docs/build-records/2026-11-11-case1-finalize-race.md` found, in 5 failing drill runs of 5, that a staged update is dropped at shutdown when systemd's `boot.automount` ("EFI System Partition Automount", on `/boot`) goes before `ostree-finalize-staged`: `error: Remounting /boot read-write: Invalid argument`. The node stays safely on its image and logs "never applied", but the update does not happen. 2 drill runs of 2 on PR #87 hit it.

Upstream knows it (read 2026-11-11, data only):

- [bootc #2402](https://github.com/bootc-dev/bootc/issues/2402), open, milestone 1.18: two generators claim `/boot`. ostree's generator adds a bind mount of `/sysroot/boot`; systemd-gpt-auto-generator adds an ESP `boot.automount` with a 120 s idle timeout, which tears down ostree's mount when it goes. Bisected to ostree 2026.3, after which gpt-auto no longer skips partition discovery on composefs. [bootc #2622](https://github.com/bootc-dev/bootc/issues/2622) is our symptom, closed as its duplicate.
- The fix, [ostree #3690](https://github.com/ostreedev/ostree/pull/3690) (finalize through the boot file descriptor, not the `/boot` path), is open with changes requested. An earlier ostree patch that masked `boot.automount` from ostree's own generator was declined, because ostree should not disable part of gpt-auto behind the system's back. That concerns ostree doing it for everyone. An image choosing it for itself is a different decision, and the owner's.

## Task Contract

1. **Outcome:** an update staged on a node is applied at the next boot, instead of being dropped about half the time by a shutdown race over `/boot`.
2. **Scope:** high-risk (the OS image, its update path). The owner chose "Mask boot.automount" (2026-11-11), over the kernel argument `systemd.gpt_auto=0` and over waiting for upstream. Files:
   - `image/rootfs/usr/lib/systemd/system/boot.automount`, a link to `/dev/null`: the image masks the automount, as it masks the getty units on tty2. A mask in `/usr/lib` takes priority over the generator's late folder, where gpt-auto writes, and goes back with an image rollback. ostree's own `boot.mount` (its bind of `/sysroot/boot`) is a separate unit, and stays.
   - `image/check_image_root.py` and its tests: the build fails unless the mask is there and nothing in the image would override it.
   - `image/drill/vm_drill.py` and its tests: a check after the first boot that `boot.automount` is masked and inactive and that `/boot` is ostree's ext4 alone (no autofs, no vfat).
   - this record.

   **Not included:** the kernel command line; `/efi`; any change to ostree, bootc or greenboot; the drill's other cases. Removing the mask once a Fedora ostree has #3690 is a later task.
3. **Done when:**
   - red tests, committed and seen failing in CI first, then passing after the fix: the image check (mask missing, pointing elsewhere, overridden) and the drill's check;
   - `Full gate (Ubuntu)` green on the PR, and the image build's `check_image_root.py` passing on the real image;
   - the drill on the PR: the new check passes (`LoadState=masked`, `/boot` ext4 only), and case 1 passes, **in 3 drill runs** (the PR's run and 2 re-runs of the job). Since the race hit 5 of 8 recent runs, 3 passes by chance alone would be unlikely, and the mask check shows the mechanism directly;
   - one verifier pass with hand mutations, and the follow-up if needed.
4. **Authority:** the owner's "Fix" and "Mask boot.automount" (2026-11-11). Edit the files in Scope. Read this repository's CI evidence with `gh`, and the upstream pages above (data only). Python tests run on `rikuri-drill` through `safe-run.sh`. Commit, push this branch, open a draft PR stacked on #87, and re-run its drill job twice. No change to CI workflows, the gate or the guard. Verifier: required.
5. **Limits:** this task only; at most two repair cycles and two review rounds. No budget configured; CI used is reported.

## Plan

1. Red:
   - `test_check_image_root.py`: the mask is missing, a regular file, a link elsewhere, or overridden by `boot.automount` in `/etc/systemd/system`, `system.control`, `system.attached` or `/usr/local/lib/systemd/system`. Each is a finding. The shipped root passes.
   - `test_vm_drill.py`: `boot_automount_masked(show, findmnt)`; the drill's step through a stand-in; the expected checks.
   - Commit; push; see it fail in CI.
2. Fix: the link, the image check, the drill's check. Commit.
3. The gate and the image build on the PR; three drill runs; the verifier; this record.

## Evidence log

### Red (`b7dcc1c`, the tests alone)

- On `rikuri-drill`, through `safe-run.sh`: `Ran 532 tests`, `FAILED (failures=16, errors=17)`. Every failure is in the new tests, and fails for the expected reason:
  - no mask in `rootfs`;
  - no finding for a missing, wrong or overridden mask;
  - `no attribute 'boot_automount_masked'` and `'SHOW_BOOT_AUTOMOUNT'`;
  - `main` without the step;
  - the expected checks without the new one.

  "The masked root has no finding" passes, as it should with no check.
- CI: `Full gate (Ubuntu)` **Fail**, as wanted, on `b7dcc1c`: [run 43150462244](https://github.com/rikuripi/rikurinode/actions/runs/43150462244) (job 130958137855). The image tests report `FAILED` in the same 33 new tests as above; nothing else fails.
- The same commit's rollback drill (no mask yet), job 130958936180: case 1 `never applied`, with `Remounting /boot read-write: Invalid argument`. This is the third drill run in a row to hit the race; it is the "before".

### Fix

- `image/rootfs/usr/lib/systemd/system/boot.automount` → `/dev/null`.
- `image/check_image_root.py`: `BOOT_AUTOMOUNT`, `BOOT_AUTOMOUNT_OVERRIDES`, and `check_boot_automount()`, in `check_root`.
- `image/drill/vm_drill.py`: `SHOW_BOOT_AUTOMOUNT`, `BOOT_FSTYPES`, `boot_automount_masked()`, and `Drill.boot_automount()`, run right after the first boot. It keeps `01d-boot-automount.out` and is in `EXPECTED`.
- On `rikuri-drill`, through `safe-run.sh`: `Ran 532 tests`, `OK`. No test changed after red.
