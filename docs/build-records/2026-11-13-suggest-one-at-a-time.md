# Build Record — one free-name suggestion at a time

| | |
|---|---|
| **Date** | 2026-11-13 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/suggest-bound`, from `main` at `346bdae`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
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
