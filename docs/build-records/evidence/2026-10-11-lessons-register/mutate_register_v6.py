"""Written by the round-6 verifier (its tools/mut16.py), kept as written but for ROW43,
which round 7's note on row 43 changed. Verifier round 6: my own mutations of lessons-register.md, on copies only.
Expected outcome per case: CATCH (a claimed class) or LIMIT (a class the record states it misses)
or UNCLAIMED (no claim either way). Usage: mut16.py <check_register.py> <register.md> <out dir>"""
import hashlib, os, subprocess, sys
CHK, REG, OUT = sys.argv[1:4]
orig = open(REG).read()
sha0 = hashlib.sha256(orig.encode()).hexdigest()

def once(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:80])
    return t.replace(old, new)

OOM = "2026-08-16-mempool-oom-recurrence.md"
PROSE = "startup memory footprint scales with live mempool size and accumulated disk cache"   # the record's bold finding, quoted nowhere in it
PLAT04_1 = "  - A standing rule in the record, which does not say who set it: if this OOMs again, stop raising ceilings and bound the growth instead — " + OOM
PLAT04_95 = "  - “Fine with 95% limit for now.” (2026-09-27, on measuring the 95% as docker stats shows it) — 2026-09-26-mempool-api-memory.md"
PLAT04_LAST = "Shotdown or reduce RAM usage if necessary.” — 2026-10-03-upgrade-gates-round-2.md\n- **Port:**"
EVID06 = "  - AskUserQuestion choices (2026-09-29): “MAs + returns backup:” Kraken daily candles, plus the node's own daily-close archive; “funding: a second venue” (Deribit, labelled) — 2026-09-29-market-intel-freshness-arkb.md"
ARKB = "2026-09-29-market-intel-freshness-arkb.md"
EVID03_A = "Make sure every one of them is actually meansuring"
EVID03_N = 1 + orig.split("\n").index(next(x for x in orig.split("\n") if EVID03_A in x))
def line_sub(t, n, old, new):
    lines = t.split("\n")
    assert lines[n - 1].count(old) == 1
    lines[n - 1] = lines[n - 1].replace(old, new)
    return "\n".join(lines)
HEAL03 = "- **Owner:** the owner's decision as the record gives it (asked, not quoted): budget spent → skip that hypothesis and continue down the ladder (escalate only when all are spent), and a 24-hour rolling window — 2026-09-16-drb-attempt-budget-and-escalation.md"
MEM = "2026-09-26-mempool-api-memory.md"
ROW2 = '| 2 | "nothing should fail silently or be in a crash loop" |'
ROW4 = "| 4 | Owner spec (paraphrased in the record): a live progress view until a VERIFIED end state. *(the record's summary)* |"
ROW43 = "| 43 | AskUserQuestion choices (2026-09-29): \"MAs + returns backup: Kraken daily candles, plus the node's own daily-close archive\"; \"funding: a second venue (Deribit, labelled)\". *(the record bolds only the option labels, “MAs + returns backup:” and “funding: a second venue”; the rest of each is its own description)* | 2026-09-29-market-intel-freshness-arkb.md |"
ROW119 = "| 119 | \"OK\" — the 55 s limit accepted, 2026-10-10 *(corrected: the harvest read \"OK (55 s accepted, 2026-10-10)\", as if all of it were the owner's words)* |"
ROW9_NOTE = "*(the record's wording: \"budget spent → skip that hypothesis … and a 24-hour rolling window\")*"
SEC4 = "\n## 4. Port candidates"
PLAT04_WHY = "the container hit its limit 21,921 times (2026-09-26-mempool-api-memory.md)"

def item(open_, close_):
    return lambda t: once(t, PLAT04_1, "  - " + open_ + PROSE + close_ + " — " + OOM)

