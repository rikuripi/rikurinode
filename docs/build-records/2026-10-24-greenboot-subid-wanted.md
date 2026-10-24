# Build Record — A greenboot wanted check for Podman's containers range

| | |
|---|---|
| **Date** | 2026-10-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/greenboot-subid-wanted`, from `main` at `6c6038c`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature (the OS image's health check) |

## Task Contract

1. **Outcome:** when `rikuri-containers-subid` does not succeed at boot, greenboot records it as a failed wanted check with the reason and where to look, instead of reporting a healthy node in silence; the boot still counts as good, so no rollback.
2. **Scope:**
   - `image/rootfs/usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid`, new: Python, `-I`, no shell.
   - `image/check_image_root.py`: require it, executable, in `wanted.d`, and in no `required.d`.
   - Tests in `image/tests/`.
   - `image/drill/vm_drill.py`: the first-boot range check also requires greenboot's "wanted script … success!" line for it.
   - Risk tier: **high-risk** (greenboot decides rollbacks).
   - **Not included:**
     - a required check, or any rollback on this failure (owner, 2026-10-24: a rollback cannot repair `/etc`);
     - Fedora's own `01_update_platforms_check.sh`, which fails on every boot without a route to Fedora (noted for the owner);
     - a repair action or a status page (later stages).
3. **Done when:**
   - the check's tests are committed failing first, then pass;
   - in `rikuri-drill`, an image with the check: (i) a normal boot logs the check's success; (ii) with `/etc/subuid` made unreadable to the unit (a `# comment` line), the boot logs the check failed with its reason, greenboot still passes, `boot_success=1`, and the booted deployment does not change;
   - the CI drill passes, with the new line in its first-boot check;
   - `Full gate (Ubuntu)` passes;
   - one `verifier` pass has no Important finding.
4. **Authority:**
   - the owner's "Ok Next" (2026-10-24), after the wanted-check design was put to them ("Say 'Next' and I'll start it on that basis");
   - edit the files in Scope;
   - use `rikuri-drill` as before;
   - push this branch and open the pull request; no merge;
   - CI drill development runs: at most 2;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 2 hours.

## 0b. Spec

- [x] **How greenboot runs a check** (`01-probe-wanted-python.out`):
  - greenboot 0.16.4 executes a `wanted.d` file by its shebang: the Python probe ran as `/usr/bin/python3`, its parent `greenboot`;
  - a failure logs "wanted script … failed!" and the script's output;
  - the health check still passes, and `boot_success=1` is set.
- [x] **Design:**
  - The check asks systemd for the unit's `ActiveState` and `Result` (`/usr/bin/systemctl show`, fixed arguments, no shell). It passes only on `active` and `success`: the unit is a `RemainAfterExit` oneshot, so `Result=success` alone would also be a unit that never ran (verifier, 2026-10-23).
  - On failure it prints one plain line: what failed, what it breaks, and the journal command.
  - It lives in `/usr/lib` (image-owned, not merged from `/etc`).
- [x] **Alternatives rejected:**
  - a required check (rolls back for a cause no image can fix);
  - reading the files again in the check (duplicates the unit's rules; the unit's own verdict is the single source).

## Evidence log
