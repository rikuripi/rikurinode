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
2. **Scope:** high-risk? No: routine. It changes which service a node starts, but only to turn off one that nothing uses; no key, funds or sign-in path.
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
