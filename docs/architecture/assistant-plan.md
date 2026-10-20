# Assistant plan

**Status: a plan, written 2026-10-18 from a review of the previous
repository's AI scaffolding. Its five owner decisions (F1 to F5, §2) were
taken the same day; nothing in it exists yet.** It governs stage 8 of the
[platform plan](platform-plan.md#8-stages) and names what stage 7 must expose
for it (the action templates, §4 A). It changes nothing in stages 1 to 6.
What the previous repository's code does is stated as what its source and
records show, never as proven behaviour (§1); facts about outside software
carry the date they were read (§7). Where this plan and the
[lessons register](../requirements/lessons-register.md) name the same
requirement, the register's AI and HEAL rules are the tests.

## In one page

- **The model has two jobs.** It turns an utterance into a typed intent and
  fills the fields it can, under a grammar; and it explains or answers from
  retrieved text, with citations. It never selects a command, computes an
  amount, picks a peer or judges the node's state unaided. Everything else
  is deterministic Rust in the control plane: the state machine, the
  templates, the runbooks, the memory.
- **The engine is llama.cpp's own server image, pinned by digest** in the
  release set (F1, [ADR 0008](../adr/0008-inference-engine.md)). The model is
  a checksummed file chosen in stage 8 from a measurement on the N150; one
  model if it passes the gate (F4).
- **Memory is the control plane's records,** queried deterministically.
  Version one has no loop that changes behaviour; reflection is ported only
  once a labelled evaluation exists to judge it (F2).
- **Runbooks are typed Rust actions,** checked by the compiler and the tests
  against the real units and proven on the test stack before a release
  ships. The Guardian supplies evidence; the Build Procedure changes
  runbooks.
- **One event store, one page.** Every model call, proposal, approval, run
  and outcome is one typed event in the control plane's store; the AI page
  and the status API read it; nothing is copied.
- **Agent flows are action templates:** open a channel, send a payment,
  filled by the template's own questions and Rust's recommendations,
  approved by the owner's tap behind step-up, executed and verified by the
  control plane. The assistant is a front door to the same path the UI uses.
- **Cloud is an owner-enabled exception** for reflection and evaluation
  only, off by default, redacted and recorded (F3). Chat and actions stay
  local. Amended 2026-10-20 (decided, ADR 0012): three lanes by data
  class, including a weekly performance review on a typed, sanitized
  report card.
- **Voice is the phone's job first** (F5); whisper.cpp on the node later, if
  the memory budget allows. Approval is never by voice.

## 1. What the previous repository shows (read 2026-10-18)

Read by absolute path at its HEAD `3bbbe392`. The fork was read at
`/home/junc/Lean_llama.cpp`, HEAD `1b37afab`. Nothing below was run.

### 1.1 The engine and the models

- The node served its models with Lean_llama.cpp, a fork of ik_llama.cpp
  carrying the TurboQuant KV-cache types TQ2, TQ3 and TQ4. Its upstream
  snapshot is from 2026-07-17; its own work since is 22 commits, about
  13,800 added lines in 89 files; no ik_llama.cpp remote is configured. Its
  executive summary (`docs/leankv-EXECUTIVE-SUMMARY-2026-07.md`) recommends
  TQ4 and concludes: "KV quantization is no longer the binding constraint on
  edge inference. Weight quantization is the next lever."
- `config/model-registry.json` (version 1.1, notes to 2026-07-21): hosts
  with 16 GB or more ran Gemma-4-E2B-it-Q4_K_M (2,960 MB of weights,
  context 8,192, KV cache q8_0; "E2B does NOT use TQ") inside a 6 GB or 8 GB
  service cap; hosts with 7 to 16 GB ran Qwen2.5-1.5B (1,100 MB) with deep
  reasoning routed to Groq's cloud; under 7 GB, cloud only. Beside the tier
  model every local install ran a router model, Qwen3.5-2B (1,221 MB), and
  an embedding model, bge-base-en-v1.5 (209 MB).
- `docs/node-deeptier-bakeoff-2026-07.md`: on a Ryzen 7 7735U with 8
  threads, E2B generated about 23 to 24 tokens a second against Gemma-3-4B's
  14; on 18 policy cases E2B answered 17 to Gemma-3's 14 and did not invent
  an `lncli` command where Gemma-3 did. The same document found the fork's
  flash-attention setting architecture-dependent: the wrong setting garbles
  output ("deployment-critical").
- `docs/specs/ROUTER-MODEL-BENCHMARK-2026-04-19.md`: a 24-case multilingual
  intent suite; the best models reached 96 % with two misses the document
  calls irreducible; "KV quant doesn't help (it's a memory/precision lever,
  not a speed lever)"; Gemma-4-E4B did not run because the fork's build did
  not know the architecture.
