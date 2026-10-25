#!/bin/bash
# Repair 1 probe (verifier I1, I3): a one-item array, a non-ASCII byte before '=', C escapes and quotes in PodmanArgs=.
set -u
Q=/etc/containers/systemd
IMG=localhost/rikuri-os:gbp
unit() { printf '[Container]\nImage=%s\n%b\n' "$IMG" "$2" | sudo tee "$Q/$1" >/dev/null; }
unit hr01.container 'HealthCmd=["/standin"]'
unit hr02.container 'HealthCmd\xa0=/standin probe'
unit hr03.container 'PodmanArgs\xa0=--health-cmd=/standin'
unit hr04.container 'PodmanArgs=--\\x68ealth-cmd=/standin\\x20probe'
unit hr05.container 'PodmanArgs=--hea""lth-cmd "/standin probe"'
echo "## the unit lines, as written:"
for f in $Q/hr0*.container; do echo "--- $f"; sudo sed -n 3p "$f" | cat -A; done
echo "## quadlet -dryrun:"
sudo /usr/libexec/podman/quadlet -dryrun > /tmp/hcq.out 2>/tmp/hcq.err; echo "exit $?"; grep -iv "loading" /tmp/hcq.err | head
awk '/^---.*---$/ {name=$0} /^ExecStart=/ {print name; print "  " $0}' /tmp/hcq.out | sed 's/ --cidfile=[^ ]*//; s/ --sdnotify=[^ ]*//; s/--name systemd-%N --replace --rm --cgroups=split -d //'
echo "## Podman's record of a one-item array:"
sudo podman create -q --name phr01 --health-cmd '["/standin"]' $IMG >/dev/null && sudo podman inspect -f '{{json .Config.Healthcheck.Test}}' phr01; sudo podman rm -f phr01 >/dev/null 2>&1
sudo podman create -q --name phr06 --health-cmd '["/standin", "probe"]' $IMG >/dev/null && echo "two items: $(sudo podman inspect -f '{{json .Config.Healthcheck.Test}}' phr06)"; sudo podman rm -f phr06 >/dev/null 2>&1
echo "## cleanup"
sudo rm -f $Q/hr0*.container /tmp/hcq.out /tmp/hcq.err
echo "left in $Q: $(sudo find $Q -mindepth 1 | wc -l); probe containers left: $(sudo podman ps -a --format '{{.Names}}' | grep -c '^phr' || true)"
