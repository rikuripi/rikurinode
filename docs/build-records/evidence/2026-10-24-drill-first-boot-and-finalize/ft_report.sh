#!/bin/sh
# Runs as root after the reboot: what booted, and how the previous shutdown's finalize went.
python3 -c "import json,subprocess; s=json.loads(subprocess.run(['bootc','status','--format=json'],capture_output=True,check=True).stdout)['status']; print('booted:', s['booted']['image']['image']['image'])"
echo "finalize (previous boot):"; journalctl -b -1 -u ostree-finalize-staged.service --no-pager -o cat | grep -E 'Failed with result|exited|Deactivated successfully|Finished writing|error' | sed 's/^/  /'
echo "greenboot trigger (previous boot):"; journalctl -b -1 -u greenboot-set-rollback-trigger.service --no-pager -o cat | grep -E 'Setting rollback|non-zero|No staged' | sed 's/^/  /'
echo "error lines (previous boot):"; journalctl -b -1 --no-pager -o short-monotonic --grep '(^error:|ostree.*(error|fail))' 2>/dev/null | tail -5 | sed 's/^/  /'
