"""Written by the round-9 verifier (its tools/mut20b.py), kept as written.
Verifier round 9, second batch (same conventions as mut20.py).
Usage: mut20b.py <check_register.py> <register.md> <out dir>"""
import hashlib, os, re, subprocess, sys
from markdown_it import MarkdownIt
md = MarkdownIt("commonmark").enable("table")
CHK, REG, OUT = sys.argv[1:4]
orig = open(REG, newline="").read()
sha0 = hashlib.sha256(orig.encode()).hexdigest()
OOM = "2026-08-16-mempool-oom-recurrence.md"
PROSE = "startup memory footprint scales with live mempool size and accumulated disk cache"
def rule(extra):
    def f(t):
        i = t.index("#### PLAT-04"); a = t.index("- **Rule:**", i); e = t.index("\n", a)
        return t[:e] + extra + t[e:]
    return f
M = [
 ("A1b", "CATCH?", "a carriage return (U+000D) followed by an indent inside PLAT-04's Rule line (CR is outside the claimed alphabet)", rule("\r  (the owner)")),
 ("A1c", "CATCH?", "CRLF line endings for the whole file", lambda t: t.replace("\n", "\r\n")),
 ("A1d", "CTRL", "control: a tab (U+0009) inside PLAT-04's Rule line", rule("\t(the owner)")),
]
os.makedirs(OUT, exist_ok=True)
for key, expect, name, f in M:
    new = f(orig); assert new != orig
    p = os.path.join(OUT, key + ".md"); open(p, "w", newline="").write(new)
    r = subprocess.run([sys.executable, "-B", CHK, p], capture_output=True, text=True)
    probs = [x for x in r.stdout.split("\n") if x.startswith(" - ")]
    print("%-6s %-4s expect %-7s %s  (exit %d, %d problem(s))" % ("CAUGHT" if r.returncode else "MISSED", key, expect, name, r.returncode, len(probs)))
    for x in probs[:5]: print("          ", x[:200])
    if key == "A1b":
        i = new.index("#### PLAT-04"); h = md.render(new[i:new.index("- **Why:**", i)]); j = h.find("(the owner)"); print("           render:", h[j-120:j+40].replace("\n", "\\n"))
assert hashlib.sha256(open(REG, newline="").read().encode()).hexdigest() == sha0
print("register unchanged, sha256", sha0)
