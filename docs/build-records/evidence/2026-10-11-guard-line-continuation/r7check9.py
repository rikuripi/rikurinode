"""R7: every must-ask Bash example, put on a script's second line (a real newline inside
quotes) and after a \\n escape in a code string. Text only, in-process decide()."""
import importlib.util, json, sys, os, collections
S = os.path.dirname(os.path.abspath(__file__))
B = chr(92); N = chr(10); Q = chr(39); D = chr(34)
def load(name, root):
    spec = importlib.util.spec_from_file_location(name, root + "/.claude/hooks/guard.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
res = {}
for clone in sys.argv[1].split(","):
    root, prof = clone.split(":"); g = load("g" + prof, root); cfg = dict(g.load_config(), profile=prof)
    key = "expect" if cfg.get("profile") == "stable" else "expect_dev"
    def v(c):
        return g.decide({"tool_name": "Bash", "tool_input": {"command": c}, "cwd": g.ROOT}, cfg, g.ROOT, lock_present=False, branch_fn=lambda _c: "feature/x")[0]
    exs = [e["input"]["command"] for e in cfg["examples"] if e["tool"] == "Bash" and e.get(key) in ("ask", "deny")]
    exs = sorted(set(c for c in exs if N not in c and Q not in c and D not in c and B not in c))
    forms = {
      "2nd line of a quoted script": lambda c: "python3 -c " + Q + "import subprocess" + N + "subprocess.run(" + D + c + D + ", shell=True)" + Q,
      "after a \\n escape (python)": lambda c: "python3 -c " + Q + "import subprocess; subprocess.run(" + D + "ls" + B + "n" + c + D + ", shell=True)" + Q,
      "after a \\n escape (node)": lambda c: "node -e " + Q + "require(" + D + "child_process" + D + ").execSync(" + D + "ls" + B + "n" + c + D + ")" + Q,
      "one line in code": lambda c: "python3 -c " + Q + "import subprocess; subprocess.run(" + D + c + D + ", shell=True)" + Q,
    }
    lost = collections.defaultdict(list)
    for c in exs:
        base = v(c)
        if base == "allow":
            continue
        for fname, f in forms.items():
            if v(f(c)) == "allow":
                lost[fname].append(c)
    print("== %s (%s): %d single-line must-ask examples without quotes/backslashes" % (clone, key, len(exs)))
    for fname in forms:
        print("   %-30s allowed: %d" % (fname, len(lost[fname])))
        for c in lost[fname][:30]:
            print("        %r" % c)
