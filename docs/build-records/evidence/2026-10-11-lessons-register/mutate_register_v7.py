"""Written by the round-7 verifier (its tools/mut17.py), kept as written. Verifier round 7: my own mutations of lessons-register.md, on copies only (the register is read,
never written; its sha256 is compared at the end).
Expected per case: CATCH (a class round 7 claims), LIMIT (a stated limit), UNCLAIMED (no claim either way).
Usage: mut17.py <check_register.py> <register.md> <out dir>"""
import hashlib, os, subprocess, sys, unicodedata
CHK, REG, OUT = sys.argv[1:4]
orig = open(REG).read()
sha0 = hashlib.sha256(orig.encode()).hexdigest()

def once(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:80])
    return t.replace(old, new)

OOM = "2026-08-16-mempool-oom-recurrence.md"
MEM = "2026-09-26-mempool-api-memory.md"
PROSE = "startup memory footprint scales with live mempool size and accumulated disk cache"  # record's bold finding, quoted nowhere
PROSE_S = "if this OOMs again, we STOP raising ceilings"   # record's prose (Skipped items), not in quotation marks; ends in "s"
PLAT04_1 = "  - A standing rule in the record, which does not say who set it: if this OOMs again, stop raising ceilings and bound the growth instead — " + OOM
PLAT04_LAST = "Shotdown or reduce RAM usage if necessary.” — 2026-10-03-upgrade-gates-round-2.md\n- **Port:**"
HEAL03 = "- **Owner:** the owner's decision as the record gives it (asked, not quoted): budget spent → skip that hypothesis and continue down the ladder (escalate only when all are spent), and a 24-hour rolling window — 2026-09-16-drb-attempt-budget-and-escalation.md"
DRB = "2026-09-16-drb-attempt-budget-and-escalation.md"
DRB_PROSE = "budget spent → skip that hypothesis and continue down the ladder"
ROW43 = "| 2026-09-29-market-intel-freshness-arkb.md | EVID-06 | Current |"
ROW44_START = "| 44 | \"Need to replace GBTC"
EVID03_A = "Make sure every one of them is actually meansuring"

def item(o, c, prose=PROSE):     # a PLAT-04 Owner sub-item quoting the record's prose in marks o … c
    return lambda t: once(t, PLAT04_1, "  - " + o + prose + c + " — " + OOM)

def top(o, c):                   # HEAL-03's top-level Owner line, the record's bold prose in marks o … c
    return lambda t: once(t, HEAL03, "- **Owner:** " + o + DRB_PROSE + c + " — " + DRB)

def after_owner(extra):          # text placed after PLAT-04's last Owner item, before its Port field
    return lambda t: once(t, PLAT04_LAST, PLAT04_LAST.replace("\n- **Port:**", extra + "\n- **Port:**"))

def sec3_end(row):               # a line appended at the end of section 3's table
    def f(t):
        i = t.index("\n\n## 4. Port candidates")
        return t[:i] + "\n" + row + t[i:]
    return f

M = []
# --- Q: quotation styles the closed-world claim says are reported (Unicode characters named as quotation marks) ---
seen = set()
read = set("\"“”‘’'")
for cp in list(range(0x20, 0x3000 + 0x100)) + list(range(0xFE00, 0xFF10)) + list(range(0x1F670, 0x1F680)):
    c = chr(cp)
    n = unicodedata.name(c, "")
    if ("QUOTATION MARK" in n or "PRIME" in n) and c not in read and c not in seen:
        seen.add(c)
        M.append(("QU-%04X" % cp, "CATCH", "%s…%s (U+%04X %s) around the record's prose" % (c, c, cp, n), item(c, c)))
for k, (o, c, what) in enumerate([("〝", "〞", "CJK double prime quotation marks 〝…〞"), ("「", "」", "CJK corner brackets 「…」 (Japanese quotation marks)"),
                   ("『", "』", "CJK white corner brackets 『…』"), ("‟", "”", "‟…” (high-reversed-9 opener)"),
                   ("❝", "❞", "heavy ornament quotation marks ❝…❞"), ("❛", "❜", "heavy single ornament quotation marks ❛…❜"),
                   ("‵", "′", "reversed prime ‵…′"), ("‶", "″", "‶…″ reversed double prime then double prime"),
                   ("<<", ">>", "ASCII guillemets <<…>>"), ("≪", "≫", "much-less/greater-than as guillemets ≪…≫")], 1):
    M.append(("QP%d" % k, "CATCH", what, item(o, c)))
