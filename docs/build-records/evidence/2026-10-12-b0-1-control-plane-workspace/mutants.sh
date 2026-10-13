#!/bin/sh
# Planted faults, each run against the gate step that must catch it, then the
# files restored byte for byte (checked by sha256). Usage, from the checkout:
#   sh docs/build-records/evidence/2026-10-12-b0-1-control-plane-workspace/mutants.sh
# The backups stay in a folder under TMPDIR, named at the end.
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2
M=control-plane/Cargo.toml
STATUS=control-plane/crates/rikuri-control/src/status.rs
DENY=control-plane/deny.toml
keep="$(mktemp -d "${TMPDIR:-/tmp}/rikuri-mutants.XXXXXX")" || exit 2
cp "$STATUS" "$keep/status.rs"
cp "$DENY" "$keep/deny.toml"
before="$(sha256sum "$STATUS" "$DENY")"
restore() { cp "$keep/status.rs" "$STATUS"; cp "$keep/deny.toml" "$DENY"; }
# A mutant must make its step fail: exit 0 means the gate would have missed it.
verdict() { if [ "$2" -ne 0 ]; then echo "CAUGHT  $1 (exit $2)"; else echo "MISSED  $1 (exit 0)"; fi; }

echo "== mutant 1: an unused variable in report(): clippy with warnings as errors must fail"
sed -i 's/^pub fn report(started: Started) -> Report {$/&\n    let unused = 1;/' "$STATUS"
grep -n 'let unused' "$STATUS"
scripts/cargo.sh clippy --workspace --all-targets --locked --offline --manifest-path "$M" -- -D warnings > "$keep/m1.out" 2>&1
rc=$?
grep -E '^error' "$keep/m1.out" | head -3
verdict "clippy: unused variable" "$rc"
restore

echo "== mutant 2: unknown ranked like healthy: the tests must fail"
sed -i 's/State::Unknown => 1,/State::Unknown => 0,/' "$STATUS"
grep -n 'State::Unknown => 0' "$STATUS"
scripts/quality/safe-run.sh scripts/cargo.sh test --workspace --locked --offline --manifest-path "$M" > "$keep/m2.out" 2>&1
rc=$?
grep -E 'FAILED|panicked|test result' "$keep/m2.out" | head -8
verdict "tests: unknown ranked as healthy" "$rc"
restore

echo "== mutant 3: MIT dropped from the licence allow list: cargo deny must fail"
sed -i '/^    "MIT",$/d' "$DENY"
grep -c '"MIT"' "$DENY"
scripts/cargo.sh deny --manifest-path "$M" --locked check licenses > "$keep/m3.out" 2>&1
rc=$?
grep -E '^error|FAILED|licenses' "$keep/m3.out" | head -3
verdict "deny: a licence outside the allow list" "$rc"
restore

echo "== mutant 4: the syn skip removed: cargo deny bans must fail"
sed -i '/crate = "syn@2.0.119"/d' "$DENY"
grep -c 'syn@2.0.119' "$DENY"
scripts/cargo.sh deny --manifest-path "$M" --locked check bans > "$keep/m4.out" 2>&1
rc=$?
grep -E '^error|FAILED|bans' "$keep/m4.out" | head -3
verdict "deny: a duplicate crate version" "$rc"
restore

after="$(sha256sum "$STATUS" "$DENY")"
if [ "$before" = "$after" ]; then
  echo "restored byte for byte:"
  echo "$after"
else
  echo "RESTORE FAILED:"
  echo "$before"
  echo "$after"
  exit 1
fi
git status --short control-plane
echo "backups and the mutants' full output: $keep"
