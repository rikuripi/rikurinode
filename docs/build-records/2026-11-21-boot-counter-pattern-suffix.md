# Build Record — the deployment pattern held whole by a test (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-21 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-counter-pattern-suffix`, from `main` at `657aaf5`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `afc1c75` (contract), `58f7fec` (test), and this record |
| **Status** | IN PROGRESS |
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
