# Build Record — ADR 0007 clarified: rootless versus rootful for this node, and pods

| | |
|---|---|
| **Date** | 2026-10-21 |
| **Author / session** | Claude (Fable 5.1, desktop app session on the Ryzen) for Henry Chen |
| **Branch** | `docs/adr-0007-clarification` (renamed on the owner's word from the app's `worktree-docs+adr-0007-clarification`), from `main` at `c070a98`, in the worktree the app made at `/home/junc/rikuripi/rikurinode/.claude/worktrees/docs+adr-0007-clarification` (isolation: the main checkout holds another session's branch, `ci/weekly-advisory-audit`). Pushed and handed to the owner as a compare link on the owner's word ("Yes, on branch docs/adr-0007-clarification", 2026-10-21) |
| **Commits** | (fill at close-out) |
| **Status** | DONE locally: the §5 checks pass (Evidence log). Commit, push and CI's `Full gate (Ubuntu)` on the pull request Not yet proven, pending the owner's word |
| **Change type** | ops (documentation only: a dated clarification of an accepted decision) |

## Task Contract

1. **Outcome:** the owner's question of 2026-10-21 on rootless versus rootful Podman and on pods, and its answer, are kept with the decision they support: a dated clarification under ADR 0007 that D13 and D14 point to, so the reasoning is not lost in a chat.
2. **Scope:** `docs/adr/0007-rootful-range-per-container.md` (the status row; one new section, "Clarification (2026-10-21)"; a source read today); `docs/architecture/platform-plan.md` (one clause in the status paragraph; the Decided cells of D13 and D14); this record. Tier: **routine** (a decision already taken is explained; no rule, control or behaviour changes; BUILD-PROCEDURE.md, "Risk tiers"). **Not included:** any change to what D13 or D14 decide; ADR 0003's text (history, kept as written); the threat model (its §3 already cites ADR 0007 for isolation; no row changes); the lessons register (EXEC-08 was answered by ADR 0007); code.
3. **Done when:** ADR 0007 carries the clarification with the owner's words, and every Podman fact in it carries a source read on 2026-10-21 or points to ADR 0007's and ADR 0003's sources; D13 and D14 point to it; the plan's status paragraph names it; `git diff --check` is clean; `repo_hygiene.py` exits 0 on the staged files; the D13 and D14 rows keep four cells; relative links in added lines resolve; CI's `Full gate (Ubuntu)` is green on the pull request (Not yet proven until the owner opens it).
4. **Authority:** the owner, 2026-10-21: "Yes, please record.", answering "If you want this question and answer recorded as a dated clarification under ADR 0007 and D14, that is a small documentation task." Edit the files in Scope in the worktree; stage them for the hygiene check. Commit, push and the pull request wait for the owner's word (the owner's standing rule: commit and push only when asked). Routine documentation: the AGENTS.md §5 checks and the owner's review, no verifier. Network: GitHub's raw-content host, for Podman's own documentation. No merge.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured; usage reported at close-out.

## 0. Intent

- [x] **Problem, in the owner's words** (2026-10-21): "Regarding Podman. I guess it runs without daemon and can run rootless for security. Our plan call for running containers rootful. I need to know the difference and whether it's safer to run rootless given the nature of bitcoin node and its disparate services. And what is Podman Pod, does it have any relevance on the node?" Then, to the offer of recording the answer: "Yes, please record."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** the decision records; nothing running.
- [x] **Open questions:** none.
- [x] **Owner approved the intent:** the message above.

## 0b. Spec

