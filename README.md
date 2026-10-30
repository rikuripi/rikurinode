# Rikuri Node

A self-hosted Bitcoin and Lightning node built for people who are not system
administrators: a full node on a small x86 machine and a pruned node on a
Raspberry Pi 5, both on Fedora IoT, updated and rolled back as whole images.
The design goal: a failed update must never cost the node or its funds.

**Status: stage 1, the operating system, and B0, the control plane's
skeleton.** This repository holds the engineering process and its gates, the
node's OS image ([image/](image/)), built and checked only in CI and
published, signed, when the owner starts it
([runbook](docs/runbooks/publish-os-image.md)); its VM drill shows the node's
own update command refusing an unsigned image and staging a signed one; a USB
installer, built with each publish, that installs the node on a machine's one
internal disk with no network, proven in a CI VM
([runbook](docs/runbooks/install-node.md)); and the
first control plane code ([control-plane/](control-plane/)): a daemon that
serves its API over HTTPS from a certificate authority it makes at first
start, takes a claim code from the console to make the first person the
owner, signs the owner in with a password and a revocable session, and
reports every component as `unknown`, because nothing probes the node yet.
Nothing here is ready to run on a node. The
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
its tests inside `safe-run.sh`. The daemon serves its API over HTTPS on
`127.0.0.1:8443` (`RIKURI_LISTEN`) with a certificate signed by the node's own
CA, both made at first start under `RIKURI_STATE_DIR` (default
`/var/lib/rikuri/control-plane`, a 0700 folder of 0600 files: the keys, the
hashes of the claim code and the owner's password, the sessions). A plain
listener (`RIKURI_HTTP_LISTEN`, off unless set) serves only the CA
certificate at `/ca.crt` and a redirect to HTTPS. `RIKURI_NAMES` lists the
names a request may use for the node (`localhost` always may); any other
`Host` is refused. At its first start the daemon logs a claim code; the first
person to send it with a password becomes the owner, and only
`rikuri-control-plane rearm-claim`, run at the console, arms another once it
expires or is retired. Logs go to stderr at the level `RUST_LOG` sets
(default `info`). On a machine with a live node, run it inside `safe-run.sh`,
which gives it a private loopback.

Logs, runtime state, secrets and machine-specific settings never enter git.
The gate and the pre-commit hook refuse them (AGENTS.md > Never in git).
