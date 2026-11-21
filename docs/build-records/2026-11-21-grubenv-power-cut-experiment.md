# Build Record — experiment: does GRUB read a grubenv write a power cut caught? (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-21 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `experiment/grubenv-power-cut`, from `main` at `b458c8a`, draft PR #153 marked do-not-merge, closed unmerged; this record from `docs/grubenv-power-cut-experiment`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | on #153: `3aac068` (contract), `e9d3da8` (experiment), `bdb19cd` (repair 1); this record |
| **Status** | DONE |
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

### Run 1, the experiment's first commit: Fail before any trial (an experiment bug)

- The image workflow, [run 44932985081](https://github.com/rikuripi/rikurinode/actions/runs/44932985081): the first boot passed; then `grub2-editenv: error: cannot open '/boot/grub2/grubenv': Read-only file system`. The experiment wrote grubenv directly, but /boot is mounted read-only.
- `Full gate (Ubuntu)`, [run 44932985087](https://github.com/rikuripi/rikurinode/actions/runs/44932985087): failed as expected on this branch: `test_vm_drill.BootCauseCase1.test_main_reads_the_record_right_after_its_step` (`ValueError: substring not found`), because `main` runs the experiment in place of the cases.

### Repair 1 (the second and last run)

- Every grubenv write in the experiment now runs as the node's `edit_grubenv` runs it: `mount -o remount,rw /boot`, the write, then `mount -o remount,bind,ro /boot`.
- **Why this matters for the question:** a bind remount read-only flags only this mount. ext4 itself stays writable and keeps its journal, so the node's own writes leave the same window. A plain `remount,ro` would flush the journal.
- Each trial also keeps /boot's mount line before the write. The fsfreeze fallback (`remount,ro`) leaves /boot read-only, as the node does.

### Run 2, `bdb19cd`: the 14 trials ran

- The image workflow, [run 44944602844](https://github.com/rikuripi/rikurinode/actions/runs/44944602844): the drill job failed by design (its cases did not run); the build and the USB install passed. `Full gate (Ubuntu)`, [run 44944602726](https://github.com/rikuripi/rikurinode/actions/runs/44944602726): failed as in run 1, on this branch's `main`.
- Evidence: the run's `drill-evidence` artifact (`exp-01.out` … `exp-14.out`, `exp-trials.json`, `serial-1.log` … `serial-15.log`), downloaded with the owner's yes, read as data, then deleted.

| Trials | Gap after the write | Flushed after | `boot_counter` Linux read | What GRUB read |
|---|---|---|---|---|
| 01, 02 | 1 s | no | 3, 3 | the old grubenv |
| 03, 04 | 3 s | no | 3, 3 | the old grubenv |
| 05, 06 | 5 s | no | 3, 3 | the old grubenv |
| 07, 08 | 10 s | no | 3, 3 | the old grubenv |
| 09, 10 | 20 s | no | 3, 3 | the old grubenv |
| 11, 12 | 30 s | no | 3, 3 | the old grubenv |
| 13, 14 | 1 s | `fsfreeze` | 2, 2 | the write |

- **In every trial:**
  - the baseline flush was `fsfreeze`;
  - the write moved grubenv to a new block (`filefrag`: for example 4784218 → 4784231 in trial 1);
  - /boot was `/dev/vda3[/boot] ext4 ro,relatime`: **a bind mount of a folder on the root filesystem, not a partition of its own**;
  - the boot after the cut logged `systemd-fsck[…]: root: recovering journal` (serial-2 … serial-15; not serial-1, the first boot). The replay is e2fsck's, in user space before the kernel mounts the root, which is why the kernel logged no recovery line.

## Result

- **Pass (the hypothesis holds, observed):** after a `grub2-editenv` write, a power cut up to at least 30 s later makes GRUB read grubenv as it was before the write, while Linux, after e2fsck replays the root's journal, reads the new one. 12 of 12 trials.
- **The window is at least 30 s; its end is Not yet proven.** It is not ext4's 5 s commit: the write was committed to the journal and still not at its home block at 30 s. Case 1b's give-back (run 44921422972) was read correctly by GRUB, so in that run something wrote it home, or the cut came later; not proven which.
- **Pass (the mitigation, observed):** `fsfreeze -f /boot; fsfreeze -u /boot` right after the write, then a cut at 1 s: GRUB read the write, 2 of 2.
- **What it means for D22's rule (read, not run):**
  - the arm: unaffected; a clean shutdown follows it;
  - the give-back, at boot: a power cut within the window makes GRUB count from the value before the give-back, so the update has one boot fewer than the rule intends (it can roll back a boot early);
  - greenboot's own writes at boot have the same window.
- **Derived from the evidence and GRUB's source, not proven; for the owner:** when GRUB counts after such a cut, `save_env` writes in place to the blocks it found, which are the file's old block. ext4 freed that block when the file moved, and it may already hold another file's data once the freeing transaction is committed. GRUB would then overwrite 1 KiB of that file. /boot is on the root filesystem, which holds `/var`, where the node's data will live.

## Outcome

- **Mitigation: keep**, as its own fix task: flush the root's journal after each grubenv write of the node's (and, if it can be reached, greenboot's), with a drill case made from this experiment as its red test.
- **The experiment: drop** (it is the red test's design, not code to keep). Draft PR #153 closed unmerged and its branch deleted; its commits stay reachable from the closed PR on GitHub.
