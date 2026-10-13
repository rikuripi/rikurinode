"""Apply fact-checks B, C and E to the lessons register (exact replacements;
each must match at least once, and the count replaced is printed)."""
import re
import sys

F = sys.argv[1]
t = open(F).read()
done = []


def sub(old, new, expect=None):
    global t
    n = t.count(old)
    if n == 0 or (expect is not None and n != expect):
        sys.exit("no match (%d): %r" % (n, old[:90]))
    t = t.replace(old, new)
    done.append((n, old[:70]))


# --- C: FUND, LN, SEC -------------------------------------------------------------------
sub("Stall-rule tests (12 of 16 failed on the old code)",
    "Stall-rule tests (12 of 14 failed on the old code; the suite later grew to 16)")
sub("failing with HTTP 401 for 3+ minutes after the cookie rotated",
    "failing with HTTP 401 for 2.5+ minutes (3+ in the verifier's re-run) after the cookie rotated")
sub("twice a session printed LND's Tor control password while reading lnd.conf for ordinary settings "
    "(2026-09-30-node-power-buttons.md, 2026-10-02-tor-control-password-rotation.md)",
    "a session printed LND's Tor control password while reading lnd.conf for ordinary settings "
    "(2026-09-30-node-power-buttons.md), and the password was then rotated "
    "(2026-10-02-tor-control-password-rotation.md)")
sub("a cleanup runbook deleted directories while measuring the wrong disk",
    "a cleanup runbook targeted `rikuri-backup-*` directories that did not exist while measuring `df /`, "
    "the wrong disk")
sub("restarted whichever container was highest at ≥ 90 % of its limit, LND included",
    "would restart whichever container was highest at ≥ 90 % of its limit, so LND was eligible (it did not fire)")
sub("runbooks called invented LND routes and tuned watchtower fees on a node with no tower",
    "runbooks called invented LND routes, one of them to tune watchtower sweep fees on a node with no "
    "registered tower")
sub("tested /mnt/backup, a path that never existed,", "tested /mnt/backup, a path that was never one of the node's drives,")
sub("on every path (UI, self-heal, cascade, upgrade)", "on every path (UI, self-heal, cascade, compose)")
sub("The old node auto-unlocked LND from a password file on disk",
    "The old node unlocked LND automatically when a password file existed on disk")
sub("*The old node never held a funded channel; these are the only lessons about LND and money paths, and each "
    "must be re-proven on current LND.*",
    "*The old mainnet node had no channels whenever a record checked (its testnet LND held the test funds); these "
    "are the lessons about LND itself — FUND, SEC and EXEC hold more about money paths — and each must be "
    "re-proven on current LND.*")
sub("the live skip was never observed.", "the live skip was not yet observed when the record closed.")
sub("this path never once ran with a channel open.",
    "this backup has never succeeded; its first real run is the first channel open.")
sub("12 stray bytes made every reader return an empty list",
    "12 stray bytes made the drive-selection reader return an empty list (the others fell back to silent "
    "defaults)")

# --- B: HEAL, UPG ---------------------------------------------------------------------------
sub("“Budget spent: skip that hypothesis and continue down the ladder (escalate only when all are spent), with a "
    "24-hour rolling window.”",
    "“budget spent → skip that hypothesis and continue down the ladder (escalate only when all are spent), and a "
    "24-hour rolling window.”")
sub('"A hypothesis over budget is skipped, not executed", "the attempt is recorded before the runbook runs" and '
    '"exhausted pages the owner" tests',
    '"a hypothesis over budget is skipped, not executed", "records the attempt BEFORE running the runbook" and '
    '"exhausted pages the owner with the DRB rollback message" tests')
sub("14 of 89 runbooks targeted invented routes or sent LND REST calls to the local model server's port",
    "14 of 89 runbooks were broken (invented or wrong routes, LND REST calls sent to the local model server's "
    "port, unsupplied template variables, units that did not exist)")
sub("“The owner chose to fix the violations rather than baseline them; deleting DRB-NETWORK-OFFLINE-01 was "
    "owner-approved.”",
    "The owner chose to fix the violations rather than baseline them; deleting DRB-NETWORK-OFFLINE-01 was "
    "owner-approved (the record's account, not a quotation)")
