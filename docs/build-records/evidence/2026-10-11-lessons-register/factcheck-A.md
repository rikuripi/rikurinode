# Fact-check A: EVID-01..10, IDEN-01..03, OWN-01..09

Records are in /home/junc/rikuri/rikurinode/docs/build-records/. All 60 repository paths (Port lines and their tests) exist at HEAD (checked against git ls-tree). Rust inline-test claims for uptime.rs and proposal_engine.rs were not opened individually.

## EVID-01
- SUPPORTED: mempool-api "Up (healthy)", 120 blocks / 20.6 h behind, frozen — 2026-08-22-mempool-page-stale-explorer-and-zero-fees.md:42-47
- NOT FOUND: "with no error or alert" — record says "no error, no exception, no restart, and the container never leaving Up (healthy)" (:46-47). It never mentions an alert. Correct to: "with no error, exception or restart".
- SUPPORTED: Electrs "Synced 100%" copied bitcoind's height whenever the port-open check passed — dashboard-measurements.md:28
- SUPPORTED: BLOCKED control plane passed because body contained "status" — dashboard-measurements.md:29
- SUPPORTED: service cards "Operational" when only the container ran — dashboard-page-truth.md:81 ("today: container running only")
- SUPPORTED: absent mempool-api read healthy — health-exact-container-names.md:165-166
- SUPPORTED: Port notes. Async probe runners (probeBitcoin etc.) have no direct tests (only stubbed in healthScore*.test.ts); lesson 248 says "Gap: the async runners ... have no unit tests".
- Rule/Tripwire: no overclaim. The "electrs on the x86 node only" wording matches lesson 248 applies_to_new_node.

## EVID-02
- SUPPORTED: "Disk space low: 0 GB"; unreadable CPU became the Guardian baseline "CPU at N% — normally 0%" — dashboard-measurements.md:774-776, :834
- SUPPORTED: `|| 0` vs `|| '—'` on peers/channels — dashboard-page-truth.md:901-902
- WRONG (minor, quoted wording): the register quotes "could not be read" for what the assistant's tools called down. Record says: "both tools called "could not read" (non-2xx, bitcoind loading) DOWN and advised `docker restart`" (dashboard-page-truth.md:1337-1338). Correct to: called "could not read" (a non-2xx or a loading bitcoind) down.
- SUPPORTED: uptime API answered `uptime_pct: 100` for a never-measured component — reliability-uptime-truth.md:354
- SUPPORTED: knowledge loader "0 services, 0 commands" from files that never existed — runbook-command-audit.md:186-191
- Rule/Tripwire: no overclaim. Mutations and the ratchet are stated as "must", and lesson 261 says a ratchet was "suggested".

## EVID-03
- SUPPORTED: mempool count read a field never sent, showed "— txs", 66,164 txs — dashboard-page-truth.md:26, :912-915
- SUPPORTED: sync ETA = remaining fraction × 48 h — dashboard-page-truth.md:461
- SUPPORTED: API shape change made infra bar show all four down — dashboard-measurements.md:278-280
- SUPPORTED: auto-install switch showed new state while server kept the old (failed POST swallowed) — upgrade-gates-round-2.md:138-139
- SUPPORTED: Owner quote, character for character including "meansuring" — dashboard-page-truth.md:14-17

## EVID-04
- SUPPORTED: Strict "in use" while bitcoind still Standard — posture-restart-to-apply.md:13; lesson 159 (config written 3.5 min after bitcoind started)
- SUPPORTED: pin watcher read Core from an uninitialised singleton on a Knots node — knots-pin-review.md:110-116
- SUPPORTED: "Last update completed successfully" permanent and undated — os-update-banner-staleness.md:14, :47
- SUPPORTED: 13-hour-old 1/8 shown as current — health-score-never-freezes.md:14-28
- SUPPORTED: Owner quotes "let the restart button surface..." (posture-restart-to-apply.md:16-18) and "Restart dashboard + fix (Recommended)" (health-score-never-freezes.md:16)
- NOTE (not a factual error): the record says the popup part was "Overturned by the owner's live test (2026-09-24): no popup" (posture-restart-to-apply.md:28). The register quotes the original ask, including "may be popup with authentication", without that.

