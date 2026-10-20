# ADR 0009 — Security built in: a threat model per stage, a weekly intake loop, and AISecurity as a pinned dependency that signals while the platform enforces

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-18 ("for the 4 choices 1 through 4, do as you recommended. Our security should fit the node like a glove. Can't be an after thought."; record `docs/build-records/2026-10-18-security-plan.md`) |
| **Decision** | S1 to S4 of `docs/security/THREAT_MODEL.md`; D17 of `docs/architecture/platform-plan.md` |
| **Supersedes** | Nothing. It gives the security baseline of `AGENTS.md` its threat model and its intake loop |
| **Beside it** | ADR 0002 (the Rust control plane, the one authority), ADR 0005 (systemd enforces, the control plane decides), ADR 0007 (rootful Podman, a range per container), ADR 0008 (the inference engine) |

## Context

The owner asked on 2026-10-18 whether the emphasis on node and AI security
was well defined along the way, with vulnerabilities appearing on their own
clock and the owner's AISecurity repository most complete on macOS. The
assessment found the rules strict and three things undefined. The platform
plan's stage table had a "Delivers" and a "Drill" column and no security
column, so stages 2 to 7 each created a boundary with no named negative
test. The node had no threat model of its own; Rikuri-PI has one, and the
agent payments plan borrowed it by reference. Every security check in CI
ran on pull requests and pushes to `main` only, cargo-deny read RustSec
alone, the
image was never scanned, and the procedure's dependency audit was quarterly,
which is the failure the lessons register records in SEC-06 and TEST-05.
AISecurity was a reuse candidate for stage 9 with no decision on its role,
its form or its timing.

AISecurity, read at `12ff2e8`: a Rust core of 28 detector and policy modules
with cross-validation tests, an optional `wasm-plugins` feature that pulls
wasmtime, a macOS app as the most finished surface, a Linux daemon whose
rows in the implementation plan disagree on what is done. Its own posture is
"monitor first, block second" with the user's dial. The previous node
vendored the core as a fork and stripped wasmtime by hand
(`vendor/security-core/PROVENANCE.md` at `3bbbe392`). Rikuri-PI's adopted
split: the policy service evaluates and translates, detectors only
contribute signals, a qualified backend enforces.

## Decision

- **S4. The node has its own threat model now,** `docs/security/THREAT_MODEL.md`:
  assets, what is trusted and what is not, and for every threat the
  control, the owning stage and the test. Every stage row of the platform
  plan carries a **security slice** the threat model details, and a stage's
  Build Record copies it into its "Done when". A stage whose security tests
  have not been seen to pass has not closed.
- **S1. AISecurity's `security-core` is linked into the control plane as a
  Git dependency pinned by commit,** with `default-features = false`, a
  feature set limited to the detectors the node uses, cargo-deny over the
  resulting tree, the crate's own tests in our gate, and an absence alarm per
  detector. **Its detectors signal; systemd, Podman, the sandbox and the
  control plane enforce.** On the node a signal holds the action and fails
  closed; the app's dial does not apply. First consumer: the redaction filter
  at every sink in stage 7 (the assistant plan's contracts B2 and B5); then
  prompt injection in stage 8 and the policy detectors in stage 9. The
  dependency cost is proven before any code (threat model §7).
- **S2. Advisories are read weekly, and a release follows.** A scheduled
  weekly CI run of the dependency audit against a merged advisory source and
  of the image scan, with a failure that emails the owner; the local gate
  warns on a stale scheduled run (TEST-05). A critical advisory in bitcoind,
  LND, Tor, Podman, the kernel or the control plane's dependencies cuts a
  release set within 7 days, a high one within 30, and at least one set
  ships each month: an explicit, reversible owner setting. No dependency
  bots. The CI parts are the next task, a control change.
- **S3. A scanner for the built images is adopted** after the inspection
  `AGENTS.md` §2 requires for third-party code, and runs in CI only.

## Consequences

- Every stage's Build Record gains security "Done when" items, and every
  drill gains negative tests. The cost is paid per stage, not at the end.
- The control plane's dependency tree grows by `security-core`'s; the
  linking task measures it and cargo-deny must stay green, with a named
  fallback (a `detectors` feature upstream) if it is too wide.
- A change to a detector the node uses is a release here: a new pinned
  commit and a Build Record through the gate. AISecurity and this repository
  move in lockstep, as the guard files already do.
- Every node reboots at least monthly, because every release reboots
  (ADR 0006), and the owner's weekly loop gains an advisory check.
- The security baseline of `AGENTS.md` points at the threat model; the rules
  themselves do not change.

## Rejected

- **The Linux daemon beside the control plane.** A second process with its
  own egress and authentication to govern, for detectors the control plane
  can call as functions.
- **Defer AISecurity to stage 8.** The redaction filter would be written
  twice, once in stage 7 and once when the crate arrives.
- **Vendor the crate** as the previous node did: a fork re-synced by hand,
  with manual edits that drift.
- **Let the app's "monitor first" dial decide on the node.** A funds action
  flagged by a detector cannot proceed because a dial says observe.
- **Quarterly audits only.** Advisories wait up to three months.
- **Dependency bots.** Pins change on a bot's clock; each bump is a
  supply-chain event without a Build Record.
- **The threat model at stage 7.** Five stages would build boundaries
  without it.

## Sources (read 2026-10-18)

- `docs/security/THREAT_MODEL.md` §10 lists every file read, with revisions.
- AISecurity at `12ff2e8`: `SecurityCore/crates/security-core/Cargo.toml`
  (the `wasm-plugins` feature and its note), `docs/AISECIMPLEMENTATION.md`,
  `.github/workflows/supply-chain-weekly.yml`.
- Rikuri-PI: `docs/security/THREAT_MODEL.md` §4 ("AISecurity evaluates and
  translates", "detectors only contribute signals").
- The previous repository at `3bbbe392`: `vendor/security-core/PROVENANCE.md`.
