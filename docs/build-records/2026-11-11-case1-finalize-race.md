# Build Record — Case 1's timeout: an update dropped at shutdown, diagnosed

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/case1-finalize-evidence`, from `main` at `65c8e99`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
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
- **Cause, as far as the evidence goes:** a shutdown ordering race between ostree-finalize-staged and the ESP automount on `/boot`. Nothing orders the two, and when the automount goes first, ostree's remount of `/boot` fails with EINVAL. Five runs show the correlation; no run has tested a fix. The N150 installs with the same `bootc install to-disk` layout and the same generator, so a node can drop an update the same way: safely, and logged, but not applied.
- **Next task (not started):** fix the race in the image, for example by ordering ostree-finalize-staged against `boot.automount`, or by keeping the generator off `/boot`, proved by the drill.

## Plan

1. Red: tests for `case1_outcome(status, installed_digest)` ("rolled back", "never applied", or None while waiting), `finalize_error(journal)`, and case 1 through a stand-in VM on both paths. Commit; push; see it fail in CI.
2. Fix: the two readers, and case 1 using them, with a poll interval the stand-in can set to 0. Commit.
3. The gate on the PR; the VM drills; the verifier; this record.

## Evidence log
