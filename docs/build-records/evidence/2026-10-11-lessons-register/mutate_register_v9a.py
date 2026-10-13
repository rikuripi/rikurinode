"""Written by the round-9 verifier (its tools/mut20.py), kept as written.
Verifier round 9: own mutations of lessons-register.md on copies (register read only;
sha256 compared at the end). Each mutant is run through check_register.py and the changed
region rendered with markdown-it-py (CommonMark + tables) to show what a reader sees.
Expect: CATCH (in a class round 9 claims), CATCH? (arguably claimed), LIMIT (stated),
UNCLAIMED (not claimed), CTRL (a control that must be caught).
Usage: mut20.py <check_register.py> <register.md> <out dir>"""
import hashlib, os, re, subprocess, sys
from markdown_it import MarkdownIt
md = MarkdownIt("commonmark").enable("table")
CHK, REG, OUT = sys.argv[1:4]
orig = open(REG, newline="").read()
sha0 = hashlib.sha256(orig.encode()).hexdigest()

def once(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:80])
    return t.replace(old, new)

OOM = "2026-08-16-mempool-oom-recurrence.md"
DRB = "2026-09-16-drb-attempt-budget-and-escalation.md"
PROSE = "startup memory footprint scales with live mempool size and accumulated disk cache"
DRB_PROSE = "budget spent → skip that hypothesis and continue down the ladder"
PLAT04_1 = "  - A standing rule in the record, which does not say who set it: if this OOMs again, stop raising ceilings and bound the growth instead — " + OOM
PLAT04_LAST = "Shotdown or reduce RAM usage if necessary.” — 2026-10-03-upgrade-gates-round-2.md\n- **Port:**"
PLAT04_SUP = "was later superseded by 2026-08-16-mempool-oom-recurrence.md.\n"
PLAT04_RULE_END = None
HEAL03 = "- **Owner:** the owner's decision as the record gives it (asked, not quoted): budget spent → skip that hypothesis and continue down the ladder (escalate only when all are spent), and a 24-hour rolling window — " + DRB
SEC5_INTRO_END = "each gap needs its own evidence first.\n"
ROW122_END = "| 2026-10-10-upgrades-survive-code-updates.md | UPG-08 | Current |\n"
CONTENTS = "\n## Contents\n"

def item(text):            # PLAT-04's first Owner sub-item replaced by `text`
    return lambda t: once(t, PLAT04_1, "  - " + text + " — " + OOM)
def heal(text):            # HEAL-03's one-line Owner field replaced
    return lambda t: once(t, HEAL03, "- **Owner:** " + text + " — " + DRB)
def after_owner(extra):    # right after PLAT-04's last Owner item, before its Port field
    return lambda t: once(t, PLAT04_LAST, PLAT04_LAST.replace("\n- **Port:**", extra + "\n- **Port:**"))
def after_sup(extra):      # right after PLAT-04's last field (Superseded), still in its body
    return lambda t: once(t, PLAT04_SUP, PLAT04_SUP + extra + "\n")
def after_port(extra):     # an indented sub-item under PLAT-04's Port field (before its Superseded field)
    return lambda t: once(t, "\n- **Superseded / caveat:** The lesson \"runtime default heap", extra + "\n- **Superseded / caveat:** The lesson \"runtime default heap")
def sec5(par):             # a new paragraph in section 5, after its introduction
    return lambda t: once(t, SEC5_INTRO_END, SEC5_INTRO_END + "\n" + par + "\n")
def intro(par):            # a new paragraph before the Contents (before the first ####)
    return lambda t: once(t, CONTENTS, "\n" + par + "\n" + CONTENTS)
def rule(extra):           # appended to PLAT-04's Rule line
    def f(t):
        i = t.index("#### PLAT-04"); a = t.index("- **Rule:**", i); e = t.index("\n", a)
        return t[:e] + extra + t[e:]
    return f
def field(name, extra):    # appended to a PLAT-04 field line
    def f(t):
        i = t.index("#### PLAT-04"); a = t.index("- **%s:**" % name, i); e = t.index("\n", a)
        return t[:e] + extra + t[e:]
    return f
def after_table(par):      # a paragraph after section 3's table (after its blank line)
    return lambda t: once(t, ROW122_END + "\n## 4.", ROW122_END + "\n" + par + "\n\n## 4.")
