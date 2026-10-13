# Fact-check D: EXEC-01..08, AI-01..10

All Port paths and named test files exist at HEAD (checked with `git ls-tree`): scripts/quality-ratchet.mjs/.json, requestValuesNoShell, templater.rs + runbook-template-cases.json, mountPathNoShell, apiAccessPolicy(.test), stepUp(+Binding test), storageKnownDrivesOnly, trustedNetwork, rateLimiterLanTrust, internalServiceToken, internalServiceAuth, aiRunPolicy, assistantExecutionPaths, emergencyStop(+test), conceptCardsIntegrity, conceptCardBudget, retrievalRelevance, ragRelevanceCalibration, slimKnowledge (+slimKnowledge/cardBlend/cardRanking tests, fixtures/card-questions.json, cardRankingCheck.ts), docNamesUnique, ragSources, ragSources/ragSweepSafety tests. Port "what it proves" lines match the lessons' port_candidate fields.

## EXEC-01
- SUPPORTED: GET /api/upgrades/status/:service loginless on LAN; URL value into `docker inspect` via shell — 2026-10-06-request-values-never-reach-a-shell.md:36-48
- SUPPORTED: 19 of 229 shell-text sites reachable with untrusted input — same record:128-136
- SUPPORTED: drive label reached shell strings in 8 places, one a loginless route — 2026-10-05-usb-backup-run-media.md:44-56 (six listed sites + 8th site `blockchain-status` du added after round 3), :166-176 (check-initialization loginless)
- SUPPORTED: value inside runbook single quotes ended up unquoted in the shell — 2026-09-17-self-heal-p2-honest-executor.md:43-44
- SUPPORTED: owner quotes "Fix all six now (Recommended)" (usb:30) and the "Let's also fix S11, 13, and 8..." text (lesson 427 owner_decision)
- SUPPORTED: prototype-key merge rule (lesson 75, 2026-09-16-backup-device-config-store.md); alias-probe ratchet (lesson 439)
- SUPPORTED: Port lines (ratchet, templater "do not port as is", mountPathNoShell)

## EXEC-02
- SUPPORTED: re-cased `/api/Lightning-Mobile/zeus-connection` returned admin macaroon without credentials — 2026-08-23-auth-gate-case-bypass.md:15,23-25
- SUPPORTED: fund routes and AI executor matched no tier — 2026-08-23-gate-executor-and-fund-twins.md:20-23
- SUPPORTED: theme change raised the funds-password modal — 2026-08-23-loginless-over-gating.md:24
- SUPPORTED: public route listed every .onion and OS username — 2026-08-24-stepup-binding-onion-socket-redgate.md:20
- SUPPORTED: Tripwire (968 routes x 5 spellings, lesson 442); Port line

## EXEC-03
- SUPPORTED: password for one benign action gave a token replayable on any step-up route — 2026-08-24-stepup-binding-onion-socket-redgate.md:13,40-44
- SUPPORTED: Safe Shutdown/Start All/Restart All dead in loginless mode, no initiation line in 14 days — 2026-09-30-node-power-buttons.md:20-24
- SUPPORTED: first nine clicks got "401 Token expired" — 2026-09-23-posture-restart-to-apply.md:283-284
- SUPPORTED: Owner "should require password" — 2026-09-23-posture-restart-to-apply.md:33

## EXEC-04
- SUPPORTED: Terminal page showed a password+2FA lock that unlocked itself, backend deleted — 2026-08-23-remove-terminal-page.md:14,27
- WRONG (minor): Upgrades page rendered "✓ Ready to upgrade" — record says the green Upgrade BUTTON was observed rendered after the API fix (2026-09-20-consensus-upgrade-guard.md:66-70); the badge text is stated as what the local countdown "would still have shown" (:77-79). Also the release was flagged consensus-changing/not-ready by the API, not "refused". Correct to: "the Upgrades page still rendered the green Upgrade button for a consensus-changing release the API had marked not ready, because it recomputed readiness locally".
- SUPPORTED: unreachable tabs held a second copy of the AI emergency stop — 2026-10-02-cleanups-dead-security-tabs-flaky-test.md (lesson 320)
- SUPPORTED: Owner quote "3. Dead code should be cleaned up if not needed." — same record:13
- OVERCLAIM (Tripwire): "a test mapping each UI gate to a server tier" — lesson 39 says "Should exist"; the old repo did not have it. The bundle check and render test do exist. Mark the mapping test "(owed)" as done elsewhere in the register.