## EVID-05
- SUPPORTED: 84,346 vs 83,260; source refused node ~10 h; `live: true` — btc-price-exchanges-first.md:13-22
- SUPPORTED: rows deleted after 3× TTL, "No data yet" — market-intel-freshness-arkb.md:32-33
- SUPPORTED: a not-yet-reported upstream row counted as 0 — lesson 236 (market-intel-freshness-arkb.md, Farside rows)
- WRONG: "a 24h volume silently omitted Coinbase, ~58 % of the total" — record says "Coinbase is ~58 % of the three" (market-cap-volume-etf-warm.md:138; :287 "Coinbase (58 %)"). Correct to: "~58 % of the three-venue total".
- SUPPORTED: all four Owner quotes and the "1. Ok" cost (market-cap-volume-etf-warm.md:15-21; market-intel-freshness-arkb.md:13-16, :57-62). The two quotes from market-intel-freshness-arkb.md are both parts of one owner message.
- SUPPORTED: backoff doubling and Retry-After — btc-price-exchanges-first.md:80, :199
- OVERCLAIM (Tripwire): "a browser network log showing no third-party calls". Lesson 228 says the Playwright log showed no browser CoinGecko calls, and that Fear & Greed and the chart fallback "still go from the browser to third parties (out of scope, stated)". The old repository proved it only for CoinGecko. Reword to: "a browser network log showing no calls to price/market APIs".

## EVID-06
- SUPPORTED: IBD monitor failed every 60 s since it shipped, read as RPC noise — bip110-invalid-mark-leak.md:44-45
- SUPPORTED: RAG canary passed on the fallback — rag-relevance-calibration.md:53-55
- SUPPORTED: collector threw on every run (added 2025-11-25, 135 errors per collection) — remove-community-issue-collection.md:39-42. "For months" is consistent with the 2025-11-25 start; the record does not say "months".
- SUPPORTED: other collector never stored a result because searchIssues returned an object — remove-mcp-data-collector.md:23-27
- SUPPORTED: 4 Owner quotes ("1. Remove it." :24; "4. remove collector and unused endpoints." :14; "1. Ok" and the cost; the AskUserQuestion choices)
- SUPPORTED: superseded caveat — lesson 361 superseded_by = remove-mcp-data-collector.md
- Rule/Tripwire: no overclaim. Several items are "should exist" in the lessons, so the register states them as prescriptions.

## EVID-07
- WRONG: "the assistant called a 3-hour-stale node 'fully synced' from verificationprogress". The record splits this in two:
  - the knowledge service called a node "fully synced" when the progress estimate was > 99.99%, so "a stale tip or a node a few blocks behind is 'fully synced'" (dashboard-page-truth.md:597-599);
  - the rewritten Bitcoin Core tool took sync from the IBD flag alone, so a 3 h stale tip read "HEALTHY · Sync: synced" (:1332-1335).
  Correct to: "the assistant's knowledge service called any node with verificationprogress > 99.99% 'fully synced', and its Bitcoin Core tool, using only the IBD flag, called a 3-hour-stale node 'synced'".
- SUPPORTED: page used a 2 h stale-tip rule — :637
- SUPPORTED: CPU ignored iowait, mean error 5.5 points — dashboard-measurements.md:23
- SUPPORTED: three disk paths agree by accident, 95 %-full backup NVMe appears nowhere — dashboard-measurements.md:24
- SUPPORTED: Owner "Every mounted drive" and its cost — dashboard-measurements.md:152-154

## EVID-08
- SUPPORTED: LND down scored 87 "Excellent" — dashboard-measurements.md:43
- SUPPORTED: shared counter bumped by page visits — lesson 253
- SUPPORTED: `overall` stayed healthy with electrs down; degraded only set in catch blocks — health-exact-container-names.md:102-104
- SUPPORTED: Tripwire "up to 21,589,200 inputs, 0 invariant failures" — dashboard-measurements.md:861-862 ("harness was shown able to fail"; other rounds 1.5M and 3M say "negative controls caught")
- SUPPORTED: all Owner quotes — dashboard-measurements.md:53, :460, :542-545, :599, :634, :758

## EVID-09
- SUPPORTED: Electrum probe clean close never settled; 13 h at 1/8 — health-score-never-freezes.md:14-34
- SUPPORTED: ~20 synchronous shell calls every 30 s — dashboard-measurements.md:50, :228
- SUPPORTED: status pre-check could wait forever; `lndCall` no timeout — posture-restart-to-apply.md:252, :355
- SUPPORTED: model call's timeout never passed to the call — health-check-parallel-stats.md:436
- SUPPORTED: "Fix it now (Recommended)" (:19); "Restart dashboard + fix (Recommended)"
- WRONG (quote): `“OK (55 s accepted, 2026-10-10)”` is shown as a verbatim owner quote. The record says "**Owner, 2026-10-10: "OK" — 55 s accepted.**" (health-score-never-freezes.md:281-282); the owner's words were only "OK". Correct to: `“OK” (55 s limit accepted, 2026-10-10)`.

