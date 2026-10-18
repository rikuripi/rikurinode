# Build Record — The assistant: engine decision and the three contracts

| | |
|---|---|
| **Date** | 2026-10-18 |
| **Author / session** | Claude Code (Fable 5.1) for Henry Chen, in the owner's desktop session |
| **Branch** | `docs/assistant-plan-2026-10-18`, this checkout, from `main` `283dcb5` (PR #12 merged). The sandbox refuses writes to `.git/config` (a device sits at `.git/config.lock`), so the branch carries no upstream entry; a push names the remote and branch explicitly. |
| **Commits** | `8e7fee1`, the change (the pre-commit hook ran: gitleaks "no leaks found"); the next commit, this row and the push |
| **Status** | DONE; committed and pushed on the owner's word ("Commit and push", 2026-10-18); CI on the pull request Not yet proven |
| **Change type** | ops (architecture decision, plan and contracts; documentation only) |

## Task Contract

1. **Outcome:** the owner's five decisions of 2026-10-18 about the assistant become recorded decisions, with an ADR for the inference engine and a plan holding the three contracts stages 7 and 8 build against (action templates, the AI event schema, the evaluation gate), so the next assistant task starts from them and not from the previous repository.
2. **Scope:** this record; `docs/adr/0008-inference-engine.md` (new); `docs/architecture/assistant-plan.md` (new); `docs/architecture/platform-plan.md` (the stage 8 row, the paragraph after the stage table, a §7 row D16, the status line's count); `docs/requirements/lessons-register.md` (AI-02: a dated caveat for decision F3). Tier: **routine** (documentation and process text; [BUILD-PROCEDURE.md, "Risk tiers"](../../.agents/workflows/BUILD-PROCEDURE.md#risk-tiers)), with a risk note: F3 relaxes AI-02's "private node data never goes to cloud models" by an owner-enabled, off-by-default option, recorded as a dated clarification; the code that implements it is high-risk when it comes. **Not included:** code, CI, the guard, `AGENTS.md`, the OS image, any port of the previous repository's code, the fork repositories (`Lean_llama.cpp`, `LeanKV`, `LeanInfer`), stage 7 or 8 work.
3. **Done when:** the five decisions are in the assistant plan with the owner's words and date and summarised in the platform plan's §7; ADR 0008 states the engine decision with its sources; each contract is specific enough that a stage 7 or 8 Build Record can cite it as a "Done when" item; every fact about the previous repository names the file or record it comes from, and every outside fact carries a source read 2026-10-18; every relative link and anchor in the changed files resolves; `git diff --check` is clean; `repo_hygiene.py` exits 0.
4. **Authority:** edit the files in Scope on the task branch; read the previous checkout and the fork by absolute path, read-only; web reads for sources. No commit, push or PR until the owner says so (the owner's standing rule). No code, no agents beyond this session, no verifier (documentation only: the `AGENTS.md` §5 checks and the owner's pull-request review).
5. **Limits:** one task; two repair cycles; no review rounds beyond the owner's. Budget: none configured; consumption reported at close-out.

## 0. Intent

- [x] **Problem, in the owner's words** (2026-10-18): "We need further review with our AI scaffolding before porting from the old /rikuri/rikurinode." On the fork: "It may be easier to just use ik_llama.cpp (for cpu focus only) or llama.cpp since keeping up with them might be a little difficult and our KV experiment may not surpass that they each would quickly enhance in the future." On the harness: "I am not sure our short and long term memory and recursive learning capability are working or not. With a small LLM, I'm not sure if it knows how to analyze or see/recall prior patterns of the node and learn from them. That whole scaffolding has never been tested, rigorously. So what's the best future proof build should be? Small LLM hallucinates too much." On knowledge: "We'll need to write and update our RAG and Runbook for this new node as we go. Like a live operational manual. … For every new upgrade, the RAG needs to update to new functions or changes as will. The Runbook's auto healing scripts also need regular refresh so that the commands applied actually work. … The Guardian seems to not able to do so based on the log we have." On telemetry: "What I wanted was all the AI related telemetry, data, logs are in once place; where we can monitor the AI performance." On agency: "'Need to open a channel, help me do that.' And the AI can ask a few clarifying questions … AI provide the search, and input, then human approves. … With Rust doing the heavy lifting while AI agent just calling up the templates for each (see intelligent but it's just deterministic programming). Ultimately, we can talk to it via mic/phone etc. … Need a realistic plan for this."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** the platform plan's stage 8 (and what stage 7 must expose for it); the lessons register's AI-02; nothing running.
- [x] **Open questions:** the five choices put to the owner in the review were answered the same day: "1. use llama.cpp 2. B. port reflection once a labeled eval exits. 3. Owner enabled cloud: option for reflection and eval 4. One model if possible. 5. First phone side; then whisper.cpp if enough RAM."
- [x] **Owner approved the intent:** the review ended "Next: one Build Record for the engine ADR and the three contracts, started only after you answer"; the owner answered with the five picks (2026-10-18).

## 0b. Spec

- [x] **Requirements:** record each decision with the owner's words and date; a decided default is explicit, costed and reversible (each decision names its alternatives and their cost); a fact about the previous repository is stated as what its source or records show, never as proven behaviour; a fact about outside software carries a source read today; a rule relaxed by a decision (AI-02) keeps its history by a dated clarification, not a rewrite (`AGENTS.md` §8, "Conflicts"); the contracts bind nothing until a stage's Build Record cites them.
- [x] **Design:** one ADR for the engine, because it is settled whatever stage 8 later measures (the engine is a pinned container behind an HTTP boundary; the model is a separate, checksummed artefact chosen in stage 8). One plan document for the rest, in the shape of the agent payments plan: evidence from the previous repository, the decisions, the three contracts, the sequence by stage, sources. The platform plan only points at it. Rejected: putting the contracts into the platform plan (it is the owner's decision document, and the agent payments plan set the pattern of a separate plan per area); an ADR per decision (F2 to F5 are plan-level choices that stage 8's measurements may revisit; an ADR each would be five documents about things not yet built); editing `AGENTS.md`'s security baseline for F3 (high-risk tier for a pointer; the baseline's "outbound network is denied by default, with an explicit allow-list" already describes how F3 must be built).
- [x] **Policy applied:** the first principle in every decision row; the design rules in the contracts (nothing fails silently: every model call is an event; runtime truth: the eval score shown is the one measured on the release; pinning: engine by digest, model by checksum); the security baseline (the assistant plans and never holds authority; stop when blocked; keys and payments stay in deterministic code; payments above a cap need the owner).
- [x] **Flagged concerns:** F3 conflicts with AI-02's "private node data never goes to cloud models". Resolution, the smallest: the rule keeps its default (off) and gains an owner-enabled exception limited to reflection and evaluation, with the data that leaves redacted, bounded and recorded as an AI event the owner can see; recorded as a dated caveat under AI-02 and as F3 in the plan. Said to the owner in the review and in this record.

