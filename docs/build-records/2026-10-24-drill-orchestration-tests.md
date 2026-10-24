# Build Record — Unit tests for the drill's containers-range steps and its verdict

| | |
|---|---|
| **Date** | 2026-10-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/drill-orchestration-tests`, from `main` at `c588fb7`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | red `8e325df`, fix `4146c8f`, record `9a08b61`; merged as `66e88cb` (#37); this close-out |
| **Status** | DONE: pull request #37 green at `9a08b61` and merged by the owner (`Full gate (Ubuntu)` [run 40115835518](https://github.com/rikuripi/rikurinode/actions/runs/40115835518); the image build and the drill [run 40115835578](https://github.com/rikuripi/rikurinode/actions/runs/40115835578), 7 of 7 checks Pass) |
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
- [x] **Why stand-ins over `vm`/`journal`** (and a silent `log`): `Drill.__init__` has no side effects, and `subid_files`, `keep` and `check` then run for real (`keep` writes to a temporary artifacts folder).

## Evidence log

- **Red** (`01-red-tests.out`, commit `8e325df`):
  - 165 tests ran; the 5 `Verdict` tests errored (`FAILED (errors=5)`), each an `AttributeError` for `EXPECTED`;
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

### Verifier and CI

- **Verifier, one pass: no Important finding.**
  - `EXPECTED` and `verdict` are the old rule exactly; `main` is otherwise unchanged.
  - The red commit is red only for the stated reason.
  - The stand-ins replace `vm`, `journal` and `log` only.
  - It found no weaker variant that survives, apart from one that does not matter (`passed` built without the `ok` filter gives the same result whenever the `all(ok)` part holds).
  - Nits 2 and 3, the wording above ("errored", the silent `log`), are fixed in this close-out.
- **CI on `9a08b61`:**
  - `Full gate (Ubuntu)` Pass (run 40115835518).
  - The drill Pass (run 40115835578), 7 of 7, with "the containers range at the first boot: added in boot 1 to both files: True".

## 5. Close Out

- [x] **Done when:**
  - red, then green: Pass;
  - six mutants red: Pass;
  - the CI drill 7 of 7: Pass;
  - Full gate: Pass;
  - verifier with no Important finding: Pass.
- [x] **Limits:**
  - Repair cycles: 0 of 2.
  - Review rounds: 1 of 2.
  - CI drill development runs: 1 of 1. This close-out touches only `docs/`, so the image workflow skips its drill.
  - Time: within the 1-hour budget.
- [x] **Backlog, not started:**
  - verifier nit 4: `main` as a whole has no unit test (`return 0` there would survive);
  - nit 5: the `vm` stand-in raises where the real one returns `None`, so the unreadable-file path of `subid_files` is untested;
  - nit 1: the VM test runs copy macOS metadata (`tar:` warnings, `._*` files, `__pycache__`) into `rikuri-drill`. `COPYFILE_DISABLE=1` and an exclude in `vm_tests.sh` would quiet them.
