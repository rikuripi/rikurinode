# ADR 0012 — Cloud model lanes and the weekly performance review (amends F3)

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-20 ("accept all five."; record `docs/build-records/2026-10-20-accept-adrs-0010-0014.md`); drafted the same day from the owner's direction in chat ("Ok, so we'll stay rootful, and make all the adjustments you just listed with report-card schema and F3 changes to the Rikuri Node Plan."); its defaults confirmed the same day ("1. SSH window OK with 1 hour default, 24 hours at most. Manual approval for each external AI send until finish of shadow period, OK.") |
| **Decision** | F3 of `docs/architecture/assistant-plan.md` §2, amended; D16 of `docs/architecture/platform-plan.md` §7; the dated caveat on AI-02 in the lessons register |
| **Supersedes** | Nothing. F3's alternatives A to C stand as written; this is a dated clarification of the option chosen on 2026-10-18 ("Owner enabled cloud: option for reflection and eval") |
| **Beside it** | ADR 0008 (the inference engine), ADR 0009 (the redaction filter), ADR 0010 (the AI relay in the lobby zone) |

## Context

F3, decided 2026-10-18: no cloud model by default; an owner-enabled exception
for reflection and evaluation only, off by default, redacted and recorded
before each send; chat and actions stay local (AI-02).

The owner, 2026-10-20: "AI model, originally set for a thinking model that
may help to evaluate(reasoning) how the node is performing and if lightning
management is maxmizing profitability, fees, and rebalancing. That may
contradict the privacy on data. So, I don't know." The owner also uses hosted
models (a hosted open-weight model and frontier models) and can run a bigger
local model on a machine of their own.

The redaction filter of ADR 0009 catches secrets and keys. It is not built to
hide a node's strategy, and a performance review needs numbers about channels.
Whether a model that can reason about fees fits on the N150 is measured in
stage 8 (assistant plan §3.1) and not known today.

## Decision

- **Three lanes, chosen by data class and not by the model.**
  - *Local (default).* Anything that touches node data, plus chat and action
    classification. The engine is ADR 0008's, on the node. An owner-run machine
    on the owner's own network may serve a bigger model; it counts as local
    only when it is the owner's, reached over the LAN or Tailscale, and
    recorded as such.
  - *External public.* General questions and public data, such as explaining
    a fee-market chart. The control plane builds the prompt from a template
    with no private fields, so the model is never asked to leave things out.
    Off by default.
  - *External review.* The weekly performance review, reflection and
    evaluation. It carries only the sanitized report card below. Off by
    default.
- **Data classes.** *Never leaves:* seed, keys, macaroons, addresses, peer
  keys and aliases, channel and transaction identifiers, payment hashes and
  memos, onion and IP addresses, absolute amounts, exact timestamps, free text
  from outsiders. *Sanitized card:* ratios, percentages, buckets, relabelled
  channels, week-aligned dates. *Public:* market data and the public graph.
- **The report card is typed Rust, versioned, and the only thing the review
  lane may carry:**

```rust
struct ReportCard {
    schema: &'static str,        // "rikuri.report-card/1"
    period: Period,              // week-aligned dates, no clock times
    node: NodeSummary,
    channels: Vec<ChannelRow>,   // labels reshuffled in every report
    bounds: Bounds,              // limits any suggestion must respect
    public: PublicContext,       // public data only
}
struct Period { start: Date, end: Date }
struct NodeSummary {
    size_class: SizeClass,       // Small | Medium | Large
    channel_count: CountBucket,  // 1-3 | 4-8 | 9-20 | 20+
    fee_yield_bps: u32,          // annualized earnings, basis points of average capacity
    rebalance_cost_pct: u8,      // of routing revenue
    onchain_cost_pct: u8,        // of routing revenue
    forward_success_pct: u8,
}
struct ChannelRow {
    label: char,                 // 'A', 'B', ...; the mapping never leaves the node
    age: AgeBucket,              // Under30d | D30to90 | Over90d
    capacity_share_pct: u8,      // share of node capacity
    local_ratio_pct: u8,         // local share of this channel
    ppm_out: u32,                // the node's own fee policy
    ppm_in: u32,
    forward_share_pct: u8,       // share of the node's forwards
    earned_share_pct: u8,        // share of routing revenue
    failure_pct: u8,
    peer_class: PeerClass,       // Hub | Mid | Small, from public graph data
}
struct Bounds { min_ppm: u32, max_ppm: u32, max_step_pct: u8 }
struct PublicContext { mempool_fee_level: Level, market_trend: Trend }
```

