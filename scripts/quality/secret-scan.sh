#!/usr/bin/env bash
# Secret scan of the checked-out commit's history (BUILD-PROCEDURE.md, Phase 0).
# Usage: secret-scan.sh [repo-dir]   (default: this repository)
#
# Scope is HEAD's history only: without --log-opts gitleaks reads every ref in
# the clone, so one branch's finding would fail every other branch, and the
# result would depend on which remote branches happen to be fetched (found by
# Rikuri-PI's drill, 2026-10-05). -m also scans each merge commit's own diff,
# so a key written while resolving a conflict is found. Values are redacted.
set -euo pipefail
repo="${1:-$(git rev-parse --show-toplevel)}"
config="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)/.gitleaks.toml"
exec gitleaks git "$repo" --config "$config" --redact --verbose --no-banner --exit-code 1 \
  --log-opts="--full-history -m HEAD"
