# Build Record — case 3b fails when the flush after its own write fails (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/case3b-own-flush-failure`, from `b8e6d1a`, the head of PR #155, which the owner merged into `main` (`40b128e`) while this contract was being written; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at the end) |
| **Status** | IN PROGRESS |
| **Change type** | defect fix in the drill (test tooling) |

## Intent: the owner's words

- **"Next"** (2026-11-22), after `docs/build-records/2026-11-22-grubenv-flush-node-write.md` ended DONE. Its Next: case 3b also fails when the node's write prints `FAILED`, so a failed flush after the case's own write is seen (the verifier's nit 1).

## The defect

- `edit_grubenv` logs a failed flush (`FAILED to write grubenv's journal home …`) to stdout and keeps the write's result, so it returns 0.
- Case 3b runs it over SSH: that line reaches the case's `said`, not the journal its `FLUSH_FAILED` search reads. `case3b_result` checks only that `said` ends in `rc=0`.
- So a failed flush after the case's own write passes the checks on `said` and the journal; only the counter's 2 stands against it.

## Task Contract

1. **Outcome:** case 3b fails, and says why, when the flush after its own write fails, so the drill's Pass shows that flush worked rather than only implying it.
2. **Scope:** routine (test tooling; the rollback path's code is untouched).
   - `image/drill/vm_drill.py`: `case3b_result` also requires no `FAILED` line in `said`, shown in its detail.
   - `image/tests/test_vm_drill.py`: a red test first; the comment on `test_the_failures_it_greps_are_both_programs` corrected (the node's line reaches the journal only when the node runs as a service).
   - This record.
   - **Not included:** the verifier's other nits (timing, orchestration tests); the fix's code; greenboot; the image.
3. **Done when:**
   - Red: the test committed alone and seen failing in CI's full gate on exactly that test.
   - Then the fix in its own commit; the full gate passes in CI; the image workflow's drill passes, case 3b included.
   - One verifier pass on the test and the fix.
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`. The tests run in CI only. Commit and push this branch; a draft PR to `main`; the owner merges. One `verifier` pass, required for code by AGENTS.md §5 (corrected 2026-11-22: this contract first said none was required, which §5 does not allow).
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; VM time is reported.

## Evidence log

### Red

- `Case3b.test_a_failed_flush_after_the_write_fails`: `said` with the node's `FAILED to write grubenv's journal home` line, then `rc=0`, must fail, and the detail must say so.
- **Reason for the test change:** a new test for the defect; no existing test changes. Expected in CI: the full gate fails on this test alone.

### The red run, `c93978d`: Fail on that test alone, as expected

- `CI`, [run 44996441795](https://github.com/rikuripi/rikurinode/actions/runs/44996441795): `Full gate (Ubuntu)` failed with `FAILED (failures=1)`, in `test_a_failed_flush_after_the_write_fails` alone:
  `AssertionError: True is not false : GRUB read the node's write: True (boot_counter 2 …); the write returned 0: True; …`: the case passed with the node's failed-flush line in `said`, the defect.
- The image workflow, [run 44996441759](https://github.com/rikuripi/rikurinode/actions/runs/44996441759): every job Pass, case 3b included (nothing in the VM changed).

### The fix

- `case3b_result` (`image/drill/vm_drill.py`) also requires no line of `said` to hold `FAILED` (`clean`), and its detail says `no FAILED line from the node's write: …`. Its docstring says why the journal cannot show that line over SSH.
- Nothing else in the drill changes: `said` was already captured and kept.
- **Reason for the test change (`test_vm_drill.py`):** the comment on `test_the_failures_it_greps_are_both_programs` said the journal holds the node's failed-flush line; it does only when the node runs as a service. Comment only; the test is unchanged.
