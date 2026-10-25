#!/bin/bash
# Probe 1: what the image ships for signature checks, and whether this node changed it. Reads only.
set -u
echo "## versions: $(rpm -q podman skopeo containers-common bootc 2>&1 | tr '\n' ' ')"
echo "## cosign on the node: $(command -v cosign || echo absent)"
echo "## /etc/containers/policy.json:"; cat /etc/containers/policy.json
echo "## the image's default (/usr/etc/containers/policy.json) differs? $(cmp -s /usr/etc/containers/policy.json /etc/containers/policy.json && echo no || echo yes)"
echo "## ostree admin config-diff, containers lines:"; sudo ostree admin config-diff 2>/dev/null | grep -E 'containers' || echo "(none)"
echo "## registries.d:"; ls -la /etc/containers/registries.d/; for f in /etc/containers/registries.d/*; do echo "--- $f"; grep -vE '^\s*(#|$)' "$f"; done
echo "## files under /etc/pki/containers and /usr/share/containers:"; ls -la /etc/pki/containers 2>&1; ls /usr/share/containers
echo "## bootc's own view:"; sudo bootc status --format=json 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); b=d["status"]["booted"]; print(b["image"]["image"])'
