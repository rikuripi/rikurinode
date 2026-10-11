# ADR 0002 — The control plane is written in Rust

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-11 (the plan first recommended Go; the owner chose Rust the same day) |
| **Decision** | D3 of `docs/architecture/platform-plan.md` |

## Context

The control plane decides what "healthy" means, which phase a service is
in, which fix applies and how an upgrade is checked and rolled back, and it
is the assistant's only door to the node: a fixed menu of actions. systemd
and Podman enforce; the control plane decides; the assistant suggests.

## Decision

The control plane is Rust. It talks to LND over LND's gRPC API, with a
client generated from the pinned LND version's protocol files, never by
linking LND in as a library. Thin interfaces over systemd, Podman and LND
keep each backend replaceable: the analysis the owner shared proposed them
for systemd and LND, so the language stays swappable; Podman is added, and
they let each backend be faked in tests.

## Why

- The previous node's control plane is Rust (103 `.rs` files under
  `control-plane/`), and 12 of the lessons register's 90 port candidates
  come from it.
- It already uses LDK's `lightning` crate, and LDK is in the previous
  repository's plans.
- Rikuri-PI is Rust: its foundation crates and gates can be shared.
- The compiler checks that every case of a closed set — the assistant's
  actions, the phase, wizard and upgrade state machines — is handled,
  unless a catch-all arm is written.

## Consequences

- Keeping the LND client current with each LND release is this project's
  work. The previous node's community client, `lnd_grpc_rust`, trails LND:
  its latest version lacks calls LND 0.21.4 has (`XCreateAccount` and
  `SubmitPackage`).
- The seed words and wallet password typed during setup pass through to LND
  and are not kept by the control plane. Whether the wallet password is
  stored on the node for unlocking after a reboot is a later decision (G9 in
  the plan).
- Compiles are slower than Go's.

## Rejected

- Go: Lightning Labs' `lndclient` follows LND's releases, but Go would be a
  third language whose compiler does not check that every case is handled,
  and `lndclient` would bring LND's own code and its dependencies inside the
  control plane's boundary.
- TypeScript: the previous node's dashboard backend broke on runtime upgrades
  through native modules (lessons register, PLAT-03). It stays the
  frontend's language.
