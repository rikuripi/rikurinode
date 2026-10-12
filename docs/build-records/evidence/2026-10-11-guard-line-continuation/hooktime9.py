"""Time the real hook (python3 -B guard.py, JSON on stdin) on given commands. Text only."""
import json, subprocess, sys, time, os
S = os.path.dirname(os.path.abspath(__file__))
clones = sys.argv[1].split(",")
cases = json.load(open(sys.argv[2]))
B = chr(92); N = chr(10); Q = chr(39)
for c in cases:
    cmd = eval(c["py"], {"B": B, "N": N, "Q": Q, "L": 16000})
    for cl in clones:
        root = S + "/" + cl
        ev = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": root, "session_id": "hooktime8"})
        t = time.time()
        try:
            p = subprocess.run([sys.executable, "-B", root + "/.claude/hooks/guard.py"], input=ev, capture_output=True,
                               text=True, timeout=c.get("cap", 60), cwd=root)
            dt = time.time() - t
            d = json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"
            if p.returncode: d = "rc=%d" % p.returncode
        except subprocess.TimeoutExpired:
            dt, d = time.time() - t, "KILLED at cap"
        print("%-48s %-9s len=%5d  %6.2fs  %s%s" % (c["label"], cl, len(cmd), dt, d, "   > 10 s HOOK TIMEOUT" if dt > 10 else ""))
        sys.stdout.flush()