def status43(new):
    def f(t):
        i = t.index("\n| 43 | AskUserQuestion"); e = t.index("\n", i + 1)
        line = t[i:e]; assert line.endswith("| Current |")
        return t[:i] + line[:-len("Current |")] + new + " |" + t[e:]
    return f

M = []
# --- T: the whole file's HTML tags (claimed closed: <a id>, </a>, <br> outside code spans) ---
M.append(("T0", "CTRL", "control: <q>prose</q> in PLAT-04's Rule line", rule(" <q>" + PROSE + "</q>")))
M.append(("T1", "CATCH", "<q>prose</q> between backslash-escaped backticks (\\`…\\`, no code span in Markdown) in PLAT-04's Rule line",
          rule(" \\`<q>" + PROSE + "</q>\\`")))
M.append(("T2", "CATCH", "<q>prose</q> between two backticks that sit in link destinations ([](x`) … [](y`)), in a section-5 paragraph",
          sec5("The owner, on the record:[](x`) <q>" + PROSE + "</q> (" + OOM + ")[](y`)")))
M.append(("T3", "CATCH", "<i>“prose”</i> hidden the same way in PLAT-04's Rule line", rule(" [](x`)<i>the owner: “" + PROSE + "”</i>[](y`)")))
M.append(("T4", "CATCH", "section 3 row 43's Status cell: <q>prose</q> between escaped backticks (Status is unchecked, the tag set is file-wide)",
          status43("Current \\`<q>" + PROSE + "</q>\\`")))
# --- C: code spans in Owner lines (claimed: backtick runs of equal length; quotations outside code spans read) ---
M.append(("C0", "CTRL", "control: straight \"prose\" plain in PLAT-04's Owner item", item("\"" + PROSE + "\"")))
M.append(("C0b", "LIMIT", "control: straight \"prose\" inside a real code span (E0t, stated)", item("`\"" + PROSE + "\"`")))
M.append(("C1", "CATCH", "straight \"prose\" between backticks that sit in link destinations [](x`)…[](y`): Markdown has no code span there",
          item("[](x`)\"" + PROSE + "\"[](y`)")))
M.append(("C2", "CATCH", "the same with straight '…'", item("[](x`)'" + PROSE + "'[](y`)")))
M.append(("C3", "CATCH", "HEAL-03's top-level Owner line: [](x`)\"…\"[](y`) around the record's prose",
          heal("[](x`)\"" + DRB_PROSE + "\"[](y`)")))
M.append(("C6", "CATCH", "PLAT-04 sub-item, the pair after ' — ' (so the port-path check does not read it): per the record — [](x`)\"prose\"[](y`)",
          item("per the record — [](x`)\"" + PROSE + "\"[](y`)")))
M.append(("C4", "CTRL", "control: curly “prose” in the same link-destination pair (curly marks in a 'code span' are reported)",
          item("[](x`)“" + PROSE + "”[](y`)")))
M.append(("C5", "CATCH", "visible link text: [the owner](x`) said \"prose\" [.](y`)", item("[the owner](x`) said \"" + PROSE + "\" [.](y`)")))
# --- H: #### headings and a requirement's body (claimed: every #### a requirement; body only its six fields at column 0) ---
M.append(("H0", "CTRL", "control: '#### Owner' at column 0 after PLAT-04, then an indented bullet with the prose",
          after_sup("#### Owner\n  - “" + PROSE + "” — " + OOM)))
M.append(("H1", "CATCH", "' #### Owner' indented one space (still an h4 in Markdown), then an indented bullet with the prose",
          after_sup(" #### Owner\n  - “" + PROSE + "” — " + OOM)))
M.append(("H1b", "CATCH", "'   #### Owner' indented three spaces", after_sup("   #### Owner\n  - “" + PROSE + "” — " + OOM)))
M.append(("H2", "CATCH", "a '#x' line (not a heading; a lazy continuation) then a column-0 bullet 'The owner: “prose”' in PLAT-04's body",
          after_sup("#x\n- The owner: “" + PROSE + "” — " + OOM)))
M.append(("H2c", "CTRL", "control: the same bullet with no '#x' line before it", after_sup("- The owner: “" + PROSE + "” — " + OOM)))
M.append(("H3", "CATCH?", "an empty anchor line <a id=\"x\"></a> then a column-0 bullet 'The owner: “prose”' in PLAT-04's body",
          after_sup("<a id=\"x\"></a>\n- The owner: “" + PROSE + "” — " + OOM)))
