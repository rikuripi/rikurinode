import hashlib, subprocess, sys
P = ".claude/hooks/guard.py"
orig = open(P, "rb").read()
h = hashlib.sha256(orig).hexdigest()
src = orig.decode()
MUTANTS = {
 "M1 no join": ('            if cmd[i + 1] == "\\n":  # a line continuation: the shell joins the two lines\n                i += 2\n                continue\n', ''),
 "M2 join inside single quotes": ('if c == "\\\\" and quote != "\'" and not comment', 'if c == "\\\\" and not comment'),
 "M3 join inside a comment": ('if c == "\\\\" and quote != "\'" and not comment', 'if c == "\\\\" and quote != "\'"'),
 "M4 no comments": ('                comment = True\n', '                pass\n'),
 "M5 quotes open in comments": ('elif c in "\'\\"" and not comment:', 'elif c in "\'\\"":'),
 "M6 \\\" ends a double quote": ('if quote is None or cmd[i + 1] in "\\"\\\\$`":', 'if quote is None:'),
 "M7 comment never ends": ('            if c == "\\n":\n                comment = False\n', ''),
 "M8 # mid-word starts a comment": ('if c == "#" and (not cur or cur[-1][-1] in WORD_BREAK):', 'if c == "#":'),
}
out = []
try:
    for name, (a, b) in MUTANTS.items():
        assert src.count(a) == 1, (name, src.count(a))
        open(P, "w").write(src.replace(a, b))
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"],
                           capture_output=True, text=True)
        last = [l for l in r.stderr.splitlines() if l.startswith(("FAILED", "OK"))]
        fails = sorted({l.split("(")[0].split(":")[1].strip() for l in r.stderr.splitlines() if l.startswith(("FAIL:", "ERROR:"))})
        out.append("%-32s %s %s" % (name, "RED  " if r.returncode else "GREEN", (last[-1] if last else "") + " " + ",".join(fails)))
finally:
    open(P, "wb").write(orig)
    assert hashlib.sha256(open(P, "rb").read()).hexdigest() == h
print("\n".join(out)); print("restored, sha256", h[:12])
