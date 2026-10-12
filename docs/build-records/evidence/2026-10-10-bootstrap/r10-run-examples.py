"""Replay a list of worked examples against a checkout's guard and policy, both profiles."""
import json, os, sys
root, path = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(root, ".claude/hooks"))
import guard
cfg = guard.load_config()
bad = 0
for e in json.load(open(path)):
    got = {}
    for prof, key in (("stable", "expect"), ("development", "expect_dev")):
        ev = {"tool_name": e["tool"], "tool_input": e["input"], "cwd": guard.ROOT}
        got[key] = guard.decide(ev, dict(cfg, profile=prof), guard.ROOT, lock_present=False,
                                branch_fn=lambda _c: "feature/x")[0]
    if got["expect"] != e["expect"] or got["expect_dev"] != e["expect_dev"]:
        bad += 1
        print("WRONG want %s/%s got %s/%s | %r" % (e["expect"], e["expect_dev"], got["expect"], got["expect_dev"],
                                                   e["input"]["command"]))
print("%d of %d wrong" % (bad, len(json.load(open(path)))))
