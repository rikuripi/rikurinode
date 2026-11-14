# Build Record — one free-name suggestion at a time

| | |
|---|---|
| **Date** | 2026-11-13 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/suggest-bound`, from `main` at `346bdae`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `f18af0e` (contract), `8862779` (red), `50c7eba` (fix); merged as `1d186a3` (#100) |
| **Status** | DONE |
| **Change type** | fix |

## Intent: the owner's words

- "Next" (2026-11-13), answering the proposed task: "limit how many free-name suggestion requests the node handles at once". It is backlog from 5c.4b-2's verifier: "the suggestion route has no bound on concurrent requests" (`docs/build-records/2026-11-13-5c4b2-naming-page.md`).
- The owner's choice, 2026-11-13: "Refuse it (Recommended)". While a suggestion runs, another one is answered 429 "a suggestion is already being checked" at once. The page already shows its "could not check" hint for any answer but a suggestion, and the owner may type a name.

## Task Contract

1. **Outcome:** however many suggestion requests arrive together, the node asks resolved about one name at a time and holds no queue of waiting requests.
2. **Scope:** high-risk, because it changes a signed-in route's answers.
   - Files:
     - `control-plane/crates/rikuri-control/src/http.rs`: `Inner` gains `suggest_lock: tokio::sync::Mutex<()>`. `suggestion` takes it with `try_lock` after `authenticate`, so a request without a session still gets 401 and never learns whether a check runs. It holds the guard to the end, and refuses with 429 when the lock is taken.
     - `tests/rename.rs` and `tests/common/bus.rs`: one more stand-in mode, `Lookups::Slow(d)`, in which every name is free after `d`. Plus the test below.
     - `README.md`: one sentence on the route.
   - **Not included:**
     - the page: its handling of a non-`ok` answer already fits;
     - the rename route: it has its own lock;
     - any limit across sessions or over time.
3. **Done when:**
   - `a_second_suggestion_while_one_runs_is_refused` passes in CI, after being seen failing on the current code (a red commit, pushed alone). It shows:
     - while the first suggestion's lookup is held, a second gets 429 with the exact words, and resolved is asked nothing more;
     - a request without a session still gets 401;
     - the first ends 200 `rikuri01`;
     - a third, after it, gets 200: the lock is let go.
   - The full gate, the mutants run and the OS image drills pass in CI.
   - The verifier passes, with hand mutations: no lock; the guard dropped at once (`let _ =`); the lock taken before `authenticate`; the status changed.
4. **Authority:**
   - These files.
   - On the Mac, `scripts/cargo.sh` check, clippy and fmt. The Rust tests run in CI.
   - Commit, push this branch, and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Red (the current code)

- `tests/common/bus.rs`: `Lookups::Slow(d)` records the lookup, waits `d`, then answers NXDOMAIN.
- `tests/rename.rs`: `a_second_suggestion_while_one_runs_is_refused`. It joins the first suggestion with a second request, sent once the stand-in has seen the first lookup. The wait for that lookup is bounded at 10 s.
- **Expected on the current code:** the second is not refused. It runs beside the first and ends 200, so `assert_eq!(second.status, 429…)` fails.
- On the Mac: fmt and clippy (all targets, `-D warnings`) are clean. Pushed alone, so CI shows the red before the fix.

### CI on `8862779` (the red): Fail, as expected

- `Full gate (Ubuntu)`, [run 43550401872](https://github.com/rikuripi/rikurinode/actions/runs/43550401872):
  - `test a_second_suggestion_while_one_runs_is_refused ... FAILED`, panicked at `tests/rename.rs:524:5` (`assert_eq!(second.status, 429, …)`), with `left: 200`, `right: 429`;
  - the other tests passed: `test result: FAILED. 21 passed; 1 failed`.
- Rust mutants [43550401797](https://github.com/rikuripi/rikurinode/actions/runs/43550401797) and the OS image [43550401826](https://github.com/rikuripi/rikurinode/actions/runs/43550401826) passed.

### Fix

- `src/http.rs`: `Inner.suggest_lock`. In `suggestion`, after `authenticate`:
  `let Ok(_one) = app.0.suggest_lock.try_lock() else { return Err(refuse(429, "a suggestion is already being checked")) };`
  - The guard is bound to `_one`, not `_`, so it is held until the function returns, on every path.
- `README.md`: one suggestion at a time; another gets 429.
- No test changed after red.
- On the Mac: fmt and clippy (all targets, `-D warnings`) are clean.

### CI on `50c7eba` (the fix): Pass

- `Full gate (Ubuntu)`, [run 43551496243](https://github.com/rikuripi/rikurinode/actions/runs/43551496243): `test a_second_suggestion_while_one_runs_is_refused ... ok`; `tests/rename.rs` `22 passed; 0 failed`.
- Rust mutants, [run 43551496190](https://github.com/rikuripi/rikurinode/actions/runs/43551496190): `4 mutants tested … 4 unviable`. All four replace the body of `http.rs:691` and fail to build (`E0599`, `E0283`), so there was nothing to catch.
- OS image, [run 43551496217](https://github.com/rikuripi/rikurinode/actions/runs/43551496217): passed.
- The owner merged #100 at `50c7eba` (as `1d186a3`) before the verifier ran.

### The verifier, at `50c7eba`: PASS

- **The fix:** the guard is held until `suggestion` returns, on every path (the `own_uid()?` return, the 503, the 30 s limit). The lock is taken after `authenticate`. `try_lock` never waits.
- **The test:** unchanged between the red and the fix (`git diff 8862779 50c7eba -- control-plane/crates/rikuri-control/tests` is empty). It cannot pass vacuously: the 10 s wait panics if no lookup comes, and `asked` and the third 200 pin the rest. A runner stall over 2 s would show as a failure, never a false pass.
- **Hand mutations, reasoned against the test** (the Rust tests do not run on the Mac):
  | Mutant | Killed by |
  |---|---|
  | no lock | `second.status == 429` (the red run) |
  | the guard dropped at once (`let _`) | `second.status == 429` |
  | the lock before `authenticate` | `anonymous.status == 401` |
  | another status | `second.status == 429` |
  | other words | `second`'s JSON body |
  | `lock().await` (waits in line) | `second.status == 429` |
  | `drop(_one)` before the lookup | `second.status == 429` |
  | `drop(_one)` after the lookup | survives; it behaves the same |
- `git diff --check` and `fmt --check` are clean.
- **Findings:** no Important finding. Nits, not fixed:
  1. this close-out (answered here);
  2. the 401 check relies on the anonymous request arriving within the 2 s hold;
  3. no test shows the lock let go after a 503 or a timeout; it is released by drop;
  4. one session can keep others refused for up to 30 s per request, which the contract leaves out ("any limit across sessions or over time").

### Close-out

- **Done when:** met. The test was seen red in CI, then green; the gate, the mutants run and the OS image passed; the verifier passed.
- **Repairs:** 0. Review rounds: 1.
- **Used:** no budget is configured. Two CI pushes and one verifier pass.
- **Backlog, not started:** the verifier's nits 2 and 3, as test-only follow-ups.
