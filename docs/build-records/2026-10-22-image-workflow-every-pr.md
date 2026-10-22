# Build Record — The OS image workflow starts on every pull request and skips quickly when the image is untouched

| | |
|---|---|
| **Date** | 2026-10-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `ci/image-workflow-every-pr`, from `main` at `a3babce`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | ops (CI; a control change, authorized as its own task) |

## Task Contract

1. **Outcome:** the image workflow's jobs can later be made required checks without blocking pull requests that do not touch the image: every pull request starts the workflow, and the build and the drill run only when `image/` or the workflow changed, otherwise they are skipped within a minute (a skipped job counts as passed for a required check).
2. **Scope:** `.github/workflows/image.yml` (the `pull_request` trigger loses its path filter; a `changes` job; `build` and `drill` gated on it); `scripts/quality/tests/test_workflows.py` (tests that hold this); this record. Risk tier: **routine** (CI plumbing; the drill itself unchanged), with the gate's tests. **Not included:** making any check required (a repository setting, the owner's, after the review set for 2026-11-16); the push, schedule and dispatch triggers (unchanged: they always run everything).
3. **Done when:** the new tests fail before the change and pass after; on this task's pull request, which touches the workflow, `changes` says yes and the build and the drill run and pass; on the next pull request that touches neither (the ADR 0006 docs pull request, branch `docs/close-out-29-adr-0006`, after this merges), `changes` says no and the build and the drill are reported skipped; `Full gate (Ubuntu)` passes.
4. **Authority:** the owner's "Ok make the small fix and remind me for 16 Nov." (2026-10-22); edit the files in Scope; commit, push, open the pull request; no merge. No independent check (routine), unless a finding needs one.
5. **Limits:** one task; two repair cycles; two review rounds.

## Spec

- **Fail-safe direction:** anything but a pull request (push to `main`, schedule, dispatch), or a diff that cannot be computed, runs everything. Only a pull request whose files are all outside `image/` and the workflow skips.
- **The decision:** `git diff --name-only <base sha> HEAD` on the pull request's merge commit, matched against `^image/` and `^\.github/workflows/image\.yml$`. No third-party action.
- **Rejected:** a third-party path-filter action (adoption inspection, another pinned dependency); keeping the path filter and adding a stub workflow of the same job names (two workflows to keep in step).

## Evidence log
