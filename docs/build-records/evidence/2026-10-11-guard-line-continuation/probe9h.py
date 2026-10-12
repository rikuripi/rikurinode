#!/usr/bin/env python3
"""Text-only guard probes through the real hook (python3 -B guard.py, JSON on stdin).
Never executes a probed command."""
import json, subprocess, sys, os, time
S = os.path.dirname(os.path.abspath(__file__))
CLONES = [(n, S + "/" + n) for n in os.environ.get("CLONES", "new-dev,old-dev,new-stab,old-stab").split(",")]
LOCKSNIP = r'''
import sys, json; sys.path.insert(0, sys.argv[1] + "/.claude/hooks"); import guard
ev = json.loads(sys.stdin.read())
d, r = guard.decide(ev, guard.load_config(), guard.ROOT, lock_present=True)
print(json.dumps([d, r]))
'''
def hook(root, cmd, lock=False):
    ev = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": root, "session_id": "verifier-probe8"}
    t = time.time()
    if lock:
        p = subprocess.run([sys.executable, "-B", "-c", LOCKSNIP, root], input=json.dumps(ev), capture_output=True, text=True, timeout=60)
        d, r = json.loads(p.stdout)
        return d, " | ".join(r), time.time() - t
    p = subprocess.run([sys.executable, "-B", root + "/.claude/hooks/guard.py"], input=json.dumps(ev), capture_output=True, text=True, timeout=60, cwd=root)
    dt = time.time() - t
    if p.returncode != 0:
        return "ERR rc=%d %s" % (p.returncode, p.stderr[-200:]), "", dt
    if not p.stdout.strip():
        return "allow", "", dt
    o = json.loads(p.stdout)["hookSpecificOutput"]
    return o["permissionDecision"], o["permissionDecisionReason"], dt
M = {"@B@": chr(92), "@N@": chr(10), "@Q@": chr(39), "@T@": chr(9), "@R@": chr(13), "@D@": chr(34)}
def main(path):
    cases = json.load(open(path))
    for c in cases:
        for k, v in M.items():
            c["cmd"] = c["cmd"].replace(k, v)
        cmd, lock = c["cmd"], c.get("lock", False)
        res = {n: hook(r, cmd, lock) for n, r in CLONES}
        print("### %s%s\n    cmd=%r\n    want=%s\n    %s" % (c["label"], " [lock via decide(lock_present=True)]" if lock else "", cmd, c.get("want", "?"),
              "  ".join("%s=%s" % (n, res[n][0]) for n, _ in CLONES)))
        if c.get("why"):
            print("    reason(%s): %s" % (CLONES[0][0], res[CLONES[0][0]][1][:240]))
if __name__ == "__main__":
    main(sys.argv[1])
