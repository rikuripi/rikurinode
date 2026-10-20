# Build Record — safe-run.sh refuses when loopback cannot come up

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Author / session** | Claude (Opus 5.5, cloud session linked to the owner's Mac) for Henry Chen |
| **Branch** | `fix/safe-run-loopback`, from `main` at `c3b4c70`, in a clone at `/home/claude/rikurinode` in the cloud session |
| **Commits** | `d750045` (the red tests and this record), `cc6dd73` (the fix), the next commit (these rows); the pre-commit hook ran on each (gitleaks "no leaks found"). Pushed and opened as a pull request on the owner's word ("Record PR and safe-run.sh backlog item.", 2026-10-20) |
| **Status** | DONE locally: one `verifier` pass **PASS**, no Important finding, 8 of 8 hand mutants killed; CI's `Full gate (Ubuntu)` on the pull request Not yet proven when this row was written |
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
- [x] **Protected-path risk note** (`scripts/quality` is listed in `.claude/hooks/guard-config.json`): the change makes the layer refuse in one more case and weakens nothing; the no-namespace path, the stand-ins and the start-time check are untouched. Worst case: a machine without iproute2 can no longer run tests through the layer until `ip` is installed, and the message says so.
- [x] **Risks:** a test that fakes a failing `ip` could pass for the wrong reason (the fake not resolving), so it asserts the fake is what resolves; the refusal must not leave the stand-in folder behind.
- [x] **Verification defined up front:** I will know this works when the refusal test is red on the old script and green on the new one, and the loopback test passes wherever `ip` works.

## 2. Build

- [x] New code meets the bar: one line in the inner script, in the same form as the `/run` refusal above it; `ip`'s own error now reaches stderr; the header comment says what happens.
- [x] Clean as you go: the `2>/dev/null` that hid the error is gone; nothing else to remove.
- [x] Security question answered: touches the test boundary, not auth, money or keys. A refusal is the safe direction: no command runs in a namespace whose state the layer did not set up. The no-namespace path is unchanged. Proof: the two tests, and the refusal observed end to end.

## 3. Debug

- [x] Reproduced before fixing: on `main`, in this session, the control plane's `plain_listener` and `sign_in` suites failed with `NetworkUnreachable` through `safe-run.sh`, and `test_loopback_is_up_inside` failed with `DOWN [Errno 101] Network is unreachable`.
- [x] Failing test written and SEEN failing: red commit `d750045`; on the old script `test_a_loopback_that_cannot_come_up_is_a_refusal` fails `AssertionError: 0 != 2 : RAN` (with and without the `ip` stand-in); fix-lock not engaged (opt-in), the red commit stands in for it.
- [x] Root cause is a CLASS: a setup step whose failure is discarded (`2>/dev/null` with no exit-code check), so the layer reports success for an environment it did not build — the "nothing important fails silently" class.
- [x] Swept for siblings: the other setup step in the inner script (`mount … /run`) already refuses; `mktemp` refuses (`|| exit 2`); `node_started` discards errors on purpose (no Docker means nothing to compare, and it says so). No other silent setup step in `safe-run.sh`.

## 4. Verify

- [x] Unit tests: `test_safe_run.py` 16 OK with an `ip` stand-in for `link set lo up` first on `PATH` (this session has no iproute2); the gate's step 3 suites (`scripts/quality/tests`, OK, 1 skipped as before) and step 2's guard tests (OK).
- [x] Watched it work: `scripts/quality/safe-run.sh echo RAN` without `ip` → `ip: command not found`, `safe-run: cannot bring loopback up inside the layer (is iproute2's ip installed?); refusing to run`, rc 2, nothing ran; the control plane's tests through the layer with loopback up: unit 104, `plain_listener` 3, `sign_in` 9, `status_route` 3, all ok; without `ip`, the same command is refused with rc 2.
- [x] Recovery/fallback path triggered: the refusal path, above; no stand-in folder left behind (`rikuri-safe-bin.*`: 0).
- [x] Regression guard proven to FAIL on the old code: the red commit, above.
- [x] Independent verification: one `verifier` pass, **PASS**. It re-ran the red commit in a scratch copy (fails as recorded), found no test loosened (`git diff d750045 HEAD -- scripts/quality/tests` empty), exercised the real entry point with and without `ip`, and killed all 8 hand mutants of the changed line (drop the check, `exit 0`, `exit 1`, `|| true`, the check after `exec`, the message removed, `ip`'s error hidden, `lo down`). Three nits: the risk note was not labelled (fixed above); two for the backlog, below.
- [x] Diff matches the plan: `safe-run.sh`, `test_safe_run.py` and this record.

## 5. Close Out

- [ ] Full gate: CI's `Full gate (Ubuntu)` on the pull request, Not yet proven when this record was closed. Locally: steps 2 to 6 green with `ip` present (the verifier's run); steps 1, 8 and 9 not run here (pinned toolchain unavailable; no Rust changed).
- [x] Scrap Sweep: the verifier's scratch copies are deleted; nothing else to remove.
- [x] Reviewed per `REVIEW.md`: the verifier's pass above.
- [x] Lesson loop: N/A (first occurrence; the class is an existing design rule).
- [x] Knowledge layer: AGENTS.md ("no network but loopback") and README ("a private loopback") already describe the intended behaviour; the script's header now names the refusal.
- [x] Commit message explains why: yes, each commit.

## Skipped items — visible, never silent

- **Full gate as one script:** see Close Out; CI's run counts.
- **Backlog nit 1:** on a machine without `ip`, `Namespace.setUp` reports "did not report namespace mode" and hides the layer's own refusal, so 12 failures do not point at iproute2. A follow-up could have `isolated()` surface the layer's stderr.
- **Backlog nit 2 (predates this change):** a refusal (rc 2) cannot be told apart from a command that itself exits 2; the `/run` refusal has the same shape.

## Evidence log

```
# red, old script (commit d750045), this session has no `ip`
$ python3 -m unittest scripts.quality.tests.test_safe_run.Namespace
FAIL: test_a_loopback_that_cannot_come_up_is_a_refusal   AssertionError: 0 != 2 : RAN
FAIL: test_loopback_is_up_inside                         AssertionError: 'DOWN [Errno 101] Network is unreachable' != 'UP'
# old script, `ip` stand-in for `link set lo up` first on PATH
FAIL: test_a_loopback_that_cannot_come_up_is_a_refusal   AssertionError: 0 != 2 : RAN   (15 others OK)

# green, fixed script
$ shellcheck --severity=style scripts/quality/*.sh scripts/quality/hooks/* scripts/cargo.sh      -> rc 0 (0.11.0)
$ scripts/quality/safe-run.sh echo RAN          (no ip)
safe-run: line 2: ip: command not found
safe-run: cannot bring loopback up inside the layer (is iproute2's ip installed?); refusing to run   -> rc 2
$ PATH=<ip stand-in>:$PATH python3 -m unittest scripts.quality.tests.test_safe_run           -> Ran 16, OK
$ PATH=<ip stand-in>:$PATH python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'  -> OK (skipped=1)
$ python3 -m unittest discover -s .claude/hooks -p 'test_*.py'                                 -> OK
$ PATH=<ip stand-in>:$PATH safe-run.sh cargo test --workspace ... (stable 1.97.0, --ignore-rust-version)
unit 104 ok; plain_listener 3 ok; sign_in 9 ok; status_route 3 ok
```
