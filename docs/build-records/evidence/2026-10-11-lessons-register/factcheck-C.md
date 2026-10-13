# Fact-check C: FUND-01..07, LN-01..09, SEC-01..06

All records are under /home/junc/rikuri/rikurinode/docs/build-records/. All 37 Port paths and their named tests exist at HEAD (checked with git ls-tree; Rust fns/mod tests confirmed by grep: channeldb.rs files_to_prune / keep_count_from / ChangeWatch / mod tests; proposal_engine.rs owner_hold_reason / runbook_route; cascade.rs; auth.rs mod tests).

## FUND-01
- SUPPORTED: backups reported success while drive copies skipped; "Locations: N" counted the node disk — 2026-09-16-backup-truth-and-alerts.md:37
- NOT FOUND: "/mnt/backup, a path that never existed" — 2026-09-17-self-heal-p2-backup-drive-signals.md:28-30 says `mountpoint -q /mnt/backup` was "always false" because the node's drives were /mnt/storage and /media/junc/BACKUP1; it never says the path did not exist. Correct to: "tested /mnt/backup, which was never one of the node's drives, so the signal was always false and its alert could never fire".
- SUPPORTED: udisks2 mounted the stick under /run/media after the OS upgrade and it vanished — 2026-10-05-usb-backup-run-media.md:115-116
- SUPPORTED: staleness diagnosis read a systemd timer under no name — 2026-08-23-runbook-command-audit.md:71, :94-96
- SUPPORTED: Tripwire "replay of the five-week silent failure" (I1 = five-week backup-config incident) — 2026-09-16-backup-truth-and-alerts.md:17,53,117; 2026-09-16-backup-device-config-store.md:17,97
- SUPPORTED: real lsblk -J fixture (26.04) — lesson 407; Owner quote matches (record :25-29, three separate answers joined by ";").
- SUPPORTED: Port paths and tests exist; verdicts match.

## FUND-02
- SUPPORTED: 186 skipped_no_key, then 450 skipped_no_channels; never succeeded; first channel = first run — 2026-10-02-channel-backup-after-open-close.md:158-165
- SUPPORTED: recovery searched /media/usb{,1}, "was never this node's path" — 2026-10-05-usb-backup-run-media.md:228-229

## FUND-03
- SUPPORTED: plaintext .env archives (RPC passwords, JWT, bot tokens) to USB and SSD; local wallet copies 0644 — 2026-09-16-backup-truth-and-alerts.md:41-50
- SUPPORTED: Owner quote — same record :144-145

## FUND-04
- SUPPORTED: SCB staleness from mtime, permanently stale with zero channels — 2026-09-14-guardian-scb-restart-loop.md:54-58
- SUPPORTED: 96 plaintext channel.db copies on a drive — 2026-09-16-backup-truth-and-alerts.md:163
- SUPPORTED: channel.db backup route stopped LND inside the request; hang-up left LND stopped — 2026-09-28-repairs-outlive-the-request.md:207-208
- SUPPORTED: full channel.db copied only every 6 h; penalty warning; SCB copied within 30 s and mirrored — 2026-10-02-channel-backup-after-open-close.md:17-25
- SUPPORTED: Owner quote — :13-15, :30
- OVERCLAIM (Port caveat, also FUND-06): "this path never once ran with a channel open" — the record says only that "The channel.db backup has never succeeded on this node" (:158). It lists 2 stop_failed and 3 read_failed runs on 2026-06-02, and it does not say how many channels existed then. Correct to: "this path has never succeeded; its first real run is the first channel open".

## FUND-05
- SUPPORTED: hourly and nightly device syncs both wrote backup-config.json at 02:00 with no lock; 12 stray bytes (2026-08-10); five weeks — 2026-09-16-backup-device-config-store.md:34-45, :97
- OVERCLAIM (minor): "made every reader return an empty list" — the record (:36-40) says the device-list reader returned [] and the others returned silent defaults. Suggest "made the drive-selection reader return an empty list".

