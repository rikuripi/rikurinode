# Build Record — case 3b fails when its journal search could not run (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/case3b-journal-search`, from `main` at `41ab20d`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at the end) |
| **Status** | IN PROGRESS |
| **Change type** | defect fix in the drill (test tooling) |

## Intent: the owner's words

- **"Next"** (2026-11-22), after `docs/build-records/2026-11-22-case3b-boot-left-writable.md` ended DONE. Its Next: case 3b's journal search tells "no match" from a `journalctl` error, so a search that could not run fails the case instead of passing as clean (that record's verifier, nit 2).

## The defect

- Case 3b's search, `self.vm("journalctl … --grep \"…\"", check=False) or ""`: `vm()` returns `None` for any non-zero exit, and `or ""` makes it the empty text of a clean search.
- So a `journalctl` that failed (a pattern it cannot compile, a journal it cannot open, a lost SSH connection) reads as "no flush failure logged" and "/boot read-only again", and case 3b passes on a search that never ran. AGENTS.md > Design rules: "Nothing important fails silently."
- The exit code alone cannot tell the two apart: `journalctl` exits 1 on an error, and with `--grep` may exit 1 when nothing matches too. Its errors go to standard error; its matches, with `-q`, are all it writes to standard output.

## Design

- `CASE3B_SEARCH`, the case's command: the same `journalctl -q --no-pager -o cat --grep "<CASE3B_JOURNAL>"`, its standard error to a temporary file, then `rc=N` and each standard-error line as `stderr: …`, the file removed. Its own exit is the `echo`'s, so `vm()` returns the output whenever SSH worked.
- `journal_search(out) -> (text, searched)`, a pure function:
  - `searched` only when the output holds an `rc=` line, that code is 0 or 1, and no `stderr:` line follows it;
  - `text`: the lines before the `rc=` line, the matches.
  - No output (SSH failed): not searched.
- `case3b_result(…, failures, …)`: `failures=None` means the search did not run; the case fails, its detail saying `the journal searched: False`.
- `Drill.case3b` runs `CASE3B_SEARCH`, reads it with `journal_search`, and keeps the raw output in `04-case3b.out`.
- **Risk:** a warning `journalctl` writes to standard error while still searching (for example about a journal file left unclean by the power cut) now fails the case. It fails loudly, with the warning in its detail's kept output; it never passes quietly. If it happens, the owner decides whether such warnings are allowed.
- **Not changed:** the drill's other journal reads. They look for a line that must be there, so a failed read fails them already; case 3b's is the drill's one search for lines that must be absent.

## Task Contract

1. **Outcome:** case 3b passes only when its journal search really ran, so "no flush failure logged" and "/boot read-only again" are observed, not assumed.
2. **Scope:** routine (test tooling; the node's code is untouched).
   - `image/drill/vm_drill.py`: `CASE3B_SEARCH`, `journal_search`, `case3b_result`'s `None`, and the case's search.
   - `image/tests/test_vm_drill.py`: red tests first.
   - This record.
   - **Not included:** the drill's other journal reads; `vm()` itself; other cases.
3. **Done when:**
   - Red: the tests committed alone and seen failing in CI's full gate on exactly those tests.
   - Then the fix in its own commit; the full gate passes in CI; the image workflow's drill passes, case 3b included, with `the journal searched: True`.
   - One `verifier` pass (code; AGENTS.md §5).
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`. The tests run in CI only. Commit and push this branch; a draft PR to `main`; the owner merges.
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; VM time is reported.

## Evidence log

### Red

- New tests:
  - `Case3b.test_a_journal_search_that_did_not_run_fails`: `failures=None` must fail, with `the journal searched: False`; the passing case says `True`.
  - `JournalSearch` (new class): `journal_search` on matches then `rc=0`; on `rc=1` alone; on `rc=2`; on `rc=1` with a `stderr:` line; on no `rc=` line; on `None`.
  - `JournalSearch.test_case_3b_runs_its_search_through_journal_search`: `CASE3B_SEARCH` holds `--grep "<CASE3B_JOURNAL>"`, `-q`, its standard error kept apart, then `rc=$?`; and `Drill.case3b`'s source uses `CASE3B_SEARCH` and `journal_search(`. This also covers the last verifier's survivor (the case's call reverted to another pattern).
- **Reason for the test change:** new tests for the defect; no existing test changes. Expected in CI: the full gate fails on these tests alone (the `JournalSearch` ones with an `AttributeError`, the function and the command not yet defined).

### The red run, `3154ced`: Fail on the new tests alone, as expected

- `CI`, [run 45054978851](https://github.com/rikuripi/rikurinode/actions/runs/45054978851): `Full gate (Ubuntu)` failed with `FAILED (failures=1, errors=11)`, nothing else:
  - `Case3b.test_a_journal_search_that_did_not_run_fails`: `AssertionError: True is not false : …`: the case passed with `failures=None`, the defect;
  - the four `JournalSearch` tests: `AttributeError: module 'vm_drill' has no attribute 'journal_search'` (and `'CASE3B_SEARCH'`), 11 errors with the subtests.
- The image workflow, [run 45054978938](https://github.com/rikuripi/rikurinode/actions/runs/45054978938): Pass (nothing in the VM changed).

### The fix

- `image/drill/vm_drill.py`, as designed:
  - `CASE3B_SEARCH`: `e=$(mktemp) || exit 1; journalctl -q --no-pager -o cat --grep "<CASE3B_JOURNAL>" 2>"$e"; echo "rc=$?"; sed "s/^/stderr: /" "$e" && rm -f "$e"`. The command's own exit is non-zero (so `vm()` returns nothing, not searched) when the temporary file, the copy or its removal fails.
  - `journal_search`; `case3b_result` with `failures=None` failing, its detail `the journal searched: …`; `Drill.case3b` passing `None` when the search did not run, and keeping the search's raw output in `04-case3b.out`.
- No test changes after the red.
- **On the Mac, beyond the contract's parse checks:** `journal_search` alone, lifted out of the file with `ast`, was called on the tests' inputs in a Python process that started nothing else; and the rendered `CASE3B_SEARCH` was checked with `bash -n` (syntax only, not run). Both passed. Recorded because the contract named only `ast` parse checks; neither is evidence the gate relies on.
