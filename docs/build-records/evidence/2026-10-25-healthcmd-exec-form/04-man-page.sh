echo "## podman-systemd.unit(5), podman 5.8.9: the search paths and drop-ins"
zcat /usr/share/man/man5/podman-systemd.unit.5.gz | grep -nE 'containers/systemd|\.d/|drop-in|HealthStartupCmd|^\.SS|users/' | grep -vE '^\s*$' | head -50
