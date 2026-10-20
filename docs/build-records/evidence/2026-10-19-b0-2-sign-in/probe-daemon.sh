#!/bin/sh
# The daemon through its real entry point, inside the test-safety layer (a
# private loopback: nothing on this machine is reached). Build the daemon first:
# `cargo test` does not relink it, so after a code change the binary is stale.
#   scripts/cargo.sh build --workspace --locked --offline --manifest-path control-plane/Cargo.toml
#   scripts/quality/safe-run.sh sh docs/build-records/evidence/2026-10-19-b0-2-sign-in/probe-daemon.sh control-plane/target/debug/rikuri-control-plane
# Shows: the identity and the claim code at first start; the CA certificate
# fetched in the clear and a client that trusts it reading the API over TLS;
# a client without it refused at the handshake; the plain listener answering
# an API path with a redirect; the console re-arm and the claim with its
# code; a session read back; a rebinding Host refused; the status open on
# loopback; the re-arm refused once claimed; a clean stop on SIGTERM; a bad
# listen address refused. Claim codes are masked in the output.
set -u
bin="$1"
scratch="${TMPDIR:-/tmp}/rikuri-probe.$$"
mkdir -p "$scratch"
export RIKURI_STATE_DIR="$scratch/state"
export RIKURI_LISTEN=127.0.0.1:18443
export RIKURI_HTTP_LISTEN=127.0.0.1:18080
export RIKURI_NAMES=rikuri01.local
log="$scratch/daemon.log"
jar="$scratch/cookies"
ca="$scratch/ca.crt"
masked=""
mask() { if [ -n "$masked" ]; then sed "$masked"; else cat; fi; }
tls() { curl -sS --cacert "$ca" --resolve "localhost:18443:127.0.0.1" "$@"; }

echo "== 1. first start: the identity and an armed claim code (masked)"
"$bin" 2> "$log" &
pid=$!
sleep 1
first=$(sed -n 's/.*claim_code=\([A-Z0-9-]*\).*/\1/p' "$log" | head -1)
[ -n "$first" ] && masked="s/$first/[CODE-1]/g"
grep -E "node identity|claim code armed|listener" "$log" | mask

echo "== 2. the CA certificate in the clear, then the API over TLS from a client that trusts it"
curl -sS -i -o "$scratch/ca.headers" http://127.0.0.1:18080/ca.crt
tr -d '\r' < "$scratch/ca.headers" | sed -n '1p;/^content-type/Ip;/^content-disposition/Ip'
curl -sS http://127.0.0.1:18080/ca.crt > "$ca"
head -1 "$ca"; tail -1 "$ca"
echo "--- GET /api/setup:"
tls -i https://localhost:18443/api/setup | tr -d '\r' | sed -n '1p;/^cache-control/Ip;/^{/p'
echo

echo "== 3. a client without the CA cannot complete the handshake"
refused=$(curl -sS --resolve "localhost:18443:127.0.0.1" -o /dev/null https://localhost:18443/api/setup 2>&1)
rc=$?
printf '%s\n' "$refused" | head -1
echo "curl exit=$rc (60 is a certificate problem)"

echo "== 4. the plain listener answers an API path with a redirect, never the API"
curl -sS -i -X POST -H 'Content-Type: application/json' -d '{"code":"x","password":"y"}' http://127.0.0.1:18080/api/claim | tr -d '\r' | sed -n '1p;/^location/Ip'

echo "== 5. the console re-arms the claim (a new code, masked); the old one is dead"
rearm=$("$bin" rearm-claim)
echo "rearm exit=$?"
code=$(printf '%s\n' "$rearm" | sed -n 's/^claim code: //p')
masked="$masked;s/$code/[CODE-2]/g"
printf '%s\n' "$rearm" | mask
echo "--- the first code, refused (401):"
tls -o /dev/null -w '%{http_code}\n' -X POST -H 'Origin: https://localhost' -H 'Content-Type: application/json' \
  -d "{\"code\":\"$first\",\"password\":\"correct horse battery staple\"}" https://localhost:18443/api/claim

echo "== 6. the claim with the console's code: the owner is made and signed in"
tls -i -c "$jar" -X POST -H 'Origin: https://localhost' -H 'Content-Type: application/json' \
  -d "{\"code\":\"$code\",\"password\":\"correct horse battery staple\"}" https://localhost:18443/api/claim \
  | tr -d '\r' | sed -n '1p;/^set-cookie/Ip' | sed 's/rikuri_session=[0-9a-f]*/rikuri_session=[SESSION]/'
echo "--- GET /api/setup after the claim:"
tls https://localhost:18443/api/setup; echo
echo "--- GET /api/session with the cookie (csrf masked):"
tls -b "$jar" https://localhost:18443/api/session | sed 's/"csrf_token":"[0-9a-f]*"/"csrf_token":"[CSRF]"/'; echo
echo "--- DELETE /api/session without the CSRF token (403):"
tls -b "$jar" -o /dev/null -w '%{http_code}\n' -X DELETE -H 'Origin: https://localhost' https://localhost:18443/api/session
echo "--- a second claim (409):"
tls -o /dev/null -w '%{http_code}\n' -X POST -H 'Origin: https://localhost' -H 'Content-Type: application/json' \
  -d "{\"code\":\"$code\",\"password\":\"correct horse battery staple\"}" https://localhost:18443/api/claim

echo "== 7. a Host that is not this node (421); the status open to loopback (200) and its first line"
tls -o /dev/null -w '%{http_code}\n' -H 'Host: evil.example' https://localhost:18443/api/setup
tls -w '\n%{http_code}\n' https://localhost:18443/api/status | sed -n '1s/^\(.\{80\}\).*/\1.../p;2p'

echo "== 8. the re-arm is refused once the node is claimed"
"$bin" rearm-claim
echo "rearm exit=$?"

echo "== 9. the state folder: a 0700 folder of 0600 files"
stat -c '%A' "$RIKURI_STATE_DIR"
find "$RIKURI_STATE_DIR" -mindepth 1 -maxdepth 1 -type f -printf '%M %f\n' | sort -k2

echo "== 10. SIGTERM: a clean stop"
kill -TERM "$pid"
wait "$pid"
echo "daemon exit=$?"
tail -3 "$log" | mask

echo "== 11. a bad listen address is refused before anything binds"
bad=$(RIKURI_LISTEN=localhost:1 "$bin" 2>&1)
rc=$?
printf '%s\n' "$bad" | mask
echo "exit=$rc"
rm -rf "$scratch"
