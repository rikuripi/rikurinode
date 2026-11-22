# Build Record — experiment: which flush makes GRUB read greenboot's write, and does GRUB save boot_success at every boot? (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-21 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `experiment/grubenv-flush-methods`, from `main` at `5ef53bb`, a draft PR marked do-not-merge, closed unmerged; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | on the draft PR (#156): `47301f5` (contract), `9e1d8a5` (experiment), `55d2409` (repair 1); this record's result on `stage1/grubenv-flush` |
| **Status** | DONE |
| **Change type** | experiment (no production change) |

## Intent: the owner's words

- Asked how to tell the two causes of case 3b's failure apart, before a repair (`docs/build-records/2026-11-21-grubenv-flush.md`, [run 44950453875](https://github.com/rikuripi/rikurinode/actions/runs/44950453875)): **"One more experiment"**.

## The questions

1. **Does GRUB save `boot_success=0` at a boot with no `boot_counter`?** Case 3b's probe assumes it does. If it doesn't, the probe reads greenboot's 1 whatever the flush does.
2. **Which flush makes GRUB read a write a power cut 3 s later caught:** none, ext4's checkpoint call (`EXT4_IOC_CHECKPOINT`), `syncfs` (`sync -f`), or `fsfreeze`?

## Design

- **The experiment** is an `experiment` method in `image/drill/vm_drill.py`, run by `main` after the first boot in place of the cases, as in the first experiment (`docs/build-records/2026-11-21-grubenv-power-cut-experiment.md`).
- **Each trial:**
  - the node's installed image, its health check done;
  - greenboot's check held at the next boot (`hold_first`), then `sync`;
  - a baseline written as the node writes (`remount,rw`, the write, `remount,bind,ro`): `boot_counter` and `boot_success` unset;
  - the baseline flushed with `fsfreeze`;
  - the trial's write, as the node writes;
  - the trial's flush;
  - then either a power cut 3 s after the write, or a clean reboot;
  - at the held boot, read `boot_success` and `boot_counter`, and keep `filefrag` before and after the write.
- **Trials (10):**

| Trials | Write | Flush | End | What it answers |
|---|---|---|---|---|
| 01, 02 | `boot_success=1` | `fsfreeze` | clean reboot | Q1: `boot_success` 0 means GRUB saved it |
| 03, 04 | `boot_success=1` | none | cut at 3 s | Q2: the baseline without a flush |
| 05, 06 | `boot_success=1` | the checkpoint call | cut at 3 s | Q2 |
| 07, 08 | `boot_success=1` | `sync -f /boot/grub2` | cut at 3 s | Q2 |
| 09, 10 | `boot_success=1` | `fsfreeze` | cut at 3 s | Q2 |

- The checkpoint call runs as the fix's program makes it: `python3 -I`, `/boot/grub2` opened read-only as a directory, `0x4004662b` with 4 zero bytes.
- **Reading the result:**
  - If 01 and 02 read 1, GRUB does not save `boot_success` on such a boot. Then Q2 can't be read from `boot_success`, and case 3b's probe must change.
  - If they read 0, Q2 is read directly: 0 means GRUB's write reached the file.
- **The result:** the artifact `drill-evidence` (`exp-trials.json`, `exp-*.out`, the serial logs) and a summary table. The drill's own checks don't run, so the job's verdict is not the result.

## Task Contract

1. **Outcome:** the owner knows whether case 3b's probe is sound and which flush makes GRUB read greenboot's write, so #155's repair is chosen on evidence.
2. **Scope:** experiment (a disposable experiment; nothing reaches `main` but this record).
   - On the experiment branch only: `image/drill/vm_drill.py` (the `experiment` method; `main` runs it in place of the cases) and this record.
   - **Not included:** any change to #155 (its repair is decided after this), the image, greenboot, or the drill on `main`.
