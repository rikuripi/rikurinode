# Build Record — journal_search returns None when case 3b's search did not run (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/journal-search-none`, from `main` at `876d925`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `b67af4f` (contract), `3e07de7` (red), `d54de73` (the change), `a3abe58` (record): PR #163, merged by the owner at `a3abe58` (`b063c12`) before the verifier's pass; this record's last commit on `docs/journal-search-none-record`, a docs-only PR |
| **Status** | DONE |
| **Change type** | test tooling: a safety rule moved from an untested line into a tested function |

## Intent: the owner's words

- **"Next"** (2026-11-22), after `docs/build-records/2026-11-22-case3b-journal-search.md` ended DONE. Its Next: `journal_search` returns `None` when the search did not run, so a unit test holds the one line that turns "not searched" into a Fail (that record's verifier, nit 1).

## The gap

- `journal_search(out)` returns `(matches, searched)`. `Drill.case3b` turns it into `case3b_result`'s input with `failures if searched else None` (`image/drill/vm_drill.py`).
- That expression is the only place where "not searched" becomes a Fail. Changing it to `failures` brings back #161's defect (a search that did not run reads as clean), and no test fails: the verifier's surviving mutant. `Drill.case3b` runs only in the VM, and a green drill shows only the searched path.
- No behaviour is wrong today; the rule is unguarded.

## Design

- `journal_search(out)` returns the matches (`""` when none) when the search ran, and `None` when it did not: the same input `case3b_result` already takes (`failures=None`: not searched).
- `Drill.case3b`: `failures = journal_search(searched_out)`, passed to `case3b_result` as it is: no condition at the call site. (This line first said nothing was left there to get wrong; the verifier found an added line can still undo it, see Verification.)
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
  - `test_case_3b_runs_its_search_through_journal_search`: tightened. It also requires `failures = journal_search(searched_out)` and `case3b_result(held, said, state, failures, since)`, so those two lines cannot carry a fallback or a condition. It does not rule out a line added between them (corrected after the verifier's nit 1).
  - New, `Case3b.test_a_search_that_did_not_run_fails_the_case_end_to_end`: for each not-searched output, `case3b_result(…, journal_search(out), …)` fails, with `the journal searched: False`; and `rc=1` alone passes.
- Expected in CI: the full gate fails on these tests alone, with the old code's tuple.

### The red run, `3e07de7`: Fail on the changed and new tests alone, as expected

- `CI`, [run 45061623521](https://github.com/rikuripi/rikurinode/actions/runs/45061623521): `Full gate (Ubuntu)` failed with `FAILED (failures=11, errors=6)` in its step 3 of 11 (the image tests), nothing else in that step; steps 4 to 11 were not reached:
  - `JournalSearch`: the old tuple, e.g. `AssertionError: ('', False) is not None` and `('a FAILED line\nanother', True) != 'a FAILED line\nanother'`;
  - the source check: `'failures = journal_search(searched_out)\n' not found`;
  - `Case3b.test_a_search_that_did_not_run_fails_the_case_end_to_end`: `AttributeError: 'tuple' object has no attribute 'splitlines'`, the old tuple given to `case3b_result`.
- The image workflow, [run 45061623539](https://github.com/rikuripi/rikurinode/actions/runs/45061623539): Pass (nothing in the VM changed).

### The change

- `image/drill/vm_drill.py`: `journal_search` returns the matches or `None`; `Drill.case3b` assigns `failures = journal_search(searched_out)` and passes it on as it is; both docstrings say so. The command, `case3b_result`'s logic and the kept output are unchanged.
- No test changes after the red.

### The change, `a3abe58`: Pass

- `CI`, [run 45064722187](https://github.com/rikuripi/rikurinode/actions/runs/45064722187): `Full gate (Ubuntu)` Pass, `full-gate: all 11 steps passed`.
- The image workflow, [run 45064722229](https://github.com/rikuripi/rikurinode/actions/runs/45064722229): every job Pass; the drill took about 12 minutes of VM time. Case 3b, from the job's log (the artifact was not downloaded): `… the journal searched: True; no flush failure logged since the install: True; /boot read-only again after every write: True; …`.

## Verification

- **The verifier**, one pass on `876d925..a3abe58` (routine), after the merge: **Pass**, no Important findings.
  - The gap confirmed: at `876d925` only the call site's `failures if searched else None` turned "not searched" into a Fail, and no test held it.
  - No behaviour change, observed: the old and the new path give the same verdict and detail on 972 input combinations (the old and new modules side by side in a scratch copy); `journal_search` has no other caller.
  - The test changes: every input kept, `assertFalse(…[1])` become the stricter `assertIsNone`, no test changed after the red.
  - Hand mutations (`Case3b` and `JournalSearch` only, no `PATH`, no Docker socket): every named mutant killed, the last verifier's survivor among them in its new form (`… or ""` at the call: killed by the source check). Two survive: `ends[0]` (equivalent on reachable input, already listed) and a line `failures = failures or ""` added between the call and `case3b_result`.
  - The CI quotes confirmed.
- **Minor findings, for the backlog, not fixed here:**
  1. The added-line survivor: the source check holds the two lines as written, not that nothing comes between them; the record's two claims are corrected above. Suggested: an `ast` check that `Drill.case3b` assigns `failures` once.
  2. The red run's "nothing else": qualified above (the gate stops at its first failing step).

## Result

- **Pass (observed):** `journal_search` returns `None` when the search did not run, and a unit test composing it with `case3b_result` holds that such a search fails case 3b (red: gate run 45061623521; green: gate 45064722187, drill 45064722229). What case 3b passes or fails on is unchanged.
- **Not yet proven:** that no edit of `Drill.case3b` can undo it; only the source check and the VM run hold that method.
