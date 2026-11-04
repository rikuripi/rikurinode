# Build Record — a test for the `/run` override of the containers user, and the Fedora 45 record's close-out

| | |
|---|---|
| **Date** | 2026-11-04 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/f45-run-override-test`, from `main` at `f17057b`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `229bcf8` (the test), `4c43fb3` (the Fedora 45 close-out); merged as `1c5301f` (#64) |
| **Status** | DONE |
| **Change type** | test (a missing case) and record |

## Task Contract

1. **Outcome:** the image check's refusal of a `/run/sysusers.d` copy of the `containers` user's file is held by a test, so removing it can no longer pass unseen; and the Fedora 45 record on `main` says how that task ended.
2. **Scope:** stage 1, the OS image (owner, 2026-11-04: "Small follow-up PR (Recommended)", for the verifier's finding I-1 on #63).
   - `image/tests/test_check_image_root.py`: one new test, `test_containers_user_overridden_in_run`, beside the `/etc` one. No existing test changes.
   - `docs/build-records/2026-11-03-fedora-45.md`: its close-out (CI on `9570d03`, the verifier's follow-up, the merge, I-1 and this task, status).
   - Risk tier: **high-risk** (a validation check of the image), but no code changes: `check_image_root.py` already refuses the path.
   - **Not included:** the verifier's two nits (no unit test reaches `System.write_storage_conf`; the sysusers comment's "no home of its own"); the installer power-off task.
3. **Done when:**
   - the new test passes on `main`'s code, and fails on a mutant without `run/sysusers.d/rikuri-containers.conf` in `CONTAINERS_USER_OVERRIDES` (rikuri-drill, `safe-run.sh`);
   - `image/tests` passes; `git diff --check` is clean;
   - on the PR, `Full gate (Ubuntu)` passes.
   - An independent check is not required: the change is one test that adds a case and touches no code. The mutant run above is its proof.
4. **Authority:** the owner's words above; this branch; one draft PR; no merge.
5. **Limits:** one task; two repair cycles; two review rounds; development CI at most 2 runs.

## Evidence log

- **The gap** (the verifier's follow-up pass on #63, finding I-1): with `"run/sysusers.d/rikuri-containers.conf"` removed from `CONTAINERS_USER_OVERRIDES` (`image/check_image_root.py`), all 118 tests of `test_check_image_root.py` passed; only the `/etc` override had a test. Confirmed with `git grep -n "sysusers.d" -- image/tests`: one test, the `/etc` one.
- **The test** (rikuri-drill, `safe-run.sh`, as the gate runs it):
  - on `main`'s code: `image/tests` `Ran 370 tests` `OK`;
  - on the mutant (`CONTAINERS_USER_OVERRIDES = ("etc/sysusers.d/rikuri-containers.conf",)`): `Ran 119 tests` `FAILED (failures=1)`, `FAIL: test_containers_user_overridden_in_run`, `expected a finding with 'run/sysusers.d/rikuri-containers.conf: overrides', got []`.
  - A test that passes at once is expected here: the code was already right, and the mutant is the red run.
- `git diff --check`: clean. No existing test changed.

## Close-out

- **CI on `4c43fb3`:** [Full gate](https://github.com/rikuripi/rikurinode/actions/runs/41765915905) passed. The [OS image workflow](https://github.com/rikuripi/rikurinode/actions/runs/41765915967) ran too, because `image/tests/` is in its path filter: the build, the drill and the install test passed. That was 1 CI run of the 2 allowed.
- **Merged** by the owner as `1c5301f` (#64, 2026-11-04T03:28:11Z). This close-out lands with the next task's PR (`docs/build-records/2026-11-04-installer-power-off.md`), so it needs no PR of its own.
