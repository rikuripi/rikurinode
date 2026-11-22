# Build Record — case 3b on the node's own grubenv write, so #155's fix is proven (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/grubenv-flush` (draft PR #155), the fix's branch: the case proves that fix and lands with it; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at the end) |
| **Status** | IN PROGRESS |
| **Change type** | test (the drill), then the fix restored |

## Intent: the owner's words

- **"Next"** (2026-11-22), after #155 ended BLOCKED (`docs/build-records/2026-11-21-grubenv-flush.md`). That report's Next: replace case 3b with the node's own lone write, a cut at 3 s, red without the fix, then the fix restored; and record the file's blocks around greenboot's two writes.

## Why

- Through greenboot's two writes, GRUB read the new grubenv after a cut even with no flush (runs 44972841610, 44974871058, 44977046574), so case 3b could not fail for the defect.
- A lone `grub2-editenv` write was read stale by GRUB after a cut at 1–30 s, 12 of 12 (`docs/build-records/2026-11-21-grubenv-power-cut-experiment.md`). The node's clear and give-back are lone writes.

## Design

- **Case 3b, new:** a power cut seconds after the node's own write, the clear, made by the node's program itself (`greenboot-unapplied-update`, no arguments), not a stand-in:
  1. greenboot's check held at the next boot (`hold_first`);
  2. a baseline written as the node writes (`remount,rw`, the write, `remount,bind,ro`): `boot_counter=3`, `boot_success=0`, and the rollback trigger `greenboot_next_deployment_id` set to an image digest no deployment has;
  3. the baseline and the hold made durable: `fsfreeze -f /boot; fsfreeze -u /boot` (the first experiment's baseline flush);
  4. `filefrag -v` of grubenv;
  5. the node's program run once over SSH. It finds the update never applied and clears it: one `edit_grubenv` write that unsets the trigger and the counter, then (with the fix) the flush;
  6. `filefrag -v` again, then the power cut at once (a few seconds after the write);
  7. at the held boot, `boot_counter` as GRUB left it.
- **Pass:** no `boot_counter` at the held boot (GRUB read the clear); the program logged its clear; no flush failure logged since the install; the cut within 8 s of the program's end; and `rikuri-grubenv-flush.service` ran with success at the boot before the cut (greenboot's path, as before).
- **Fail, the defect:** `boot_counter=2`. GRUB read the grubenv from before the clear, counted 3 to 2 and saved it in the file's old block.
- **Evidence only, not a check:** at the boot after the cut, `filefrag -v` of grubenv at the start and the end of greenboot's check (a probe drop-in: `ExecStartPre=-` and `ExecStartPost=-`), to test whether greenboot's second write puts the file back on its home block (#155's record, derived).
- **Safety in the VM:** GRUB counts from 3 at most once: no fallback. After the held boot, the node's pre-check clears a trigger left by a stale read, as it does on a node.
- **Removed:** the old case 3b (the arm read through greenboot's writes), its `ARM_3B` and its two-probe reading.

## Task Contract

1. **Outcome:** #155's fix is proven on the write it protects: after a power cut seconds after the node's own grubenv write, GRUB reads that write.
2. **Scope:** high-risk (the rollback path; BUILD-PROCEDURE, "Risk tiers").
   - `image/drill/vm_drill.py` and `image/tests/test_vm_drill.py`: case 3b replaced as designed above.
   - Restoring the fix: `git revert d3b9f4d` (the fix's code exactly as `ae10134`).
   - This record, and #155's record, a pointer to it.
   - **Not included:** any change to the fix's code, greenboot, or the image; the give-back path in a case of its own; the reason greenboot's writes are read (the `filefrag` lines are evidence for the backlog); N2 and the other backlog items.
3. **Done when:**
   - Red: the new case committed with the fix still reverted and seen failing in CI on `boot_counter 2`. A Fail for another reason alone is not the red.
   - Then the fix restored in its own commit; the full gate passes in CI; the image workflow's drill passes, case 3b included, with cases 1, 1b, 2b, 2d, 2e and 3 as before.
   - One verifier pass on the case and the restore, with hand mutations (high-risk).
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`. The tests and the drill run in CI only. Commit and push `stage1/grubenv-flush`; #155 stays a draft; the owner merges. Download a run's `drill-evidence` only with the owner's yes.
5. **Limits:** one task, a newly authorized follow-up to #155: two repair cycles and two review rounds, renewed. No budget is configured; VM time is reported.

## Evidence log
