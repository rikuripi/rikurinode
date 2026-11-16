# Build Record — tests that read the name log lines

| | |
|---|---|
| **Date** | 2026-11-16 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-log-tests`, from `main` at `fce25b3`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `32fb218` (contract), `11d10ca` (tests), `1a3d17b` (record); merged as `f43ab6a` (#122) |
| **Status** | DONE |
| **Change type** | test |

## Intent: the owner's words

- "Next" (2026-11-16), answering the proposed task: "a test that reads the name log lines: start-up, lost, found and changed. It would cover the log lines that the last five name tasks' tests never read. It makes `tracing-subscriber`, already pinned in the workspace, a dev-dependency of `rikuri-control`".
- Survivors this closes:
  - `docs/build-records/2026-11-15-name-reload-warn.md`: the `Lost` and `Changed` arms swapped; `Same` logging.
  - `docs/build-records/2026-11-15-name-false-loss.md`: `load` warning on `names == configured` again.
  - `docs/build-records/2026-11-16-name-found-again.md`: the `Found` arm emptied.

## Task Contract

1. **Outcome:** an edit that changes which name log line the node writes, or its level, fails a test. The warnings that tell the owner the node lost its name can then no longer go quiet unseen.
2. **Scope:** routine; test code and one dev-dependency.
   - `control-plane/crates/rikuri-control/Cargo.toml`: `tracing-subscriber.workspace = true` under `[dev-dependencies]`.
     - It is the workspace's pin (`=0.3.23`), already used by `apps/rikuri-control-plane` and already vetted by cargo-deny.
     - `Cargo.lock` gains only that edge in `rikuri-control`'s list; no new package. The gate's cargo-deny step checks it.
   - `control-plane/crates/rikuri-control/src/names.rs`, test module:
     - a helper, `logged(f)`, which runs `f` under a `tracing_subscriber::fmt` subscriber that writes, without time or colour, into a buffer, and returns the text. It uses `tracing::subscriber::with_default`, which holds only on this thread; `load` and `reload` are synchronous.
     - `the_start_warns_only_when_the_file_names_no_name`, two cases:
       - blank: a `WARN` with "names no node name";
       - named, with `RIKURI_NAMES` holding the same name: nothing logged (the false-loss case).
     - `a_reload_logs_what_the_file_did`, four cases, each on a real file from `load`:
       - renamed: `INFO` "the node's names changed";
       - lost: `WARN` "no longer names a node name";
       - found again (`RIKURI_NAMES` holding the name): `INFO` "names a node name again";
       - unchanged: nothing logged.
     - Each asserts the level and the words, and that no other name line is present.
   - **Not included:**
     - any change to the node's code or its log words;
     - the `Display` form of the logged name (nit 3 of the found-again review);
     - a rename between two configured names, still unlogged;
     - log tests for other modules.
3. **Done when:**
   - The tests pass in CI; the full gate (cargo-deny included), the mutants run and the OS image pass.
   - No red commit: no defect is fixed, and the tests pass against today's code. The verifier reasons the survivors above instead.
   - One verifier pass (the change has code).
4. **Authority:** these files and this record. On the Mac, `scripts/cargo.sh` fmt, clippy and check; `scripts/cargo.sh` may update `Cargo.lock` for the new edge, from crates already fetched. The Rust tests run in CI. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Tests, `11d10ca`

- `Cargo.toml`: `tracing-subscriber.workspace = true` under `[dev-dependencies]`, with a comment naming this record. `Cargo.lock` gains one line, the edge in `rikuri-control`'s list; no package added or changed.
- `names.rs`, test module:
  - `logged(f)`: a `tracing_subscriber::fmt` subscriber (no time, no colour) writing into a shared buffer, set with `tracing::subscriber::with_default` for `f` only. The setting holds on this thread alone, so tests running in parallel cannot write into the buffer.
  - `one_line(log, want, case)`: either nothing logged, or exactly one line that starts with the level and holds the words.
  - `the_start_warns_only_when_the_file_names_no_name`: blank gives `WARN` "names no node name"; named with `rikuri01.local` configured gives nothing.
  - `a_reload_logs_what_the_file_did`: renamed gives `INFO` "the node's names changed"; lost gives `WARN` "no longer names a node name"; found again with `rikuri01.local` configured gives `INFO` "names a node name again"; unchanged gives nothing. `load` runs outside the capture, so only `reload`'s line is read.
  - Their temp files (`start-…`, `log-…`) are not used by another test.
- No other test changed. On the Mac, fmt and clippy (all targets, `--locked`, `-D warnings`) are clean. The tests run in CI.

### CI on `1a3d17b`: Pass

- `Full gate (Ubuntu)`, [run 43805869906](https://github.com/rikuripi/rikurinode/actions/runs/43805869906): `a_reload_logs_what_the_file_did ... ok` and `the_start_warns_only_when_the_file_names_no_name ... ok`; `181 passed; 0 failed`; cargo deny "advisories ok, bans ok, licenses ok, sources ok".
- Rust mutants, [run 43805869805](https://github.com/rikuripi/rikurinode/actions/runs/43805869805): passed, "No mutants to filter": no production code changed.
- OS image, [run 43805869884](https://github.com/rikuripi/rikurinode/actions/runs/43805869884): passed.
- Advisory audit, [run 43805869902](https://github.com/rikuripi/rikurinode/actions/runs/43805869902): passed (it runs when `Cargo.lock` changes).
- The owner merged #122 at `1a3d17b` (as `f43ab6a`) before the verifier ran.

### The verifier, at `1a3d17b`: PASS

- Scope: test code, the dev-dependency and one lockfile edge. `tracing-subscriber 0.3.23` was already in the lock; no package was added or changed.
- No other test's events can leak into a capture: without a global subscriber, an event goes to the subscriber of the thread that emits it.
- The level check holds against fmt's padding (`" INFO"`, `" WARN"`); the temp files do not collide; every case goes through a real file and the real `load` or `reload`.
- **Hand mutations, reasoned:**
  | Mutant | Result |
  |---|---|
  | `Lost` and `Changed` swapped (whole, levels only, or words only); `Lost` at `info` or `error` | killed |
  | `Same` logging at `info`, `warn` or `error` | killed ("unchanged") |
  | `Same` logging at `debug` or `trace` | survives: below the capture's `info` filter, as in production |
  | `load` warning on `names == configured`, or on `name.is_some()` | killed (the start cases) |
  | `Found` emptied, or set to `warn` | killed ("found again") |
  | log fields changed or dropped | survives (excluded by the Scope) |
  All four survivors this task named are killed.
- **Nits, for the backlog:**
  1. **A rare missed event.** While a capture's subscriber is the only one alive, tracing-core caches a log line's interest from the thread that reaches it first. A parallel test with no subscriber can then cache "never", and the capture misses its own line. That would be a rare false red, or a rare surviving mutant. Calling `tracing::callsite::rebuild_interest_cache()` inside the capture, before `f`, would close it. This record's reasoning covered events leaking in, not events being missed.
  2. `Same` logging at `debug` or `trace` survives (invisible in production too).
  3. The record lacked the green runs and DONE: this close-out.

## Outcome

DONE, with 0 repairs and 1 review round.
