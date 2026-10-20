#!/bin/sh
# The daemon through its real entry point, inside the test-safety layer
# (a private loopback: nothing on this machine is reached). Usage:
#   scripts/quality/safe-run.sh sh docs/build-records/evidence/2026-10-12-b0-1-control-plane-workspace/probe-daemon.sh <path to rikuri-control-plane>
# Shows one legitimate use (start, GET /api/status, 404, 405, stop on
# SIGTERM), two refusals (a non-loopback address, a host name), a bad
# RUST_LOG said rather than swallowed, and a stop on SIGINT.
set -u
bin="$1"
log="${TMPDIR:-/tmp}/rikuri-probe.$$.log"

echo "== 1. legitimate use: start on loopback, GET /api/status, 404, 405, SIGTERM"
"$bin" 2> "$log" &
pid=$!
sleep 1
echo "--- GET /api/status (status line, headers, body; HTTP's CR LF shown as LF):"
curl -sS -i http://127.0.0.1:8080/api/status | tr -d '\r'
echo
echo "--- GET /nope:"
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/nope
echo "--- POST /api/status:"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8080/api/status
kill -TERM "$pid"
wait "$pid"
echo "daemon exit=$?"
echo "--- daemon log:"
cat "$log"

echo "== 2. refused: a non-loopback address"
RIKURI_LISTEN=0.0.0.0:8080 "$bin"
echo "exit=$?"

echo "== 3. refused: a host name"
RIKURI_LISTEN=localhost:8080 "$bin"
echo "exit=$?"

echo "== 4. a bad RUST_LOG is said, not swallowed; SIGINT stops it"
RUST_LOG='not a filter[[' "$bin" &
pid=$!
sleep 1
kill -INT "$pid"
wait "$pid"
echo "exit=$?"
