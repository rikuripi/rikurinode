"""Written by the round-11 verifier (its tools/mut27.py), kept as written.
Verifier round 11 (rn-verify27): mutations on copies only, aimed at the items the
register's opening says the script re-checks and that no kept mutation exercises
(the mapping, the Coverage table, the cited records, section 4's paths, a Port
line's main path), plus probes of what the wording might be read to cover.
Expect: CATCH (a listed item), UNCLAIMED (not claimed either way).
Usage: mut27.py <check_register.py> <register.md> <out dir>"""
import hashlib, json, os, shutil, subprocess, sys
CHK, REG, OUT = sys.argv[1:4]
orig = open(REG, newline="").read()
sha0 = hashlib.sha256(orig.encode()).hexdigest()
EVD = os.path.dirname(os.path.abspath(CHK))

def once(t, old, new):
    assert t.count(old) == 1, (t.count(old), old[:90]); return t.replace(old, new)
def line_sub(t, n, old, new):
    L = t.split("\n"); assert L[n - 1].count(old) == 1, (n, old, L[n - 1][:90]); L[n - 1] = L[n - 1].replace(old, new); return "\n".join(L)
def swap_headings(t):
    a = "#### UPG-01 — Upgrades prove the new version runs before saying so"
    b = "#### UPG-02 — One apply path; touch only the target"
    t = once(t, a, "@@A@@"); t = once(t, b, a); return t.replace("@@A@@", b)

M = [
 # --- the mapping
 ("MP1", "CATCH", "requirement-lessons.json: lesson 0 also listed under a second requirement (JSON copy)", "json-dup", None),
 ("MP2", "CATCH", "two requirement headings swapped (UPG-01 <-> UPG-02 titles; order differs from the mapping)", None, swap_headings),
 ("MP3", "CATCH", "a requirement id renamed: #### SEC-06 -> #### SEC-07", None,
     lambda t: once(t, "#### SEC-06 — The dependency audit", "#### SEC-07 — The dependency audit")),
 # --- per-theme counts
 ("PT1", "CATCH", "Contents SEC row: 6 (SEC-01 to SEC-06) -> 7 (SEC-01 to SEC-07)", None,
     lambda t: once(t, "| 6 (SEC-01 to SEC-06) | 16 |", "| 7 (SEC-01 to SEC-07) | 16 |")),
 # --- the Coverage table
 ("CV1", "CATCH", "Coverage row 2: 3 lessons -> 4", None,
     lambda t: once(t, "| 2 | 2026-08-08-sudo-rs-sudoers-wrappers.md | 3 |", "| 2 | 2026-08-08-sudo-rs-sudoers-wrappers.md | 4 |")),
 ("CV2", "CATCH", "Coverage row 2: one requirement dropped from 'Requirements fed'", None,
     lambda t: once(t, "| 3 | EXEC-08, TEST-07, PLAT-01 |", "| 3 | EXEC-08, PLAT-01 |")),
 ("CV3", "CATCH", "Coverage row 2: TEST-07 -> TEST-08", None,
     lambda t: once(t, "| 3 | EXEC-08, TEST-07, PLAT-01 |", "| 3 | EXEC-08, TEST-08, PLAT-01 |")),
 ("CV4", "CATCH", "Coverage: the last row (114) deleted", None,
     lambda t: once(t, "\n| 114 | 2026-10-10-upgrades-survive-code-updates.md | 4 | UPG-08, SEC-03 |", "")),
 # --- the cited records
 ("CR1", "CATCH", "EVID-01 Why: a cited record renamed to one that does not exist", None,
     lambda t: line_sub(t, 43, "2026-09-26-health-exact-container-names.md", "2026-09-26-health-exact-container-name.md")),
 ("CR2", "CATCH", "EVID-01 Why: a cited record replaced by an existing record that did not feed EVID-01", None,
     lambda t: line_sub(t, 43, "2026-09-26-health-exact-container-names.md", "2026-08-08-one-click-infra-upgrades.md")),
 ("CR3", "CATCH", "EVID-02 Why: (+1 more) -> (+2 more)", None,
     lambda t: line_sub(t, 52, "(+1 more)", "(+2 more)")),
 ("CR4", "CATCH", "Gap G2: its record renamed to one that does not exist", None,
     lambda t: once(t, "the newest encrypted config archive (2026-09-16-backup-truth-and-alerts.md)", "the newest encrypted config archive (2026-09-16-backup-truth-and-alert.md)")),
 ("CR5", "CATCH", "Coverage row 2: its record renamed to one that does not exist", None,
     lambda t: once(t, "| 2 | 2026-08-08-sudo-rs-sudoers-wrappers.md | 3 |", "| 2 | 2026-08-08-sudo-rs-sudoers-wrapper.md | 3 |")),
 ("CR6", "CATCH", "EVID-03 Owner line: its record renamed to one that does not exist", None,
     lambda t: line_sub(t, 61, "— 2026-09-30-dashboard-page-truth.md", "— 2026-09-30-dashboard-page-truths.md")),
 # --- section 3 against the harvest (beyond the kept sets' rows 7, 9, 119)
 ("S3a", "CATCH", "section 3 row 2: its Records cell names another existing record", None,
     lambda t: once(t, "| 2 | \"nothing should fail silently or be in a crash loop\" | 2026-08-10-crashloop-detection.md | HEAL-10 |",
                       "| 2 | \"nothing should fail silently or be in a crash loop\" | 2026-08-08-one-click-infra-upgrades.md | HEAL-10 |")),
 ("S3b", "CATCH", "section 3 row 2: its Feeds cell HEAL-10 -> HEAL-09", None,
     lambda t: once(t, "| 2026-08-10-crashloop-detection.md | HEAL-10 | Current |", "| 2026-08-10-crashloop-detection.md | HEAL-09 | Current |")),
 ("S3c", "CATCH", "section 3 row 2: one word of the harvest's text changed", None,
     lambda t: once(t, "| 2 | \"nothing should fail silently or be in a crash loop\" |", "| 2 | \"nothing should fail quietly or be in a crash loop\" |")),
 # --- section 4's paths
 ("S4a", "CATCH", "section 4 row 90: its path renamed to one that does not exist", None,
     lambda t: once(t, "| 90 | `scripts/rikuri-bluetooth-revive.sh` and", "| 90 | `scripts/rikuri-bluetooth-revival.sh` and")),
 ("S4b", "CATCH", "section 4 row 90: its test path renamed to one that does not exist", None,
     lambda t: once(t, "`systemd/rikuri-bluetooth-revive.service` | dashboard/backend/src/tests/bluetoothRevive.test.ts |",
                       "`systemd/rikuri-bluetooth-revive.service` | dashboard/backend/src/tests/bluetoothRevival.test.ts |")),
 ("S4c", "UNCLAIMED", "section 4's 'Explicitly' paragraph: its path renamed to one that does not exist", None,
     lambda t: once(t, "**Explicitly: `scripts/rikuri-bluetooth-revive.sh` must NOT", "**Explicitly: `scripts/rikuri-bluetooth-revival.sh` must NOT")),
 ("S4d", "UNCLAIMED", "section 4 Totals line: 42 port with tests -> 43", None,
     lambda t: once(t, "Totals: 90 entries — 42 port with tests", "Totals: 90 entries — 43 port with tests")),
 # --- a Port line's main path
 ("PL1", "CATCH", "EVID-04 Port line: its main path renamed to one that does not exist", None,
     lambda t: once(t, "- **Port:** `dashboard/backend/src/utils/upgradeStateCheck.ts` (tests:", "- **Port:** `dashboard/backend/src/utils/upgradeStateChecks.ts` (tests:")),
 ("PL2", "CATCH", "EVID-01 Port sub-item: its main path renamed to one that does not exist", None,
     lambda t: line_sub(t, 46, "`dashboard/backend/src/tests/mempoolStalenessAndFees.test.ts` — Port", "`dashboard/backend/src/tests/mempoolStalenessAndFee.test.ts` — Port")),
 ("PL3", "UNCLAIMED", "EVID-04 Port line: its main path replaced by another path that exists", None,
     lambda t: once(t, "- **Port:** `dashboard/backend/src/utils/upgradeStateCheck.ts` (tests:", "- **Port:** `dashboard/frontend/src/utils/topCards.ts` (tests:")),
 # --- probes
 ("U1", "UNCLAIMED", "EVID-01 Why: two fed records swapped (each incident now attributed to the other's record)", None,
     lambda t: line_sub(line_sub(t, 43, "2026-09-30-dashboard-page-truth.md", "@@X@@"), 43, "2026-09-26-health-exact-container-names.md", "2026-09-30-dashboard-page-truth.md").replace("@@X@@", "2026-09-26-health-exact-container-names.md")),
 ("U2", "UNCLAIMED", "Coverage intro: All 114 records -> All 115 records", None,
     lambda t: once(t, "All 114 records, in date order", "All 115 records, in date order")),
 ("U3", "UNCLAIMED", "section 3 intro: (122) -> (123)", None,
     lambda t: once(t, "Every distinct owner decision in the harvest (122)", "Every distinct owner decision in the harvest (123)")),
 ("U4", "UNCLAIMED", "Coverage: a second row 2 with wrong figures, written with two spaces after its first pipe", None,
     lambda t: once(t, "| 2 | 2026-08-08-sudo-rs-sudoers-wrappers.md | 3 | EXEC-08, TEST-07, PLAT-01 |",
                       "| 2 | 2026-08-08-sudo-rs-sudoers-wrappers.md | 3 | EXEC-08, TEST-07, PLAT-01 |\n|  2 | 2026-08-08-sudo-rs-sudoers-wrappers.md | 9 | SEC-01 |")),
]

