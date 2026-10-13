# Fact-check E: TEST-01..TEST-12, PLAT-01..PLAT-11

Records are in /home/junc/rikuri/rikurinode/docs/build-records (read-only greps only). "+N more" counts in every Why were recomputed from reqs.txt and all match (N = distinct records not cited). All Port paths exist at HEAD (ls-tree) and every stated test file exists. All Owner lines equal the lesson's owner_decision field; every double-quoted phrase was found in its record (line wraps only).

## Known error (confirmed, outside this slice's headings): LN-03 Tripwire (register line 558)
- WRONG: "Stall-rule tests (12 of 16 failed on the old code)" — record says: "`src/tests/lndSyncStall.test.ts`, 14 tests, **12 failed** on the old" (2026-09-24-lnd-sync-stall-misclassified.md:169) — correct to: "(12 of 14 failed on the old code)".

## TEST-01
- WRONG: "mutation runs of the assistant's Run tests terminated the live mainnet LND three times in one day" — record says: "LND was terminated **four** times by this session's tests, not three — 08:53:31.710, 13:27:04.907, 15:29:55.786, and 15:30:02.624, a knock-on" (2026-10-08-tests-restarted-live-lnd.md:34-37; title also says "four terminations") — correct to: "terminated the live mainnet LND four times in one day (three by mutation runs, a fourth as a knock-on of the health check)". The harvest lesson 452 still says three; the record's verifier correction supersedes it.
- SUPPORTED: 90 fake outcomes in live outcomes DB — 2026-09-16-backup-truth-and-alerts.md:100
- SUPPORTED: 93 fake entries in owner's Activity log — 2026-10-06-request-values-never-reach-a-shell.md:457
- SUPPORTED: a test rewrote live Knots bitcoin.conf — 2026-09-20-postures-per-engine.md:52-55
- SUPPORTED: stand-ins exit 126, missing runtime socket, outer logging layer, absolute-path scan, lock-location scan, checksum of live data — 2026-10-08-tests-restarted-live-lnd.md:132-175; lessons 437, 468, 79
- SUPPORTED: Port setup.ts / noLiveNode.globalSetup.js notes (Jest-specific; not network-hermetic) — lesson 452 limits
- SUPPORTED: Owner quote — 2026-10-02-cleanups-dead-security-tabs-flaky-test.md:14

## TEST-02
- WRONG (minor wording): "30 of 79 mutations survived a round that had been reported as verified" — record says: "Round 4: verifier subagent, FAIL ... **30 of 79 mutations stayed green**" (2026-09-30-dashboard-page-truth.md:1041, 1060) — the record shows the verifier of round 4 found them; it does not say a round "had been reported as verified". Correct to: "a verifier found 30 of 79 mutations still green in a round of work".
- SUPPORTED: first button-style gate passed on the bug it was written for — 2026-09-20-invisible-buttons.md:49-52
- SUPPORTED: "port stays closed while indexing" from a probe that could never succeed (/dev/tcp absent in sh) — 2026-10-03-electrs-0.12-support.md:107-114
- SUPPORTED: live check for missing WebSocket route could not fail (HEAD answered 200) — 2026-10-06-nginx-socket-io-location.md:90-93
- SUPPORTED: Rule items (scratch copy, equivalent mutants, characterisation label) — lessons 16, 281, 411

## TEST-03
- SUPPORTED: test asserted a tier, emergency stop still demanded a password — 2026-08-23-gate-executor-and-fund-twins.md:69-77
- SUPPORTED: test pinned owner_hold_reason, not that submit_runbook called it — 2026-09-26-memory-restart-asks-for-funds.md:198-201
- SUPPORTED: Run button ran nothing (verdict.allowed vs verdict.validation.allowed), no test drove a legitimate command — 2026-10-06-request-values-never-reach-a-shell.md:59-62, lesson 431 root_cause
- SUPPORTED: test resolver found files plain Node would not — lesson 400 (2026-10-04-remove-model-warmup-and-post-ibd.md)
- SUPPORTED: Tripwire and Port (startupBrokenCodeRemoved.test.ts exists)

