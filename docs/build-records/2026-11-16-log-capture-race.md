# Build Record — the log capture cannot miss its own line

| | |
|---|---|
| **Date** | 2026-11-16 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/log-capture-race`, from `main` at `d79ae74`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled in as they land) |
| **Status** | IN PROGRESS |
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
