# Build Record — Draft ADRs 0010 to 0012: the lobby zone, remote and expert access, cloud model lanes

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Author / session** | Claude (Sonnet 5.5, desktop chat session) for Henry Chen |
| **Branch** | `docs/adrs-0010-0014`, made in a cloud-session clone at `/home/claude/rikurinode` (the owner's Mac could not reach GitHub from that session) and stacked on `fix/rustsec-2026-0382` (pull request #18) so its CI can pass; the same files were first written uncommitted in the owner's checkout on the Mac, byte-identical (sha256 compared) |
| **Commits** | `c8f3e82` (ADRs 0010 to 0014 and their two records), `2708860` (the plan, register and threat-model edits and their three records), `51e6692` (the verifier's first-pass corrections), the next commit (these rows); the pre-commit hook ran on each (gitleaks "no leaks found"). Committed, pushed and opened as a pull request on the owner's word ("commit, create branch, verify and make pull request", 2026-10-20) |
| **Status** | DONE locally; the ADRs stay Proposed until the owner accepts them. One `verifier` pass over all five records of this branch: **FAIL** on one Important finding (threat model rows T20 to T24 and T26 read as adopted), fixed in `51e6692` with its nits; follow-up pass **PASS**. CI's `Full gate (Ubuntu)` Not yet proven when this row was written |
| **Change type** | ops (architecture decisions; documentation only) |

## Task Contract

1. **Outcome:** the owner's three agreements of 2026-10-20 (a lobby zone for everything that talks to outsiders, a diagnostics page and key-only SSH instead of a terminal in the web UI, and the cloud model lanes with a weekly sanitized performance review) are written as ADRs in the repository's format, ready for the owner's review.
2. **Scope:** this record; `docs/adr/0010-lobby-zone.md`, `docs/adr/0011-remote-and-expert-access.md`, `docs/adr/0012-cloud-model-lanes-and-performance-review.md` (all new). Tier: **high-risk** (security boundary, outside data transfer; BUILD-PROCEDURE.md, "Risk tiers"); documentation only, so the independent review is one verifier pass over the documents. **Not included:** the platform plan's D18 and D19 rows and stage slices, the assistant plan's F3 and contract B5, the AI-02 caveat, the threat model's rows, README.md and any code; each is listed under "Edits that follow" in its ADR and is its own task.
3. **Done when:** each ADR carries the owner's words, a status of Proposed, its alternatives and costs, and its sources with the date read; every claim about the repository names its file or lesson; relative links resolve; `git diff --check` is clean on the new files; `repo_hygiene.py` exits 0; the verifier's pass has no Important finding; the owner confirms or edits the wording and the proposed defaults.
4. **Authority:** create the four files above in this checkout. Read the repository and, for three external claims, the web. No commit, push, branch or PR. No running node was touched.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured.

## 0. Intent

- [x] **Problem, in the owner's words** (2026-10-20): "should these external data be in their own container to minimize exposure to attack? I use Tailscale, Telegram, Discord, cloud backup options (not used yet), tor and ssh (like Umbrel). There is a Terminal access with limited command (not sure if an expert would want full access to Terminal: is it safe?)"; on the AI: "a thinking model that may help to evaluate(reasoning) how the node is performing and if lightning management is maxmizing profitability, fees, and rebalancing. That may contradict the privacy on data."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** nothing running; the later stages that build helpers, remote access and the assistant.
- [x] **Open questions:** listed in each ADR's "Edits that follow" and in the plan document's open decisions (which remote path ships first, which helpers ship in version one, whether a bigger local model runs on an owner-run machine, the proposed SSH window and the per-send approval default).
- [x] **Owner approved the intent:** "Ok, so we'll stay rootful, and make all the adjustments you just listed with report-card schema and F3 changes to the Rikuri Node Plan." then "Yes, draft the ADRs in repo format" (2026-10-20). ADR 0007 (rootful, a range per container) is re-confirmed by the first message and needs no edit.

## 0b. Spec

- [x] **Requirements:** the repository's ADR shape (status table, Context, Decision, Consequences, Rejected, Sources); the owner's words quoted; alternatives with their costs; proposed defaults marked as the owner's reversible settings (AGENTS.md §6); no behaviour or rule is recorded as Accepted without the owner's confirmation.
- [x] **Design:** three ADRs, one per decision (D18, D19, the F3 amendment), each small enough to be accepted or sent back on its own. Rejected: one ADR for all three (they have different owners in the plan: platform, access, assistant); editing ADR 0007 (it is not contradicted); drafting an ADR for Nix-built images (a proposal with no decision yet; it stays in the plan document's open decisions).
- [x] **Policy applied:** hard limits outside the model; outside data transfers stay with the owner; a lock the server does not enforce is not a lock (EXEC-04); the first principle (behaviour-changing defaults are explicit, costed, reversible owner choices).
- [x] **Flagged concerns:** (1) Three external claims came from the web and are cited in the ADRs: Telegram's cloud chats are not end-to-end encrypted (that Bot API messages are cloud chats is flagged "to be confirmed"), Tailscale HTTPS certificates publish machine names in the Certificate Transparency ledger, and LND encrypts static channel backups with a key derived from the seed (cited in the plan document, not in an ADR). (2) No provider's retention or training terms were read; ADR 0012 makes reading them a condition of enabling one.

## 1. Plan

- [x] **One sentence:** write three Proposed ADRs and this record, then check them and hand them to the owner.
- [x] **Blast radius:** four new untracked files; nothing irreversible.
- [x] **Current behaviour characterized:** read this session: `AGENTS.md` §1 to §6, `docs/adr/0006`, `0007`, `0009`, `docs/architecture/platform-plan.md` §7 and §8, `docs/architecture/assistant-plan.md` §2, §3.1, §3.7 and §6, `docs/security/THREAT_MODEL.md` §1 to §3 and §8, the lessons register's EVID, EXEC, HEAL, UPG, AI and FUND entries named in the ADRs; `git for-each-ref` for ADR numbers in flight (none beyond 0009 on any branch).
- [x] **Files and order:** this record, ADR 0010, ADR 0011, ADR 0012, checks.
- [x] **Risks:** a claim stated more firmly than its source; a default read as a decision; numbering clashing with a branch not fetched.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] New documents follow the existing ADR shape.
- [x] Clean as you go: no old version replaced.
- [x] **Security question answered:** the ADRs touch outside data transfer, private data and remote access. The gates that will cover them are the threat model's rows (to be added) and the tests named in each ADR (route-scope test, egress test, fixture-card test, remote-path drill); none exists yet, so every protection is Not yet proven.

## 3. Debug

- N/A: no defect fixed.

## 4. Verify

- [ ] Links, `git diff --check` and hygiene: see the Evidence log.
- [x] Independent verification: one `verifier` pass over the five records of this branch, FAIL on one Important finding (T20 to T24 and T26 not marked Proposed), corrected in `51e6692` with the nits; follow-up pass PASS. Backlog nit: none open in this record.
- [ ] Diff matches the §1 plan: yes; one extra file, this record, as the procedure requires.

## 5. Close Out

- [ ] Full gate: Not yet proven (documentation-only: link and citation checks, `git diff --check`; CI runs the full gate on the pull request).
- [x] Reviewed per `REVIEW.md`: the verifier's two passes above.
- [ ] Knowledge layer updated: the follow-up edits listed in each ADR are not done.
- [x] Commit: made and pushed; see the Commits row.

## Skipped items — visible, never silent

- **Full gate:** CI's `Full gate (Ubuntu)` on the pull request, Not yet proven when this record was closed.
- **Follow-up edits (platform plan D18 and D19, assistant plan F3 and B5, AI-02 caveat, threat model rows):** each is its own task by AGENTS.md §3.

## Evidence log

Checks run 2026-10-20 on the uncommitted files (documentation only):

- `git diff --no-index --check /dev/null <file>` on all four files: no
  whitespace errors reported (the exit code 1 is the diff's, not the check's).
- `python3 scripts/quality/repo_hygiene.py .`: exit 0.
- Relative links and backticked repository paths in the four files: 0 broken.
- Every lesson ID the ADRs cite (EVID-05, EVID-06, HEAL-09, UPG-04, AI-02,
  EXEC-04, EXEC-07, EXEC-08, SEC-01, FUND-01 to FUND-04) exists in
  the lessons register, and the claims drawn from them were re-read against
  their entries.
- Quoted plan text (D10, D11, F2, F3, B5, threat model §8) re-read against the
  files; one overstatement about F2 was corrected before this record closed.
- Not run: the verifier pass, the full gate, the guard tests (nothing under
  `.claude/` changed).
- A stray empty file, `docs/adr/.write-test`, was created while testing that
  the folder was writable and removed with the owner's approval of a deletion
  prompt; nothing else was deleted.
