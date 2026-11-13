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
installer, built with each publish, that installs the node with no network on
the internal disk the owner picks, proven in a CI VM and on the N150
([runbook](docs/runbooks/install-node.md)); and the
first control plane code ([control-plane/](control-plane/)): a daemon that
serves its API over HTTPS from a certificate authority it makes at first
start, takes a claim code from the console to make the first person the
owner, signs the owner in with a password and a revocable session, and
reports every component as `unknown`, because nothing probes the node yet.
The OS image builds the control plane in and runs it as a service of its own
user, open to the LAN on 80 and 443 and answering as `rikurisetup.local` over
mDNS on its physical interfaces only (never on a container bridge), with a certificate that names that name and the node's current address,
and a claim screen on the node's second
console (Ctrl+Alt+F2) that shows its address, its CA fingerprint and, on
Enter, a claim code. A browser on the same network opens the node's first
setup pages ([ui/](ui/), Svelte, built in CI and compiled into the control
plane): in the clear, a page that installs the node's certificate on that
device; then, over HTTPS trusting only that certificate, a page that shows the
connection is private and asks the owner to compare the browser's fingerprint
with the claim screen's, then leads on: to the claim, where the owner types the
code and chooses a password; to sign-in; and to a page that says the node is
theirs: the SetupHub, with the node's UUID, given at the claim, and each step
of setup read from the node's real state (done, next, or with a later update),
and sign-out. Naming the node comes next; the rest of setup is still to come.
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
checksums. The setup pages build and render in Docker, from images pinned
by digest (`scripts/quality/ui.sh`); outside CI it refuses to start containers
unless `RIKURI_UI_LOCAL=1` says that machine's Docker is not a live node's, so
on the live node's machine the gate stops at that step and CI's run is the
reference. AI sessions need Claude Code 2.1.295 or later: older versions
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
certificate at `/ca.crt`, the certificate page at `/` with its files, and
a redirect to HTTPS for everything else; over HTTPS the secure page answers at
`/` and `/setup`. The pages are embedded in the binary at build time from
`ui/dist` (`scripts/quality/ui.sh build`, in pinned Node and Playwright images
only, never on the machine itself; `RIKURI_UI_DIR` names another `ui/`). The node's
name is its static hostname, `<name>.local`, read from `/etc/hostname` at start,
on each of the daemon's 60 s looks and after a rename; `RIKURI_NAMES` adds
other names (`localhost` always may be used); any other `Host` is refused. A
signed-in owner renames the node with `PUT /api/node/name`: the daemon asks
systemd-hostnamed over the system bus, which a polkit rule allows for its
user alone, and the new name replaces the old one at once (5c.4b-1). The
server certificate names them, the loopback addresses
and the node's LAN address; the daemon looks at that address again every
60 s and, when it changes, reissues the certificate from the same CA and
serves it to new connections without a restart. At its first start the daemon logs a claim code; the first
person to send it with a password becomes the owner, and only
`rikuri-control-plane rearm-claim`, run at the console, arms another once it
expires or is retired. Logs go to stderr at the level `RUST_LOG` sets
(default `info`). On a machine with a live node, run it inside `safe-run.sh`,
which gives it a private loopback.

Logs, runtime state, secrets and machine-specific settings never enter git.
The gate and the pre-commit hook refuse them (AGENTS.md > Never in git).
