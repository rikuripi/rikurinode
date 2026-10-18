# Agent payments and marketplace plan

**Status: a plan, written 2026-10-17. Nothing in it exists yet.** It adds two
stages after the [platform plan's](platform-plan.md#8-stages) eight, names
the security layer they sit behind, and lists the owner's open decisions
(§6). It governs nothing until the owner decides them, and it changes nothing
in stages 1 to 8. Facts carry the date they were checked (§2). What the
previous repository's commerce code does is stated as what its source and
tests show, never as proven behaviour
([lessons register §7](../requirements/lessons-register.md#7-the-commerce-service-a-module-level-harvest-2026-10-17)).

## In one page

- **The node is the treasury and the accounting department.** It alone holds
  LND's credentials, pays, issues invoices, keeps the ledger and reconciles
  it. The owner's agents are purchasing staff: each has an identity of its
  own and a mandate the treasury signed, pays within the mandate without
  asking, and asks the owner, through the app's approval queue, for anything
  above it. Losing an agent means revoking a mandate, never losing access to
  money.
- **Agent payments work without a marketplace.** An agent with a mandate
  pays any L402 endpoint on the internet. The marketplace is a separable
  service (E2) that adds discovery, reputation, selling and auctions. On a
  Rikuri node it is a client of the treasury like any agent; the same service
  can run beside another maker's node (E9).
- **Three artifacts, never conflated:** identity (who the agent is), mandate
  (what it may spend, signed and revocable), proof of payment (the L402 token
  and preimage, a bearer artifact).
- **Three truths, reconciled:** the ledger, what LND reports, and the
  cryptographic evidence. A disagreement halts the affected mandates and
  alerts; nothing is quietly corrected.
- **The security layer has three parts.** The AISecurity policy evaluates
  and its detectors contribute signals; OpenShell encloses each agent (files,
  network, processes, credentials) and is its only path out; Sentry is a
  research input. Hard limits live outside the model
  ([AGENTS.md > Security baseline](../../AGENTS.md#security-baseline)).
- **Profit comes last.** Protect funds, preserve recoverability, keep the
  required liquidity, keep the security limits, meet obligations, minimise
  cost, then optimise net return. The AI recommends; Rust enforces the caps;
  LND executes.
- **Order:** stage 9, the treasury and agent payments; stage 10, the
  marketplace; both after stage 8's drill (E10). Both tiers get them (E6).
  The AI optimiser is the one piece the Pi may run elsewhere, or not at all.

## 1. What this plan answers

The owner's direction, given 2026-10-17 around the ChatGPT thread "OpenShell
Sentry Watch" (the vision of the node as a treasury, the "financial blast
radius" of each component, and a profitable node through AI-recommended,
Rust-enforced channel management):

1. Agent payment must work with or without the marketplace. The marketplace
   may be hosted by the nodes themselves, and nodes that are not Rikuri nodes
   should be able to join through an add-on, if their agents can pay in sats
   or a stablecoin.
2. Owner-signed authority is the more secure model. The process must stay
   automatic: the owner signs once to issue an agent's authority and once
   more when an amount exceeds it; authority can be renewed.
3. The pruned tier (the Raspberry Pi 5) gets revenue features too, in a
   simpler form if the hardware demands it.
4. The vision goes into the plan now and is updated before its stage starts.
5. The security layer is part of this plan, with the owner's AISecurity
   project as the example (most complete on macOS) and the owner's running
   analysis of NVIDIA's OpenShell and Sentry as its reference.

This plan does not decide the marketplace's product scope (which services,
what prices, which auction forms ship first); that belongs to stage 10's
Build Records. It writes no code and no ADR.

## 2. Facts this plan rests on (checked 2026-10-17)

| Item | Fact | Consequence |
|---|---|---|
| L402 | Lightning Labs' protocol for selling API calls and compute over HTTP: the server answers `402 Payment Required` with a token and an invoice; the client pays, obtains the preimage, and presents token and preimage. The token "commits to the Lightning invoice by containing the invoice's payment hash"; the recommended format is a macaroon, which "can be verified using only a root key and basic cryptography", so the seller verifies without a payment database. The token is a bearer instrument that can be attenuated and passed on. Aperture is the reference reverse proxy. | Proof of payment is a bearer artifact: it is neither identity nor authority, and the treasury stores cached proofs encrypted. Selling (stage 10) needs the treasury to issue invoices and tokens, and to verify statelessly. |
| LND macaroons | Three default macaroons share one root key; a caveat added to a macaroon "cannot be removed" by whoever receives it; `lncli` adds a 60-second timeout caveat by default; third-party caveats are not implemented; caveats that limit payments to routes, channels or nodes are listed as future work; a macaroon is invalidated only by replacing the root key (`changepassword --new_mac_root_key`), which invalidates all of them; root key rotation and per-macaroon invalidation are future improvements. | A single macaroon cannot be revoked, so no agent may ever hold one (AGENTS.md > Security baseline). The control plane alone holds a macaroon baked for invoices and payments; mandates are the treasury's own documents, revocable one at a time. |
| LND on a pruned bitcoind | Supported since LND 0.13: LND fetches blocks the server has pruned "by connecting to the server's full node peers and querying them directly" (`pruned-node-max-peers`, default 4; pull request 5154, merged 2021-04-08). The run-LND guide: "You may prune your Bitcoin backend. As LND will then need to fetch some blocks elsewhere, aggressive pruning can lead to performance loss"; `txindex` applies only to an unpruned node. | The Pi tier can run LND, open channels and pay. Re-verified at stage 4 against the pinned LND version, as the register requires (PLAT). |
| Taproot Assets | Lightning Labs' operational safety guidelines: there is "no recovery mechanism in place yet that allows you to recover assets from only the `lnd` seed"; the `tapd` database must be backed up regularly (hourly or more is suggested); Universe servers hold proofs but "the mechanisms to query all required data by just using `lnd`'s seed are not yet in place" (issue 426); losing `tapd` data can also make the bitcoin carrying the assets unspendable. tapd 0.8 (2026-06-23) adds wallet backup and restore in raw, compact and optimistic modes. | A stablecoin rail is its own backup-and-restore drill, after stage 5's, and buyer-side first (§4.4). It is not part of stages 9 or 10 unless the owner decides so (E7). |
| OpenShell | Apache-2.0. Newest stable v0.1.4 (2026-10-13; v0.1.3 10-09, v0.1.2 09-28); stable releases weekly, security updates for the newest minor and the one before. Architecture: a gateway (control plane, with a policy prover for agent-proposed network rules), a trusted supervisor ("The supervisor is trusted and makes the decisions": it checks requests against policy, supplies credentials, resolves DNS, opens approved connections) and an untrusted sandbox (non-root, no capabilities; Landlock for files, seccomp user notification staging network operations). "The mediated channel to the supervisor is the workload's only allowed egress path." "Agents never see real credentials": the supervisor adds a stored credential only to requests bound for endpoints policy approves. Drivers: Docker, Podman (rootless), Kubernetes, MicroVM (libkrun; KVM on Linux). Supported hosts: Debian/Ubuntu on x86_64 and aarch64, macOS; Fedora is not in the support matrix. | The candidate boundary for the assistant (stage 8) and for every purchasing agent (stage 9). The Podman driver matches decisions D2 and D5. Fedora IoT is unsupported upstream, so qualification on the node's OS is this project's own work. The version is pinned like every other component. |
| Sentry | NVIDIA's Open Agent Safety Platform (announced 2026-09-28) is "an open reference system design" that "combines the NVIDIA OpenShell secure runtime and NVIDIA Sentry with NVIDIA BlueField-4 in-silicon security enforcement"; no availability, price or licence is stated for Sentry; secondary reports describe monitoring from a DPU outside the agent's machine with quarantine on violation. | A research input, as Rikuri-PI's threat model already says. No hardware dependency; nothing in this plan waits for it. |
| OpenShell, tested | Rikuri-PI's receipt of 2026-09-28 (`/home/junc/Rikuri-PI/docs/security/evidence/2026-09-28-openshell-v0.1.2/`): v0.1.2 on Ubuntu x86_64 with the Docker driver passed ten bounded smoke outcomes (allowed reads and writes work; forbidden reads, writes, a symlink, a child process, TCP, HTTP and UDP are denied). Not tested: revocation, supervisor crash, live policy change, credentials, DNS leakage, IPv6, resource exhaustion, syscall escapes, a policy that permits selected destinations. Its status line: "production qualification Not yet proven". | The sandbox boundary test of stage 8 (register gap G5) is the prerequisite of stage 9, and it must cover what the receipt did not, on Fedora IoT with the Podman or MicroVM driver. |
| AISecurity | The owner's repository (`/home/junc/AISecurity`): a Rust core (`security-core`: agent policy, command policy, intent verifier, prompt injection, sensitive data, key filter, file sanitizer, model verifier and vetting, process manager, privacy router, threat feeds, vault, WASM sandbox) with an FFI, a macOS app in Swift (the most complete side), a Linux daemon crate, an MCP server crate and an intent hook; its implementation plan names OpenShell as a reference for declarative policy. | Policy evaluation and detectors are reuse candidates. In Rikuri-PI's adopted design the policy service "evaluates and translates" and "detectors only contribute signals"; enforcement is the sandbox's. This plan keeps that split (§4.3). |
| The previous commerce code | `commerce-service/` at 3bbbe392: 28,294 lines of Rust in `src/`, 10 integration test files with 53 test functions, 2 acceptance scripts, a separate binary on port 8089 speaking to the node through an adapter trait (`LnHostAdapter`: add and pay invoices, sign and verify messages, hold invoices, circular rebalance, BOLT12 decode) with LND-direct, Core Lightning and generic JSON-RPC adapters. No build record covers its behaviour (the records that name it do so in dependency or deployment notes); the lessons register had no entry for it. Its BLUEPRINT marks Tracks E, J, K, M and N complete; Track L's "AI agent payment safety" phase (signed `agent_id` attestation, a cross-node agent payment test) is queued and was never done; its two-node arc never passed; pay-via-BOLT12 is blocked. The agent identity is a self-asserted string; all mutating calls share one HMAC key when configured, else the loopback bind. | Behaviour and test cases carry over, code does not (platform plan §8). The adapter's surface is kept as the design of the treasury's door; the identity model is replaced (§4.2). Register §7 holds the harvest; gap G12 what must be proven. |

## 3. Roles

| Role | Who | Holds | Never holds |
|---|---|---|---|
| **Treasury and accounting** | the control plane (Rust, decision D3) | the LND macaroon for invoices and payments, the mandate-signing key, the ledger, the approval queue, the caps | untrusted content, model output as instructions |
| **Purchasing staff** | the owner's agents, each in its own sandbox (stage 8's boundary) | a mandate, cached proofs of payment, its task | an LND credential, a seed, a key that moves money, the treasury's signing key |
| **Trading floor** | the marketplace service (stage 10), on this node or another maker's | listings, reviews, reputation, auctions, a mandate for its own purchases | an LND credential; on a Rikuri node, any path to LND but the treasury |
| **Owner** | the person, through the app with step-up (register EXEC-03) | the seed and the static channel backup off the node, the decisions, the approvals | nothing the node needs at run time |

Three artifacts stay distinct: an **identity** says who is asking; a
**mandate** says what that identity may spend, on what, until when, signed
by the treasury and revocable one at a time; a **proof of payment** (the
L402 token and preimage) says a payment happened and can be shown to anyone.
The owner's term "AI Passport" names the first two together; this plan uses
"identity" and "mandate" so the two cannot be confused with the third.

## 4. Architecture

```
                owner (app, step-up)
                        │ decisions, approvals
                        ▼
   ┌─────────────────────────────────────────────┐
   │ control plane: THE TREASURY                 │
   │  mandates · payment pipeline · invoices     │     the one door
   │  ledger · reconciliation · approval queue   │ ───────────────▶ LND
   │  caps (blast radius) · revocation list      │   baked macaroon
   └───────────▲──────────────────▲──────────────┘
   signed      │                  │ invoice / verify
   requests    │                  │
   ┌───────────┴────────┐   ┌─────┴──────────────────┐
   │ OpenShell sandbox  │   │ marketplace service     │
   │  agent (purchasing)│   │  listings · reviews     │
   │  AISecurity signals│   │  auctions · discovery   │
   │  egress: treasury  │   │  a client of the        │
   │  + allowed vendors │   │  treasury, on this node │
   └────────────────────┘   └─────────────────────────┘
```

### 4.1 The treasury, in the control plane

In the platform plan's design the control plane is the single authority
over LND and the assistant's only door ([platform plan, "In one page"](platform-plan.md#in-one-page)).
The treasury is a module of it, not a second service with its own path to
LND: the previous repository's commerce service spoke to LND through its own
adapter, which is a second door, and this plan closes it. On a Rikuri node
everything that moves money goes through the treasury.

What it does:

- **Mandates:** issue, renew, revoke, list (§4.2).
- **The payment pipeline**, for each request from an agent:
  1. verify the request's signature and that its identity has a mandate
     that is current, unrevoked and names this vendor or class of vendor;
  2. check the caps: per payment, per day, per vendor if set; **reserve**
     the amount against the day's cap before paying, so two requests cannot
     both pass on the same headroom (register OWN-02);
  3. take AISecurity's signals into account (a vendor flagged, an anomaly in
     the agent's pattern) under the owner's policy: a signal can hold a
     payment for approval, never approve one;
  4. within the allowance: pay through LND with the treasury's own macaroon,
     with the timeout and pending-id handling of register LN-06 so a slow
     payment is never paid twice;
  5. above the allowance, or held: put it on the approval queue (register
     HEAL-07); the owner's step-up approves or denies; a denied or expired
     request releases its reservation;
  6. write the ledger entry and hand the agent its receipt (the preimage and
     token). A refusal is recorded and told to the agent; a retry through
     another path is alerted (AGENTS.md > Security baseline).
- **Invoices for sales:** the marketplace, or any seller endpoint, asks the
  treasury for an invoice and a token; the treasury verifies presented
  proofs statelessly (§2, L402) and records the sale.
- **The ledger:** append-only and hash-chained, holding mandates issued and
  revoked, reservations, payments, receipts, invoices, settlements and
  approvals, with the agent, vendor and reason on every line. It is written
  off the node with the same destination rules as the static channel backup
  (register FUND-01): the wallet proves money moved; it is not the only
  record.
- **Reconciliation:** on a cadence and after every payment batch, three
  truths are compared: the ledger, LND's own payment and invoice lists, and
  the evidence (payment hashes, preimages, proofs). A disagreement raises
  **financial state divergence**: the affected mandates are suspended, the
  owner is alerted (register EVID-06, HEAL-09), and nothing is corrected
  silently. This is register EVID-04 (runtime truth over declared truth)
  applied to money.
- **Caps as the blast radius.** Every component gets a maximum-loss
  envelope the owner sets (E5), so "is this safe?" becomes "if this exact
  component fails completely, what is the most that can be lost?":

  | Component fails completely | Maximum irreversible loss | How |
  |---|---|---|
  | one purchasing agent, or its sandbox | its mandate's remaining daily cap | revoke; the reservation rule stops a burst above the cap |
  | the marketplace service | its own mandate's daily cap | it is a client, not an authority |
  | the treasury's software | the node's operating balance, if LND itself is reached | the control plane's narrow access to LND (register EXEC-08); funds beyond the operating balance stay with the owner, off the node, as the seed and the static channel backup do ([platform plan §4.3](platform-plan.md#43-layer-3--funds-and-data)) |
  | the ledger | no funds; the time to restore and reconcile | append-only, off-node copy, reconciliation against LND and the evidence |
  | a vendor or the directory | the payments already made to it | reputation and allow-lists; no credential of ours is at the vendor |

- **Security-critical state survives software changes.** Mandates,
  revocations, reservations and caps are versioned; an update, a rollback or
  a mixed-version period must never drop or reinterpret them. If an older
  component cannot read a newer record, the feature stays disabled until it
  can (register UPG-08 and UPG-10 extended; the owner's OpenShell analysis of
  2026-10-17 found exactly this class in a sandbox-update proposal, where an
  older replica could rewrite state without the newer security fields).
  Stage 9's drill updates and rolls back the node with a reservation
  outstanding and shows it intact.

### 4.2 Agent identity and mandates

**Identity.** Each agent has an identity key pair. The private half never
sits in the agent's own context: OpenShell's credential model attaches a
stored credential to requests bound for approved endpoints and "agents never
see real credentials" (§2), so the agent's identity is a credential the
supervisor attaches to requests bound for the treasury and nowhere else.
Compromise of the agent's context then cannot steal its identity. If
qualification shows the supervisor's credential path cannot carry this
(untested in the receipt), the fallback is a key inside the sandbox with a
short-lived mandate; that is a weaker property and an option under E4, not
a quiet substitution.
An agent outside any Rikuri sandbox (another node's, a third party's) is
just an untrusted client with a key of its own: it gets a mandate only if
the owner issues one, and the treasury trusts nothing but the signature.

**Mandate.** A document signed by the treasury's mandate key (in the
control plane's secrets store, never exported), with:

- the identity it binds to;
- the caps: per payment, per day, optionally per vendor;
- what it may buy: an allow-list of vendors or vendor classes, or "any L402
  endpoint" as an explicit choice with its own cap;
- the currency (sats; a stablecoin only after E7);
- not-before and expiry; a serial number;
- the issuer's signature.

**Issue, renew, revoke.** The owner creates an agent in the app behind
step-up and sets its caps, or accepts the defaults of E5: one signature, the
treasury's, on the owner's approved action. A payment above the mandate goes
to the approval queue: the owner's second signature is the app's step-up on
that item, not a raw key stored on the node (if the node signed for the
owner, the node would be approving itself). Renewal is a new mandate with a
later expiry; expiry is short by default (E5), and an expired mandate is
shown in the app and the ledger, so a forgotten agent stops spending without
being forgotten. Revocation is a serial on the treasury's list, checked on every
request, effective at once, and recorded in the ledger. Losing an agent's
identity therefore means "revoke and issue another", never "we lost access
to the money".

**Proof of payment.** The treasury hands the agent the L402 token and
preimage as its receipt, and may cache them for reuse, encrypted at rest.
The previous code cached them as plain JSON files: its at-rest encryption
helper was never wired into that cache, so the requirement is new here. A
proof is a bearer artifact: it buys access to the paid resource and nothing
else, and the ledger, not the cache, is the record.

### 4.3 The security layer

The rules come from [AGENTS.md > Security baseline](../../AGENTS.md#security-baseline):
the assistant plans and never holds authority; hard limits are enforced
outside the model; outbound network is denied by default with an explicit
allow-list; tool scope is fixed per task; a denied call ends the attempt and
a retry through another path is alerted; keys, seeds, macaroons and L402
credentials never enter an agent's context; signing and payments stay in
deterministic code behind a secrets store; payments above an owner-set amount
need the owner; and no single component holds untrusted input, outside
communication and payment authority together. This section says which part
holds which rule, and what each part is proven to do today.

**Part 1, the AISecurity policy: evaluates and signals.** Rikuri-PI's
adopted design (its threat model of 2026-09-28) splits the layer in two:
trusted policy evaluation emits a versioned plan within the current grant,
detectors only contribute signals, and a qualified enforcement backend
enforces. The owner's AISecurity core already has the detectors this plan
needs (prompt injection, sensitive data, key filtering, command and agent
policy, intent verification, model verification) and a policy vocabulary.
Here they do three things: screen what an agent sends to the treasury (a
request built from injected text is a signal, and the pipeline holds the
payment); screen what comes back from vendors and the directory before an
agent reads it (register AI-02: untrusted external text is not ingested
unless a reviewed feature needs it); and keep secrets out of logs, responses
and the agents' context (register SEC-01). The Linux daemon side of
AISecurity is less complete than the macOS app; what stage 9 uses is pinned
and gated like every other dependency, and a detector that stops firing is
alerted by its absence (AGENTS.md > Design rules: nothing fails silently).

**Part 2, OpenShell: encloses and enforces.** One sandbox per agent, built
by the Podman driver (or the MicroVM driver if qualification prefers it), on
the node's own user ranges (decision D5). Files: only the agent's working
directory, read-only elsewhere, no secret path at all. Network: the
supervisor is the only egress; policy permits the treasury's loopback
endpoint and the vendors the mandate names, nothing else, and DNS is the
supervisor's. Processes: unprivileged, seccomp-filtered. Credentials: the
agent's identity is attached by the supervisor (§4.2). OpenShell's own
proposal and auto-approval features are disabled, or routed to the
treasury's queue as untrusted requests, so an agent cannot widen its own
policy (Rikuri-PI's threat model, row "Worker widens its own policy").
What is proven today is the receipt in §2: ten smoke outcomes on Ubuntu with
Docker, v0.1.2. What is not proven is the list beside it, plus Fedora IoT
and the Podman driver. Stage 8's sandbox boundary test (register gap G5)
proves it before stage 9 begins: no secret file readable by any command
form, no host shell, network limited to the allow-list, no key and no
signing authority in the sandbox, the emergency stop cancelling in-flight
calls (register AI-03).

**Part 3, Sentry: a research input.** A reference design for monitoring
from hardware the agent's machine does not control. Nothing here waits for
it; if it becomes available on hardware a node can have, it is an added
layer, never a replacement for the two above.

**Who holds what.** The rule that no single component holds all three
together, checked against this design:

| Component | Untrusted input | Outside communication | Payment authority |
|---|---|---|---|
| purchasing agent (in its sandbox) | yes | yes, through the supervisor, to allowed vendors | **no** |
| marketplace service | yes (listings, reviews, peers) | yes | **no**; it has a mandate like any agent |
| treasury (control plane) | **no**: signed, schema-checked requests only | **no**: LND on loopback, the ledger destination | yes, within mandates and caps |
| owner's app | no | no | the approvals, behind step-up |

The treasury takes no free text from anyone: a payment request is a typed,
signed, schema-validated message, and model output never becomes an
instruction to it (register AI-01: one executor, read-only tool surface,
mutations through the authoritative control plane).

**The owner's running analysis** of OpenShell and Sentry (the "Sentry
Watch" thread) stays the way this layer is kept current: each new finding
is a fact for §2 with its date, and a requirement only when a Build Record
adopts it. Two patterns from it are noted for stage 8 and 9's design, not
adopted: security state that must survive mixed versions (already a rule in
§4.1), and sandbox-initiated control connections so a host exposes no
inbound management port (worth testing for remote agents; reversing the
direction does not by itself create trust).

### 4.4 The marketplace

A separable service, in Rust, that on a Rikuri node is a client of the
treasury: it holds a mandate for its own purchases, asks the treasury for
invoices and verification when it sells, and has no path to LND (decision
E2). The same service runs beside another maker's node, speaking to that
node's LND or Core Lightning through a thin adapter; that door is theirs
(E9). It carries:

- **Listings and reviews, signed** with the node's Lightning identity key,
  verified before they are accepted, with challenge-response proof of key
  ownership and anti-replay nonces (the previous repository's registry
  design, register §7).
- **Reputation** that costs an attacker real resources: reviews bound to
  settled payments, counterparty diversity, tiers, rate limits per key, a
  wash-trading ring scoring below the tier (its acceptance script is a test
  case to carry).
- **Auctions** for scarce services: every bid backed by a hold invoice so
  "you can't bid what you can't pay", the winner's invoice settled and the
  losers' released; an agent's auto-bid policy is a mandate with auction
  caps. The previous design led with a sealed second-price form; which forms
  ship first is stage 10's decision (§1).
- **Discovery:** a distributed hash table over libp2p in the previous code,
  tested on two nodes at most. A directory of nodes needs bootstrap peers,
  and who runs them is a centralization point the owner decides (E3).
- **Currencies:** sats. A stablecoin rail is Taproot Assets with edge-node
  conversion: a seller can always receive sats, a buyer paying in a
  stablecoin needs `tapd` and an asset channel on its own node, and `tapd`'s
  state needs its own backup and restore drill (§2). Buyer-side, after that
  drill, if E7 says so.

A marketplace with few nodes is a directory with few entries; the
previous repository's flywheel (marketplace traffic → payment flow → better
channel data → better liquidity management → cheaper payments) starts only
when nodes exist. Stage 10's drill therefore runs two nodes, one of them not
a Rikuri node, and proves the service without assuming a network.

### 4.5 The node's economics, stage 7's controller

Stage 7 is planned to deliver channels, fees, rebalancing, node search
and analytics. This plan adds only the objective and the interface the treasury
needs from it. The objective is the channel's **net economic contribution**:
routing revenue, plus the payment flow the node's own agents and marketplace
generate, plus liquidity-service revenue, minus rebalancing cost, open and
close fees, failed-payment cost, capital cost and operational risk. Not
routing volume, not balanced channels, not uptime: those are proxies. The AI
recommends (a fee change, a rebalance up to a cost, a channel to open or
close) with its expected net benefit and confidence; Rust checks the
recommendation against caps the owner set (rebalance cost ceiling, minimum
reserve, permitted peers) and executes or refuses; LND does the work. The
previous repository's rebalance executor had five such gates and per-call
and daily caps; its gates are test cases for stage 7, with register gap G1's
warning that none of it ever ran with funds. The AI never decides "close
enough, spend more": a recommendation above a cap is a proposal on the
owner's queue, like a payment above a mandate.

### 4.6 The two tiers

Both tiers get the treasury, agent payments and the marketplace service, if
E6 says so. LND on the Pi's pruned backend is supported (§2) and re-verified at stage 4.
The deterministic parts are light; the heavy part is local inference for the
optimiser and the agents. The Pi may run the optimiser on a schedule, use a
remote model through the sandbox's allow-list, or not run it at all (E6).
Resource budgets come from register PLAT-04, sized per tier in one place.
The Pi itself stays on hold under decision D1 until Fedora IoT runs on it.

## 5. Stages 9 and 10

| Stage | Delivers | Its drill | After |
|---|---|---|---|
| 9 Treasury and agent payments | Mandates (issue, renew, revoke) in the app behind step-up; the payment pipeline with reservations and the approval queue; invoices and stateless verification for sellers; the hash-chained ledger written off the node; reconciliation and the divergence alarm; the caps and the blast-radius table as settings with defaults (E5); one agent in an OpenShell sandbox on Fedora IoT, with AISecurity's detectors in its path | On a test network: an agent with a mandate pays an L402 endpoint within its allowance and gets its receipt; a payment above the cap waits on the queue and goes through only on step-up; a revoked agent, a forged mandate, an expired one and a replayed request are refused and recorded; two requests racing for the same headroom cannot both pass; an injected ledger-versus-LND disagreement suspends the mandates and alerts; a reservation survives an OS update and its rollback; the sandbox boundary test of stage 8 passes again with the agent inside, and the agent cannot reach LND, a macaroon or the mandate key by any command form | stage 8's drill |
| 10 Marketplace | The marketplace service as a separable binary; signed listings and reviews; reputation and its anti-fraud scoring; discovery with the owner's bootstrap decision (E3); auctions with hold-invoice collateral; selling through the treasury's invoices; the help pages for all of it | On a test network, two nodes, one Rikuri and one not (E9): publish, discover, buy, review; a forged listing and a replayed review are refused; a ten-key wash-trading ring scores below the trusted tier; a sealed auction settles with hold invoices, the loser's released; the Rikuri node's marketplace has no path to LND except the treasury | stage 9's drill |

Stage 7's backend API is designed with these in view: the treasury's door
to LND is the same narrow interface stage 7 builds, and the one approval
path register HEAL-07 requires, wherever stages 7 and 8 build it, is the one
stage 9 extends. Neither stage pulls work forward: stages
1 to 8 are built, drilled and closed first.

## 6. Owner decisions

None of these is taken. Each is a behaviour-changing default, exposed as a
costed, reversible choice (AGENTS.md > Design rules; register OWN-09).

| | Decision | Options and their costs | Recommended |
|---|---|---|---|
| E1 | Where the security layer is planned | **A section of this plan** (§4.3): one document, the layer read beside what it protects; costs: this plan grows with every security finding. **A dedicated security plan**: its own facts, drills and decisions; costs: two documents to keep aligned before any of it exists. | A section now; split out when stage 8's Build Records make the layer concrete |
| E2 | Where the marketplace runs | **A separable service** that is a client of the treasury: a separate crash and audit surface, portable to other makers' nodes, no path to LND; costs: one more service to update, drill and watch. **Inside the control plane**: one binary, one update; costs: the trusted binary grows, and a marketplace bug sits beside the money. | A separable service |
| E3 | Directory bootstrap | **Manual peer entry only**: no central point; costs: a novice must know a peer. **Owner-run seed nodes**, their addresses signed and shipped in the image: easy joining; costs: a centralization point the owner operates and pays for. **DNS seeds** as Bitcoin does: costs: DNS as a trust path, and operators needed. | Manual entry plus a signed seed list the owner can run, revisited when nodes exist |
| E4 | Agent identity | **Owner-signed mandates with an automatic allowance** (§4.2): per-agent caps enforced by signature, revocation one at a time; costs: a mandate key to protect and a mandate format to version. Within it, where the identity lives: **attached by the sandbox's supervisor**, so the agent never sees it; costs: it depends on OpenShell's credential path, untested in the receipt. **A key inside the sandbox**: works with any sandbox; costs: a compromised agent context holds the key, so the answer is revocation rather than nothing. **One shared write key** (the previous code): simple; costs: agents indistinguishable, a cap only a database row anyone with the key can raise, revocation means rotating every agent. | Owner-signed mandates, the identity attached by the supervisor where qualification allows it |
| E5 | Default caps for a new agent | Proposed defaults, each a setting: per payment 100 sats, per day 1,000 sats, approval for anything above, mandate expiry 30 days, "any L402 endpoint" off. Lower: smaller blast radius, more approvals; higher: fewer interruptions, more at risk per agent. The previous code's default was 500 sats a day with a "net-positive" mode that cut off an agent spending more than it earned after 14 days; whether that mode returns is part of this choice. | The proposed defaults, decided when stage 9 begins and re-costed at today's prices |
| E6 | The pruned tier's share | **Treasury and marketplace on both tiers, the optimiser optional on the Pi** (scheduled, remote through the allow-list, or off); costs: two resource budgets to size and test. **N150 only** for revenue features; costs: the Pi stays a plain node. | Both tiers, optimiser optional |
| E7 | A stablecoin rail | **Taproot Assets, buyer-side, after its own backup and restore drill**; costs: `tapd` on the node, its hourly backups, an asset channel with an edge node, a drill. **Sats only** for stages 9 and 10; costs: agents cannot pay vendors that price in dollars. | After its drill, as its own stage |
| E8 | Harvest depth of the previous commerce code | **Module-level now** (register §7), **per-file verdicts before stage 9 opens**; costs: a second read later. **Full per-file now**: costs: days of reading 28,000 lines whose stage is far off. | Module-level now, per-file before stage 9 |
| E9 | An add-on for other makers' nodes | **Ship the marketplace service standalone** with thin LND and Core Lightning adapters, as the previous design intended; costs: support for platforms this project does not run, and the add-on's door to their node is theirs to secure. **Rikuri nodes only**: costs: a smaller marketplace. | Standalone, documented as "your node, your door" |
| E10 | Stage placement | **Stages 9 and 10 after stage 8**: the approval queue in the app and the sandbox exist first; costs: revenue features wait for the frontend. **The treasury inside stage 7**: earlier; costs: payments before the sandbox and the UI that approve them exist, against the baseline. | After stage 8 |

## 7. What the previous repository gives, and what it does not

The platform plan's rule stands: behaviour and test cases carry over, code
does not. [Lessons register §7](../requirements/lessons-register.md#7-the-commerce-service-a-module-level-harvest-2026-10-17)
holds the module-level harvest: each module, what its source says it does,
the tests it has, and a provisional verdict. The short form:

- **Keep as design:** the adapter's surface (invoice, pay, sign, verify, hold
  invoices, circular rebalance) as the treasury's door; the registry's
  signature, challenge and nonce scheme; hold-invoice collateral for bids;
  "AI proposes, Rust decides" with per-call and daily caps.
- **Keep as test cases:** the integration tests and the two acceptance
  scripts (the wash-trading ring, the fly-by agent); the rebalance
  executor's five gates; the HMAC write gate's tests as negative cases for
  the mandate check.
- **Replace:** the identity model (a self-asserted string and one shared
  key); the second door to LND; the yield-protocol interface (no
  implementation, out of scope).
- **Not evidence:** BLUEPRINT's "complete" marks. No build record covering
  its behaviour, no payment on any network, no two-node run passed. Register gap G12 says what
  must be proven.

## 8. Sources (read 2026-10-17)

- Lightning Labs, L402: https://docs.lightning.engineering/the-lightning-network/l402
- LND macaroons: https://github.com/lightningnetwork/lnd/blob/master/docs/macaroons.md
- LND pruned backends: https://github.com/lightningnetwork/lnd/pull/5154; run LND: https://docs.lightning.engineering/lightning-network-tools/lnd/run-lnd
- Taproot Assets operational safety: https://docs.lightning.engineering/lightning-network-tools/taproot-assets/operational-safety-guidelines; tapd 0.8: https://lightning.engineering/posts/2026-06-23-tapd-0.8-launch/
- NVIDIA OpenShell: repository and releases https://github.com/NVIDIA/OpenShell/releases; architecture https://docs.nvidia.com/openshell/latest/about/architecture.html; support matrix https://docs.nvidia.com/openshell/latest/about/support-matrix.html; overview https://docs.nvidia.com/openshell/latest/; product page https://www.nvidia.com/en-us/ai/openshell/ (Sentry, "open reference system design")
- Rikuri-PI (read with `git -C /home/junc/Rikuri-PI show HEAD:`): `docs/security/THREAT_MODEL.md`; `docs/security/evidence/2026-09-28-openshell-v0.1.2/README.md`; `docs/build-records/2026-09-28-option-c-security-and-personal-data.md`
- AISecurity (`/home/junc/AISecurity`): `README.md`, `docs/AISECIMPLEMENTATION.md`, `SecurityCore/crates/`
- The previous repository (read with `git -C /home/junc/rikuri/rikurinode show HEAD:` at 3bbbe392): `commerce-service/` and `ln-host-adapter/` sources and tests; `docs/plans/BLUEPRINT.md` (Tracks E, J, K, L, M, N); `docs/plans/UniversalAgenticPayment.md`; `docs/plans/AGENT-COMMERCE-VISION.md`; `docs/plans/MARKETPLACE-PLAN.md`; `docs/L402/`; `docs/knowledge/services/lightning-marketplace.md`
- The owner's ChatGPT thread "OpenShell Sentry Watch" (shared 2026-10-17), the vision this plan places; its claims about OpenShell pull requests are not relied on here
