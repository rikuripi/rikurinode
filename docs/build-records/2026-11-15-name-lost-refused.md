# Build Record — a reload that loses the name refuses it

| | |
|---|---|
| **Date** | 2026-11-15 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-lost-refused`, from `main` at `70bfcf0`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `c9df850` (contract), `4130701` (test), `02cce4e` (record); merged as `91ee25d` (#114) |
| **Status** | DONE |
| **Change type** | test |

## Intent: the owner's words

- "Next" (2026-11-15), answering the proposed task: "a test that a reload from a named state to a lost one refuses the old name, which also runs the warning line". This is nit 2 of the verifier in `docs/build-records/2026-11-15-name-reload-warn.md`.

## Task Contract

1. **Outcome:** a later edit that stops a lost name from leaving the `Host` and `Origin` checks fails a test, so the node cannot keep accepting pages served under a name it no longer has.
2. **Scope:** routine; one test in `control-plane/crates/rikuri-control/src/names.rs`, `a_reload_that_loses_the_name_refuses_it`.
   - The hostname file names `rikuri01`; `LiveNames::load` with a configured `extra.local`.
   - Each case empties the file in its own way: missing, blank, a dotted name, a line that is not a name.
   - After `reload`: the names returned and in force are the configured ones alone; `rikuri01.local` is refused as `Host` and as `Origin`; `extra.local` is still allowed.
   - **Not included:** any change to the node's code; a test that reads the warning (it runs, but no test in the crate reads logs); nit 1 of that review.
3. **Done when:**
   - The test passes in CI; the full gate, the mutants run and the OS image pass.
   - No red commit: no defect is fixed, and the test passes against today's code. The verifier reasons the mutant this test exists for instead: the assignment to the names in force kept only in `reload`'s `Changed` arm.
   - One verifier pass (the change has code).
4. **Authority:** this file and this record. On the Mac, `scripts/cargo.sh` fmt, clippy and check; the Rust tests run in CI. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Test, `4130701`

- `a_reload_that_loses_the_name_refuses_it`, four cases (missing, blank, dotted, odd). Each starts with the file naming `rikuri01` and checks that `rikuri01.local` is allowed. After the file is emptied, it checks four things:
  - `reload()` and `get()` both equal the configured names;
  - `rikuri01.local` is refused as `Host`;
  - `https://rikuri01.local` is refused as `Origin`;
  - `extra.local` is still allowed.
- Every case's reload takes `reload`'s `Lost` arm, so the warning line now runs in a test.
- No other test changed. On the Mac, fmt and clippy (all targets, `-D warnings`) are clean. The test runs in CI.

### CI on `02cce4e`: Pass

- `Full gate (Ubuntu)`, [run 43763189474](https://github.com/rikuripi/rikurinode/actions/runs/43763189474): `a_reload_that_loses_the_name_refuses_it ... ok`; `176 passed; 0 failed`.
- Rust mutants, [run 43763189487](https://github.com/rikuripi/rikurinode/actions/runs/43763189487): passed, "No mutants to filter": the diff is test code only.
- OS image, [run 43763189483](https://github.com/rikuripi/rikurinode/actions/runs/43763189483): passed.
- The owner merged #114 at `02cce4e` (as `91ee25d`) before the verifier ran.

### The verifier, at `02cce4e`: PASS

- The diff is one new test; no production line or other test changed. The case for no red commit holds.
- The test drives the real `load`, `reload`, `get`, `host_allowed` and `origin_allowed` on a real file. Every case reaches the `Lost` arm: `compose` returns the configured names alone (the file unreadable, or `name_in` finding no name), while the names before held `rikuri01.local`.
- The temp files (`rikuri-names-<pid>-lost-<case>.hostname`) cannot collide with the module's other tests.
- **Hand mutations, reasoned:**
  | Mutant | Result |
  |---|---|
  | the assignment to the names in force kept only in the `Changed` arm | killed, by this test alone |
  | the assignment removed | killed (this test and `a_reload_follows_the_file_and_the_old_name_leaves`) |
  | `change`'s `Lost` branch removed | not killed by this test (only the log changes); killed by `a_reload_that_loses_the_name_is_a_loss` |
- **Nits:** the record lacked the green runs and DONE (this close-out); #114 merged before the verifier ran (the owner's call). Still for the backlog: no test reads the `Lost` warning itself.

## Outcome

DONE, with 0 repairs and 1 review round.
