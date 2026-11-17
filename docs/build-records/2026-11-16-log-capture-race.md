# Build Record — the log capture cannot miss its own line

| | |
|---|---|
| **Date** | 2026-11-16 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/log-capture-race`, from `main` at `d79ae74`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `87ebe3a` (contract), `4fa07c2` (red); the owner-requested update from `main`, `420b02d` (bringing in #125 and #126 only); `6e32361` (fix), `9dd219d` (record); merged as `2c425eb` (#124) |
| **Status** | DONE |
| **Change type** | defect fix (test code) |

## Intent: the owner's words

- "Next" (2026-11-16), answering the proposed task: "close a rare race in the log capture, which could make a CI run fail for no real reason: call `tracing::callsite::rebuild_interest_cache()` inside `logged`, before it runs the test". This is nit 1 of the verifier in `docs/build-records/2026-11-16-name-log-tests.md`.

## The defect

The test helper `logged` (`control-plane/crates/rikuri-control/src/names.rs`) can miss the line it exists to capture. In tracing-core 0.1.36 (`src/callsite.rs`, read from the pinned source):

- `Dispatchers::register_dispatch` sets `has_just_one` to whether one dispatcher or fewer is alive. It does so only when a dispatcher registers.
- While it is true, the first thread to reach a log line caches that line's interest from its own default dispatcher (`Rebuilder::JustOne`, `dispatcher::get_default`).
- So while one capture is the only dispatcher alive, a parallel test thread with no subscriber can reach a line first. It caches `Interest::never`, and the capture's own event on that line is dropped. The interest is rebuilt only when another dispatcher registers.
- The result is a false red in CI, or a mutant that survives on that run.

**Why not the proposed fix.** `rebuild_interest_cache()` before `f` resets interest once, but the wrong interest can be cached during `f`. It narrows the window and does not close it.

## Task Contract

1. **Outcome:** a log capture in a test always hears its own line, whatever other test threads reach first. A CI run cannot fail for that reason.
2. **Scope:** routine; test code in `names.rs` only.
   - **The fix:** `logged` first makes sure a second dispatcher is alive for the whole test process: a `Dispatch` of `tracing::subscriber::NoSubscriber`, kept in a `OnceLock`. With two or more alive, `has_just_one` is false. A new line's interest is then the `and` of every live dispatcher (`never` with the capture's `always` gives `sometimes`), so each event asks its own thread's subscriber.
   - **The red test**, `a_capture_hears_a_line_another_thread_reached_first`:
     - inside `logged`, a spawned thread with no subscriber reaches a line that only this test logs and is joined;
     - then this thread logs the same line;
     - the capture must hold exactly that one line.
     It fails without the fix whenever its capture is the only dispatcher alive when it registers. That is nearly always, since the module's other captures last microseconds.
   - **A residue of the red:** if another capture registers while this one is alive, the red can pass by chance. The red run in CI is the evidence; if it passes, I report that and do not count it as red.
   - **Not included:** the node's code; the other nits of that review; captures in other modules (there are none).
3. **Done when:**
   - Red: the test is committed and pushed alone, and fails in CI on an empty capture.
   - The fix in its own commit; the module's tests pass in CI; the full gate, the mutants run and the OS image pass.
   - One verifier pass (the change has code).
4. **Authority:** this file and this record. On the Mac, `scripts/cargo.sh` fmt, clippy and check; the Rust tests run in CI. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Red on `4fa07c2`: blocked, not counted

- `Full gate (Ubuntu)`, [run 43967988915](https://github.com/rikuripi/rikurinode/actions/runs/43967988915), and Rust mutants, [run 43967988871](https://github.com/rikuripi/rikurinode/actions/runs/43967988871): both stopped at the npm audit, before any Rust test: `npm_audit: FAIL GHSA-gcqx-w48m-w2h4: excepted, but npm no longer reports it; remove the exception`. Not the red; the stale exception was removed by `docs/build-records/2026-11-16-audit-stale-exception.md` (#125).

### Red on `420b02d`: Fail, as intended

- `420b02d` is `gh pr update-branch 124`, at the owner's word ("update #124"). It merges `main` (#125, #126) and changes nothing under `control-plane/`; the red test is `4fa07c2`'s.
- `Full gate (Ubuntu)`, [run 44119463554](https://github.com/rikuripi/rikurinode/actions/runs/44119463554): the audit passed (`npm audit: 0 advisories, all recorded exceptions`); `181 passed; 1 failed`, exactly:
  - `a_capture_hears_a_line_another_thread_reached_first`, at `names.rs:583`: `left: 0`, `right: 1`: the capture held no line.
- Rust mutants, [run 44119463299](https://github.com/rikuripi/rikurinode/actions/runs/44119463299): passed, "No mutants to filter": the diff is test code only, so no baseline ran.
- OS image, [run 44119463159](https://github.com/rikuripi/rikurinode/actions/runs/44119463159): passed.

### Fix, `6e32361`

- `logged` first gets or makes a `static OTHER: OnceLock<tracing::Dispatch>` holding `Dispatch::new(NoSubscriber::default())`, then builds the capture as before.
- In tracing-core 0.1.36 (pinned source), `Dispatch::new` calls `callsite::register_dispatch`, and `NoSubscriber::register_callsite` returns `Interest::never()`. Once the capture registers beside it, two are alive and `has_just_one` is false; a line's interest is the `and` of both (`sometimes`), and each event asks its own thread's subscriber.
- The `OnceLock` holds the dispatch for the whole test process, so it is never dropped and never pruned.
- No test changed after the red. On the Mac, fmt and clippy (all targets, `--locked`, `-D warnings`) are clean. The tests run in CI.

### CI on `9dd219d`: Pass

- `Full gate (Ubuntu)`, [run 44129260265](https://github.com/rikuripi/rikurinode/actions/runs/44129260265): `a_capture_hears_a_line_another_thread_reached_first ... ok`; `182 passed; 0 failed`.
- Rust mutants, [run 44129259999](https://github.com/rikuripi/rikurinode/actions/runs/44129259999): passed, "No mutants to filter": the diff is test code only.
- OS image, [run 44129260168](https://github.com/rikuripi/rikurinode/actions/runs/44129260168): passed.
- The owner merged #124 at `9dd219d` (as `2c425eb`) before the verifier ran.

### The verifier, at `9dd219d`: PASS

- The red is the test alone; it failed in run 44119463554 at `one_line`'s count (`left: 0`, `right: 1`): the capture was empty. `420b02d` changes nothing under `control-plane/`; from the red to the head, the only Rust change is the eight lines in `logged`.
- The mechanism, from the pinned tracing-core 0.1.36 and tracing 0.1.44 source:
  - `Dispatch::new` registers; `register_dispatch` prunes dead entries, sets `has_just_one` to `len <= 1`, and rebuilds every callsite's interest. The `OnceLock` holds the strong reference, so `OTHER` is never pruned, and every later registration sees two or more.
  - With two alive, interest is the `and` of both (`never` and `always` give `sometimes`), and each event asks its own thread's default subscriber.
  - **Level:** `NoSubscriber` gives no `max_level_hint`, which counts as TRACE, so `OTHER` raises the test binary's global level filter to TRACE; it never lowers it. `debug!` and `trace!` lines then pass the global check and are refused by their interest instead. Harmless.
- Test-only, inside `#[cfg(test)]`; production logging (`apps/rikuri-control-plane/src/main.rs`) is untouched.
- **Hand mutations, reasoned:**
  | Mutant | Result |
  |---|---|
  | `OTHER` removed | killed (the red itself) |
  | `OTHER` a local alive through `f`, dropped at the end | survives, equivalent: two are alive during `f`; only the first-call window (nit 1) reopens on every call |
  | `OTHER` made and dropped at once | killed: pruned at the capture's registration |
  | `OTHER` made after `with_default` | killed only by test order: libtest starts tests by name, and `a_capture_…` sorts first |
  | an always-interested subscriber in place of `NoSubscriber` | survives, equivalent: no `never` can be cached while a capture is alive |
  | the red's spawned thread removed, or its `join` | the test loses its power: the capture's thread reaches the line first |
- **Nits, for the backlog:**
  1. **A first-call window.** In the process's first `logged` call, `OTHER` registers alone (`has_just_one` true) until the capture registers just after. A callsite first reached by another thread in those microseconds could still cache `never`. Two `NoSubscriber` dispatches in the `OnceLock` would close it. The new test's line cannot hit it: it is reached only inside the capture.
  2. The level fact above: the builder's brief had guessed `NoSubscriber` might lower the filter; it raises it.
  3. The record lacked the green runs and DONE: this close-out.

## Outcome

DONE, with 0 repairs and 1 review round.
