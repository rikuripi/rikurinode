# Build Record — Platform plan: add D18 and D19 as proposed, record the F3 amendment under D16

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Author / session** | Claude (Sonnet 5.5, desktop chat session) for Henry Chen |
| **Branch** | None created. The edit is uncommitted in this checkout, on top of `main` (AGENTS.md §2); the branch, commit and pull request are the owner's call |
| **Commits** | None |
| **Status** | IN PROGRESS: edited; verifier pass Not yet run; CI Not yet proven |
| **Change type** | ops (plan amendment; documentation only) |

## Task Contract

1. **Outcome:** the platform plan shows the two new proposed decisions (the lobby zone, remote and expert access) and the proposed F3 amendment, each pointing to its Proposed ADR, so the plan and the ADRs of `2026-10-20-lobby-zone-access-and-ai-lanes-adrs.md` agree.
2. **Scope:** `docs/architecture/platform-plan.md` only: the status paragraph, one "In one page" bullet, the D16 row (a dated amendment sentence), new rows D18 and D19 in §7, the security slice of stages 5 and 8 in §8, and a dated block in §9. Tier: **high-risk** (security decisions in the plan; documentation only, so one verifier pass). **Not included:** the assistant plan's F3 and contract B5, the AI-02 caveat, the threat model's rows, README.md, any ADR text, code.
3. **Done when:** D18 and D19 are marked proposed everywhere they appear and counted as open; the D16 text of 2026-10-18 is unchanged and the amendment is a dated addition; every claim names its ADR; `git diff --check` is clean; `repo_hygiene.py` exits 0; relative links resolve; the verifier's pass has no Important finding.
4. **Authority:** edit the one file; read the repository. No commit, push, branch or PR; nothing running was touched.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured.

## 0. Intent

- [x] **Problem, in the owner's words:** "You can do the platform-plan edit." (2026-10-20), after the three draft ADRs.
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** the plan's decision table and two stage slices; nothing running.
- [x] **Open questions:** none new; D18 and D19 stay open until the owner accepts ADRs 0010 and 0011.
- [x] **Owner approved the intent:** the message above.

## 0b. Spec

- [x] **Requirements:** keep decided text intact (ADR history is by dated clarification, AGENTS.md §3 "Conflicts"); a proposed decision is never written as decided; the counts in the status paragraph stay true.
- [x] **Design:** additions only, at the places the existing decisions use. Rejected: rewriting D16 (it was decided; the amendment is a dated sentence); marking D18 and D19 decided on the strength of the chat agreement (the ADRs are Proposed until the owner confirms their wording).
- [x] **Policy applied:** the first principle (the SSH window and the per-send approval default are explicit, reversible owner choices); no protection is called proven.
- [x] **Flagged concerns:** the status paragraph says "fifteen are taken"; it now says four are open, which is the honest count while D18 and D19 are Proposed.

## 1. Plan

- [x] **One sentence:** add D18, D19 and the D16 amendment to the plan as proposed, with their stage slices and sources.
- [x] **Blast radius:** one documentation file; nothing irreversible.
- [x] **Current behaviour characterized:** read this session: the status paragraph, "In one page", §7 rows D14, D16, D17, §8 rows 5 and 8, and the end of §9.
- [x] **Files and order:** this record, the plan, checks.
- [x] **Risks:** a count or cross-reference left stale.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] Additions only; no old text removed except the counts that the new open decisions change.
- [x] **Security question answered:** the edit records decisions about outside data, remote access and private data leaving the node; the tests are named in the ADRs and the stage slices and none exists yet, so every protection is Not yet proven.

## 3. Debug

- N/A

## 4. Verify

- [ ] Checks: see the Evidence log.
- [ ] Independent verification: `verifier` pass, Not yet run.

## 5. Close Out

- [ ] Full gate: Not yet proven (documentation-only; CI runs it on the pull request).
- [ ] Reviewed per `REVIEW.md`: Not yet run.
- [ ] Commit: not made.

## Skipped items — visible, never silent

- **Verifier pass, review, commit, full gate:** need a branch and the owner's go-ahead (AGENTS.md §2).

## Evidence log

Checks run 2026-10-20 on the uncommitted edit (documentation only):

- `git diff --stat`: one file, 28 insertions and 7 deletions; the deletions are
  the three counts and dates in the status paragraph, the D16, stage 5 and
  stage 8 lines that gained a dated sentence, and nothing else.
- `git diff --check`: clean. `python3 scripts/quality/repo_hygiene.py .`: exit 0.
- Every §7 row still has the table's four cells; D16's decided text of
  2026-10-18 is unchanged and the amendment is a dated addition.
- Not run: the verifier pass, the full gate, the guard tests (nothing under
  `.claude/` changed).
