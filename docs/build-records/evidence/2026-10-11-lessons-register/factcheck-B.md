# Fact-check B: HEAL-01..HEAL-10, UPG-01..UPG-12

All Port paths exist at HEAD of the old repo (ls-tree): every file listed in the 22 requirements. Named symbols confirmed: `run_to_completion` (http_server.rs:1227), `mod repair_lifetime_tests` (:1776), electrs_phase.rs `mod tests` (:448), executor.rs has tests. Port verdict wording is consistent with the lessons' port_candidate fields (those fields hold only paths).

## HEAL-01
- SUPPORTED: induced `docker stop mempool-web`; synthesizer rewrote target to mempool-api, runbook restarted healthy container; triggerAIAutoFix restarted real one "no tier check, no runbook, no decision row" — 2026-09-18-self-heal-p3-incident-record.md:38-42
- SUPPORTED: control plane monitor wrote findings only to `decisions`; never became incidents; its own repairs invisible — 2026-09-18-guardian-page-and-rust-detectors.md:30-35
- SUPPORTED: unknown issue type = loud 400; TS test reads Rust constants and fails on unknown; route authenticated — guardian-page:46-54, :113
- SUPPORTED: Owner quote "Ok replace AI Fixes and Rust-side detectors write incidents" — guardian-page:13-14 (exact)
- SUPPORTED: Tripwire drill: one incident, right container (`mempool-web:CONTAINER_DOWN`), restarted mempool-web, left mempool-api alone — p3-incident-record:93-95

## HEAL-02
- SUPPORTED: "completed" 71x (validation could never pass) and 4x (every command failed) — 2026-09-17-self-heal-p2-honest-executor.md:34-37
- SUPPORTED: `compose up` without profile matched nothing, exit 0 — 2026-08-22-rollback-consolidation.md:60-61
- SUPPORTED: USB remount runbook SUCCESS while dashboard/backup engine could not see the drive — 2026-10-05-usb-backup-run-media.md:183-186, :490-491
- SUPPORTED: prune row "executed" when Docker refused — guardian-page:86-87; clock-derived id collision :133-134
- SUPPORTED: mutation tests back to old behaviour, each red — honest-executor:113-118
- NOTE (not counted): Tripwire "the remount validation queries the backup engine's own view of the drive" is a prescription; the usb-backup record contains no such validation step (grep "validat" found nothing). Fine as a new-node tripwire, but must not be read as something the old repo had.

## HEAL-03
- SUPPORTED: tapd start runbook 783 PARTIAL since 2026-07-11, 48 last 24h; limit was within one call — 2026-09-16-drb-attempt-budget-and-escalation.md:35, :44-48
- SUPPORTED: ~200 dashboard-restart firings left no rows because remedy killed recorder — drb-attempt-budget:58-64
- SUPPORTED: ~339 failed proposals in 24 h (678 lines) — 2026-09-16-owner-notification-delivery.md:49-51
- WRONG: Owner quote “Budget spent: skip that hypothesis and continue down the ladder (escalate only when all are spent), with a 24-hour rolling window.” — record says: "**budget spent → skip that hypothesis and continue down the ladder** (escalate only when all are spent), and a **24-hour rolling window**." (drb-attempt-budget:66-68) — correct to: “budget spent → skip that hypothesis and continue down the ladder (escalate only when all are spent), and a 24-hour rolling window.”
- WRONG (quoted test names): record test names are "a hypothesis over budget is skipped, not executed" (exact), "exhausted pages the owner with the DRB rollback message", "records the attempt BEFORE running the runbook" (drb-attempt-budget:140-142). Register quotes "the attempt is recorded before the runbook runs" and "exhausted pages the owner" — correct to the real names or drop the quote marks.
- SUPPORTED: those tests proven red on pre-fix code — :137-143 (4 guard tests)

