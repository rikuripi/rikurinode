# Rikuri Node

A self-hosted Bitcoin and Lightning node built for people who are not system
administrators: a full node on a small x86 machine and a pruned node on a
Raspberry Pi 5, both on Fedora IoT, updated and rolled back as whole images.
The design goal: a failed update must never cost the node or its funds.

**Status: stage 1, the operating system, and B0, the control plane's
skeleton.** This repository holds the engineering process and its gates, the
node's OS image ([image/](image/)), built and checked only in CI, and the
first control plane code ([control-plane/](control-plane/)): a daemon that
serves `GET /api/status` on loopback and reports every component as
`unknown`, because nothing probes the node yet. Nothing here is ready to
run on a node. The
[platform and architecture plan](docs/architecture/platform-plan.md) says how
the node will be built, and which decisions are still the owner's; its
decisions are in [docs/adr/](docs/adr/). The
[lessons register](docs/requirements/lessons-register.md) holds what the
previous node taught: each requirement with the incidents behind it and the
check that must exist.

## How the work is done

- [AGENTS.md](AGENTS.md): the rules every contributor and AI agent follows.
- [.agents/workflows/BUILD-PROCEDURE.md](.agents/workflows/BUILD-PROCEDURE.md):
  the standard work for every change; one Build Record per change in
  [docs/build-records/](docs/build-records/).
- [REVIEW.md](REVIEW.md): how changes are reviewed.

## Working on this repository

Requirements: Python 3.9 or newer, [gitleaks](https://github.com/gitleaks/gitleaks)
8.30.1, [ShellCheck](https://github.com/koalaman/shellcheck) 0.11.0 and
[cargo-deny](https://github.com/EmbarkStudios/cargo-deny) 0.20.2 on `PATH`,
and [rustup](https://rustup.rs): `rust-toolchain.toml` names the Rust
version (1.98.1, with rustfmt and clippy), and rustup installs it on first
use. Install the three tools from their release pages;
`.github/workflows/ci.yml` shows the exact archives and their SHA-256
checksums. AI sessions need Claude Code 2.1.295 or later: older versions
ignore the setting that stops a tool call when the guard times out or fails.

```sh
git config core.hooksPath scripts/quality/hooks   # once per clone
scripts/quality/full-gate.sh                      # the gate CI runs
scripts/quality/safe-run.sh <command>             # any test run on a machine with a live node
scripts/cargo.sh <cargo args>                     # cargo, with its cache in the checkout (never plain cargo)
```

The control plane (`control-plane/`, a Cargo workspace: the `rikuri-control`
library and the `rikuri-control-plane` daemon) builds and tests with
`scripts/cargo.sh … --manifest-path control-plane/Cargo.toml`; the gate runs
its tests inside `safe-run.sh`. The daemon listens on `127.0.0.1:8080`
(`RIKURI_LISTEN` overrides it; only a loopback address is accepted until TLS
and sign-in exist) and logs to stderr at the level `RUST_LOG` sets (default
`info`). On a machine with a live node, run it inside `safe-run.sh`, which
gives it a private loopback.

Logs, runtime state, secrets and machine-specific settings never enter git.
The gate and the pre-commit hook refuse them (AGENTS.md > Never in git).
