# Build Record — Security built in: the node's threat model, a security slice per stage, AISecurity's place

| | |
|---|---|
| **Date** | 2026-10-18 |
| **Author / session** | Claude Code (Fable 5.1) for Henry Chen, in the owner's desktop session |
| **Branch** | `docs/security-plan-2026-10-18`, this checkout, stacked on `docs/assistant-plan-2026-10-18` at `5cc484d` (pushed, its pull request not yet open) because this change cites ADR 0008 and edits the assistant plan. Whichever pull request lands second rebases. No upstream entry (the sandbox refuses `.git/config` writes). |
| **Commits** | (fill at close-out) |
| **Status** | DONE locally, 2026-10-18: every "Done when" item holds (§4), the verifier passed with five nits, all fixed in place. Not committed, not pushed; CI Not yet proven |
| **Change type** | ops (threat model, architecture decision, plan amendments; documentation only) |

## Task Contract

1. **Outcome:** the node has a threat model of its own, every stage of the platform plan names the security it ships and the tests that prove it, and the owner's four security decisions of 2026-10-18 are recorded, so security is built with each module and never added afterwards.
2. **Scope:** this record; `docs/security/THREAT_MODEL.md` (new); `docs/adr/0009-security-built-in.md` (new); `docs/architecture/platform-plan.md` (status line, one "In one page" bullet, a fourth column in the §8 stage table, a §7 row D17); `AGENTS.md` (one sentence in "Security baseline" and one row in §8's table, both pointers); `docs/architecture/assistant-plan.md` (§6: the redaction filter is decided). Tier: **high-risk** — the threat model fixes the security boundary's assumptions and `AGENTS.md` is an agent-rules file ([BUILD-PROCEDURE.md, "Risk tiers"](../../.agents/workflows/BUILD-PROCEDURE.md#risk-tiers)); documentation only, so the independent review is one verifier pass over the documents and no mutation run. **Not included:** code; CI and the quality scripts (the weekly scheduled audit, the merged advisory source and the image scanner are a control change and the next task); `BUILD-PROCEDURE.md`'s periodic loops (they change with that task); the guard; the lessons register; any port of AISecurity's code; the fork repositories.
3. **Done when:** the threat model names the assets, what is trusted and what is not, and maps each threat to a control, a stage and a test; every stage row in the platform plan has a security slice that the threat model details; the four decisions are in the plan's §7 and in ADR 0009 with the owner's words; the two intake defaults chosen here (the release cadence for advisories, the weekly audit) are stated as explicit, reversible owner settings; every claim about AISecurity, Rikuri-PI or the previous repository names its file; every relative link and anchor resolves; `git diff --check` is clean; `repo_hygiene.py` exits 0; the guard's tests still pass (an `AGENTS.md` edit touches a protected path); the verifier's pass has no Important finding.
4. **Authority:** edit the files in Scope on the task branch; read `/home/junc/AISecurity`, `/home/junc/Rikuri-PI` and the previous checkout by absolute path, read-only. One verifier pass. No commit, push or PR until the owner says so (the owner's standing rule). No code, no other agents.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured; consumption reported at close-out.

## 0. Intent

- [x] **Problem, in the owner's words** (2026-10-18): "Is our emphasis on node and AI security well defined along the way? We have existing security as well as the need to keep up with the latest vulnerability popping up concurrently. Our AISecurity on Mac that partially includes Linux implementation. So, this needs to be developed along side each module we build from beginning to finish." After the assessment: "for the 4 choices 1 through 4, do as you recommended. Our security should fit the node like a glove. Can't be an after thought."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** every stage's deliverables and drill; the agent rules' pointers; the assistant plan's redaction filter; nothing running.
- [x] **Open questions:** the four choices were put to the owner with their alternatives and costs and answered "do as you recommended": S1 AISecurity's core crate linked as a pinned dependency that signals and never enforces; S2 a weekly scheduled advisory audit plus a release cadence for advisories; S3 an image scanner adopted after the inspection the rules require; S4 the threat model now. Two defaults inside S2 were not put as numbers and are chosen here as reversible settings (§0b).
- [x] **Owner approved the intent:** the assessment ended "Next: one Build Record that writes the node's threat model, adds the security column to the stage table and records the AISecurity decision"; the owner answered "do as you recommended" (2026-10-18).

## 0b. Spec

- [x] **Requirements:** a threat model in the shape Rikuri-PI adopted (assets, trust assumptions, threats to controls to owning tests), written for this node's assets; a security slice per stage that the stage's drill proves; the decisions recorded with the owner's words, each with its alternatives and costs; defaults chosen by the author stated as the owner's reversible settings; every protection marked Not yet proven until its test passes; rules relaxed or extended keep their history.
- [x] **Design:** one threat model document under `docs/security/`, the platform plan's stage table gains a column that points into it, one ADR for the architecture decision (AISecurity linked as a pinned crate, the signals-versus-enforcement split, the intake loop's shape), and pointers from `AGENTS.md`. Rejected: putting the threat model inside the platform plan (it is a living security document with its own evidence section, like Rikuri-PI's); an ADR per decision (S2 to S4 are process decisions, recorded in the threat model and D17; S1 is the architecture decision); editing `BUILD-PROCEDURE.md`'s weekly loop now (it changes with the CI task so the scheduled gate and the owner's loop land together); vendoring `security-core` as the previous node did (its `vendor/security-core/PROVENANCE.md` records a fork that had to be re-synced by hand and had wasmtime stripped manually; a pinned Git dependency with `default-features = false` gets the same result without a fork).
- [x] **Policy applied:** the first principle in every decision and in the two defaults; the security baseline (hard limits outside the model; egress denied by default; stop when blocked; keys never in context; one component never holds untrusted input, outside communication and payment authority together); the design rules (nothing fails silently: a detector that stops firing alarms; runtime truth: security health reflects measured protection; pinning: the crate by commit).
- [x] **Flagged concerns:** (1) `AGENTS.md` is a protected path and an agent-rules file; the edit is two pointers and no rule change, and the guard logs the write in the `development` profile. (2) Linking `security-core` brings its dependency tree inside the control plane's boundary; the ADR requires `default-features = false`, a feature set limited to the detectors used, and cargo-deny over the result, and names the check that proves it before any code. (3) Disk encryption at rest is a real gap no decision covers; the threat model lists it as an open owner decision (S5), not decided here.

## 1. Plan

- [x] **One sentence:** write the threat model and ADR 0009, add the security slice to every stage, record D17, point `AGENTS.md` and the assistant plan at them.
- [x] **Blast radius:** documents only; nothing irreversible; Git history keeps the old texts.
- [x] **Current behaviour characterized:** read 2026-10-18: `AGENTS.md` (§2, §7 Security baseline, §8), `REVIEW.md` (passes), `.agents/workflows/BUILD-PROCEDURE.md` (risk tiers, periodic loops, release gate), `docs/architecture/platform-plan.md` (§4, §7, §8), `docs/architecture/agent-payments-and-marketplace-plan.md` (§2, §4.3), the lessons register's EXEC, SEC, UPG, TEST and AI rules and gap G5, `.github/workflows/{ci,image,claude-guard}.yml` (triggers and steps), `control-plane/deny.toml`; `/home/junc/AISecurity` at `12ff2e8` (`README.md`, `docs/AISECIMPLEMENTATION.md`, `.github/workflows/supply-chain-weekly.yml`, `SecurityCore/Cargo.toml`, `SecurityCore/crates/security-core/Cargo.toml` and `src/`, `crates/security-linux/src/`); `/home/junc/Rikuri-PI` (`docs/security/THREAT_MODEL.md`, `docs/architecture/adr/0004-foundation-threat-model-assumptions.md`); the previous repository at `3bbbe392` (`vendor/security-core/PROVENANCE.md`); the owner's briefing notes of 2026-10-10, -11 and -12 in `/home/junc/Security Briefing/`. Findings in the Evidence log.
- [x] **Files and order:** this record → the threat model → ADR 0009 → the platform plan → `AGENTS.md` → the assistant plan → checks → the verifier → corrections.
- [x] **Riskiest step:** claiming a protection the node does not have. Guard: every control in the threat model carries "Not yet proven" and the stage and test that will prove it; §6 of the threat model lists what exists today and nothing more.
- [x] **I will know this works when** the "Done when" line holds and a stage's Build Record can copy its security slice into its own "Done when".

## 2. Build

- [x] `docs/security/THREAT_MODEL.md` (new): status; §1 highest responsibility; §2 eleven assets with where they live and the protection required; §3 what is trusted, what is not, what is out of scope; §4 nineteen threats (T1 to T19), each with its control, owning stage, proof and status, all Not yet proven except the development controls already in place and the two open items; §5 the security slice of every stage (boundary, controls, negative tests, drill addition); §6 the intake loop with its sources, cadence and the two defaults chosen as owner settings; §7 AISecurity's place (role, form, dependency cost, detectors by stage, lockstep, readiness); §8 open decisions (S5 disk encryption, shell access, G9); §9 current evidence and limits; §10 sources with revisions.
- [x] `docs/adr/0009-security-built-in.md` (new): context (the assessment's three gaps; AISecurity's state and posture; the previous node's vendored fork; Rikuri-PI's split); decision S4, S1, S2, S3 with the owner's words; consequences; rejected (the daemon beside the control plane, deferral, vendoring, the app's dial, quarterly audits, dependency bots, a threat model at stage 7); sources.
- [x] `docs/architecture/platform-plan.md`: status line (D17; seventeen decisions, fifteen taken; ADRs 0001 to 0009); an "In one page" bullet, "Security fits each stage"; the §8 stage table gains a fourth column, "Its security slice", filled for all ten stages and linked to the threat model's §5; a §7 row D17 with S1 to S4 and their rejected alternatives.
- [x] `AGENTS.md`: one sentence in "Security baseline" pointing at the threat model and ADR 0009; one row in §8's table. No rule changed. The guard logged the protected-path writes (development profile) and its tests still pass (Evidence log).
- [x] `docs/architecture/assistant-plan.md`: §6, the redaction filter is no longer open: AISecurity's sensitive-data and key-filter detectors, linked as a pinned crate (ADR 0009, threat model §7).
- [x] **Clean as you go:** no replaced text; the stage table keeps its three columns and gains one; the assistant plan's open item is narrowed, not duplicated.
- [x] **Security question:** no code. The documents define controls; none grants authority. The `AGENTS.md` edit is pointers only. The two defaults chosen by the author (7 and 30 days, one set a month) are stated as the owner's reversible settings in the threat model §6, D17 and ADR 0009.

## 3. Debug

N/A: no defect fixed.

## 4. Verify

- [x] Links and anchors in the changed files resolve: 33 relative links in the six changed files, 0 broken (Evidence log).
- [x] `git diff --check` clean; `python3 scripts/quality/repo_hygiene.py .` exit 0; `python3 -I .claude/hooks/test_guard.py` exit 0; `check_guard_wiring.py` and `guard_policy.py --check` exit 0 (Evidence log). Table shapes: every stage row and D17 have the header's column count; the threat model's four tables are each uniform.
- [x] Independent verification — `verifier` subagent, one pass over the documents: **PASS, no Important finding, five nits.** It re-ran the gate's documentation checks (links 33/0, `diff --check`, hygiene, wiring, policy), the guard's 91 tests and the quality tools' 80 tests inside `safe-run.sh`, and read every cited source by absolute path: AISecurity's crates, module count, Cargo features and dependencies, status counts and weekly workflow; Rikuri-PI's §4 wording and ADR 0004; the previous node's PROVENANCE.md; this repository's workflow triggers, deny.toml, the procedure's loops, 23 register rule IDs, the ADR and decision references; the owner's quotes (verbatim). Nits and their fixes: (1) AISecurity's implementation plan contradicts itself on the Linux daemon (PAM and notification channels marked both done and not started) — the three documents now say the rows disagree instead of "notifications not started"; (2) "on every push" overstated CI's triggers — now "pull requests and pushes to `main`" in the threat model (T8, §6, §9) and the ADR; (3) the plan's "In one page" bullet read as present tense — now "once the CI task lands"; (4) the guard tests had been run outside `safe-run.sh` — rerun inside it, 91 tests OK (Evidence log); (5) the untracked `.codex/` folder, not this task's, left as found and reported to the owner.
- [x] Diff matches the §1 plan: the six files in Scope and nothing else (the verifier confirmed). Deviation: none.

## 5. Close Out

- [x] Full gate: not run (documentation only; `AGENTS.md` §5 names the checks for it, all run above, the guard's tests inside `safe-run.sh`); CI runs the full gate on the pull request.
- [x] Scrap sweep: the link checker and the edit scripts live in the session's scratchpad, not the repository; nothing in the tree beyond the three new files and the three edits. The untracked `.codex/` folder (2026-10-14, not this task's) was left as found; the owner disposes.
- [x] Reviewed per `REVIEW.md`: the verifier's three passes above, plus the author's own re-read. No Important finding; the five nits fixed in place.
- [x] Lesson loop: N/A (no mistake made twice; the nits were wording).
- [x] Knowledge layer: the threat model and the ADR are the knowledge for this change; the stage table carries the short form.
- [ ] Commit message explains WHY; record committed with the change: on the owner's word.

## Skipped items — visible, never silent

- §5 "Commit": the owner's standing rule; the commit and push follow the owner's word, and the Commits row is filled then.
- §5 "Full gate": documentation-only change; the `AGENTS.md` §5 checks replace it locally and CI runs the gate on the pull request.

## Evidence log

```
Read 2026-10-18 (read-only, absolute paths):
  AISecurity /home/junc/AISecurity HEAD 12ff2e8 (2026-10-05 "fix(guard): sync guard.py/test_guard.py with rikurinode ...")
    SecurityCore/crates: ai-exec aisec-mcp intent-hook privacy-router security-core security-core-ffi security-linux
    security-core/src: 28 modules + lib.rs (agent_policy, command_policy, intent_verifier, key_filter, prompt_injection,
      sensitive_data, model_verifier, model_vetting, package_vulns, threat_feeds, vault, wasm_sandbox, ...)
    security-core/Cargo.toml: features default=["wasm-plugins"]; wasmtime optional; deps regex serde serde_json once_cell toml
      sha2 pbkdf2 hmac chrono aes-gcm rand rustls webpki-roots reqwest(rustls-tls, blocking) rusqlite(bundled) url
    docs/AISECIMPLEMENTATION.md: "✅ Done" x395, "⬜ Not started" x45; its Linux rows disagree: l.233 PAM/polkit
      "Not started" vs l.343 PAM auth "Done 2026-03-31"; l.302 notification channels "Not started" vs l.357-361
      Telegram/Discord/Email "Done"; l.368 notification end-to-end test "Not started" (the verifier's finding)
    .github/workflows: ci.yml claude-guard.yml supply-chain-weekly.yml (cron '0 8 * * 2', cargo deny advisories bans sources)
    tests: crates/security-core/tests/cross_validation.rs, tests/integration/test_cases.json
  Rikuri-PI docs/security/THREAT_MODEL.md (status "adopted design requirements, September 28, 2026; runtime protection Not yet
    proven"; §4 "AISecurity evaluates and translates ... detectors only contribute signals");
    docs/architecture/adr/0004-foundation-threat-model-assumptions.md (Proposed, 2026-10-05)
  previous repository 3bbbe392: vendor/security-core/PROVENANCE.md (vendored 2026-06-09 from 1163dadf; wasm-plugins and
    wasmtime removed by hand; "This is a fork: improvements ... do not flow here automatically")
  this repository: ci.yml triggers pull_request and push, both to main, plus workflow_dispatch; image.yml and
    claude-guard.yml path-filtered on pull_request and push; no schedule anywhere;
    no .github/dependabot.yml or renovate config; control-plane/deny.toml [advisories] yanked=deny unmaintained=all
    unsound=all ignore=[]; BUILD-PROCEDURE "Periodic Loops": weekly smoke/fallback scan, monthly drills, quarterly
    security pass and dependency/image audit; platform-plan §8 table had 3 columns (Stage | Delivers | Its drill)
  owner's notes: /home/junc/Security Briefing/Oct 10, 2026.md, Oct 11, 2026.md, Oct 12, 2026.md
Checks:
  python3 -I <scratchpad>/linkcheck.py over the 6 changed files -> checked 33 relative links in 6 files; 0 broken
  git diff --check -> clean
  python3 scripts/quality/repo_hygiene.py . -> exit 0
  python3 -I .claude/hooks/test_guard.py -> exit 0 (run outside safe-run.sh: a nit the verifier raised);
  scripts/quality/safe-run.sh python3 -m unittest discover -s .claude/hooks -p 'test_*.py' -> exit 0, "Ran 91 tests ... OK";
    safe-run: "no live node containers found here; the start-time check had nothing to compare"
  verifier (one pass): PASS; its own reruns: links 33/0, diff --check 0, hygiene 0, wiring 0, policy 0, guard tests 91 OK,
    quality tests "Ran 80 tests ... OK (skipped=1)", both inside safe-run.sh; docker inspect before/after: permission denied
    (sandbox), compared nothing
  after the nit fixes: linkcheck 33/0; git diff --check clean; repo_hygiene exit 0
  python3 scripts/quality/check_guard_wiring.py -> exit 0; python3 scripts/quality/guard_policy.py --check -> exit 0
  table shapes: 11 stage-table lines (header + 10 rows) at 5 pipes; D17 row 5 pipes;
    THREAT_MODEL.md tables uniform: §2 13 lines x 4 pipes, §4 21 x 7, §5 12 x 6, §6 8 x 4
  git diff --stat (tracked): AGENTS.md +2/-1, assistant-plan.md +4/-2, platform-plan.md +26/-20 (table rows rewritten
    with the 4th column); untracked new: docs/security/THREAT_MODEL.md, docs/adr/0009-security-built-in.md, this record
```
