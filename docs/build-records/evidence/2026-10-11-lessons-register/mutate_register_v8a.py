"""Written by the round-8 verifier (its tools/mut19.py), kept as written.
Verifier round 8: own mutations of lessons-register.md, on copies only (the register
is read, never written; its sha256 is compared at the end). Each mutant is checked
with check_register.py and its changed region rendered with markdown-it-py
(CommonMark + GFM tables) to show how a reader sees it.
Expected: CATCH (a class round 8 claims), CATCH? (arguably claimed), LIMIT (stated), UNCLAIMED.
Usage: mut19.py <check_register.py> <register.md> <out dir>"""
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
PROSE = "startup memory footprint scales with live mempool size and accumulated disk cache"   # record's bold finding, in no quotation marks
PLAT04_1 = "  - A standing rule in the record, which does not say who set it: if this OOMs again, stop raising ceilings and bound the growth instead — " + OOM
PLAT04_LAST = "Shotdown or reduce RAM usage if necessary.” — 2026-10-03-upgrade-gates-round-2.md\n- **Port:**"
PLAT05 = "\n#### PLAT-05 — "
ROW2 = "| 2 | \"nothing should fail silently or be in a crash loop\" | 2026-08-10-crashloop-detection.md | HEAL-10 | Current |"
ROW3_REC = "| 2026-08-16-mempool-oom-recurrence.md | PLAT-04 | Current |"
SEC3_INTRO_END = "except row 119, whose text was corrected (its note gives the harvest's)."
HDR = "| # | Owner decision (verbatim) | Record(s) | Feeds | Status |"
EVID_INTRO = "honest about what it does not know.*\n"

def item(text):                       # PLAT-04's first Owner sub-item replaced by `text`
    return lambda t: once(t, PLAT04_1, "  - " + text + " — " + OOM)

def after_owner(extra):               # text after PLAT-04's last Owner item, before its Port field
    return lambda t: once(t, PLAT04_LAST, PLAT04_LAST.replace("\n- **Port:**", extra + "\n- **Port:**"))

def sec3_end(line):                   # a line appended directly under row 122 (no blank line)
    def f(t):
        i = t.index("\n\n## 4. Port candidates")
        return t[:i] + "\n" + line + t[i:]
    return f

M = []
# --- A: Owner-line quotation styles the round-8 claim says are read or reported ---
M.append(("A1", "CATCH", "straight single quotes '…' inside underscore emphasis: _'prose'_", item("_'" + PROSE + "'_")))
M.append(("A2", "CATCH", "the same in strong emphasis: __'prose'__", item("__'" + PROSE + "'__")))
M.append(("A3", "CATCH?", "curly ’…’ (reversed opener) inside underscore emphasis: _’prose’_", item("_’" + PROSE + "’_")))
M.append(("A4", "CATCH?", "a '…' opener glued to the previous word, closer after an s: said'…ceilings'",
          item("the owner said'if this OOMs again, we STOP raising ceilings'")))
M.append(("A0", "CATCH", "control: plain '…' around the same prose", item("'" + PROSE + "'")))
M.append(("A0b", "CATCH", "control: _\"prose\"_ (double quotes in emphasis)", item("_\"" + PROSE + "\"_")))
# --- B: blockquotes in an Owner section ---
M.append(("B1", "CATCH", "a blockquote opened after an ordered '1)' marker: '  1) > prose'",
          lambda t: once(t, PLAT04_1, "  1) > " + PROSE + " — " + OOM)))
