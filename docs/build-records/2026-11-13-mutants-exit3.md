# Build Record — a timeout no longer hides missed mutants

| | |
|---|---|
| **Date** | 2026-11-13 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/mutants-exit3`, from `main` at `85b7992`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `2e4859b` (contract), `c7255aa` (red), `25f1dc4` (fix), `1611bc5` (repair 1); merged as `b78aab3` (#96) |
| **Status** | DONE |
| **Change type** | fix |

## Intent: the owner's words

- "Next" (2026-11-13), answering the proposed next task: "fix the control defect in `mutants.yml` (its handling of cargo-mutants' exit code 3)".
- The defect, as 5c.4b-1's verifier found it (`docs/build-records/2026-11-13-5c4b1-rename-engine.md`, its first pass): "`.github/workflows/mutants.yml:86` accepts cargo-mutants' exit code 3. Here 2 timeouts produced exit 3 and masked 14 missed mutants, so the check went green. Fixing it is its own control task."
- What stays: the owner's 2026-11-06 rules, "Fail the job" on a missed mutant, and timeouts pass because the tests did not pass under that mutant (`docs/build-records/2026-11-06-ci-cargo-mutants.md`).

## Task Contract

1. **Outcome:** the Rust mutants check fails whenever a mutant was missed, even when another mutant timed out in the same run.
2. **Scope:** high-risk: it changes a CI control (BUILD-PROCEDURE, "Risk tiers").
   - Files:
     - `.github/workflows/mutants.yml`: the mutation step only, plus its header comment;
     - `scripts/quality/tests/test_workflows.py`: the `Mutants` tests;
     - this record.
   - **Not included:**
     - the timeout policy (timeouts still pass);
     - the run's flags, the pinned binary, the triggers or the report steps;
     - other workflows;
     - making the check required.
3. **Done when:**
   - A new test runs the mutation step's own script under `bash -e`, with a stand-in for `safe-run.sh` that sets the exit code and writes `mutants.out`. It shows:
     - exit 3 with a missed mutant fails;
     - exit 3 with no `missed.txt` fails;
     - exit 0 and 3 with an empty `missed.txt` pass;
     - exit 2 and 4 fail.
   - That test is seen failing on the current workflow, then passing on the fix: `scripts/quality/tests` on rikuri-drill through `safe-run.sh`.
   - The full gate passes in CI on the PR, and the mutants workflow runs on it (it triggers on its own file).
   - The verifier passes.
4. **Authority:**
   - Edits to the files above.
   - Python tests on rikuri-drill through `safe-run.sh`, and `git diff --check` on the Mac.
   - Read-only `gh` for cargo-mutants' v27.1.0 source and the CI runs.
   - Commit and push to this branch, and a draft PR. The owner merges.
   - An independent check is required: the verifier, with hand mutations.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured, so I report what was used.

## Design notes (before any edit)

- **cargo-mutants v27.1.0's rule** (`src/outcome.rs:110-124`, read at the tag):
  1. a failed baseline gives 4;
  2. otherwise, any timeout gives 3;
  3. otherwise, any missed mutant gives 2;
  4. otherwise, 0.

  So exit 3 says nothing about missed mutants. The current `0|3) ;;` passes a run that missed some, if any other mutant timed out.
- **`missed.txt` is created when `mutants.out` is**, before any mutant runs (`src/output.rs:116-149`). One missed mutant is one line.
- **The fix:**
  - exit 0 and 3 pass only when `$RUNNER_TEMP/mutants.out/missed.txt` exists and is empty;
  - a non-empty `missed.txt` fails with exit 2;
  - a missing one fails with exit 1, because it is not readable evidence that nothing was missed.

  Any other exit still fails, as now.
- **Rejected:**
  - Counting the "missed" lines in the console output: that's text, not a file the tool writes for this.
  - Failing on timeouts: the owner's policy, outside this task.
  - `--json` parsing: more surface, and it says the same thing.
- **Why the test runs the script:** the current tests compare the step's lines. They pinned `0|3) ;;` exactly, so they held the defect in place. A test that runs the script checks what it does.

## Evidence log

### Red (the current workflow)

- `MutantsVerdict` runs the mutation step's own `run:` script under `bash -e`, with a stand-in `scripts/quality/safe-run.sh`. That stand-in creates `mutants.out`, writes `missed.txt` (or doesn't) and exits with the code given.
- On rikuri-drill: `scripts/quality/safe-run.sh python3 -B -m unittest scripts/quality/tests/test_workflows.py -k Mutants`. The result was `Ran 24 tests … FAILED (failures=3)`, all `AssertionError: 0 == 0`:
  - `test_a_timeout_does_not_hide_a_missed_mutant`: exit 3 with one missed mutant passes. This is 5c.4b-1's defect, reproduced.
  - `test_a_timeout_with_no_missed_list_fails`
  - `test_no_missed_list_fails_even_on_success`
- Exit 0 and 3 with an empty list pass; 2 and 4 fail, as now. The 17 line-checking `Mutants` tests pass.
- This red run is recorded here. CI will also see red only if its run on the red commit is not cancelled by the fix's push.

### Fix

- `.github/workflows/mutants.yml`, the mutation step: after the existing `case`, which still passes 0 and 3 and fails any other exit, two more lines:
  - no `missed.txt` fails with exit 1;
  - a non-empty one fails with exit 2.
  The header comment says so.
- **A test change after red, with its reason:** `test_the_mutation_step_is_exactly_this` now lists the step's three new lines. It still pins the whole step, so the line checks keep refusing an added `exit 0`, `2) ;;` or `if: false` (2026-11-06's verifier, round 1).
- On rikuri-drill, through `safe-run.sh`:
  - `test_workflows.py`: `Ran 62 tests … OK`, all 7 `MutantsVerdict` cases included.
  - The whole `scripts/quality/tests`: `Ran 207 tests … FAILED (errors=7, skipped=1)`. All 7 errors are `FileNotFoundError: … 'git'` in `test_repo_hygiene.WholeRepository` and `test_advisory_audit_age.Remotes`: the drill VM has no `git`, and the copied tree is not a checkout. They are outside this change; CI runs them.

### A defect in the fix, found before CI, and its correction

- **Found by reading cargo-mutants v27.1.0** after pushing `25f1dc4`. An empty diff, a diff with no Rust source, or one that matches no mutant gives exit 0 *before* `mutants.out` exists (`src/main.rs:596-606`, `src/in_diff.rs:47-51`).
  - `25f1dc4` would fail every such run with "wrote no missed.txt". That includes this PR's own mutants run, which changes `mutants.yml` and no Rust.
  - The design note above ("missing is not readable evidence") was wrong for exit 0.
- **Correction:** a missing `missed.txt` fails only when the exit is not 0. Exit 3 always means mutants ran, so its list must exist. A non-empty list fails with any exit.
- **Test changes after red, each with its reason:**
  - `test_no_missed_list_fails_even_on_success` is replaced by `test_nothing_to_mutate_passes` (exit 0, no `mutants.out`: pass). The red test asserted behaviour cargo-mutants contradicts, as cited above. It kills `25f1dc4`'s version.
  - Added `test_success_with_a_missed_mutant_listed_fails`: exit 0 with a listed mutant fails. This is stricter.
  - The stand-in now creates `mutants.out` only when it writes a list, as cargo-mutants does in the no-mutants case.
  - `test_the_mutation_step_is_exactly_this` pins the corrected line.
- On rikuri-drill, `test_workflows.py`: `Ran 63 tests … OK`, all 8 `MutantsVerdict` cases included.
- **Counted as repair 1 of 2.** It was found before CI, but after the fix was pushed.

### CI

- **On `25f1dc4` (the first fix): Fail, as predicted above.**
  - `Rust mutants` [run 43547528497](https://github.com/rikuripi/rikurinode/actions/runs/43547528497): `INFO Diff file is empty`, then `cargo-mutants exited 0 but wrote no missed.txt`, exit 1.
  - CI 43547528415 was cancelled by the next push.
- **On `1611bc5` (repair 1): Pass.**
  - `Full gate (Ubuntu)` [run 43547640347](https://github.com/rikuripi/rikurinode/actions/runs/43547640347): `scripts/quality/tests` `Ran 208 tests … OK`.
  - `Rust mutants` [run 43547640411](https://github.com/rikuripi/rikurinode/actions/runs/43547640411): the real nothing-to-mutate path (`Diff file is empty`), passed.
  - OS image [run 43547640342](https://github.com/rikuripi/rikurinode/actions/runs/43547640342) and guard/quality [run 43547640529](https://github.com/rikuripi/rikurinode/actions/runs/43547640529): passed.
- The owner merged #96 at `1611bc5` (as `b78aab3`) before the verifier ran.

### The verifier, at `1611bc5`: PASS

- **The premises, against cargo-mutants v27.1.0's source:**
  - the exit-code order;
  - `missed.txt` is created before any mutant runs, and every missed mutant is both counted and listed from one `summary()`;
  - exit 3 only ever comes after `mutants.out` exists;
  - no exit 0 can carry a missed mutant.
- **The script under `bash -e`:** run in scratch for rc 0, 1, 2, 3, 4, 5, 6, 70, 125 and 126, each with the list absent, empty and listed. Only 0 (no list, or an empty one) and 3 (an empty list) pass.
- **The red reproduced:** on `c7255aa`'s workflow, 3 cases fail. On `25f1dc4`'s, only `nothing_to_mutate` fails.
- **19 hand mutations:** 17 killed by `MutantsVerdict`. 2 survive the behaviour tests and are caught by the line pin: `0|2|3` and `-f` → `-e`. Both behave the same today.
- **Test changes after red:** each reason holds, including replacing `test_no_missed_list_fails_even_on_success`.
- **Nits, not fixed here:**
  1. this record's close-out (answered here);
  2. a `verdict(2, None)` case would kill `0|2|3` by behaviour;
  3. the header comment's new line is about 125 columns, and it cites the record by bare filename;
  4. a real exit 3 with a missed mutant has not been seen in CI.

### Close-out

- **Done when:**
  - the 8 behaviour cases were red, then green, on rikuri-drill;
  - the gate passed in CI on the merged code, and the PR's own mutants run passed through the real empty-diff path;
  - the verifier passed.
- **Not yet proven:** a real cargo-mutants exit 3 beside a missed mutant. Only the stand-in covers it; the first real timeout on a Rust PR will show it.
- **Repairs:** 1 of 2. Review rounds: 1.
- **Used:** no budget is configured. There were five CI pushes across PRs #96 and this one, and one verifier pass.
- **Backlog, not started:** the verifier's nits 2 and 3, as one small follow-up to the workflow and its tests.