## HEAL-04
- SUPPORTED: `required_any` never read, `[].every` vacuous, DRB-BACKUP-STALE-01 restarted live dashboard every 30 min, 156 restarts on 2026-09-14 — 2026-09-14-guardian-scb-restart-loop.md:43-47, :98-100; drb-schema-gate:24-27
- WRONG (imprecise): "14 of 89 runbooks targeted invented routes or sent LND REST calls to the local model server's port" — record: "What was actually broken — 14 of 89 runbooks" (2026-08-23-runbook-command-audit.md:37), and the 14 also include unsupplied template variables (`{{container}}`, `{{repo_root}}`) and a nonexistent `rikuri-backup-*` unit (:44-49, :62-72). Correct to: "14 of 89 runbooks were broken (invented or wrong routes, LND REST calls sent to the local model server's port, unsupplied template variables, nonexistent units)".
- SUPPORTED: bare `sweep-fee-rate=` written then LND restarted — honest-executor:41-42
- SUPPORTED: five runbook ids existed nowhere — 2026-08-10-crashloop-detection.md:33, :71-73
- WRONG (quote): Owner “The owner chose to fix the violations rather than baseline them; deleting DRB-NETWORK-OFFLINE-01 was owner-approved.” is narration, not the owner's words. drb-schema-gate:33-34 "once the owner chose to fix the violations rather than baseline them" and :118 "`DRB-NETWORK-OFFLINE-01` **deleted** (owner-approved)". Remove the quote marks or write: Owner chose to fix the violations rather than baseline them (record narration).
- SUPPORTED: Tripwire negative controls / misspelt field `required_anyy` and invented signal — drb-schema-gate:137-142; runbook-command-audit:134-135
- NOTE: Tripwire "a registry test that every issue type has a producer and every signal a consumer" was a follow-up in the old repo (2026-10-03-electrs-0.12-support.md: "left as a follow-up"); acceptable as a prescription only.

## HEAL-05
- SUPPORTED: "electrs stopped" scored as index problem, destructive-reindex approval (I6); +3 for service name; 26-row table — 2026-09-17-self-heal-p2-probes-and-selection.md:36-37, :70
- SUPPORTED: reindex runbook hard-coded `electrs-data:/data`, would restart Electrs on corrupt live index; case-sensitive grep; 3-case runbook test — 2026-10-05-electrs-0.11-index-removed.md:26-31, :46
- SUPPORTED: three DRBs restart whole dashboard; clock-drift 332 attempts, 0 successes, will page P0 — drb-schema-gate:193, :210-221
- SUPPORTED: restart baseline = uptime >= 60 s not RestartCount — electrs-0.11-index-removed:52-53

## HEAL-06
- SUPPORTED: one tapd problem every 30 min shown as "100 incidents, 99 unresolved" beside 94/100 — 2026-09-18-self-heal-p3-incident-record.md:30-33
- SUPPORTED: `docker stop` exits 0 so no report (control plane gated on exit_code != 0); +20 s open, closes on start event — guardian-page:64, :113-123
- WRONG (imprecise): "an LND incident could never close because its closing state lived in memory lost on restart" — record says it "never closes, because nothing reports 'syncing → synced' as a recovery" (2026-09-24-lnd-sync-stall-misclassified.md:21-22); the in-memory/restart orphan point is a secondary fix ("Incidents orphaned by a restart: settleAbsent closes only what the loop's in-memory state holds", :187-190). Correct to: "an LND incident never closed because nothing reported syncing-to-synced as a recovery, and incidents orphaned by a restart were not seen by the in-memory loop".
- SUPPORTED: Owner quote — guardian-page:13-14
- SUPPORTED: resolved state frozen; fix recorded up front; 4 s late write, 35 s late — p3-incident-record:97-101

