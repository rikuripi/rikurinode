# Build Record — a reload that loses the node's name warns

| | |
|---|---|
| **Date** | 2026-11-15 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-reload-warn`, from `main` at `83c4a60`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `d5eca60` (contract), `4d65907` (red), `c47460d` (fix), `33805f2` (record); merged as `b606be2` (#112) |
| **Status** | DONE |
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

### Red on `4d65907`: Fail, as intended

- `Full gate (Ubuntu)`, [run 43744530182](https://github.com/rikuripi/rikurinode/actions/runs/43744530182): `a_reload_that_loses_the_name_is_a_loss ... FAILED`, "assertion `left == right` failed: name lost", `left: Changed`, `right: Lost`. `174 passed; 1 failed`; no other test failed.
- Rust mutants, [run 43744530156](https://github.com/rikuripi/rikurinode/actions/runs/43744530156): "FAILED Unmutated baseline", because the baseline includes the red test.
- OS image, [run 43744530078](https://github.com/rikuripi/rikurinode/actions/runs/43744530078): passed.
- In the red, `Lost` carried `#[cfg_attr(not(test), expect(dead_code, …))]`: clippy refuses an unbuilt variant outside tests. The fix removes it; `expect` would fail had it stayed.

### Fix, `c47460d`

- `change` returns `Lost` when the names differ and the fresh ones are the configured names alone; otherwise `Changed`, or `Same` when they are equal.
- `reload` matches it: `Same` logs nothing; `Changed` keeps the `info` line; `Lost` warns "the hostname file no longer names a node name: the node answers by address and its configured names only", with the file. The names in force follow the file as before; `*current = fresh` now runs in every case, which changes nothing when they are equal.
- No test changed after the red.
- On the Mac: fmt and clippy (all targets, `-D warnings`) are clean. The tests run in CI.

### CI on `33805f2`: Pass

- `Full gate (Ubuntu)`, [run 43746413671](https://github.com/rikuripi/rikurinode/actions/runs/43746413671): `a_reload_that_loses_the_name_is_a_loss ... ok`; `175 passed; 0 failed`.
- Rust mutants, [run 43746413805](https://github.com/rikuripi/rikurinode/actions/runs/43746413805): `4 mutants tested in 60s: 2 caught, 2 unviable`, none missed. The caught ones invert `before == fresh` and `fresh == configured` in `change`; the unviable ones need a `Default` that `Names` and `Change` do not have.
- OS image, [run 43746413839](https://github.com/rikuripi/rikurinode/actions/runs/43746413839): passed.
- The owner merged #112 at `33805f2` (as `b606be2`) before the verifier finished.

### The verifier, at `33805f2`: PASS

- The red holds only the test, `change` with the old behaviour, and an equivalent rewrite of `reload`'s check; it failed in CI on "name lost" alone. The fix is its own commit; no test changed after the red.
- `change` is right in every case: `compose` always returns the configured names, plus the node's `.local` name when the file has one, so `fresh == configured` means exactly "no node name now". At start, `load` warns on its own; a node that starts and stays without a name logs once.
- The `Lost` warning carries only the file's path, which comes from the node's configuration. The names in force follow the file as before.
- **Hand mutations, reasoned:**
  | Mutant | Result |
  |---|---|
  | the `Lost` and `Changed` arms' lines or levels swapped; `Same` logging | survive: no test reads logs (excluded by the Contract) |
  | the `fresh == configured` branch removed, inverted, or made `true`/`false` | killed (`a_reload_that_loses_the_name_is_a_loss`) |
  | the `before == fresh` branch removed or inverted | killed (the same test; cargo-mutants too) |
  | `*current = fresh` removed | killed (`a_reload_follows_the_file_and_the_old_name_leaves`) |
  | the assignment kept only in the `Changed` arm | survives: see nit 2 |
- **Nits, for the backlog:**
  1. When `RIKURI_NAMES` itself holds the node's `.local` name, a rename back to that name logs the `Lost` warning though the file names a name. `load` has the same false warning at start; not new.
  2. No test reloads from a named state to a lost one and checks that the old name is then refused. The assignment runs in every arm, so it holds by reading; a test of `reload` there would also run the warning line.
  3. The record lacked the green runs and DONE: this close-out.
  4. #112 was not a draft when the verifier looked; the owner had marked it ready to merge.

## Outcome

DONE, with 0 repairs and 1 review round.
