# Build Record — no "name lost" warning while the file names one

| | |
|---|---|
| **Date** | 2026-11-15 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-false-loss`, from `main` at `455bcc9`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled in as they land) |
| **Status** | IN PROGRESS |
| **Change type** | defect fix |

## Intent: the owner's words

- "Next" (2026-11-15), answering the proposed task: "fix the false 'name lost' warning. If `RIKURI_NAMES` already holds the node's `.local` name, the node says the name is lost, at start and after a rename back, even though the file names it". This is nit 1 of the verifier in `docs/build-records/2026-11-15-name-reload-warn.md`.

## The defect

- `compose` (`control-plane/crates/rikuri-control/src/names.rs`) returns the configured names plus the file's `<name>.local`. Both warnings then infer "the file names no node name" from "the names equal the configured ones".
- When `RIKURI_NAMES` holds `rikuri01.local` and the file names `rikuri01`, adding the name changes nothing, so the inference is wrong:
  - `LiveNames::load` warns "the hostname file names no node name";
  - a reload from `rikuri02` back to `rikuri01` warns "no longer names a node name".
- Which names are in force is right in both cases; only the log lies. A false warning teaches the owner to ignore the true one.

## Task Contract

1. **Outcome:** the node warns that its hostname file names no node name only when the file does not name one, whatever `RIKURI_NAMES` holds.
2. **Scope:** routine; one file, `names.rs`.
   - `compose` returns a `Read`: the node name the file gave (`Option<NodeName>`) and the names in force. `LiveNames` keeps the current `Read`; `get`, `host_allowed`, `origin_allowed` and `reload`'s return use its names as before.
   - `load` warns when `name` is `None`. `change(before, fresh)`: `Lost` when `before` had a name and `fresh` has none; else `Same` when the names are equal; else `Changed`.
   - **The red commit** makes that structure but keeps today's flaw in `compose`: it records the file's name only when the name adds to the configured names. Every warning is then what it is today. The existing test `a_reload_that_loses_the_name_is_a_loss` is rewritten in that same commit to build `Read`s: the reason is the new signature, and its five cases and answers stay the same.
   - **The red test**, `a_configured_name_does_not_hide_the_files`: with `extra.local` and `rikuri01.local` configured and the file naming `rikuri01`, `compose` gives `Some(rikuri01)`; then a reload from `rikuri02` to `rikuri01` is `Changed`, not `Lost`.
   - **A choice:** with the order above, a file that stops naming `rikuri01` while `RIKURI_NAMES` holds `rikuri01.local` now warns `Lost`, though the name still answers. The warning is about the file, as it is at start; the message says the node answers by its configured names, which is true.
   - **Not included:** which names are in force (unchanged); the warning's words; a test that reads logs.
3. **Done when:**
   - Red: the test is committed and pushed alone, and fails in CI on `compose`'s answer.
   - The fix in its own commit; the module's tests pass in CI; the full gate, the mutants run and the OS image pass.
   - One verifier pass (the change has code).
4. **Authority:** this file and this record. On the Mac, `scripts/cargo.sh` fmt, clippy and check; the Rust tests run in CI. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log
