# Build Record — Draft ADRs 0013 and 0014: Nix-built shell-less images, the runbook executor

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Author / session** | Claude (Sonnet 5.5, desktop chat session) for Henry Chen |
| **Branch** | `docs/adrs-0010-0014`, made in a cloud-session clone at `/home/claude/rikurinode` (the owner's Mac could not reach GitHub from that session) and stacked on `fix/rustsec-2026-0382` (pull request #18) so its CI can pass; the same files were first written uncommitted in the owner's checkout on the Mac, byte-identical (sha256 compared) |
| **Commits** | `c8f3e82` (ADRs 0010 to 0014 and their two records), `2708860` (the plan, register and threat-model edits and their three records), `51e6692` (the verifier's first-pass corrections), the next commit (these rows); the pre-commit hook ran on each (gitleaks "no leaks found"). Committed, pushed and opened as a pull request on the owner's word ("commit, create branch, verify and make pull request", 2026-10-20) |
| **Status** | COMPLETE; the ADRs stay Proposed until the owner accepts them. One `verifier` pass over all five records of this branch: **FAIL** on one Important finding (threat model rows T20 to T24 and T26 read as adopted), fixed in `51e6692` with its nits; follow-up pass **PASS**. CI seen green on pull request #19: run #48 `Full gate (Ubuntu)` on `5eee4c7`, 2026-10-20 20:27–20:29 UTC; merged by the owner as `3018f4f` at 20:37 UTC; `main` green after it (run #51) |
| **Change type** | ops (architecture decisions; documentation only) |

## Task Contract

1. **Outcome:** two ideas the owner liked in the design discussion of 2026-10-20 (container images built by Nix with nothing in them but the program, and a runbook executor that acts through APIs and never a shell) are written as ADRs in the repository's format, ready for the owner's review.
2. **Scope:** this record; `docs/adr/0013-nix-built-shell-less-images.md` and `docs/adr/0014-runbook-executor.md` (new). Tier: **high-risk** (the supply chain of every image; the node's self-repair authority); documentation only, so one verifier pass. **Not included:** the platform plan's D20 and D21 rows, any change to `docs/architecture/platform-plan.md` §4.2, `control-plane/clippy.toml`, CI, the Containerfile, any Nix file or code; each is listed under "Edits that follow" in its ADR.
3. **Done when:** each ADR carries the owner's words, status Proposed, alternatives and costs, and sources with the date read; the Nix ADR is framed as an experiment with stated keep or drop criteria (AGENTS.md §6); every claim about the repository names its file or lesson; relative links resolve; `git diff --check` is clean; `repo_hygiene.py` exits 0; the verifier's pass has no Important finding; the owner confirms or edits the wording.
4. **Authority:** create the two files above; read the repository and the web. No commit, push, branch or PR; no Nix installed or run; no node touched.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured.

## 0. Intent

- [x] **Problem, in the owner's words** (2026-10-20): "Yes, let's promote Nix-built images and Rusts runbook executor to ADRs."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** stages 2 to 6 (image builds, health probes, self-repair); nothing running.
- [x] **Open questions:** in each ADR; the main ones are whether an upstream Bitcoin Core binary can run in a from-scratch image without changing the bytes the signature covered, and whether Quadlet's `HealthCmd=` accepts an exec form with no shell.
- [x] **Owner approved the intent:** the message above.

## 0b. Spec

- [x] **Requirements:** the repository's ADR shape; a proposal that conflicts with a decided text says so and proposes the amendment (the Nix ADR against plan §4.2; the executor ADR against my own earlier suggestion of YAML runbooks and against the assistant plan §3.4, which already says Rust values); nothing is recorded as Accepted.
- [x] **Design:** two ADRs. Rejected: one ADR for both (different stages and owners); adding D20 and D21 to the plan now (not asked; listed as follow-ups).
- [x] **Policy applied:** the first principle; "before adopting third-party code, inspect" (AGENTS.md §2) written into the Nix ADR's experiment; "an experiment ends in keep, simplify or drop" (§6).
- [x] **Flagged concerns:** (1) shell-less images need an exec-form probe or ADR 0005's `Notify=healthy` breaks: written into the Nix ADR. (2) Patching an upstream binary to run in a from-scratch image changes what its signature covered: written as the experiment's first question. (3) The tier ladder in ADR 0014 is new (the repository has none beyond HEAL-01's "tiered proposal"): marked as proposed.

## 1. Plan

- [x] **One sentence:** write two Proposed ADRs and this record, then check them.
- [x] **Blast radius:** two new untracked files; nothing irreversible.
- [x] **Current behaviour characterized:** read this session: ADR 0002, 0005, 0007, `docs/architecture/platform-plan.md` §4.2, `docs/architecture/assistant-plan.md` §3.4 and contract A, `control-plane/clippy.toml`, the lessons register's HEAL-01 to HEAL-10, EXEC-01, PLAT-06.
- [x] **Files and order:** this record, ADR 0013, ADR 0014, checks.
- [x] **Risks:** a claim about Nix stated more firmly than its source.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] New documents follow the ADR shape.
- [x] **Security question answered:** the ADRs touch the image supply chain and the repair authority. Gates and tests that will cover them are named in the ADRs; none exists yet, so everything is Not yet proven.

## 3. Debug

- N/A

## 4. Verify

- [x] Checks: see the Evidence log.
- [x] Independent verification: one `verifier` pass over the five records of this branch, FAIL on one Important finding (T20 to T24 and T26 not marked Proposed), corrected in `51e6692` with the nits; follow-up pass PASS. Backlog nit: none open in this record.

## 5. Close Out

- [x] Full gate: CI seen green on pull request #19: run #48 `Full gate (Ubuntu)` on `5eee4c7`, 2026-10-20 20:27–20:29 UTC; merged by the owner as `3018f4f` at 20:37 UTC; `main` green after it (run #51). Review and commit: done, see Status and Commits.

## Skipped items — visible, never silent

- (none open: CI's full gate has since passed, see Status)
- **Follow-up edits (D20 and D21 rows in the plan, §4.2's amendment if the Nix experiment keeps, the clippy ban, threat model rows T25 and T26):** T25 and T26 are done in `2026-10-20-follow-ups-f3-b5-ai02-threat-model.md`; the rest are their own tasks.

## Evidence log

Checks run 2026-10-20 on the uncommitted files (documentation only):

- `git diff --no-index --check /dev/null <file>` on both ADRs and this record:
  no whitespace errors reported.
- `python3 scripts/quality/repo_hygiene.py .`: exit 0.
- Relative links and backticked repository paths in both ADRs: 0 broken.
- Every lesson ID the ADRs cite exists in the lessons register; the claims
  drawn from HEAL-01 to HEAL-04, HEAL-08, EXEC-01 and PLAT-06 were re-read
  against their entries, and the assistant plan's §3.4 and ADR 0005 and 0007
  were re-read for the runbook and probe statements.
- Two typing slips in ADR 0014 ("ADR 5", and a sentence saying the drills
  "prove" a rule) were corrected before this record closed.
- Not run: the verifier pass, the full gate, the guard tests (nothing under
  `.claude/` changed). No Nix was installed or run, so every statement about
  Nix's behaviour rests on the cited documentation only.