M.append(("H4", "CATCH?", "an empty '####' heading (renders as an empty h4) after PLAT-04", after_sup("####\n\n“" + PROSE + "” — " + OOM)))
M.append(("H5", "CATCH?", "'##### Owner' (h5) then the prose in “…” at column 0, inside PLAT-04's block", after_sup("##### Owner\n\n“" + PROSE + "” — " + OOM)))
M.append(("H6", "CATCH?", "a seventh field: a second '- **Rule:**' at column 0 giving the prose as the owner's", after_sup("- **Rule:** the owner: “" + PROSE + "” — " + OOM)))
# --- L: Owner labels (claimed: any other spelling or case reported) ---
M.append(("L0", "CTRL", "control: '- **owner:**' (case) in section 5", sec5("- **owner:** “" + PROSE + "” — " + OOM)))
M.append(("L1", "CATCH", "'- **0wner:**' (digit zero for O) in section 5", sec5("- **0wner:** “" + PROSE + "” — " + OOM)))
M.append(("L1b", "CATCH", "'  - **0wner:**' as an indented sub-item under PLAT-04's Port field", after_port("\n  - **0wner:** “" + PROSE + "” — " + OOM)))
M.append(("L2", "CATCH", "'- **Ovvner:**' (vv for w) in section 5", sec5("- **Ovvner:** “" + PROSE + "” — " + OOM)))
M.append(("L3", "CATCH?", "'- ***Owner:***' (bold italic) before the first requirement", intro("- ***Owner:*** “" + PROSE + "” — " + OOM)))
M.append(("L3b", "CATCH?", "'- ***Owner:***' in section 5", sec5("- ***Owner:*** “" + PROSE + "” — " + OOM)))
M.append(("L4", "CATCH?", "'- **Ow**ner:' (bold split inside the word) in section 5", sec5("- **Ow**ner: “" + PROSE + "” — " + OOM)))
M.append(("L5", "CATCH?", "'- **_Owner:_**' in section 5", sec5("- **_Owner:_** “" + PROSE + "” — " + OOM)))
M.append(("L6", "CATCH?", "'- _**Owner:**_' before the first requirement", intro("- _**Owner:**_ “" + PROSE + "” — " + OOM)))
M.append(("L7", "CATCH?", "'- [**Owner:**](#own)' (linked label) before the first requirement", intro("- [**Owner:**](#own) “" + PROSE + "” — " + OOM)))
M.append(("L8", "CATCH?", "'- **`Owner:`**' (code inside bold) in section 5", sec5("- **`Owner:`** “" + PROSE + "” — " + OOM)))
M.append(("L9", "UNCLAIMED", "'- **The owner:**' in section 5", sec5("- **The owner:** “" + PROSE + "” — " + OOM)))
M.append(("L10", "CATCH?", "'Owner:' as a plain label, no emphasis, in section 5", sec5("- Owner: “" + PROSE + "” — " + OOM)))
# --- E: quotations in emphasis (claimed read) ---
M.append(("E1", "CATCH", "***'prose'*** in PLAT-04's Owner item", item("***'" + PROSE + "'***")))
M.append(("E2", "CATCH", "~~“prose”~~ (strikethrough)", item("~~“" + PROSE + "”~~")))
M.append(("E3", "CATCH", "*‘prose’* in HEAL-03's Owner line", heal("*‘" + DRB_PROSE + "’*")))
# --- O: where an Owner section ends (claimed: only at a real heading) ---
M.append(("O1", "CATCH", "an empty heading '  #' INSIDE the Owner item (2-space indent), then '  - “prose”' still inside the Owner field",
          after_owner("\n  #\n  - “" + PROSE + "” — " + OOM)))
M.append(("O2", "CATCH", "'  ###### Also, from the record:' inside the Owner item, then '  - “prose”'",
          after_owner("\n  ###### Also, from the record:\n  - “" + PROSE + "” — " + OOM)))
M.append(("O3", "CATCH", "an empty heading '  #' inside the Owner item, then a blockquote '  > prose' inside the Owner field",
          after_owner("\n  #\n  > " + PROSE + " — " + OOM)))
