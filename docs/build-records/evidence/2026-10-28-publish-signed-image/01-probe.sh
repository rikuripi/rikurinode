#!/bin/bash
# Probe 5 (2b), on rikuri-drill: (a) does an image pushed by podman keep, as its manifest's config digest, the
# ID of the image built (the sign job's "the image pulled is the one built")? (b) does cosign v3.1.4 sign with
# the key read from an environment variable (--key env://...), with a password, in the older format, and does
# the shipped policy accept it? Throwaway key and a registry on 127.0.0.1 only. Run as: sudo bash 01-probe.sh
# <dir holding cosign, registry, policy.json, rikuri.yaml>. The node's /etc is not changed; the folder, the
# probe's image names and the registry are removed at the end; the images of earlier tasks are left.
set -u
IN=$1
W=$(mktemp -d /var/tmp/sp5.XXXX); cd "$W"
cp "$IN/cosign" "$IN/registry" . && chmod +x cosign registry
REG=127.0.0.1:5000
GHCR=ghcr.io/rikuripi/rikurinode
mkdir -p reg rd
printf 'version: 0.1\nstorage:\n  filesystem:\n    rootdirectory: %s/reg\nhttp:\n  addr: %s\nlog:\n  level: error\n' "$W" "$REG" > reg.yml
env -u REGISTRY_VERSION ./registry serve reg.yml >registry.log 2>&1 & RPID=$!
for i in $(seq 50); do curl -fsS "http://$REG/v2/" >/dev/null 2>&1 && break; sleep 0.2; done
printf '[[registry]]\nprefix = "%s"\nlocation = "%s/rikuripi/rikurinode"\ninsecure = true\n' "$GHCR" "$REG" > registries.conf
sed "s#$GHCR:#$REG/rikuripi/rikurinode:#" "$IN/rikuri.yaml" > rd/rikuri.yaml
sed -e "s#/usr/share/rikuri/signing/rikuri-main.pub#$W/k.pub#" -e "s#/usr/share/rikuri/signing/rikuri-spare.pub#$W/k.pub#" \
    "$IN/policy.json" > policy.json

echo "## (a) the pushed manifest's config digest against the built image's ID"
mkdir img; echo tiny > img/f; printf 'FROM scratch\nCOPY f /f\n' > img/Containerfile
podman build -q --network=none -t "$REG/rikuripi/rikurinode:tiny" img >/dev/null
podman tag localhost/rikuri-os:gbp "$REG/rikuripi/rikurinode:os"
for t in tiny os; do
  id=$(podman image inspect --format '{{.Id}}' "$REG/rikuripi/rikurinode:$t")
  podman push -q --tls-verify=false --digestfile "d-$t" "$REG/rikuripi/rikurinode:$t"
  cfg=$(skopeo inspect --tls-verify=false --raw "docker://$REG/rikuripi/rikurinode@$(cat d-$t)" | python3 -c 'import json,sys; print(json.load(sys.stdin)["config"]["digest"])')
  echo "$t: image ID sha256:$id; pushed $(cat d-$t), its config $cfg: $([ "sha256:$id" = "$cfg" ] && echo EQUAL || echo DIFFERENT)"
done

echo "## (b) cosign, the key from an environment variable, with a password"
export COSIGN_PASSWORD="probe-$RANDOM-password"
./cosign generate-key-pair --output-key-prefix k >/dev/null 2>&1
K=$(cat k.key); rm k.key   # the key now exists only in this shell's variable
ls k.key 2>/dev/null || echo "no key file left"
COSIGN_PRIVATE_KEY="$K" ./cosign sign -y --key env://COSIGN_PRIVATE_KEY --new-bundle-format=false --tlog-upload=false \
  --use-signing-config=false --allow-http-registry --sign-container-identity "$GHCR:tiny" \
  "$REG/rikuripi/rikurinode@$(cat d-tiny)" >sign.log 2>&1 && echo "signed by env://" || { echo "SIGN FAILED:"; tail -3 sign.log; }
COSIGN_PASSWORD=wrong COSIGN_PRIVATE_KEY="$K" ./cosign sign -y --key env://COSIGN_PRIVATE_KEY --new-bundle-format=false \
  --tlog-upload=false --use-signing-config=false --allow-http-registry "$REG/rikuripi/rikurinode@$(cat d-tiny)" >bad.log 2>&1 \
  && echo "WRONG PASSWORD SIGNED" || echo "wrong password refused: $(grep -o -m1 'decrypt[^"]*' bad.log | head -c 80)"
try() { out=$(skopeo --policy policy.json --registries-conf registries.conf --registries.d rd copy -q "docker://$1" "dir:$W/o-$RANDOM" 2>&1) \
  && echo "$2: ACCEPTED" || echo "$2: REFUSED: ${out##*msg=}"; }
try "$GHCR@$(cat d-tiny)" "signed by env://, by digest"
try "$GHCR:tiny" "signed by env://, by tag"
try "$GHCR@$(cat d-os)" "the OS image, unsigned"

echo "## cleanup"
kill "$RPID"; wait "$RPID" 2>/dev/null
podman rmi -f "$REG/rikuripi/rikurinode:tiny" >/dev/null 2>&1; podman untag localhost/rikuri-os:gbp "$REG/rikuripi/rikurinode:os"
cd /; rm -rf "$W"
echo "left: $(podman images --format '{{.Repository}}' | grep -c "$REG"); folders: $(ls -d /var/tmp/sp5.* 2>/dev/null | wc -l); gbp: $(podman images -q localhost/rikuri-os:gbp | wc -l)"
