"""Written by the round-12 verifier (its tools/mut31.py), kept as written but for
T69a and T69b's anchors: round 13 wrote row 69's two bare test names as full paths.
Verifier round 12 (rn-verify31): mutations on copies only, aimed at the round-12
wording "the paths in section 4's table" and "the main path of each Port line".
The register is read, never written; its sha256 is compared at the end.
Expect: CATCH (a listed item), UNCLAIMED (not claimed either way), PROBE (tests the wording).
Usage: mut31.py <check_register.py> <register.md> <out dir>"""
import hashlib, os, subprocess, sys
CHK, REG, OUT = sys.argv[1:4]
orig = open(REG, newline="").read()
sha0 = hashlib.sha256(orig.encode()).hexdigest()
ROW69 = next(l for l in orig.split("\n") if l.startswith("| 69 | `dashboard/backend/src/ai/slimKnowledge.ts`"))
def row69(old, new):
    def f(t):
        assert ROW69.count(old) == 1, old
        assert t.count(ROW69) == 1
        return t.replace(ROW69, ROW69.replace(old, new))
    return f
M = [
 ("T69a", "PROBE", "row 69's tests cell: 'cardBlend.test.ts' renamed to one that does not exist",
  row69("; dashboard/backend/src/tests/cardBlend.test.ts;", "; dashboard/backend/src/tests/cardBlendGone.test.ts;")),
 ("T69b", "PROBE", "row 69's tests cell: 'cardRanking.test.ts' renamed to one that does not exist",
  row69("; dashboard/backend/src/tests/cardRanking.test.ts;", "; dashboard/backend/src/tests/cardRankingGone.test.ts;")),
 ("T69c", "CATCH", "control: row 69's tests cell, the full path slimKnowledge.test.ts renamed",
  row69("dashboard/backend/src/tests/slimKnowledge.test.ts;", "dashboard/backend/src/tests/slimKnowledgeGone.test.ts;")),
 ("P69", "CATCH", "control: row 69's Old path cell renamed",
  row69("`dashboard/backend/src/ai/slimKnowledge.ts`", "`dashboard/backend/src/ai/slimKnowledgeGone.ts`")),
 ("T69d", "PROBE", "row 69's tests cell: a full test path moved into a bracketed note and renamed",
  row69("dashboard/backend/src/tests/slimKnowledge.test.ts;", "dashboard/backend/src/tests/slimKnowledge.test.ts (with dashboard/backend/src/tests/nowhere.test.ts);")),
]
os.makedirs(OUT, exist_ok=True)
for key, exp, what, fn in M:
    t = fn(orig)
    assert t != orig, key
    p = os.path.join(OUT, key + ".md")
    open(p, "w", newline="").write(t)
    r = subprocess.run([sys.executable, "-B", CHK, p], capture_output=True, text=True)
    probs = [l for l in r.stdout.split("\n") if l.startswith(" - ")]
    n = r.stdout.strip().split("\n")
    tag = "CAUGHT" if r.returncode != 0 else "MISSED"
    print("%s %-6s expect %-9s %s  (exit %d, %d problem(s))" % (tag, key, exp, what, r.returncode, len(probs)))
    for l in probs:
        print("   " + l)
    if r.stderr.strip():
        print("   stderr: " + r.stderr.strip().split("\n")[-1])
    os.remove(p)
now = hashlib.sha256(open(REG, newline="").read().encode()).hexdigest()
print("register unchanged, sha256", now) if now == sha0 else print("REGISTER CHANGED", sha0, now)