sub("an LND incident could never close because its closing state lived in memory lost on restart",
    "an LND incident could never close because nothing reported \"syncing → synced\" as a recovery (its closing "
    "state was also held in memory lost on restart)")
sub("by the caller's timeout on two days, after it had already restarted Tor, and left no record",
    "by the caller's timeout on two days (on 2026-09-24 after it had already restarted Tor) and left no record")
sub("“\"Let's fix the tor onion.\" (2026-09-28)”", "“Let's fix the tor onion.” (2026-09-28)")
sub("restarted the wedged backend and destroyed the only evidence",
    "restarted the wedged backend and destroyed its wedged state before a stack could be captured")
sub("“Roll back. Then close the three gaps. / Yes, roll back + tell me”",
    "“Roll back. Then close the three gaps.”; then “Yes, roll back + tell me”")
sub("“Supported release lines / Hold it, show why”",
    "“Supported release lines” and “Hold it, show why” (answers to two questions)")
sub("3. Electrs 0.12” — 2026-10-03-", "3. Electrs 0.12 …” — 2026-10-03-")
sub("“C1: (a), the newer one runs (the node's pin is dropped once the default reaches or passes it); C2: 'No other "
    "node exists now. So it's OK.'; parked: 'Yes, you can park it'”",
    "C1: option (a), the newer one runs (the node's pin is dropped once the default reaches or passes it); C2: "
    "“No other node exists now. So it's OK.”; parked: “Yes, you can park it”")
sub("a release-mode test run overwrote production binaries",
    "a release-mode test run replaced the release binaries with test-feature builds that the deploy steps "
    "would then have installed (they were rebuilt before any install)")
sub("a migration would have re-applied to every later patch",
    "a migration would have been attempted on every later 0.12.x patch and refused, because its exact-text edits "
    "could not match the already-migrated compose file")
sub("“Owner spec (paraphrased in the record): a live progress view until a VERIFIED end state.”",
    "Owner spec (paraphrased in the record): a live progress view until a VERIFIED end state")
sub("730 of 741 decisions were never resolved and nothing alarmed",
    "730 of 741 decisions were never resolved (last success 2026-04-30)")
sub("mempool-api restarted 305 times over about 9 hours with zero notifications",
    "mempool-api restarted 305 times without a word to the owner")
sub("it was proven live on 2026-08-16, notifying the owner within about 2 h",
    "it worked in a real recurrence on 2026-08-16 (the owner reported it within about 2 h); no deliberate live "
    "drill was run")
sub("rollback for four services was only code-reviewed, never fired",
    "rollback for four services was code-reviewed but not live-fired")
sub("any \"Breaking Changes\" section held LND patches that did not affect the node",
    "any \"Breaking Changes\" section would have held LND patches that did not affect the node (0.21.3 → "
    "0.21.4)")

# --- E: TEST, PLAT --------------------------------------------------------------------------------
sub("terminated the live mainnet LND three times in one day",
    "terminated the live mainnet LND four times in one day (three by mutation runs, a fourth as a knock-on)")
sub("30 of 79 mutations survived a round that had been reported as verified",
    "a verifier found 30 of 79 mutations still green")
sub("verifier rounds 2 to 6 failed one record only on its numbers",
    "verifier rounds 2 to 6 failed one record on its wording and figures alone")
sub("two days later it had restarted 75 more times",
    "two days later its unit's restart counter read 75, with 56 more firings of the backup rule that day")
sub(", so clock sync read false for months and its runbook ran 332 times without success "
    "(2026-09-16-owner-notification-delivery.md)",
    ", so clock sync read false for months (2026-09-16-owner-notification-delivery.md)")
sub("a ratchet sat red for over a month, each session calling it \"pre-existing\", and 43 test files",
    "a ratchet sat red for over a month, each session calling it \"pre-existing\" "
    "(2026-08-24-stepup-binding-onion-socket-redgate.md), and 43 test files")
sub("a pin gate nearly passed by exempting its own file (2026-09-20-relay-profiles-c1.md) (+2 more)",
    "a pin gate nearly passed by exempting the very file it flagged (2026-09-20-relay-profiles-c1.md) (+1 more)")