## TEST-04
- NOT FOUND (in the cited record): "a ratchet sat red for over a month, each session calling it 'pre-existing'" — searched 2026-09-14-script-style-test-conversion.md for pre-existing/1319/1307/month: the record shows baseline 1304 and HEAD 1315 only. The claim IS supported by other records (2026-08-10-upgrade-reboot-compose-race.md:286 "1309 vs baseline 1304 — RED, pre-existing"; 2026-08-24-stepup-binding-onion-socket-redgate.md:138-141 "PRE-EXISTING RED ... 1319"; 2026-09-03-mdns-local-name-docker-bridge.md:250). Fix: cite those records, or drop the citation to script-style-test-conversion for this clause.
- SUPPORTED: 43 test files outside CI; fsmEngine.test.ts 20 of 23 assertions at a deleted module — script-style-test-conversion.md:6, 137-142, lesson 68
- SUPPORTED: frontend lint matched only .js/.jsx — 2026-09-30-dashboard-page-truth.md (lesson 282)
- SUPPORTED: pin gate nearly passed by exempting a file (consensusBuilds.ts) — 2026-09-20-relay-profiles-c1.md:60-64. Note: the file nearly exempted was the scanned file, not the gate's own file; "its own file" is loose. Suggest "nearly passed by exempting the file it flagged".
- OVERCLAIM (Owner line): the quoted text “Owner decision (2026-09-14): delete the file (fsmEngine.test.ts), after its 3 surviving assertions were shown to duplicate existing coverage.” is the harvester's summary, not the owner's words; the record (script-style-test-conversion.md:152) is the AI's note: "**Owner decision (2026-09-14, same session): delete the file.**". Present it unquoted or as "Owner decision: delete the file".
- OVERCLAIM (Port): the Port test "requestValuesNoShell.test.ts" belongs to lesson 427 (EXEC-01), not to the ratchet lessons 68/71 of TEST-04. It tests the shell-interpolation counter only. Fine only if the Port line says so.
- SUPPORTED: Superseded note (script-style-test-conversion.md fixed the require-count attribution) — plausible per lesson 56 superseded_by; the record never uses the word "superseded".

## TEST-05
- SUPPORTED: CI red 7 weeks — 2026-09-23-ci-shared-deps.md:13-14
- SUPPORTED: weekly dep-audit only on non-default branch, "has never run once" — 2026-09-28-runtime-dependency-vulnerabilities.md:199-203
- SUPPORTED: deployed with failing suite, pipeline status was tail's — 2026-09-26-mempool-api-memory.md:236, 422
- SUPPORTED: one-word card edit ("after") broke ranking test — 2026-10-02-channel-backup-after-open-close.md:137-145
- SUPPORTED: Owner quote — runtime-dependency-vulnerabilities.md:36-38
- SUPPORTED: Tripwire items; "scheduled gate ran within 8 days" is labelled (proposed), matches lesson 219 ("not made")

