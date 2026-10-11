#!/usr/bin/env bash
# The full gate: the same script locally and in CI (.github/workflows/ci.yml),
# so their results cannot drift. Every step must pass; none is skipped.
# Bootstrap steps today; the language's build, lint, type and test steps, the
# smoke script and the debt ratchet join with the first code (AGENTS.md >
# Verification by maturity). Record: docs/build-records/2026-10-10-bootstrap.md
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

SHELLCHECK_VERSION=0.11.0
GITLEAKS_VERSION=8.30.1
step() { printf '\n== %s\n' "$1"; }
fail() { echo "full-gate: $1" >&2; exit 1; }

step "1/7 pinned tools"
command -v python3 >/dev/null || fail "python3 is missing"
sc="$(shellcheck --version 2>/dev/null | sed -n 's/^version: //p')" || true
[ "$sc" = "$SHELLCHECK_VERSION" ] || fail "shellcheck $SHELLCHECK_VERSION required, found '${sc:-none}'"
gl="$(gitleaks version 2>/dev/null)" || true
[ "$gl" = "$GITLEAKS_VERSION" ] || fail "gitleaks $GITLEAKS_VERSION required, found '${gl:-none}'"

step "2/7 AI-session guard: wired to every tool, hooks on; policy as generated; every example and failure mode"
python3 scripts/quality/check_guard_wiring.py || fail "the guard is not wired (above)"
python3 scripts/quality/guard_policy.py --check || fail "the guard policy was edited by hand (above)"
python3 -m unittest discover -s .claude/hooks -p 'test_*.py'

step "3/7 the quality tools' own tests (hygiene, guard wiring, guard policy, test-safety layer)"
python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'

step "4/7 repository hygiene: nothing tracked that belongs on the machine"
python3 scripts/quality/repo_hygiene.py .

step "5/7 shell lint"
shellcheck --severity=style scripts/quality/*.sh scripts/quality/hooks/*

step "6/7 whitespace errors in every tracked file, committed or not"
git diff --check "$(git hash-object -t tree /dev/null)" HEAD
git diff HEAD --check

step "7/7 secret scan of history"
scripts/quality/secret-scan.sh

printf '\nfull-gate: all 7 steps passed\n'