3. **Done when:**
   - one CI run of the image workflow on the draft PR completes the 10 trials, with the evidence downloaded (with the owner's yes) and read;
   - the result is recorded with its run, and ends in a recommendation for #155's repair;
   - the draft PR closed unmerged and its branch deleted (both made by this task);
   - this record lands on `main` with #155 (added to its branch), so no separate docs PR is needed.
4. **Authority:** the files above. Commit and push this branch; a draft PR titled do-not-merge; close it and delete its branch; add this record to `stage1/grubenv-flush`. Download the run's `drill-evidence` artifact once the owner says yes. On the Mac: `ast` parse checks and `git diff --check`. CI runs the VM; nothing runs against the live node. No verifier pass: no code reaches `main`.
5. **Limits:** one task; at most two CI runs (one repair); two review rounds. Budget: about 25 minutes of VM time per run.

## Evidence log

### Run 1: question 1 answered; question 2 not readable

- The image workflow, [run 44957539989](https://github.com/rikuripi/rikurinode/actions/runs/44957539989), from the job's log; the artifact was not downloaded:

| Trials | Flush | End | `boot_success` at the held boot |
|---|---|---|---|
| 01, 02 | `fsfreeze` | clean reboot | 1, 1 |
| 03, 04 | none | cut at 3 s | 1, 1 |
| 05, 06 | the checkpoint call | cut at 3 s | 1, 1 |
| 07, 08 | `sync -f` | cut at 3 s | 1, 1 |
| 09, 10 | `fsfreeze` | cut at 3 s | 1, 1 |

- Every flush ran (it said its name), and every write moved grubenv to a new block.
- **Question 1, observed:** GRUB does not save `boot_success=0` at a boot with no `boot_counter`. Even after a clean reboot, which writes everything home, the file kept the 1.
- **So:**
  - question 2 cannot be read from `boot_success`;
  - case 3b's probe in #155 cannot see GRUB's write, and its red run's Fail was not evidence of the defect.

### Repair 1 (the second and last run)

- The trials read GRUB's countdown, which the first experiment showed GRUB saves:
  - write `boot_counter=3 boot_success=0`;
  - 2 at the held boot means GRUB read the write, 3 that it read the old grubenv.
- **Trials (9):**
  - 01: no flush, clean reboot (the probe's control: must read 2);
  - 02, 03: no flush, cut at 3 s;
  - 04, 05: the checkpoint call, cut at 3 s;
  - 06, 07: `sync -f`, cut at 3 s;
  - 08, 09: `fsfreeze`, cut at 3 s.

### Run 2, `55d2409`: the 9 trials ran

- The image workflow, [run 44958580763](https://github.com/rikuripi/rikurinode/actions/runs/44958580763), from the job's log; the artifact was not downloaded. The drill job failed by design (its cases did not run); the build and the USB install passed.
- `CI`, [run 44958580808](https://github.com/rikuripi/rikurinode/actions/runs/44958580808): `Full gate (Ubuntu)` failed as on the first experiment's branch, in `test_vm_drill` (`ValueError: substring not found`), because `main` runs the experiment in place of the cases.

| Trial | Flush | End | `boot_counter` at the held boot | What GRUB read |
|---|---|---|---|---|
| 01 | none | clean reboot | 2 | the write (the control) |
| 02, 03 | none | cut at 3 s | 3, 3 | the old grubenv |
| 04, 05 | the checkpoint call | cut at 3 s | 2, 2 | the write |
| 06, 07 | `sync -f /boot/grub2` | cut at 3 s | 2, 2 | the write |
| 08, 09 | `fsfreeze` | cut at 3 s | 2, 2 | the write |

- In every trial the flush said its name, and the write moved grubenv to a new block.

## Result

- **Question 1, Pass (observed, run 1):** GRUB does not save `boot_success` at a boot with no `boot_counter`. Case 3b's probe in #155 cannot see GRUB's write; its red run's Fail and its Fail with the fix (run 44950453875) are not evidence either way.
- **The countdown probe, Pass (observed, run 2):** the control read 2 and the unflushed cuts read 3, 2 of 2, so the probe tells the two outcomes apart.
- **Question 2, Pass (observed, run 2):** each of ext4's checkpoint call, `syncfs` and `fsfreeze`, run after the write, made GRUB read it after a cut 3 s later, 2 of 2 each. No flush: GRUB read the old grubenv, 2 of 2, as in the first experiment.
- **Not proven:** two trials per method; the cut at 3 s only; the VM's virtio disk, not the N150's or the Pi's.

## Outcome

- **The checkpoint call: keep.** #155's choice stands; no change of method.
- **For #155's repair:** case 3b reads GRUB's countdown, not `boot_success`: a write that sets `boot_counter`, a cut a few seconds later, and 2 read at the held boot. Its red evidence is re-run with the flush removed, and the record's red claim is corrected.
- **The experiment: drop.** The draft PR closed unmerged and its branch deleted; its commits stay reachable from the closed PR on GitHub.
