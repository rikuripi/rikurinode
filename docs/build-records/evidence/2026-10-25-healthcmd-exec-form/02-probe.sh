#!/bin/bash
set -u
Q=/etc/containers/systemd
IMG=localhost/rikuri-os:gbp
echo "## folders named in the quadlet binary:"
strings /usr/libexec/podman/quadlet | grep -oE '(/[a-z.]+)*/containers/systemd/?(users)?' | sort -u
unit() { printf '[Container]\nImage=%s\n%s\n' "$IMG" "$2" | sudo tee "$Q/$1" >/dev/null; }
unit hs01.container $'HealthCmd=["/standin", "probe"]\nHealthStartupCmd=/standin startup'
unit hs02.container 'PodmanArgs=--health-cmd=/standin\x20probe'
unit hs03.container 'PodmanArgs=--health-cmd "/standin probe"'
unit hs04.container 'HealthCmd=["/standin", "probe"]
PodmanArgs=--health-cmd "/standin probe"'
sudo mkdir -p /var/tmp/hclinked; unit ../../../var/tmp/hclinked/hs05.container 'HealthCmd=/standin probe'
sudo ln -s /var/tmp/hclinked $Q/linkeddir
sudo ln -s /var/tmp/hclinked/hs05.container $Q/hs06.container
echo "## quadlet -dryrun -v:"
sudo /usr/libexec/podman/quadlet -dryrun -v > /tmp/hcq.out 2>/tmp/hcq.err; echo "exit $?"
grep -vE 'Loading source unit file' /tmp/hcq.err | sed 's/^/  /' | head -20
grep -E 'Loading source unit file' /tmp/hcq.err | sed 's/^/  /'
awk '/^---.*---$/ {name=$0} /^ExecStart=/ {print name; print "  " $0}' /tmp/hcq.out | sed 's/ --cidfile=[^ ]*//; s/ --sdnotify=[^ ]*//'
echo "## Podman's record:"
pc() { sudo podman create -q --name "p$1" "${@:2}" $IMG >/dev/null 2>/tmp/hcp.err \
  && echo "$1: test $(sudo podman inspect -f '{{json .Config.Healthcheck.Test}}' p$1); startup $(sudo podman inspect -f '{{json .Config.StartupHealthCheck}}' p$1)" \
  || echo "$1: create refused: $(head -1 /tmp/hcp.err)"; sudo podman rm -f "p$1" >/dev/null 2>&1; }
pc hs01 --health-cmd '["/standin", "probe"]' --health-startup-cmd '/standin startup'
pc hs04 --health-cmd '["/standin", "probe"]' --health-cmd '/standin probe'
echo "## cleanup"
sudo rm -rf $Q/hs0*.container $Q/linkeddir /var/tmp/hclinked /tmp/hcq.out /tmp/hcq.err /tmp/hcp.err
echo "left in $Q: $(sudo find $Q -mindepth 1 | wc -l); probe containers left: $(sudo podman ps -a --format '{{.Names}}' | grep -c '^phs' || true)"