# the possessive hole: a closing mark after a word ending in s is dropped as an apostrophe
M.append(("QH1", "CATCH", "`…' (TeX/GNU style), the closing ' after an s", item("`", "'", PROSE_S)))
M.append(("QH2", "CATCH", "‛…’ (U+201B opener), the closing ’ after an s", item("‛", "’", PROSE_S)))
M.append(("QH3", "CATCH", "′…’ (prime opener), the closing ’ after an s", item("′", "’", PROSE_S)))
M.append(("QH4", "CATCH", "control: ‘…’ around the same s-ending prose", item("‘", "’", PROSE_S)))
# --- H: HTML entities and markup ---
for o, c in [("&lsaquo;", "&rsaquo;"), ("&OpenCurlyDoubleQuote;", "&CloseCurlyDoubleQuote;"), ("&OpenCurlyQuote;", "&CloseCurlyQuote;"),
             ("&ldquor;", "&rdquor;"), ("&lsquor;", "&rsquor;"), ("&apos;", "&apos;"), ("&Prime;", "&Prime;"), ("&prime;", "&prime;"),
             ("&ldquo;", "&rdquo;")]:
    M.append(("HE-" + o.strip("&;")[:14].replace("/", ""), "CATCH", "HTML entities %s…%s" % (o, c), item(o, c)))
M.append(("HT1", "CATCH", "<blockquote>…</blockquote> in an Owner item", item("<blockquote>", "</blockquote>")))
M.append(("HT2", "CATCH?", "a Markdown blockquote '> ' as the Owner sub-item's content", item("> ", "")))
M.append(("HT3", "CATCH", "control: <q>…</q>", item("<q>", "</q>")))
# --- E: empty quotations ---
for ch, nm in [(" ", "no-break space"), ("\t", "tab"), (" ", "em space"), ("　", "ideographic space"), (" ", "space (control)")]:
    M.append(("EQ-" + nm.split()[0][:6], "CATCH", "an empty quotation “%s” (%s) beside a real one" % (ch.encode("unicode_escape").decode(), nm),
              (lambda ch: lambda t: once(t, PLAT04_1, PLAT04_1.replace("  - A standing rule", "  - “" + ch + "” A standing rule")))(ch)))
M.append(("EQ-ellip", "UNCLAIMED", "a quotation of an ellipsis only “…”", lambda t: once(t, PLAT04_1, PLAT04_1.replace("  - A standing rule", "  - “…” A standing rule").replace(OOM, OOM + ", " + DRB))))
M.append(("EQ-dash", "UNCLAIMED", "a quotation of a dash only “—”", lambda t: once(t, PLAT04_1, PLAT04_1.replace("  - A standing rule", "  - “—” A standing rule").replace(OOM, OOM + ", " + DRB))))
# --- C: code spans ---
M.append(("CS1", "CATCH", "a backslash-escaped backtick pair (not a code span in Markdown) hiding a “…” quotation", top("\\`“", "”\\`")))
M.append(("CS2", "UNCLAIMED*", "a real code span holding “…” the record's prose (register: 'every quotation in an Owner line')", top("`“", "”`")))
M.append(("CS3", "CATCH", "control: the same in plain “…”", top("“", "”")))
# --- B: Owner-section boundaries ---
M.append(("OB1", "CATCH", "blank line, then an indented '* ' Owner sub-item quoting the prose", after_owner("\n\n  * “" + PROSE + "” — " + OOM)))
M.append(("OB2", "CATCH", "blank line, then an indented '+ ' Owner sub-item", after_owner("\n\n  + “" + PROSE + "” — " + OOM)))
M.append(("OB3", "CATCH", "blank line, then an indented '1. ' Owner sub-item", after_owner("\n\n  1. “" + PROSE + "” — " + OOM)))
M.append(("OB4", "CATCH", "blank line, then an indented continuation paragraph of the Owner item", after_owner("\n\n    The owner also said “" + PROSE + "” — " + OOM)))
M.append(("OB5", "CATCH", "control: blank line, then an indented '- ' sub-item", after_owner("\n\n  - “" + PROSE + "” — " + OOM)))
M.append(("OB6", "CATCH", "a '* ' sub-item with no blank line (joined to the previous item)", after_owner("\n  * “" + PROSE + "” — " + OOM)))
M.append(("OB7", "CATCH?", "a second Owner field written __Owner:__ (renders exactly as **Owner:**)", after_owner("\n- __Owner:__ “" + PROSE + "” — " + OOM)))
M.append(("OB8", "CATCH?", "a second Owner field written **Owner**: (colon outside the bold)", after_owner("\n- **Owner**: “" + PROSE + "” — " + OOM)))
M.append(("OB9", "CATCH?", "PLAT-04's own Owner label rewritten __Owner:__, its first item now record prose in “…”", lambda t: item("“", "”")(t).replace(
    "- **Owner:**\n  - “" + PROSE, "- __Owner:__\n  - “" + PROSE)))
