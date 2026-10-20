#!/bin/bash
# Verifier's own planted faults (different from the record's mutants.sh). Each file
# is backed up, mutated, the relevant gate step run, then restored from the backup;
# sha256 before and after are printed at the end.
set -u
cd /home/junc/claude-wip/b0/rn || exit 2
M=control-plane/Cargo.toml
L=control-plane/crates/rikuri-control/src/listen.rs
H=control-plane/crates/rikuri-control/src/http.rs
S=control-plane/crates/rikuri-control/src/status.rs
LIB=control-plane/crates/rikuri-control/src/lib.rs
LOCK=control-plane/Cargo.lock
RH=scripts/quality/repo_hygiene.py
FILES=("$L" "$H" "$S" "$LIB" "$LOCK" "$M" "$RH")
keep="$(mktemp -d "$TMPDIR/verify-mutants.XXXXXX")" || exit 2
i=0; for f in "${FILES[@]}"; do cp "$f" "$keep/$i"; i=$((i+1)); done
before="$(sha256sum "${FILES[@]}")"
restore() { local i=0; for f in "${FILES[@]}"; do cp "$keep/$i" "$f"; i=$((i+1)); done; }
trap restore EXIT
verdict() { if [ "$2" -ne 0 ]; then echo "CAUGHT  $1 (exit $2)"; else echo "MISSED  $1 (exit 0)"; fi; }
tests() { scripts/quality/safe-run.sh scripts/cargo.sh test -p rikuri-control --locked --offline --manifest-path "$M" > "$1" 2>&1; echo $?; }

echo "== V1: listen accepts unspecified addresses too (0.0.0.0, [::])"
sed -i 's/if addr.ip().is_loopback() {/if addr.ip().is_loopback() || addr.ip().is_unspecified() {/' "$L"; grep -c 'is_unspecified' "$L"
rc=$(tests "$keep/v1.out"); grep -E 'FAILED|panicked at|test result' "$keep/v1.out" | head -5; verdict "tests: non-loopback accepted" "$rc"; restore

echo "== V2: Cache-Control no-store becomes no-cache"
sed -i 's/"no-store"/"no-cache"/' "$H"; grep -c 'no-cache' "$H"
rc=$(tests "$keep/v2.out"); grep -E 'FAILED|panicked at|test result' "$keep/v2.out" | head -5; verdict "tests: cache header weakened" "$rc"; restore

echo "== V3: unknown carries checked_unix 0 instead of null (EVID-02)"
sed -i 's/checked_unix: None,/checked_unix: Some(0),/' "$S"; grep -c 'Some(0)' "$S"
rc=$(tests "$keep/v3.out"); grep -E 'FAILED|panicked at|test result' "$keep/v3.out" | head -8; verdict "tests: unknown time as 0" "$rc"; restore

echo "== V4: no components folds to healthy"
sed -i 's/.unwrap_or(State::Unknown)/.unwrap_or(State::Healthy)/' "$S"; grep -c 'unwrap_or(State::Healthy)' "$S"
rc=$(tests "$keep/v4.out"); grep -E 'FAILED|panicked at|test result' "$keep/v4.out" | head -5; verdict "tests: empty is healthy" "$rc"; restore

echo "== V5: a direct dependency unpinned (axum =0.8.9 -> 0.8.9): does any gate step notice?"
sed -i 's/version = "=0.8.9"/version = "0.8.9"/' "$M"; grep -n 'axum = ' "$M"
scripts/cargo.sh fetch --locked --manifest-path "$M" > "$keep/v5a.out" 2>&1; a=$?; tail -1 "$keep/v5a.out"
scripts/cargo.sh clippy --workspace --all-targets --locked --offline --manifest-path "$M" -- -D warnings > "$keep/v5b.out" 2>&1; b=$?; tail -1 "$keep/v5b.out"
scripts/cargo.sh deny --manifest-path "$M" --locked check > "$keep/v5c.out" 2>&1; c=$?; tail -1 "$keep/v5c.out"
echo "fetch=$a clippy=$b deny=$c"; verdict "unpinned direct dependency" $(( a | b | c )); restore

echo "== V6: a checksum in Cargo.lock altered"
python3 -I - "$LOCK" <<'PY'
import sys
p=sys.argv[1]; t=open(p).read(); k='checksum = "'; i=t.index(k)+len(k)
c=t[i]; t=t[:i]+('1' if c!='1' else '2')+t[i+1:]; open(p,'w').write(t)
print("altered checksum line:", t[t.rfind('\n',0,i)+1:t.index('\n',i)])
PY
scripts/cargo.sh fetch --locked --manifest-path "$M" > "$keep/v6.out" 2>&1; rc=$?; grep -E '^error' "$keep/v6.out" | head -3; verdict "cargo fetch --locked: altered lock checksum" "$rc"; restore

echo "== V7: the hygiene rule looks for 'targets' instead of 'target'"
sed -i 's/if seg == "target" and/if seg == "targets" and/' "$RH"; grep -c '"targets"' "$RH"
python3 -m unittest discover -s scripts/quality/tests -p 'test_repo_hygiene.py' > "$keep/v7.out" 2>&1; rc=$?; grep -E '^FAIL:|^Ran|^FAILED' "$keep/v7.out"; verdict "hygiene tests: rule broken" "$rc"; restore

echo "== V8: an unformatted line in lib.rs"
sed -i 's/^pub mod http;$/pub  mod   http;/' "$LIB"; grep -c 'pub  mod' "$LIB"
scripts/cargo.sh fmt --all --check --manifest-path "$M" > "$keep/v8.out" 2>&1; rc=$?; grep -E '^Diff in' "$keep/v8.out" | head -2; verdict "cargo fmt --check" "$rc"; restore

trap - EXIT
after="$(sha256sum "${FILES[@]}")"
echo "== sha256 before:"; echo "$before"; echo "== sha256 after:"; echo "$after"
if [ "$before" = "$after" ]; then echo "RESTORED byte for byte"; else echo "RESTORE FAILED"; fi
echo "== git status of the touched files (expect 'A ' only, no working-tree change):"; git status --short -- "${FILES[@]}"
echo "backups and full outputs: $keep"
