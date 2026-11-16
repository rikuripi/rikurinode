# Build Record — a name found again is logged

| | |
|---|---|
| **Date** | 2026-11-16 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-found-again`, from `main` at `87a2646`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled in as they land) |
| **Status** | IN PROGRESS |
| **Change type** | defect fix |

## Intent: the owner's words

- "Next" (2026-11-16), answering the proposed task: "log when the hostname file names a name again after the start-up warning, in the case where `RIKURI_NAMES` already holds that name. Today `change` calls that 'same' and logs nothing". This is nit 4 (first half) of the verifier in `docs/build-records/2026-11-15-name-false-loss.md`.

## The defect

- With `rikuri01.local` in `RIKURI_NAMES`, a blank hostname file gives a warning: "names no node name" at start, or "no longer names a node name" on reload.
- When the file names `rikuri01` again, the names in force do not change, so `change` (`control-plane/crates/rikuri-control/src/names.rs`) gives `Same`, and `reload` logs nothing.
- The last word in the log is then the warning, though the file is fixed. Whoever reads the log cannot tell the node recovered. AGENTS.md, "Nothing important fails silently".

## Task Contract

1. **Outcome:** when the hostname file names a node name again after naming none, the log says so, whatever `RIKURI_NAMES` holds.
2. **Scope:** routine; one file, `names.rs`.
   - A new case, `Change::Found`: `before` had no name and `fresh` has one. `change` checks it after `Lost` and before `Same`, the mirror of `Lost`.
   - `reload` logs `Found` at `info`: "the hostname file names a node name again", with the name and the names in force.
   - **The red commit** holds:
     - the variant;
     - a new test, `a_name_found_again_is_found`: a real file read through `compose`, with `extra.local` and `rikuri01.local` configured, first blank and then `rikuri01`; the names stay equal, and `change` must be `Found`;
     - in `a_reload_that_loses_the_name_is_a_loss`, the "name found" case's answer changed from `Changed` to `Found`. The reason: the new case names that change exactly, so the test is stricter, not looser.
     `change` stays as it is. Clippy refuses an unbuilt variant outside tests, so the variant carries `#[cfg_attr(not(test), expect(dead_code, …))]`, which the fix removes.
   - **Not included:**
     - a rename between two configured names, still unlogged (the other half of that nit);
     - the warning words;
     - a test that reads logs;
     - `load`, which logs nothing on a name (its silence is right: nothing was lost).
3. **Done when:**
   - Red: committed and pushed alone, and fails in CI on both `Found` assertions.
   - The fix in its own commit; the module's tests pass in CI; the full gate, the mutants run and the OS image pass.
   - One verifier pass (the change has code).
4. **Authority:** this file and this record. On the Mac, `scripts/cargo.sh` fmt, clippy and check; the Rust tests run in CI. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log
