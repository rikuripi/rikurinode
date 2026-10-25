#!/bin/bash
# Probe: which files Quadlet reads, and how HealthCmd= forms reach Podman. Throwaway units; removed at the end.
set -u
Q=/etc/containers/systemd
IMG=localhost/rikuri-os:gbp
echo "## podman: $(podman --version); systemd: $(systemctl --version | head -1)"
unit() { # name, HealthCmd line(s)
  printf '[Container]\nImage=%s\n%s\n' "$IMG" "$2" | sudo tee "$Q/$1" >/dev/null
}
sudo mkdir -p $Q/sub $Q/hcprobe-a.container.d $Q/hcprobe-.container.d $Q/container.d
unit hcprobe-a.container 'Environment=FROM=main'
printf '[Container]\nEnvironment=DROPIN_NAME=1\n' | sudo tee $Q/hcprobe-a.container.d/50-name.conf >/dev/null
printf '[Container]\nEnvironment=DROPIN_PREFIX=1\n' | sudo tee $Q/hcprobe-.container.d/50-prefix.conf >/dev/null
printf '[Container]\nEnvironment=DROPIN_TYPE=1\n' | sudo tee $Q/container.d/50-type.conf >/dev/null
unit sub/hcprobe-sub.container 'Environment=FROM=subfolder'
unit hc01.container 'HealthCmd=["/standin", "probe"]'
unit hc02.container 'HealthCmd=["CMD-SHELL", "/standin probe"]'
unit hc03.container 'HealthCmd=["CMD", "/standin", "probe"]'
unit hc04.container 'HealthCmd=[/standin, probe]'
unit hc05.container 'HealthCmd=   ["/standin", "probe"]   '
unit hc06.container 'HealthCmd=none'
unit hc07.container 'HealthCmd="[\"/standin\", \"probe\"]"'
unit hc08.container 'HealthCmd=["/standin", \
  "probe"]'
unit hc09.container 'HealthCmd=["/standin", "probe"]
HealthCmd=/standin probe'
unit hc10.container 'HealthCmd = ["/standin", "probe"]'
unit hc11.container 'healthcmd=/standin probe'
unit hc12.container 'HealthCmd=[]'
unit hc13.container 'HealthCmd=["NONE"]'
unit hc14.container 'HealthCmd=/standin probe'
unit hc15.container 'HealthCmd=["/standin", "probe"] # trailing'
echo "## the unit files, as written:"
for f in $(sudo find $Q -type f | sort); do echo "--- $f"; sudo cat -A "$f"; done
echo "## quadlet -dryrun -v (stderr: the folders and files it reads):"
sudo /usr/libexec/podman/quadlet -dryrun -v > /tmp/hcq.out 2>/tmp/hcq.err; echo "exit $?"
grep -iE 'unit dir|search|loading|reading|source|error|warn' /tmp/hcq.err | sed 's/^/  /' | head -40
echo "## per unit: the Environment= or health-cmd Quadlet hands Podman:"
awk '/^---.*---$/ {name=$0} /^ExecStart=/ {print name; n=split($0, a, " --"); for (i=1;i<=n;i++) if (a[i] ~ /^(health-cmd|env)/) print "  --" a[i]}' /tmp/hcq.out
echo "## Podman's record of each form (podman create, never started):"
pc() { # case, the --health-cmd value as Quadlet passed it
  sudo podman create -q --name "p$1" --health-cmd "$2" $IMG >/dev/null 2>/tmp/hcp.err \
    && echo "$1: $(sudo podman inspect -f '{{json .Config.Healthcheck.Test}}' p$1)" \
    || echo "$1: create refused: $(head -1 /tmp/hcp.err)"
  sudo podman rm -f "p$1" >/dev/null 2>&1
}
pc hc01 '["/standin", "probe"]'
pc hc02 '["CMD-SHELL", "/standin probe"]'
pc hc03 '["CMD", "/standin", "probe"]'
pc hc04 '[/standin, probe]'
pc hc06 'none'
pc hc07 '"[\"/standin\", \"probe\"]"'
pc hc12 '[]'
pc hc13 '["NONE"]'
pc hc14 '/standin probe'
pc hc15 '["/standin", "probe"] # trailing'
pc hc16 ' ["/standin", "probe"]'
pc hc17 '["/standin",  "probe" ]'
echo "## cleanup"
sudo rm -rf $Q/sub $Q/hcprobe-a.container $Q/hcprobe-a.container.d $Q/hcprobe-.container.d $Q/container.d $Q/hc*.container /tmp/hcq.out /tmp/hcq.err /tmp/hcp.err
echo "left in $Q: $(sudo find $Q -mindepth 1 | wc -l); probe containers left: $(sudo podman ps -a --format '{{.Names}}' | grep -c '^phc' || true)"