## 1. Plan

- [x] **One sentence:** write ADR 0008 and the assistant plan, point the platform plan and AI-02 at them.
- [x] **Blast radius:** documents only; nothing irreversible; Git history keeps the old texts.
- [x] **Current behaviour characterized:** the previous repository read by absolute path at its HEAD `3bbbe392` on 2026-10-18 (its `docs/architecture/AI-SYSTEM-COMPLETE.md`, `ai-orchestration-vision.md`; `docs/plans/2026-06-22-pi-memory-architecture-execution.md`, `RUNBOOK-COVERAGE.md`; `docs/specs/ROUTER-MODEL-BENCHMARK-2026-04-19.md`; `docs/node-deeptier-bakeoff-2026-07.md`; `docs/rag/ai_intelligence_hub.md`; `config/model-registry.json`, `config/llama*.env`; `dashboard/backend/src/ai/{intentRouter,structuredOrchestrator,jsonControlLoop,queryClassifier}.ts`, `context/memory/{store,reflection,weightUpdate,operationalPatterns,learnedParams}.ts`, `context/ontology/{clarification,commandMap}.ts`, `context/autonomy/runbookIndexer.ts`, `core/runbookEngine.ts`, `guardian/{llmRouter,memory}.ts`, `routes/aiAgent.ts`; `control-plane/src/tools/dispatcher.rs`, `ln_manager/{guardrails,executor}.rs`; `ragdocs/runbooks/RB-TOR-RESTART-01.json`; `scripts/eval-fixtures/*.jsonl`; `shared/orchestrator/src/classifier.ts`); the fork `/home/junc/Lean_llama.cpp` at `1b37afab` (its `README.md`, `docs/leankv-EXECUTIVE-SUMMARY-2026-07.md`, `docs/RESULTS.md`, remotes and log); the lessons register's AI-01 to AI-10, HEAL-02 to HEAL-07, gap G5, PLAT-04; the platform plan §8. Findings in the Evidence log.
- [x] **Files and order:** this record → ADR 0008 → the assistant plan → the platform plan's pointers → AI-02's caveat → checks.
- [x] **Riskiest step:** stating as fact something the previous repository only planned. Guard: every claim about it names its file or record, and "never run live" is said where the records show it.
- [x] **I will know this works when** the "Done when" line holds and a stage 7 or 8 Build Record could copy a contract item into its own "Done when".

