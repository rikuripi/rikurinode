# Build Record — the rollback rule: which boots count against an update (D22, task 3 of 3)

| | |
|---|---|
| **Date** | 2026-11-20 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-cause-rollback-rule`, from `main` at `0b50fa3`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `59ac4d7` (contract), `9c29ef2` (change), and this record |
| **Status** | IN PROGRESS |
| **Change type** | feature (OS image: greenboot's counter armed for every new image and told which boots not to count; the VM drill) |

## Intent: the owner's words

- "Choice 1: A; Choice 2: A; go" (2026-11-19): task 3 of 3 is "the rollback rule: greenboot told which boots not to count" (`docs/build-records/2026-11-19-boot-cause-record.md`).
- "Next" (2026-11-20), starting this task, after task 2 closed (#139).
- Asked how boots are counted, given what greenboot does (below): **"Count from first boot"**: arm greenboot's counter at the shutdown that applies an update, so GRUB counts every boot of the new image; the boot path gives back one count for a boot the rule says not to count.
- Asked whether a clean restart during the trial counts: **"Count it"**: greenboot's own restart after a failed check is a clean shutdown too, and the node cannot tell the two apart.

## What exists

- **greenboot 0.16.4** (and 0.16.6, the newest; source read at both tags, `src/main.rs`, `src/lib/grub.rs`, `grub2/08_greenboot.cfg`):
  - At shutdown, `set-rollback-trigger` writes `greenboot_next_deployment_id` (the staged deployment) and `fallback=1`, only when a deployment is staged.
  - GRUB's snippet decrements `boot_counter` at each boot only when it is set and `boot_success=0`; at 0 it boots entry 1, the previous deployment.
  - `boot_counter` is set (to `GREENBOOT_MAX_BOOT_ATTEMPTS`, 3) only by a **failed health check** when none is set. A passed check sets `boot_success=1` and unsets the counter and the trigger.
  - So, today: a new image's boots are not counted until its first failed check. A boot that crashes, hangs or loses power before any check fails is never counted, and a new image that never reaches its checks is never rolled back. After that first failure, GRUB counts every boot down, a power cut included. Both are the opposite of plan §4.1's rule.
  - `fallback=1` is GRUB's own: the next entry when the default fails to load, not after a kernel that started.
- **`greenboot-unapplied-update`** (`ExecStartPre=-` of `greenboot-healthcheck.service`, record `2026-10-22-d22-unapplied-update.md`): clears the trigger when the default deployment booted and is not the update named (never applied, greenboot-rs #219), with `/boot` remounted writable for its one write.
- **`rikuri-boot-cause`** (before `sysinit.target`): one entry per boot in `/var/lib/rikuri/boot-cause/history.jsonl`, the cause of the boot that ended (`power-cut`, `clean`, `update-applied`, `kernel-crash`, `watchdog`, `rolled-back`, `unknown`, `first-boot`), and this boot's entry in `/run/rikuri-boot-cause/this-boot.json`.
- **The VM drill**: case 1 (a broken update, four boots then greenboot's rollback), case 2b (finalize fails), case 3 (a power cut while the update is applied), and `kill_vm()`, a real power cut.

## Design

- **Arm at the shutdown that applies an update.** A new `ExecStop=-` in the existing drop-in on `greenboot-set-rollback-trigger.service`, after greenboot's own: when a deployment is staged and the trigger names it, set `boot_counter=3` and `boot_success=0`. A shutdown with nothing staged (a restart during the trial) arms nothing, so it never resets a countdown. GRUB then counts every boot of the new image from its first: three boots, then the previous image.
- **Never applied, all of it cleared.** When `greenboot-unapplied-update` clears the trigger (#219), it also unsets the counter armed for that update, so a healthy node that kept its image is exactly as before.
- **Given back: a first power cut in a row.** In the same pre-check run, while the update is on trial (the booted deployment is the one the trigger names, the counter set and above 0): when this boot's entry, read strictly with its boot id the kernel's, says `power-cut` and the entry before it does not, add one to `boot_counter`, never above 3. A second power cut in a row counts, as the plan says ("a frozen node that its owner unplugs looks the same as a power cut").
- **Everything else counts:** a kernel crash, a watchdog reset, an unknown cause, a failed check, a clean restart (the owner's choice). No UPS exists until stage 4, so no shutdown cause is given back for it yet; ADR 0006's migration rule waits for the first migration.
- **Nothing silent.** Each arm, clear and give-back is logged to the journal and appended as one JSON line to a record under `/var/lib/rikuri`; anything unreadable leaves greenboot's count as it is (an unknown counts against the update).
- The record informs greenboot's counter and never replaces it: greenboot and GRUB still count and roll back.

## Task Contract

1. **Outcome:** a new image is counted from its first boot, so one that crashes or hangs before its checks run is still rolled back, while a single power cut during its trial does not count against it.
2. **Scope:** high-risk (the rollback path; BUILD-PROCEDURE, "Risk tiers").
   - `image/rootfs/usr/libexec/rikuri/greenboot-unapplied-update`: arming at shutdown, the counter cleared with the trigger, the give-back; its tests in `image/tests/`.
   - `image/rootfs/usr/lib/systemd/system/greenboot-set-rollback-trigger.service.d/50-rikuri-run-at-shutdown.conf`: the new `ExecStop=-`; `image/check_image_root.py` and its tests, if they assert the drop-in.
   - `image/drill/vm_drill.py` and `image/tests/test_vm_drill.py`: case 1 rolls back after three boots, the counter armed at the new image's first boot; a new case: a broken update with one power cut in its trial given back and a second in a row counted, still rolled back; cases 2b and 3 stay Pass with no counter left.
   - `image/rootfs/etc/greenboot/greenboot.conf`'s comment, `docs/architecture/platform-plan.md` §4.1 ("four boots" becomes three) and D22's row: a dated clarification; `README.md`'s status.
   - **Not included:** the kernel's panic setting and the hardware watchdog (a crash that hangs waits for the owner to unplug the node, which counts as a second power cut); staging an unapplied update again (needs the control plane's updater); a UPS cause; the sentence's wording; any control plane change.
3. **Done when:**
   - The full gate passes in CI, with unit tests for every arm, clear and give-back case and for every state left alone.
   - The image workflow's VM drill passes: case 1 rolls back after three boots, with `boot_counter` armed at the new image's first boot; the new power-cut case gives back one count and not the second; cases 2b and 3 leave no counter and no rollback; every earlier check stays Pass.
   - No red commit: a new feature, not a defect fix.
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** the files above and this record. On the Mac: `ast` parse checks, `git diff --check`; the Python tests and the drill run in CI only (`safe-run.sh` cannot run on this Mac). Read greenboot-rs's source on GitHub (done; data, nothing run). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Change, `9c29ef2`

- `greenboot-unapplied-update` keeps its name and its boot-time run, and gains the rule's other parts:
  - `arm` (a new `ExecStop=-` after greenboot's own in the trigger's drop-in): when `bootc status --json`'s staged image digest, read as greenboot reads it, is the one the trigger names, `grub2-editenv set boot_counter=3 boot_success=0`. Nothing staged, another digest, or anything unreadable: nothing armed. `/boot` is remounted around the write as before (the trigger's unit has `PrivateMounts=yes`).
  - never applied: the one `unset` now names the trigger and `boot_counter`.
  - `decide` gives the on-trial state its own action, `trial`; then `give_back`: a counter from 0 to 2, this boot's history entry (its boot id the kernel's) a `power-cut`, the entry before not: `boot_counter + 1`, appended to `/var/lib/rikuri/boot-count-given-back`. Every other state, and anything unreadable, is logged and changes nothing. With no counter set, the history is not read.
  - `MAX_BOOT_ATTEMPTS = 3`, held equal to `greenboot.conf`'s by a test.
- `check_image_root.py`: the trigger's drop-in must hold `ExecStop=-/usr/libexec/rikuri/greenboot-unapplied-update arm` under `[Service]`.
- The VM drill:
  - Case 1 gains "the new image counted from its first boot": the record since the switch is exactly `update-applied, clean, clean, rolled-back` (four boots of the broken image would be greenboot counting alone).
  - Case 1b, "power cuts in a new image's trial": the broken image again, greenboot's check held after the node's pre-check by an `/etc` drop-in (`99-`, after the node's `50-`) while a flag in `/var` exists; the counter read at each held boot after the heartbeat is written, then the power cut; expected `2, 2, 1`, one give-back recorded `[1, 2]`, the record `update-applied, power-cut, power-cut, clean, rolled-back`, and the rollback.
  - Cases 2b and 3 also require no `boot_counter` left.
- `greenboot.conf`'s comments, plan §4.1 (three boots; the rule's dated clarification) and D22's row, `README.md`.
- On the Mac: every changed Python file parses; `git diff --check` clean. The tests run in CI.

### Test changes, with their reasons

- `test_greenboot_unapplied_update.py`:
  - `decide`'s two on-trial tests expect `trial`, not `none`: the state has its own action now, as the give-back acts on it; they still assert no clear.
  - The never-applied tests expect `unset greenboot_next_deployment_id boot_counter`: the counter armed for the update is cleared with its trigger.
  - `Run.runner` answers `set` and `bootc status --json` as well, for the new classes; new classes `MaxAttempts`, `StagedDigest`, `Arm`, `GiveBack`, `RunOnTrial`.
- `test_check_image_root.py`: a new test for the arm line.
- `test_vm_drill.py`:
  - `BootCauseCase1.run_with` unpacks two results, as `boot_cause_case1` now makes two checks, and keeps asserting the first's name; a new test for the count.
  - The order test gains `drill.case1_power_cuts()` between case 1's record and case 2b (stricter).
  - `Verdict`'s expected set gains the two new checks, as each earlier check did; new class `RollbackRule`.
