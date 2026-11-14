# Build Record — the mutants step's two follow-up nits

| | |
|---|---|
| **Date** | 2026-11-13 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/mutants-nits`, from `main` at `c33274c`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
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
