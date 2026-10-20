# Build Record — Platform plan: add D20 (Nix-built images, an experiment) and D21 (the runbook executor) as proposed

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Author / session** | Claude (Sonnet 5.5, desktop chat session) for Henry Chen |
| **Branch** | `docs/adrs-0010-0014`, made in a cloud-session clone at `/home/claude/rikurinode` (the owner's Mac could not reach GitHub from that session) and stacked on `fix/rustsec-2026-0382` (pull request #18) so its CI can pass; the same files were first written uncommitted in the owner's checkout on the Mac, byte-identical (sha256 compared) |
| **Commits** | `c8f3e82` (ADRs 0010 to 0014 and their two records), `2708860` (the plan, register and threat-model edits and their three records), `51e6692` (the verifier's first-pass corrections), the next commit (these rows); the pre-commit hook ran on each (gitleaks "no leaks found"). Committed, pushed and opened as a pull request on the owner's word ("commit, create branch, verify and make pull request", 2026-10-20) |
| **Status** | COMPLETE; the ADRs stay Proposed until the owner accepts them. One `verifier` pass over all five records of this branch: **FAIL** on one Important finding (threat model rows T20 to T24 and T26 read as adopted), fixed in `51e6692` with its nits; follow-up pass **PASS**. CI seen green on pull request #19: run #48 `Full gate (Ubuntu)` on `5eee4c7`, 2026-10-20 20:27–20:29 UTC; merged by the owner as `3018f4f` at 20:37 UTC; `main` green after it (run #51) |
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

- [x] Checks: see the Evidence log.
- [x] Independent verification: one `verifier` pass over the five records of this branch, FAIL on one Important finding (T20 to T24 and T26 not marked Proposed), corrected in `51e6692` with the nits; follow-up pass PASS. Backlog nit: none open in this record.

## 5. Close Out

- [x] Full gate: CI seen green on pull request #19: run #48 `Full gate (Ubuntu)` on `5eee4c7`, 2026-10-20 20:27–20:29 UTC; merged by the owner as `3018f4f` at 20:37 UTC; `main` green after it (run #51). Review and commit: done, see Status and Commits.

## Skipped items — visible, never silent

- (none open: CI's full gate has since passed, see Status)

## Evidence log

Checks run 2026-10-20 on the uncommitted edit (documentation only):

- `git diff --check`: clean. `python3 scripts/quality/repo_hygiene.py .`: exit 0.
- Rows D1 to D21 each have the table's four cells.
- Not run: the verifier pass, the full gate, the guard tests (nothing under
  `.claude/` changed).
