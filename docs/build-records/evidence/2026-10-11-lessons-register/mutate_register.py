"""Mutations of lessons-register.md, each a defect the checker should catch,
run on copies: the register itself is read, never written (its sha256 is
compared at the end). From the round-3, round-4 and round-5 verifiers'
cases (M*, V*, A* to F*) and this record's own controls (C*).

Usage: mutate_register.py <check_register.py> <lessons-register.md> <scratch dir>"""
import hashlib
import os
import subprocess
import sys

CHK, REG, OUT = sys.argv[1:4]
orig = open(REG).read()
sha0 = hashlib.sha256(orig.encode()).hexdigest()


def once(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:80])
    return t.replace(old, new)


def line_sub(t, n, old, new):
    lines = t.split("\n")
    assert lines[n - 1].count(old) == 1, lines[n - 1][:80]
    lines[n - 1] = lines[n - 1].replace(old, new)
    return "\n".join(lines)


PLAT04_1 = "  - A standing rule in the record, which does not say who set it: if this OOMs again, stop raising ceilings and bound the growth instead — 2026-08-16-mempool-oom-recurrence.md"
PLAT04_95 = "  - “Fine with 95% limit for now.” (2026-09-27, on measuring the 95% as docker stats shows it) — 2026-09-26-mempool-api-memory.md"
PLAT04_RAM = "“The original memory limit for each service depends on the size of RAM for a node … if there is only 8 or 16 GB, that needs to be limited or controlled. Not sure what .env has.”"
EXEC01_1 = "  - “Fix all six now (Recommended)” — 2026-10-05-usb-backup-run-media.md"
EXEC01_2 = "  - “Let's also fix S11, 13, and 8.” Then,"
HEAL03 = "- **Owner:** the owner's decision as the record gives it (asked, not quoted): budget spent → skip that hypothesis and continue down the ladder (escalate only when all are spent), and a 24-hour rolling window — 2026-09-16-drb-attempt-budget-and-escalation.md"
ROW9 = "| 9 | Budget spent: skip that hypothesis and continue down the ladder (escalate only when all are spent), with a 24-hour rolling window. *(the record's wording: \"budget spent → skip that hypothesis … and a 24-hour rolling window\")*"
ROW9_HARVEST = "Budget spent: skip that hypothesis and continue down the ladder (escalate only when all are spent), with a 24-hour rolling window."
ROW7_NOTE = "existing coverage. *(the record's summary)* |"
ROW119 = "| 119 | \"OK\" — the 55 s limit accepted, 2026-10-10 *(corrected:"
VERIF_REC = "2026-10-06-request-values-never-reach-a-shell.md"
EVID03 = 1 + orig.split("\n").index(next(x for x in orig.split("\n") if "Make sure every one of them is actually meansuring" in x))
M = {
    "C1 FUND-03's record prose put back in quotation marks": lambda t: once(t,
        "- **Owner:** the owner's decision as the record gives it (asked, not quoted): delete the remaining plaintext archives now; no secret rotation (the USB drive never left the owner's possession) —",
        "- **Owner:** “Owner decision (asked): delete the remaining plaintext archives now; no secret rotation (the USB drive never left the owner's possession).” —"),
    "C2 an option label changed (EVID-06)": lambda t: once(t, "(2026-09-29): “MAs + returns backup:”", "(2026-09-29): “MAs + returns fallback:”"),
    "C3 row 119's 'corrected' note no longer gives the harvest's text": lambda t: once(t,
        '(corrected: the harvest read "OK (55 s accepted, 2026-10-10)"', '(corrected: the harvest read "OK, 55 s accepted"'),
    "M1 a summary put in quotation marks (HEAL-04)": lambda t: once(t,
        "- **Owner:** The owner chose to fix the violations rather than baseline them; deleting DRB-NETWORK-OFFLINE-01 was owner-approved (the record's account, not a quotation)",
        "- **Owner:** “The owner chose to fix the violations rather than baseline them, and approved deleting DRB-NETWORK-OFFLINE-01.”"),
    "M1b the record's bold prose put in quotation marks (TEST-04)": lambda t: once(t,
        "- **Owner:** Owner decision (2026-09-14, same session): delete the file (fsmEngine.test.ts) — the record's account;",
        "- **Owner:** “Owner decision (2026-09-14, same session): delete the file.” (fsmEngine.test.ts) —"),
    "M2 one quoted word changed (EVID-03)": lambda t: line_sub(t, EVID03, "meansuring", "measuring"),
    "M2b a short quotation changed (SEC-01)": lambda t: once(t, "“4. yes” (2026-09-26), to having LND", "“4. no” (2026-09-26), to having LND"),
    "M2c emphasis added inside a quotation (EVID-03)": lambda t: line_sub(t, EVID03, "Make sure every one of them", "Make sure **every one** of them"),
    "M3 the cited record dropped (EVID-09)": lambda t: once(t, "“Fix it now (Recommended)” — 2026-10-06-health-check-parallel-stats.md", "“Fix it now (Recommended)”"),
    "M3b one of two cited records dropped (LN-06)": lambda t: once(t,
        "— 2026-10-06-health-check-parallel-stats.md, 2026-10-07-money-routes-not-cut-by-watchdog.md",
        "— 2026-10-07-money-routes-not-cut-by-watchdog.md"),
    "M4 a quotation wrapped over two lines, a word changed after the wrap (EVID-03)": lambda t: line_sub(t, EVID03,
        "Make sure every one of them is actually meansuring", "Make sure every one of them\n  is actually measuring"),
    "V1 the record's bold finding quoted as the owner's (PLAT-04)": lambda t: once(t,
        "  - A standing rule in the record, which does not say who set it: if this OOMs again, stop raising ceilings and bound the growth instead —",
        "  - “startup memory footprint scales with live mempool size and accumulated disk cache” —"),
    "V2 the session's prose, in a record whose quotation marks pair across paragraphs, quoted as the owner's (EXEC-01)": lambda t: once(t,
        "  - “Fix all six now (Recommended)” — 2026-10-05-usb-backup-run-media.md",
        "  - “Fix all six now (Recommended)”, then “found while fixing the six; same class, same file, included” — 2026-10-05-usb-backup-run-media.md"),
    "V3 the session's words, which its record also quotes, given as the owner's (PLAT-04)": lambda t: once(t,
        "restart mempool-api itself, never the heaviest container; no CPU alert)",
        "restart mempool-api itself, never “the heaviest container”; no CPU alert)"),
    "V4 section 3 row 9 changed away from the harvest": lambda t: once(t,
        "| 9 | Budget spent: skip that hypothesis and continue down the ladder",
        "| 9 | Budget spent: escalate at once instead of continuing down the ladder"),
    # the round-5 verifier's cases (rn-verify15/mut15.py), kept as they were written
    "A1 HEAL-03: the record's bold mid-item prose quoted as the owner's": lambda t: once(t, HEAL03,
        "- **Owner:** “budget spent → skip that hypothesis and continue down the ladder” — 2026-09-16-drb-attempt-budget-and-escalation.md"),
    "A2 PLAT-04: the record's bold list-item label quoted as the owner's": lambda t: once(t, PLAT04_1,
        "  - “Third-strike rule (standing decision):” if this OOMs again, stop raising ceilings — 2026-08-16-mempool-oom-recurrence.md"),
    "A3 PLAT-04: the session's first-person bold label quoted as the owner's": lambda t: once(t, PLAT04_95,
        PLAT04_95 + "\n  - “My mistake: I deployed the backend with a red suite.” — 2026-09-26-mempool-api-memory.md"),
    "A4 PLAT-04: the session's bold label quoted as the owner's": lambda t: once(t, PLAT04_95,
        PLAT04_95 + "\n  - “What investigation found, BEFORE building” — 2026-09-26-mempool-api-memory.md"),
    "A5 EXEC-01: a verifier's prose from a list item with an empty \"\" quoted as the owner's": lambda t: once(t, EXEC01_1,
        EXEC01_1 + "\n  - “the doc watcher indexes the working tree” — " + VERIF_REC),
    "A6 EXEC-01: more of that verifier's prose quoted as the owner's": lambda t: once(t, EXEC01_1,
        EXEC01_1 + "\n  - “Reverting round 3's source makes its tests red” — " + VERIF_REC),
    "A7 EXEC-01: the session's prose from a part with no quotation marks": lambda t: once(t, EXEC01_1,
        EXEC01_1 + "\n  - “a test wrote the owner's state” then “writes dashboard/data/chat-executions.jsonl from a __dirname path” — " + VERIF_REC),
    "B1 PLAT-04: V1's record prose as the owner's, in straight quotes": lambda t: once(t, PLAT04_1,
        "  - \"startup memory footprint scales with live mempool size and accumulated disk cache\" — 2026-08-16-mempool-oom-recurrence.md"),
    "B2 PLAT-04: V1's record prose as the owner's, in single curly quotes": lambda t: once(t, PLAT04_1,
        "  - ‘startup memory footprint scales with live mempool size and accumulated disk cache’ — 2026-08-16-mempool-oom-recurrence.md"),
    "B3 PLAT-04: V1's record prose as the owner's, an opening mark only": lambda t: once(t, PLAT04_1,
        "  - “startup memory footprint scales with live mempool size and accumulated disk cache — 2026-08-16-mempool-oom-recurrence.md"),
    "B4 PLAT-04: V1's record prose as the owner's, opened with a closing mark": lambda t: once(t, PLAT04_1,
        "  - ”startup memory footprint scales with live mempool size and accumulated disk cache” — 2026-08-16-mempool-oom-recurrence.md"),
    "C4 EXEC-01: a nested bold label (a finding) quoted as the owner's": lambda t: once(t, EXEC01_1,
        EXEC01_1 + "\n  - “Found while answering N-1 — a test wrote the owner's state:” — " + VERIF_REC),
    "D1 PLAT-04: a quotation wrapped over two lines, a word changed after the wrap": lambda t: once(t, PLAT04_RAM,
        PLAT04_RAM.replace("limited or controlled.", "limited or\n    capped.")),
    "D2 PLAT-04: a word changed in a quotation the record itself wraps": lambda t: once(t,
        "chose “Heap follows limit”", "chose “Heap tracks limit”"),
    "D3 EXEC-01: a quotation wrapped so the next line starts with '- ', a word changed after the wrap": lambda t: once(t,
        EXEC01_2, "  - “Let's also fix S11, 13,\n  - and 9.” Then,"),
    "E1 row 9 changed, its note relabelled 'corrected' quoting the harvest": lambda t: once(t, ROW9,
        "| 9 | Budget spent: escalate at once instead of continuing down the ladder. *(corrected: the harvest read \"" + ROW9_HARVEST + "\")*"),
    "E2 row 119's corrected text changed": lambda t: once(t, ROW119, ROW119.replace('"OK"', '"Fine"')),
    "E3 row 7's note relabelled 'the owner's words'": lambda t: once(t, ROW7_NOTE, "existing coverage. *(the owner's words)* |"),
    "E4 row 9 changed, its note 'Corrected' (capital C) quoting the harvest": lambda t: once(t, ROW9,
        "| 9 | Budget spent: escalate at once instead of continuing down the ladder. *(Corrected: the harvest read \"" + ROW9_HARVEST + "\")*"),
    "F1 EXEC-01: “OK” cited from a record where 'ok' occurs only inside words": lambda t: once(t, EXEC01_1,
        "  - “Fix all six now (Recommended)”, then “OK” — 2026-10-05-usb-backup-run-media.md"),
    "F2 PLAT-04: underscore emphasis added inside a quotation": lambda t: once(t,
        "“Fine with 95% limit for now.”", "“Fine with _95% limit_ for now.”"),
}
os.makedirs(OUT, exist_ok=True)
for name, f in M.items():
    p = os.path.join(OUT, name.split(" ")[0] + ".md")
    open(p, "w").write(f(orig))
    r = subprocess.run([sys.executable, "-B", CHK, p], capture_output=True, text=True)
    probs = [x for x in r.stdout.split("\n") if x.startswith(" - ")]
    print("%-4s %s  (exit %d, %d problem(s))" % ("CAUGHT" if r.returncode else "MISSED", name, r.returncode, len(probs)))
    for x in probs:
        print("      ", x[:200])
assert hashlib.sha256(open(REG).read().encode()).hexdigest() == sha0
print("register unchanged, sha256", sha0)
