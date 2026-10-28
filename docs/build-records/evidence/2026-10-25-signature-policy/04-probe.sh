#!/bin/bash
# Probe 4: as probe 3, plus a registries.d file for the local registry's own name (probe 3 found the
# setting is looked up by the address read from, not by the policy's name). Probe 3: the shipped policy (image/rootfs/etc/containers/policy.json) and registries.d file, with skopeo
# 1.22.3 on rikuri-drill, against a registry on 127.0.0.1. Throwaway keys only; the policy's two key paths
# are rewritten to them, nothing else. Run as: sudo bash 03-probe.sh <dir holding cosign, registry,
# policy.json, rikuri.yaml>. The node's /etc is not changed; the folder is removed at the end.
set -u
IN=$1
W=$(mktemp -d /var/tmp/sp4.XXXX); cd "$W"
cp "$IN/cosign" "$IN/registry" . && chmod +x cosign registry
echo "## $(./cosign version 2>&1 | grep GitVersion | tr -s ' '); $(./registry --version)"
REG=127.0.0.1:5000
GHCR=ghcr.io/rikuripi/rikurinode
mkdir -p reg rd rd-empty rd-shipped home/.config/containers
printf 'version: 0.1\nstorage:\n  filesystem:\n    rootdirectory: %s/reg\nhttp:\n  addr: %s\nlog:\n  level: error\n' "$W" "$REG" > reg.yml
./registry serve reg.yml >registry.log 2>&1 & RPID=$!
for i in $(seq 50); do curl -fsS "http://$REG/v2/" >/dev/null 2>&1 && break; sleep 0.2; done
echo "## registry up: $(curl -fsS -o /dev/null -w '%{http_code}' "http://$REG/v2/")"

# The probe's registries.conf: the policy's scope is read from the local registry (c/image's prefix
# rewrite), and nothing else in it changes. The VM has no route out, so ghcr.io itself is unreachable.
cat > registries.conf <<EOF
[[registry]]
prefix = "$GHCR"
location = "$REG/rikuripi/rikurinode"
insecure = true

[[registry]]
location = "$REG"
insecure = true
EOF
cp "$IN/rikuri.yaml" rd/; cp "$IN/rikuri.yaml" rd-shipped/
# The CI-only addition: the same setting for the address the probe reads from.
printf 'docker:\n  %s/rikuripi/rikurinode:\n    use-sigstore-attachments: true\n' "$REG" > rd/ci-local-registry.yaml
echo "## rd: $(ls rd | tr '\n' ' '); rd-shipped: $(ls rd-shipped)"
sed -e "s#/usr/share/rikuri/signing/rikuri-main.pub#$W/main.pub#" \
    -e "s#/usr/share/rikuri/signing/rikuri-spare.pub#$W/spare.pub#" "$IN/policy.json" > policy.json
echo "## policy.json against the shipped one, every changed line:"; diff "$IN/policy.json" policy.json | grep '^[<>]'

export COSIGN_PASSWORD=""
for k in main spare other; do ./cosign generate-key-pair --output-key-prefix "$k" >/dev/null 2>&1; done
echo "## throwaway keys: $(ls *.pub | tr '\n' ' ')"

# One tiny image per case, each with its own content, so each has its own digest.
digest() { skopeo inspect --tls-verify=false --format '{{.Digest}}' "docker://$REG/$1"; }
for t in main spare unsigned other identity tampered; do
  mkdir -p "img-$t"; echo "$t" > "img-$t/f"; printf 'FROM scratch\nCOPY f /f\n' > "img-$t/Containerfile"
  podman build -q --network=none -t "$REG/rikuripi/rikurinode:$t" "img-$t" >/dev/null
  podman push -q --tls-verify=false "$REG/rikuripi/rikurinode:$t"
