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

- **Clarified before any code (2026-11-22), against the first draft of this design, which used the node's clear:** after a cut, e2fsck replays the journal, so Linux always reads the **new** grubenv. When GRUB reads the old one and counts, it saves into the file's old block, which Linux no longer reads. So a stale read is invisible to Linux unless the new grubenv makes GRUB count and the old one does not: the write must **set** the counter, as the first experiment's did (stale: 3; read: 2).
  - The clear unsets the counter, so it could not show the defect; nor could #155's case 3b, whose greenboot write unsets it (see "What this corrects" below).
- **Case 3b, new:** a power cut seconds after a grubenv write made by the node's own `edit_grubenv`, the function its clear, arm and give-back use, loaded from the node's program and called over SSH, with the flush the fix adds:
  1. greenboot's check held at the next boot (`hold_first`);
  2. a baseline written as the node writes (`remount,rw`, the write, `remount,bind,ro`): `boot_counter` and `boot_success` unset;
  3. the baseline and the hold made durable: `fsfreeze -f /boot; fsfreeze -u /boot` (the first experiment's baseline flush);
  4. `filefrag -v` of grubenv;
  5. `edit_grubenv` sets `boot_counter=3 boot_success=0`, as the arm writes it;
  6. `filefrag -v` again, then the power cut at once;
  7. at the held boot, `boot_counter` as Linux reads it.
- **Pass:** `boot_counter=2` at the held boot (GRUB read the write and counted in its block); the write returned 0; no flush failure logged since the install; the cut within 8 s of the write; and `rikuri-grubenv-flush.service` ran with success at the boot before the cut (greenboot's path, as before).
- **Fail, the defect:** `boot_counter=3`. GRUB read grubenv as it was before the write, with no counter, and did not count.
- **Safety in the VM:** GRUB counts from 3 at most once: no fallback. After the held boot greenboot's check passes and unsets the counter.
- **Removed:** the old case 3b (the arm read through greenboot's writes), its `ARM_3B`, its probe drop-in and its two-probe reading.

## What this corrects (#155's record)

- #155's case 3b after repair 1: greenboot's write unsets the counter. A stale GRUB counts 2 to 1 in the old block; Linux reads the new grubenv, with no counter, either way. So "GRUB read greenboot's write" in runs 44972841610, 44974871058 and 44977046574 is **not** shown: the case could not tell. The derived explanation there (greenboot's second write back on the home block) has no evidence behind it.
- Whether greenboot's writes are read after a cut: Not yet proven; this task does not test it. The fix flushes after them all the same.

## Task Contract

1. **Outcome:** #155's fix is proven on the write it protects: after a power cut seconds after the node's own grubenv write, GRUB reads that write.
2. **Scope:** high-risk (the rollback path; BUILD-PROCEDURE, "Risk tiers").
   - `image/drill/vm_drill.py` and `image/tests/test_vm_drill.py`: case 3b replaced as designed above; `counter_held_first` split so the case reads the held boot's whole grubenv (no change in behaviour).
   - Restoring the fix: `git revert d3b9f4d` (the fix's code exactly as `ae10134`).
   - This record, and #155's record: a pointer to it and the correction above.
   - **Not included:** any change to the fix's code, greenboot, or the image; the give-back path in a case of its own; the reason greenboot's writes are read (the `filefrag` lines are evidence for the backlog); N2 and the other backlog items.
3. **Done when:**
   - Red: the new case committed with the fix still reverted and seen failing in CI on `boot_counter 3`. A Fail for another reason alone is not the red.
   - Then the fix restored in its own commit; the full gate passes in CI; the image workflow's drill passes, case 3b included, with cases 1, 1b, 2b, 2d, 2e and 3 as before.
   - One verifier pass on the case and the restore, with hand mutations (high-risk).
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`. The tests and the drill run in CI only. Commit and push `stage1/grubenv-flush`; #155 stays a draft; the owner merges. Download a run's `drill-evidence` only with the owner's yes.
5. **Limits:** one task, a newly authorized follow-up to #155: two repair cycles and two review rounds, renewed. No budget is configured; VM time is reported.

## Evidence log

### The new case 3b (red: the fix still reverted at `d3b9f4d`)

- `vm_drill.py`:
  - case 3b as designed: `BASELINE_3B`, `FREEZE`, `FILEFRAG`, `NODE_PROGRAM`, `NODE_WRITE` (the node's `edit_grubenv`, loaded from its program with `importlib`, so its `__main__` block does not run; its exit echoed as `rc=N`);
  - `case3b_result(held, said, flush_state, failures, since)`: Pass on `boot_counter 2` at the held boot, `rc=0` as the write's last line, greenboot's flush unit active with success before the cut, no flush failure, a cut within `CUT_WITHIN_S` (8 s) of the write, timed on the drill's side;
  - `counter_held_first` split: the waits and the read move to `grubenv_held`, which returns the whole list; `counter_held_first` returns its `boot_counter` as before;
  - removed with the old case: its probe drop-in, `ARM_3B`, `grubenv_value` and `seconds_since` (unused now).
- **Reasons for the test changes (`test_vm_drill.py`):**
  - `Case3b` rewritten for the new reading. The old one passed on a reading that could not show a stale GRUB (see "What this corrects"). New: 3 fails (the defect), and so does any other counter or none; the write's `rc=0` must be its last line; the flush, failure-line and timing tests kept, now with 8.0 and 0.0 passing and 8.1 failing.
  - The probe drop-in's test and `ARM_3B`'s test removed with what they tested. New: `test_case_3b_writes_as_the_node_writes` pins the commands, and `test_case_3b_s_write_is_python_that_calls_the_node_s_function` parses the inner Python and checks that the program still defines `edit_grubenv`, `read_mountinfo` and `default_run` with the signatures it calls.
  - `test_grubenv_value` and `test_seconds_since` removed with their helpers.
  - The check's name in `EXPECTED` changes with the case.
- On the Mac: both files parse; the inner Python of `NODE_WRITE` parses; `git diff --check` clean. The tests run in CI.
- **Expected in CI on this commit:** the full gate fails the 18 flush tests, as at `404b14d` (the fix is reverted); the drill fails case 3b on `boot_counter 3`.

### The red run, `0969b30`: Fail on `boot_counter 3`, as expected

- The image workflow, [run 44980095991](https://github.com/rikuripi/rikurinode/actions/runs/44980095991), from the job's log; the artifact was not downloaded. Case 3b, the drill's only Fail:
  - `GRUB read the node's write: False (boot_counter 3 at the held boot; 3: GRUB read grubenv as before the write)`;
  - `the write returned 0: True`; `no flush failure logged since the install: True`; `cut 0.2s after the node's write: True`;
  - `greenboot's flush ran before the cut: False`: the fix's unit is not in this image (reverted), as expected.
  - Cases 1, 1b, 2b, 2d, 2e and 3 passed, as did every other check.
- `CI`, [run 44980096048](https://github.com/rikuripi/rikurinode/actions/runs/44980096048): `Full gate (Ubuntu)` failed with `FAILED (failures=8, errors=10)`, the 18 flush tests, as at `404b14d`; nothing else failed.
- **So the red is observed:** without the flush, GRUB read grubenv as it was before the node's own write, after a power cut 0.2 s later. This is the defect, seen through the node's real code.

### The fix restored, `f2aa2a5`: Pass

- `f2aa2a5` reverts `d3b9f4d`; its six files are identical to `ae10134` (`git diff ae10134 f2aa2a5` on them is empty).
- `CI`, [run 44986918090](https://github.com/rikuripi/rikurinode/actions/runs/44986918090): `Full gate (Ubuntu)` Pass.
- The image workflow, [run 44986918042](https://github.com/rikuripi/rikurinode/actions/runs/44986918042): every job Pass; the drill took about 12 minutes of VM time. From the job's log (the artifact was not downloaded):
  - case 3b: `GRUB read the node's write: True (boot_counter 2 at the held boot …)`; the write returned 0; greenboot's flush ran before the cut; no flush failure logged since the install; the cut 0.2 s after the write;
  - cases 1, 1b, 2b, 2d, 2e, 3, 4 and 5 Pass, as before.
- **So:** with the same cut 0.2 s after the same write, the read moved from 3 (no fix) to 2 (the fix). One run each: the method's experiment had 2 of 2 per flush, the first experiment 12 of 12 stale without one.
