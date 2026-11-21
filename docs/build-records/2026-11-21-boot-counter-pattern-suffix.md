# Build Record — the deployment pattern held whole by a test (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-21 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-counter-pattern-suffix`, from `main` at `657aaf5`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `afc1c75` (contract), `58f7fec` (test), `5e34791` (record) (#151, merged as `5d15b23`); this close-out |
| **Status** | DONE |
| **Change type** | tests (OS image: `greenboot-unapplied-update`'s tests) |

## Intent: the owner's words

- "Next" (2026-11-21), after the deployment tests' close-out (#150), whose Next was this case.

## What exists

- The deployment tests' verifier, Minor 1 (`docs/build-records/2026-11-21-boot-counter-deployment-tests.md`): changing `arm`'s `DEPLOYMENT.fullmatch` to `DEPLOYMENT.match` survives every test.
- A note of a valid deployment path followed by a suffix would then pass the pattern, and rest on `deployment_kept` alone. Every suffix case today names a path that does not exist.

## Task Contract

1. **Outcome:** a change that lets `arm` accept a note whose deployment path only begins with a valid one fails the gate.
2. **Scope:** routine (tests only; no behaviour change). One case in `Arm.test_a_deployment_the_pattern_alone_refuses`, `image/tests/test_greenboot_unapplied_update.py`:
   - the path `DEPLOY + "/../../../../../" + DEPLOY`, which climbs from the applied deployment back to the sysroot and down to that deployment again;
   - the path exists, asserted with `deployment_kept`, so only `fullmatch` refuses it.

   **Not included:** code changes; anything else in the backlog.
3. **Done when:**
   - the full gate passes in CI;
   - one verifier pass finds, by reading, that the case passes against the code as it is and fails under `.match`.
4. **Authority:** the test file and this record. On the Mac: `ast` parse checks and `git diff --check`. The tests run in CI only. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Test, `58f7fec`

- `Arm.test_a_deployment_the_pattern_alone_refuses`: a third subtest, the note `<digest> ` + `DEPLOY + "/../../../../../" + DEPLOY`.
  - The five `..` climb from the applied deployment's folder back to the sysroot, so the path names that deployment, and `deployment_kept` is True (asserted).
  - `DEPLOYMENT.fullmatch` refuses it; `DEPLOYMENT.match` matches the valid prefix, and `arm` would set the counter.
- **Reason:** a new case in an existing test, stricter; nothing else changed, no code changed.
- Checked by reading against the code as it is: it passes. Under `.match` it fails.
- On the Mac: the file parses; `git diff --check` clean. The tests run in CI.

### CI on `5e34791`: Pass

- `Full gate (Ubuntu)`, [run 44924362489](https://github.com/rikuripi/rikurinode/actions/runs/44924362489): success; `Ran 691 tests … OK`. The same count as #149, because the new case is a subtest.
- The OS image, [run 44924362508](https://github.com/rikuripi/rikurinode/actions/runs/44924362508): success.
- The owner merged #151 as `5d15b23`.

### Verifier, `5e34791`: PASS (round 1)

- The diff changes no code and loosens no case; the reason is given.
- By reading:
  - the path climbs exactly five levels back to the sysroot, so `deployment_kept` is True;
  - `fullmatch` refuses the note, so the case passes;
  - under `.match`, `arm` sets the counter, so the case fails.
- **Hand mutations: Not yet proven by running**; worked through by reading.
  - **Caught:** dropping the newline check, `split()` for `split(" ")`, dropping `0|`, a serial of one digit, and each narrowing of the stateroot class.
  - **Equivalent for every note `note` writes:** `>= 2` parts, `IMAGE_DIGEST.match` or no digest check (the trigger must equal the digest), and any loosening of `DEPLOYMENT` (the `..` cases rest on `deployment_kept`).
- **Important: none.** Minor:
  1. Two stricter mutants on lines this change did not touch survive, both failing closed (nothing armed, greenboot counting as alone):
     - `DEPLOYMENT`'s checksum class without digits (every `arm` test's checksum is `d` × 64);
     - the stateroot's first character without digits.
     - The fix: an `arm` case whose checksum mixes digits and letters and whose stateroot starts with a digit.
  2. The risk tier: routine, for a test on high-risk code; the review went to high-risk depth.
  3. This record's status and CI evidence, added here.

## Outcome

- **DONE.** `arm`'s note pattern must match the whole deployment path: a valid path with a suffix now fails the gate if accepted.
- **Backlog, not started:** Minor 1, one positive `arm` case with digits in the checksum and a stateroot starting with a digit.
