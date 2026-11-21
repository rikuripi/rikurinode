# Build Record — experiment: does GRUB read a grubenv write a power cut caught? (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-21 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `experiment/grubenv-power-cut`, from `main` at `b458c8a`, a draft PR marked do-not-merge, closed unmerged; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at the end) |
| **Status** | IN PROGRESS |
| **Change type** | experiment (no production change) |

## Intent: the owner's words

- "Next" (2026-11-21), after the investigation of case 3's counter of 3, whose Next was this experiment.
- Where it runs: **"Throwaway draft PR"**. The budget: **"N = 1, 3, 5, 10, 20, 30 s, twice each"**.

## The question

After `grub2-editenv` writes `/boot/grub2/grubenv`, does a power cut N seconds later make GRUB read the grubenv as it was before the write, while Linux, which replays ext4's journal, reads the new one? If so, for how long after the write?

- **Why it matters:** the give-back (D22) writes grubenv at boot. A power cut inside such a window would let GRUB count from a stale value, at most one boot either way. The arm is unaffected: a clean shutdown follows it.
- **The hypothesis, read in source, not proven:**
  - `grub2-editenv` rewrites the file (`fopen "wb"`, then fsync), which can move it to new blocks with the change held in the journal;
  - GRUB's ext2 driver ignores the journal;
  - case 3 in #142's red run (run 44819244785) read 3 after a cut about 3 s after the old arm's write;
  - case 1b today (run 44921422972) read a give-back correctly after a cut some 10–15 s later.

## Design

- **The experiment** is an `experiment` method in `image/drill/vm_drill.py`, run by `main` after the first boot in place of the cases.
- **Each trial:**
  - the node's installed image, its health check done;
  - greenboot's check held at the next boot (the drill's `hold_first`), then `sync`;
  - grubenv's baseline flushed to its home blocks (`fsfreeze -f /boot; fsfreeze -u /boot`), with no `boot_counter`;
  - `filefrag -v` of grubenv;
  - `grub2-editenv … set boot_counter=3 boot_success=0`;
  - `filefrag -v` again (did the file move?);
  - wait N s, kill QEMU, start it;
  - at the held boot, read `boot_counter`: **2** means GRUB read the write and counted, **3** means GRUB read the old grubenv, anything else is recorded as is;
  - keep the boot's kernel lines for /boot (`EXT4-fs` recovery) and its mount options;
  - release the hold, wait for the check, unset `boot_counter` and `boot_success`.
- **Gaps:** N = 1, 3, 5, 10, 20, 30 s, twice each (12 trials).
- **One more arm:** the candidate mitigation, a `fsfreeze` of /boot right after the write, at N = 1 s twice (2 trials), so that its effect is seen in the same run.
- **Safety in the VM:** GRUB counts down from 3 or not at all, so no trial reaches a fallback.
- **The result** is the artifact `drill-evidence` (`exp-trials.json`, `exp-*.out`, the serial logs) and a summary table. The drill's own checks don't run; the job's verdict is not the result.

## Task Contract

1. **Outcome:** the owner knows whether a power cut shortly after a grubenv write makes GRUB read stale data, for how long, and whether flushing /boot's journal closes it, so a fix is decided on evidence.
2. **Scope:** experiment (the tier of a disposable experiment; nothing reaches `main` but this record).
   - On the experiment branch only: `image/drill/vm_drill.py` (the `experiment` method; `main` runs it in place of the cases) and this record.
   - **Not included:** any change to the image, greenboot's rule, the give-back or the drill on `main`; any mitigation; the backlog items (N2 and the others).
3. **Done when:**
   - one CI run of the image workflow on the draft PR completes the 14 trials, with the evidence downloaded and read;
   - the result is recorded below with its run, Pass / Fail / Not yet proven per trial, and ends in keep, simplify or drop for the mitigation;
   - the draft PR closed unmerged and its branch deleted (both made by this task); this record lands on `main` in a docs-only PR.
4. **Authority:** the files above. Commit and push this branch; a draft PR titled do-not-merge; close it and delete its branch. Download the run's `drill-evidence` artifact (asked for by name when the run is done). On the Mac: `ast` parse checks and `git diff --check`. CI runs the VM; nothing runs against the live node. No verifier pass: no code reaches `main`.
5. **Limits:** one task; at most two CI runs of the experiment (one repair); two review rounds. Budget: about 25 minutes of VM time per run.

## Evidence log

(to come)