## HEAL-07
- SUPPORTED: every approval 403 since ~2026-07; 730 of 741 never resolved; any chat member could approve; seven other stores — 2026-09-17-self-heal-p3-approvals.md:27-35, :40-42, :112
- NOT FOUND: "nothing alarmed" — searched approvals record for alarm, alert, silent; the record states the 403 cause and counts but not that nothing alarmed (only the lesson's root_cause says so). Keep as inference or delete.
- SUPPORTED: held LND restart text "Risk level: low" / "safe, reversible" — 2026-09-26-memory-restart-asks-for-funds.md:104-105, :251
- SUPPORTED: `.on(...)` on module not instance; "Approval notifications not available" fires every start — 2026-10-04-config-tamper-notifies-owner.md:153-157 (record says surfaced to the owner, NOT fixed there; Rule is a prescription so fine)

## HEAL-08
- SUPPORTED: onion repair cut at exactly 2:00, handler with kill_on_drop, no decision row — 2026-09-28-repairs-outlive-the-request.md:77-92
- WRONG: "killed at exactly 2:00 on two days, after it had already restarted Tor" — record: cut off on 09-24 and 09-28, and "on 09-24 the script had already restarted Tor (18:49:23) before it was killed" (:78-80, :90-91). Correct to: "...on two days (2026-09-24, 2026-09-28); on 2026-09-24 it had already restarted Tor".
- SUPPORTED: dashboard logged "Control plane unreachable" while repair still running — :80, :93-96
- NOTE (formatting): Owner line shows `“"Let's fix the tor onion." (2026-09-28)”`; the date is the record's, outside the quote (:27 'Owner approved the intent: 2026-09-28, "Let's fix the tor onion."'). Move the date out of the quote.
- SUPPORTED: Port note "a bypass mutation survived" — :212, :220

## HEAL-09
- SUPPORTED: 401 x16 in 72 h from the node's own auth gate; 404 swallowed; TypeError swallowed at debug — 2026-09-16-owner-notification-delivery.md:34-42
- SUPPORTED: daily digest logged "sent", routed to bell, 0 clients — 2026-10-02-guardian-summaries-reach-the-owner.md:21-25
- SUPPORTED: constitution.rs logged "Tampering notification sent" for any response incl. 401 — 2026-09-16-rust-alert-delivery-and-owner-token.md:53-54 (register says "service senders", plural; record shows one confirmed logger plus others ignoring status: fine)
- SUPPORTED: "notified" store written before sending; mutants "mark before send" and `>= 0` caught — config-tamper-notifies-owner:34, :161, :176
- SUPPORTED: Owner quote — guardian-summaries:12-15 (quote is a verbatim prefix; record continues "Restart All health services..." in the same sentence group)

## HEAL-10
- SUPPORTED: Owner quote "nothing should fail silently or be in a crash loop" — 2026-08-10-crashloop-detection.md:13-14
- NOT FOUND: "restarted 305 times over about 9 hours with zero notifications" in the cited record — 2026-08-10-crashloop-detection.md says only "305 silent restarts" (:13). The "~9 hours, zero notifications" wording is at 2026-08-10-bip110-invalid-mark-leak.md:88. Add that record as the citation.
- WRONG (overstated): "destroyed the only evidence" — record: "destroyed the wedged state before its stack could be captured" (2026-08-22-mempool-page-stale-explorer-and-zero-fees.md:100-101). Correct to: "destroyed the wedged state before its stack could be captured".
- OVERCLAIM (Tripwire): "it was proven live on 2026-08-16, notifying the owner within about 2 h" — the source is a different, uncited record (2026-08-16-mempool-oom-recurrence.md:33-35: "the owner was NOTIFIED by the restart-loop detector ... and reported it within ~2h"). That was an organic recurrence, not a drill: the 08-10 record says the live notification path was untested and a live drill was deferred to the monthly rotation (crashloop-detection:64-67). Reword: "observed working in a real recurrence on 2026-08-16 (the owner was notified and reported it within about 2 h); no deliberate live drill was done", and cite 2026-08-16-mempool-oom-recurrence.md.
- SUPPORTED: 8 cases, injected clock — crashloop-detection:47-49, :75

## UPG-01
- SUPPORTED: Electrs 0.12.0 "Upgrade complete" two seconds after start, `--help` pre-flight, unknown argument, RestartCount 363, rolled back by hand — 2026-10-03-upgrades-cannot-break-a-service.md:16-24 (13:08:03 to 14:49 = about 1 h 41 min; also 2026-09-30-dashboard-page-truth.md:1037)
- OVERCLAIM (Why): "rollback for four services was only code-reviewed, never fired" — record: "Rollback was NOT live-fired for the four new services (only code-reviewed + pattern-shared with the proven bitcoin path)" (2026-08-08-one-click-infra-upgrades.md:74-75). Say "not live-fired at that time"; "never" is not claimed.
- WRONG (quote form): Owner “Roll back. Then close the three gaps. / Yes, roll back + tell me” is two separate quotes from different places (upgrades-cannot-break:39 and :53-54) joined by " / ". Present as two quotes.
- SUPPORTED: maintenance 15 min TTL, exit in finally; watch start_period + interval x retries + 60 s — :489-495
- SUPPORTED: settings check refuses failing release with exact crash line; watch drilled on crash-looping scratch container — :83, :248, :304, :419

## UPG-02
- SUPPORTED: second rollback path never once succeeded; uninstalled docker-compose v1; rotted image map — 2026-08-22-rollback-consolidation.md:23, :32-36, :54-56
- SUPPORTED: bumping mempool-web recreated bitcoin, electrs, tor, lnd (also mempool-api/db, redis); LND no network, restart loop, reconnected by hand — 2026-08-22-mempool-page-stale-explorer-and-zero-fees.md:173-195
- NOTE: Owner “Owner chose: consolidate, not repair-in-place.” — record: "(owner chose: consolidate, not repair-in-place)" (rollback-consolidation:68), lowercase "owner"; trivial.
- NOTE: Rule "untouched containers kept their IDs" and Tripwire "container-ID check" are not from the old repo (it had a network/DNS tell, :206-207); prescriptive only.

## UPG-03
- SUPPORTED: Revert re-pinned tag from running (new) container, cleared the failure; picked OLDEST snapshot (11 lines different) — 2026-10-03-electrs-0.12-support.md:207-212, :328-329
- SUPPORTED: failed-upgrade rollback not run live because a failing hold would really upgrade mainnet — electrs-0.12-support:376-388; upgrades-cannot-break
- SUPPORTED: 63.92 GB index deleted while older snapshots still declare it — 2026-10-05-electrs-0.11-index-removed.md:69, :102-105
- SUPPORTED: Owner "1. Delete the old index." — :13

## UPG-04
- SUPPORTED: consensus guard UI-only; Retry, /execute, Telegram button had no hold check — upgrades-cannot-break:107-111, :196
- SUPPORTED: MariaDB 10.11.19 (7 CVEs) never offered; only newest (13.0.2 held) considered — 2026-10-03-inline-patch-beside-held-line.md:13-18
- SUPPORTED: "any older line is supported" let a Core-29 tag pass on a Core-31 node — electrs-0.12-support:165-168
- WRONG (quote form): Owner “Supported release lines / Hold it, show why” merges two answers to two different questions (upgrades-cannot-break:57 and :52); present as two quotes.
- WRONG (truncated quote): Owner “3. We should have a auto rollback. ... Electrs 0.12” stops mid-sentence; the verbatim text continues "Electrs 0.12 Then when rikurinode 1.5 is ready ..." (2026-10-03-upgrade-gates-round-2.md:16-23). Add an ellipsis.
- SUPPORTED: Owner "Do both now." — inline-patch:18; Port paths/tests exist.

## UPG-05
- SUPPORTED: "rce" matched inside force/source/resource; 34 of 107 flagged; LND 0.21.2/.3/.4 sent as CRITICAL with Upgrade Now, skipping 14-day wait; would install on day one — 2026-10-03-upgrade-gates-round-2.md:36-45
- OVERCLAIM (Why): "any 'Breaking Changes' section held LND patches that did not affect the node" — record says LND 0.21.3 to 0.21.4 "WOULD have been held" (upgrades-cannot-break:242-243, :357); no patch was actually held. Correct to "would have held".
- SUPPORTED: Tripwire after fix 19 flagged, all Redis security-urgency, 0 LND/Bitcoin — round-2:108-112
- SUPPORTED: Owners "Yes, count them" (:106), "Auto-install, only if all gates pass" (:25), "1. relax it" (:16), waiting-period quote (upgrades-cannot-break:61-68, verbatim prefix; record continues "So we need to apply the same process ..."), "when the release notes show…, hold" (:130)
- SUPPORTED: Superseded caveat — owner relaxed R9 in round 2 (round-2:54, owner answer 1)

## UPG-06
- SUPPORTED: pinned Knots rejected mainnet block 961,642 and followed BIP-110 fork; `consensusrules=rdts` set nowhere — 2026-09-20-knots-repin-and-gate.md:62-64, :248
- SUPPORTED: Upgrades page offered Knots 29.4.20260508 as "minor", readyToUpgrade true, one click would rewrite pin and restart bitcoind — 2026-09-20-consensus-upgrade-guard.md:23-27
- SUPPORTED: frozen pin lacked Core 29.4 chainstate fix (SSD wear) — 2026-09-22-knots-pin-review.md:51-56
- SUPPORTED: <= 92 days; re-pinning without re-reviewing fails CI; "could not check" is unknown — knots-pin-review:137-140; tests red on old pin knots-repin:38

## UPG-07
- SUPPORTED: mempool-web v3.2.1 vs api v3.3.1 about three and a half months; floors sub-1 sat/vB fees — mempool-page-stale-explorer:158-168, :240
- SUPPORTED: legacy overlays pinned LND v0.18.0-beta; later -f wins; three-major downgrade — rollback-consolidation:46-51
- SUPPORTED: chroma API reported "1.0.0" forever — 2026-08-08-one-click-infra-upgrades.md:49
- SUPPORTED: hourly drift check informs owner; CI test every image registered — mempool-page-stale-explorer:252-258
- NOTE: Port composeControl.ts entry comes from lesson 24 (UPG-02), not from UPG-07's lessons (1, 21, 25); path/tests exist.

## UPG-08
- SUPPORTED: in-app upgrade writes pin into tracked compose; `git pull --rebase` refuses, exit 128 (scratch clone); or stash + `git reset --hard` returns old pin; next `compose up` downgrades — 2026-10-10-upgrades-survive-code-updates.md:44-51
- SUPPORTED: separate pins file rejected, about 46 call sites — :83-87
- SUPPORTED: Tripwire "planned but not built": Status Parked, "Nothing was changed in code; no test, gate or verifier ran" — :9, :206
- WRONG (quote form): Owner line is wrapped in one pair of quotes, but only 'No other node exists now. So it's OK.' (:104) and 'Yes, you can park it' (:191) are verbatim; "C1: (a), the newer one runs (the node's pin is dropped once the default reaches or passes it)" is the record's paraphrase of option (a) (:99-102; the owner answered "(a)"). Quote only the verbatim parts.
- SUPPORTED: Caveat — C3 open, recommended (a) pin-only upgrades — :110-122

