# Rikuri Node threat model

**Status: adopted design requirements, 2026-10-18 (owner: "Our security
should fit the node like a glove. Can't be an after thought."); runtime
protection Not yet proven.** This is the companion to
[AGENTS.md > Security baseline](../../AGENTS.md#security-baseline) and to the
[platform plan's three safety layers](../architecture/platform-plan.md#4-three-safety-layers).
It names what the node protects, what it trusts, and for every threat the
control, the stage that builds it and the test that proves it (§4). Every
stage row of the platform plan carries a security slice that §5 details, so a
stage's Build Record takes its security "Done when" from here. §6 is how the
node keeps up with vulnerabilities; §7 is AISecurity's place (ADR 0009). The
owner's decisions S1 to S4 of 2026-10-18 are recorded in
`docs/build-records/2026-10-18-security-plan.md`; S5 is open (§8). Facts
about other repositories carry the revision they were read at (§10).

## 1. Highest responsibility

Funds and keys first; then the owner's privacy; then the node's availability
(AGENTS.md §1). A failed update, a hostile peer, a poisoned help page or a
misled model must never cost the node its funds or expose its keys. This is
an engineering obligation with tests, not a promise that every attack is
covered: §3 says what is assumed, §9 what is proven today, which is nothing
on a node yet.

## 2. Assets and required protection

| Asset | Where it lives | Required protection |
|---|---|---|
| The wallet seed | Shown once at wallet creation; kept by the owner off the node | Never stored readable on the node; never in a log, response, event, backup or agent context; the restore drill proves seed plus SCB suffice (FUND-02) |
| LND's channel database and channel state | LND's data volume | Never restored from a backup: an old state can lose that channel's funds; owned by LND's ID range only; copied for forensics, never for restore |
| The static channel backup (SCB) | Written off the node on every channel change | Encrypted before it leaves; a UUID-identified destination; a backup counts only once restored (FUND-01, FUND-02, FUND-04) |
| LND's macaroons, TLS key and wallet unlock | LND's volume; the control plane's secrets store | One macaroon per client with the least caveats; never on a command line, in a unit file, in git, in a log or an event (SEC-01 to SEC-03); the unlock-after-reboot question is the plan's G9 |
| bitcoind's `rpcauth` credentials; Tor's control authentication | Per-client static credentials (ADR 0005) | Per client; the private network only; `rpcwhitelist`; no password file for Tor's control port |
| The owner's sign-in, step-up secret and sessions | The control plane | Authentication fails closed (EXEC-05); step-up for every funds move; one approval store with expiry (HEAL-07) |
| The release signing key and its offline spare | CI; offline | D6 and D7; the node verifies before staging an update |
| The release set: image, container digests, settings, migrations | GitHub's registry; the node's two deployments | Signed and by digest; a tampered, partial or downgraded set is refused (UPG-07, UPG-09); the previous set kept |
| The node's data and its availability | `/var` | Limits per service (PLAT-04); crash loops page the owner (HEAL-10); disk and thermal checks; rollback never touches data |
| The owner's private data: balances, addresses, payment history, peers, chat, AI events, incidents | The control plane's store | Stays on the node; leaves only by the owner's explicit, recorded choice (assistant plan F3); secrets redacted at write time (SEC-01) |
| Agents' mandates and the ledger (stage 9) | The treasury in the control plane | Owner-signed, revocable; hash-chained; reconciled against LND; a disagreement suspends and alerts (agent payments plan §4) |

## 3. What is trusted, and what is not

**Trusted** (assumptions; a claim below rests on them and on nothing else):

- the N150's hardware and firmware, and the kernel of the signed image with
  SELinux enforcing;
- systemd and Podman as shipped in the image, as the enforcers of limits,
  ordering and isolation (ADR 0005, ADR 0007);
- the owner's authenticated account in the app, and the owner's physical
  access to the box;
- GitHub Actions as the build environment and the custody of the signing
  key (D6, D7); the upstream release signatures of Bitcoin Core, LND and Tor
  as the proof of what the images were built from;
- the control plane itself as the one authority (EXEC-04), kept small,
  tested and reviewed under REVIEW.md.

**Not trusted** (modelled as hostile, or as compromisable with limited
damage):

- everything that arrives over the network: peers, gossip, invoices and
  their memos, payment requests, onion traffic, web pages, registries'
  content before verification, and the owner's own LAN;
- what a container computes: bitcoind, LND and Tor are relied on for their
  function, but the compromise of any one is an event the design bounds
  (its own ID range, its own volume, the private network, no secret of
  another's);
- model output, retrieved text, help pages once indexed, the engine's image,
  anything an agent does, the marketplace;
- removable media, and the host of the backup destination;
- a browser session before it is authenticated, and the owner's phone as a
  source of text until the session is;
- this project's own AI sessions: the guard, the sandbox and the gate exist
  because an agent writing the code is not trusted either (AGENTS.md §7).

**Out of scope,** stated so no claim implies it: root compromise of the
host; hardware or firmware implants; a malicious owner; a compromise of
Fedora's or GitHub's supply chain that yields correctly signed, pinned
artefacts; theft of the box while it is powered on. Theft of the powered-off
box is bounded by LND's encrypted wallet and the seed being off the node;
disk encryption at rest is an open decision (S5, §8).

## 4. Threats, controls, owning stage and proof

Every row is **Not yet proven** until its test or drill is seen to pass in
CI or on the N150, and its stage's Build Record says so. "In place" marks
the few controls this repository already runs for its own development.

| # | Threat | Control | Stage | Proof | Status |
|---|---|---|---|---|---|
| T1 | The seed or the wallet is read from disk by another component | The seed is never stored readable; LND's volume is owned by LND's range; no secret path exists in any other container or sandbox | 4, 8 | A negative test from the Tor, engine and agent containers: the wallet path is unreadable (gap G5 for the sandbox) | Not yet proven |
| T2 | An old channel state is restored after a failure | `channel.db` is never restored; restore means seed plus SCB; the restore UI has no path to it | 5 | The restore drill on clean hardware, test network (FUND-02); a `channel.db` restore attempt refused | Not yet proven |
| T3 | RPC, gRPC or REST reachable off the node | Services bind to the private network's fixed addresses (D14); `rpcwhitelist`; inbound closed except 8333, 9735 and 443 | 2, 4 | A port scan from the LAN in the stage drill; a whitelist refusal test | Not yet proven |
| T4 | A credential reaches a log, a response, an event or an agent's context | `secrecy` types; the redaction filter at every sink: AISecurity's sensitive-data and key-filter detectors (§7); SEC-01, SEC-02 | 7, 8 | Tests that feed a macaroon, an extended private key, a seed phrase and a password through each sink | Not yet proven |
| T5 | An unauthenticated, replayed or forged API action | Authentication fails closed (EXEC-05); step-up and one approval store with expiry and the instance hash (HEAL-07; assistant plan A4); origin checks; constant-time comparison (EXEC-07) | 7 | The register's tripwires as tests; a replay test | Not yet proven |
| T6 | An external value reaches a shell or a command line | No shell anywhere; argv only; a closed action enum; no credential on a command line (EXEC-01, ADR 0005) | 7 | The AI-01 probe class rewritten for the new executor; `cargo mutants` on the refusal paths | Not yet proven |
| T7 | A tampered, partial or downgraded update | The signature is verified before staging; sets by digest; a set with a missing part refuses to start; downgrade refused (UPG-07, UPG-09); migrations end automatic rollback | 6 | The stage 6 drill: a broken image, a tampered manifest, a downgrade attempt | Not yet proven |
| T8 | A malicious or vulnerable dependency or image | Every dependency and image pinned, lockfiles committed; cargo-deny; verified upstream builds; no third-party prebuilt node images (plan §4.2); the engine image by digest after the gate (ADR 0008) | all; CI | The gate on every pull request; the weekly audit and the image scan (§6, S2, S3) | Partly in place: cargo-deny and gitleaks on pull requests and pushes to `main`; nothing scheduled |
| T9 | A known vulnerability stays unpatched on a node | The intake loop (§6): sources, the weekly audit, the release cadence | process | TEST-05's stale-run warning; every release's Build Record names the advisories it carries | Not in place |
| T10 | Prompt injection through retrieved text, a peer alias, an invoice memo or a help page | Model output is data; typed intents under a grammar; templates fill from the owner's words and Rust's recommendations only; AISecurity's prompt-injection detector as a signal that holds the turn | 8 | The eval gate's injection probes (assistant plan C1); a held turn is an event | Not yet proven |
| T11 | The assistant or an agent gains authority | The sandbox boundary (G5); no key, macaroon or signing in any sandbox; one executor; every funds move through the approval store; the emergency stop cancels in-flight calls (AI-01 to AI-03) | 8, 9 | The sandbox boundary tests; the stop tests | Not yet proven |
| T12 | An agent or the assistant reaches cloud metadata, the LAN or an arbitrary host | Egress denied by default; an allow-list per mandate; every fetch in the control plane refuses 169.254.0.0/16, the RFC 1918 ranges and loopback except its own API; no URL shorteners, no open resolvers (baseline; the owner's note of 2026-10-12) | 8, 9 | Network tests from inside the sandbox; a fetch-to-metadata test | Not yet proven |
| T13 | A test acts on a real system | `safe-run.sh`; regtest and signet; tests behind an egress allow-list with dry-run execution; no mainnet amount before D4 and the plan's §6 | all | The gate runs inside `safe-run.sh`; a test that reaches the network fails | Partly in place: `safe-run.sh` and the sandbox exist |
| T14 | The brake needs a password, or the owner is locked out | The emergency stop needs no password and resume needs step-up (AI-03); recovery from a failed update without a shell (G8, UPG-03) | 6, 8 | The stop tests; the rollback drill ends in the UI | Not yet proven |
| T15 | A crash loop, resource exhaustion or a full disk | Limits in the units (PLAT-04); crash-loop paging (HEAL-10); disk and thermal checks; bounded restarts (ADR 0005) | 2 | Induced faults in the stage 2 drill | Not yet proven |
| T16 | The backup destination is compromised or lost | The SCB is encrypted before it leaves; a UUID-identified destination; the last success shown; a missing backup alarms | 5 | The restore drill; a stale-backup alarm test | Not yet proven |
| T17 | Tor's control port or onion keys are abused | Control-port authentication without a password file; onion keys in Tor's range only; LND reaches Tor on the private network | 3 | The stage 3 drill: unauthenticated control refused; keys unreadable from other containers | Not yet proven |
| T18 | A detector or control stops working silently | Absence alarms: heartbeats and last-success times; security health in the status API; the assistant degraded when a detector is missing | 7, 8 | A test that a detector that stops firing is a health finding | Not yet proven |
| T19 | Theft of the powered-off box | LND's wallet encrypted at rest; the seed off the node; the SCB off the node; disk encryption open | 1 | Decision S5 | Open decision |

## 5. The security slice of every stage

Each stage ships the boundary it creates with its controls and negative
tests, and its drill proves them. The platform plan's stage table carries
the short form; this is the detail a stage's Build Record copies.

| Stage | Boundary created | Controls shipped | Negative tests | Added to the drill |
|---|---|---|---|---|
| 1 Platform | The image, the first web page, the first sign-in | Image signed in CI and verified before staging; no secret in the image (the hygiene check); SELinux enforcing; inbound closed except the node's published ports; the setup page's TLS (D10) and sign-in (D11); no shell login enabled by default (§8) | A tampered image refused; the image scanned for secrets and listening services; a wrong sign-in refused and rate-limited | The rollback drill includes a tampered update |
| 2 Bitcoin Core | RPC and ZMQ | `rpcauth` per client; `rpcwhitelist`; RPC on the private network only; the build verified from signed checksums; the data volume owned by its range; limits in the unit | A whitelist refusal; a wrong credential refused; the port unreachable from the LAN; the unit's limits enforced | Induced faults, then a port scan from the LAN |
| 3 Tor | The control port, the onion keys | Control-port authentication without a password file; onion keys in Tor's range; no exit; LND to Tor on the private network | Unauthenticated control refused; the keys unreadable from other containers | Restart, reachability, scan |
| 4 LND | The wallet, the macaroons | The seed shown once and never stored readable; one macaroon per client with the least caveats, in the secrets store; TLS; wallet data in LND's range; G9 decided before mainnet | A read macaroon cannot pay; the wallet path unreadable from Tor and the engine; no macaroon in any log or event | The plan's §6 step 1 |
| 5 Backup and restore | The backup path off the node | The SCB encrypted before it leaves; a UUID destination; the stale-backup alarm; no path restores `channel.db` | The restore drill; the alarm fires on a missed backup; a `channel.db` restore refused | The restore drill on clean hardware |
| 6 Updates | The update path | Signature and digest verification; a partial set refuses to start; downgrade refused; migrations end rollback; the advisory release cadence (§6); the owner told in plain words | Tampered and downgraded sets refused; a broken set rolls back by itself | The §4.1 drill plus a tampered update |
| 7 Backend API and channel management | The API, the executor, the secrets store | One authority; authentication fails closed; step-up and one approval store; no shell and a closed action enum; the network-trust helper (EXEC-07); rate limits; the redaction filter at every sink (§7, S1's first consumer); security health in the status API; runbooks as code; Lightning guardrails with immutable safety limits | The register's EXEC and SEC tripwires; `cargo mutants` on refusal and validation paths; a replay test | The plan's §6 steps 2 and 3, plus an authentication and replay drill |
| 8 Frontend, then the assistant | The browser session, the model, the sandbox | Content security policy and session cookie flags; step-up prompts that name the exact action; the engine with no egress; the sandbox boundary (G5); the emergency stop; metadata and LAN ranges refused in every fetch; the eval gate's injection probes; `data_egress` events for anything that leaves (assistant plan B5) | G5's list; the stop tests; a fetch-to-metadata test; the eval gate | G5, and one action template end to end behind step-up |
| 9 Treasury and agent payments | Agents, mandates, payments | The agent payments plan's §4.3; detectors' signals hold payments; the "who holds what" table enforced by deployment; the ledger reconciled | Forged, replayed, revoked and expired mandates refused; a divergence suspends and alerts | That plan's drill |
| 10 Marketplace | Peers and listings | No path to LND but the treasury; signed listings and reviews; untrusted text never ingested into the assistant's stores without a reviewed feature (AI-02) | Forged and replayed items refused; a wash-trading ring scored low | That plan's drill |

Cross-cutting, from stage 1 on: the intake loop (§6), AISecurity as a pinned
dependency (§7), and the project's own controls for its AI sessions, which
already run (§9).

## 6. Keeping up: the intake loop (S2, S3)

Advisories appear on their own clock, not the code's. Today every check in
CI runs on a pull request or a push to `main` and nothing is scheduled, which is the
failure the lessons register records in SEC-06 and TEST-05 and which
AISecurity fixed with a weekly workflow. The loop below is decided (S2, S3);
its CI parts are the next task, a control change.

**Sources, and who reads them**

| Source | Covers | Read by |
|---|---|---|
| RustSec and GitHub's advisories through a merged source (OSV), per SEC-06 | The control plane's Cargo dependencies, including `security-core` and its tree | The weekly CI audit (today: cargo-deny reads RustSec only, on pull requests and pushes to `main`) |
| GitHub's advisories for the actions CI uses | The build pipeline | The weekly CI audit |
| Fedora's security advisories for the packages in the pinned base image; a scan of the built images (S3) | The OS image and the container images | The image workflow after a build, weekly on a schedule; the scanner is adopted only after the inspection AGENTS.md §2 requires (source, provenance, licence, maintenance, dependency tree, side effects) and runs in CI only, never on a node |
| Bitcoin Core's security advisories and release notes; LND's releases and security notices; Tor's announcements; Podman's and the kernel's advisories; llama.cpp's releases | The node's services | The owner's weekly loop until UPG-05's release-notes reader exists on the node |
| AISecurity's own weekly audit | The detectors' tree | AISecurity's CI, emailing the owner |
| The owner's AI Security Watch notes | New attack patterns and guidance | Disposed weekly: each item becomes a rule, a backlog entry or a recorded "not for us" |

**Cadence and alarm**

- A scheduled weekly CI run of the dependency audit against the merged
  source, and of the image scan, with a failure that emails the owner (as
  AISecurity's `supply-chain-weekly.yml` does). The local gate warns when
  the last scheduled run is older than eight days (TEST-05).
- **The release cadence for advisories,** an explicit and reversible owner
  setting, chosen here as the default: a critical advisory in bitcoind, LND,
  Tor, Podman, the kernel or the control plane's dependencies cuts a release
  set within 7 days; a high one within 30 days; and at least one release set
  ships each month, so the base image's security updates are never older
  than a month on a node. Each release's Build Record names the advisories it
  carries. Costs: a monthly reboot for every node (every release reboots,
  ADR 0006), and the owner's time.
- The owner's weekly loop in `BUILD-PROCEDURE.md` gains the advisory check
  when the CI task lands; the quarterly audit stays for end-of-life dates.
- Dependency bots opening pull requests are not used: a pin would change on
  a bot's clock and each bump is a supply-chain event. Bumps are deliberate,
  weekly, with the audit's evidence in a Build Record.
- Two items from the owner's note of 2026-10-12 are requirements from today:
  every fetch tool refuses cloud metadata and LAN ranges in the control
  plane, never in a prompt (T12); tests run behind an egress allow-list with
  dry-run execution and never post, trade or pay outside a sandbox (T13).

## 7. AISecurity's place (S1)

- **Role: detectors signal; the platform enforces.** AISecurity's detectors
  contribute signals; systemd, Podman, the sandbox and the control plane
  enforce. The node sets the floor: a signal holds the action, fails closed
  and alarms. The app's own posture, "monitor first, block second" with the
  user's dial, does not apply on the node. This is the split Rikuri-PI
  adopted (its threat model §4: "AISecurity evaluates and translates …
  detectors only contribute signals") and the agent payments plan kept.
- **Form: a pinned Git dependency, not a vendored fork.** The control plane
  links the `security-core` crate from `/home/junc/AISecurity`'s repository
  by commit, with `default-features = false` so the `wasm-plugins` feature
  and its wasmtime engine stay out, with cargo-deny over the resulting tree,
  with the crate's own tests (`tests/cross_validation.rs`,
  `tests/integration/test_cases.json`) run in our gate, and with an absence
  alarm per detector the node uses (T18). The previous node vendored a copy
  instead (`vendor/security-core/PROVENANCE.md` at `3bbbe392`): a fork
  re-synced by hand with wasmtime stripped by hand; this design gets the same
  result without a fork. The Linux daemon, the TUI, the macOS app, the MCP
  server and the intent hook are not used on the node.
- **Dependency cost, proven before any code.** The crate pulls `reqwest`,
  `rustls`, `rusqlite` with bundled SQLite, `aes-gcm` and more
  (`crates/security-core/Cargo.toml` at `12ff2e8`). The linking task compares
  `cargo tree` of the control plane with and without the crate and needs
  cargo-deny green on the result. If the tree is too wide, the fallback is a
  `detectors` feature in AISecurity that builds the pattern modules alone, a
  change there with its own Build Record.
- **Detectors the node uses, by stage.** Stage 7: sensitive data and key
  filter, as the redaction filter at every sink (T4; the assistant plan's
  B2 and B5). Stage 8: prompt injection, holding the turn (T10); model
  verifier only if it does not duplicate AI-05's own checksum-on-load (one
  check, not two). Stage 9: command policy, agent policy and the intent
  verifier, screening agents' requests to the treasury. Not used on the node:
  package vulnerabilities and threat feeds (the intake loop runs in CI, and
  the node has no egress for feeds), the vault and the encryption module
  (the control plane's own secrets store).
- **Lockstep.** A change to a detector the node uses is a new pinned commit
  and a Build Record here, through the gate. AISecurity's weekly audit covers
  its tree. The guard files are already kept identical across the two
  repositories.
- **Readiness, read 2026-10-18 at `12ff2e8`.** The Rust core is the complete
  part: 28 modules, with cross-validation and integration tests. The
  implementation plan marks 395 items done and 45 not started, mostly macOS
  UI and Linux notifications. The macOS app is the most finished surface. For the
  Linux daemon the plan's own rows disagree: owner authentication and the
  notification channels are marked done in one phase and not started in an
  earlier one, and the end-to-end notification test is not started. None of
  the Linux daemon is needed by the node.

## 8. Open decisions

- **S5, disk encryption at rest.** Not decided; needed before stage 1's
  install media is final. **A. LUKS sealed to the TPM** (if the N150 has
  TPM 2.0): unattended reboots keep working; cost: a firmware change or a
  moved disk needs the recovery passphrase, and the TPM path must be drilled.
  **B. LUKS with a passphrase typed at boot:** simplest; cost: no unattended
  reboot, so an update at night waits for the owner. **C. None:** the LND
  wallet's own encryption and the seed off the node bound the loss; cost: the
  owner's data, peers and history on a stolen disk. Recommended: A where the
  hardware allows, else B; check Fedora IoT's bootc install path for both.
- **Shell access.** No SSH or console login enabled by default; whether the
  owner may enable SSH behind the app's step-up is a later choice.
- **G9**, LND's wallet unlock after a reboot, stays where the platform plan
  has it.

## 9. Current evidence and limits

What runs today, for this repository's own development: the guard, the OS
sandbox and `safe-run.sh` for AI sessions; on pull requests and pushes to
`main`, gitleaks over the history, the hygiene check, ShellCheck, `cargo fmt`,
clippy, `cargo test` inside `safe-run.sh`, cargo-deny (RustSec advisories,
bans, licences, sources), the guard's tests, and the image's build and
check. Nothing runs on a schedule. No node exists yet (stage 1 and B0), so
every row of §4 is Not yet proven, and the security slice of every stage is
owed by that stage. Evidence from other repositories, such as Rikuri-PI's
OpenShell receipt of 2026-09-28, supports continued qualification and proves
nothing here.

## 10. Sources (read 2026-10-18)

- This repository: `AGENTS.md` (§1, §2, §7), `REVIEW.md`,
  `.agents/workflows/BUILD-PROCEDURE.md` (risk tiers, periodic loops, release
  gate), `docs/architecture/platform-plan.md` (§4, §7, §8),
  `docs/architecture/agent-payments-and-marketplace-plan.md` (§2, §4.3),
  `docs/architecture/assistant-plan.md` (contracts B and C),
  `docs/requirements/lessons-register.md` (EXEC, SEC, UPG, TEST, AI, FUND,
  HEAL, PLAT rules and gap G5), `.github/workflows/{ci,image,claude-guard}.yml`,
  `control-plane/deny.toml`.
- Rikuri-PI: `/home/junc/Rikuri-PI/docs/security/THREAT_MODEL.md` and
  `docs/architecture/adr/0004-foundation-threat-model-assumptions.md` (the
  shape of §2 to §4 here, and the split of §7).
- AISecurity at `12ff2e8` (2026-10-05): `README.md`,
  `docs/AISECIMPLEMENTATION.md`, `.github/workflows/supply-chain-weekly.yml`,
  `SecurityCore/Cargo.toml`, `SecurityCore/crates/security-core/Cargo.toml`
  and `src/`, `SecurityCore/crates/security-linux/src/`.
- The previous repository at `3bbbe392`: `vendor/security-core/PROVENANCE.md`.
- The owner's notes: `/home/junc/Security Briefing/Oct 10, 2026.md`,
  `Oct 11, 2026.md`, `Oct 12, 2026.md` (the "worth doing this week" items;
  the PCI SSC guidance on agents and secrets, approvals, independent
  controls and the separation of data access, outside communication and
  untrusted input).
