# Build Record — a name found again is logged

| | |
|---|---|
| **Date** | 2026-11-16 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-found-again`, from `main` at `87a2646`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `b06686c` (contract), `641c44a` (red), `a768f27` (fix), `a44ad71` (record); the owner's update-branch merge `5ec4ccc` (bringing in #119 only); merged as `1f413f0` (#120) |
| **Status** | DONE |
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

### Red on `641c44a`: Fail, as intended

- `Full gate (Ubuntu)`, [run 43795323994](https://github.com/rikuripi/rikurinode/actions/runs/43795323994): `177 passed; 2 failed`, exactly the two `Found` assertions:
  - `a_name_found_again_is_found`: `left: Same`, `right: Found`;
  - `a_reload_that_loses_the_name_is_a_loss`, "name found": `left: Changed`, `right: Found`.
- Rust mutants, [run 43795323999](https://github.com/rikuripi/rikurinode/actions/runs/43795323999): failed, as its baseline includes the red tests.
- OS image, [run 43795323995](https://github.com/rikuripi/rikurinode/actions/runs/43795323995): passed.
- **A deviation from the Contract:** the red also holds `reload`'s `Found` arm (the `info` line), because the compiler requires the `match` to cover the new variant. It cannot run in the red, where `change` never returns `Found`, so every log is still today's.
- **Test change in the red, with its reason:** the table's "name found" answer, from `Changed` to `Found`. The new case names that change exactly; the test is stricter.

### Fix, `a768f27`

- `change` returns `Found` when `before` had no name and `fresh` has one, checked after `Lost` and before `Same`. The `expect(dead_code)` marker is removed.
- A name found while the names in force also change (the table's case) now logs the `Found` line instead of "the node's names changed". Nothing is lost: the line carries the names too.
- No test changed after the red. On the Mac, fmt and clippy (all targets, `-D warnings`) are clean. The tests run in CI.

### CI on `5ec4ccc`: Pass

- `5ec4ccc` is the owner's update-branch merge; it brings in only #119 (`docs/build-records/2026-11-16-name-lost-same-names.md`). The same three runs also passed on `a44ad71`.
- `Full gate (Ubuntu)`, [run 43801376828](https://github.com/rikuripi/rikurinode/actions/runs/43801376828): `a_name_found_again_is_found ... ok`; `179 passed; 0 failed`.
- Rust mutants, [run 43801376907](https://github.com/rikuripi/rikurinode/actions/runs/43801376907): `3 mutants tested: 1 caught, 2 unviable`, none missed. The caught one is `&&` to `||` in the `Found` branch; the unviable ones need a `Default` that `Names` and `Change` do not have.
- OS image, [run 43801376820](https://github.com/rikuripi/rikurinode/actions/runs/43801376820): passed.
- The owner merged #120 at `5ec4ccc` (as `1f413f0`) before the verifier ran.

### The verifier, at `5ec4ccc`: PASS

- The red's `Found` arm could not run (`change` never built `Found`), so every log there was `main`'s. The deviation from the Contract is sound and recorded; the red's test edit is stricter.
- The fix is exactly the `Found` branch and the marker's removal; the test module is byte-identical from the red to the head.
- The names in force are `main`'s in every case; only which log line runs changes. (None, Some) now logs `Found` whether or not the names change; the line carries the names, as `Changed` did.
- The `Found` line logs a checked DNS label and the names `Changed` already logged; nothing secret.
- **Hand mutations, reasoned:**
  | Mutant | Result |
  |---|---|
  | the `Found` branch removed, or its conditions swapped | killed (both `Found` assertions; the red itself) |
  | one condition alone; `&&` to `\|\|` | killed (`a_reload_that_loses_the_name_is_a_loss`) |
  | `Same` checked before `Found` | killed, by `a_name_found_again_is_found` alone |
  | `Found` checked before `Lost` | equivalent: the two cannot both hold |
  | `reload`'s `Found` arm emptied | survives: no test reads logs (excluded by the Contract) |
- **Nits, for the backlog:**
  1. No test shows the `Found` line is written; only a log-reading test, or one of `reload` across blank to named, would.
  2. The record lacked the green runs and DONE: this close-out.
  3. `name = ?fresh.name` logs `Some(NodeName("rikuri01"))`; a `Display` form would read better. #120 merged before the verifier ran (the owner's call).

## Outcome

DONE, with 0 repairs and 1 review round.
