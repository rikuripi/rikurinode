#!/bin/sh
# The loop that drove 01-finalize-tries.out from the Mac (written down after
# the run; ssh_drill.sh is the session's ssh wrapper with the pinned host key).
# Odd tries run the --userns=auto container first ("with"), even ones do not.
for n in 1 2 3 4 5 6; do
  if [ $((n % 2)) -eq 1 ]; then m=with; else m=without; fi
  old=$(ssh_drill.sh 'cat /proc/sys/kernel/random/boot_id')
  ssh_drill.sh "sudo /var/tmp/ftbin/stage.sh $n $m && sudo systemctl reboot" 2>&1 | grep -v 'closed by remote host'
  i=0; while [ $i -lt 60 ]; do i=$((i+1)); sleep 5; new=$(ssh_drill.sh 'cat /proc/sys/kernel/random/boot_id' 2>/dev/null); [ -n "$new" ] && [ "$new" != "$old" ] && break; done
  ssh_drill.sh 'sudo /var/tmp/ftbin/report.sh' 2>&1; echo
done