- [x] **Requirements:** the clarification changes no decision; it answers the three parts of the question (the difference, whether rootless is safer for this node, what a pod is and whether it matters here); it is honest in both directions, naming rootful's own residual cost as ADR 0007 already does; every Podman fact is sourced.
- [x] **Design:** one dated section inside ADR 0007, plus a one-line pointer in each of the plan's D13 and D14 rows and a clause in the plan's status paragraph. Rejected: a new ADR (ADR 0012 was one because it amended a decision; this amends nothing); editing ADR 0003 (superseded, kept as written); a note in the lessons register (EXEC-08 is already answered there by ADR 0007).
- [x] **Policy applied:** ADR history kept by dated clarification (AGENTS.md §8, "Conflicts"); runtime truth over declared truth, applied to documents: the pod facts re-read from Podman's own documentation today, not from memory.
- [x] **Flagged concerns:** none routed. The one place rootful is worse, a bug in Podman's own setup path reaching the host as root, is stated plainly, as ADR 0007's Consequences already do.

## 1. Plan

- [x] **One sentence:** add the clarification section to ADR 0007 with its sources, point D13 and D14 at it, and name it in the plan's status line.
- [x] **Blast radius:** documentation only.
- [x] **Current behaviour characterized:** ADR 0007 at `c070a98` has Context, Decision, Consequences, Rejected and Sources, and no clarification; the plan's D13 and D14 Decided cells end with the 2026-10-17 decision and ADR 0007; the status paragraph's last dated item is 2026-10-20.
- [x] **Files and order:** this record, the ADR, the plan, the checks.
- [x] **Risks:** a pod fact stated from memory and wrong (held by the source read today); a table row broken by the edit (held by the cell-count check); a link that does not resolve (held by the link check).
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] Wording only; no code.
- [x] Clean as you go: nothing replaced.
- [x] **Security question answered:** records reasoning about the container boundary; no protection changes and none is claimed proven.

## 3. Debug

- N/A

## 4. Verify

- [x] Checks: see the Evidence log. Diff matches the §1 plan: the three files in Scope, nothing else.

## 5. Close Out

- [ ] Full gate: CI's `Full gate (Ubuntu)` on the pull request.
- [x] Scrap Sweep: Podman's documentation was read from the fetch's output, never written to disk; nothing to remove.
- [ ] Reviewed per `REVIEW.md`: the owner's review on the pull request.
- [x] Lesson loop: N/A.
- [x] Knowledge layer: N/A (no user-visible behaviour).
- [ ] Commit message explains why; record committed with the change: pending the owner's word.

## Skipped items — visible, never silent

- **Independent verifier:** not required for a routine documentation change (BUILD-PROCEDURE.md, "Risk tiers").
- **Full gate, review, commit (§5):** the commit, the push and the pull request wait for the owner's word; CI's full gate and the owner's review happen on the pull request. Recorded here when seen.

## Evidence log

All runs 2026-10-21 in the worktree, on `main`'s `c070a98` plus the staged edits, before this log was written.

```
$ git diff --check; git diff --cached --check            -> no whitespace errors, tree and index
$ python3 scripts/quality/repo_hygiene.py .              -> rc 0 (the three files staged)
$ git diff --cached --stat                                -> 3 files changed, 180 insertions(+), 4 deletions(-)
    docs/adr/0007-rootful-range-per-container.md                               | 101 +-
    docs/architecture/platform-plan.md                                         |   9 +-
    docs/build-records/2026-10-21-adr-0007-clarification-rootless-and-pods.md  |  74 +
$ awk cell counts: D13 4 cells, D14 4 cells; the clarification's table 5 rows of 3 cells;
  ADR 0007's status row 2 cells
$ relative links and `docs/...md` paths in the three files: 31 checked, 3 unresolved, all
  pre-existing lines of platform-plan.md that point into the previous repository
  (docs/plans/BLUEPRINT.md, docs/plans/UniversalAgenticPayment.md,
  docs/build-records/2026-09-26-lnd-rpccookie.md); none in an added line
  (git diff --cached -U0 shows the four added lines of the plan)
$ Podman's podman-pod-create.1.md.in, read from raw.githubusercontent.com (containers/podman, main):
  --share "Defaults match Kubernetes default (ipc, net, uts)", choices "cgroup, ipc, net, pid, uts";
  --infra "Default: true"; --publish "only by the pod itself"; /etc/hosts and /etc/resolv.conf
  "shared between all containers in the pod"
```