# --- S: section 3 ---
M.append(("S3a", "CATCH", "an extra section-3 row without leading/trailing pipes (GFM renders it as a row)",
          sec3_end("123 | \"" + PROSE + "\" | " + OOM + " | PLAT-04 | Current")))
M.append(("S3b", "CATCH", "an extra section-3 row indented by one space", sec3_end(" | 123 | \"" + PROSE + "\" | " + OOM + " | PLAT-04 | Current |")))
M.append(("S3c", "CATCH", "control: an extra five-cell row", sec3_end("| 123 | \"" + PROSE + "\" | " + OOM + " | PLAT-04 | Current |")))
M.append(("S3d", "UNCLAIMED", "row 43's Feeds cell changed EVID-06 -> SEC-01", lambda t: once(t, ROW43, ROW43.replace("EVID-06", "SEC-01"))))
M.append(("S3e", "UNCLAIMED", "row 43's Status changed Current -> Superseded", lambda t: once(t, ROW43, ROW43.replace("Current", "Superseded"))))
M.append(("S3f", "UNCLAIMED", "row 44 renumbered 43 (two rows numbered 43)", lambda t: once(t, ROW44_START, ROW44_START.replace("| 44 |", "| 43 |"))))
M.append(("S3g", "CATCH", "row 43's record cell gains a second record", lambda t: once(t, ROW43, ROW43.replace("arkb.md |", "arkb.md, " + OOM + " |"))))
# --- W: wording ---
M.append(("W-case", "UNCLAIMED", "a quoted passage's case changed (EVID-03 'Make sure' -> 'MAKE SURE', first of its two copies)",
          lambda t: t.replace("Dashboard. " + EVID03_A, "Dashboard. " + EVID03_A.replace("Make sure", "MAKE SURE"), 1)))

os.makedirs(OUT, exist_ok=True)
res = {"CATCH": [0, 0], "CATCH?": [0, 0], "LIMIT": [0, 0], "UNCLAIMED": [0, 0], "UNCLAIMED*": [0, 0]}
for key, expect, name, f in M:
    new = f(orig)
    assert new != orig, key
    p = os.path.join(OUT, key + ".md")
    open(p, "w").write(new)
    r = subprocess.run([sys.executable, "-B", CHK, p], capture_output=True, text=True)
    probs = [x for x in r.stdout.split("\n") if x.startswith(" - ")]
    res[expect][0 if r.returncode else 1] += 1
    print("%-6s %-14s expect %-10s %s  (exit %d, %d problem(s))" % ("CAUGHT" if r.returncode else "MISSED", key, expect, name, r.returncode, len(probs)))
    for x in probs:
        print("        ", x[:220])
    if r.stderr.strip():
        print("         stderr:", r.stderr.strip()[-300:])
print("\nby expectation (caught, missed):", res)
assert hashlib.sha256(open(REG).read().encode()).hexdigest() == sha0
print("register unchanged, sha256", sha0)
