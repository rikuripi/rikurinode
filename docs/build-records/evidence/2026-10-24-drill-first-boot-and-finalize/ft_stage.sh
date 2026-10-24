#!/bin/sh
# Runs as root in rikuri-drill. Stages try n: an image built on the booted one;
# with mode "with", a --userns=auto run of the booted image first.
set -e
n=$1; mode=$2
img() { bootc status --format=json | python3 -c "import json,sys; s=json.load(sys.stdin)['status']; d=s['$1']; print(d['image']['image']['image'] if d else 'none')"; }
base=$(img booted)
echo "try $n ($mode): booted $base"
d=/var/tmp/ft/$n; mkdir -p "$d"
printf 'FROM %s\nLABEL rikuri.finalize-try=%s\n' "$base" "$n" > "$d/Containerfile"
podman build -q --pull=never --network=none -t "localhost/rikuri-os:ft$n" "$d" >/dev/null
if [ "$mode" = with ]; then
  podman run --rm --userns=auto --network=none --read-only "$base" /usr/bin/true && echo "userns=auto run: started"
fi
bootc switch --transport containers-storage "localhost/rikuri-os:ft$n" 2>&1 | tail -1
echo "staged: $(img staged)"
