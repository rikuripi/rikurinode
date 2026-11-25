# Build Record — sshd off by default in the image (stage 1, plan §8; ADR 0011)

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/sshd-off`, from `main` at `04a12cb`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `a692435` (contract), `2e7f303` (red), `47683cb` (fix): PR #175, merged by the owner at `47683cb` (`56e1c64`); this close-out on `docs/sshd-off-record`, a docs-only PR |
| **Status** | DONE |
| **Change type** | defect fix (the image) |

## Intent: the owner's words

- **"A, then Next"** (2026-11-24), after `docs/build-records/2026-11-24-no-shell-login.md` ended `NEEDS_OWNER_DECISION`: option A, "Switch sshd off in the image": the image ships a setting that disables sshd, ahead of Fedora's default; the drill still works, its kernel argument starting sshd without enabling it.

## The defect

- **Seen:** the drill's new check, on PR #174's branch, [run 45495422770](https://github.com/rikuripi/rikurinode/actions/runs/45495422770): after its first boot the node has `sshd.service: enabled` and listens on port 22. Everything else the check reads is closed.
- **Against:** the plan's stage 1 "no shell login by default"; ADR 0011, "Expert shell: SSH, key-only, off by default"; the threat model's "No SSH or console login enabled by default".
- **Not yet known:** whether the base image ships an enablement link, or Fedora's presets enable sshd at the first boot. The red run of the image check below shows which.

## Design

- **The setting:** `image/rootfs/usr/lib/systemd/system-preset/10-rikuri-node.preset`, two lines, `disable sshd.service` and `disable sshd.socket`. systemd reads preset files across their folders in the order of their names, and the first line that matches a unit decides. `10-` comes before Fedora's own (`90-default.preset` and others). Not a mask: the drill's `systemd.wants=sshd.service` must still start it, and ADR 0011's later window must be able to switch it on.
- **If the base image ships an enablement link** (seen in the red run), `RUN systemctl disable sshd.service sshd.socket` in `image/Containerfile` removes it at build. Otherwise the Containerfile is not changed.
- **The check** (`image/check_image_root.py`, `check_sshd_off`), on every image build:
  - the preset file is exactly its two lines;
  - in the image's preset folders (`etc/systemd/system-preset`, `usr/lib/systemd/system-preset`; a file in `etc` replaces one of the same name in `usr/lib`), the first line matching `sshd.service`, and the first matching `sshd.socket`, is this file's `disable`;
  - no `.wants`, `.requires` or `.upholds` folder under `etc/systemd/system` or `usr/lib/systemd/system` holds `sshd.service` or `sshd.socket`.
  As every read in the check, a link on the way ends it.
- **The running node:** the drill's "no shell login by default" (PR #174, not on `main` yet) must pass once this change is under it. That is #174's evidence, after this merges.
- **Not changed:** the drill; the firewall; sshd's configuration.

## Task Contract

1. **Outcome:** a node built from the image has sshd disabled after its first boot, as ADR 0011 and the plan say, and the image check holds it.
2. **Scope:** routine. It changes which service a node starts, but only to turn off one that nothing uses; no key, funds or sign-in path.
   - `image/check_image_root.py` (`check_sshd_off`, in `check_root`); `image/tests/test_check_image_root.py` (red first).
   - `image/rootfs/usr/lib/systemd/system-preset/10-rikuri-node.preset`; `image/Containerfile` only if the red run shows a link.
   - This record.
   - **Not included:** the drill check (#174); masking sshd; ADR 0011's window.
3. **Done when:**
   - Red: the check and its tests committed alone and seen failing in CI: the full gate on the fixture tests, and the image workflow's check on the real image, its findings read.
   - Then the fix in its own commit; the full gate and the image workflow pass, the image check with no sshd finding.
   - One `verifier` pass (code; AGENTS.md §5).
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`; the tests run in CI only. Commit and push this branch; a draft PR to `main`; the owner merges.
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; VM time is reported.

## Evidence log

### Red

- `image/check_image_root.py`: `check_sshd_off` and `preset_decisions`, in `check_root`, as designed. No preset shipped yet.
- **Reasons for the test changes** (`image/tests/test_check_image_root.py`; red first, the defect seen in the drill):
  - The fixture `Root` copies the shipped preset when it exists, as it does for every shipped file, so the good root holds it once the fix ships it.
  - New `SshdOff`:
    - the image ships the preset's two lines;
    - with Fedora's `90-default.preset` enabling sshd after it, the root passes;
    - the preset missing, with one unit, enabling, or a link is a finding;
    - an earlier preset that enables sshd is a finding (by name, by `sshd.*`, by `*`), and so is one in `etc` that replaces the image's of the same name;
    - an earlier preset that disables it is a finding too, since only the image's own line is held: another file may change or go with an update;
    - a later line does not count;
    - an enablement link for sshd in `.wants`, `.requires` or `.upholds`, in `etc` or `usr/lib`, is a finding;
    - `preset_decisions` reads comments, globs and the first match as systemd does.
- Expected in CI: the full gate fails on the good-root tests (no preset in `rootfs`) and `test_the_image_ships_the_preset`; the image workflow's check fails on the real image, its findings showing which preset decides sshd today and whether the base image ships an enablement link.

