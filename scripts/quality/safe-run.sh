#!/usr/bin/env bash
# Run a command inside the outer test-safety layer (AGENTS.md > Testing on this
# machine). The machine that develops this repository may run a live node: no
# test may reach its container runtime, systemd, network services or
# processes — not even a child that clears its environment.
#
#   1. Namespaces (unprivileged): a private mount namespace with an empty /run
#      (no Docker, Podman or systemd socket), a private network with only
#      loopback (no live service on 127.0.0.1; if loopback cannot be brought up,
#      it refuses with exit 2), a private PID namespace (no
#      process outside can be seen or signalled). The command runs as a mapped
#      root inside, with no privilege outside.
#   2. Stand-ins first on PATH that refuse (exit 126) for container, service and
#      node programs (their folder is SAFE_RUN_BIN), and DOCKER_HOST at a socket
#      that does not exist.
#   3. The live node's container start times (lnd, bitcoin, tor) are read,
#      read-only, before and after: a change fails the run.
#
# Without namespace support it refuses (exit 2), unless the caller sets
# SAFE_RUN_ALLOW_NO_NAMESPACE=1 — only where no live node runs (CI) — and then
# says it runs with stand-ins only. Network access is not available inside.
# Usage: scripts/quality/safe-run.sh <command> [args…]
# Record: docs/build-records/2026-10-10-bootstrap.md
set -uo pipefail

[ $# -gt 0 ] || { echo "usage: safe-run.sh <command> [args…]" >&2; exit 2; }

bin="$(mktemp -d "${TMPDIR:-/tmp}/rikuri-safe-bin.XXXXXX")" || exit 2
trap 'rm -rf "$bin"' EXIT
for p in docker podman nerdctl ctr runc nsenter sudo pkexec su systemctl loginctl service \
         lncli bitcoin-cli tapcli loop pool hwi tailscale shutdown reboot poweroff halt init telinit \
         pkill killall; do
  cat > "$bin/$p" <<EOF
#!/bin/sh
echo "refused by the test safety layer: $p \$*" >&2
exit 126
EOF
  chmod +x "$bin/$p"
done

node_started() {
  command docker inspect -f '{{.Name}}={{.State.StartedAt}}' lnd bitcoin tor 2>/dev/null | sort
}
before="$(node_started)"

NS=(unshare --user --map-root-user --mount --net --pid --fork --mount-proc)
inner='mount -t tmpfs -o mode=755 none /run || { echo "safe-run: cannot hide /run" >&2; exit 2; }
ip link set lo up || { echo "safe-run: cannot bring loopback up inside the layer (is iproute2'"'"'s ip installed?); refusing to run" >&2; exit 2; }
exec "$@"'
if [ -z "${SAFE_RUN_FORCE_NO_NAMESPACE:-}" ] && "${NS[@]}" true 2>/dev/null; then
  PATH="$bin:$PATH" SAFE_RUN_BIN="$bin" DOCKER_HOST="unix:///nonexistent/rikuri-safe-run.sock" SAFE_RUN_MODE="namespace" \
    "${NS[@]}" bash -c "$inner" safe-run "$@"
  rc=$?
elif [ "${SAFE_RUN_ALLOW_NO_NAMESPACE:-}" = 1 ]; then
  echo "safe-run: namespace isolation unavailable — stand-ins only (SAFE_RUN_ALLOW_NO_NAMESPACE=1)" >&2
  PATH="$bin:$PATH" SAFE_RUN_BIN="$bin" DOCKER_HOST="unix:///nonexistent/rikuri-safe-run.sock" \
    SAFE_RUN_MODE="stand-ins only" "$@"
  rc=$?
else
  echo "safe-run: namespace isolation unavailable here; refusing to run (set SAFE_RUN_ALLOW_NO_NAMESPACE=1 only where no live node runs)" >&2
  exit 2
fi

after="$(node_started)"
if [ -z "$before" ]; then
  echo "safe-run: no live node containers found here; the start-time check had nothing to compare" >&2
elif [ "$before" != "$after" ]; then
  echo "safe-run: a live node container restarted during the run:" >&2
  diff <(echo "$before") <(echo "$after") >&2
  exit 125
fi
exit "$rc"
