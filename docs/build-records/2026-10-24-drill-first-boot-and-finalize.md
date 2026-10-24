# Build Record — The drill asserts the containers range at the first boot; run 2's finalize failure investigated

| | |
|---|---|
| **Date** | 2026-10-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/drill-first-boot-subid`, from `main` at `452e6c6`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | fix (the CI drill, a control) and an investigation |

## Task Contract

1. **Outcome:** the drill fails if a fresh install does not get the containers range at its first boot, and the owner knows whether the finalize failure of drill run 2 (40057729110) can come back on a node, or was a drill artefact.
2. **Scope:** two items left by `docs/build-records/2026-10-23-containers-subid.md` (its follow-up pass, nits 1 and 2). (a) `image/drill/vm_drill.py`: right after the first boot, read the two files and that boot's journal of `rikuri-containers-subid`, and require the range once in each and "added" for both; at the end, require the files unchanged since then (what `subid_after_reboots` claims); tests in `image/tests/test_vm_drill.py`. (b) An investigation in `rikuri-drill`: does a `podman run --userns=auto` of an image just before `bootc switch --transport containers-storage` to an image built on it make the update fail to finalize? Risk tier: **high-risk** (the drill is a control). **Not included:** any change to `image/rootfs` or the checker; a fix for (b) beyond the drill (if (b) shows a node-side problem, it goes to the owner as its own task).
3. **Done when:**
   - (a) the new drill helpers' tests committed failing first, then pass; the CI drill on the pull request passes all checks, with the first-boot one stating "added" in boot 1;
   - (b) a stated answer in this record, from runs in `rikuri-drill` with the evidence kept: reproduced (how often, and with which ostree error), or not reproduced in N tries with and N without the `--userns=auto` run; no claim beyond what the runs show;
   - `Full gate (Ubuntu)` passes; one `verifier` pass has no Important finding.
4. **Authority:** the owner's "Yes, let's follow-up" (2026-10-24), to "make the drill assert first-boot state directly, and find run 2's finalize failure from the post-mortem it now keeps"; edit the files in Scope; use `rikuri-drill` as before (host key pinned to the fingerprint the owner saw); push this branch; open the pull request; no merge. CI drill development runs: at most 2. Independent check required.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 3 hours.

## 0b. Spec

- [x] **What run 2 shows** (`99-post-mortem.out` of 40057729110, against run 3's artifact): at case 1's shutdown, greenboot's trigger reported "'bootc status --booted --json' exited with non-zero status" and "No staged deployment found"; `ostree-finalize-staged.service` exited 1. In run 3 (pass), the same shutdown has "Setting rollback trigger" and neither error. So in run 2 bootc itself could not read its state at that shutdown; ostree's message is not in the artifact.
- [x] **Hypothesis to test in (b):** a `--userns=auto` run of the OS image (which can add ID-mapped layers to containers-storage) shortly before `bootc switch --transport containers-storage` leaves a staged deployment that bootc and ostree cannot read or finalize.
- [x] **Design of (a):** the reads are harmless at the first boot (only the container run was moved after the cases); `subid_unchanged(first, now)` compares the files' text.

## Evidence log

### (b) Run 2's finalize failure: not reproduced

- **Setup.** `rikuri-drill` (aarch64, Parallels), booted on `localhost/rikuri-os:subid2` and its successors. Each try: build an image on the booted one (a `LABEL` only, `--pull=never --network=none`); for "with", first `podman run --rm --userns=auto --network=none --read-only <booted image> /usr/bin/true`, as the drill did in run 2; `bootc switch --transport containers-storage` to the new image; reboot; read the previous boot's journal of `ostree-finalize-staged.service` and `greenboot-set-rollback-trigger.service`. Scripts: `ft_stage.sh` and `ft_report.sh`, quoted in the evidence's command lines below.
- **First attempt invalid** (`00-finalize-tries-script-bug.out`): the try number and mode were expanded to empty when the script was written (an unquoted heredoc), so no try ran the `--userns=auto` container and only the first staged anything. Kept as evidence of the mistake, not counted.
- **Result** (`01-finalize-tries.out`): **6 of 6 finalized**, 3 with the `--userns=auto` run (tries 1, 3, 5) and 3 without (2, 4, 6). Each shows "Finished writing deployment", `Deactivated successfully`, greenboot's "Setting rollback trigger" for the staged digest, and the new image booted. The two `error: mm_reap: child terminated by signal 15` lines come from `sshd-session`, killed by the reboot, not from ostree.
- **Run 2's artifact again** (`99-post-mortem.out` of 40057729110): at case 1's shutdown, `bootc status --booted --json` failed inside greenboot's trigger, greenboot then found no staged deployment, and finalize's stop exited 1. ostree's own message is not in it: the post-mortem kept that unit's journal only from #34's repair on. The node then booted the installed image, so the update was not applied and nothing broke; case 2b drills exactly that outcome every run.
- **Answer.** The hypothesis (a `--userns=auto` run before `bootc switch` breaks finalize) is **not supported**: 0 of 3 tries with it failed, as 0 of 3 without. The cause of run 2's failure is **not known**. Limits: 3 + 3 tries; aarch64 in Parallels, not the x86_64 KVM runner; a `LABEL`-only image, not the drill's `broken` variant. Since #34 the drill keeps `ostree-finalize-staged`'s journal in its post-mortem, so a recurrence will name the error. Not proven: that it cannot recur.

### (a) The first-boot check

- **Red** (`02-red-tests.out`, commit `91fc6e1`): `ContainersRangeFirstBoot`, 4 tests, 9 errors, all `AttributeError` for `subid_added` and `subid_unchanged`; nothing else failed. Run in `rikuri-drill` with `python3 -m unittest discover -s image/tests` (`safe-run.sh` refuses on macOS, as in the earlier records; the CI gate runs them through it).
- **Fix** (commit `9f333e8`): `subid_added(journal)` needs "<file>: added <range>" ending a line for both files (the folder-sync warning does not count); `subid_unchanged(first, now)` needs both files' text as at the first boot, with the range once. `first_boot` calls the new `subid_first_boot`, which keeps `01a-subid-first-boot.out` and checks "the containers range at the first boot" (in `expected`); "after reboots" compares against that read. The module docstring now lists the containers-range checks (#34 had left them out).
- **Green** (`03-green-tests.out`): 153 tests, OK.
- **Mutants** (each applied, checked to differ, then reverted): drop the line-end anchor; `any` for `all` in `subid_added`; drop `now == first`; drop the range-once condition. Each turned the suite red (1, 5, 1, 1 failures).