- **The only accepted answers are these suggestions:**

```rust
enum Suggestion {
    SetFeePpm { label: char, ppm: u32, evidence: Vec<FieldRef> },
    SetRebalanceTarget { label: char, local_ratio_pct: u8, evidence: Vec<FieldRef> },
    FlagForReview { label: char, reason: ReasonCode },
}
```

  There is no open, close or send. Anything that does not parse is dropped.
- **Every external send goes through the AI relay** (ADR 0010) and is
  recorded before it leaves as a `data_egress` event holding the exact payload
  (assistant plan contract B5). Each lane is opted into separately. The
  owner sees and approves each send until the review lane's shadow period
  ends (confirmed by the owner, 2026-10-20); moving the review lane to
  automatic weekly sends is a later owner choice, made after its shadow
  period.
- **External models get no tools, no secrets and no access to the node.**
  Their answers are labelled as external wherever shown.
- **Rust checks every suggestion:** inside `Bounds`, within the step size,
  and every evidence reference exists in the card. Applying one goes through
  an action template and the owner's tap behind step-up (assistant plan
  §3.7). No suggestion type moves funds.
- **Shadow first, judged on outcomes (in the spirit of F2).** For the first weeks the review
  only logs what it would have suggested and what happened afterwards, against
  a simple baseline such as a policy-based fee manager. It is promoted on
  evidence, by the owner. It is advice, not a learning loop that changes
  behaviour.
- **Providers.** Before a provider is enabled, its retention and training
  terms are read and recorded in a Build Record. One key per lane, held by the
  relay, with a spend cap set at the provider.
- **Proofs.** A CI test serializes a fixture card and fails if it contains
  anything shaped like a public key, transaction ID, address or large amount.
  A test shows the relay has no route to the core network. Changing the card's
  fields is a high-risk change.
- **AI-02 stays true for chat and actions:** private node data never goes to
  cloud models. Its dated caveat gains one sentence: the sanitized report card
  is derived from private data, and may leave only in the review lane, opted
  into, shown before each send.

## Consequences

- The owner accepts a residual risk in exchange for a stronger review:
  sanitizing is not perfect, unique patterns can re-identify a node, and the
  provider still sees the owner's strategy. This is why it is opt-in.
- A small node produces thin, noisy numbers, and routing profit depends on
  liquidity and demand, which no model creates. The review's value is judged
  on outcomes, not on how persuasive it reads.
- Edits that follow, each its own change: the platform plan's D16 row;
  assistant plan §2 F3 and contract B5 (new event kinds); the AI-02 caveat;
  the threat model's data-egress row. The card's types belong in the
  control-plane crate with their tests.

## Rejected

- Raw node data to a cloud model, even redacted: the filter hides secrets,
  not strategy.
- Cloud for chat and actions (F3 option C): node data would leave on every
  question.
- No external model at all: the owner's profitability question may need more
  reasoning than the node's engine gives; stage 8 measures it, and an
  owner-run machine covers the gap without a third party.
- Autonomous fee changes by the model: unattended changes to fee policy with
  no labelled evaluation yet (F2). Suggestions stay advice behind the
  owner's tap.

## Sources (read 2026-10-20)

- `docs/architecture/assistant-plan.md`: §2 F1 to F5, §3.1, §3.7, contract B5
  and §6.
- `docs/requirements/lessons-register.md`: AI-02 and its 2026-10-18 caveat.
- `docs/adr/0008-inference-engine.md`, `docs/adr/0009-security-built-in.md`.
- A provider's retention and training terms were not read for this draft;
  they are read before any provider is enabled (see the decision above).