## FUND-06
- SUPPORTED: ~229 MB each, two folders, nothing deletes — 2026-10-02-channel-backup-after-open-close.md:36-43
- SUPPORTED: Settings promised "Every 15 min / 96 copies", code ran every 6 h — :26-28
- SUPPORTED: Owner "Newest 4 (Recommended)" — :39

## FUND-07
- SUPPORTED: backup rule proposed restarts for a full drive — 2026-09-17-self-heal-p2-backup-drive-signals.md:64, :90
- WRONG: "a cleanup runbook deleted directories while measuring the wrong disk" — record says: "`RB-BACKUP-DEST-CLEANUP-01` deleted `rikuri-backup-*` dirs (none exist) while measuring `df /`" (:40-41). Correct to: "a cleanup runbook targeted `rikuri-backup-*` directories that did not exist while measuring `df /`, the wrong disk".
- SUPPORTED: polkit refused the service's remount — :43-44
- SUPPORTED: stick labelled "not mounted" reported ejected; errors=remount-ro read as read-only — 2026-10-06-eject-outcome-not-from-label.md:15-17, :84
- SUPPORTED: Port caveat "never exercised live" (unmount/remount NOT exercised live) and "space-in-label follow-up" listed as Skipped (:297); I found no later record closing it.

## LN (section intro)
- OVERCLAIM: "The old node never held a funded channel; these are the only lessons about LND and money paths" — mainnet 0 channels is supported (2026-08-22-mempool-page-stale-explorer-and-zero-fees.md:194-195; 2026-10-08-tests-restarted-live-lnd.md:395), but lnd-testnet "holds the sats" (same :195, 2026-10-03-ubuntu-26.04-upgrade.md:21), and FUND-04/05/06, SEC-01 and EXEC lessons also concern LND and money paths. Suggest: "Mainnet LND never held a channel on the old node; LND with testnet funds only. These are the LND- and money-specific lessons."

## LN-01
- SUPPORTED: 14 forced kills since 2026-09-18 (14 of 15 LND exits were 137; reworded to "14 forced kills") — 2026-09-25-lnd-clean-stop.md:14-15, :209-210
- SUPPORTED: Electrs died in 0.1 s (exit 130), hours-long index rebuild — 2026-09-25-electrs-mempool-clean-stop.md:17, :123
- SUPPORTED: `docker stop -t 15` overrode 90 s grace; page said "Safe to disconnect power" while testnet pair and tapd ran — 2026-09-30-node-power-buttons.md:27-33
- SUPPORTED: PID-1 probe LND 10.2 s/137 to 2.2 s/0 — lnd-clean-stop :138, :178
- SUPPORTED: Owner quotes (3) — lnd-clean-stop :47; electrs-mempool :47; power-buttons :54
- NOT FOUND: "on every path (UI, self-heal, cascade, upgrade)" — the records list self-healing, the Rust cascade, `docker compose` and the owner (lnd-clean-stop :16-17). Searched lnd-clean-stop, electrs-mempool-clean-stop, node-power-buttons, lnd-rpccookie for "upgrade": no hit. Replace "upgrade" with "compose".

## LN-02
- WRONG: "the auto-executing memory runbook restarted whichever container was highest at >= 90 % of its limit, LND included" — record says it "restarts whichever container is highest ... That can be LND" (2026-09-26-memory-restart-asks-for-funds.md:14-18) and "so LND was eligible. It did not fire." (2026-09-26-health-exact-container-names.md:114-115). No record says it restarted LND. Correct to: "would restart whichever container was highest at >= 90 %, so LND was eligible (it had not fired)".
- WRONG (wording): "tuned watchtower fees on a node with no tower" — record: the tune step called a non-existent route (/api/lnd/internal/tune-wt-sweep-fee), and the rewrite gated it "on at least one registered watchtower — this node reports {"towers": []}, so it is now a safe no-op instead of a broken one" (2026-08-23-runbook-command-audit.md:58-59, :92-93). Correct to: "had a runbook to tune watchtower sweep fees through a non-existent route, on a node with no registered tower".
- SUPPORTED: invented LND routes — :58-59
- SUPPORTED: Owner quotes — memory-restart :20, :32, :336-337
- SUPPORTED (conditional): Caveat "auto-unlocked LND from a password file" — lnd-start.sh:153-157 and runbook-command-audit :83-84 unlock only when the file exists; not shown that the file existed on the live node. Suggest "unlocks LND from a password file when one exists".

