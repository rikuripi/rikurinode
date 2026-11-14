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
