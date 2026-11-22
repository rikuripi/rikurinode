# Build Record — case 3b fails when the node leaves /boot writable after a write (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/case3b-boot-left-writable`, from `main` at `17c8645`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at the end) |
| **Status** | IN PROGRESS |
| **Change type** | defect fix in the drill (test tooling) |

## Intent: the owner's words

- **"Next"** (2026-11-22), after `docs/build-records/2026-11-22-case3b-own-flush-failure.md` ended DONE. Its Next: the drill catches a failed remount of `/boot` back to read-only, the `/boot left writable` line, which has no `FAILED` (that record's verifier, nit 2).

## The defect

- `edit_grubenv` (`image/rootfs/usr/libexec/rikuri/greenboot-unapplied-update`) makes `/boot` writable for its write when it is mounted read-only, then remounts it `bind,ro`. When that remount fails it logs `/boot left writable in this unit's mount namespace (remount exit N)` and returns the write's result.
- Case 3b checks the node's write output (`said`) for `FAILED` and the journal for `FLUSH_FAILED`'s two lines. Neither holds `/boot left writable`, so a node that left `/boot` writable passes case 3b.

## Design

- `LEFT_WRITABLE = "/boot left writable"`, the line's fixed start.
- `case3b_result` also fails when `said` or the journal's lines hold it; its detail says `/boot read-only again after every write: …`.
- The case's journal search (`CASE3B_JOURNAL`) is `FLUSH_FAILED` and `LEFT_WRITABLE` together. `no flush failure logged since the install` counts only the lines that are not `LEFT_WRITABLE`'s, so each part of the detail says what it saw.
- **Not changed:** the node's message, the node's code, and every other case.

## Task Contract

1. **Outcome:** case 3b fails, and says so, when the node's write or any logged write left `/boot` writable, so the drill's Pass shows `/boot` was read-only again.
2. **Scope:** routine (test tooling; the node's code is untouched).
   - `image/drill/vm_drill.py`: `LEFT_WRITABLE`, `CASE3B_JOURNAL`, `case3b_result`, and the case's journal search.
   - `image/tests/test_vm_drill.py`: red tests first.
   - This record.
   - **Not included:** changing the node's message to hold `FAILED`; other cases; the earlier verifier's other nits.
3. **Done when:**
   - Red: the tests committed alone and seen failing in CI's full gate on exactly those tests.
   - Then the fix in its own commit; the full gate passes in CI; the image workflow's drill passes, case 3b included.
   - One `verifier` pass (code; AGENTS.md §5).
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`. The tests run in CI only. Commit and push this branch; a draft PR to `main`; the owner merges.
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; VM time is reported.

## Evidence log

### Red

- New tests in `Case3b`:
  - `test_boot_left_writable_by_the_node_s_write_fails`: `said` with another line, then the node's `/boot left writable … (remount exit 32)` line, then `rc=0`, must fail, with `/boot read-only again after every write: False`. The other line first also kills the first-line-only mutant the last verifier left.
  - `test_boot_left_writable_in_the_journal_fails`: the same line in the journal must fail, with `/boot read-only again …: False` and `no flush failure logged since the install: True`.
  - `test_the_case_s_journal_search_holds_both`: `CASE3B_JOURNAL` holds `FLUSH_FAILED`'s lines and `LEFT_WRITABLE`, and `LEFT_WRITABLE` is the start of the node's own message.
- **Reason for the test change:** new tests for the defect; no existing test changes. Expected in CI: the full gate fails on these three tests alone (the third with an `AttributeError`, its constants not yet defined).

### The red run, `9f1ad13`: Fail on the three tests alone, as expected

- `CI`, [run 45047950191](https://github.com/rikuripi/rikurinode/actions/runs/45047950191): `Full gate (Ubuntu)` failed with `FAILED (failures=2, errors=1)`, nothing else:
  - `test_boot_left_writable_by_the_node_s_write_fails`: `AssertionError: True is not false : … no FAILED line from the node's write: True; …`: the case passed with the node's `/boot left writable` line in `said`, the defect.
  - `test_boot_left_writable_in_the_journal_fails`: failed on its detail (`'/boot read-only again after every write: False' not found`), not its verdict: given the line directly, the old `quiet` already failed the case. In the VM the line never reached it, because the journal search did not look for it; `test_the_case_s_journal_search_holds_both` is the test for that.
  - `test_the_case_s_journal_search_holds_both`: `AttributeError: module 'vm_drill' has no attribute 'CASE3B_JOURNAL'`.
- The image workflow, [run 45047950112](https://github.com/rikuripi/rikurinode/actions/runs/45047950112): Pass (nothing in the VM changed).

### The fix

- `image/drill/vm_drill.py`: `LEFT_WRITABLE` and `CASE3B_JOURNAL` (`FLUSH_FAILED`'s lines and `LEFT_WRITABLE`); case 3b's journal search uses `CASE3B_JOURNAL`; `case3b_result` fails when `said` or a journal line holds `LEFT_WRITABLE` (`kept_ro`), says `/boot read-only again after every write: …`, and counts as a flush failure only the journal lines that are not `LEFT_WRITABLE`'s.
- No test changes after the red.
