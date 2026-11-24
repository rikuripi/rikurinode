# Build Record — sshd off by default in the image (stage 1, plan §8; ADR 0011)

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/sshd-off`, from `main` at `04a12cb`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at close-out) |
| **Status** | IN PROGRESS |
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
