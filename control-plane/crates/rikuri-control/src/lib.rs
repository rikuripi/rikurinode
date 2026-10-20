//! Rikuri Node's control plane: what the node reports and decides.
//!
//! B0.1 (the skeleton): the status model and the listen policy. B0.2: the
//! node's own certificate authority and HTTPS, the claim code that makes the
//! first person at the console the owner, password sign-in with revocable
//! cookie sessions, CSRF, `Host` and `Origin` checks, a step-up token bound to
//! one action, and the peer-trust helper. No probe of any component exists
//! yet, so every component still reports `unknown`; the interfaces to
//! systemd, Podman, LND and bitcoind, with fakes, come with B0.3.
//! Records: docs/build-records/2026-10-12-b0-1-control-plane-workspace.md,
//! docs/build-records/2026-10-19-b0-2-sign-in.md.

pub mod boot;
pub mod claim;
pub mod config;
pub mod http;
pub mod limiter;
pub mod listen;
pub mod names;
pub mod owner;
pub mod password;
pub mod random;
pub mod serve;
pub mod session;
pub mod state;
pub mod status;
pub mod stepup;
pub mod tls;
pub mod trust;

pub use http::{App, Peer, api_router, plain_router};
pub use serve::{serve_plain, serve_tls};
