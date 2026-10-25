echo "## folders named in /usr/libexec/podman/quadlet (grep -a):"
grep -aoE '/[a-z/.]*containers/systemd[a-z/]*' /usr/libexec/podman/quadlet | sort -u
echo "## rpm: $(rpm -q podman)"
echo "## the man page's search paths, if shipped:"
ls /usr/share/man/man5/podman-systemd.unit.5* 2>&1 | head -2
