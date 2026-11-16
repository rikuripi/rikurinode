# Build Record — no "name lost" warning while the file names one

| | |
|---|---|
| **Date** | 2026-11-15 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-false-loss`, from `main` at `455bcc9`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `74511ac` (contract), `3c1378c` (red), `7dac185` (fix), `f64b375` (record); merged as `177a0f4` (#116) |
| **Status** | DONE |
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

### Red on `3c1378c`: Fail, as intended

- `Full gate (Ubuntu)`, [run 43767528876](https://github.com/rikuripi/rikurinode/actions/runs/43767528876): `a_configured_name_does_not_hide_the_files ... FAILED`, "assertion `left == right` failed: the file's name", `left: None`, `right: Some(NodeName("rikuri01"))`. `176 passed; 1 failed`; no other test failed, so the refactor kept every other answer.
- Rust mutants, [run 43767528910](https://github.com/rikuripi/rikurinode/actions/runs/43767528910): failed, as its baseline includes the red test.
- OS image, [run 43767528951](https://github.com/rikuripi/rikurinode/actions/runs/43767528951): passed.
- The red's structure:
  - `LiveNames` keeps a `Read`, the file's name and the names in force;
  - `load` warns on `name.is_none()`;
  - `change(before, fresh)` is `Lost` first, then `Same`, then `Changed`.
  With the flaw kept in `compose`, both warnings are exactly today's. "No name" there means the names equal the configured ones, so `Lost` needs names that differ.
- **Test change in the red, with its reason:** `a_reload_that_loses_the_name_is_a_loss` builds `Read`s for `change`'s new signature. Its five cases and answers are unchanged.

### Fix, `7dac185`

- `compose` no longer drops a name that adds nothing to the configured names: the `filter` and its comment are removed. Nothing else changed.
- No test changed after the red. On the Mac, fmt and clippy (all targets, `-D warnings`) are clean. The tests run in CI.

### CI on `f64b375`: Pass

- `Full gate (Ubuntu)`, [run 43778918223](https://github.com/rikuripi/rikurinode/actions/runs/43778918223): `a_configured_name_does_not_hide_the_files ... ok`; `177 passed; 0 failed`.
- Rust mutants, [run 43778918178](https://github.com/rikuripi/rikurinode/actions/runs/43778918178): `11 mutants tested in 84s: 6 caught, 5 unviable`, none missed. The unviable ones need a `Default` that `LiveNames`, `Names`, `Change` and `Read` do not have.
- OS image, [run 43778918177](https://github.com/rikuripi/rikurinode/actions/runs/43778918177): passed.
- The owner merged #116 at `f64b375` (as `177a0f4`) before the verifier ran.

### The verifier, at `f64b375`: PASS

- The red kept every answer and warning, reasoned case by case:
  - `load`'s `name.is_none()` is `main`'s `current == configured`;
  - `change` gives the same result for every combination (`configured` never changes inside `LiveNames`);
  - `get`, `host_allowed`, `origin_allowed` and `reload` use the same names.
  The rewritten test keeps its five cases and answers.
- The fix removes exactly the filter and its comment; no test changed after the red.
- The names in force are byte-for-byte `main`'s in every case; only logs differ. The flagged choice (a file losing a name `RIKURI_NAMES` also holds warns `Lost`) is sound: it matches `load` at start, the message stays true, and it ends a silence about a broken file.
- **Hand mutations, reasoned:**
  | Mutant | Result |
  |---|---|
  | the filter restored | killed (`a_configured_name_does_not_hide_the_files`; seen in the red run) |
  | either `Lost` condition removed, the roles swapped, `&&` to `\|\|` | killed (`a_reload_that_loses_the_name_is_a_loss`) |
  | `Same` checked before `Lost` | survives: no test has a name before, none after, and equal names |
  | `load` warning on `names == configured` again | survives: no test reads `load`'s warning |
- **Nits, for the backlog:**
  1. The two survivors. One `change` case (named before, none after, equal names) would kill the first without reading logs.
  2. The record lacked the green runs and DONE: this close-out.
  3. The red test stopped at its first assert, so its second (the rename back is `Changed`) was not seen failing; by reasoning it would have.
  4. Existing behaviour, unchanged from `main`:
     - a file that gains a name `RIKURI_NAMES` already holds is `Same`, so recovery from the start warning is not logged;
     - a rename between two configured names is not logged.

## Outcome

DONE, with 0 repairs and 1 review round.
