# Build Record — two tests for the boot counter's deployment check (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-21 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-counter-deployment-tests`, from `main` at `771c7cd`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `265c0fc` (contract), `04f48f4` (tests), and this record |
| **Status** | IN PROGRESS |
| **Change type** | tests (OS image: `greenboot-unapplied-update`'s tests) |

## Intent: the owner's words

- "Next" (2026-11-21), after the cancelled-update fix's close-out (#148), whose Next was these two tests.

## What exists

The cancelled-update fix's verifier (`docs/build-records/2026-11-20-boot-counter-cancelled.md`, round 1, Minor 1 and 2) found two kinds of mutant of `greenboot-unapplied-update` that no unit test catches.

1. **`arm` without `DEPLOYMENT.fullmatch`.** Every malformed note's deployment path is refused anyway by `deployment_kept`, because no such path exists. So nothing tests the pattern itself. Two notes it alone refuses: an absolute path to a deployment that exists elsewhere, and a path climbing back through `..` to the applied deployment.
2. **Stricter patterns.** `STATEROOT` and `DEPLOYMENT` without `_` or `A-Z`, or `DEPLOYMENT` with only serial `0`, would refuse a real update:
   - a re-staged image gets serial 1 or more;
   - a stateroot may hold capitals or `_`.

   That fails closed, but a node would then count as greenboot alone counts. No test notes and then arms a deployment of serial ≥ 1, or one with such a stateroot.

## Task Contract

1. **Outcome:** the deployment check's patterns are held by tests, so a change that loosens or narrows them fails the gate.
2. **Scope:** routine (tests only; no behaviour change).
   - `image/tests/test_greenboot_unapplied_update.py`:
     - a round trip: `note` writes a note for stateroot `Fedora_IoT-2.x` and serial 12, and `arm` arms from that very file, with that deployment applied under the sysroot;
     - two notes refused by the pattern alone, each naming a deployment that exists: an absolute path, and one through `..`.
   - **Not included:** code changes; the three wording nits of #148's verifier; anything else in the backlog.
3. **Done when:**
   - the full gate passes in CI;
   - one verifier pass finds, by reading, that the mutants above now fail a test, and that the new tests pass against the code as it is.
4. **Authority:** the test file and this record. On the Mac: `ast` parse checks and `git diff --check`. The tests run in CI only (`safe-run.sh` cannot run on this Mac). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Tests, `04f48f4`

- `Arm.test_a_note_and_its_arm_for_any_stateroot_and_serial`:
  - `note` writes `<digest> ostree/deploy/Fedora_IoT-2.x/deploy/<checksum>.12` from bootc's status;
  - the staged state is then removed and the deployment is made, as finalize leaves it;
  - `arm`, reading that very file, sets `boot_counter=3 boot_success=0`.
  - Catches: `STATEROOT` without `A-Z` or `_` (nothing noted), and `DEPLOYMENT` without them or with only serial `0` (nothing armed).
- `Arm.test_a_deployment_the_pattern_alone_refuses`: two notes, each naming a deployment that is there (asserted with `deployment_kept`), so only `DEPLOYMENT` refuses them: an absolute path to a deployment elsewhere, and a path back through `..` to the applied one. Catches: `arm` without `DEPLOYMENT.fullmatch`.
- **Reason:** new tests only; no existing test changed, no code changed.
- Checked by reading against the code as it is: both pass. Each mutant above fails one of them.
- On the Mac: the file parses; `git diff --check` clean. The tests run in CI.