## 2. Build

- [x] `docs/adr/0008-inference-engine.md` (new): context (the fork's state and its own conclusion, the previous node's registry, bench and bake-off, the node's workload, upstream's status, the official images); decision (the official `server` image by digest in the release set, the model as a checksummed artefact, the HTTP interface as the only dependency, the fork repositories retired to research, the gate and the smoke on load); consequences; rejected (keep the fork, ik_llama.cpp as the measured fallback, a community fork, Fedora's package); sources read today.
- [x] `docs/architecture/assistant-plan.md` (new): status and one page; §1 what the previous repository shows, each fact with its file or record (engine and models, harness, memory and learning, runbooks and retrieval, telemetry, action flows); §2 the five decisions with the owner's words, alternatives and costs; §3 the build (engine and model, the two-job harness, memory, runbooks as code, knowledge layer, one event store, action templates, voice, the hardware budget); §4 contracts A (action templates, A1 to A6), B (the AI event store, B1 to B8), C (the evaluation gate, C1 to C6); §5 the sequence by stage; §6 open items; §7 sources.
- [x] `docs/architecture/platform-plan.md`: status line (D16 added; sixteen decisions, fourteen taken; facts checked 2026-10-18); §7 row D16; §8 stage 8's deliverables and drill; a paragraph after the stage table pointing at the assistant plan.
- [x] `docs/requirements/lessons-register.md`: AI-02 gains a dated "Superseded / caveat" line for F3 (default unchanged; the owner-enabled exception for reflection and evaluation; redacted, bounded, recorded before the send; the implementing code high-risk).
- [x] **Clean as you go:** no replaced text anywhere; AI-02's rule stands with a dated caveat, not a rewrite.
- [x] **Security question:** no code. F3 touches private data as a policy; its caveat and contract B5 say what leaves (redacted summaries and incident records), when (only while the owner has the option on, for reflection or evaluation), and how it is recorded (a `data_egress` event written before the send by the one function that can send).

## 3. Debug

N/A: no defect fixed.

## 4. Verify

- [x] Links and anchors in the changed files resolve: 28 relative links in the five changed files, 0 broken in this change. The checker flagged one anchor in the lessons register's own contents table, `#5-gaps--where-the-old-repository-has-no-evidence`; the heading exists (line 1280) and the double hyphen is GitHub's slug of " — ", which the scratchpad checker collapses — a false positive, not this change's link (Evidence log).
- [x] `git diff --check` clean; `python3 scripts/quality/repo_hygiene.py .` exit 0 (it scans tracked files; the three new files are unstaged and hold no secret, log or state).
- [x] Independent verification: N/A, documentation only (routine tier: the `AGENTS.md` §5 checks and the owner's pull-request review).
- [x] Diff matches the §1 plan: the five files in Scope, nothing else. Deviation: none. The owner's decision wording is quoted verbatim in §0 and §2 of the plan.
- [x] Table shape: the D16 row and the stage 8 row have the same column count as their headers (Evidence log).

## 5. Close Out

- [x] Full gate: not run — documentation only; `AGENTS.md` §5 names the checks for it, all run above. CI runs the full gate on the pull request.
- [x] Scrap sweep: the link checker and the edit script live in the session's scratchpad, not the repository; nothing was created in the tree beyond the three new files and the two edits. Untracked files in the checkout root that are not this task's (`.codex/`) were left as found. The device placeholders `git status` shows inside the sandbox (`.bash_profile`, `.idea`, `.claude/skills` …) are the sandbox's masks, not files.
- [x] Reviewed per `REVIEW.md`, its three passes (Bugs; Security & funds; Compliance) by the author on a full re-read of the two new documents: Bugs — three nits fixed in place (HEAL-07's "seven other approval stores" was quoted as "seven"; a sentence blamed PLAT-03 for retiring the TypeScript backend where D3 and D15 do; the TurboQuant status sentence now says the two status pages disagree); Security & funds — F3's caveat and B5 state default, scope, redaction and recording, and name the implementing code high-risk; no funds path, key or authority is created by a document; Compliance — the diff is the Task Contract's Scope and nothing else, every decision is exposed with its alternatives and costs, and every claim about the previous repository names its file or record, and §1 says "never measured", "not checkable" and "unwired" where the records show it. No Important finding.
- [x] Lesson loop: N/A.
- [x] Knowledge layer: the plan and the ADR are the knowledge for this change; no help page exists yet.
- [x] Commit message explains WHY; record committed with the change: `8e7fee1` on the owner's word ("Commit and push", 2026-10-18).

## Skipped items — visible, never silent

- §5 "Full gate": documentation-only change; the §5 checks of `AGENTS.md` replace it locally and CI runs the gate on the pull request.

## Evidence log

```
Evidence read 2026-10-18 (read-only, absolute paths):
  previous repository HEAD: 3bbbe392 (2026-10-10 20:11 -0700)
  fork /home/junc/Lean_llama.cpp HEAD 1b37afab (2026-07-21); last upstream-side
    commit c904d6eb "Claude (rebase session)" 2026-07-17; rev-list c904d6eb..HEAD -> 22;
    diff --stat c904d6eb HEAD -> 89 files changed, 13779 insertions(+), 482 deletions(-);
    remotes: aulora, origin (both Lean_llama.cpp; no ik_llama.cpp remote);
    last fetch 2026-07-17
  git grep memory_insight -- control-plane -> no match (reflection's Gate 2 never done)
  git ls-files ragdocs/runbooks | wc -l -> 86
  eval fixtures: intent-classifier.jsonl 44 lines (3 comment lines); runbook-symptoms.jsonl 14 lines
  monthly commits touching ai/, context/, guardian/, shared/orchestrator: peak 44 (2026-05), 40 (2026-07), 6 (2026-10)
  no N150 tok/s figure anywhere under docs/ (grep tok/s|tokens/s with N150|N100|alder -> none)
Web (read 2026-10-18):
  arXiv 2610.11245 ReadKV (submitted 2026-10-08): progressive codes + query-dependent reads; no code named
  arXiv 2610.18642 MultiAlloc (submitted 2026-10-13): profiling-guided precision allocation; code github.com/RL-MIND/MultiAlloc
  llama.cpp docs/docker.md: ghcr.io/ggml-org/llama.cpp full|light|server, CPU for linux/amd64 + linux/arm64
  llama.cpp releases/latest: v0.7.0, 2026-10-15
  TurboQuant status pages: PR to mainline closed unmerged as of July 2026 (newer page); an April page had it open
  whisper.cpp models/README.md: tiny 75 MiB, base 142 MiB, small 466 MiB, medium 1.5 GiB
Checks:
  python3 -I <scratchpad>/linkcheck.py over the 5 changed files
    -> checked 28 relative links in 5 files; 1 flagged (false positive, see §4)
  python3 -I <scratchpad>/linkcheck.py over the 3 new files -> checked 4 relative links; 0 broken
  git diff --check -> clean (run twice, after the wording fixes too)
  python3 scripts/quality/repo_hygiene.py . -> exit 0
  table columns: "| D16" row 5 pipes = header 5; "| 8 Frontend" row 4 pipes = header 4
  git diff --stat (tracked files): platform-plan.md 25 lines (+18/-7), lessons-register.md +1;
    untracked new: docs/adr/0008-inference-engine.md, docs/architecture/assistant-plan.md,
    docs/build-records/2026-10-18-assistant-plan.md
Sandbox note:
  git checkout -b <branch> origin/main failed at the tracking step:
    "could not lock config file .git/config: File exists" (a device sits at .git/config.lock);
    the branch ref had been created; checked out with --no-track; no upstream recorded.
```