## UPG-09
- SUPPORTED: lnd-start.sh edited in place, same inode, shifted bytes under PID 1, restored before harm — 2026-09-25-lesson-gates.md:18-21
- SUPPORTED: dist contained another session's uncommitted DRB schema-gate code — 2026-09-26-exact-container-target.md:214-216
- SUPPORTED: control plane build 10:08Z predated 10:15Z refactor and went live — 2026-09-26-memory-restart-asks-for-funds.md:244-248
- WRONG: "a release-mode test run overwrote production binaries" — record: `cargo test --release --workspace` "replaces the target/release binaries with test-feature builds; the deploy steps (and install-node-watchdog.sh) should rebuild ... immediately before installing" and "production binaries rebuilt last, before any install" (2026-09-28-runtime-alerts-round-two.md:231-233, :256-259). They were build-directory binaries, caught before install. Correct to: "a release-mode test run replaced the target/release binaries with test-feature builds that the deploy steps would then have installed".
- SUPPORTED: Owner "ok with 2 rules" — lesson-gates:38 (record: 'ok with 2 rules' lowercase, as quoted)
- SUPPORTED (Rule/Tripwire): `cmp /proc/<pid>/exe` and atomic rename — 2026-09-30-reliability-uptime-truth.md (lesson 306); memory-restart:262

