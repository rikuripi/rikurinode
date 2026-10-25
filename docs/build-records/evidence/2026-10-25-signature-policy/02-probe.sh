#!/bin/bash
# Probe 2: a policy naming a key file that does not exist, and a reject default, with skopeo --policy on a
# throwaway file (the node's /etc is not changed). A tiny local image, no network.
set -u
W=$(mktemp -d /var/tmp/sp-probe.XXXX); cd "$W"
echo probe > f; printf 'FROM scratch\nCOPY f /f\n' > Containerfile
sudo podman build -q --network=none -t localhost/sp-probe:0.1 . >/dev/null && echo "## tiny image built"
pol() { cat > "$1"; }
pol missing-key.json <<'J'
{"default": [{"type": "insecureAcceptAnything"}],
 "transports": {"docker": {"ghcr.io/rikuripi/rikurinode": [{"type": "sigstoreSigned", "keyPaths": ["/nonexistent/main.pub"], "signedIdentity": {"type": "matchRepository"}}]}}}
J
pol reject-default.json <<'J'
{"default": [{"type": "reject"}],
 "transports": {"containers-storage": {"": [{"type": "insecureAcceptAnything"}]}}}
J
pol reject-all.json <<'J'
{"default": [{"type": "reject"}]}
J
try() { # policy, source, what
  out=$(sudo skopeo --policy "$1" copy -q "$2" "dir:$W/out-$RANDOM" 2>&1) && echo "$3: copied" || echo "$3: refused: $(echo "$out" | tail -1)"
}
try missing-key.json containers-storage:localhost/sp-probe:0.1 "missing key, a local image (another scope)"
try missing-key.json docker://127.0.0.1:1/other/image:1 "missing key, another registry (unreachable)"
try missing-key.json docker://ghcr.io/rikuripi/rikurinode:1 "missing key, its own scope (no network)"
try reject-default.json containers-storage:localhost/sp-probe:0.1 "reject default, local images allowed"
try reject-default.json docker://127.0.0.1:1/other/image:1 "reject default, another registry"
try reject-all.json containers-storage:localhost/sp-probe:0.1 "reject everything, a local image"
echo "## podman run with a reject-everything policy, a local image:"
sudo podman --log-level=error run --rm --signature-policy reject-all.json --network=none localhost/sp-probe:0.1 /f 2>&1 | tail -1
echo "## cleanup"
sudo podman rmi -f localhost/sp-probe:0.1 >/dev/null 2>&1; cd /; sudo rm -rf "$W"
echo "probe images left: $(sudo podman images --format '{{.Repository}}' | grep -c sp-probe || true); folder left: $(ls -d /var/tmp/sp-probe.* 2>/dev/null | wc -l)"
