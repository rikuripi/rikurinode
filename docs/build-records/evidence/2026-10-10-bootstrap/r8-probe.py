"""Kept as run, from the session's scratchpad: its copies (r8/, the round-7
verifier's rn-verify12/r7-*, the round-6 verifier's rn-verify10/probe-*) and
case files (both verifiers' cases-*.txt) lived there, not in this repository.
Text-only guard probes for round 8: each case is one PreToolUse event on
stdin to the real guard.py of copies of round 8 (r8/), round 7 (rn-verify12/r7-*)
and round 6 (rn-verify10/probe-*), in stable and development. Nothing probed is
executed. Case line: id ||| tool ||| expect ||| text (expect: one verdict, or
stable/dev); {ROOT} is replaced by each copy's root. LOOSER: round 8 allows
where round 7 or round 6 asked."""
import json, os, subprocess, sys
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPIES = [("r8s", S + "/r8/stable"), ("r8d", S + "/r8/development"),
          ("r7s", S + "/rn-verify12/r7-stable"), ("r7d", S + "/rn-verify12/r7-dev"),
          ("r6s", S + "/rn-verify10/probe-stable"), ("r6d", S + "/rn-verify10/probe-dev")]
RANK = {"allow": 0, "ask": 1, "deny": 2}


def decide(root, tool, text):
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    tin = {"command": text} if tool == "Bash" else {key: text}
    if tool == "Edit":
        tin.update({"old_string": "a", "new_string": "b"})
    if tool == "Write":
        tin.update({"content": "x"})
    if tool == "NotebookEdit":
        tin.update({"new_source": "x"})
    ev = {"session_id": "r8-probe", "transcript_path": "/dev/null", "cwd": root, "hook_event_name": "PreToolUse",
          "tool_name": tool, "tool_input": tin}
    p = subprocess.run([sys.executable, "-B", os.path.join(root, ".claude/hooks/guard.py")], input=json.dumps(ev),
                       capture_output=True, text=True, cwd=root, env=dict(os.environ, CLAUDE_PROJECT_DIR=root),
                       timeout=30)
    if p.stdout.strip():
        return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"]
    return "allow" if p.returncode == 0 else "rc=%d" % p.returncode


miss = total = looser = 0
for path in sys.argv[1:]:
    for line in open(path):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        cid, tool, expect, text = [x.strip() for x in line.split("|||", 3)]
        text = text.replace("\\n", "\n") if tool == "Bash" and "\\n" in text and "<<" in text else text
        want = dict(zip("sd", expect.split("/") if "/" in expect else (expect, expect)))
        got = {k: decide(d, tool, text.replace("{ROOT}", d)) for k, d in COPIES}
        ok = got["r8s"] == want["s"] and got["r8d"] == want["d"]
        loos = any(RANK.get(got["r8" + p], 9) < RANK.get(got[r + p], 9) for p in "sd" for r in ("r7", "r6"))
        total += 1
        miss += not ok
        looser += loos
        print("%s%s %-6s %-6s want=%-10s r8: s=%-5s d=%-5s | r7: s=%-5s d=%-5s | r6: s=%-5s d=%-5s | %s" % (
            "ok  " if ok else "MISS", " LOOSER" if loos else "", os.path.basename(path)[:6], cid, expect,
            got["r8s"], got["r8d"], got["r7s"], got["r7d"], got["r6s"], got["r6d"], text[:140]))
print("cases %d; MISS (round 8 vs want) %d; LOOSER than round 7 or 6: %d" % (total, miss, looser))
