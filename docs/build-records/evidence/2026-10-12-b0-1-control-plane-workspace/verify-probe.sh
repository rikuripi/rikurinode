#!/bin/sh
# Verifier's own probe of the daemon, run inside safe-run.sh (private loopback).
set -u
bin="$1"
log="${TMPDIR:-/tmp}/verify-probe.$$.log"
start() { "$bin" 2> "$log" & pid=$!; sleep 1; }
stop() { kill -TERM "$pid" 2>/dev/null; wait "$pid"; echo "daemon exit=$?"; }

echo "== A. legitimate: default address; HEAD, OPTIONS, trailing slash, query, upper case, HTTP/1.0, garbage request line"
start
echo "--- HEAD /api/status:"; curl -sS -o /dev/null -w '%{http_code}\n' -I http://127.0.0.1:8080/api/status
echo "--- OPTIONS /api/status:"; curl -sS -o /dev/null -w '%{http_code}\n' -X OPTIONS http://127.0.0.1:8080/api/status
echo "--- GET /api/status/ (trailing slash):"; curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/api/status/
echo "--- GET /api/status?x=1:"; curl -sS -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:8080/api/status?x=1'
echo "--- GET /API/STATUS:"; curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/API/STATUS
echo "--- GET / :"; curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/
echo "--- GET with a 200 KB header:"; curl -sS -o /dev/null -w '%{http_code}\n' -H "X-Big: $(head -c 200000 /dev/zero | tr '\0' a)" http://127.0.0.1:8080/api/status; echo "curl rc=$?"
echo "--- HTTP/1.0 request:"; curl -sS -0 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/api/status
echo "--- garbage request line (raw):"; printf 'NOT HTTP\r\n\r\n' | nc -w 2 127.0.0.1 8080 | head -1 | tr -d '\r'
echo "--- runtime truth: two GETs 2 s apart (uptime_seconds and observed_unix must move):"
curl -sS http://127.0.0.1:8080/api/status | sed 's/.*"observed_unix":\([0-9]*\).*"uptime_seconds":\([0-9]*\).*/observed=\1 uptime=\2/'
sleep 2
curl -sS http://127.0.0.1:8080/api/status | sed 's/.*"observed_unix":\([0-9]*\).*"uptime_seconds":\([0-9]*\).*/observed=\1 uptime=\2/'
echo "--- the full body, pretty, for the secret check:"; curl -sS http://127.0.0.1:8080/api/status; echo
echo "--- a keep-alive connection open while SIGTERM arrives (graceful shutdown):"
( printf 'GET /api/status HTTP/1.1\r\nHost: x\r\n\r\n'; sleep 3 ) | nc -w 5 127.0.0.1 8080 > "$log.ka" 2>&1 &
sleep 1
stop
echo "keep-alive client got: $(head -1 "$log.ka" | tr -d '\r')"
echo "--- daemon log:"; cat "$log"

echo "== B. second instance on a busy port fails loudly"
start
RIKURI_LISTEN=127.0.0.1:8080 "$bin"; echo "second exit=$?"
stop

echo "== C. listen boundary: accepted forms"
for spec in '127.0.0.1:0' '127.255.255.255:8080' '[::1]:8080' '127.0.0.1:1'; do
  echo "--- RIKURI_LISTEN=$spec"
  RIKURI_LISTEN="$spec" "$bin" 2> "$log" & pid=$!; sleep 1
  grep -o 'bound=[^ ]*' "$log" || grep ERROR "$log"
  stop
done

echo "== D. listen boundary: refused forms"
for spec in '' ' ' '127.0.0.1:8080 ' '127.0.0.1:65536' '[::ffff:127.0.0.1]:8080' '10.0.0.1:8080' '::1:8080' 'http://127.0.0.1:8080' '127.0.0.1:8080,127.0.0.1:8081' '0:8080' '127.1:8080'; do
  echo "--- RIKURI_LISTEN='$spec'"
  RIKURI_LISTEN="$spec" "$bin"; echo "exit=$?"
done
echo "--- RIKURI_LISTEN not valid UTF-8:"
env RIKURI_LISTEN="$(printf 'a\377b')" "$bin"; echo "exit=$?"

echo "== E. a refusal with RUST_LOG=off: is anything said?"
RUST_LOG=off RIKURI_LISTEN=0.0.0.0:8080 "$bin"; echo "exit=$? (stderr above, if any)"
echo "== F. a secret-looking value in RIKURI_LISTEN is echoed into the log?"
RIKURI_LISTEN='hunter2@127.0.0.1:8080' "$bin"; echo "exit=$?"