## LN-03
- SUPPORTED: 11 unneeded restarts; block 968341 — 2026-09-24-lnd-sync-stall-misclassified.md:19, :207
- SUPPORTED: starting, wallet-locked LND reported CRITICAL down; control plane terminated it a fourth time — 2026-10-08-tests-restarted-live-lnd.md:34-41, :184
- WRONG: Tripwire "12 of 16 failed on the old code" — record says: "14 tests, **12 failed** on the old code" (lnd-sync-stall :169); the suite grew to 16 later (:194). Correct to: "12 of 14 failed on the old code (the suite later grew to 16)".
- SUPPORTED: Owner quote — :48

## LN-04
- SUPPORTED: LND restarted itself 00:12:42, cascade 00:12:48 (6 s later); 30 s stop timeout vs 90 s grace — 2026-09-26-cascade-skip-restarted.md:17-19, :32-35
- WRONG: "a regtest experiment showed LND 0.21.3 failing with HTTP 401 for 3+ minutes" — record says: "LND kept failing with 401 for 2.5+ minutes" (builder, 2026-09-26-lnd-rpccookie.md:26); "401 for 3+ min" was the verifier's independent re-run (:121). Correct to: "a regtest experiment showed LND 0.21.3 failing with HTTP 401 for 2.5+ minutes (3+ in the verifier's re-run)".
- SUPPORTED: Owner quote — cascade :42
- OVERCLAIM (Port): "the live skip was never observed" — the record says the live skip "is confirmed at the next Bitcoin restart" (:9, :111, still pending). Correct to: "the live skip was not yet observed when the record closed".

## LN-05
- SUPPORTED: single `nc -z tor 9051` probe; LND started without onion at boot, Start All, Restart All's first cascade — 2026-09-30-node-power-buttons.md:380-386
- SUPPORTED: 2 minutes; 10 min no onion = high; two failed SOCKS probes = unreachable, alert-only — :399-404, :423, :566-599
- SUPPORTED: Owner quotes — :399, :549

## LN-06
- SUPPORTED: payment, send, channel open, PSBT broadcast slower than 8 s got "503 request stalled" while continuing — 2026-10-07-money-routes-not-cut-by-watchdog.md:14-19
- SUPPORTED: rebalancing route not exempt (POST /api/rebalancer/check, 503 at 8,004 ms) — :27-29, :127-129
- SUPPORTED: testnet open, close, send answered from read cache (13 of 13 failed) — 2026-10-06-request-values-never-reach-a-shell.md:173-174, :231-232
- SUPPORTED: 30 of 30 mutations red — money-routes :160; exemptions by exact method and path — :26-27, :54-56
- SUPPORTED: Owner quote — health-check-parallel-stats :279; money-routes :23
- SUPPORTED: Superseded caveat — superseded_by field set.

## LN-07
- SUPPORTED: 404 body valid JSON, `.get("fastestFee", 30)`, 30 vs 2.11 sat/vB (about 14x) — 2026-08-23-runbook-command-audit.md:42-50
- SUPPORTED: 0.443 sat/vB rounded to 0, displayed "—" — 2026-08-22-mempool-page-stale-explorer-and-zero-fees.md:20-21, :69
- SUPPORTED: advisor silently used 100,000 — 2026-09-29-btc-price-exchanges-first.md:32
- SUPPORTED: Caveat FALLBACK_BTC_USD = 100_000 still feeds channelAnalyticsService break-even, noted not fixed — :535-538
- Note: the 30 sat/vB figure is what the bump "would have used" (:46); the register's "fell through to a default of 30" is consistent.

## LN-08
- SUPPORTED: gossip address in lncli connect built as shell text; request could set rebalanceLndPath — 2026-10-06-request-values-never-reach-a-shell.md:99, :178-180; tilde/glob regression :101-104

