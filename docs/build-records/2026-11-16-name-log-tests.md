# Build Record — tests that read the name log lines

| | |
|---|---|
| **Date** | 2026-11-16 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-log-tests`, from `main` at `fce25b3`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `32fb218` (contract), `11d10ca` (tests) |
| **Status** | IN PROGRESS |
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
