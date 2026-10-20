#!/usr/bin/env bash
# The full gate: the same script locally and in CI (.github/workflows/ci.yml),
# so their results cannot drift. Every step must pass; none is skipped.
# The Rust steps joined with the first code (AGENTS.md > Verification by
# maturity); the smoke script and the debt ratchet are still to come.
# Records: docs/build-records/2026-10-10-bootstrap.md,
# docs/build-records/2026-10-12-b0-1-control-plane-workspace.md
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

SHELLCHECK_VERSION=0.11.0
GITLEAKS_VERSION=8.30.1
CARGO_DENY_VERSION=0.20.2
# The Rust version is spelled once, in rust-toolchain.toml; rustup installs it.
RUST_VERSION="$(sed -n 's/^channel = "\(.*\)"$/\1/p' rust-toolchain.toml)"
CARGO=(scripts/cargo.sh)   # cargo with its cache in the checkout (D24)
MANIFEST=control-plane/Cargo.toml
step() { printf '\n== %s\n' "$1"; }
fail() { echo "full-gate: $1" >&2; exit 1; }

step "1/9 pinned tools"
command -v python3 >/dev/null || fail "python3 is missing"
sc="$(shellcheck --version 2>/dev/null | sed -n 's/^version: //p')" || true
[ "$sc" = "$SHELLCHECK_VERSION" ] || fail "shellcheck $SHELLCHECK_VERSION required, found '${sc:-none}'"
gl="$(gitleaks version 2>/dev/null)" || true
[ "$gl" = "$GITLEAKS_VERSION" ] || fail "gitleaks $GITLEAKS_VERSION required, found '${gl:-none}'"
[ -n "$RUST_VERSION" ] || fail "rust-toolchain.toml names no channel"
rc="$("${CARGO[@]}" --version 2>/dev/null | awk '{print $2}')" || true
[ "$rc" = "$RUST_VERSION" ] || fail "cargo $RUST_VERSION required (rust-toolchain.toml; rustup installs it), found '${rc:-none}'"
cd_="$(cargo-deny --version 2>/dev/null | awk '{print $2}')" || true
[ "$cd_" = "$CARGO_DENY_VERSION" ] || fail "cargo-deny $CARGO_DENY_VERSION required, found '${cd_:-none}'"

step "2/9 AI-session guard: wired to the tools in its matcher, hooks on; policy as generated; every example and failure mode"
python3 scripts/quality/check_guard_wiring.py || fail "the guard is not wired (above)"
python3 scripts/quality/guard_policy.py --check || fail "the guard policy was edited by hand (above)"
python3 -m unittest discover -s .claude/hooks -p 'test_*.py'

step "3/9 the quality tools' own tests (hygiene, guard wiring, guard policy, test-safety layer), and the OS image check's"
python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'
python3 -m unittest discover -s image/tests -p 'test_*.py'

step "4/9 repository hygiene: nothing tracked that belongs on the machine"
python3 scripts/quality/repo_hygiene.py .

step "5/9 shell lint"
shellcheck --severity=style scripts/quality/*.sh scripts/quality/hooks/* scripts/cargo.sh

step "6/9 whitespace errors in every tracked file, committed or not"
git diff --check "$(git hash-object -t tree /dev/null)" HEAD
git diff HEAD --check

step "7/9 secret scan of history"
scripts/quality/secret-scan.sh

step "8/9 Rust: dependencies as locked, formatted, clippy clean (warnings are errors), tests green inside the test-safety layer"
"${CARGO[@]}" fetch --locked --manifest-path "$MANIFEST"
"${CARGO[@]}" fmt --all --check --manifest-path "$MANIFEST"
"${CARGO[@]}" clippy --workspace --all-targets --locked --offline --manifest-path "$MANIFEST" -- -D warnings
# No network inside the layer: --offline makes a missing crate a failure, not a hang.
scripts/quality/safe-run.sh "${CARGO[@]}" test --workspace --locked --offline --manifest-path "$MANIFEST"

step "9/9 Rust dependencies: licences, advisories, bans and sources (control-plane/deny.toml)"
"${CARGO[@]}" deny --manifest-path "$MANIFEST" --locked check

printf '\nfull-gate: all 9 steps passed\n'