M.append(("B2", "CATCH", "a blockquote after two list markers: '  - * > prose'", lambda t: once(t, PLAT04_1, "  - * > " + PROSE + " — " + OOM)))
M.append(("B3", "CATCH", "a blockquote after '- 1. ': '  - 1. > prose'", lambda t: once(t, PLAT04_1, "  - 1. > " + PROSE + " — " + OOM)))
M.append(("B0", "CATCH", "control: '  - > prose'", lambda t: once(t, PLAT04_1, "  - > " + PROSE + " — " + OOM)))
# --- C: where an Owner section ends ---
M.append(("C1", "CATCH", "a lazy continuation line starting '#2' (not a heading) inside the last Owner item", after_owner("\n#2 the owner also said “" + PROSE + "” — " + OOM)))
M.append(("C2", "CATCH", "a lazy continuation line starting '#owner:' (not a heading)", after_owner("\n#owner: “" + PROSE + "” — " + OOM)))
M.append(("C0", "CATCH", "control: the same line indented (no '#' at column 0)", after_owner("\n  #2 the owner also said “" + PROSE + "” — " + OOM)))
M.append(("C3", "UNCLAIMED", "a column-0 '- **“prose”**' bullet right after the Owner items (a sibling bullet)", after_owner("\n- **“" + PROSE + "”** — " + OOM)))
# --- D: Owner labels written another way ---
def label(lbl):
    return after_owner("\n" + lbl + " “" + PROSE + "” — " + OOM)
M.append(("D1", "CATCH", "a second Owner field, its O a Cyrillic О (U+041E): renders as Owner:", label("- **Оwner:**")))
M.append(("D2", "CATCH", "a second Owner field written **&#79;wner:** (an entity for O)", label("- **&#79;wner:**")))
M.append(("D3", "CATCH", "a second Owner field written <strong>Owner:</strong>", label("- <strong>Owner:</strong>")))
M.append(("D4", "CATCH", "a second Owner field with a soft hyphen inside: **Ow\\u00adner:**", label("- **Ow­ner:**")))
M.append(("D5", "CATCH", "a second Owner field with a zero-width space inside: **O\\u200bwner:**", label("- **O​wner:**")))
M.append(("D6", "CATCH?", "a second Owner field written **OWNER:**", label("- **OWNER:**")))
M.append(("D7", "CATCH?", "a second Owner field written **Owners:**", label("- **Owners:**")))
M.append(("D0", "CATCH", "control: a second Owner field written __Owner:__", label("- __Owner:__")))
M.append(("D8", "CATCH", "an Owner field written exactly `- **Owner:**` under an added '#### Notes' heading after PLAT-04",
          lambda t: once(t, PLAT05, "\n#### Notes\n\n- **Owner:** “" + PROSE + "” — " + OOM + "\n" + PLAT05)))
M.append(("D9", "CATCH?", "an Owner field written exactly `- **Owner:**` in the EVID theme intro (before the first ####)",
          lambda t: once(t, EVID_INTRO, EVID_INTRO + "\n- **Owner:** “" + PROSE + "” — " + OOM + "\n")))
# --- S: section 3 ---
M.append(("S1", "CATCH", "a pipe-less line between rows 2 and 3 (GFM renders it as a row)",
          lambda t: once(t, ROW2, ROW2 + "\n\"" + PROSE + "\" — the owner, " + OOM)))
M.append(("S2", "CATCH", "a pipe-less line directly under row 122", sec3_end("123 \"" + PROSE + "\" " + OOM)))
M.append(("S3", "CATCH", "a one-pipe line under row 122: '123 | \"prose\" — OOM'", sec3_end("123 | \"" + PROSE + "\" — " + OOM)))
M.append(("S4", "CATCH", "a one-pipe line under row 122: '| 123 \"prose\" OOM'", sec3_end("| 123 \"" + PROSE + "\" " + OOM)))
M.append(("S5", "CATCH", "a five-cell row whose first cell starts with '#': '| #123 | \"prose\" | … |'",
          sec3_end("| #123 | \"" + PROSE + "\" | " + OOM + " | PLAT-04 | Current |")))
M.append(("S6", "CATCH", "a row whose first cell starts with '---': '| --- \"prose\" | … |'",
          sec3_end("| --- \"" + PROSE + "\" | " + OOM + " | PLAT-04 | Current |")))
