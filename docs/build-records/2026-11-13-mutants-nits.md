# Build Record — the mutants step's two follow-up nits

| | |
|---|---|
| **Date** | 2026-11-13 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/mutants-nits`, from `main` at `c33274c`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `e616ff2` (contract), `3174db0` (change); merged as `b1f0113` (#98) |
| **Status** | DONE |
| **Change type** | refactor |

## Task Contract

1. **Outcome:** the mutants step's verdict is pinned by behaviour, not only by its text, and its header comment reads cleanly.
   - The owner said "Next" (2026-11-13) to the task proposed at the exit-3 fix's close-out: the verifier's nits 2 and 3 (`docs/build-records/2026-11-13-mutants-exit3.md`).
2. **Scope:** routine. The workflow's behaviour does not change: only a comment changes there, and a test is added.
   - `scripts/quality/tests/test_workflows.py`: `MutantsVerdict` gains `test_exit_2_with_no_list_fails`. Exit 2 with no `mutants.out` is how `safe-run.sh` refuses before cargo-mutants runs. The test kills the surviving mutant that widens the case to `0|2|3`.
   - `.github/workflows/mutants.yml`, the header comment only:
     - the line my exit-3 edit joined to the next sentence (126 columns) is rewrapped;
     - the record is cited by its full path, on the `Records:` line.
   - **Not included:** the `-f` → `-e` survivor (it differs only if `missed.txt` were a directory), and the exit-3-in-CI nit, which needs a real timeout.
3. **Done when:**
   - `test_workflows.py` passes on rikuri-drill through `safe-run.sh`;
   - the new case fails against the `0|2|3` mutant (a hand run, recorded here);
   - `git diff --check` is clean;
   - CI's full gate passes on the PR;
   - one verifier pass (the change has test code).
4. **Authority:** these files. Python on rikuri-drill through `safe-run.sh`. Commit, push and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Change and evidence

- `test_exit_2_with_no_list_fails` is added. It is stricter, and no existing assertion changes.
- The header comment is rewrapped. Every comment line in it is now 80 columns or fewer, and it cites both records by path.
- On rikuri-drill, through `safe-run.sh`:
  - `test_workflows.py` as written: `Ran 64 tests … OK`.
  - With the copy's case widened to `0|2|3` by `sed` (one line matched): `FAIL: test_exit_2_with_no_list_fails` and `Ran 9 tests … FAILED (failures=1)`. That is the only failure, so this case is what kills that mutant.
- `git diff --check` is clean.

### CI on `3174db0`: Pass

- [CI 43549044003](https://github.com/rikuripi/rikurinode/actions/runs/43549044003) (`Full gate (Ubuntu)`, `Ran 209 tests`).
- [Rust mutants 43549044046](https://github.com/rikuripi/rikurinode/actions/runs/43549044046).
- [OS image 43549043943](https://github.com/rikuripi/rikurinode/actions/runs/43549043943).
- [Guard and quality tools 43549044064](https://github.com/rikuripi/rikurinode/actions/runs/43549044064): `test_exit_2_with_no_list_fails … ok` on py3.9 and py3.12.
- The owner merged #98 at `3174db0` (as `b1f0113`) before the verifier ran.

### The verifier, at `3174db0`: PASS

- **The workflow:** only comments change, and the widest header line is 77 columns. Both cited records exist.
- **The new test's premise:** `safe-run.sh` exits 2 before the command runs, at lines 26, 28, 47-48 and 61.
- **The mutant:** the step script under `bash -e`, with the test's stand-in, original against `0|2|3`. Only "2, no list" differs (2 against 1), so the new test kills it.
- **The diff:** one added method, no assertion changed, and `git diff --check` is clean.
- **Findings:** no Important finding. The one nit is this close-out.

### Close-out

- **Done when:** met. The tests passed on rikuri-drill and in CI, the mutant was killed by hand on rikuri-drill and by the verifier, the gate passed, and the verifier passed.
- **Repairs:** 0. Review rounds: 1.
- **Still open, not started:** the `-f` → `-e` survivor (it differs only for a directory) and a real exit 3 in CI. Both are recorded in `2026-11-13-mutants-exit3.md`.
