"""Written by the round-10 verifier (its tools/mut25.py), kept as written.
Verifier round 10: mutations of lessons-register.md on copies (register read only,
sha256 compared at the end). Accidental-change classes the round-10 text claims:
"the counts ... match the harvest", "every path named for porting exists", plus controls.
Usage: mut25.py <check_register.py> <register.md> <out dir>"""
import hashlib, os, subprocess, sys
CHK, REG, OUT = sys.argv[1:4]
orig = open(REG, newline="").read()
sha0 = hashlib.sha256(orig.encode()).hexdigest()
def once(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:80])
    return t.replace(old, new)
def first(t, old, new):
    assert old in t, old[:80]
    return t.replace(old, new, 1)
SEC_ROW = "| [SEC — Secrets and credentials](#sec) | 6 (SEC-01 to SEC-06) | 16 |\n"
M = [
 ("N0", "CTRL", "control: contents row SEC says 17 lessons", lambda t: once(t, SEC_ROW, SEC_ROW.replace("| 16 |", "| 17 |"))),
 ("N1", "COUNTS", "Source paragraph: 118 live incidents -> 119", lambda t: once(t, "**118 live incidents**", "**119 live incidents**")),
 ("N2", "COUNTS", "Source paragraph: (122 distinct) -> (123 distinct)", lambda t: once(t, "(122 distinct)", "(123 distinct)")),
 ("N3", "COUNTS", "Source paragraph: 114 build records -> 115", lambda t: once(t, "All 114 build records", "All 115 build records")),
 ("N4", "COUNTS", "Contents Total row: **475** -> **476**", lambda t: once(t, "| **Total** | **107** | **475** |", "| **Total** | **107** | **476** |")),
 ("N5", "COUNTS", "Contents: the SEC row deleted", lambda t: once(t, SEC_ROW, "")),
 ("N6", "COUNTS", "Contents: SEC row's link text changed so the row no longer matches the pattern, and its count wrong", lambda t: once(t, SEC_ROW, "| [SEC — Secrets and credentials](#sec) | 6 (SEC-01–SEC-06) | 17 |\n")),
 ("P0", "CTRL", "control: a Port sub-item's code path renamed", lambda t: once(t, "  - `dashboard/backend/src/services/btcSupply.ts` (tests:", "  - `dashboard/backend/src/services/btcSupplyX.ts` (tests:")),
 ("P1", "PORT", "a test path in a requirement's Port line (UPG Port line, line 71) renamed to one that does not exist",
     lambda t: first(t, "- **Port:** `dashboard/backend/src/utils/upgradeStateCheck.ts` (tests: dashboard/backend/src/tests/upgradeRebootBringup.test.ts; dashboard/backend/src/tests/upgradeDoneBanner.test.ts)",
                        "- **Port:** `dashboard/backend/src/utils/upgradeStateCheck.ts` (tests: dashboard/backend/src/tests/upgradeRebootBringup.test.ts; dashboard/backend/src/tests/upgradeDoneBanners.test.ts)")),
 ("P2", "PORT", "a test path in a requirement's Port sub-item renamed (btcSupply.test.ts -> btcSupplyX.test.ts)",
     lambda t: once(t, "  - `dashboard/backend/src/services/btcSupply.ts` (tests: dashboard/backend/src/tests/btcSupply.test.ts)", "  - `dashboard/backend/src/services/btcSupply.ts` (tests: dashboard/backend/src/tests/btcSupplyX.test.ts)")),
 ("P3", "PORT", "a second code path in a Port line, after the first (the 'and' list on line 54): serviceCard.ts -> serviceCards.ts",
     lambda t: once(t, "and `dashboard/frontend/src/utils/serviceCard.ts` (tests: dashboard/frontend/tests/pageRound4.test.tsx", "and `dashboard/frontend/src/utils/serviceCards.ts` (tests: dashboard/frontend/tests/pageRound4.test.tsx")),
]
os.makedirs(OUT, exist_ok=True)
for key, expect, name, f in M:
    new = f(orig); assert new != orig, key
    p = os.path.join(OUT, key + ".md"); open(p, "w", newline="").write(new)
    r = subprocess.run([sys.executable, "-B", CHK, p], capture_output=True, text=True)
    probs = [x for x in r.stdout.split("\n") if x.startswith(" - ")]
    print("%-6s %-3s expect %-6s %s  (exit %d, %d problem(s))" % ("CAUGHT" if r.returncode else "MISSED", key, expect, name, r.returncode, len(probs)))
    for x in probs[:4]: print("          ", x[:200])
    if r.stderr.strip(): print("         stderr:", r.stderr.strip()[-300:])
assert hashlib.sha256(open(REG, newline="").read().encode()).hexdigest() == sha0
print("register unchanged, sha256", sha0)