## EXEC-05
- SUPPORTED: agent POST /fix ran `sh -c` as root, no-op auth because no token configured, no caller — 2026-09-17-self-heal-p3-one-monitor.md:38-39,54
- SUPPORTED: websocket auth shared an error boundary with notifications — 2026-08-24-stepup-binding-onion-socket-redgate.md:24-25
- OVERCLAIM (Tripwire): "a simulated registration-failure test" — lesson 54: "Should exist"; not built in the old repo. Mark "(owed)". The route-surface test proven red by re-adding /fix does exist (the_agent_exposes_no_remediation_endpoints).

## EXEC-06
- SUPPORTED: drive-browse route listed any readable directory to LAN clients, 269 entries under /etc, bare startsWith — 2026-10-07-storage-routes-known-drives-only.md:19-22; 2026-10-06-eject-outcome-not-from-label.md:211,307-308
- SUPPORTED: tripwire cases (/etc 404, ../BACKUP2, symlink out) — lesson 444
- SUPPORTED: Owner "Fix now, own record (Recommended)" — storage record:29, eject record:302

## EXEC-07
- SUPPORTED: Mac on IPv6 link-local got 136 HTTP 429s; correct helper had zero callers; second incident — 2026-09-14-rate-limiter-ipv6-lan-trust.md:21-23,59
- SUPPORTED: loopback trust rejected because the proxy forwards LAN requests from 127.0.0.1 — 2026-09-16-rust-alert-delivery-and-owner-token.md:79-80
- SUPPORTED: peer node data accepted with no signature check — 2026-08-23-gate-executor-and-fund-twins.md:150
- NOTE (not a defect): the signature rule is "maybe" for the new node (lesson 36 applies_to_new_node: only if the x86 and Pi nodes exchange messages); Rule states it unconditionally. Consider "if nodes exchange messages". The Tripwire already says "(owed)".

## EXEC-08
- SUPPORTED: LAN shell injection root-equivalent because dashboard user in docker group — 2026-10-06-request-values-never-reach-a-shell.md:36-45
- SUPPORTED: reboot reason `-c` cancelled the reboot after the stack had stopped — same record:288-290
- SUPPORTED: argument-glob sudoers rules would have stranded drive operations under sudo-rs — 2026-08-08-sudo-rs-sudoers-wrappers.md:22 (lesson 3: "drive, backup and candidate operations")
- SUPPORTED: root container given the probe-name pattern is exempt from the root scan — 2026-10-03-upgrades-cannot-break-a-service.md:273
- OVERCLAIM (Tripwire): "a check that the backend's user cannot reach the runtime socket" (lesson 428: "None in the record... Should exist") and "a check that every privilege rule is an exact path" (lesson 3: "Should exist") were never built in the old repo; only the reboot argv test exists (requestValuesNoShell.test.ts). Mark the other two "(owed)".

## AI-01
- SUPPORTED: chat auto-ran autoApprove/low-risk database entries, one a write (lncli newaddress) — 2026-10-08-assistant-execution-paths.md:43-51
- SUPPORTED: /api/ai/execute ran any entry incl. `docker restart lnd` with no validator — same:14-18
- SUPPORTED: agent whitelist accepted `cat` of a private SSH key via `../..` — same:21-23
- SUPPORTED: allow-list admitted `systemctl status -H <user>@<host>` that spawned ssh — 2026-10-06-request-values-never-reach-a-shell.md:284-285
- SUPPORTED: 20 of 21 red on old code — 2026-10-08-assistant-execution-paths.md:128 ("20 failed, 1 passed")
- SUPPORTED: 117 probes — 2026-10-06 record:360 (verifier; 35 allowed, 81 refused). Note: these were the verifier's probes, "the old one had 117" is acceptable.
- SUPPORTED: Owner "Click required, auto off" (10-06:64,384) and "Own record now (Recommended)" (10-08:29)

