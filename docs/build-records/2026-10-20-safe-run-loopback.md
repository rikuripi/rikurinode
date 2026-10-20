# Build Record — safe-run.sh refuses when loopback cannot come up

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Author / session** | Claude (Opus 5.5, cloud session linked to the owner's Mac) for Henry Chen |
| **Branch** | `fix/safe-run-loopback`, from `main` at `c3b4c70`, in a clone at `/home/claude/rikurinode` in the cloud session |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | fix (a control: the test-safety layer) |

## Task Contract

1. **Outcome:** when the test-safety layer cannot bring loopback up inside its namespace, it refuses with a message that names the cause, instead of running the command with loopback down and letting every test that listens on 127.0.0.1 fail with `NetworkUnreachable`.
2. **Scope:** `scripts/quality/safe-run.sh` (the inner script's `ip link set lo up` line and the header comment), `scripts/quality/tests/test_safe_run.py` (two tests), and this record. Tier: **high-risk** (a control that enforces the test boundary, BUILD-PROCEDURE.md, "Risk tiers"; `scripts/quality` is a protected path). **Not included:** the no-namespace path (it never calls `ip`), the stand-in list, CI, the guard, AGENTS.md (its "no network but loopback" already states the intended behaviour), installing iproute2 anywhere.
3. **Done when:** a new test, run on the old script, fails because the layer ran the command although `ip` failed (the red commit); with the fix it passes; a second test shows a listener inside the layer reachable on 127.0.0.1 (loopback is up); every other test in `test_safe_run.py` still passes; shellcheck at the pinned 0.11.0 passes; the verifier's pass, with hand mutations of the changed line, has no Important finding; CI's `Full gate (Ubuntu)` is green on the pull request.
4. **Authority:** the owner, 2026-10-20: "Record PR and safe-run.sh backlog item.", answering the proposal "`safe-run.sh` should refuse outright when the `ip` tool is missing, instead of failing silently and leaving loopback down". Edit the files in Scope on this branch; commit (red test first, fix in its own commit), push, open one pull request; one verifier pass. No merge.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured.

## 0. Intent

- [x] **Problem, in the owner's words:** "Record PR and safe-run.sh backlog item." (2026-10-20). The backlog item came from the RUSTSEC-2026-0382 verifier: "`safe-run.sh` discards the error of `ip link set lo up`, so a missing iproute2 shows up as confusing loopback failures instead of a refusal."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** every local test run on a machine whose `ip` is missing or cannot set the link up. CI's runner (ubuntu-24.04) has iproute2; on it nothing changes.
- [x] **Open questions:** none.
- [x] **Owner approved the intent:** the message above.

## 0b. Spec

- [x] **Requirements:** inside the namespace, a failure to bring `lo` up stops the run before the command starts, with exit 2 (the script's refusal code, as for "cannot hide /run") and a message naming loopback and `ip`; the command's own result still passes through when loopback comes up.
- [x] **Design:** `ip link set lo up || { echo "safe-run: cannot bring loopback up inside the layer …" >&2; exit 2; }` in the inner script, keeping `ip`'s own error on stderr. Rejected: a fallback that sets the flag another way (a second mechanism to keep working and test, for machines without a standard tool); carrying on with a warning (the old silent failure, made louder but still a wrong environment for every test).
- [x] **Policy applied:** "Nothing important fails silently" (AGENTS.md > Design rules); the first principle: this changes a default (run with a broken loopback → refuse), stated here and put to the owner in the pull request; it is reversible.
- [x] **Flagged concerns:** a machine that ran tests through safe-run without iproute2 now gets exit 2 instead of a run whose loopback tests fail; the message tells it what to install.

## 1. Plan

- [x] **One sentence:** stop discarding `ip link set lo up`'s failure in the inner script and refuse, with a red test first.
- [x] **Blast radius:** the inner script of the namespace path; nothing irreversible.
- [x] **Current behaviour characterized:** this cloud session has no `ip` binary. `scripts/quality/safe-run.sh python3 -c` with a listener on 127.0.0.1 inside the layer fails with `NetworkUnreachable`; on `main` the `plain_listener` (3) and `sign_in` (9) suites failed that way today (`docs/build-records/2026-10-20-rustsec-2026-0382.md`). With a stand-in for `ip link set lo up` first on `PATH`, they pass.
- [x] **Files and order:** this record, the two tests (red commit), the fix (its own commit), the checks.
- [x] **Risks:** a test that fakes a failing `ip` could pass for the wrong reason (the fake not resolving), so it asserts the fake is what resolves; the refusal must not leave the stand-in folder behind.
- [x] **Verification defined up front:** I will know this works when the refusal test is red on the old script and green on the new one, and the loopback test passes wherever `ip` works.

## 2. Build

- [ ] New code meets the bar:
- [ ] Clean as you go:
- [ ] Security question answered:

## 3. Debug

- [ ] Reproduced before fixing:
- [ ] Failing test written and SEEN failing:
- [ ] Root cause is a CLASS:
- [ ] Swept for siblings:

## 4. Verify

- [ ] Unit tests:
- [ ] Watched it work:
- [ ] Recovery/fallback path triggered:
- [ ] Regression guard proven to FAIL on the old code:
- [ ] Independent verification:
- [ ] Diff matches the plan:

## 5. Close Out

- [ ] Full gate:
- [ ] Scrap Sweep:
- [ ] Reviewed per `REVIEW.md`:
- [ ] Lesson loop:
- [ ] Knowledge layer:
- [ ] Commit message explains why:

## Skipped items — visible, never silent

- (none yet)

## Evidence log

```
```