## TEST-06
- SUPPORTED: broad staging swept in a deletion; committed drbRouting.ts routed to a nonexistent DRB for 11 days — 2026-09-17-drb-schema-gate.md:158-166, 178-182 (the sweep was done by the self-heal session over this work, so "another session's deletion" is the viewpoint of this record's session; acceptable)
- SUPPORTED: twice a gate passed locally and failed in CI because of another session's uncommitted edits — 2026-10-04-gates-run-on-the-commit.md:13-17, 2026-10-03-upgrades-cannot-break-a-service.md:462-474
- SUPPORTED: Owner quote ("gattes" typo is in the record); Port .githooks/pre-commit + precommitGatesOnIndex.test.ts exist

## TEST-07
- SUPPORTED: sudo-rs record written 25 days later by another session — 2026-08-08-sudo-rs-sudoers-wrappers.md:11-12
- WRONG (imprecise): "verifier rounds 2 to 6 failed one record only on its numbers" — record says: "Verifier round 2: FAIL, on the record only"; "round 5: FAIL, on the record only, on units"; "round 6: FAIL, on one phrase" (2026-09-26-mempool-api-memory.md:347, 378, 395, 404), and lesson 200 includes an unmet acceptance clause ("never reaches its limit") and a swap claim. Correct to: "verifier rounds 2 to 6 failed one record on its wording and figures although the code and tests were sound".
- SUPPORTED: `head` hid one of 133 uses — 2026-09-28-fix-lock-covers-inline-tests.md:144-145
- SUPPORTED: edit matched nothing yet reported success — 2026-08-24-stepup-binding-onion-socket-redgate.md:75
- SUPPORTED: Owner quote — 2026-10-04-guard-secret-searches-and-inline-targets.md

## TEST-08
- WRONG: "two days later it had restarted 75 more times" — record says: "a pre-commit sanity check found `NRestarts=75` and 56 more `DRB-BACKUP-STALE-01` firings that same day" (2026-09-14-guardian-scb-restart-loop.md:21-23, 245) — 75 is the unit's restart counter value, not 75 additional restarts. Correct to: "two days later the dashboard unit's restart counter read 75 and the stale-backup runbook had fired 56 more times that day".
- SUPPORTED: one quiet cycle taken as proof — same record :18-20
- SUPPORTED: committed diagnosis blamed a formula that measurement showed correct — 2026-09-02-rag-relevance-calibration.md:43, 95-100
- SUPPORTED: name-based sweeps missed regex form and eighth loginless shell site — 2026-10-05-usb-backup-run-media.md:212, 318
- SUPPORTED: both Owner quotes
- OVERCLAIM (Owner line 1): “Decision Q0 = "repair all three by hand first".” is a harvester summary wrapped in curly quotes; only the inner words are quoted from the record.

## TEST-09
- SUPPORTED: three wrong "dead" verdicts, one would have deleted two live endpoints — 2026-08-23-runbook-command-audit.md:170-176, 204-206
- SUPPORTED: deleting a stylesheet removed styles used by 31 components (".modal-overlay is used by 31 components") — 2026-09-30-dashboard-page-truth.md:1678-1683
- SUPPORTED: deadness proof missed port reservations — 2026-09-28-runtime-alerts-round-two.md:131 / lesson 218
- SUPPORTED: warm-up written for Ollama logged a failure every start — 2026-10-04-remove-model-warmup-and-post-ibd.md:15-24, 89
- SUPPORTED: Owner quote (record :18-19)

## TEST-10
- SUPPORTED: relay-posture buttons invisible, owner concluded the choice did not exist — 2026-09-20-invisible-buttons.md:17-25
- SUPPORTED: border variable used 243 times, defined by no theme; raw keys on channel-open errors — 2026-09-30-dashboard-page-truth.md:269-273, lesson 269
- SUPPORTED: every visible defect was a rendering defect — 2026-09-22-posture-panel-frontend-test.md:13-14
- SUPPORTED: Owner quote — dashboard-page-truth.md:278-

## TEST-11
- SUPPORTED: settings.local.json write / rm -rf .claude/state silent allow — lesson 172 (2026-09-25-guard-self-disable-hole.md)
- SUPPORTED: rewrite dropped six money-move checks (round 3 found 19, six money moves) — lesson 392
- SUPPORTED: interpreter heredocs wrote test code under the lock — lessons 359, 405
- SUPPORTED: Tripwire (about 70,000 variants, none looser; byte-identical guards) — lesson 392
- OVERCLAIM (Superseded note): "The lesson 'guard can be switched off through an unprotected side channel' ... was later superseded by 2026-09-26-guard-owner-relaxations.md". That record (:34-43) relaxes only fix-lock off, container restarts and edits to .claude/hooks and CI workflows; it says the `.claude/settings*` files and the fix-lock file "still ask". It does not use the word superseded. Reword: "partly relaxed by the owner on 2026-09-26 (hook and CI edits no longer ask; settings files still do)". The Rule ("protects every way of disabling it") is therefore not contradicted but the status word is unsupported.
- OVERCLAIM (Superseded note): "'write hidden inside inline interpreter code bypasses a path-based guard' from 2026-10-03-fix-lock-per-session.md was later superseded by 2026-10-04-guard-secret-searches-and-inline-targets.md". That record refines the inline-code tripwire to look at write targets (false-positive fix, :21-29, 47-55); the bypass lesson itself stands (and 2026-10-05-guard-interpreter-writes-inline-tests.md found another bypass). Reword to "refined by".
- OVERCLAIM (Owner lines): lines 2 and 3 of the Owner block are fine. Line 5 does not apply to this slice's other lines.

## TEST-12
- SUPPORTED: every rule had been advisory — 2026-09-22-ai-native-sdlc-controls.md:35
- SUPPORTED: control-plane restarts waited ~11 h and ~6 h — 2026-09-27-guard-profiles.md:21-23, lesson 201
- SUPPORTED: shared lock file blocked parallel sessions; `off` released anyone's — 2026-10-03-fix-lock-per-session.md:15
- SUPPORTED: lock released in same command as test run — 2026-10-06-nginx-socket-io-location.md:44-48
- SUPPORTED: funds-daemon restart gate to be raised again when mainnet channels open — 2026-09-26-guard-owner-relaxations.md:140-141 ("raise the LND/Bitcoin restart gate again as a question")
- SUPPORTED: Owner quotes 1-6 appear in records (incl. 2026-09-26 "We'll put these back on when appropriate" at :137; guard-profiles quotes at :14-26)
- OVERCLAIM (Owner line 5, 2026-09-27-guard-profiles): the block ends with “Chosen: development still asks only before money moves ...; all four repos switch now.” — "Chosen:" is the harvester's summary inside the curly quotes; only the two sentences and the "sending funds/payments ..." phrase are the owner's/record's words.
- OVERCLAIM (Superseded note): "advisory-only rules for AI sessions ... later superseded by 2026-09-26-guard-owner-relaxations.md" — the 09-22 record itself replaced advisory rules with the guard; the 09-26 record only loosened some asks (see TEST-11). Reword "partly relaxed". The 09-27 control-plane-restart -> guard-profiles link is plausible (profiles record cites the same evidence).

## PLAT-01
- SUPPORTED: .local name resolved to Compose bridge 172.18.0.1 after container churn; deny-list could not name br-<id> bridges whose id changes; avahi config hand-edited — 2026-09-03-mdns-local-name-docker-bridge.md:15, 20, 49-60
- SUPPORTED: hard-coded Ubuntu repo path, lsb_release absent on minimal installs — lesson 4 (2026-08-08-sudo-rs-sudoers-wrappers.md)
- SUPPORTED: Rule's mDNS allow-list, empty-list refusal, restore-on-mismatch — mdns record :127-143, scripts/rikuri-mdns-interfaces-fix.sh:49, 95
- Note: "OS identity comes from /etc/os-release" is a new rule (lesson 4 says "Should exist"), fine as a rule.

## PLAT-02
- WRONG (citation): "its runbook ran 332 times without success" is attributed to 2026-09-16-owner-notification-delivery.md; that record has no "332" and no DRB-HOST-CLOCK-DRIFT-01 (searched both). The figure is in 2026-09-17-drb-schema-gate.md:193 and :218 ("332 attempts, **0 successes**"). Correct the citation (add 2026-09-17-drb-schema-gate.md). "false on every cycle for months" is at owner-notification-delivery.md:113.
- SUPPORTED: NTP probe printed nothing on this systemd; repeated -p form works — owner-notification-delivery.md:56-57
- SUPPORTED: "Temp 60 C" was the Wi-Fi card (iwlwifi); acpitz fallback; a rewrite dropped Pi temperature — 2026-09-30-dashboard-measurements.md:22, 627
- SUPPORTED: chain disk unknown because volume path unreadable (EACCES; read via mount point) — dashboard-measurements.md:1182-1192
- SUPPORTED: util-linux 2.41 prints booleans — 2026-10-05-usb-backup-run-media.md:230-231
- SUPPORTED: Owner quote and choices (:14, :155, :158)
- OVERCLAIM (Rule, minor): "Pi 5 cpu_thermal" and "x86 ... coretemp": the records say only "Raspberry Pi" cpu_thermal and k10temp; Pi 5 and coretemp are new-node assumptions, acceptable as a rule but not old-repo facts.

## PLAT-03
- SUPPORTED: upgrade replaced NodeSource Node 20.20.2 with Ubuntu nodejs 22.22.1 under better-sqlite3 built for module version 115; health 200; smoke stayed GREEN 29/1/0 — 2026-10-03-ubuntu-26.04-upgrade.md:121-130, 142-145
- SUPPORTED: next runtime (Node 24) old module core-dumped dashboard — ubuntu-26.04-upgrade.md:152-158, lesson 364
- SUPPORTED: Owner quotes (:131, :152, :14) and "5. Yes add smoke check." (smoke-catches-broken-native-modules.md:18)
- OVERCLAIM (Owner line 2): “Node 22 from NodeSource (owner's choice as recorded); then 'maybe we should have moved to Node 24'” mixes a harvester note ("owner's choice as recorded") with a quote; record has "Owner's choice (2026-10-03): **Node 22 from NodeSource**" and ("maybe we should have moved to Node 24") at :152.

## PLAT-04
- SUPPORTED: mempool-api crash-looped 305 times on default heap — 2026-08-10-bip110-invalid-mark-leak.md:88; then at the raised ceiling (103 restarts) — 2026-08-16-mempool-oom-recurrence.md
- SUPPORTED: container hit its limit 21,921 times; size and heap set in different places — 2026-09-26-mempool-api-memory.md:36, 107
- SUPPORTED: six containers ran at default limits after partial recreates — 2026-10-03-upgrade-gates-round-2.md (lesson 370)
- SUPPORTED: Owner quotes 2-5 verified (mempool-api-memory.md:23-27, 82, 451-452; upgrade-gates-round-2.md:261-264). Owner line 1 and the first half of line 2 are explicitly labelled as record/harvest text, which is honest. The “Standing decision ... ” item is the record's wording (oom-recurrence.md:48), not the owner's, and is labelled so.
- SUPPORTED: Superseded note (heap raised 2G->3G after 1536 MB ceiling hit) — lesson 9 superseded_by

## PLAT-05
- SUPPORTED: dashboard unit Requires=docker.service went down on every Docker restart — 2026-10-09-upgrade-deadlock-and-progress.md (lesson 467)
- SUPPORTED: control-plane restarts erased update-freeze marker in /run — 2026-09-16-rust-alert-delivery-and-owner-token.md (lesson 93)
- SUPPORTED: awaiting an email before readiness could cause a systemd restart loop (3 min start timeout) — 2026-10-04-config-tamper-notifies-owner.md (lesson 387; conditional "could" is accurate)
- SUPPORTED: systemd-analyze verify used on a drop-in — rust-alert-delivery-and-owner-token.md:148
- SUPPORTED: Tripwire items; "never-resolving send under 500 ms" is lesson 387's test

## PLAT-06
- SUPPORTED: probe used `nc`, absent from bitcoind image; 36 cascades since 2026-08-10 — 2026-09-17-self-heal-p2-probes-and-selection.md:30
- SUPPORTED: bitcoind started before Tor, exited on unresolvable proxy; Tor served only the dashboard onion while recovery reported success — 2026-09-30-node-power-buttons.md (lesson 293, 295)
- SUPPORTED: two repair paths restarted Tor and LND twice per Docker-restarting update — upgrade-deadlock-and-progress.md:287 (lesson 464)
- SUPPORTED: "not restarting blind" — self-heal-p2:48; Owner quotes (node-power-buttons.md:333, 528, 544)
- SUPPORTED: Port tor_cascade.rs "reads Docker container addresses" (container_ips via bollard)

## PLAT-07
- SUPPORTED: "Standard" meant engine defaults; Core and Knots differed (datacarriersize 100000 vs 83 etc.) — lesson 143, 2026-09-20-postures-per-engine.md
- SUPPORTED: Knots overlay did not parse from 2026-09-20 to 2026-10-02 (12 days) while node ran Core — 2026-10-02-knots-overlay-parses.md:19, 52 (the failing file is the Knots compose overlay, not bitcoin.conf; "Knots configuration" is acceptable)
- SUPPORTED: Knots-only option (mempoolfullrbf) in Core's config — lesson 150 (2026-09-20-relay-profiles-c1.md)
- SUPPORTED: Electrs 0.12 required bitcoind REST, served without authentication — 2026-10-03-electrs-0.12-support.md:19-23
- SUPPORTED: Owner quotes (knots-overlay-parses.md:26, electrs-0.12-support.md:15); Superseded note (engine-cards.md:104-109 says "not pruned (-prune=0)")

## PLAT-08
- SUPPORTED: "Synced" from verificationprogress; stalled tip read Synced for about 50 h — dashboard-measurements.md:34, 1045; stall detector fooled over four rounds — lesson 251
- SUPPORTED: Knots health check read down for a whole first sync — 2026-09-30-reliability-uptime-truth.md:1029-1030
- SUPPORTED: Rule's synced definition (blocks == headers, 2 h tip) — dashboard-measurements.md:101
- OVERCLAIM (Why): "a wallet refresh threw about once a minute because Bitcoin Core 31 dropped balance fields" — dashboard-page-truth.md:754, 1346, 1383 say it threw 'toFixed' errors about once a minute and that the fix reads `getbalances` "when `getwalletinfo` has none (Bitcoin Core 31)". The record does not say Core 31 "dropped" fields. Reword: "because getwalletinfo returned no balance fields on Bitcoin Core 31".
- SUPPORTED: Owner quote (dashboard-measurements.md:758, 820) — the second half is partly summary ("after being told the stated cost was false and asked again" is the harvester's gloss).

## PLAT-09
- SUPPORTED: after Knots to Core switch, Core inherited the invalid mark, crawled the 1-2%-hashrate chain (9 blocks/10 h) until owner ran reconsiderblock — 2026-08-10-bip110-invalid-mark-leak.md:39-40, 101-103; also 2026-09-20-knots-repin-and-gate.md
- SUPPORTED: Owner line (summary labelled by the harvest; inner quote at the record)
- OVERCLAIM (Tripwire): "an engine-switch drill (never exercised by a real switch in the old node)" — lesson 6 says the convergence supervisor was "not yet exercised by a real switch at record time" (2026-08-10), and lesson 140 says the switch was "owner-gated and unverified" (2026-09-20). Neither proves "never" for the whole old repository; and the 2026-08-10 incident was itself a real switch. Reword: "not exercised by a real switch as of the records (2026-08-10, 2026-09-20)".

## PLAT-10
- SUPPORTED: USB Bluetooth adapter failed firmware load at two boots after outage (06:22, 10:15) — 2026-09-30-bluetooth-revive-at-boot.md:80-83
- SUPPORTED: old local fix pointed at deleted /home/junc/Aulora path and `set -e` exited before its remedy — :90-93
- SUPPORTED: review found it would authorize policy-de-authorized devices and could reset a combined Wi-Fi+Bluetooth dongle ("maybe the node's link") — :203-212
- SUPPORTED: Port note: record Status IN PROGRESS (verifier box and live-run boxes unchecked, :9, 156-158); accepted review fixes absent from HEAD scripts/rikuri-bluetooth-revive.sh (no HELD/marker logic). The DefaultDependencies=no and TimeoutStartSec=300 nit WAS committed (systemd/rikuri-bluetooth-revive.service), which the register does not claim otherwise.
- SUPPORTED: Owner quote (:13, :26)

## PLAT-11
- SUPPORTED: the site the owner used (ryzen.conf: ryzen.local :80 and :3002) had no /socket.io/ location; nginx answered with index.html (200); socket.io never connected — 2026-10-06-nginx-socket-io-location.md:14-17, 58-62; 2026-09-28-runtime-dependency-vulnerabilities.md:240-246
- SUPPORTED: Tripwire (101 on websocket handshake, mutations red) — nginx record :84-95
- SUPPORTED: Owner quote (:19); Port test exists

TOTAL: ~165 claims checked, 6 wrong (TEST-01 three-vs-four, TEST-02 "reported as verified", TEST-07 "only on its numbers", TEST-08 "75 more", PLAT-02 wrong citation for 332, plus LN-03 "12 of 16" outside the slice), 1 not found (TEST-04 "over a month ... pre-existing" in the cited record), 12 overclaims (TEST-04 x2, TEST-08, TEST-11 x2, TEST-12 x2, PLAT-02, PLAT-03, PLAT-08, PLAT-09, plus Owner-line summary-as-quote items)
