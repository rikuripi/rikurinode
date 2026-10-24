# Build Record — ADR 0006 clarified: four failed boots, and what rollback depends on; #29 closed out

| | |
|---|---|
| **Date** | 2026-10-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `docs/close-out-29-adr-0006`, from `main` at `a3babce`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `a68e620` (the clarification and #29's close-outs); this close-out |
| **Status** | COMPLETE but for the merge: pull request #31 |
| **Change type** | ops (documentation only) |

## Task Contract

1. **Outcome:** ADR 0006 states what was observed about its rollback (four failed boots, not three) and what the rollback depends on, so the builder of release sets finds it in the decision itself; the two tasks merged in #29 are closed out.
2. **Scope:** `docs/adr/0006-release-sets-bound-to-the-image.md` (a dated "Clarification" section and its Status line; the text above it unchanged); the Status and close-out lines of `docs/build-records/2026-10-22-ci-vm-drill.md` and `docs/build-records/2026-10-22-greenboot-218.md`, including the owner's answers of 2026-10-22. Risk tier: routine (documentation; no decision changed). **Not included:** making the drill a required check (the owner's later choice, and a repository setting); any code.
3. **Done when:** the clarification says nothing the evidence does not; the ADR's decision text is unchanged; link and citation checks, `git diff --check` and `repo_hygiene.py` pass; CI's full gate passes on the pull request.
4. **Authority:** the owner's "4. Add dated clarification to ADR 0006. We'll probably use the information when our build gets there." and "1. Merge #29 2. Keep it" (2026-10-22); commit, push and open the pull request; no merge. No independent check (documentation only, routine).
5. **Limits:** one task; two repair cycles; two review rounds.

## Evidence log

- **The clarification:** `docs/adr/0006-release-sets-bound-to-the-image.md` gains the section "Clarification (2026-10-22): how many failed boots, and what the rollback depends on" and a Status line that says it was clarified, not changed. Against `main`, the only line removed is the old Status line (`git diff origin/main...HEAD`); the decision text is unchanged. The ADR's links: the one added is external (bootc's logically bound images page); the cited records exist.
- **Its claims, against the evidence:** four failed boots, from `2026-10-21-greenboot-drill-parallels.md` (Conclusion) and the CI drill's case 1 (`2026-10-22-ci-vm-drill.md`); "about a minute in the VMs tried; not yet measured on the N150 or the Pi"; #218 and #219 fixed in the image (`2026-10-22-greenboot-218.md`, `2026-10-22-d22-unapplied-update.md`) and held by the CI drill, which ran green on `main` after #29's merge (run 39734507606).
- **#29's close-outs:** the Status and close-out lines of `2026-10-22-ci-vm-drill.md` and `2026-10-22-greenboot-218.md`, with the owner's answers of 2026-10-22 ("1. Merge #29 2. Keep it"; the drill becoming a required check is the owner's later choice, with a review set for 2026-11-16).
- **Checks:** `git diff --check` and `repo_hygiene.py` pass. On pull request #31: the first `Full gate (Ubuntu)` run (40042158214) **failed** on RUSTSEC-2026-0385 and -0386, unrelated to this change and fixed by #33 (`docs/build-records/2026-10-23-rustsec-2026-0385-0386.md`); the gate re-runs on this close-out, with `main` (and #33) merged into the branch.