### The red run, `2e7f303`: Fail as expected, and what the real image holds

- `CI`, [run 45502844723](https://github.com/rikuripi/rikurinode/actions/runs/45502844723): `Full gate (Ubuntu)` failed in the image tests with `FAILED (failures=15, errors=1)`. The error is `SshdOff.test_the_image_ships_the_preset`: `FileNotFoundError` for the preset. The 15 failures are the good-root tests (`test_good_root_passes`, every `test_the_shipped_files_pass`, and the others built on the fixture root): each fails on this check's findings alone, because there is no preset in `rootfs`.
- The image workflow, [run 45502845036](https://github.com/rikuripi/rikurinode/actions/runs/45502845036): the check on the built root, four findings:
  - `usr/lib/systemd/system-preset/10-rikuri-node.preset: missing, or not a regular file`;
  - `sshd.service: the first preset for it is enable, in usr/lib/systemd/system-preset/90-default.preset`;
  - `sshd.socket: the first preset for it is disable, in usr/lib/systemd/system-preset/99-default-disable.preset`;
  - `etc/systemd/system/multi-user.target.wants/sshd.service: enables sshd on every node`.
- **So both causes are real:** Fedora's base image ships sshd enabled (the link in `/etc`), and Fedora's presets would enable it at a first boot. The fix needs both parts of the Design.

### The fix

- `image/rootfs/usr/lib/systemd/system-preset/10-rikuri-node.preset`: `disable sshd.service`, `disable sshd.socket`, with the reason.
- `image/Containerfile`: `RUN systemctl disable sshd.service sshd.socket` after the `rootfs` copy. It removes the base image's link at build.
- No test changes after the red.
- **Not yet proven: a node installed before this change,** such as the owner's N150. Presets apply only at a first boot. Whether an update removes the old link from its `/etc` depends on ostree's merge of `/etc` (a file the owner never changed takes the new image's state). The drill installs fresh, so it does not show this.

## Verification

- **The verifier**, one pass on `04a12cb..47683cb` (routine): **no Important finding**; its verdict was "not yet proven" only because CI on `47683cb` was still running.
  - Checked: the red commit holds only the check, its tests and this record, and failed as recorded (runs 45502844723, 45502845036); `git diff 2e7f303 47683cb -- image/tests image/check_image_root.py` is empty, so no test changed after the red; every new test has its reason; scope as the contract names; `git diff --check` clean.
  - Reasoned: the build's `systemctl disable` removes the base image's link offline; at a first boot `10-` sorts before `90-default.preset`, so the disable decides; not a mask, so the drill's `systemd.wants=sshd.service` still starts it.
  - Hand mutants (on a scratch copy, `python3 -I`): first match replaced by last, globs replaced by equality, the `etc`-over-`usr/lib` order dropped, `.upholds` dropped: killed. Survived: `ignore` dropped from the verbs (no test uses `ignore`, though a test's name says so); the finding for a linked preset file other than the image's; the skip of a missing folder; `len(words) < 2` as `< 1`.
- **Nits, and what was done:** none fixed here; each is backlog.
  1. The check does not read `usr/local/lib/systemd/system-preset`, nor the unit folders `etc/systemd/system.control`, `etc/systemd/system.attached` and `usr/local/lib/systemd/system` (the repository's `SUBID_UNIT_DIRS` and `BOOT_AUTOMOUNT_OVERRIDES` already list them). As designed, but narrower than systemd reads.
  2. The surviving mutants above, `ignore` first.
  3. A linked `*.wants` folder is skipped without a finding, while a linked preset file is one.
  4. Paths the check cannot see: a drop-in `Wants=sshd.service`, and generators, `systemd-ssh-generator` among them (a local AF_UNIX socket, and AF_VSOCK in a VM, unless `systemd.ssh_auto=no`). Neither is reachable from the LAN; the drill's runtime check (#174) reads the running node.

## CI, `47683cb`

- `CI`, [run 45503324502](https://github.com/rikuripi/rikurinode/actions/runs/45503324502): `Full gate (Ubuntu)` **Pass**.
- The image workflow, [run 45503324685](https://github.com/rikuripi/rikurinode/actions/runs/45503324685): "Build and check the OS image" **Pass**. Its log: `RUN systemctl disable sshd.service sshd.socket` printed `Removed '/etc/systemd/system/multi-user.target.wants/sshd.service'.`, and `check_image_root: 0 finding(s)` on the built root. The drill and the USB install: **Pass**; every job of the run Pass.

## Result

- **Pass (observed):** the image ships sshd disabled. The build removes the base image's enablement link, the image's preset decides sshd before Fedora's, and the image check holds both with `0 finding(s)` (runs 45503324502, 45503324685). The red run showed each cause on the real image first (45502844723, 45502845036).
- **Not yet proven:**
  - on a booted node, sshd disabled after the first boot: the drill's "no shell login by default" check on PR #174, once it is updated onto `main`;
  - a node installed before this change (the owner's N150) after an update: ostree's `/etc` merge.
- **Backlog:** the verifier's nits 1 to 4 above; the N150's sshd state after its next update.
