# Build Record — Case 1's timeout: an update dropped at shutdown, diagnosed

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/case1-finalize-evidence`, from `main` at `65c8e99`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `85823de` contract, `086f96e` red, `0824991` fix, `fc64269` record, `00d53bc` and `e4e3d3e` the verifier's nits, `6944e86`, `723eb4c` and this close the record |
| **Status** | DONE |
| **Change type** | fix (the drill's diagnosis of a real fault; the fault itself is the next task) |

## Why

Case 1 of the rollback drill (`image/drill/vm_drill.py`) stages a deliberately broken update, reboots, and waits up to 600 s for greenboot to roll it back. It timed out in 4 of the runs we have evidence for, and passed on re-run each time with no change. The owner chose "Re-run, then fix case 1" (5c.4a) and, once the cause was shown to be a dropped update rather than a slow test, "Diagnose first" (2026-11-11).

## Task Contract

1. **Outcome:** when a staged update is dropped at shutdown, the drill says so at once (case 1 Fail, "never applied", with ostree's own error and the shutdown order kept as evidence) instead of a 600 s timeout, and the owner has the cause recorded.
2. **Scope:** high-risk (the rollback drill is a control over the update path). Files:
   - `image/drill/vm_drill.py`: case 1 tells "rolled back" from "never applied" from bootc's status; on "never applied" it keeps ostree-finalize-staged's and boot.automount's journal of the boot that shut down, records case 1 as Fail with ostree's error, and goes on to the other cases;
   - `image/tests/test_vm_drill.py`: tests for those;
   - this record.

   **Not included:** fixing the race (no change to the image, its units or its kernel arguments); changing case 1's pass condition; any other drill case.
3. **Done when:**
   - this record names the cause with the evidence of each failing run;
   - red tests, committed and seen failing in CI, then passing after the fix: the status reader, the error reader, case 1's "never applied" path (Fail, the detail naming "never applied" and ostree's error, no wait for the 600 s), and its "rolled back" path (Pass, as before);
   - `Full gate (Ubuntu)` green on the PR, and the VM drills run on it: case 1 either passes or fails within one boot with "never applied" and ostree's error. The live "never applied" path is Not yet proven unless a run on the PR hits the race;
   - one verifier pass (with hand mutations of the changed checks), and the follow-up if needed.
4. **Authority:** the owner's "Go" and "Diagnose first" (2026-11-11). Edit the files in Scope. Read CI logs and drill evidence of this repository's runs with `gh` (data only, in the scratchpad). Python tests run on `rikuri-drill` through `scripts/quality/safe-run.sh`, as before (host key pinned). Commit, push this branch, open a draft PR. No change to the image, CI workflows, the gate or the guard. Verifier: required.
5. **Limits:** this task only; at most two repair cycles and two review rounds. No budget configured: CI minutes used are reported.

## Diagnosis (before any edit)

All from this repository's CI artifacts (`drill-evidence`), read in the scratchpad.

- **What fails.** At the shutdown after `bootc switch` to the broken image, `ostree-finalize-staged.service`'s stop exits 1 within about 60 ms:
  `ostree[2417]: error: Remounting /boot read-write: Invalid argument` (run 43126288251, attempt 1).
  The staged deployment is dropped, the VM boots the installed image again, and the image's own `rikuri-unapplied-update` logs "update … was never applied", clears greenboot's trigger and stays on the installed image: the safe path case 2b tests on purpose. bootc's status then shows `staged: null, rollback: null`, so case 1's wait for a rollback can only time out.
- **When.** systemd-gpt-auto-generator's `boot.automount` ("EFI System Partition Automount", on `/boot`) is stopped *before* finalize runs in every failing run, and *after* it in the passing one:

  | Run (drill evidence) | `Unset automount boot.automount` (serial line) | finalize's stop | ostree's error |
  |---|---|---|---|
  | 43126288251 attempt 1 (5c.4a run 5), fail | 1811 | 1916 | `Remounting /boot read-write: Invalid argument` |
  | 43120587044 (5c.4a run 2), fail | 1792 | 1911 | the same |
  | 43090784113 (5c.3a run 3), fail | 1799 | 1914 | the same |
  | 40057729110 (October's run 2), fail | 1739 | 1835 | not kept then (its post-mortem predates 5223dea) |
  | 43126288251 attempt 2, pass | 1963 | 1899 to 1957 | none: finalized |

- **Ruled out.** greenboot's "/boot is already read-only" at its trigger (it says the same in passing runs). The 600 s limit (case 1 passes in about 80 s when finalize works). The `--userns=auto` hypothesis (2026-10-24 record: 0 of 3).
- **Cause, as far as the evidence goes:** a shutdown ordering race between ostree-finalize-staged and the ESP automount on `/boot`. Nothing seen in these runs orders the two (`ostree-finalize-staged-hold.service`, "Hold /boot Open", runs in every one, passing and failing, and does not prevent it; the next task must account for it), and when the automount goes first, ostree's remount of `/boot` fails with EINVAL. Five runs show the correlation; no run has tested a fix. The N150 installs with the same `bootc install to-disk` layout and the same generator, so a node can drop an update the same way: safely, and logged, but not applied.
- **Next task (not started):** fix the race in the image, for example by ordering ostree-finalize-staged against `boot.automount`, or by keeping the generator off `/boot`, proved by the drill.

## Plan

1. Red: tests for `case1_outcome(status, installed_digest)` ("rolled back", "never applied", or None while waiting), `finalize_error(journal)`, and case 1 through a stand-in VM on both paths. Commit; push; see it fail in CI.
2. Fix: the two readers, and case 1 using them, with a poll interval the stand-in can set to 0. Commit.
3. The gate on the PR; the VM drills; the verifier; this record.

## Evidence log

### Red (`086f96e`, the tests alone)

- On `rikuri-drill`, through `safe-run.sh`: every new test but "a rollback passes as before" errors or fails (`no attribute 'case1_outcome'`, `'finalize_error'`, `'FINALIZE_JOURNAL'`; the old case 1 kept reading bootc's status after the update was gone).
- CI: `Full gate (Ubuntu)` **Fail**, as wanted, [run 43144551290](https://github.com/rikuripi/rikurinode/actions/runs/43144551290) (job 130939192780): `FAILED (failures=1, errors=15)`, all in `Case1Outcome`, `FinalizeError` and `Case1Steps`. "A rollback passes as before" passes on the old code, as it should: that path does not change.

### Fix

- `image/drill/vm_drill.py`: `BROKEN`, `FINALIZE_JOURNAL`, `OSTREE_ERROR`; `case1_outcome()` and `finalize_error()`; `case1_poll` (10 s, as before); case 1 waits for either outcome, and on "never applied" keeps the boot-that-shut-down's journal of finalize and the automount in `02-case1.out`, records case 1 Fail with ostree's error, and returns, so cases 2b, 3, 4 and 5 still run.
- On `rikuri-drill`, through `safe-run.sh`: every `image/tests` test, `Ran 520 tests`, `OK`; the six new ones by name, `OK`.
- No test changed after red.

### The verifier's first pass, at `fc64269`: no Important finding; Not yet proven (the PR's drill was still running)

- It checked `case1_outcome` against every state case 1 passes through, the pass rule (unchanged), the "never applied" path (always a Fail; the later cases start from the state case 2b expects), the regex against the real journal line, the red-then-fix commits, the scope, and the diagnosis table against the five artifacts (it matches). `Full gate (Ubuntu)` Pass on `fc64269`, run 43144786947.
- Hand mutations: 26, 21 caught. The 5 survivors were in what is kept and shown, not in a pass or fail: the regex's `\b`, its `$`, any ostree line rather than `error: …`, `-b 0` for `-b -1`, and `-u boot.automount` dropped.
- **Nits, fixed:**
  1. The survivors. The test now pins `FINALIZE_JOURNAL` and checks case 1 reads it; the fixture has an ostree line that is not an error; `finalize_error` is tested against `rpm-ostree[…]: error:` and a plain ostree line. **Reason for these test changes after red:** they add cases that the first fix already met; none loosens an assertion. On `rikuri-drill`, four of the five former survivors (and the regex with `\b` instead of the lookbehind, and with none) now fail the tests; the fifth, the regex without `$`, is equivalent (`.*` stops at the line's end) and no test can tell it apart.
  2. The new tests sat after `if __name__ == "__main__"`; the block is the file's end again (test layout only).
  3. The regex now excludes `rpm-ostree` and `ostree-…` by a lookbehind, not `\b`.
  4. The diagnosis now names `ostree-finalize-staged-hold.service`.
  5. Case 1's wait says "to roll back or be dropped".
- After the nits, on `rikuri-drill` through `safe-run.sh`: `image/tests`, `OK`.

### CI on `6944e86` (the nits): the race, seen and reported at once

- `Full gate (Ubuntu)`: **Pass**, run 43145532078. The image build and the USB installer drill: **Pass**, run 43145532277.
- The rollback drill, job 130943349431: **Fail**, as this change means it to when the race happens. The race happened on this run, and case 1 said so 38 s after the variants were built (03:11:29 to 03:12:07 UTC), not after 600 s:
  `FAIL case 1, a failing update: never applied: the update was dropped at shutdown, not rolled back; 'never applied' logged: True; ostree-finalize-staged: error: Remounting /boot read-write: Invalid argument`
  Then every other check passed, including cases 2b, 3, 4 and 5, which the old case 1 never let a failing run reach.
- **The live "never applied" path: Pass** (no longer Not yet proven).
- `02-case1.out` (artifact 13912255990) keeps the order in one journal. This is the fifth failing run seen, after the four in the diagnosis table, and the same order again:
  - `175.499 boot.automount: Got automount request for /boot, triggered by 2241 (tokio-rt-worker)`
  - `185.674 Unset automount boot.automount - EFI System Partition Automount.`
  - `185.917 Stopping ostree-finalize-staged.service`
  - `185.960 ostree[2410]: error: Remounting /boot read-write: Invalid argument`
  - The first line is a clue for the next task, not a finding: some Rust (tokio) process touched `/boot` during the update and mounted the EFI partition there. Which one is not known from this evidence.
- So the PR's rollback drill is red for a real fault, which the next task fixes. `image.yml` is not a required check (AGENTS.md, "Verification by maturity"); whether to merge with it red is the owner's decision.

### The verifier's follow-up, at `723eb4c`: PASS

- The five nit fixes hold, and none loosens a test. Running the test file directly gives `Ran 134 tests … OK`.
- Mutations rerun on `rikuri-drill`, with no bytecode reused: 30 mutants, 29 caught. The one survivor is the equivalent `$`.
- The PR's drill (job 130943349431) behaved as specified: a Fail within one boot, with "never applied" and ostree's error, and every later case ran. This record's entry for that run states only what the log and `02-case1.out` show.
- Its two nits were in this record's wording, and are fixed above.

## Close-out

- **Done when:** every item is met.
  - The cause is recorded, with five failing runs.
  - The tests went red first, then green, with a reason recorded for the later test changes.
  - `Full gate (Ubuntu)` passes on `6944e86`.
  - On the PR, case 1 failed within one boot with "never applied" and ostree's error.
  - The verifier passed: the first pass found no Important issue, and the follow-up passed.
- One repair cycle of two was used (the nits), and both review rounds.
- **The rollback drill stays red** on most runs until the race is fixed: about one in three, or every run that hits it. This is the drill reporting a real fault. It is not a required check, so whether to merge with it red is the owner's decision.
- **CI used:** four gate runs and three image workflow runs. The drill on `fc64269` was superseded by the push of the nits.
- **Next (not started):** fix the race in the image, with the drill as the proof.

### Merged

- PR #87's commits, at head `a2613c7`, were merged on 2026-11-12 with PR #88, as `544f1bf`. The race this record diagnosed is fixed there: the EFI partition's automount is masked, and case 1 passed in 3 drill runs of 3 (`docs/build-records/2026-11-11-boot-automount-mask.md`).