## EVID-10
- SUPPORTED: substring matching vs testnet siblings, bitcoin 83.38 % vs ≈ 99.92–99.93 % — reliability-uptime-truth.md:21-35
- SUPPORTED: 10 h 27 m crash read up, last state extended forever — :38, :42
- SUPPORTED: old window logic wrong on 7,253 of 25,000 — :1060
- SUPPORTED: `last_sample_ts` and `stale` (no sample for 3 polls) — :78, :88; boundaries +899/+900/+901 s (lesson 301)
- WRONG (Rule wording): "window queries include intervals that began before the window". Lesson 303 and the record describe a crash interval that ended in the 15 minutes before `window_start` and was not fetched (`end_ts > window_start`). Correct to: "window queries include intervals that ended just before the window start (the grace period)".
- SUPPORTED: Owner quotes — :52, :55, :331, :339, :482, :557, :903, :913

## IDEN-01
- SUPPORTED: `name.contains("bitcoin")` picked bitcoin-testnet at random per poll, uptime 83 % — reliability-uptime-truth.md:22-35
- SUPPORTED: `wrapper-probe-mempool` made health report mempool down, self-healing restarted healthy mempool-api — health-exact-container-names.md:12-20; electrs-mempool-clean-stop.md:136
- SUPPORTED: with lnd absent, restart "lnd" would act on lnd-testnet — exact-container-target.md:19-21
- SUPPORTED: Owner "So must pass along the name..." (:29-30), "4. yes" (health-exact-container-names.md:38), "Yes, in fact..." (reliability-uptime-truth.md:14-17)
- OVERCLAIM (Tripwire): "refusal tests for broad names (`-e.`, `...`, `ssh`)". The old tests refused `-e.`, `...`, `.hidden`, `-` and `--all` (request-values-never-reach-a-shell.md:317). `ssh` was the case that was not fixed: "`ssh` as a client name still revokes every key" (lesson 440, Skipped item). Drop `ssh` or mark it as the case the old repo failed.
- Port: SUPPORTED — `control-plane/src/uptime.rs` exists and is the file lesson 299 is about.

## IDEN-02
- SUPPORTED: mempool-db alert carried only "mempool", classifier mapped to mempool-api — exact-container-target.md:14-17
- SUPPORTED: runbook failed "Container bitcoin-knots does not exist" — tests-restarted-live-lnd.md:83-84

## IDEN-03
- SUPPORTED: "stay on Bitcoin" stored under one key, looked up under another, `success: true`, no effect — consensus-decision-p2.md:40-45
- SUPPORTED: `lnd:*` incidents never closed because recoveries said `lightning` — lnd-sync-stall-misclassified.md:73, :181
- SUPPORTED: testnet4 LND stall would restart mainnet LND — :239
- SUPPORTED: commands built at import froze the network — assistant-execution-paths.md:296-299
- Port: SUPPORTED — containers.rs, and proposal_engine.rs has `mod tests`. Lesson 111 says "proposal tests 6/6".

## OWN-01
- SUPPORTED: Start All lacked RAM-scaled limits, lock, health gate, testnet stack — node-power-buttons.md:41-48
- SUPPORTED: runner's start plus queued unit start recreated every container, LND restarted twice — upgrade-deadlock-and-progress.md:39-44; lesson 463
- SUPPORTED: MariaDB auto-install recreated bitcoind and Electrs and restarted LND — upgrade-gates-round-2.md:114-118
- SUPPORTED: legacy `install-services.sh` would run `lsof -ti:5000 | xargs kill -9` on the live dashboard port — rollback-consolidation.md:143-151. The same record (:163) says the script was "not called by the real installer".

## OWN-02
- SUPPORTED: four units raced; 28 conflicts on five days since 2026-07-01; upgrade reported failed though apt succeeded — upgrade-reboot-compose-race.md:14, :37, :51-52
- SUPPORTED: two components brought the stack up — dashboard-page-truth.md:1029-1030
- SUPPORTED: cookie cascade started LND about 25 s early, LND came up without its onion — node-power-buttons.md:362-367
- SUPPORTED: double press started a second Electrs upgrade — electrs-0.12-support.md:308, :366
- SUPPORTED: Tripwire "7 conflicts without the lock, 0 with" — upgrade-reboot-compose-race.md:98-99, :154-155

## OWN-03
- SUPPORTED: runner held compose lock through `apt-get upgrade`; docker-ce restart; stops waited on the lock; ~9 minutes; exclusive-lock probe made stops skip — upgrade-deadlock-and-progress.md:25-36; lesson 465
- SUPPORTED: Owner "Let's just fix it" (:15, :62); Tripwire 300 pairs and SIGKILLed holder (lesson 465)
- WRONG (status word): "The fix was never proven on real systemd and Docker." The record says "Not yet proven: real systemd and Docker; CI." (:359, :425). "Never" is an absolute. Correct to: "The fix was not yet proven on real systemd and Docker when the record closed."

