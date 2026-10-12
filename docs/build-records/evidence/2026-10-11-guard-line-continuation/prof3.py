"""Each policy rule's search time on one slow command, and the new checks' time under their deadline."""
import os, re, sys, time
F = sys.argv[1]
sys.path.insert(0, os.path.join(F, ".claude/hooks"))
import guard
cfg = dict(guard.load_config(), profile="stable")
cmd = ("~/" * 16000)[:16000]
ev = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": F}
guard._DEADLINE = time.time() + guard.SEARCH_TIME_BUDGET; guard._DEADLINE_ALL = time.time() + guard.CHECK_TIME_BUDGET
t0 = time.time()
try:
    guard._decide_new(ev, cfg, F, lock_present=False, branch_fn=lambda c: "x"); print("new finished")
except guard._TooSlow:
    print("new: _TooSlow")
print("new under its deadline %.2fs (budget %.1f)" % (time.time() - t0, guard.CHECK_TIME_BUDGET))
rows = []
for r in cfg["funds_patterns"]:
    rx = re.compile(r["regex"]); a = time.time(); rx.search(cmd); rows.append((time.time() - a, r["reason"][:70]))
for dt, why in sorted(rows, reverse=True)[:8]:
    print("%.3fs %s" % (dt, why))
print("all %d rules once: %.2fs" % (len(rows), sum(d for d, _ in rows)))
