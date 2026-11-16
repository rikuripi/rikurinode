# Build Record — a lost name is lost though the names stay

| | |
|---|---|
| **Date** | 2026-11-16 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-lost-same-names`, from `main` at `4ff6044`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `20caa6c` (contract), `00d1708` (test) |
| **Status** | IN PROGRESS |
| **Change type** | test |

## Intent: the owner's words

- "Next" (2026-11-16), answering the proposed task: "a test that a reload reports the name lost even when the names in force don't change: a name before, none after, equal names. A later edit that checks 'same' before 'lost' would then fail it". This is nit 1 of the verifier in `docs/build-records/2026-11-15-name-false-loss.md`.

## Task Contract

1. **Outcome:** a later edit that checks "same" before "lost" in `change` fails a test. Such an edit would silence the warning for a hostname file that stops naming a name `RIKURI_NAMES` also holds.
2. **Scope:** routine; one new test in `control-plane/crates/rikuri-control/src/names.rs`, `a_lost_name_is_lost_though_the_names_stay`.
   - `RIKURI_NAMES` holds `extra.local` and `rikuri01.local`; the file names `rikuri01`; `compose` reads it.
   - The file is then blanked and read again.
   - The test asserts:
     - the two reads give the same names;
     - the first read has a name and the second has none;
     - `change` is `Lost`.
   - It uses a real file and `compose`, not hand-built `Read`s, so it pins what the node reads.
   - **Not included:** any change to the node's code; the other survivor (`load`'s warning condition, which only a log test could reach); nits 3 and 4 of that review.
3. **Done when:**
   - The test passes in CI; the full gate, the mutants run and the OS image pass.
   - No red commit: no defect is fixed, and the test passes against today's code. The verifier reasons the mutant it exists for instead: `Same` checked before `Lost`.
   - One verifier pass (the change has code).
4. **Authority:** this file and this record. On the Mac, `scripts/cargo.sh` fmt, clippy and check; the Rust tests run in CI. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Test, `00d1708`

- `a_lost_name_is_lost_though_the_names_stay`:
  - `compose` reads the file naming `rikuri01`, then reads it again blanked, with `extra.local` and `rikuri01.local` configured;
  - it asserts equal names, a name before and none after, and `change` is `Lost`.
- Its temp file, `kept`, is not used by another test in the module.
- No other test changed. On the Mac, fmt and clippy (all targets, `-D warnings`) are clean. The test runs in CI.
