//! Rikuri Node's control plane: what the node reports and decides.
//!
//! B0.1 (the skeleton): the status model, its one HTTP route and the listen
//! policy. No probe of any component exists yet, so every component reports
//! `unknown`, and the route is served over plain HTTP on loopback only. TLS,
//! the claim code, sign-in and sessions come with B0.2; the interfaces to
//! systemd, Podman, LND and bitcoind, with fakes, come with B0.3.
//! Record: docs/build-records/2026-10-12-b0-1-control-plane-workspace.md

pub mod http;
pub mod listen;
pub mod status;

pub use http::{router, serve};
