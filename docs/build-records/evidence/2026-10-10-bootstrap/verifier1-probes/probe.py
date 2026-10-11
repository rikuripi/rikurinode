import json, os, subprocess, sys
C = sys.argv[1]
CASES = sys.argv[2]
SUB = {"M@C": "maca"+"roon", "W@D": "wall"+"et.db", "W@T": "wall"+"et", "C@B": "chann"+"el.backup",
       "C@K": "coo"+"kie", "E@NV": "e"+"nv", "G@H": "g"+"h", "K@Y": "k"+"ey", "I@D": "id_"+"ed25519", "H@Y": "hos"+"ts.yml"}
def sub(s):
    for k, v in SUB.items():
        s = s.replace(k, v)
    return s
sys.path.insert(0, os.path.join(C, ".claude/hooks"))
import guard
cfg_stable = guard.load_config(os.path.join(C, ".claude/hooks/guard-config.json"))
cfg_stable["profile"] = "stable"
rows = []
for line in open(CASES):
    line = line.rstrip("\n")
    if not line.strip() or line.startswith("#"):
        continue
    cid, tool, expect, payload = [x.strip() for x in line.split("|||", 3)]
    payload = sub(payload).replace("\\n", "\n")
    tin = {"command": payload} if tool == "Bash" else {"file_path": payload}
    if tool in ("Edit", "MultiEdit"):
        tin.update({"old_string": "a", "new_string": "b"})
    if tool == "Write":
        tin.update({"content": "x"})
    ev = {"session_id": "verifier-probe", "transcript_path": "/dev/null", "cwd": C,
          "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tin}
    p = subprocess.run([sys.executable, os.path.join(C, ".claude/hooks/guard.py")], input=json.dumps(ev),
                       capture_output=True, text=True, cwd=C, env=dict(os.environ, CLAUDE_PROJECT_DIR=C), timeout=30)
    if p.stdout.strip():
        o = json.loads(p.stdout)["hookSpecificOutput"]
        dec, why = o["permissionDecision"], o["permissionDecisionReason"]
    else:
        dec, why = "allow", ""
    st = guard.decide(ev, cfg_stable, root=C, lock_present=False, branch_fn=lambda _c: "feat/x")
    mark = "ok  " if dec == expect else "MISS"
    rows.append((mark, cid, tool, expect, dec, st[0], payload.replace("\n", "\\n"), why[:110], p.returncode))
for r in rows:
    print("%s %-5s %-5s exp=%-5s dev=%-5s stable=%-5s rc=%d | %s%s" % (r[0], r[1], r[2], r[3], r[4], r[5], r[8], r[6],
          ("  [" + r[7] + "]") if r[0] == "MISS" and r[7] else ""))
print("MISS count:", sum(1 for r in rows if r[0] == "MISS"), "of", len(rows))