## AI-02
- SUPPORTED: after eight verifier rounds the guard listed forms it cannot see (xargs, code strings, run-time paths), "tripwire, not a sandbox" — 2026-10-04-guard-secret-searches-and-inline-targets.md:479,485-488 (rounds 1-8 present)
- SUPPORTED: collector pulled GitHub issue text, 20 injection warnings per start, no consumer — 2026-10-04-remove-mcp-data-collector.md:25-38
- SUPPORTED: agent-gateway plan required read-only defaults and approval-queue projection — 2026-09-20-agent-mcp-gateway.md:19,127,161
- SUPPORTED: Owner "4. remove collector and unused endpoints." — collector record:14
- OVERCLAIM (Tripwire): "a test that no exposed tool is both authoritative and dangerous" — lesson 127: "Planned... not yet built"; only the sandbox test is marked "(owed)". Mark this "(planned)" as well.
- NOTE: Rule items "per-token scopes on a private network" and "dangerous tools projected onto the approval queue" come from a plan (G0 done, G1-G4 not started), not a built feature; fine as a rule, but do not imply the old node did it.

## AI-03
- WRONG: "an approved command on the agent path ran to the end 5.9 s after the stop and reported success" — this happened only on a MUTANT (X1) of the agent executor, not on the old production code. Record says: "on the X1 mutant an approved `docker logs electrs --tail 7` ran to the end 5.9 s after the stop (`status: "success"`), where the candidate killed it (TERM)" (2026-10-08-assistant-execution-paths.md:156-159). Correct to: "in a test mutant of the agent executor that skipped the policy, which also dropped the emergency stop, an approved command ran to the end 5.9 s after the stop and reported success; no test covered the stop on the agent path."
- WRONG (minor): status reading "not operational" is presented as a quote — record says `aiOperational: false` (2026-08-24-ai-emergency-stop-actually-stops.md:23-24). Correct to: status reading `aiOperational: false` (chat still answered and executed the getBlockHeight tool).
- SUPPORTED: a brake that needs a password first is not a brake — 2026-08-23-gate-executor-and-fund-twins.md:45-48 (a paraphrase, correctly not in quote marks)
- SUPPORTED: Owner three quotes — 2026-08-24-ai-emergency-stop-actually-stops.md:119,127,131 (the owner's questions, quoted verbatim)
- SUPPORTED: Port note "mid-flight model-call cancellation (not done in old node)" — lesson 49 tripwire.

## AI-04
- WRONG (quote): "UNHEALTHY / Blocks 0 / Peers 0" — record says: "UNHEALTHY / Sync: down (0.00%) / Blocks: 0 / 0 / Peers: 0" on a synced node with 19 peers (2026-09-30-dashboard-page-truth.md:1259-1260). Correct to the exact string, or drop the quote marks.
- SUPPORTED: advised pruning on a txindex node (the tool's 95% disk check, "Enable blockchain pruning") — same:1588
- SUPPORTED: assistant had no tool that read the health score — 2026-09-30-dashboard-measurements.md:1058
- WRONG: "it presented a 4-hour-old price as 'Current Bitcoin Price'" — record says: "the AI presented an old saved row as "Current Bitcoin Price", with no date" (2026-09-29-btc-price-exchanges-first.md:433-434). "4 h ago" is only a test-fixture string (:317). Correct to: "it presented an old saved price row as 'Current Bitcoin Price', with no date".
- SUPPORTED: Owner "Note doesn't degrade (Recommended)" (page-truth:1705) and "Same rule (Recommended)" (:1811)

## AI-05
- SUPPORTED: embedding model truncated 15,013,666 vs 22,972,370 bytes (15.0 of 23.0 MB), canary "Protobuf parsing failed", 476 "Failed to index", interrupted by a stop — 2026-09-16-self-heal-p0-live-repairs.md:36-38,71,91
- SUPPORTED: checksum-on-load planned, not built (:113)

## AI-06
- SUPPORTED: card loader silently dropped cards twice, second time because the first fix had no gate — 2026-08-10-upgrade-reboot-compose-race.md; 2026-09-02-os-update-banner-staleness.md (lessons 14, 58)
- SUPPORTED: 1,500-byte cut ended the reliability card mid-sentence and read as the opposite of the owner's rule — 2026-09-30-reliability-uptime-truth.md (lesson 308)
- SUPPORTED: telemetry listed cards the budget had dropped — 2026-10-02-slim-path-searches-docs-when-no-card.md (lesson 338)
- WRONG (attribution): Owner line 1 cites 2026-09-30-reliability-uptime-truth.md for both choices. "Shorten cards to fit (Recommended)" is there (:1163), but "Search docs when no card (Recommended)" is the owner's choice recorded in 2026-10-02-slim-path-searches-docs-when-no-card.md:44 (reliability only has the lowercase phrase at :1342). Cite both records.
- SUPPORTED: Owner "Shorten cards to fit (Recommended)" — 2026-10-02-concept-cards-fit-slim-budget.md:24; "We can increase the context window to 3000 bytes..." — slim record:53-55 (typo "cars" is the owner's)
- SUPPORTED: Superseded caveat — lesson 308 superseded_by 2026-10-02-slim-path-searches-docs-when-no-card.md

## AI-07
- SUPPORTED: thresholds 0.5/0.6 vs scores 0.35-0.63, store discarded for ~40%/~70% of queries, fallback hid it — 2026-09-02-rag-relevance-calibration.md:45-50,109
- SUPPORTED: 13 of 36 uptime questions got neither card nor docs — slim record:21
- SUPPORTED: "Where is the Terminal page?" got "no information" though direct search ranked the answer first — 2026-08-23-remove-terminal-page.md:116-128
- SUPPORTED: 242 questions, each card's third question held out — slim record:192-194
- WRONG (quote): Owner line 3: "Blend word + meaning (Recommended) — supersedes the earlier choice 'Fix the word-matching (Recommended)'" — the record's quote is only "Blend word + meaning (Recommended)" (slim record:70-71); the "supersedes" clause is the record's own annotation (:88, which reads 'This supersedes "Fix the word-matching" (word-matching only)'). Put the clause outside the quote marks.
- SUPPORTED: Owner 1 "Fix the word-matching (Recommended)" (reliability:1367) and 2 "Search docs when no card (Recommended); later: Card + docs when weak (Recommended)" (slim:44, :302)
- NOTE: Port says values belong to all-MiniLM-L6-v2: supported (calibration record:45, slim:186 in-process MiniLM)

## AI-08
- SUPPORTED: 751-token Health score section lost owner's new choices; corrections files without headings became single unretrievable chunks — 2026-09-30-dashboard-measurements.md:304-306,464-465
- SUPPORTED: "why is the volume so low" buried in a long chunk — 2026-09-29-market-cap-volume-etf-warm.md:222
- SUPPORTED: "target <= 450 tokens, never over 512" — 512 in reliability record (none over 512, :1039); 450 appears as the chunk target in 2026-10-02-concept-cards-fit-slim-budget.md:166 and 2026-09-30-node-power-buttons.md:147 (not in the reliability record that lesson 310 cites)

## AI-09
- SUPPORTED: advised upgrading Knots to 29.4, an RDTS build that leaves the chain; stale advice checked gone from live store — 2026-09-20-knots-repin-and-gate.md:32-36,193-198
- SUPPORTED: commands store cited downgrading overlays (12 entries); 42 of 77 entries were make targets, no Makefile — 2026-08-22-rollback-consolidation.md:187-192
- SUPPORTED: cards claimed closing channels sweeps to cold wallet; "Does a force close send my funds to my cold wallet?" got no answer — 2026-10-02-concept-cards-fit-slim-budget.md:106,227
- SUPPORTED: guides named controls that do not exist — 2026-09-30-dashboard-page-truth.md (lesson 275)
- SUPPORTED: Superseded caveat — lesson 30 superseded_by 2026-08-23-runbook-command-audit.md

## AI-10
- SUPPORTED: three glossary.md files overwrote each other; Bitcoin and Lightning glossaries missing — 2026-10-02-knowledge-store-one-name-one-guide.md:14-16
- SUPPORTED: doc watcher indexed working-tree text for behaviour the running node lacked — 2026-09-30-dashboard-page-truth.md:588-592; 2026-10-06-request-values-never-reach-a-shell.md:443-445
- SUPPORTED: ingest failed because chromadb had been stopped — 2026-10-02-concept-cards-fit-slim-budget.md:195-196
- SUPPORTED: Owner "1. Make the 2 glossaries if that's what's needed." — one-name record:24
- NOTE: Rule items "stamped with the commit" and "failed ingest is a visible health finding" are suggestions in lessons 286/325, not old-node features; Tripwire does not claim otherwise.

TOTAL: 82 claims checked, 7 wrong, 0 not found, 4 overclaims
