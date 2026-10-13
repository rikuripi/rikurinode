#!/usr/bin/env bash
# cargo, with its download cache inside this checkout (owner, D24, 2026-10-12).
# Claude Code's sandbox lets a session write only inside the repository, so
# ~/.cargo is out of reach on purpose and plain `cargo` fails to fetch there.
# Toolchains still come from rustup's own folder, read-only. Crates download
# from the two crates.io hosts the sandbox allows (index.crates.io, static.crates.io).
# Record: docs/build-records/2026-10-12-sandbox-crates-io.md
set -euo pipefail
top="$(git rev-parse --show-toplevel)"
export CARGO_HOME="$top/.cargo-home"
exec cargo "$@"
