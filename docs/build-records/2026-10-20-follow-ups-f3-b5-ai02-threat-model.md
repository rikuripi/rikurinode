# Build Record — Follow-ups to ADRs 0010 to 0014: assistant plan F3 and B5, AI-02's caveat, the threat model's rows

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Author / session** | Claude (Sonnet 5.5, desktop chat session) for Henry Chen |
| **Branch** | None created. The edits are uncommitted in this checkout, on top of `main` (AGENTS.md §2) |
| **Commits** | None |
| **Status** | IN PROGRESS: edited; verifier pass Not yet run; CI Not yet proven |
| **Change type** | ops (plan, register and threat-model amendments; documentation only) |

## Task Contract

1. **Outcome:** the assistant plan, the lessons register and the threat model agree with the Proposed ADRs 0010 to 0014, so no document still says the opposite of a proposal the owner has seen.
2. **Scope:** `docs/architecture/assistant-plan.md` (the F3 row, the "In one page" cloud bullet, contract B5, the §5 sequence row, §6 open items); `docs/requirements/lessons-register.md` (AI-02's "Superseded / caveat" line, one dated sentence); `docs/security/THREAT_MODEL.md` (§3 lists, rows T20 to T26 in §4, the "Shell access" bullet in §8, a sources entry). Tier: **high-risk** (security boundary and an outside-data rule); documentation only, so one verifier pass. **Not included:** the platform plan (done in `2026-10-20-platform-plan-d18-d19.md`; its D20 and D21 rows are a later task), `README.md`, any ADR text, code, CI.
3. **Done when:** every addition is dated 2026-10-20 and names its ADR and says Proposed; the decided texts of 2026-10-18 are unchanged and the additions are dated clarifications (AGENTS.md §8, "Conflicts"); the new rows are Not yet proven; `git diff --check` is clean; `repo_hygiene.py` exits 0; relative links resolve; the verifier's pass has no Important finding.
4. **Authority:** edit the three files; read the repository. No commit, push, branch or PR; nothing running was touched.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured.

## 0. Intent

- [x] **Problem, in the owner's words** (2026-10-20): "Then, do the follow=ups from F3 and B5, then AI-02 and threat-model rows."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** three documents; nothing running.
- [x] **Open questions:** none new; every addition stays Proposed until the owner accepts its ADR.
- [x] **Owner approved the intent:** the message above.

## 0b. Spec

- [x] **Requirements:** additions only, dated; no decided text rewritten; each new threat-model row has a control, a stage, a proof and the status Not yet proven.
- [x] **Design:** the amendments sit beside the text they amend. Rejected: editing F3's decided wording (ADR history is by dated clarification); marking anything Accepted.
- [x] **Policy applied:** the first principle; the threat model's own rule that every row is Not yet proven until its test is seen to pass.
- [x] **Flagged concerns:** the threat model's §3 "Out of scope" list is unchanged; Tailscale's and the chat services' coordination servers join the "not trusted" list.

## 1. Plan

- [x] **One sentence:** add the proposed amendments to the three documents.
- [x] **Blast radius:** three documentation files; nothing irreversible.
- [x] **Current behaviour characterized:** read this session: the assistant plan's F2, F3, §3.4, contract A, B5, §6 and the lines mentioning the cloud; AI-02; the threat model's §3, §4 (T1 to T19), §8 and §9.
- [x] **Files and order:** this record, assistant plan, AI-02, threat model, checks.
- [x] **Risks:** a count or cross-reference left stale.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] Additions only.
- [x] **Security question answered:** the edits record rules about outside data, remote access and image supply; no test exists yet, so every protection is Not yet proven.

## 3. Debug

- N/A

## 4. Verify

- [ ] Checks: see the Evidence log. [ ] Independent verification: `verifier` pass, Not yet run.

## 5. Close Out

- [ ] Full gate, review, commit: not done (documentation-only; needs a branch and the owner's go-ahead).

## Skipped items — visible, never silent

- **Verifier pass, review, commit, full gate:** need a branch and the owner's go-ahead.

## Evidence log

Checks run 2026-10-20 on the uncommitted edits (documentation only):

- `git diff --check`: clean. `python3 scripts/quality/repo_hygiene.py .`: exit 0.
- Links and backticked paths in the added lines: 0 broken (the files hold
  older references to the previous repository's paths; none were touched).
- Every new threat-model row has the table's six cells, T20 to T26 follow
  T19, and each is marked Not yet proven. AI-02's rule text and the 2026-10-18
  caveat are unchanged; the new sentence is appended and dated.
- The assistant plan's F3 row keeps its decided text; the amendment is a dated
  addition, and B5, the "In one page" bullet, §5 and §6 point to ADR 0012.
- Not run: the verifier pass, the full gate, the guard tests (nothing under
  `.claude/` changed).
