# Build Record — Unit tests for the drill's containers-range steps and its verdict

| | |
|---|---|
| **Date** | 2026-10-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/drill-orchestration-tests`, from `main` at `c588fb7`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | refactor and tests (the CI drill, a control) |

## Task Contract

1. **Outcome:** a change that weakens the drill's containers-range checks, or drops a check from its pass list, fails the unit tests in seconds, not only (or never) in a 20-minute CI drill.
2. **Scope:** verifier nit 2 of `docs/build-records/2026-10-24-drill-first-boot-and-finalize.md`.
   - `image/drill/vm_drill.py`:
     - the pass rule at the end of `main` becomes a module constant `EXPECTED` and a pure `verdict(results, error)`, with the same behaviour;
     - no other change.
   - `image/tests/test_vm_drill.py`:
     - tests for `verdict` and `EXPECTED`;
     - tests for `Drill.subid_first_boot` and `Drill.subid_after_reboots`, through a `Drill` whose `vm` and `journal` are stand-ins (no VM, no subprocess).
   - Risk tier: **high-risk** (the drill is a control).
   - **Not included:**
     - any other drill method;
     - `image/rootfs`;
     - the checker;
     - nit 6 (post-mortems kept by run id).
3. **Done when:**
   - the `verdict` tests are committed failing first (the function does not exist), then pass;
   - the method tests pass, and hand mutants of `subid_first_boot` (drop `once and`, drop `subid_added`, read the journal without `-b`) and of `verdict` (drop a name from `EXPECTED`, ignore a failing check, ignore `error`) each turn the suite red;
   - the CI drill on the pull request passes 7 of 7;
   - `Full gate (Ubuntu)` passes;
   - one `verifier` pass has no Important finding.
4. **Authority:**
   - the owner's "Next" (2026-10-24), after this was named as the next task;
   - edit the files in Scope;
   - run the tests in `rikuri-drill` as before;
   - push this branch and open the pull request; no merge;
   - CI drill development runs: at most 1;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 1 hour.

## 0b. Spec

- [x] **Why a refactor:** `main` cannot be unit-tested without a VM; the pass rule is the part that can silently lose a check (a name missing from the set passes whatever that check did). Lifting it out unchanged makes it testable; `main` keeps its order and its error handling.
- [x] **Why stand-ins over `vm`/`journal`:** `Drill.__init__` has no side effects, and `subid_files`, `keep` and `check` then run for real (`keep` writes to a temporary artifacts folder).

## Evidence log