sub("“Decision Q0 = \"repair all three by hand first\".”", "Decision Q0: “repair all three by hand first”")
sub("was later superseded by 2026-09-26-guard-owner-relaxations.md; the lesson \"write hidden inside inline "
    "interpreter code bypasses a path-based guard\" from 2026-10-03-fix-lock-per-session.md was later superseded by "
    "2026-10-04-guard-secret-searches-and-inline-targets.md.",
    "was later partly relaxed by 2026-09-26-guard-owner-relaxations.md (the settings files still ask); the lesson "
    "\"write hidden inside inline interpreter code bypasses a path-based guard\" from "
    "2026-10-03-fix-lock-per-session.md was later refined by 2026-10-04-guard-secret-searches-and-inline-targets.md "
    "(a false-positive fix; the bypass lesson stands).")
sub("The lesson \"advisory-only rules for AI sessions\" from 2026-09-22-ai-native-sdlc-controls.md was later "
    "superseded by 2026-09-26-guard-owner-relaxations.md;",
    "The lesson \"advisory-only rules for AI sessions\" from 2026-09-22-ai-native-sdlc-controls.md was answered in "
    "that record (the guard replaced advisory rules), and 2026-09-26-guard-owner-relaxations.md later loosened "
    "some of the guard's asks;")
sub("“\"I think for now we'll just follow the Auto mode for Claude or Codex. It's too restrictive the way I set "
    "this up.\" … \"They need to be able to adjust this permission system easily. These restrictions are more "
    "suited for something close to completion.\" Chosen: development still asks only before money moves "
    "(\"sending funds/payments, Iceman live trading, deleting wallet or chain data\"); all four repos switch now.”",
    "“I think for now we'll just follow the Auto mode for Claude or Codex. It's too restrictive the way I set this "
    "up.” … “They need to be able to adjust this permission system easily. These restrictions are more suited for "
    "something close to completion.” Chosen: development still asks only before money moves (“sending "
    "funds/payments, Iceman live trading, deleting wallet or chain data”); all four repos switch now.")
sub("“Node 22 from NodeSource (owner's choice as recorded); then 'maybe we should have moved to Node 24'”",
    "Node 22 from NodeSource (the owner's choice as the record gives it); then “maybe we should have moved to "
    "Node 24”")
sub("because Bitcoin Core 31 dropped balance fields",
    "because, on Bitcoin Core 31, getwalletinfo carried no balances and getbalances had to be used")
sub("(never exercised by a real switch in the old node)", "(not exercised as of those records)")

# --- joined answers, split ------------------------------------------------------------------
sub("“Search docs when no card (Recommended); later: Card + docs when weak (Recommended)”",
    "“Search docs when no card (Recommended)”; later “Card + docs when weak (Recommended)”")
sub("“Core fix + test (Recommended); Leave it to the runbook (Recommended); Include it now (Recommended)”",
    "“Core fix + test (Recommended)”, “Leave it to the runbook (Recommended)”, “Include it now (Recommended)”")

# --- section 3: mark the rows whose harvest field is a summary or joins answers ----------------------
sec3_start, sec3_end = t.index("## 3. Owner decisions"), t.index("## 4. Port candidates")
sec3 = t[sec3_start:sec3_end]
marks = {4: "the record's summary", 7: "the record's summary", 11: "the record's summary",
         85: "the record's summary, with a quotation", 115: "the owner's words, then the session's summary",
         122: "the record's summary, with quotations",
         9: "corrected: the record reads \"budget spent → skip that hypothesis … and a 24-hour rolling window\"",
         76: "two answers joined", 92: "two answers joined", 93: "answers to two questions joined",
         106: "three answers joined"}
for n, note in marks.items():
    m = re.search(r"^(\| %d \| )(.*?)( \| [^|]*\.md[^|]* \| [^|]* \| [^|]* \|)$" % n, sec3, re.M)
    if not m:
        sys.exit("section 3 row %d not found" % n)
    sec3 = sec3[:m.start()] + m.group(1) + m.group(2) + " *(" + note + ")*" + m.group(3) + sec3[m.end():]
    done.append((1, "section 3 row %d" % n))
t = t[:sec3_start] + sec3 + t[sec3_end:]
open(F, "w").write(t)
for n, what in done:
    print("%d× %s" % (n, what))
print(len(done), "corrections")