os.makedirs(OUT, exist_ok=True)
for key, expect, name, special, f in M:
    chk = CHK
    if special == "json-dup":
        d = os.path.join(OUT, "ev-json"); os.makedirs(d, exist_ok=True)
        for fn in ("check_register.py", "lessons-harvest.json", "owner-decision-notes.json", "requirement-lessons.json"):
            shutil.copy(os.path.join(EVD, fn), d)
        j = json.load(open(os.path.join(d, "requirement-lessons.json")))
        ks = list(j["requirements"]); a = ks[0]; b = ks[1]
        first = j["requirements"][a][0]; j["requirements"][b] = j["requirements"][b] + [first]
        json.dump(j, open(os.path.join(d, "requirement-lessons.json"), "w"), indent=1)
        chk = os.path.join(d, "check_register.py"); p = REG
    else:
        new = f(orig); assert new != orig, key
        p = os.path.join(OUT, key + ".md"); open(p, "w", newline="").write(new)
    r = subprocess.run([sys.executable, "-B", chk, p], capture_output=True, text=True)
    probs = [x for x in r.stdout.split("\n") if x.startswith(" - ")]
    print("%-6s %-4s expect %-9s %s  (exit %d, %d problem(s))" % ("CAUGHT" if r.returncode else "MISSED", key, expect, name, r.returncode, len(probs)))
    for x in probs:
        print("            ", x[:220])
    if r.stderr.strip():
        print("         stderr:", r.stderr.strip().split("\n")[-1][:220])
assert hashlib.sha256(open(REG, newline="").read().encode()).hexdigest() == sha0
print("register unchanged, sha256", sha0)