## LN-09
- SUPPORTED: "ALWAYS return to your hardware wallet" in 5 languages — 2026-09-30-dashboard-page-truth.md:347-349
- SUPPORTED: force close pays on-chain wallet after timelock (up to about 2 weeks); needs node or seed plus channel backup — :337-342
- SUPPORTED: Owner quote — :337
- NOT FOUND (Rule): "of a channel opened while it was set" and "peer accepting" — searched the record for opened / accept / upfront: not in the record (it says only "used only by a cooperative close"). It matches the protocol but is not from the record.
- NOT FOUND (Rule): "the assistant can answer this correctly" — the record covers route replies and the route warning (:350-353), not the assistant.

## SEC-01
- SUPPORTED: LND command line carried `--bitcoind.rpcpass=<cookie>`, readable by `ps` — 2026-09-25-lnd-clean-stop.md:216; 2026-09-26-lnd-rpccookie.md (lesson 186)
- SUPPORTED: owner token in a world-readable drop-in; gates approvals, chantools, channel.db restore — 2026-09-16-rust-alert-delivery-and-owner-token.md:25, :44-45
- SUPPORTED: testnet RPC credentials in execution-history API and chat answers — 2026-10-08-assistant-execution-paths.md:227-229
- SUPPORTED: Owner quote "4. yes" (2026-09-26) — lnd-rpccookie

## SEC-02
- WRONG: "twice a session printed LND's Tor control password" — both cited records describe the same incident. 2026-10-02-tor-control-password-rotation.md:13-17: "Incident (2026-10-02, power-buttons record): ... a command of mine (`grep … /root/.lnd/lnd.conf` inside the lnd container) printed `tor.password=<value>`", pointing to 2026-09-30-node-power-buttons.md:530-533. Correct to: "a session printed LND's Tor control password while reading lnd.conf for ordinary settings (2026-09-30-node-power-buttons.md, rotated in 2026-10-02-tor-control-password-rotation.md)".
- SUPPORTED: owner token printed because redaction missed quoted form — owner-token record :63-64
- SUPPORTED: Owner quote — tor-control-password-rotation :22

## SEC-03
- SUPPORTED: Tor control password in three files, torrc.base single-file bind mount — 2026-10-02-tor-control-password-rotation.md:31-35
- SUPPORTED: 12 scripts and engine switch edit root .env non-atomically, unanchored — 2026-10-10-upgrades-survive-code-updates.md:128-130
- SUPPORTED: tripwire "planned, not built" (P2 tests parked); end-to-end check of all onions — :126-128; rotation :42, :91

## SEC-04
- SUPPORTED: logged every start since at least 2026-08-08; legitimate 2026-07-21 model upgrade; log only — 2026-10-04-config-tamper-notifies-owner.md:13-19, :276
- SUPPORTED: v1 → v2 → v1 → v2 must notify; mutant "store = manifest" caught — :105, :248
- SUPPORTED: Owner quote — :23

## SEC-05
- SUPPORTED: control plane accepted a token with no iss — 2026-09-28-runtime-alerts-round-two.md:77 (lesson 216)
- SUPPORTED: nodemailer 9 → 10 described as "Node 20 or newer", actually a full rewrite — 2026-09-28-runtime-dependency-vulnerabilities.md:111-115
- SUPPORTED: Owner quote — alerts-round-two :26-29

## SEC-06
- SUPPORTED: printed "dep-audit clean", exit 0 with cargo off PATH; read only RustSec — 2026-09-28-dep-audit-sees-what-github-sees.md:201-202, :24-25
- SUPPORTED: 315 alerts, 14 lockfiles, two lockfiles read by nothing, none of 3 criticals in running code — 2026-09-28-runtime-dependency-vulnerabilities.md:13-34, :166
- SUPPORTED: 13 of 15 red on old script; run on every push — dep-audit :229, :276, :79
- SUPPORTED: Owner quote — :40

TOTAL: ~112 claims checked, 6 wrong, 5 not found, 5 overclaims