## OWN-04
- SUPPORTED: owner stop un-stopped itself after readers' 45 min default; heartbeat, Guardian loop, control plane, anomaly scanner (5 "wallet_missing" emails, :514), bell (30 "is down", :650) — node-power-buttons.md:36, lesson 290
- SUPPORTED: "29 Critical" while stopped — dashboard-page-truth.md:275-276
- SUPPORTED: Ubuntu upgrade owner stop held self-heal; boot scope brought stack back — ubuntu-26.04-upgrade.md:33-34; node-power-buttons.md:119-123
- SUPPORTED: Owner quotes (page-truth.md:284; node-power-buttons.md:61); network/nginx/sshd stay active (:107)

## OWN-05
- SUPPORTED: window lifted when bitcoind answered, before LND back, second LND restart — posture-restart-to-apply.md:296-318
- SUPPORTED: in-memory suppression lost across reboot, CRITICAL alerts fired — upgrade-reboot-compose-race.md:56, :245-246
- SUPPORTED: broad flag paused force-close and fund-movement monitors, renewed up to 6 h; held "down" alerts dropped — guardian-summaries-reach-the-owner.md:153, :180, :199-200
- WRONG: "self-heal restarted lnd and bitcoin during the owner's OS upgrade". The record corrects exactly this: "lnd's runbook ran (2/2); bitcoin's failed — "precheck not met — Container bitcoin-knots does not exist" (0/2) ... (first written "auto-restarted bitcoin and lnd")" (tests-restarted-live-lnd.md:82-86). Correct to: "self-heal restarted LND (and ran restart runbooks for electrs and mempool-web) during the owner's OS upgrade; bitcoin's runbook failed its precheck".
- SUPPORTED: Owner fragment "Restart All health services should read the flag, right?" — guardian-summaries-reach-the-owner.md:16
- Rule/Tripwire: "no runbook fires while an upgrade owns the stack" is a prescription. Lesson 456 says "Should exist", and the register does not claim the old repo had it.

## OWN-06
- SUPPORTED: runner restored only mainnet stack, tapd down 39 h while smoke said PASS — self-heal-p0-live-repairs.md:41, :96-97
- SUPPORTED: recurred 2026-10-08 — tests-restarted-live-lnd.md:78-81
- SUPPORTED: testnet stop wrote marker only after `compose down`; routes' timeouts shorter than compose's worst case — reliability-uptime-truth.md:412, :498, :575. Marker-before-action test: testnetOwnerStop.test.ts (:395).

## OWN-07
- SUPPORTED: six monitors ran twice, independent cooldowns; one cookie change restarted electrs, lnd, mempool twice; duplicate copy misconfigured and blind; disable flag read by a different binary — self-heal-p3-one-monitor.md:26-36. "Misconfigured/silently blind" comes from lesson 117; the record has no line with those words.

## OWN-08
- SUPPORTED: power ops in HTTP requests behind 60 s proxy, stop ~90 s per daemon — node-power-buttons.md:28, :50
- SUPPORTED: testnet routes 540/420 s behind 60 s — dashboard-page-truth.md:122-123
- SUPPORTED: approvals waited 120 s behind 60 s — repairs-outlive-the-request.md:199-200
- SUPPORTED: 215 "headers already sent" — health-check-parallel-stats.md:106; the process-crash risk is :342-345 ("uncaught at HEAD too"; the record says it was not reachable behind nginx)
- SUPPORTED: Owner "Every route (Recommended)" — :277-278

## OWN-09
- SUPPORTED: weekly channels narrowed (Push and Discord dropped) — guardian-summaries-reach-the-owner.md:127-131; hold "up to 45 minutes" vs 6 h renewal (:136, :199-200)
- SUPPORTED: Standard/Core confusion quote — posture-clarity.md:19-21
- SUPPORTED: IBD monitor would rewrite docker-compose.yml and force-recreate bitcoind on every start — remove-model-warmup-and-post-ibd.md:37-39
- SUPPORTED: consensus question had no way to be answered — consensus-decision-p2.md:20, :101
- SUPPORTED: Owner "I think we just have 2 different cards..." (engine-cards.md:14-19, quoted with ellipses); "3. Remove" (remove-model-warmup-and-post-ibd.md:18-19, an excerpt of "1. Delete warm-up; ... 3. Remove")

TOTAL: 131 claims checked, 7 wrong, 1 not found, 2 overclaims
