# Build Record — a suggestion's timeout gets its own log line

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/suggest-timeout-log`, from `main` at `0b19ac4`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `d0cfff0` (contract), `2c28c16` (change); merged as `06b2e64` (#106) |
| **Status** | DONE |
| **Change type** | refactor |

## Intent: the owner's words

- "Next" (2026-11-14), answering the proposed task: "give the timeout its own log message, and have its test check the error's wording". These are nits 4 and 5 of the verifier in `docs/build-records/2026-11-14-suggest-limit-503.md`:
  - "the route logs 'resolved could not say which names are free' for a timeout too";
  - "the timeout test could also assert the 'no answer within' text".

## Task Contract

1. **Outcome:** whoever reads the node's log can tell a suggestion that ran out of time from one that resolved could not answer.
2. **Scope:** routine. The route's answers do not change (both are still 503 with the same words); only the log line and an error type change.
   - `control-plane/crates/rikuri-control/src/hostname.rs`: `suggest`'s error becomes `Unchecked`, with two cases: `Unknown(String)` (which name, and why) and `OutOfTime(Duration)`. Its unit tests then pin the exact case:
     - `the_limit_ends_the_suggestion_unchecked`: `Err(Unchecked::OutOfTime(100 ms))`;
     - `an_unknown_answer_stops_the_suggestion`: `Err(Unchecked::Unknown("rikuri02.local: …"))`, the exact text.
     These replace `assert!(got.is_err())` in both: stricter, and the reason for the test change.
   - `src/http.rs`, `suggestion`: one log line per case. `Unknown` keeps "resolved could not say which names are free"; `OutOfTime` logs "resolved did not answer within the suggestion's time limit", with the limit.
   - A typed error, not a matched string: the compiler then makes the route handle both cases, and the tests compare values, not words.
   - **Not included:** the answers, the limit, the page, a test of the log lines (no test in the crate reads logs, and adding a log-capture crate is more than this needs).
3. **Done when:**
   - The two unit tests and the route tests pass in CI; the full gate, the mutants run and the OS image pass.
   - No red commit: the change is not a defect in what the node answers, and the stricter tests cannot be written against the old `String` error. The verifier reasons the mutants instead: the two cases swapped in `suggest`; the route's two log lines swapped.
   - One verifier pass (the change has code).
4. **Authority:** these files. On the Mac, `scripts/cargo.sh` fmt, clippy and check; the Rust tests run in CI. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Change

- `src/hostname.rs`: `pub enum Unchecked { Unknown(String), OutOfTime(Duration) }`; `suggest` returns `Result<Option<NodeName>, Unchecked>`. The timeout is `.unwrap_or(Err(Unchecked::OutOfTime(limit)))`; clippy (`unnecessary_lazy_evaluations`) refused the closure form.
- `src/http.rs`: the `Err` arm matches the case. `Unknown` logs "resolved could not say which names are free" with `why`; `OutOfTime` logs "resolved did not answer within the suggestion's time limit" with `limit`. Both answer the same 503.
- **Test changes, with their reason:** in `an_unknown_answer_stops_the_suggestion` and `the_limit_ends_the_suggestion_unchecked`, `assert!(got.is_err())` becomes `assert_eq!` on the exact case and value (nit 5). Both are stricter; the helper `suggesting` takes the new type.
- On the Mac: fmt and clippy (all targets, `-D warnings`) are clean. The tests run in CI.

### CI on `2c28c16`: Pass

- `Full gate (Ubuntu)`, [run 43566514238](https://github.com/rikuripi/rikurinode/actions/runs/43566514238): `an_unknown_answer_stops_the_suggestion`, `the_limit_ends_the_suggestion_unchecked` and `every_name_taken_is_no_suggestion` `ok`, with the route tests; `174 passed; 0 failed`.
- Rust mutants, [run 43566514280](https://github.com/rikuripi/rikurinode/actions/runs/43566514280): `6 mutants … 1 caught, 5 unviable`, none missed. The unviable ones need a `Default` that `NodeName` and `Json` do not have.
- OS image, [run 43566514228](https://github.com/rikuripi/rikurinode/actions/runs/43566514228): passed.
- The owner merged #106 at `2c28c16` (as `06b2e64`) before the verifier ran.

### The verifier, at `2c28c16`: PASS

- Every answer is unchanged: both `Err` cases reach the one 503 after the match; the lock is held to the end; `suggest` has no other caller.
- The log lines carry `why` (the candidate name and resolved's reason) and `limit`; nothing secret or user-entered.
- The test changes are stricter only; no route test changed. The case for no red commit holds: no answer changes, and the typed values cannot be tested against the old `String`.
- **Hand mutations, reasoned:**
  | Mutant | Result |
  |---|---|
  | the timeout gives `Unknown` | killed (`the_limit_ends_the_suggestion_unchecked`) |
  | an unknown answer gives `OutOfTime` | killed (`an_unknown_answer_stops_the_suggestion`) |
  | `OutOfTime` with another duration | killed (expects 100 ms) |
  | the two log lines swapped | survives, as the Scope expected: no test reads logs |
  | the `Unknown` case answers other than 503 | killed (`a_suggestion_resolved_cannot_give_is_refused`) |
  | the `OutOfTime` case answers other than 503 | survives: no route test waits 30 s; the 503 is shared after the match |
- **Findings:** no Important finding. Nits: this close-out (answered here); the two survivors above.

### Close-out

- **Done when:** met. The tests passed in CI; the gate, the mutants run (0 missed) and the OS image passed; the verifier passed.
- **Repairs:** 0. Review rounds: 1.
- **Used:** no budget is configured. One CI push and one verifier pass.