M = [
 # P: prose quoted as the owner's — bold of any kind
 ("PB1", "CATCH", "arkb record's bold heading label quoted as the owner's", lambda t: once(t, EVID06,
     EVID06 + "\n  - “Owner's choices (AskUserQuestion, 2026-09-29, costs stated):” — " + ARKB)),
 ("PB2", "CATCH", "arkb record's bold 'Fallbacks:' (a group label, not an option) quoted", lambda t: once(t, EVID06,
     EVID06 + "\n  - “Fallbacks:” — " + ARKB)),
 ("PB3", "CATCH", "arkb bold option text with its question header 'ETF column: ARKB (Recommended).'", lambda t: once(t, EVID06,
     EVID06 + "\n  - “ETF column: ARKB (Recommended).” — " + ARKB)),
 ("PB4", "CATCH", "option label joined with the record's description (row 43's form) in the Owner line", lambda t: once(t, EVID06,
     EVID06 + "\n  - “MAs + returns backup: Kraken daily candles, plus the node's own daily-close archive” — " + ARKB)),
 ("PB5", "CATCH", "a record heading ('Owner's decision', electrs) quoted as the owner's", lambda t: once(t, PLAT04_95,
     PLAT04_95 + "\n  - “Owner's decision (2026-10-03 ~22:15)” — 2026-10-03-electrs-0.12-support.md")),
 ("PB6", "CATCH", "a table cell's bold ('Farside's all-ETF Total') quoted", lambda t: once(t, EVID06,
     EVID06 + "\n  - “Farside's all-ETF Total” — " + ARKB)),
 # unquoted prose
 ("PU1", "CATCH", "record prose from a part with no quotation marks, in “…” (control)", item("“", "”")),
 ("PU2", "LIMIT", "record prose given as the owner's with no quotation marks at all", lambda t: once(t, PLAT04_1,
     "  - the owner said that " + PROSE + " — " + OOM)),
 # other quotation-mark styles
 ("PS1", "UNCLAIMED*", "straight single quotes '…' (register: 'in any quotation marks')", item("'", "'")),
 ("PS2", "UNCLAIMED*", "guillemets «…»", item("«", "»")),
 ("PS3", "UNCLAIMED*", "German low-high „…“", item("„", "“")),
 ("PS4", "UNCLAIMED*", "single low-high ‚…‘", item("‚", "‘")),
 ("PS5", "UNCLAIMED*", "HTML entities &ldquo;…&rdquo; (render as “…”)", item("&ldquo;", "&rdquo;")),
 ("PS6", "UNCLAIMED*", "HTML entities &quot;…&quot; (render as \"…\")", item("&quot;", "&quot;")),
 ("PS7", "UNCLAIMED*", "<q>…</q> (renders with quotation marks)", item("<q>", "</q>")),
 ("PS8", "UNCLAIMED*", "double primes ″…″", item("″", "″")),
 ("PS9", "CATCH", "“…” around a code span holding the record's prose", item("“`", "`”")),
 # unbalanced or reversed marks (claimed for “…”, "…", ‘…’)
 ("QB1", "CATCH", "‘…’ with the closing mark missing", item("‘", "")),
 ("QB2", "CATCH", "‘…’ reversed: ’…‘", item("’", "‘")),
 ("QB3", "CATCH", "a reversed ”…“ pair after a well-formed “…” pair", lambda t: once(t, PLAT04_1,
     "  - “if this OOMs again” then ”" + PROSE + "“ — " + OOM)),
 ("QB4", "CATCH", "a stray closing ” after a well-formed pair", lambda t: once(t, PLAT04_1,
     "  - “" + PROSE + "” — " + OOM + " ”")),
 ("QB5", "CATCH", "one straight \" opening the prose, none closing", item('"', "")),
 # pairing tricks on the Owner line
 ("QP1", "CATCH", "an empty \"\" before a straight-quoted span shifts the pairing", lambda t: once(t, PLAT04_1,
     "  - the setting left at \"\" and \"" + PROSE + "\" — " + OOM)),
 ("QP2", "CATCH", "inch marks around a straight-quoted span (even count)", lambda t: once(t, PLAT04_1,
     "  - a 2.5\" drive and \"" + PROSE + "\" and a 3.5\" drive — " + OOM)),
 ("QP3", "CATCH", "the prose nested in straight quotes inside a real owner quotation", lambda t: once(t, PLAT04_95,
     "  - “Fine with 95% limit for now. \"" + PROSE + "\"” (2026-09-27, on measuring the 95% as docker stats shows it) — 2026-09-26-mempool-api-memory.md, " + OOM)),
 ("QP4", "CATCH", "‘…’ opened right after a letter (contrived)", item("x‘", "’")),
 ("QP5", "CATCH", "a code span holding ” that would close an earlier “", lambda t: once(t, PLAT04_1,
     "  - “if this OOMs again `”` " + PROSE + "” — " + OOM)),
 ("QP6", "CATCH", "a quoted space \" \" then the straight-quoted prose", lambda t: once(t, PLAT04_1,
     "  - \" \" then \"" + PROSE + "\" — " + OOM)),
 # wrapped quotations
 ("W1", "CATCH", "wrap whose next line starts '1. ', word changed after it (EVID-03)", lambda t: line_sub(t, EVID03_N, EVID03_A,
     "Make sure every one of them\n  1. is actually measuring")),
 ("W2", "CATCH", "a blank line inside a quotation, word changed after it (EVID-03)", lambda t: line_sub(t, EVID03_N, EVID03_A,
     "Make sure every one of them\n\n  is actually measuring")),
 ("W3", "LIMIT?", "a loose-list Owner sub-item after a blank line, record prose quoted", lambda t: once(t, PLAT04_LAST,
     PLAT04_LAST.replace("\n- **Port:**", "\n\n  - “" + PROSE + "” — " + OOM + "\n- **Port:**"))),
 ("W4", "CATCH", "wrap whose next line starts '- **' at column 0 (ends the Owner section)", lambda t: line_sub(t, EVID03_N, EVID03_A,
     "Make sure every one of them\n- **is** actually measuring")),
 ("W5", "CATCH", "wrap indented with a tab, word changed after it", lambda t: line_sub(t, EVID03_N, EVID03_A,
     "Make sure every one of them\n\tis actually measuring")),
 # section 3
 ("S1", "CATCH", "a note added to row 2", lambda t: once(t, ROW2, ROW2[:-2] + " *(the owner's words)* |")),
 ("S2", "CATCH", "row 4's note removed", lambda t: once(t, ROW4, ROW4.replace(" *(the record's summary)*", ""))),
 ("S3", "CATCH", "row 4's text changed, note kept", lambda t: once(t, ROW4, ROW4.replace("VERIFIED", "confirmed"))),
 ("S4", "CATCH", "row 4's note re-marked _(…)_", lambda t: once(t, ROW4, ROW4.replace("*(the record's summary)*", "_(the record's summary)_"))),
 ("S5", "CATCH", "row 119's note tail changed, harvest still quoted", lambda t: once(t, ROW119,
     ROW119.replace("as if all of it were the owner's words", "all of it the owner's words"))),
 ("S6", "CATCH", "row 119's text put back to the harvest's", lambda t: once(t, ROW119,
     ROW119.replace('"OK" — the 55 s limit accepted, 2026-10-10', '"OK (55 s accepted, 2026-10-10)"'))),
 ("S7", "CATCH", "row 9's note: '…' changed to '...'", lambda t: once(t, ROW9_NOTE, ROW9_NOTE.replace("…", "..."))),
 ("S8", "UNCLAIMED", "row 43's record cell changed to another record", lambda t: once(t, ROW43,
     ROW43.replace("| 2026-09-29-market-intel-freshness-arkb.md |", "| 2026-09-29-market-cap-volume-etf-warm.md |"))),
 ("S9", "UNCLAIMED", "an extra section-3 row of four cells quoting record prose as an owner decision", lambda t: once(t, SEC4,
     "\n| 123 | \"" + PROSE + "\" | " + OOM + " | PLAT-04 |" + SEC4) if False else t.replace(
     "| 2026-10-10", "| 2026-10-10", 0)),
 # stated limits
 ("L1", "LIMIT", "V3 class: the session's option text, which the record quotes, given as the owner's (slim-path)", lambda t: once(t, PLAT04_95,
     PLAT04_95 + "\n  - “Fix the four biases” — 2026-10-02-slim-path-searches-docs-when-no-card.md")),
 ("L2", "LIMIT", "M3b class: an unrelated record added to an Owner line's citations", lambda t: once(t, PLAT04_95,
     PLAT04_95.replace("— 2026-09-26-mempool-api-memory.md", "— 2026-09-26-mempool-api-memory.md, 2026-08-08-sudo-rs-sudoers-wrappers.md"))),
 ("L3", "LIMIT", "record prose quoted as the owner's in a Why line", lambda t: once(t, PLAT04_WHY,
     PLAT04_WHY + "; the owner said “" + PROSE + "” (" + OOM + ")")),
 # option labels
 ("O1", "CATCH", "an option label cited from a record that does not hold it", lambda t: once(t, PLAT04_95,
     PLAT04_95 + "\n  - “ARKB (Recommended)” — 2026-09-29-market-cap-volume-etf-warm.md")),
 # follow-ups: the trick isolated from incidental catches
 ("QB3b", "CATCH", "a reversed ”…“ pair after a well-formed pair that is the owner's own words", lambda t: once(t, PLAT04_1,
     "  - “Fine with 95% limit for now.” then ”" + PROSE + "“ — " + MEM + ", " + OOM)),
 ("QP1b", "CATCH", "an empty \"\" right before a straight-quoted span (the shifted span is a single space)", lambda t: once(t, PLAT04_1,
     "  - left as \"\" \"" + PROSE + "\" — " + OOM)),
 ("QP1c", "CATCH", "an empty \"\" then ' and ', the shifted span found in the owner's quoted words", lambda t: once(t, PLAT04_1,
     "  - left as \"\" and \"" + PROSE + "\" — " + MEM + ", " + OOM)),
 ("QP2b", "LIMIT?", "inch marks chosen so both shifted spans pass (8\" … or 16\")", lambda t: once(t, PLAT04_1,
     "  - an 8\" \"" + PROSE + "\" or 16\" — " + MEM + ", " + OOM)),
 ("PS9b", "CATCH", "a top-level Owner line: “…” around a code span holding the record's prose", lambda t: once(t, HEAL03,
     "- **Owner:** “`budget spent → skip that hypothesis and continue down the ladder`” — 2026-09-16-drb-attempt-budget-and-escalation.md")),
 ("PS1b", "UNCLAIMED*", "a top-level Owner line in straight single quotes", lambda t: once(t, HEAL03,
     "- **Owner:** 'budget spent → skip that hypothesis and continue down the ladder' — 2026-09-16-drb-attempt-budget-and-escalation.md")),
 ("QP1d", "CATCH", "an empty \"\" right before a straight-quoted span, citing a record with multi-word quotations", lambda t: once(t, PLAT04_1,
     "  - left as \"\" \"" + PROSE + "\" — " + MEM + ", " + OOM)),
 ("QB3c", "CATCH", "reversed ”…“ alone after a good pair, single record cited", lambda t: once(t, PLAT04_95,
     "  - “Fine with 95% limit for now.” ”the container hit its limit“ — " + MEM)),
]
os.makedirs(OUT, exist_ok=True)
for key, expect, name, f in M:
    p = os.path.join(OUT, key + ".md")
    new = f(orig)
    if key == "S9":      # built here so the row lands at the end of section 3's table
        sec3_end = new.index("\n\n## 4. Port candidates")
        new = new[:sec3_end] + "\n| 123 | \"" + PROSE + "\" | " + OOM + " | PLAT-04 |" + new[sec3_end:]
    assert new != orig, key
    open(p, "w").write(new)
    r = subprocess.run([sys.executable, "-B", CHK, p], capture_output=True, text=True)
    probs = [x for x in r.stdout.split("\n") if x.startswith(" - ")]
    print("%-6s %-4s expect %-10s %s  (exit %d, %d problem(s))" % ("CAUGHT" if r.returncode else "MISSED", key, expect, name, r.returncode, len(probs)))
    for x in probs:
        print("        ", x[:210])
    if r.stderr.strip():
        print("         stderr:", r.stderr.strip()[-300:])
assert hashlib.sha256(open(REG).read().encode()).hexdigest() == sha0
print("register unchanged, sha256", sha0)
