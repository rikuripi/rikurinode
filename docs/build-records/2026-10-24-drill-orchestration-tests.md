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

- **Red** (`01-red-tests.out`, commit `8e325df`):
  - 165 tests ran; the 5 `Verdict` tests failed, each an `AttributeError` for `EXPECTED`;
  - the 6 `ContainersRangeSteps` tests passed on the unchanged methods, as they should.
  - A first try errored the whole module: a class attribute read `d.EXPECTED` at import, so nothing in the file ran. I moved it into `setUp` before committing, so red is only the missing function.
  - Run in `rikuri-drill` (`safe-run.sh` refuses on macOS); the CI gate runs the tests through it.
- **Fix** (commit `4146c8f`):
  - `EXPECTED` (a frozenset of the same seven names) and `verdict(results, error)` (the same expression) are now module-level; `main` returns `verdict(drill.results, error)`.
  - Nothing else in the drill changed.
- **Green** (`02-green-tests.out`): 165 tests, OK.
- **Mutants** (`03-mutants.out`; each applied, checked to differ, then reverted), all red:
  - first-boot check without `once and`: 3 failures;
  - without `subid_added`: 1;
  - journal read without `-b`: 2;
  - "the containers range at the first boot" dropped from `EXPECTED`: 1, caught by the explicit set test (the missing-check test iterates `EXPECTED` itself, so it cannot see a name dropped from it);
  - failing checks ignored: 1;
  - `error` ignored: 1.
