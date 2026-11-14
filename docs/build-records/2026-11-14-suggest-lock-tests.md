# Build Record — two more checks on the suggestion lock

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/suggest-lock-tests`, from `main` at `392940d`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `d12da33` (contract), `3d6f4cf` (change); merged as `8f5a581` (#102) |
| **Status** | DONE |
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

### Change

- `a_second_suggestion_while_one_runs_is_refused`: a signed-in request `still`, sent after the anonymous one inside the same hold, must get 429. `asked` is read after it, so it also shows `still` asked resolved nothing.
- `a_suggestion_resolved_cannot_give_is_refused`: each case now asks twice, and both must be 503 with the same words.
- **Test changes, with their reason:** both only add assertions; none is loosened or removed. They answer the verifier's nits 2 and 3 above.
- On the Mac: fmt and clippy (all targets, `-D warnings`) are clean. The tests run in CI.

### CI on `3d6f4cf`: Pass

- `Full gate (Ubuntu)`, [run 43560035988](https://github.com/rikuripi/rikurinode/actions/runs/43560035988): both tests `ok`; `tests/rename.rs` `22 passed; 0 failed`.
- Rust mutants, [run 43560035985](https://github.com/rikuripi/rikurinode/actions/runs/43560035985): `No mutants to filter`, since only test code changed.
- OS image, [run 43560036014](https://github.com/rikuripi/rikurinode/actions/runs/43560036014): passed.
- The owner merged #102 at `3d6f4cf` (as `8f5a581`) before the verifier ran.

### The verifier, at `3d6f4cf`: PASS

- Only assertions were added; no `src/` change; `git diff --check` and `fmt --check` are clean.
- `still` proves the anonymous request was answered while the first suggestion held the lock. A runner slower than the 2 s hold would make `still` 200, a false red, never a false green. In CI the test took about 3.9 s.
- Asking twice fails with 429 if either 503 case kept the lock.
- **Hand mutations, reasoned:**
  | Mutant | Before | Now |
  |---|---|---|
  | the lock before `authenticate`, the anonymous request inside the hold | killed (`anonymous` 429) | killed |
  | the same, the anonymous request after the hold | survived (a false pass) | killed (`still` 200) |
  | `std::mem::forget(_one)` before the 503 | survived | killed (the second request 429) |
  | the guard kept on the `own_uid()?` error | survives | survives: `own_uid` never fails in the tests |
  | the guard kept when the 30 s limit ends | survives | survives: not covered |
- **Findings:** no Important finding. Nits:
  1. **A correction to the Task Contract's reason** for leaving out the 30 s limit. It said that path "returns through the same `Err` arm as the 503". It does not: `hostname::suggest` ends `timeout(limit, first_free).await.unwrap_or(Ok(None))` (`src/hostname.rs:319-321`, checked), so the limit gives 200 `{"name": null}` through the `Ok` arm. Only a lookup's own 10 s `BUS_TIMEOUT` ends in the 503. The guard is still let go when the function returns, so leaving it out stands; the reason was wrong.
  2. The `own_uid()?` error path cannot be reached in the tests.
  3. This close-out (answered here).

### Close-out

- **Done when:** met. Both tests passed in CI; the gate, the mutants run and the OS image passed; the verifier showed each new assertion kills a mutant the old tests let through.
- **Repairs:** 0. Review rounds: 1.
- **Used:** no budget is configured. One CI push and one verifier pass.
- **For the owner, not started:** when the 30 s limit ends, the page is told "no free name" (200, `null`), not "could not check" (503). Whether that is the right answer is a behaviour question.
