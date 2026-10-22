# Build Record — ADR 0006 clarified: four failed boots, and what rollback depends on; #29 closed out

| | |
|---|---|
| **Date** | 2026-10-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `docs/close-out-29-adr-0006`, from `main` at `a3babce`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | ops (documentation only) |

## Task Contract

1. **Outcome:** ADR 0006 states what was observed about its rollback (four failed boots, not three) and what the rollback depends on, so the builder of release sets finds it in the decision itself; the two tasks merged in #29 are closed out.
2. **Scope:** `docs/adr/0006-release-sets-bound-to-the-image.md` (a dated "Clarification" section and its Status line; the text above it unchanged); the Status and close-out lines of `docs/build-records/2026-10-22-ci-vm-drill.md` and `docs/build-records/2026-10-22-greenboot-218.md`, including the owner's answers of 2026-10-22. Risk tier: routine (documentation; no decision changed). **Not included:** making the drill a required check (the owner's later choice, and a repository setting); any code.
3. **Done when:** the clarification says nothing the evidence does not; the ADR's decision text is unchanged; link and citation checks, `git diff --check` and `repo_hygiene.py` pass; CI's full gate passes on the pull request.
4. **Authority:** the owner's "4. Add dated clarification to ADR 0006. We'll probably use the information when our build gets there." and "1. Merge #29 2. Keep it" (2026-10-22); commit, push and open the pull request; no merge. No independent check (documentation only, routine).
5. **Limits:** one task; two repair cycles; two review rounds.

## Evidence log
