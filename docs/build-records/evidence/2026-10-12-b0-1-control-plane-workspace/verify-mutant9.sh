#!/bin/bash
set -u
cd /home/junc/claude-wip/b0/rn || exit 2
S=control-plane/crates/rikuri-control/src/status.rs; M=control-plane/Cargo.toml
keep="$(mktemp -d "$TMPDIR/verify-m9.XXXXXX")"; cp "$S" "$keep/status.rs"; before="$(sha256sum "$S")"
trap 'cp "$keep/status.rs" "$S"' EXIT
echo "== V9: an unwrap and a println in shipped code (report())"
sed -i 's/^pub fn report(started: Started) -> Report {$/&\n    let n: u8 = "7".parse().unwrap();\n    println!("{n}");/' "$S"; grep -n 'parse().unwrap()\|println!' "$S"
scripts/cargo.sh clippy --workspace --all-targets --locked --offline --manifest-path "$M" -- -D warnings > "$keep/v9.out" 2>&1; rc=$?
grep -E '^error' "$keep/v9.out" | sort -u | head -5; echo "clippy exit=$rc"
cp "$keep/status.rs" "$S"; trap - EXIT
after="$(sha256sum "$S")"; echo "$before"; echo "$after"; [ "$before" = "$after" ] && echo "RESTORED byte for byte" || echo "RESTORE FAILED"
git status --short -- "$S"
