# Build Record — Platform plan: add D20 (Nix-built images, an experiment) and D21 (the runbook executor) as proposed

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Author / session** | Claude (Sonnet 5.5, desktop chat session) for Henry Chen |
| **Branch** | None created. The edit is uncommitted in this checkout, on top of `main` and the other uncommitted changes of 2026-10-20 (AGENTS.md §2) |
| **Commits** | None |
| **Status** | IN PROGRESS: edited; verifier pass Not yet run; CI Not yet proven |
| **Change type** | ops (plan amendment; documentation only) |

## Task Contract

1. **Outcome:** the platform plan lists the two proposals of ADRs 0013 and 0014 as open decisions, so the plan and the ADRs agree.
2. **Scope:** `docs/architecture/platform-plan.md` only: the status paragraph, rows D20 and D21 in §7, and the security slices of stages 2 and 7 in §8. Tier: **high-risk** (image supply chain; self-repair authority); documentation only, so one verifier pass. **Not included:** §4.2's text (amended only if the Nix experiment keeps), `control-plane/clippy.toml`, CI, any ADR text, code.
3. **Done when:** D20 and D21 are marked proposed everywhere they appear and counted as open; no decided text changes; `git diff --check` is clean; `repo_hygiene.py` exits 0; the verifier's pass has no Important finding.
4. **Authority:** edit the one file; read the repository. No commit, push, branch or PR; nothing running touched.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured.

## 0. Intent

- [x] **Problem, in the owner's words:** "Ok next" (2026-10-20), answering "Do you want the D20 and D21 rows next?"
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** the plan's decision table and two stage slices; nothing running.
- [x] **Open questions:** none new; D20 stays an experiment and D21 stays open until the owner accepts the ADRs.
- [x] **Owner approved the intent:** the message above.

## 0b. Spec

- [x] **Requirements:** additions only; a proposal never written as decided; the counts in the status paragraph stay true.
- [x] **Design:** two rows after D19 and one sentence in each of two stage slices. Rejected: amending §4.2 now (the experiment has not run).
- [x] **Policy applied:** the first principle; an experiment ends in keep, simplify or drop (AGENTS.md §6).
- [x] **Flagged concerns:** none.

## 1. Plan

- [x] **One sentence:** add D20 and D21 as proposed, with their stage slices.
- [x] **Blast radius:** one documentation file; nothing irreversible.
- [x] **Current behaviour characterized:** read this session: the status paragraph, §7 D19, §8 rows 2 and 7.
- [x] **Files and order:** this record, the plan, checks.
- [x] **Risks:** a stale count.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] Additions only, except the counts the new open decisions change.
- [x] **Security question answered:** the rows record proposals about image contents and repair authority; their tests are named and none exists, so nothing is proven.

## 3. Debug

- N/A

## 4. Verify

- [ ] Checks: see the Evidence log. [ ] Independent verification: `verifier` pass, Not yet run.

## 5. Close Out

- [ ] Full gate, review, commit: not done (documentation-only; needs a branch and the owner's go-ahead).

## Skipped items — visible, never silent

- **Verifier pass, review, commit, full gate:** need a branch and the owner's go-ahead.

## Evidence log

Checks run 2026-10-20 on the uncommitted edit (documentation only):

- `git diff --check`: clean. `python3 scripts/quality/repo_hygiene.py .`: exit 0.
- Rows D1 to D21 each have the table's four cells.
- Not run: the verifier pass, the full gate, the guard tests (nothing under
  `.claude/` changed).
