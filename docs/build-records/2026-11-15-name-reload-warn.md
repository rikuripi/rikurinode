# Build Record — a reload that loses the node's name warns

| | |
|---|---|
| **Date** | 2026-11-15 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-reload-warn`, from `main` at `83c4a60`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled in as they land) |
| **Status** | IN PROGRESS |
| **Change type** | defect fix |

## Intent: the owner's words

- "Next" (2026-11-15), answering the proposed task: "log a warning when a reload loses the node's name, so that failure isn't silent".

## The defect

- `LiveNames::load` (`control-plane/crates/rikuri-control/src/names.rs`) warns when the hostname file names no node name: "the node answers by address and its configured names only".
- `LiveNames::reload` does not. When the file later becomes unreadable, blank or invalid, the node drops `<name>.local` from its `Host` and `Origin` checks and from the next certificate. The log shows only `info` "the node's names changed", the same line as a rename.
- The owner then reaches the node by name and is refused, and nothing in the log at warning level says why. AGENTS.md, "Nothing important fails silently".

## Task Contract

1. **Outcome:** when a reload drops the node's name, the log says so as a warning, the way it does at start.
2. **Scope:** routine; one file, `control-plane/crates/rikuri-control/src/names.rs`.
   - A private `enum Change { Same, Changed, Lost }` and `fn change(before, fresh, configured) -> Change`: `Lost` when the names had a node name and the fresh ones are only the configured names.
   - `reload` matches it: `Same` logs nothing; `Changed` keeps the `info` line; `Lost` logs a `warn` with the file, in `load`'s words.
   - A unit test, `a_reload_that_loses_the_name_is_a_loss`: a rename is `Changed`; no change is `Same`; a name to none is `Lost`; none to none is `Same`; none to a name is `Changed`.
   - **Not included:** what the node does when the name is lost (it still follows the file: runtime truth); why the file failed (unreadable or no name; `compose` does not say, and the path is enough to look); a test that reads the log line (no test in the crate reads logs); the page.
3. **Done when:**
   - Red: the test, with `change` encoding today's behaviour (any difference is `Changed`), is committed and pushed alone, and fails in CI on the `Lost` cases.
   - The fix in its own commit; the test passes in CI; the full gate, the mutants run and the OS image pass.
   - One verifier pass (the change has code).
4. **Authority:** this file and this record. On the Mac, `scripts/cargo.sh` fmt, clippy and check; the Rust tests run in CI. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log