M.append(("O4", "CATCH", "a thematic break '  ---' inside the Owner item, then '  - “prose”'", after_owner("\n  ---\n  - “" + PROSE + "” — " + OOM)))
M.append(("O5", "CTRL", "control: '  - “prose”' as a plain last Owner item", after_owner("\n  - “" + PROSE + "” — " + OOM)))
# --- S: section 3 ---
M.append(("S1", "UNCLAIMED", "a paragraph after section 3's table (not its introduction) giving the prose as the owner's",
          after_table("The owner also said \"" + PROSE + "\" (" + OOM + ").")))
M.append(("S2", "CTRL", "control: a whitespace-only line, then a five-cell row 123", lambda t: once(t, ROW122_END, ROW122_END + "   \n| 123 | \"" + PROSE + "\" | " + OOM + " | PLAT-04 | Current |\n")))
# --- R: fields the checker does not read (round 9 states only Why lines and section 3's intro) ---
M.append(("R1", "UNCLAIMED", "PLAT-04's Rule line: '(the owner: “prose”)'", rule(" (the owner: “" + PROSE + "”, " + OOM + ")")))
M.append(("R2", "UNCLAIMED", "PLAT-04's Tripwire line: 'the owner asked for “prose”'", field("Tripwire", " The owner asked for “" + PROSE + "” (" + OOM + ").")))
M.append(("R3", "UNCLAIMED", "section 5 paragraph: 'The owner said “prose”'", sec5("The owner said “" + PROSE + "” (" + OOM + ").")))
# --- A: alphabet (claimed: printable ASCII and 14 characters, whole file) ---
M.append(("A1", "CATCH?", "a carriage return (U+000D) inside PLAT-04's Rule line", rule("\r(the owner)")))
M.append(("A2", "CTRL", "control: a form feed (U+000C) inside PLAT-04's Rule line", rule("\x0c(the owner)")))
M.append(("A3", "UNCLAIMED", "ASCII double angle brackets with spaces '<< prose >>' in PLAT-04's Owner item", item("<< " + PROSE + " >>")))

def region(t, key):
    if key.startswith("T4") or key.startswith("S"):
        s = t.index("## 3. Owner decisions"); e = t.index("## 4. Port candidates")
        out = md.render(t[s:e])
        hits = [re.sub(r"\s+", " ", x) for x in re.findall(r"<(?:tr|p)>(.*?)</(?:tr|p)>", out, re.S) if "startup memory" in x]
        return "rendered: %s" % [h[-320:] for h in hits]
    if key.startswith("T2") or key.startswith("L") and key not in ("L1b",) or key.startswith("R3"):
        if key in ("L3", "L6", "L7"):
            return md.render(t[:t.index("## Contents")])
        i = t.index("## 5. Gaps"); return md.render(t[i:t.index("| # | Gap")])
    if key.startswith("C3") or key.startswith("E3"):
        i = t.index("#### HEAL-03"); return md.render(t[i:t.index("#### HEAL-04")])
    i = t.index("#### PLAT-04"); return md.render(t[i:t.index("#### PLAT-05")])

os.makedirs(OUT, exist_ok=True)
res = {}
for key, expect, name, f in M:
    new = f(orig)
    assert new != orig, key
    p = os.path.join(OUT, key + ".md")
    open(p, "w", newline="").write(new)
    r = subprocess.run([sys.executable, "-B", CHK, p], capture_output=True, text=True)
    probs = [x for x in r.stdout.split("\n") if x.startswith(" - ")]
    res.setdefault(expect, [0, 0])[0 if r.returncode else 1] += 1
    print("%-6s %-4s expect %-9s %s  (exit %d, %d problem(s))" % ("CAUGHT" if r.returncode else "MISSED", key, expect, name, r.returncode, len(probs)))
    for x in probs:
        print("          ", x[:230])
    if r.stderr.strip():
        print("         stderr:", r.stderr.strip()[-300:])
    rend = re.sub(r"\n+", " ", region(new, key))
    j = rend.find("startup memory") if "startup memory" in rend else rend.find("budget spent")
    if j < 0:
        j = rend.find("the owner")
    print("           render:", rend[max(0, j - 300): j + 200] if j >= 0 else rend[:400])
print("\nby expectation (caught, missed):", res)
assert hashlib.sha256(open(REG, newline="").read().encode()).hexdigest() == sha0
print("register unchanged, sha256", sha0)