M.append(("S7", "CATCH", "row 3's Record(s) cell gains the record's prose in quotation marks as the owner's",
          lambda t: once(t, ROW3_REC, "| " + OOM + " — the owner: \"" + PROSE + "\" | PLAT-04 | Current |")))
M.append(("S8", "CATCH?", "an HTML table row in section 3 (renders as a row)",
          lambda t: once(t, "\n\n## 4. Port candidates", "\n\n<table><tr><td>123</td><td>\"" + PROSE + "\"</td><td>" + OOM + "</td></tr></table>\n\n## 4. Port candidates")))
M.append(("S9", "UNCLAIMED", "section 3's intro gains the record's prose as the owner's words",
          lambda t: once(t, SEC3_INTRO_END, SEC3_INTRO_END + " The owner said \"" + PROSE + "\" (" + OOM + ").")))
M.append(("S10", "UNCLAIMED", "section 3's header cell changed", lambda t: once(t, HDR, HDR.replace("Owner decision (verbatim)", "Owner decision (verbatim): \"" + PROSE + "\""))))
M.append(("S0", "CATCH", "control: a five-cell row 123 under row 122", sec3_end("| 123 | \"" + PROSE + "\" | " + OOM + " | PLAT-04 | Current |")))
M.append(("S0b", "CATCH", "control: a two-pipe row under row 122", sec3_end("| 123 \"" + PROSE + "\" |")))

def region(t, key):
    if key.startswith("S"):
        s = t.index("## 3. Owner decisions"); e = t.index("## 4. Port candidates")
        out = md.render(t[s:e])
        rows = re.findall(r"<tr>(.*?)</tr>", out, re.S)
        extra = [re.sub(r"\s+", " ", r) for r in rows if "startup memory footprint" in r]
        para = [re.sub(r"\s+", " ", p) for p in re.findall(r"<p>(.*?)</p>", out, re.S) if "startup memory footprint" in p]
        ths = re.findall(r"<th>(.*?)</th>", out)
        return "rendered: %d <tr> in section 3 (orig 123); rows with the prose: %s; paragraphs with it: %s; header: %s" % (
            len(rows), [x[:300] for x in extra], [x[:200] for x in para], ths[:2])
    if key in ("D8",):
        i = t.index("#### Notes"); return md.render(t[i:i + 400])
    if key == "D9":
        i = t.index("### EVID"); return md.render(t[i:t.index("#### EVID-01")])
    i = t.index("#### PLAT-04")
    a = t.index("**Owner:**", i) - 2
    b = t.index("- **Port:**", a)
    return md.render(t[a:b + 12])

os.makedirs(OUT, exist_ok=True)
res = {}
for key, expect, name, f in M:
    new = f(orig)
    assert new != orig, key
    p = os.path.join(OUT, key + ".md")
    open(p, "w").write(new)
    r = subprocess.run([sys.executable, "-B", CHK, p], capture_output=True, text=True)
    probs = [x for x in r.stdout.split("\n") if x.startswith(" - ")]
    res.setdefault(expect, [0, 0])[0 if r.returncode else 1] += 1
    print("%-6s %-4s expect %-9s %s  (exit %d, %d problem(s))" % ("CAUGHT" if r.returncode else "MISSED", key, expect, name, r.returncode, len(probs)))
    for x in probs:
        print("          ", x[:230])
    if r.stderr.strip():
        print("         stderr:", r.stderr.strip()[-300:])
    rend = region(new, key)
    rend = re.sub(r"\n+", " ", rend)
    if not key.startswith("S"):
        j = rend.find("startup memory footprint")
        rend = rend[max(0, j - 260): j + 160] if j >= 0 else rend[:300]
    print("           render:", rend)
print("\nby expectation (caught, missed):", res)
assert hashlib.sha256(open(REG).read().encode()).hexdigest() == sha0
print("register unchanged, sha256", sha0)
