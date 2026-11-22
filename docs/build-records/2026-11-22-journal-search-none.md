# Build Record — journal_search returns None when case 3b's search did not run (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/journal-search-none`, from `main` at `876d925`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at the end) |
| **Status** | IN PROGRESS |
| **Change type** | test tooling: a safety rule moved from an untested line into a tested function |

## Intent: the owner's words

- **"Next"** (2026-11-22), after `docs/build-records/2026-11-22-case3b-journal-search.md` ended DONE. Its Next: `journal_search` returns `None` when the search did not run, so a unit test holds the one line that turns "not searched" into a Fail (that record's verifier, nit 1).

## The gap

- `journal_search(out)` returns `(matches, searched)`. `Drill.case3b` turns it into `case3b_result`'s input with `failures if searched else None` (`image/drill/vm_drill.py`).
- That expression is the only place where "not searched" becomes a Fail. Changing it to `failures` brings back #161's defect (a search that did not run reads as clean), and no test fails: the verifier's surviving mutant. `Drill.case3b` runs only in the VM, and a green drill shows only the searched path.
- No behaviour is wrong today; the rule is unguarded.

## Design

- `journal_search(out)` returns the matches (`""` when none) when the search ran, and `None` when it did not: the same input `case3b_result` already takes (`failures=None`: not searched).
- `Drill.case3b`: `failures = journal_search(searched_out)`, passed to `case3b_result` as it is. Nothing is left at the call site to get wrong.
- A test composes the two pure functions: a failed search's output, read by `journal_search`, fails `case3b_result`. The source check pins the call to pass `journal_search`'s result straight on.
- **Not changed:** `CASE3B_SEARCH`, `case3b_result`, and what case 3b passes or fails on. The other nits of that record (the `&&` and `|| exit 1` survivors, the kept-output label, the redirect residual).

## Task Contract

1. **Outcome:** the rule "a journal search that did not run fails case 3b" is held by unit tests, so it cannot be lost by an edit the VM run would not show.
2. **Scope:** routine (test tooling; the node's code is untouched).
   - `image/drill/vm_drill.py`: `journal_search`'s return, and `Drill.case3b`'s two lines that use it.
   - `image/tests/test_vm_drill.py`: `JournalSearch` changed to the new return (red first), one new test composing the two functions, and the source check tightened.
   - This record.
   - **Not included:** anything listed under "Not changed" above.
3. **Done when:**
   - Red: the tests committed alone and seen failing in CI's full gate on exactly the changed and new tests.
   - Then the change in its own commit; the full gate passes in CI; the image workflow's drill passes, case 3b with `the journal searched: True`.
   - One `verifier` pass (code; AGENTS.md §5), with the hand mutation the last verifier left (the call site) among its mutants.
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`. The tests run in CI only. Commit and push this branch; a draft PR to `main`; the owner merges.
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; VM time is reported.

## Evidence log

### Red

- **Reasons for the test changes (`test_vm_drill.py`):**
  - `JournalSearch`'s three reading tests: `journal_search`'s return changes from `(matches, searched)` to matches or `None`, by design. The inputs are kept; each expected value is the same reading in the new form (`("…", True)` becomes `"…"`, `searched` False becomes `None`). No case is dropped and none loosened.
  - `test_case_3b_runs_its_search_through_journal_search`: tightened. It also requires `failures = journal_search(searched_out)` and `case3b_result(held, said, state, failures, since)`, so the call site cannot add a fallback or a condition.
  - New, `Case3b.test_a_search_that_did_not_run_fails_the_case_end_to_end`: for each not-searched output, `case3b_result(…, journal_search(out), …)` fails, with `the journal searched: False`; and `rc=1` alone passes.
- Expected in CI: the full gate fails on these tests alone, with the old code's tuple.