done
podman tag "$REG/rikuripi/rikurinode:unsigned" "$REG/other/thing:1"; podman push -q --tls-verify=false "$REG/other/thing:1"
sign() { # key, tag, identity: cosign's older format, no transparency log, signed by digest
  ./cosign sign -y --key "$1.key" --tlog-upload=false --new-bundle-format=false --use-signing-config=false \
    --allow-http-registry --sign-container-identity "$3" "$REG/rikuripi/rikurinode@$(digest "rikuripi/rikurinode:$2")" >sign-$2.log 2>&1 \
    && echo "signed $2 with $1 as $3" || { echo "SIGN FAILED $2:"; tail -3 sign-$2.log; }
}
sign main main "$GHCR:main"
sign spare spare "$GHCR:spare"
sign other other "$GHCR:other"
sign main identity "ghcr.io/someone/else:identity"
sign main tampered "$GHCR:tampered"
# Tamper: the tampered image's signature is replaced by the main case's (a valid signature, another image).
DM=$(digest rikuripi/rikurinode:main); DT=$(digest rikuripi/rikurinode:tampered)
skopeo copy -q --preserve-digests --src-tls-verify=false --dest-tls-verify=false \
  "docker://$REG/rikuripi/rikurinode:${DM/:/-}.sig" "docker://$REG/rikuripi/rikurinode:${DT/:/-}.sig" \
  && echo "tampered: the main case's signature now sits at the tampered image's digest"
echo "## the registry's tags: $(skopeo list-tags --tls-verify=false "docker://$REG/rikuripi/rikurinode" | tr -d ' \n')"

try() { # what, reference, registries.d, [extra skopeo options]
  local out
  out=$(skopeo --policy policy.json --registries-conf registries.conf --registries.d "$3" ${4:-} \
        copy -q "docker://$2" "dir:$W/out-$RANDOM" 2>&1) && echo "$1: ACCEPTED" || echo "$1: REFUSED: ${out##*msg=}"
}
echo "## the shipped policy (key paths rewritten); registries.d: the shipped file and the CI-only one"
try "1 signed by the main key           " "$GHCR:main"      rd
try "2 signed by the spare key          " "$GHCR:spare"     rd
try "3 unsigned                         " "$GHCR:unsigned"  rd
try "4 signed by an untrusted key       " "$GHCR:other"     rd
try "5 main key, another repo's identity" "$GHCR:identity"  rd
try "6 another image's signature        " "$GHCR:tampered"  rd
try "7 another repository, unsigned     " "$REG/other/thing:1" rd
echo "## without the CI-only file, the shipped one alone (probe 3), and without any"
try "8a signed, shipped file only       " "$GHCR:main"      rd-shipped
try "8b signed, no registries.d file    " "$GHCR:main"      rd-empty
echo "## the main case by digest, as an update would name it; and read by the local name, outside the scope"

try "9 signed, by digest                " "$GHCR@$DM"       rd
try "9b the local name (no scope: default)" "$REG/rikuripi/rikurinode:unsigned" rd
echo "## root's own policy file (\$HOME/.config/containers/policy.json) replaces /etc's when no --policy is given"
echo '{"default": [{"type": "reject"}]}' > home/.config/containers/policy.json
out=$(HOME="$W/home" skopeo --registries-conf registries.conf --registries.d rd copy -q "docker://$REG/other/thing:1" "dir:$W/out-home" 2>&1) \
  && echo "10 HOME policy reject-all, unsigned other repo: ACCEPTED" || echo "10 HOME policy reject-all, unsigned other repo: REFUSED: ${out##*msg=}"

echo "## cleanup"
kill "$RPID"; wait "$RPID" 2>/dev/null
for t in main spare unsigned other identity tampered; do podman rmi -f "$REG/rikuripi/rikurinode:$t" >/dev/null 2>&1; done
podman rmi -f "$REG/other/thing:1" >/dev/null 2>&1
cd /; rm -rf "$W"
echo "images left: $(podman images --format '{{.Repository}}' | grep -c "$REG" || true); folder left: $(ls -d /var/tmp/sp4.* 2>/dev/null | wc -l)"
