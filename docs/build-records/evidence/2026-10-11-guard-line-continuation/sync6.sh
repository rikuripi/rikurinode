#!/bin/bash
# Copy round 6's shared guard into clean clones of the four other repositories and run the shared suite against each one's own policy.
W=/home/junc/claude-wip/guard-continuation; Y=/home/junc/claude-wip/guard-continuation/scratch/sync6
for spec in "Rikuri-PI /home/junc/Rikuri-PI origin/main" "Iceman /home/junc/Iceman HEAD" "AISecurity /home/junc/AISecurity HEAD" "old-rikurinode /home/junc/rikuri/rikurinode HEAD"; do
  set -- $spec; name=$1; src=$2; rev=$3
  out=$Y/sync6-$name.out
  git clone -q --no-checkout "$src" $Y/$name && git -C $Y/$name checkout -q $(git -C "$src" rev-parse $rev)
  { date '+%F %T'; echo "$name at $(git -C $Y/$name rev-parse --short HEAD) ($rev of $src), clean clone"
    cp $W/wt-fix/.claude/hooks/guard.py $W/wt-fix/.claude/hooks/test_guard.py $Y/$name/.claude/hooks/
    for f in guard.py test_guard.py guard_base.py; do cmp -s $W/wt-fix/.claude/hooks/$f $Y/$name/.claude/hooks/$f && echo "cmp $f: identical to fix/guard-continuation's" || echo "cmp $f: DIFFERS"; done
    cd $Y/$name && $W/wt-fix/scripts/quality/safe-run.sh env PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s .claude/hooks -p 'test_*.py' 2>&1 | grep -v "^fix-lock\|^profile\|^Nothing was changed\|^usage:\|^\.fix-lock\|^$" | tail -4
  } > $out 2>&1
done