## UPG-10
- SUPPORTED: old control-plane binary loaded runbook JSON with new hold_for_owner, held v2.0 without the hold 18:47Z to 21:22Z (harmless) — memory-restart-asks-for-funds:265-270
- WRONG (imprecise): "a migration would have re-applied to every later patch" — record: `migrationFor` keyed on target line only, so 0.12.1 "would get the 0.12 migration, and its exact text cannot match the migrated compose", i.e. every 0.12.x patch would be refused (electrs-0.12-support:332-334). Correct to: "would have been attempted on every later patch and refused".
- SUPPORTED: migration test used live compose file, suite red after real upgrade — :335-336, :376-378

## UPG-11
- SUPPORTED: Electrs 0.12 exhausted ephemeral ports in 13 s (os error 99) — electrs-0.12-support:55-58
- SUPPORTED: dropped `electrs_index_height` metric used by three readers (Health, guardian signal, control plane phase) — lesson 348 / electrs-0.12-support (R8)
- SUPPORTED: ChromaDB 1.x persisted at /data, 0.x path mounted, wiped each recreate, masked by re-ingest — one-click-infra-upgrades:45-47
- SUPPORTED: replay 20/20 then 19/20, sets 20/20; prebuild capped 4 GB live; consumer replay only in scratchpad — electrs-0.12-support:133-142, :88-91
- SUPPORTED: Owner quote — electrs-0.12-support:73-75 (verbatim)

## UPG-12
- SUPPORTED: "17/17 packages still pending" while apt succeeding; oneshot `activating` — 2026-08-19-os-update-false-fail.md:12-13, :25
- SUPPORTED: node looked dead ~9 min; first progress view all-green for failed update; failed restore after failed install showed green; "Failed" for up to 90 s — 2026-10-09-upgrade-deadlock-and-progress.md:36, :221-222, :282-285, :358
- WRONG (not a quote): Owner “Owner spec (paraphrased in the record): a live progress view until a VERIFIED end state.” — the record says only "give the owner a live progress view until a VERIFIED end state (owner spec)" (os-update-false-fail:13-14). Present as narration, not a quotation.
- SUPPORTED: Owner 2 verbatim — upgrade-deadlock-and-progress:17-18

TOTAL: 112 claims checked, 14 wrong, 2 not found, 3 overclaims