- No measurement of any model on an Intel N150 exists in the repository.

### 1.2 The harness

- `dashboard/backend/src/ai/` holds 45 files, `guardian/` 38, `context/` 31
  (13 of them `context/memory/`). The user path is deterministic first: a
  query normaliser; a seven-layer intent router with no model call
  (`ai/intentRouter.ts`); a pass-1 classifier that constrains a 2B model to
  a JSON schema (`shared/orchestrator/src/classifier.ts`); a structured
  orchestrator whose header says "The LLM is NO LONGER in the control path"
  (`ai/structuredOrchestrator.ts`); a JSON control loop that treats the
  model as a "template filler" (`ai/jsonControlLoop.ts`); fixed
  clarification templates ("The LLM does not improvise clarifications",
  `context/ontology/clarification.ts`); a command registry ("LLMs must NEVER
  invent commands", `context/ontology/commandMap.ts`). This is the design §3
  keeps; the code is the TypeScript backend that D3 and D15 leave behind.
- Evaluation assets: `scripts/eval-fixtures/intent-classifier.jsonl` (about
  40 cases in en, zh-CN, zh-TW and ja), `runbook-symptoms.jsonl` (14 cases),
  the 24-case router bench, the 11-prompt bake-off, and the 242-question
  retrieval set with every third question held out that AI-07 records.
  Enough to show the approach works; not enough to gate a release.

### 1.3 Memory and learning

- `docs/plans/2026-06-22-pi-memory-architecture-execution.md`: compaction, a
  warm tier of session summaries and a weekly reflection were built on
  2026-06-23 and pass `npm run test:pi-memory` 20/20 with the model call
  injected, so the model's own reasoning was never measured. Two gates stood
  before "live value": embeddings (done 2026-06-23) and adding
  `memory_insight` to the control plane's proposals allow-list. No such entry
  exists under `control-plane/` at HEAD, so live proposals were rejected;
  `context/memory/reflection.ts` says they are "persisted locally" regardless.
  Nothing in the repository shows a reflection proposal reaching review.
- Reflection's default model is the `frontier` tier — Groq's cloud — or a 27B
  local swap (`guardian/llmRouter.ts`, `reflection.ts`). The retrieval-weight
  update calls its signal a proxy: real attribution "belongs to a later
  pass" (`context/memory/weightUpdate.ts`). `context/memory/learnedParams.ts`
  keeps versioned, rollback-able parameters that the loops dual-write.
- The lessons register records the learning loops' own incidents: the
  diagnosis engine's design "produced several incidents" (HEAL-03); a rule
  field the engine never read matched vacuously and restarted the dashboard
  156 times in one day (HEAL-04).
- Whether a reflection ever ran on the live node cannot be checked from this
  project: the previous node's data folder is off limits.

### 1.4 Runbooks and retrieval

- 86 runbooks under `ragdocs/runbooks/`, JSON whose steps are shell strings.
  `RB-TOR-RESTART-01.json`: precheck `docker ps -a --filter name=tor`, action
  `docker restart tor`, validation by grepping the container's log.
  `core/runbookEngine.ts` matches runbooks by `issue_types` with no model;
  `context/autonomy/runbookIndexer.ts` indexes them into ChromaDB for
  retrieval.
- `docs/plans/RUNBOOK-COVERAGE.md` (2026-04-23, "PLAN — not yet
  implemented"): 7 of 14 runbooks executable, 4 naming a container that no
  longer existed; its target, "AI suggests → Rust verifies → Rust
  executes", is §3.4 here. HEAL-04: 14 of 89 runbooks broken in the August
  audit.
- No code updates a runbook from an incident. The only path from an outcome
  to a runbook was a reflection proposal of kind `runbook_refinement`
  (`reflection.ts`), and that path was unwired (§1.3). Incidents and their
  outcomes were recorded (HEAL-06).

### 1.5 Telemetry

- AI state was shown on the assistant page, AI Operations, AI Benchmarks,
  the Guardian page and an eight-tab AI Intelligence hub
  (`docs/rag/ai_intelligence_hub.md`) whose "unified outcome ledger" is, in
  its own words, "an additional, unified copy" beside each loop's own store.

### 1.6 Action flows

- The control plane had a tool dispatcher with a fixed registry, a
  permission per tool and a trace row per call
  (`control-plane/src/tools/dispatcher.rs`); Lightning guardrails with
  owner-settable budgets and immutable safety limits ("those are safety
  limits, not budgets, and nothing in the product should be able to loosen
  them over an API", `ln_manager/guardrails.rs`); an executor that acts
  through the LND client and verifies (`ln_manager/executor.rs`). The chat
  side kept pending proposals in memory ("in production, use database",
  `routes/aiAgent.ts`). HEAL-07 records approvals answering 403 for months
  and seven other approval stores.
- No voice input exists in the repository.

## 2. Decisions (owner, 2026-10-18)

| | Choice | Options and their costs | Decided |
|---|---|---|---|
| F1 | Inference engine | **A. llama.cpp's official `server` image**, CPU build, pinned by digest in the release set: upstream releases, both architectures, the same pin path as every container; cost: no TQ4 cache compression, no ik_llama.cpp CPU kernels. **B. ik_llama.cpp** built in CI from a pinned commit: faster CPU kernels; cost: one maintainer, no release images to pin, a build pipeline of our own. **C. Keep Lean_llama.cpp:** cost: a rebase every few weeks on a moving upstream, model-architecture lag, the flash-attention trap, funds safety resting on a part-time fork. | **A** ("1. use llama.cpp"; ADR 0008). B is the measured fallback if A misses stage 8's speed budget on the N150. |
| F2 | Learning loops in version one | **A. None:** deterministic reports; the model words them. **B. Port reflection once a labelled evaluation exists** (§4 C6); cost: the set must be built first. **C. Port as-is:** cost: unmeasured, needed a cloud tier, never reached review. | **B** ("port reflection once a labeled eval exits"). Until the set exists, A is what runs. |
| F3 | Cloud model tier | **A. None** (AI-02 as written). **B. Owner-enabled, off by default, for reflection and evaluation only;** cost: compacted summaries and incident records leave the node while it is on, redacted, each send recorded. **C. Cloud for chat** as the previous node did; cost: node data leaves on every question. | **B** ("Owner enabled cloud: option for reflection and eval"). AI-02 carries a dated caveat. **Amendment, 2026-10-20** (decided by the owner, "accept all five."; ADR 0012; the text of 2026-10-18 stands, amended by this): three lanes by data class. *Local* for chat, actions and anything touching node data; an owner-run machine on the owner's own network may serve it, recorded as such. *External public*, built from a template with no private fields. *External review*, which carries only a typed, sanitized weekly report card for a review of fees, rebalancing and profitability. Each is opt-in and off by default; every send goes through the AI relay in the lobby zone (platform plan D18) and is recorded first (B5); external answers are typed suggestions that Rust bounds-checks and the owner approves; none moves funds. |
| F4 | Models on the node | **A. One model** with a grammar for both jobs; cost: if it classifies below the gate's floor, the fallback is B. **B. A second router model** as before: 1.2 GB more memory, one more artefact to pin and evaluate. | **A** ("One model if possible"), measured in stage 8. |
| F5 | Voice input | **A. Phone-side speech-to-text,** text to the node; cost: on Android the recogniser may send audio to Google's servers. **B. whisper.cpp on the node:** cost: 75 MiB to 466 MiB of model and CPU time beside the LLM. **C. None.** | **A first, then B if enough RAM** ("First phone side; then whisper.cpp if enough RAM"). Approval is never by voice (§3.8). |

## 3. The build

### 3.1 Engine and model

ADR 0008: the official `server` image by digest, the model by SHA-256,
the HTTP interface as the only dependency. The first model to measure is
Gemma-4-E2B at Q4_K_M, the previous node's bake-off winner (§1.1), with a
JSON grammar for classification. The stage 8 drill measures, on the N150:
tokens a second at the production thread count; p95 latency of a
classification and of a 200-token answer; resident memory at the production
context. The gate (§4 C) decides whether one model serves both jobs (F4).

### 3.2 Harness: two jobs

The control plane holds a state machine with a fixed menu. Each turn runs:
normalise → deterministic intent match → model classification under a
grammar only when the deterministic layer is unsure → either a template
(§3.7), a read-only answer from the status API, or an explanation from
retrieved text. Every answer about the node states source and time and says
"unknown" where a figure is missing (AI-04, EVID-01). The model's output is
data: it is parsed against the schema, and anything that does not parse is
a clarifying question, never an action. No LangChain, LangGraph or generic
agent loop: the plan's single door excludes them by design.

### 3.3 Memory

Memory is the control plane's store: incidents (HEAL-06), runbook outcomes
(HEAL-02), approvals (HEAL-07), events (§4 B), later the ledger. Pattern
questions are queries, not recall: "this unit restarted three times this
week" is computed and shown to the model as a sentence. A weekly
deterministic report lists incidents without a runbook, runbooks with
failing outcomes, runbooks that never fired, and the AI page's rates; the
model may word it. Reflection — a model reasoning over summaries and
proposing changes — waits for the labelled evaluation of §4 C6 (F2), and
when ported it proposes into a backlog that a person reviews; it never
changes policy itself (the previous plan's own invariant).

### 3.4 Runbooks as code

A runbook is a Rust value: the issue types it answers, a precheck probe, an
action from the control plane's action enum (restart a unit, clear a port,
re-request an onion address …), a validate probe, an undo, an attempt budget
and a cooldown. Because they are code, `cargo test` and clippy check every
runbook against the real unit and container names in the image, the
templater cannot leave a placeholder unresolved, and a unit that disappears
breaks the build instead of the node (HEAL-04). The release gate runs every
runbook against its induced fault on the test stack before a set ships
(HEAL-02's honest executor; UPG-03's drills). Writing or changing a runbook
is a Build Procedure task with tests. The Guardian's part is evidence: the
incident, the outcome, the weekly report's gaps.

### 3.5 Knowledge layer

Help pages, runbook descriptions and the retrieval corpus change in the same
change as the behaviour they describe (AGENTS.md > Knowledge layer). The
retrieval index is built in CI from the release's own documents, stamped
with the commit, and shipped inside the set; the node never indexes
working-tree text (AI-10). Knowledge is written in short sections under
question-shaped headings within the embedder's window (AI-08); every command
or control it names resolves to something in the release (AI-09); items
reach the prompt whole and the prompt records which did (AI-06); retrieval
quality is measured on the labelled set with the release's model (AI-07).

### 3.6 One event store, one page

Contract B. One append-only event table in the control plane's store; one
AI page that reads it; the assistant as one component in the status API with
the same health judge as any service. No aggregator, no second copy.

### 3.7 Action templates

Contract A. The template does the work: fields, validation, recommendation,
guardrails, card, approval, execution, verification. The model maps the
utterance to a template and extracts the fields it can; the template asks
its own questions for the rest, in a fixed order and fixed words; Rust
proposes the options; the owner picks; the card is approved by a tap behind
step-up; the control plane executes exactly what was approved and verifies.
The UI drives the same templates without the assistant, so the assistant is
a front door, never a second path.

### 3.8 Voice

F5. Speech-to-text runs on the phone — the browser's speech recognition or
the phone's dictation — and the node receives text over the same
authenticated channel as typed chat; the phone's text-to-speech reads the
card back. Privacy note for the help page: on Android, Chrome's recogniser
may send audio to Google's servers; on-device dictation does not. Later, if
PLAT-04's budget allows after the LLM is measured, whisper.cpp on the node
with a small English model (tiny 75 MiB, base 142 MiB, small 466 MiB) for
short commands, accepting a few seconds' delay. **Approval is never by
voice:** a spoken yes can be replayed or spoofed; approval is a tap behind
step-up, and the emergency stop needs no password (AI-03, HEAL-07).

### 3.9 Hardware budget

The N150 has four efficiency cores and 12 GB of memory budgeted per service
(PLAT-04); the model's weights are the assistant's dominant line.

| Item | Budget to measure against |
|---|---|
| Gemma-4-E2B weights, Q4_K_M | about 3.0 GB |
| KV cache at 8k context, q8_0 | under 0.5 GB |
| Engine container, total | at most 4 GB resident, to be confirmed by stage 8 against bitcoind's and LND's budgets |
| A second router model (F4's fallback) | 1.2 GB more |
| whisper.cpp small model (F5, later) | 0.5 GB more, plus CPU while listening |
| Generation speed, E2B, Ryzen 7 7735U, 8 threads | about 23.5 tokens a second (the previous node) |
| Generation speed on the N150 | never measured; the stage 8 drill measures it first |

What a 2B model offers is reliability for a fixed menu, not flawlessness:
the templates do the work and the card catches a misroute. At the old
bench's 96 %, about one utterance in 25 earns a clarifying question or a
card the owner rejects — an annoyance rate, not a funds risk.

## 4. Contracts

A stage's Build Record cites these by number in its "Done when". They bind
nothing until then.

### A. Action templates (stage 7 exposes, stage 8 drives)

- **A1. A closed set.** The templates are one Rust enum; each template is a
  struct with a closed set of fields. Version one: open channel, send over
  Lightning, send on-chain. Later: close channel, rebalance, set fees,
  create invoice. A `match` over the enum has no catch-all arm.
- **A2. Each template declares** its required fields with validation ranges;
  a deterministic recommendation function from the node's state (capacity
  options from spendable balance minus reserve; peer candidates from the
  stage 7 node search with their scores; a fee from the estimator under a
  ceiling); the guardrails it is checked against (budgets, reserve floor,
  the caps as settings, stage 9's mandates for agents); the confirmation
  card's text in plain words (what, to whom, how much, the fee, whether it
  can be undone, what happens next); the approval it needs (the owner's
  step-up for every funds move); the execution steps and the verification
  that follows (for a channel: the funding transaction seen and the channel
  pending); the events it emits (§4 B).
- **A3. Filling.** An instance is built in the control plane from the
  assistant's extraction, then the template's own clarifying questions in a
  fixed order for every missing or invalid field, in the template's words,
  then the owner's picks among the recommended options. The model never
  writes a value the owner did not say or pick, never computes an amount,
  never selects a peer. Approval text never calls a funds action "safe" or
  "low risk" (HEAL-07).
- **A4. What is approved is what runs.** The approval carries the instance's
  hash; the control plane executes that instance byte for byte; any change
  restarts approval; approval expires; one approval store (HEAL-07).
  Approval is never by voice.
- **A5. One typed contract.** The template schemas are exported to the
  frontend's typed API contract (D15) so the UI renders the questions and
  the card without the assistant; the assistant is an optional front door to
  the same endpoint.
- **A6. Tests.** Table tests for validation, recommendation and card text per
  template; a refusal test per guardrail; an end-to-end run of each template
  on regtest in stage 7's drill, and of one template through the assistant
  in stage 8's.

### B. The AI event store (stage 8)

- **B1. One append-only table** in the control plane's store, beside
  incidents and approvals (and the ledger from stage 9). Event kinds:
  `model_loaded` (checksum result), `model_call`, `classification`,
  `retrieval`, `template_proposed`, `question_asked`, `approval_requested`,
  `approval_decided`, `action_run`, `outcome_verified`, `eval_result`,
  `data_egress` (F3), `stop_pressed`, `stop_released`.
- **B2. `model_call`** records the time, the engine image digest, the model
  checksum, the prompt's hash and byte count, tokens in and out, latency,
  the grammar id, the finish reason, any error, the redaction filter's
  version, and which knowledge items reached the prompt, by id and version
  (AI-06). The redacted prompt text is kept on the node for the owner's
  review; a setting turns that off.
- **B3. `classification`** records the intent, the template id, the
  confidence, the language, the fields extracted, and whether the
  deterministic layer or the model decided.
- **B4. `retrieval`** records the query hash, the index's commit stamp, the
  items ranked with their scores, the items included, and whether the answer
  was grounded.
- **B5. `data_egress`** records the provider, the purpose (reflection or
  evaluation), the byte count, the record ids summarised and the redaction
  filter's version. It is written before the send by the one function that
  can send; a send without an event is impossible by construction, and a
  failed write refuses the send (SEC, "nothing fails silently").
  *Amendment, 2026-10-20 (decided; ADR 0012):* the purpose also takes
  *performance review* and *public question*, with the lane. For the review
  lane the event holds the exact payload, a `ReportCard` of schema version
  `rikuri.report-card/1`, and whether the owner approved that send or the
  weekly send was automatic. The one function that can send is the AI relay
  of the lobby zone (platform plan D18).
- **B6. Derived views, computed and never stored:** p50 and p95 latency,
  grounded rate, clarification rate, misroute rate (cards rejected),
  approval rate, and the running release's eval score. They are the AI page
  and the assistant's row in the status API. Health rule: model loaded and
  verified, the last eval score at or above its floor, p95 latency within
  budget, error rate within budget; otherwise degraded, with the reason
  named, never "unknown" shown as healthy (EVID-01).
- **B7. No second store.** The frontend reads the control plane's API; no
  aggregator, no copy. Retention is an owner setting with a default to
  decide in stage 8 (§6).
- **B8. The emergency stop** writes `stop_pressed` at the choke point before
  every model call and cancels in-flight calls (AI-03); `stop_released`
  needs the owner's step-up.

### C. The evaluation gate (stage 8, in CI)

- **C1. Labelled sets, versioned in the repository, fixed before tuning**
  (AI-07): intents, with expected intent and template fields, grown from the
  previous node's fixtures to at least 200 cases in the four languages it
  tested (en, zh-CN, zh-TW, ja); knowledge questions in the owner's words
  with the item that must ground the answer and a must-contain and
  must-not-contain check, grown from the 242-question set; hallucination
  probes — prompts that invite an invented command, control or figure, from
  the bake-off's `lncli` class, passed by a refusal or a grounded answer;
  action extraction cases per template; runbook-symptom cases.
- **C2. Thresholds** are set per set at the first measurement and may only
  rise; a held-out split is never tuned on; the run uses the release's exact
  engine digest, model checksum, grammar and prompts.
- **C3. Where it runs.** In CI against the pinned engine and model on the CPU
  image, on the release branch and nightly; if too slow for every pull
  request, it is a required check on the release pull request and never
  skipped for a release. Its result ships inside the set as a file the node
  shows as "this release measured …" (runtime truth).
- **C4. On the node,** a smoke subset of about 20 cases runs after every
  model load and writes `eval_result` events; a failure marks the assistant
  degraded before an owner sees garbled output (the fork's flash-attention
  class, §1.1).
- **C5. A model or engine change is a release** with the gate's numbers in
  its Build Record; a regression against the thresholds blocks it.
- **C6. The labelled evaluation F2 requires before reflection:** a set of
  incident histories from the test stack's drills and the lessons register's
  records, each with the proposal an expert would make; reflection's output
  is scored against them by a written rubric; the acceptance floor is set at
  the first measurement. Reflection is not ported before this set exists,
  and when ported it proposes into a reviewed backlog only (§3.3).

## 5. Sequence by stage

| Stage | The assistant's part |
|---|---|
| Now (stage 1, B0) | This plan and ADR 0008. No code. |
| 7 Backend API and channel management | Runbooks as code (§3.4); the action templates and their regtest drill (contract A); the single approval store (HEAL-07). No model. |
| 8 Frontend, then the assistant | The UI first (D15). Then: the engine container in the release set and the model by checksum (ADR 0008); the N150 measurement and the model choice (F4); the grammar classifier and the two-job harness (§3.2); retrieval from the shipped index (§3.5); the event store and the AI page (contract B); the evaluation gate in CI and the smoke on load (contract C); the sandbox boundary tests of gap G5; one template driven end to end through the assistant on a test network. |
| 9 Treasury and agent payments | Mandates and the approval queue on the same templates; the ledger joins the store. |
| After stage 8's drill | Phone-side voice (F5 A); the weekly report (§3.3); the cloud option's code, high-risk (F3), and the review lane's report card and its shadow period (ADR 0012); the reflection evaluation set, then reflection (F2, C6); whisper.cpp if the budget allows (F5 B). |

## 6. Open items (not decisions yet)

- The model: measured in stage 8 (§3.1); E2B first.
- Whether one model meets the classification floor (F4), or the fallback
  router model is needed.
- The event store's retention default (B7) and whether redacted prompt text
  is kept by default (B2).
- The gate's initial thresholds (C2) and the size of the reflection set (C6).
- Whether whisper.cpp fits beside the model on the N150 (F5 B).
- Which cloud provider the F3 option uses, decided when its code is built;
  its Build Record is high-risk. The redaction filter is decided (2026-10-18,
  ADR 0009): AISecurity's sensitive-data and key-filter detectors, linked as
  a pinned crate; see the [threat model §7](../security/THREAT_MODEL.md#7-aisecuritys-place-s1).
- Open under ADR 0012 (decided 2026-10-20): which provider serves the review lane,
  once its retention and training terms are read and recorded; whether a
  bigger local model runs on an owner-run machine; and whether the review
  lane moves from approval of each send to an automatic weekly send after its
  shadow period. Until the shadow period ends, the owner approves each send
  (confirmed by the owner, 2026-10-20).

## 7. Sources (read 2026-10-18)

- The previous repository, `/home/junc/rikuri/rikurinode` at `3bbbe392`: the
  files named in §1.
- The fork, `/home/junc/Lean_llama.cpp` at `1b37afab`: `README.md`,
  `docs/leankv-EXECUTIVE-SUMMARY-2026-07.md`, `docs/RESULTS.md`, `git log`,
  `git remote -v`.
- [llama.cpp container images](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md);
  [latest release](https://github.com/ggml-org/llama.cpp/releases/latest)
  (v0.7.0, 2026-10-15).
- TurboQuant's upstream status: [turbo-quant.com](https://turbo-quant.com/turboquant-llama-cpp);
  [vucense.com](https://vucense.com/dev-corner/turboquant-llama-cpp-install-benchmark-2026/).
- [ReadKV, arXiv 2610.11245](https://arxiv.org/abs/2610.11245) (query-adaptive
  progressive codes; no engine or code named);
  [MultiAlloc, arXiv 2610.18642](https://arxiv.org/abs/2610.18642)
  (profiling-guided precision allocation; code on GitHub).
- [whisper.cpp models](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md):
  tiny 75 MiB, base 142 MiB, small 466 MiB, with English-only variants.
