# Build Record — two more checks on the suggestion lock

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/suggest-lock-tests`, from `main` at `392940d`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | test |

## Intent: the owner's words

- "Next" (2026-11-14), answering the proposed task: the verifier's two test-only follow-ups, nits 2 and 3 in `docs/build-records/2026-11-13-suggest-one-at-a-time.md`:
  - "The 401 check relies on the anonymous request arriving within the 2 s hold."
  - "No test shows the lock let go after a 503 or a timeout; it is released by drop."

## Task Contract

1. **Outcome:** the tests show, rather than assume, that the anonymous request came while a suggestion ran, and that a refused suggestion lets the lock go.
2. **Scope:** routine. Only test code changes; the node's behaviour does not.
   - `control-plane/crates/rikuri-control/tests/rename.rs`:
     - `a_second_suggestion_while_one_runs_is_refused`: after the anonymous request, one more signed-in request must still get 429. So the lock was held across the anonymous one, and a 401 there means the session check comes first.
     - `a_suggestion_resolved_cannot_give_is_refused`: after the 503, a second suggestion must get 503 again, not 429. So the error path lets the lock go.
   - **Not included:**
     - the 30 s timeout path: it returns through the same `Err` arm as the 503, and a test of it would wait 30 s;
     - any change to `src/`.
3. **Done when:**
   - Both tests pass in CI's full gate; the mutants run and the OS image pass.
   - Each new assertion fails against a mutant that the old tests let through, reasoned by the verifier (the Rust tests do not run on the Mac):
     - the lock taken before `authenticate`, with the anonymous request landing after the hold (the timing the old test assumed);
     - the guard kept past the end of the function on the error path (`std::mem::forget(_one)` before the 503).
   - One verifier pass (the change is test code).
4. **Authority:** this file and `tests/rename.rs`. On the Mac, `scripts/cargo.sh` fmt, clippy and check. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log
