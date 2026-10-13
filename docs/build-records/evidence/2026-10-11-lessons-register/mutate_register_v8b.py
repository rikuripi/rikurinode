"""Written by the round-8 verifier (its tools/mut19b.py), kept as written.
Verifier round 8, second batch: own mutations on copies (register read only).
Usage: mut19b.py <check_register.py> <register.md> <out dir>"""
import hashlib, os, re, subprocess, sys
from markdown_it import MarkdownIt
md = MarkdownIt("commonmark").enable("table")
CHK, REG, OUT = sys.argv[1:4]
orig = open(REG).read()
sha0 = hashlib.sha256(orig.encode()).hexdigest()

def once(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:80])
    return t.replace(old, new)

OOM = "2026-08-16-mempool-oom-recurrence.md"
DRB = "2026-09-16-drb-attempt-budget-and-escalation.md"
PROSE = "startup memory footprint scales with live mempool size and accumulated disk cache"
DRB_PROSE = "budget spent → skip that hypothesis and continue down the ladder"
HEAL03 = "- **Owner:** the owner's decision as the record gives it (asked, not quoted): budget spent → skip that hypothesis and continue down the ladder (escalate only when all are spent), and a 24-hour rolling window — " + DRB
PLAT04_1 = "  - A standing rule in the record, which does not say who set it: if this OOMs again, stop raising ceilings and bound the growth instead — " + OOM
PLAT04_SUP = "was later superseded by 2026-08-16-mempool-oom-recurrence.md.\n"
EVID03_OWN = "- **Owner:** “Yes, in fact, check all measurement on the Dashboard."
ROW3_REC = "| 2026-08-16-mempool-oom-recurrence.md | PLAT-04 | Current |"

M = []
M.append(("E1", "CATCH", "straight \"…\" between unmatched backtick runs (``` … `): the checker pairs them as a code span, CommonMark does not",
          lambda t: once(t, PLAT04_1, "  - ``` \"" + PROSE + "\" ` — " + OOM)))
M.append(("E2", "CATCH", "the same with runs ` … ``` ", lambda t: once(t, PLAT04_1, "  - ` \"" + PROSE + "\" ``` — " + OOM)))
M.append(("E0", "LIMIT", "control: straight \"…\" inside a real code span (stated limit)", lambda t: once(t, PLAT04_1, "  - `\"" + PROSE + "\"` — " + OOM)))
M.append(("A1t", "CATCH", "HEAL-03's top-level Owner line: _'…'_ around the record's prose",
          lambda t: once(t, HEAL03, "- **Owner:** _'" + DRB_PROSE + "'_ — " + DRB)))
M.append(("D3b", "CATCH", "a field <strong>Owner:</strong> after PLAT-04's last field (not inside an Owner section)",
          lambda t: once(t, PLAT04_SUP, PLAT04_SUP + "- <strong>Owner:</strong> “" + PROSE + "” — " + OOM + "\n")))
M.append(("D1b", "CATCH", "PLAT-04's own Owner label with a Cyrillic О, its first item the record's prose",
          lambda t: once(t, "- **Owner:**\n" + PLAT04_1, "- **Оwner:**\n  - “" + PROSE + "” — " + OOM)))
def c4(t):
    i = t.index("#### EVID-03"); a = t.index(EVID03_OWN, i)
    return t[:a] + "- **Owner:** the owner, in\n#1 of the answers: “" + PROSE + "” — " + OOM + "; and " + t[a + len("- **Owner:** "):]
M.append(("C4", "CATCH", "EVID-03's one-line Owner field wrapped so a column-0 line starts '#1' (lazy continuation), with the record's prose quoted", c4))
M.append(("E1t", "CATCH", "HEAL-03's top-level Owner line: straight \"…\" between unmatched backtick runs (``` … `)",
          lambda t: once(t, HEAL03, "- **Owner:** ``` \"" + DRB_PROSE + "\" ` — " + DRB)))
M.append(("E2t", "CATCH", "HEAL-03's top-level Owner line: runs ` … ```", lambda t: once(t, HEAL03, "- **Owner:** ` \"" + DRB_PROSE + "\" ``` — " + DRB)))
M.append(("E0t", "LIMIT", "control: HEAL-03, straight \"…\" inside a real code span (stated limit)", lambda t: once(t, HEAL03, "- **Owner:** `\"" + DRB_PROSE + "\"` — " + DRB)))
M.append(("S7", "CATCH", "row 3's Record(s) cell gains the record's prose in quotation marks as the owner's",
          lambda t: once(t, ROW3_REC, "| " + OOM + " — the owner: \"" + PROSE + "\" | PLAT-04 | Current |")))

def show(t, key):
    if key == "S7":
        s = t.index("## 3. Owner decisions"); e = t.index("## 4. Port candidates")
        rows = re.findall(r"<tr>(.*?)</tr>", md.render(t[s:e]), re.S)
        return re.sub(r"\s+", " ", [r for r in rows if "<td>3</td>" in r][0])
    if key in ("A1t", "E1t", "E2t", "E0t"):
        i = t.index("#### HEAL-03"); a = t.index("- **Owner:**", i); return md.render(t[a:t.index("\n", a)])
    if key == "C4":
        i = t.index("#### EVID-03"); a = t.index("- **Owner:** the owner, in", i); b = t.index("#### EVID-04", a); return md.render(t[a:b])
    i = t.index("#### PLAT-04"); a = t.index("wner:**", i) - 6; b = t.index("#### PLAT-05", a); return md.render(t[a:b])

os.makedirs(OUT, exist_ok=True)
for key, expect, name, f in M:
    new = f(orig); assert new != orig, key
    p = os.path.join(OUT, key + ".md"); open(p, "w").write(new)
    r = subprocess.run([sys.executable, "-B", CHK, p], capture_output=True, text=True)
    probs = [x for x in r.stdout.split("\n") if x.startswith(" - ")]
    print("%-6s %-4s expect %-9s %s  (exit %d, %d problem(s))" % ("CAUGHT" if r.returncode else "MISSED", key, expect, name, r.returncode, len(probs)))
    for x in probs:
        print("          ", x[:230])
    rend = re.sub(r"\n+", " ", show(new, key))
    j = max(rend.find("startup memory"), rend.find("budget spent"), rend.find("infra bar"))
    print("           render:", rend[max(0, j - 200): j + 220] if j >= 0 else rend[:400])
assert hashlib.sha256(open(REG).read().encode()).hexdigest() == sha0
print("register unchanged, sha256", sha0)
