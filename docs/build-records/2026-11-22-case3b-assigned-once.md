# Build Record — a test that case 3b's search result is assigned once, from its source (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/case3b-assigned-once`, from `main` at `562fc97`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at the end) |
| **Status** | IN PROGRESS |
| **Change type** | test only: coverage for a rule only the VM runs |

## Intent: the owner's words

- **"Next"** (2026-11-22), after `docs/build-records/2026-11-22-journal-search-none.md` ended DONE. Its Next: an `ast` check that `Drill.case3b` assigns `failures` once, from `journal_search` (that record's verifier, nit 1).

## The gap

- `Drill.case3b` (`image/drill/vm_drill.py`) runs the search and reads it in two lines: `searched_out = self.vm(CASE3B_SEARCH, check=False)`, then `failures = journal_search(searched_out)`. The source check pins those lines as written.
- A line added after either one passes every test and brings back #161's defect, a search that did not run read as clean:
  - `failures = failures or ""` (the verifier's survivor);
  - `searched_out = searched_out or "rc=1"`, the same hole one step earlier (found while writing this contract).
- `Drill.case3b` runs only in the VM, and a green drill takes only the searched path.

## Design

- A test parses `Drill.case3b`'s source with `ast` and requires, for each of `searched_out` and `failures`, exactly one place where the name is bound (any `Name` node not read: an assignment, an augmented one, a walrus, a `for` or `with` target, a `del`), and that place to be the plain assignment from its source: `self.vm(CASE3B_SEARCH, check=False)` and `journal_search(searched_out)`.
- **The test's own red:** no code changes, so the test passes on the code as it is, and a test commit on its own cannot fail. Instead the same test runs its check on two copies of the source with the mutations above inserted, and requires each copy to be rejected. So its power is shown in every gate run, not once.
- **Not changed:** `vm_drill.py`; the other tests; the other nits.

## Task Contract

1. **Outcome:** no added line in `Drill.case3b` can turn a search that did not run into a clean one without the gate failing.
2. **Scope:** routine (a test only).
   - `image/tests/test_vm_drill.py`: one new test in `JournalSearch`.
   - This record.
   - **Not included:** any change to `vm_drill.py`; the other open nits (`&&` and `|| exit 1` held only by the VM; the kept output's label; the redirect residual).
3. **Done when:**
   - The full gate passes in CI with the new test; the image workflow passes, case 3b with `the journal searched: True`.
   - One `verifier` pass (AGENTS.md §5), with the two mutations above applied to `vm_drill.py` itself in a scratch copy and seen to fail the test.
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`. The tests run in CI only. Commit and push this branch; a draft PR to `main`; the owner merges.
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; VM time is reported.

## Evidence log

### The test

- `JournalSearch.test_case_3b_binds_its_search_result_once_from_its_source`, with the reason above (new coverage; no existing test changes).
