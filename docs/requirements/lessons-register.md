# Lessons register — what the previous rikurinode taught

**Source.** All 114 build records of the previous repository, rikurinode (`docs/build-records/`, 2026-08-08 to 2026-10-10), harvested into 475 lessons. By evidence: **118 live incidents**, **290 found by verification**, **32 design decisions** and **35 owner decisions**. 130 lessons carry an owner decision (122 distinct), 131 name a file worth porting, and 11 were later superseded.

**Method.** Six readers each took a share of the records and wrote one lesson per defect class per record (what happened, root cause, lesson, tripwire, evidence, owner decision, port candidate). Here, lessons of the same class are merged into one requirement for the new node; every lesson feeds exactly one requirement, and the Coverage table at the end shows which requirements each record fed, so nothing is lost.

**Fact-check (2026-10-11).** Six more readers checked the register against the records themselves: about 830 claims, of which 44 were wrong (a figure, a quotation or an event misstated), 13 could not be found in the record cited, and 32 claimed more than the record shows (often a test or check the old repository planned but never built, now marked "owed"). All are corrected here. Then verifiers read every quotation of the owner against its record. A script kept with the build record re-checks parts of this mechanically, to catch an accidental change: the requirement-to-lesson mapping, the per-theme counts and the Coverage table, the cited records, section 3 against the harvest, the paths in section 4's table (outside its bracketed notes) and the main path of each Port line, and quotations in Owner lines against their records. It is not a proof: it cannot tell whose words a quotation is, it does not check everything (the build record says what it misses), and Markdown written to fool it can get past it. The reports and the script are kept with this register's build record.

**How to use it.** Every requirement below becomes a requirement or a test in the new node's plan, or gets an explicit, owner-approved "not applicable" with its reason. Nothing here is proven for the new node: each rule names the tripwire that must exist and be seen to fail before it counts.

**Reading a requirement.** *Rule* is the testable requirement. *Why* names the incidents behind it with their records (at most four cited; "+N more" counts the other records that fed it, listed under Coverage). *Tripwire* is the test, check or monitor that stops the class recurring. *Owner* gives the owner's decision from the harvest, with its record; quotation marks mean the record quotes the owner's own words. *Port* names old code worth carrying over with its tests, and the verdict. The new node is a clean rebuild — Fedora IoT on an Intel N150 full node, and a Raspberry Pi 5 pruned node once Fedora supports it; image updates with automatic rollback; containers under systemd; a sandboxed planning-only assistant (the platform plan, `docs/architecture/platform-plan.md`, a change of its own) — so a port means carrying the behaviour and its test cases across, rewritten if the language or platform changes.

## Contents

| Theme | Requirements | Lessons |
|---|---|---|
| [EVID — Evidence and truth of status](#evid) | 10 (EVID-01 to EVID-10) | 57 |
| [IDEN — Exact identity of targets](#iden) | 3 (IDEN-01 to IDEN-03) | 15 |
| [OWN — One owner per action and one bring-up path](#own) | 9 (OWN-01 to OWN-09) | 33 |
| [HEAL — Self-healing, runbooks, incidents, alerts and approvals](#heal) | 10 (HEAL-01 to HEAL-10) | 49 |
| [UPG — Upgrades, rollback, deploys and machine state](#upg) | 12 (UPG-01 to UPG-12) | 51 |
| [FUND — Backup, restore and funds safety](#fund) | 7 (FUND-01 to FUND-07) | 19 |
| [LN — Lightning operations](#ln) | 9 (LN-01 to LN-09) | 25 |
| [EXEC — Untrusted input, execution and access control](#exec) | 8 (EXEC-01 to EXEC-08) | 33 |
| [SEC — Secrets and credentials](#sec) | 6 (SEC-01 to SEC-06) | 16 |
| [AI — The assistant and its knowledge layer](#ai) | 10 (AI-01 to AI-10) | 41 |
| [TEST — Testing, verification and development discipline](#test) | 12 (TEST-01 to TEST-12) | 89 |
| [PLAT — Platform specifics: Fedora IoT, Raspberry Pi 5, bitcoind, Tor and containers](#plat) | 11 (PLAT-01 to PLAT-11) | 47 |
| **Total** | **107** | **475** |

Sections after the requirements: [3. Owner decisions](#3-owner-decisions) · [4. Port candidates](#4-port-candidates) · [5. Gaps](#5-gaps--where-the-old-repository-has-no-evidence) · [6. Coverage](#6-coverage) · [7. The commerce service](#7-the-commerce-service-a-module-level-harvest-2026-10-17)

## 2. Requirements

<a id="evid"></a>
### EVID — Evidence and truth of status

*What the node reports — on its pages, in its health score, in alerts and to the assistant — must be measured, current and honest about what it does not know.*

#### EVID-01 — Health means function, not liveness

- **Rule:** Every service check judges the service's own functional state (its chain tip against bitcoind's, Tor bootstrapped with its SOCKS port open, the control plane answering status "OK", every expected container present); a running container, an open port, a name match or an HTTP 200 never counts as working, and stale-but-alive raises its own alert, distinct from down.
- **Why:** mempool-api stayed "Up (healthy)" while serving a frozen snapshot 120 blocks / 20.6 h behind bitcoind, with no error, exception or restart (2026-08-22-mempool-page-stale-explorer-and-zero-fees.md). Electrs read "Synced 100%" whenever its port was open and a BLOCKED control plane passed because its body contained "status" (2026-09-30-dashboard-measurements.md); service cards said "Operational" whenever the container ran (2026-09-30-dashboard-page-truth.md); an absent mempool-api read healthy (2026-09-26-health-exact-container-names.md).
- **Tripwire:** Pure per-service judge functions, tested red first, for: stale tip, frozen-but-answering backend, missing container, BLOCKED body, Tor still bootstrapping. Health enumerates the expected stack per node (electrs on the x86 node only) and reports a missing member as down.
- **Port:**
  - `dashboard/backend/src/tests/mempoolStalenessAndFees.test.ts` — Port with tests.
  - `dashboard/backend/src/services/serviceProbes.ts` (tests: dashboard/backend/src/tests/serviceProbes.test.ts) — Port with tests: add unit tests for the async probe runners (missing in the old repository).

#### EVID-02 — Unknown stays unknown

- **Rule:** A figure or state that could not be read is carried as an explicit null ("unknown") from probe to API, UI, alerts and assistant; it is never 0, 100 %, healthy, down or all-clear, never feeds an alert or a baseline, never triggers restart advice or self-healing, and an error branch answers with an error, not a plausible default.
- **Why:** unreadable drives raised "Disk space low: 0 GB" and an unreadable CPU became the Guardian's baseline of 0 (2026-09-30-dashboard-measurements.md); `|| 0` turned unknown peers and channels into 0 while `|| '—'` hid a real 0, and the assistant's tools called "could not read" (a non-2xx answer or a loading bitcoind) down and advised `docker restart` (2026-09-30-dashboard-page-truth.md); the uptime API answered `uptime_pct: 100` for a component never measured (2026-09-30-reliability-uptime-truth.md); a knowledge loader reported "0 services, 0 commands" from files that never existed (2026-08-23-runbook-command-audit.md) (+1 more).
- **Tripwire:** A four-state status model (healthy / degraded / down / unknown) with per-figure tests using null fixtures and real zeros; mutations that re-introduce `|| 0` or `?? 100` must fail; a ratchet on falsy coalescing in display code; a check that could not run never reads as all-clear.
- **Port:** `dashboard/frontend/src/utils/topCards.ts`, `dashboard/frontend/src/utils/resources.ts` and `dashboard/frontend/src/utils/serviceCard.ts` (tests: dashboard/frontend/tests/pageRound4.test.tsx; dashboard/frontend/tests/pageRound4Fixes.test.tsx; dashboard/frontend/tests/pageRound6.test.tsx) — Port after re-check: the frontend is rebuilt; port the cases as the specification.

#### EVID-03 — Every displayed figure is measured and bound to a real field

- **Rule:** Every number or label shown to the owner is bound to a field the producing API actually returns (checked by a contract test built from the producer's real response), uses shared types and the backend's own status label, shows the server-confirmed state after any save (with the error if the save failed), and is never an estimate or guess unless labelled as an estimate with its method.
- **Why:** the Dashboard's mempool count read a field the API never sends and showed "— txs" while the mempool held 66,164 transactions, and the sync "ETA" was the remaining fraction × 48 hours (2026-09-30-dashboard-page-truth.md); an API shape change made the infra bar show all four services down (2026-09-30-dashboard-measurements.md); the auto-install switch showed a state the server had refused (2026-10-03-upgrade-gates-round-2.md).
- **Tripwire:** Page render tests with every data hook mocked in the producer's real response shapes; a test fails when a displayed field is always absent; save-failure tests; review rule that every displayed figure names its source field.
- **Owner:** “Yes, in fact, check all measurement on the Dashboard. Make sure every one of them is actually meansuring the right thing and is correctly measuring what it's suppose to.” — 2026-09-30-dashboard-page-truth.md

#### EVID-04 — Status shown is the running truth, with its age

- **Rule:** "In use", "running" and "current" come from the running process (its RPC report, or its start time against the config's last write), read fresh from the authoritative source on every call, never from a cached default; every success claim carries its timestamp and expires while failures never fade; a stale value is shown as stale, and "not yet measured" ("Checking…") is a distinct state.
- **Why:** the relay panel said Strict was "in use" while bitcoind, which reads its config only at start, still ran Standard (2026-09-23-posture-restart-to-apply.md); a pin watcher read "Core" from an uninitialised singleton on a Knots node and would have closed its own incidents (2026-09-22-knots-pin-review.md); "Last update completed successfully" was permanent and undated (2026-09-02-os-update-banner-staleness.md); the Services card showed a 13-hour-old "1/8" as current (2026-10-09-health-score-never-freezes.md).
- **Tripwire:** "A saved setting the node has not loaded is not in use" render test; banner TTL tests (mutation TTL = Infinity fails) including that a display TTL never reaches alert suppression; real-page tests for stale vs "Checking…"; every feature run once for real, not only with injected dependencies.
- **Owner:**
  - “let the restart button surface only after I click the switch from standard to strict (may be popup with authentication), then disappear after implementation.” — 2026-09-23-posture-restart-to-apply.md
  - “Restart dashboard + fix (Recommended)” — 2026-10-09-health-score-never-freezes.md
- **Port:** `dashboard/backend/src/utils/upgradeStateCheck.ts` (tests: dashboard/backend/src/tests/upgradeRebootBringup.test.ts; dashboard/backend/src/tests/upgradeDoneBanner.test.ts) — Port with tests.

#### EVID-05 — External data carries source, age and staleness

- **Rule:** Every externally sourced value carries its source, the source's own timestamp, its age and a stale flag; it is "live" only within a stated limit and is then kept and marked stale (never deleted); a failed, empty or malformed fetch is never stored with a fresh timestamp; a partial aggregate is labelled partial; a per-period delta is computed only against the previous period; each source has its own backoff; figures the node can derive from its own chain are computed locally; third-party calls go through the node, never from the owner's browser.
- **Why:** the owner saw a price of 84,346 while exchanges showed ~83,2xx: the only source had refused the node for ~10 h and its cache was served as `live: true` (2026-09-29-btc-price-exchanges-first.md); refreshers deleted rows after 3× their TTL so cards read "No data yet", and a not-yet-reported upstream row counted as 0 (2026-09-29-market-intel-freshness-arkb.md); a "24h volume" silently omitted Coinbase, ~58 % of the three-venue total (2026-09-29-market-cap-volume-etf-warm.md).
- **Tripwire:** Per-feed success/failure bookkeeping with forced-stale drills; partial-aggregate label tests; backoff test (doubling, honours Retry-After); a browser network log showing no third-party calls (owed: the old log proved it only for CoinGecko; Fear & Greed and the chart fallback still went from the browser to third parties); input dates validated (real calendar day, not in the future).
- **Owner:**
  - “rikurinode's Bitcoin price on Bitcoin section is wrong (showing 84,346, instead of 83,260). Are we not connected to the source or is the source compromised?” Chosen: “Exchanges first (Recommended)” — Kraken, then Coinbase, then the node's own mempool — 2026-09-29-btc-price-exchanges-first.md
  - “Market cap and 24h volume: CoinGeko doesn't seem reliable. It goes down sometimes, same thing happens for CoinGeko app on its smartphone app. Any alternative?” Chosen: “Computed on the node (Recommended)” for market cap and “Regulated exchanges only” for 24h volume — 2026-09-29-market-cap-volume-etf-warm.md
  - “Do we need fallback for other existing Market Intelligence? Can we know if data can't be updated or go stale?” Chosen: “Stale data: page + Guardian alert (Recommended)” — 2026-09-29-market-intel-freshness-arkb.md
  - “Need to replace GBTC as top 3 ETF, I think. There isn't much movement visible from GBTC. Looks like BITB or ARKB should be substituted.” Chosen: “ARKB (Recommended)” and Total “all spot ETFs (Recommended)” — 2026-09-29-market-intel-freshness-arkb.md
- **Port:**
  - `dashboard/backend/src/services/priceService.ts` (tests: dashboard/backend/src/tests/priceService.test.ts; dashboard/backend/src/tests/priceFeedStale.test.ts) — Port after re-check: only if a price display is rebuilt; the freshness model applies generally.
  - `dashboard/backend/src/services/btcSupply.ts` (tests: dashboard/backend/src/tests/btcSupply.test.ts) — Port with tests: if market cap is shown; works on the pruned node.
  - `dashboard/backend/src/services/marketFeeds.ts` (tests: dashboard/backend/src/tests/marketFeeds.test.ts) — Port after re-check: only if market intelligence is rebuilt.
  - `dashboard/backend/src/services/btcDailyCloses.ts` (tests: dashboard/backend/src/tests/btcDailyCloses.test.ts) — Port after re-check: only if moving averages or returns are rebuilt.
- **Superseded / caveat:** Market data applies only if the new node shows it; the freshness model applies to every node-side feed.

#### EVID-06 — Nothing fails only in a log

- **Rule:** Every monitor, watcher, scheduled job and fallback records its last attempt, last success and last error; the node alarms when one has never succeeded, has stopped succeeding, keeps producing nothing, or is being served by a fallback (fallbacks are labelled, counted and kept warm on a schedule); repeated identical errors, failed units and "safety feature unavailable" warnings become health findings; every failure log carries its reason, and a test proves it.
- **Why:** the IBD monitor failed every 60 s from the day it shipped and was read as RPC noise (2026-08-10-bip110-invalid-mark-leak.md); the RAG canary passed while the offline fallback was serving every answer (2026-09-02-rag-relevance-calibration.md); a background collector threw on every run for months, and another never stored a result because its producer's return shape had changed (2026-10-03-remove-community-issue-collection.md, 2026-10-04-remove-mcp-data-collector.md) (+7 more).
- **Tripwire:** A last-success-age check on every probe, watcher and job; canaries assert which path served; a journal error-signature monitor and a failed-unit check in smoke and health; a test that each failure log contains its reason.
- **Owner:**
  - “1. Ok” (2026-09-29), approving keeping the ETF issuer fallback warm (cost stated: one extra headless-browser visit to iShares and etfdb plus a Yahoo call per day) — 2026-09-29-market-cap-volume-etf-warm.md
  - AskUserQuestion choices (2026-09-29): “MAs + returns backup:” Kraken daily candles, plus the node's own daily-close archive; “funding: a second venue” (Deribit, labelled) — 2026-09-29-market-intel-freshness-arkb.md
  - “1. Remove it.” — 2026-10-03-remove-community-issue-collection.md
  - “4. remove collector and unused endpoints.” — 2026-10-04-remove-mcp-data-collector.md
- **Port:** `dashboard/backend/src/tests/ragCanaryBypass.test.ts` — Port with tests.
- **Superseded / caveat:** The lesson "lookup failure caught and only logged (feature never worked)" from 2026-10-03-remove-community-issue-collection.md was later superseded by 2026-10-04-remove-mcp-data-collector.md.

#### EVID-07 — One computation per fact, one threshold table

- **Rule:** Each fact (sync state, CPU %, memory, disk per drive, temperature) and each threshold band is computed by one typed module and consumed by the page, health score, alerts and assistant alike; bands come from the sensor or platform, and boundary values are tested.
- **Why:** the page used a 2 h stale-tip rule while the assistant's knowledge service called any node "fully synced" above 99.99 % verification progress, a stale tip included, and its rewritten Bitcoin Core tool, using the initial-download flag alone, read a 3-hour-stale tip as "synced" (2026-09-30-dashboard-page-truth.md); CPU % ignored iowait (mean error 5.5 points), three disk code paths agreed only by accident and a 95 %-full backup NVMe appeared nowhere (2026-09-30-dashboard-measurements.md).
- **Tripwire:** Every consumer tested against the same fixture (stale tip, N blocks behind); boundary tests at 79/80/90/91 %; a live comparison against /proc/stat, free, df and hwmon.
- **Owner:** “Every mounted drive” (any drive over 90% caps the score at Good; cost stated: a full USB stick holds the score at Good) — 2026-09-30-dashboard-measurements.md
- **Port:**
  - `dashboard/backend/src/services/hostMetrics.ts` (tests: dashboard/backend/src/tests/hostMetrics.test.ts) — Port after re-check for Fedora/Pi: capture fixtures on the Pi 5 and the new x86 hardware.
  - `dashboard/backend/src/services/assistantFacts.ts` (tests: dashboard/backend/src/tests/assistantFacts.test.ts) — Port with tests.

#### EVID-08 — Aggregate health is honest

- **Rule:** The health score is computed explicitly from component states: a failed check scores 0, a check that could not be made is a named "unknown" that caps the label, bitcoind or LND not working (wallet locked included) caps it at Critical, and "Excellent" is decided by rule; there is one threshold set with property-tested invariants; the periodic computation is single-flight and readers never trigger a recalculation.
- **Why:** LND down scored 87 "Excellent" because failed checks earned partial credit, and page visits bumped a shared counter so one slow docker read Critical (2026-09-30-dashboard-measurements.md); overall status stayed "healthy" with electrs down because "degraded" was set only in catch blocks (2026-09-26-health-exact-container-names.md).
- **Tripwire:** Property tests of the scoring rules (the old repository ran up to 21,589,200 inputs with 0 invariant failures and caught negative controls); single-flight concurrency tests; "a stopped component gives degraded" tests.
- **Owner:**
  - “Honest rework (Recommended)”; later “Rule decides the label (Recommended)”, “Critical (Recommended)” for Docker not answering, “Over 95% = serious (Recommended)” for memory, “Score it, no issue (Recommended)” for CPU load, “All inactive = Good at most (Recommended)” for channels, “Show 'Syncing' instead” for initial sync — 2026-09-30-dashboard-measurements.md
  - “Critical (Recommended)” for Docker not answering (cost stated: a docker slower than 5 s twice in a row flashes Critical) — 2026-09-30-dashboard-measurements.md
- **Port:**
  - `dashboard/backend/src/services/healthScoring.ts` (tests: dashboard/backend/src/tests/healthScoring.test.ts) — Port with tests.
  - `dashboard/backend/src/services/healthScoreService.ts` (tests: dashboard/backend/src/tests/healthScoreService.test.ts; dashboard/backend/src/tests/healthScoreRefresh.test.ts) — Port with tests.

#### EVID-09 — Every probe and wait is bounded and settles

- **Rule:** Probes are asynchronous (no shell, no synchronous calls in the server process), time-bounded by a hard deadline, settle on every socket outcome (data, error, close, timeout), run independent reads concurrently and only for things that exist; a single-flight aggregate has its own limit after which it is abandoned and a late result discarded; every timeout is proven to cancel the call it guards; a timer limit sits between the worst legitimate duration and the next scheduling boundary and is cleared when its work settles.
- **Why:** the health view froze at "1/8 up" for 13 hours; the record traced it to a probe that never settled, most likely an Electrum probe that received a clean close (consistent with the logs, not proven from them) (2026-10-09-health-score-never-freezes.md); about 20 synchronous shell calls ran every 30 s on the server's event loop (2026-09-30-dashboard-measurements.md); a status pre-check could wait forever and `lndCall` had no timeout (2026-09-23-posture-restart-to-apply.md); a model call's timeout was created but never passed to the call (2026-10-06-health-check-parallel-stats.md).
- **Tripwire:** Stand-in servers that close cleanly, send half an answer or trickle bytes; fake clocks that throw past a bound; event-loop latency measured after changes; concurrency counted, not timed.
- **Owner:**
  - “Fix it now (Recommended)” — 2026-10-06-health-check-parallel-stats.md
  - “Restart dashboard + fix (Recommended)” — 2026-10-09-health-score-never-freezes.md
  - “OK” (the 55 s limit accepted, 2026-10-10) — 2026-10-09-health-score-never-freezes.md
- **Port:**
  - `dashboard/backend/src/services/serviceProbes.ts` (tests: dashboard/backend/src/tests/serviceProbes.test.ts) — Port with tests: add unit tests for the async probe runners (missing in the old repository).
  - `dashboard/backend/src/services/healthScoreService.ts` (tests: dashboard/backend/src/tests/healthScoreService.test.ts; dashboard/backend/src/tests/healthScoreRefresh.test.ts) — Port with tests.

#### EVID-10 — Uptime says why a service was not running

- **Rule:** Every monitor writes a heartbeat; uptime keeps distinct states — up, own outage, stopped by the owner, machine off, unmeasured — under owner-chosen rules; window queries include intervals that ended just before the window start, within the grace period (a crash that ended 15 minutes before it went unseen); a component measured for less than the window is summarised over its measured span; any repair of recorded history is backed up, dry-run, reversible and labelled in the data itself.
- **Why:** substring matching against testnet siblings made bitcoin read 83.38 % uptime when it was about 99.92 %, and a 10 h 27 min crash counted as up because the poller extended the last state forever (2026-09-30-reliability-uptime-truth.md).
- **Tripwire:** Fuzzed timelines against an independent per-second model (the old window logic failed 7,253 of 25,000); API fields `last_sample_ts` and `stale`; boundary tests at +899/+900/+901 s.
- **Owner:**
  - “Count it as downtime (Recommended)” — 2026-09-30-reliability-uptime-truth.md
  - “Services only (Recommended)” (MTTR); “Show as 'stopped by you' (Recommended)”; “No: 'stopped by you' (Recommended)” (power-off after Safe Shutdown); “Stopped until up, 15-min cap (Recommended)”; “15-min rule, like Start All (Recommended)” (slow start after a crash); “Keep 'stopped by you' (Recommended)” (testnet4 stopped, then a reboot) — 2026-09-30-reliability-uptime-truth.md
  - “Rebuild, labelled (Recommended)” — 2026-09-30-reliability-uptime-truth.md
- **Port:** `control-plane/src/uptime.rs` (tests: inline Rust tests) — Port with tests: re-check the container-status source under Podman.

<a id="iden"></a>
### IDEN — Exact identity of targets

*Every action and every check must name exactly the thing it means; similarity is never identity.*

#### IDEN-01 — Exact identity, never similarity

- **Rule:** Every container, service, process, device, key or record that an action or check touches is selected by exact name or identifier (plus a small explicit alias table), never by substring, prefix, first match, map order or directory order; an unknown or over-broad name is refused and nothing is done; probe artefacts on a live node use neutral names that match no service.
- **Why:** `name.contains("bitcoin")` picked bitcoin-testnet at random per poll, so mainnet uptime read 83 % (2026-09-30-reliability-uptime-truth.md); a stopped probe container named `wrapper-probe-mempool` made health report mempool down, and self-healing restarted the healthy mempool-api (2026-09-26-health-exact-container-names.md, 2026-09-25-electrs-mempool-clean-stop.md); with lnd absent, a restart of "lnd" would have acted on lnd-testnet (2026-09-26-exact-container-target.md) (+3 more).
- **Tripwire:** Exact-target tests with decoy siblings present (bitcoin Up beside bitcoin-testnet Exited must read Up); refusal tests for broad names (`-e.`, `...`, `.hidden`, `-`, `--all`; and `ssh`, which the old node still accepted — as a client name it revoked every key); a destructive lookup that cannot parse refuses (404) instead of guessing by prefix.
- **Owner:**
  - “So must pass along the name for health check. Refuse if container name doesn't match.” — 2026-09-26-exact-container-target.md
  - “4. yes” — 2026-09-26-health-exact-container-names.md
  - “Yes, in fact, check all measurement on the Dashboard. Make sure every one of them is actually meansuring the right thing and is correctly measuring what it's suppose to.” — 2026-09-30-reliability-uptime-truth.md
- **Port:** `control-plane/src/uptime.rs` (tests: inline Rust tests) — Port with tests: re-check the container-status source under Podman.

#### IDEN-02 — The exact failing component travels end to end

- **Rule:** Every alert carries the exact failing container from the health snapshot through classification into the remedy's parameters, and every self-heal target is resolved from the node's actual service inventory and validated at startup.
- **Why:** a mempool-db outage alert carried only "mempool", which the classifier mapped to mempool-api (2026-09-26-exact-container-target.md); during an OS upgrade the bitcoin restart runbook failed with "Container bitcoin-knots does not exist" (2026-10-08-tests-restarted-live-lnd.md).
- **Tripwire:** A startup check that every runbook target exists; a test that a component-specific finding reaches the runbook naming that component.

#### IDEN-03 — One resolver per identity, resolved at use

- **Rule:** Engine, network and service identity come from one shared, engine- and network-aware resolver called at the moment of use (never cached at import); every pair that must agree — writer and reader of an owner decision, incident opener and closer, frontend and backend route keys — uses the same mapping; when the right target cannot be resolved, the action stands down and logs once.
- **Why:** a decision to stay on the Bitcoin chain, recorded in the session's live test, was stored as `bitcoin` and looked up as `knots`, so it did nothing while the request reported success (2026-09-20-consensus-decision-p2.md); incidents opened as `lnd:*` never closed because recoveries said `lightning`, and on testnet4 an LND stall would have restarted mainnet LND (2026-09-24-lnd-sync-stall-misclassified.md); commands built at import kept pointing at mainnet after a network switch (2026-10-08-assistant-execution-paths.md) (+2 more).
- **Tripwire:** Round-trip tests that read back through the shared key; a test that switches the active network and asserts generated commands follow it; planted naming-mismatch regressions.
- **Port:** `control-plane/src/containers.rs` (tests: the proposal-engine tests) — Port after re-check for Fedora/Pi: needed only if several engines or networks run; Podman container names.

<a id="own"></a>
### OWN — One owner per action and one bring-up path

*Every action on the stack has one owner and one path; the owner's own choices are explicit.*

#### OWN-01 — One canonical start path

- **Rule:** There is exactly one way to bring services up — the boot units with their scripts and environment — and the UI, updater, recovery and watchdog all call it; a second start is a no-op (containers started, not recreated); a targeted start never recreates dependencies; a missing generated environment (such as memory limits) refuses rather than starting the money daemons at defaults; there is one installer or image definition and no runnable legacy installer.
- **Why:** Start All re-implemented bring-up without the RAM-scaled limits, the lock, the health gate or the testnet stack (2026-09-30-node-power-buttons.md); after an OS update the runner's own start and the queued unit start recreated every container and restarted LND twice (2026-10-09-upgrade-deadlock-and-progress.md); a MariaDB auto-install recreated bitcoind and Electrs and restarted LND (2026-10-03-upgrade-gates-round-2.md); a legacy installer would have run `kill -9` against the live dashboard port (2026-08-22-rollback-consolidation.md).
- **Tripwire:** A test that every bring-up path carries the same environment marker; container IDs and limits unchanged after Start All; refusal test without the limits file; a check that every unit file in the repository is installed by the one installer.
- **Port:**
  - `dashboard/backend/src/utils/composeControl.ts` (tests: dashboard/backend/src/tests/rollbackConsolidation.test.ts; dashboard/backend/src/tests/upgradeRound2.test.ts) — Port after re-check for Fedora/Pi: Docker Compose v2-specific; rebuild for Podman/Quadlet keeping the test assertions.
  - `dashboard/backend/src/services/nodePower.ts` (tests: dashboard/backend/src/tests/nodePower.test.ts) — Port after re-check for Fedora/Pi: docker stop / compose calls become Podman and systemd TimeoutStopSec / Quadlet starts.

#### OWN-02 — One orchestrator, serialized mutation

- **Rule:** All mutators of the shared service namespace (boot, upgrade, self-heal, UI, cascades) take one lock that is released on process death; exactly one component owns start ordering and post-upgrade bring-up; dependants restart when their dependency is healthy (debounced), never because a credential file appeared; every upgrade, revert or restart of a service holds a per-service lock and refuses a second press visibly.
- **Why:** four units raced `docker compose up` after a reboot (28 conflicts on five days since 2026-07-01) and an upgrade was reported failed although apt had succeeded (2026-08-10-upgrade-reboot-compose-race.md); after an OS upgrade two components brought the stack up at once (2026-09-30-dashboard-page-truth.md); the cookie cascade started LND about 25 s before bitcoind was healthy, so LND came up without its onion (2026-09-30-node-power-buttons.md); a double press started a second Electrs upgrade (2026-10-03-electrs-0.12-support.md).
- **Tripwire:** A parallel bring-up race test (the old lab saw 7 conflicts without the lock, 0 with it); a test that one cookie rewrite causes at most one dependant restart; second-press refusal test.
- **Port:** `scripts/compose-lock.sh` (tests: dashboard/backend/src/tests/upgradeRebootBringup.test.ts; dashboard/backend/src/tests/upgradeNoDeadlock.test.ts) — Port after re-check for Fedora/Pi: Docker Compose-specific; with Quadlet units the single bring-up path may replace it; keep the race and deadlock scenarios as the specification.

#### OWN-03 — No lock is held across a restart that needs it

- **Rule:** A maintenance step never holds a lock across an action that can restart services whose stop or start path takes the same lock; stack ownership during maintenance is explicit, checked without mutating it (a shared lock or a read), tolerant of momentary checks, and an ownership file left by a dead process reads as free.
- **Why:** the "Update Linux" runner held the compose lock through `apt-get upgrade`; docker-ce's post-install restarted Docker, the stack units' stops waited on that lock, and the node hung about 9 minutes with the dashboard down; the ownership probe itself took an exclusive lock and made stops skip (2026-10-09-upgrade-deadlock-and-progress.md).
- **Tripwire:** A deadlock replay with fakes of docker, sudo and the package manager whose post-install replays the runtime restart (the old scripts fail); 300 simultaneous down-and-stop pairs with none skipped; a SIGKILLed holder frees the lock.
- **Owner:** “Let's just fix it” — 2026-10-09-upgrade-deadlock-and-progress.md
- **Port:**
  - `scripts/compose-lock.sh` (tests: dashboard/backend/src/tests/upgradeRebootBringup.test.ts; dashboard/backend/src/tests/upgradeNoDeadlock.test.ts) — Port after re-check for Fedora/Pi: Docker Compose-specific; with Quadlet units the single bring-up path may replace it; keep the race and deadlock scenarios as the specification.
  - `scripts/rikuri-upgrade-runner.sh` (tests: dashboard/backend/src/tests/upgradeNoDeadlock.test.ts) — Do not port as is: apt-based in-place OS updates; Fedora IoT updates whole images; keep the test's lock and restore rules as the specification.
- **Superseded / caveat:** The fix was not yet proven on real systemd and Docker when its record closed.

#### OWN-04 — Owner stop is one state every actor obeys

- **Rule:** An owner stop is written before stopping, scoped as chosen (until Start All or the next boot), and queried by every actor that can restart a service or send an alert — enumerated, each with a test; the health view shows `Stopped by you since <time>` with no score while still surfacing faults in what keeps running; network, proxy and SSH findings stay active so the owner can always reach Start.
- **Why:** the owner's stop un-stopped itself after 45 minutes; then the heartbeat, the Guardian loop, the control plane, an anomaly scanner (5 "wallet_missing" emails) and the bell (30 "is down" alerts) each acted during the stop (2026-09-30-node-power-buttons.md); the health card read "29 Critical" while the owner had stopped the node (2026-09-30-dashboard-page-truth.md); during the Ubuntu upgrade an owner stop held self-heal, and its boot scope brought the stack back after the reboot, as designed (2026-10-03-ubuntu-26.04-upgrade.md).
- **Tripwire:** One hold test per actor (heartbeat, Guardian loop, bell, anomaly loop) with a real mutation check; a live audit that every notification during a stop came from a held path.
- **Owner:**
  - “'Stopped by you' (Recommended)” — 2026-09-30-dashboard-page-truth.md
  - “Until I press Start All (Recommended)” — 2026-09-30-node-power-buttons.md
- **Port:** `dashboard/backend/src/utils/maintenanceMode.ts` (tests: dashboard/backend/src/tests/ownerStop.test.ts; dashboard/backend/src/tests/guardianHoldAllPaths.test.ts) — Port with tests: re-enumerate the actors of the new node.

#### OWN-05 — Maintenance windows hold alerts, never safety

- **Rule:** Planned operations (restart, upgrade, backup, restore, image update) hold a persisted, bounded maintenance window that survives a reboot, lasts until every dependant that was running is ready again, is honoured by every monitor and remediator, and expires (an absent, unparseable or future timestamp never silences); suppression is scoped by alert type and reason, never pauses safety monitors (force closes, fund movements), and a held alert is delayed and sent if its condition persists — never dropped.
- **Why:** the window was lifted when bitcoind answered, before LND was back, and self-heal restarted LND a second time (2026-09-23-posture-restart-to-apply.md); in-memory suppression was lost across the reboot and fired CRITICAL "LND is down" (2026-08-10-upgrade-reboot-compose-race.md); a broad maintenance flag paused force-close and fund-movement monitors for up to 6 h, and held "down" alerts were dropped (2026-10-02-guardian-summaries-reach-the-owner.md); during the owner's OS upgrade self-heal restarted LND and ran the electrs and mempool-web restart runbooks, and bitcoin's runbook failed its precheck (2026-10-08-tests-restarted-live-lnd.md).
- **Tripwire:** Grace-window evaluator tests (absent / unparseable / future timestamps); planted "window lifted when bitcoind answers" regression; tests that the flag holds alerts but not safety monitors; down during the window and still down afterwards sends exactly once; no runbook fires while an upgrade owns the stack.
- **Owner:** “Restart All health services should read the flag, right?” — 2026-10-02-guardian-summaries-reach-the-owner.md
- **Port:**
  - `dashboard/backend/src/utils/upgradeStateCheck.ts` (tests: dashboard/backend/src/tests/upgradeRebootBringup.test.ts; dashboard/backend/src/tests/upgradeDoneBanner.test.ts) — Port with tests.
  - `dashboard/backend/src/services/healthService.ts` (held-alert logic) (tests: dashboard/backend/src/tests/healthHeldAlertsFlow.test.ts; dashboard/backend/src/tests/healthHeldAlertsEdges.test.ts) — Port after re-check: port the tests as the specification; the held map lived in memory.

#### OWN-06 — Restore exactly what you stopped; record intent first

- **Rule:** Any operation that stops services records exactly what was running before and restores exactly that set, reporting what it could not restore; health fails when an enabled service is not running; intent markers (planned stop, maintenance) are written before the action and removed if it fails; every wrapper timeout exceeds the worst case of what it wraps.
- **Why:** an OS-upgrade runner restored only the mainnet stack and tapd was down 39 hours while smoke said PASS (2026-09-16-self-heal-p0-live-repairs.md); the same class recurred on 2026-10-08 (2026-10-08-tests-restarted-live-lnd.md); a testnet stop wrote its "stopped by you" marker only after `compose down` returned, so a poll recorded an outage (2026-09-30-reliability-uptime-truth.md).
- **Tripwire:** A stack running before an update is back after it, and one not running stays down; marker-before-action test (red first); smoke fails an enabled-but-inactive service.

#### OWN-07 — Each check and each repair has one owning process

- **Rule:** Each check and each repair runs exactly once, in one owning process, written down as "who watches what" (systemd, control plane, application, assistant); no second process restarts the same service; every enable/disable flag is read by the process it configures, and its effect is logged at startup.
- **Why:** six monitors ran twice in two binaries with independent cooldowns, so one cookie change restarted electrs, lnd and mempool twice, and the duplicate copy was misconfigured and silently blind; a disable flag was read by a different binary, so the loop it was meant to stop kept restarting things (2026-09-17-self-heal-p3-one-monitor.md).
- **Tripwire:** The startup log has exactly one "monitor started" line; a route-surface test per process; a startup log line per flag.

#### OWN-08 — Long operations are jobs, and timeouts are layered

- **Rule:** Multi-minute operations (power, upgrades, backups, restores) run as one background job at a time (202, or 409 if one is running) with a status endpoint and a last result that survives a restart; every client wait is shorter than every proxy timeout in front of it and reports "still running" rather than failure; every proxy timeout exceeds the longest route behind it; a request watchdog that has answered owns the response and can never crash the process.
- **Why:** power operations ran inside HTTP requests behind a 60 s proxy while a stop waits about 90 s per daemon (2026-09-30-node-power-buttons.md); testnet stop/start routes of up to 540 s sat behind a 60 s proxy timeout (2026-09-30-dashboard-page-truth.md); approvals waited 120 s behind a 60 s proxy (2026-09-28-repairs-outlive-the-request.md); late replies after a watchdog's 503 produced 215 "headers already sent" errors and could crash the process (2026-10-06-health-check-parallel-stats.md).
- **Tripwire:** 202/409 route tests; fake-timer test that the client answers before the proxy limit; proxy-timeout test (red on 60 s); watchdog late-reply tests over every reply path.
- **Owner:** “Every route (Recommended)” — 2026-10-06-health-check-parallel-stats.md
- **Port:** `dashboard/backend/src/middleware/stallWatchdog.ts` (tests: dashboard/backend/src/tests/stallWatchdogLateReply.test.ts; dashboard/backend/src/tests/moneyRoutesNotCut.test.ts) — Port after re-check: Express-specific; port the tests as the specification.

#### OWN-09 — Owner choices are explicit, costed, plain and durable

- **Rule:** Every behaviour-changing default (who is notified, how long alerts are held, outbound fetches, config rewrites, recreating bitcoind) is put to the owner as an explicit choice whose cost is read from the code and verified true before asking; choices are explained in plain language with their effect on wallet, Lightning, electrs, mempool and disk (raw options behind "Technical settings"); a control ships together with the path that makes it take effect and says when a restart is needed; decisions persist atomically, are read back from disk in tests, are a loud error when the store is corrupt, and an answered prompt collapses with its date and an undo.
- **Why:** a change silently dropped two notification channels from weekly reports, and the owner was told a hold lasted "up to 45 minutes" when it could be renewed for 6 h (2026-10-02-guardian-summaries-reach-the-owner.md); the owner asked "Is by Standard you mean Bitcoin Core? … I'm a little confused which is which" (2026-09-20-posture-clarity.md); an IBD monitor would have rewritten docker-compose.yml and force-recreated bitcoind on every start with no owner choice (2026-10-04-remove-model-warmup-and-post-ibd.md); the consensus question had no way to be answered and remembered (2026-09-20-consensus-decision-p2.md) (+2 more).
- **Tripwire:** A test that owner-facing strings carry no raw options (datacarrier, bitcoin.conf, `=<digit>`); decision-store tests (atomic, read from disk, corrupt store is a loud error); verifier review for behaviour changes nobody asked for.
- **Owner:**
  - “I think we just have 2 different cards, each for each engine.” … “For a novice, we don't understand the technical things like datacarrier=1” … — 2026-09-20-engine-cards.md
  - “3. Remove” — 2026-10-04-remove-model-warmup-and-post-ibd.md

<a id="heal"></a>
### HEAL — Self-healing, runbooks, incidents, alerts and approvals

*Automation may only act through one honest, bounded, recorded path, and the owner must actually hear about it.*

#### HEAL-01 — Detect, dispatch, execute: one path, one record

- **Rule:** Health checks only detect; every repair goes detector → one dispatcher → tiered proposal → one executor and is recorded; every detector in every process reports through one narrow, authenticated, field-validated route with one shared issue vocabulary (an unknown type is a loud 400) that can write the record but never run a fix.
- **Why:** an induced `docker stop mempool-web` made the synthesizer restart the healthy mempool-api while a side door restarted the real one with no tier check or record (2026-09-18-self-heal-p3-incident-record.md); the control plane's detector findings never became incidents and the repairs it ran itself were invisible (2026-09-18-guardian-page-and-rust-detectors.md).
- **Tripwire:** An induced-fault drill ends in one incident naming the right container and one restart; a cross-language test reads the other process's issue constants and fails on any unknown.
- **Owner:** “Ok replace AI Fixes and Rust-side detectors write incidents” — 2026-09-18-guardian-page-and-rust-detectors.md

#### HEAL-02 — Repairs report what really happened

- **Rule:** The remediation executor fails a runbook when a pre-check does not match, an action exits non-zero or times out, or the post-check never passes; it runs undo on failure, kills the whole process group on timeout and records the failed step and reason; every lifecycle command verifies its effect (the container exists and runs the expected image) instead of trusting the exit code; a fix counts only when the detector that raised it no longer sees it and the consumer's outcome holds; fires and attempts are counted separately; measured effects and refusals are recorded; record IDs are not derived from the clock alone.
- **Why:** the executor logged "completed" 71 times for a validation that could never pass and 4 times while every command failed (2026-09-17-self-heal-p2-honest-executor.md); `compose up` without a profile matched nothing and exited 0 (2026-08-22-rollback-consolidation.md); a USB remount runbook reported SUCCESS while the backup engine still could not see the drive (2026-10-05-usb-backup-run-media.md); a prune row said "executed" when Docker refused (2026-09-18-guardian-page-and-rust-detectors.md).
- **Tripwire:** Executor tests with mutations back to the old behaviour, each red; verify-by-redetect tests; the remount validation queries the backup engine's own view of the drive.
- **Port:** `control-plane/src/runbook/executor.rs` (tests: module tests) — Port with tests.

#### HEAL-03 — Attempt budgets, recorded before acting, then escalation

- **Rule:** Self-heal enforces a persisted, cross-cycle attempt budget per hypothesis over a rolling window; every attempt is recorded (outcome UNKNOWN) before the action runs, so a remediation that kills its own process still counts; caps count attempts, not successes; when every option is spent the owner is notified once, with the definition's own severity, deduplicated by a persisted sentinel; the budget query fails open and escalation dedup fails closed.
- **Why:** tapd's start runbook ran 841 times, 48 a day, 783 of them without fixing it because the limit lived inside one call, and about 200 dashboard-restart firings left no rows because the remedy killed the recorder (2026-09-16-drb-attempt-budget-and-escalation.md); a restart cap that counted only successes allowed about 339 failed proposals in 24 h (2026-09-16-owner-notification-delivery.md).
- **Tripwire:** "a hypothesis over budget is skipped, not executed", "records the attempt BEFORE running the runbook" and "exhausted pages the owner with the DRB rollback message" tests, each red on the old code.
- **Owner:** the owner's decision as the record gives it (asked, not quoted): budget spent → skip that hypothesis and continue down the ladder (escalate only when all are spent), and a 24-hour rolling window — 2026-09-16-drb-attempt-budget-and-escalation.md
- **Port:**
  - `dashboard/backend/src/core/diagnosisEngine.ts` (tests: dashboard/backend/src/tests/diagnosisEngine.test.ts) — Port after re-check: port the test scenarios as the specification; the engine design itself produced several incidents.
  - `dashboard/backend/src/tests/ownerNotificationDelivery.test.ts` — Port with tests: as the specification of the alert path.

#### HEAL-04 — The remediation catalogue is gated in CI

- **Rule:** Every declarative self-heal definition and runbook is validated in CI against the engine's real vocabulary (fields, tiers, operators, signal names parsed from the collector source, existing runbooks), against real endpoints, ports, units, scripts and container names, and against the daemons' option names; unknown fields are rejected and an empty predicate set never matches; the templater refuses unresolved placeholders; stop timeouts are at least the service's stop grace; any runbook that stops a funds or chain daemon has an undo that restarts it; every alert type has a producer and every collected signal a consumer; each schema lives apart or carries a validated type.
- **Why:** `required_any`, a field the engine never read, made a backup rule match vacuously and restart the live dashboard every 30 minutes (156 restarts on 2026-09-14) (2026-09-14-guardian-scb-restart-loop.md); 14 of 89 runbooks were broken (invented or wrong routes, LND REST calls sent to the local model server's port, unsupplied template variables, units that did not exist) (2026-08-23-runbook-command-audit.md); a runbook wrote a bare `sweep-fee-rate=` key into LND's config and restarted LND (2026-09-17-self-heal-p2-honest-executor.md); five referenced runbook ids existed nowhere (2026-08-10-crashloop-detection.md) (+3 more).
- **Tripwire:** A schema gate proven by reintroducing a misspelt field and an invented signal; a command audit with negative controls; a catalogue test over the real files; a registry test that every issue type has a producer and every signal a consumer.
- **Owner:** The owner chose to fix the violations rather than baseline them; deleting DRB-NETWORK-OFFLINE-01 was owner-approved (the record's account, not a quotation) — 2026-09-17-drb-schema-gate.md
- **Port:**
  - `dashboard/backend/src/tests/runbookCommandAudit.test.ts` — Port after re-check for Fedora/Pi: its rules name the old endpoints, ports and Docker Compose v1; rewrite the rules for the new catalogue.
  - `dashboard/backend/src/core/diagnosisEngine.ts` (tests: dashboard/backend/src/tests/diagnosisEngine.test.ts) — Port after re-check: port the test scenarios as the specification; the engine design itself produced several incidents.
  - `dashboard/backend/src/tests/drbSchemaGate.test.ts` and `ragdocs/drb-schema-baseline.json` — Port after re-check: tied to the old rule schema; port if a declarative catalogue is kept.

#### HEAL-05 — Remedies are proportionate, specific and discovered

- **Rule:** Remedies come from a curated, ordered per-issue list (each entry confirmed loadable), never filesystem order; a service name alone never selects a remedy, least of all a destructive one; a remedy is proportionate (never restart the management plane because one scheduler may be down); runbooks discover live resources from the running service (the mounted volume), fail closed when they are absent, match errors case-insensitively and are re-validated on every service upgrade; restart success is judged by uptime since the last start, not a restart counter; the owner is told in advance which long-failing conditions a new escalation will start paging about.
- **Why:** "electrs stopped" scored as an index problem and produced a destructive-reindex approval request (2026-09-17-self-heal-p2-probes-and-selection.md); the reindex runbook hard-coded the old volume and would have restarted Electrs on the corrupt live index (2026-10-05-electrs-0.11-index-removed.md); three rules restarted the whole dashboard, and a clock-drift rule with 332 failed attempts was about to page at P0 (2026-09-17-drb-schema-gate.md).
- **Tripwire:** A classification table (the old one had 26 rows); a gate that every curated runbook loads; a runbook test that reads the mount rather than a fixed volume name.
- **Port:** `ragdocs/runbooks/RB-ELECTRS-INDEX-REINDEX-01.json` (tests: a runbook test (3 cases)) — Port after re-check for Fedora/Pi: Docker volume names; x86 full node only.

#### HEAL-06 — One incident per problem, closed by its detector

- **Rule:** Every problem is one incident with an append-only timeline (opened → diagnosed → fix → verified → resolved) and one open incident per `service:ISSUE_TYPE`; repeated sightings bump a timestamp; a resolved incident is frozen and a recurrence is a new incident; the chosen fix is recorded when chosen; only the owning detector closes it, from current level state on consecutive good looks; a staleness sweep closes incidents no detector will revisit; a container that goes down is reported whatever its exit code; the owner's page shows "waiting for you / happening now / recently resolved" and runs nothing itself.
- **Why:** one tapd problem logged every 30 minutes showed as "100 incidents, 99 unresolved" beside a 94/100 score (2026-09-18-self-heal-p3-incident-record.md); `docker stop` exits 0, so the most ordinary way a container goes down produced no report (2026-09-18-guardian-page-and-rust-detectors.md); an LND incident could never close because nothing reported "syncing → synced" as a recovery (its closing state was also held in memory lost on restart) (2026-09-24-lnd-sync-stall-misclassified.md).
- **Tripwire:** Incident store and dispatch tests; induced faults (`kill` and `stop`) open an incident at +20 s and close it on the start event; a late-write-after-resolve test.
- **Owner:** “Ok replace AI Fixes and Rust-side detectors write incidents” — 2026-09-18-guardian-page-and-rust-detectors.md

#### HEAL-07 — One approval path that round-trips

- **Rule:** There is exactly one approval store — durable, step-up authenticated, signed, with expiry enforced at approve time (an unparseable deadline counts as expired), restored at startup and swept; every approval channel (dashboard, phone) is tested end to end against the server's real authorization; remote buttons verify the sender is the owner's configured identity; approval text names the exact target and why it is held and never calls a funds action "safe" or "low risk"; an approval-notification path that fails to wire is a health failure; unanswered requests are surfaced.
- **Why:** every approval answered 403 from about 2026-07, 730 of 741 decisions were never resolved (last success 2026-04-30); any member of a chat could approve a held action; seven other approval stores existed (2026-09-17-self-heal-p3-approvals.md); a held LND restart request said "Risk level: low" (2026-09-26-memory-restart-asks-for-funds.md); approval notifications were dead at every start because a module stood in for an instance (2026-10-04-config-tamper-notifies-owner.md).
- **Tripwire:** Approval round-trip tests per channel (all red on the old code); sender-check refusals; pending-survives-restart and expiry tests; approval-text tests.

#### HEAL-08 — Repairs run to completion, one at a time

- **Rule:** An accepted repair runs to completion in a task detached from the caller, always writes its decision, outcome and notification, and releases shared locks before long work; there is one run per runbook and target (a second is refused as "already running" and not counted); clients classify a missing answer truthfully (still running / unreachable / HTTP error) and never blame the server for a job that is still running.
- **Why:** the Tor onion repair was killed at exactly 2:00 by the caller's timeout on two days (on 2026-09-24 after it had already restarted Tor) and left no record; the dashboard then logged "Control plane unreachable" while the repair was still running (2026-09-28-repairs-outlive-the-request.md).
- **Tripwire:** Lifetime tests (work not cancelled with the caller, a panic returned as an error); overlapping submissions refused; still-running classification tests.
- **Owner:** “Let's fix the tor onion.” (2026-09-28) — 2026-09-28-repairs-outlive-the-request.md
- **Port:** `control-plane/src/http_server.rs` (run_to_completion) (tests: mod repair_lifetime_tests) — Port with tests: also pin each handler's use of it (a bypass mutation survived).

#### HEAL-09 — An alert counts only when delivered

- **Rule:** Alerts raised inside the node are delivered in-process (or with a scoped machine credential); a send counts as delivered only when at least one owner-facing channel confirms success, otherwise it is logged loudly and retried; text is escaped for each channel; links are ones the channel can open (on rejection, resend once without buttons); severity is one normalised enum and each source declares its channels; scheduled reports have explicit channels and descriptive titles; disabled channels are neither attempted nor counted as failures, while repeated failures of the primary channel alert; the assistant's "alert" outputs become deduplicated notifications, never actions.
- **Why:** Guardian notifications got 401 sixteen times in 72 h from the node's own auth gate, while other paths 404'd or threw silently (2026-09-16-owner-notification-delivery.md); the daily digest logged "sent" every day but went to a dashboard bell with 0 clients (2026-10-02-guardian-summaries-reach-the-owner.md); service senders logged "notification sent" on a 401 (2026-09-16-rust-alert-delivery-and-owner-token.md); a "notified" store was written before sending (2026-10-04-config-tamper-notifies-owner.md) (+1 more).
- **Tripwire:** Delivery tests for every alert path (the old code fails); mutants "mark before send" and "successes >= 0" caught; acceptance is a notification-history entry showing the primary channel's success.
- **Owner:** “Fix the guardian's daily telegram summary (is this sent to Telegram, I don't think I've been receiving any daily summary. Used to receive weekly summary from Groq, but not anymore).” — 2026-10-02-guardian-summaries-reach-the-owner.md
- **Port:**
  - `dashboard/backend/src/tests/ownerNotificationDelivery.test.ts` — Port with tests: as the specification of the alert path.
  - `control-plane/src/dashboard_internal.rs` (tests: Rust tests) — Port with tests.
  - `dashboard/backend/src/security/integrity/configIntegrity.ts` (tests: dashboard/backend/src/tests/configTamperNotify.test.ts) — Port with tests.

#### HEAL-10 — Crash loops page the owner; diagnose before restarting

- **Rule:** Any service restarted more than N times in M minutes (with OOM and heap signatures classified) notifies the owner, deduplicated per service; the remedy for a looping or wedged service is diagnosis, and its state is captured without destroying it (services that may wedge start with diagnostics enabled) before anything restarts it.
- **Why:** mempool-api restarted 305 times without a word to the owner (2026-08-10-crashloop-detection.md); a signal sent to open the debugger restarted the wedged backend and destroyed its wedged state before a stack could be captured (2026-08-22-mempool-page-stale-explorer-and-zero-fees.md).
- **Tripwire:** A pure restart-loop detector with an injected clock (8 cases); it worked in a real recurrence on 2026-08-16 (the owner reported it within about 2 h); no deliberate live drill was run.
- **Owner:** “nothing should fail silently or be in a crash loop” — 2026-08-10-crashloop-detection.md
- **Port:** `dashboard/backend/src/utils/restartLoopDetector.ts` (tests: dashboard/backend/src/tests/restartLoopDetector.test.ts) — Port after re-check for Fedora/Pi: feed it systemd NRestarts / Podman restart counts instead of Docker's.

<a id="upg"></a>
### UPG — Upgrades, rollback, deploys and machine state

*Image rollback covers the OS; everything above it still needs proven upgrades, exact reverts and a node that runs exactly what was verified.*

#### UPG-01 — Upgrades prove the new version runs before saying so

- **Rule:** Every service upgrade runs one pipeline behind an action-time owner credential and a closed allow-list: verify, check the new image with the node's real settings in an isolated container with no network and no data, snapshot, repin, recreate only that service, enter maintenance (with a TTL, left in `finally`), watch for at least start_period + interval × retries + margin and fail on any restart, exit or unhealthy state, roll back automatically and verify the rollback with the same watch, and report the real outcome on every channel.
- **Why:** Electrs 0.12.0 was reported "Upgrade complete ✓" two seconds after start while it crash-looped (RestartCount 363) on an unknown argument, until the owner rolled back by hand about 1 h 40 min later (2026-10-03-upgrades-cannot-break-a-service.md, 2026-09-30-dashboard-page-truth.md); rollback for four services was code-reviewed but not live-fired (2026-08-08-one-click-infra-upgrades.md).
- **Tripwire:** The settings check refuses the failing release with its exact crash line; the stability watch is drilled on a crash-looping scratch container; wiring guards on every step.
- **Owner:** “Roll back. Then close the three gaps.”; then “Yes, roll back + tell me” — 2026-10-03-upgrades-cannot-break-a-service.md
- **Port:** `dashboard/backend/src/services/upgradeSafety.ts` (tests: dashboard/backend/src/tests/upgradeSafety.test.ts; dashboard/backend/src/tests/upgradeRound2.test.ts) — Port after re-check for Fedora/Pi: its settings-check containers are Docker; rebuild on Podman.

#### UPG-02 — One apply path; touch only the target

- **Rule:** Upgrades and rollbacks share exactly one apply path, and one module drives the container runtime (correct binary, files, profiles, lock); upgrading one service recreates only that service, after which the node verifies every container's network attachment and that untouched containers kept their IDs; LND is never restarted as a side effect of an unrelated change.
- **Why:** a second rollback path had never once succeeded (it called an uninstalled tool with a rotted image map) (2026-08-22-rollback-consolidation.md); bumping only mempool-web recreated bitcoin, electrs, tor and lnd, and LND came back with no network and restart-looped until reconnected by hand (2026-08-22-mempool-page-stale-explorer-and-zero-fees.md).
- **Tripwire:** Consolidation tests (deleted paths stay deleted, failure reason interpolated); a post-recreate network and DNS check; a container-ID check.
- **Owner:** Owner chose: consolidate, not repair-in-place (the record's heading, not a quotation) — 2026-08-22-rollback-consolidation.md
- **Port:** `dashboard/backend/src/utils/composeControl.ts` (tests: dashboard/backend/src/tests/rollbackConsolidation.test.ts; dashboard/backend/src/tests/upgradeRound2.test.ts) — Port after re-check for Fedora/Pi: Docker Compose v2-specific; rebuild for Podman/Quadlet keeping the test assertions.

#### UPG-03 — Revert is exact, and rollback is drilled off mainnet

- **Rule:** Revert restores the exact snapshot the upgrade took, verified by hash, and refuses and notifies if it changed; upgrade rollback, Revert and holds are drilled end to end on a non-mainnet stack (testnet, signet or regtest) before they are trusted; deleting rollback state follows a stated, accepted cost and verified non-use, and rollback artefacts that still reference it are updated or flagged.
- **Why:** Revert re-pinned the tag read from the running (new) container, changed nothing and cleared the failure, and then picked the oldest snapshot (2026-10-03-electrs-0.12-support.md); a full failed-upgrade rollback was never run live because a failing hold would have upgraded mainnet (2026-10-03-upgrades-cannot-break-a-service.md); a 63.92 GB index was deleted while older snapshots still declare it (2026-10-05-electrs-0.11-index-removed.md).
- **Tripwire:** Revert-plan tests (restore whole / restart only / refuse); a recorded rollback drill on the test stack for each release.
- **Owner:** “1. Delete the old index.” — 2026-10-05-electrs-0.11-index-removed.md
- **Port:** `dashboard/backend/src/services/revertPlan.ts` (tests: dashboard/backend/src/tests/revertPlan.test.ts) — Port with tests.

#### UPG-04 — Supported release lines and one hold function

- **Rule:** The node records, per service, the release line it is tested with: patches inside the line are one-click (the newest in-line patch is offered even when a newer line exists); a new line is held as "Needs a node update first" with reasons and no UI override; an arbitrary older line is refused; prerequisites are shown as a numbered sequence; a dependant that does not stay up rolls the upgrade back; every entry point (UI, API, chat button, retry, assistant) calls one mutation function that checks the one hold function before any side effect such as an image pull.
- **Why:** the consensus guard lived only in the page, and Retry, `/execute` and the Telegram button bypassed it (2026-10-03-upgrades-cannot-break-a-service.md); a MariaDB patch fixing 7 CVEs was never offered because only the newest (held) release was considered (2026-10-03-inline-patch-beside-held-line.md); an "any older line is supported" fix let a Core 29 tag pass on a Core 31 node (2026-10-03-electrs-0.12-support.md) (+1 more).
- **Tripwire:** A wiring test that the hold is checked before anything is pulled; newest-in-line tests; older-line refusal tests.
- **Owner:**
  - “Do both now.” — 2026-10-03-inline-patch-beside-held-line.md
  - “3. We should have a auto rollback.  Incidently, if the upgrade require a sequeced upgrade (for example, must upgrade to Bitcoin Core 31 before Electrs 0.12; then  our display should say Sequenced upgrad required: start from 1. Rikurinode 1.5; 2. Bitcoin Core 31; 3. Electrs 0.12” … — 2026-10-03-upgrade-gates-round-2.md
  - “Supported release lines” and “Hold it, show why” (answers to two questions) — 2026-10-03-upgrades-cannot-break-a-service.md
- **Port:** `dashboard/backend/src/config/upgradeSupport.ts` (tests: dashboard/backend/src/tests/upgradeSafety.test.ts; dashboard/backend/src/tests/upgradeRound2.test.ts) — Port with tests.

#### UPG-05 — Release notes are read early and judged by calibrated rules

- **Rule:** On first detection of a version the node fetches the real notes of every intervening release (a pointer text never counts as read, unreadable reviews are retried, completeness of the range is tracked) and tells the owner during the waiting period; findings that always matter (reindex, migration, required versions, no downgrade) hold, others hold only when they name something the node uses; any classifier that can trigger autonomous action uses whole-word rules measured on a corpus of real releases before it is enabled; automatic security installs require every gate, one attempt per version, no active maintenance or owner stop, notices before and after, and a step-up-protected switch.
- **Why:** the keyword "rce" matched inside "force", so every LND release ("force close") was sent as a CRITICAL security update skipping the 14-day wait (34 of 107 releases flagged) and would have installed itself on day one (2026-10-03-upgrade-gates-round-2.md); any "Breaking Changes" section would have held LND patches that did not affect the node (0.21.3 → 0.21.4) (2026-10-03-upgrades-cannot-break-a-service.md).
- **Tripwire:** A corpus re-measure (after the fix: 19 flagged, all Redis security releases, none for LND or Bitcoin); hard/soft classification tests; release-review tests (unreadable reviews retried, range completeness).
- **Owner:**
  - “Yes, count them” — 2026-10-03-upgrade-gates-round-2.md
  - “Auto-install, only if all gates pass” — 2026-10-03-upgrade-gates-round-2.md
  - “1. relax it” — 2026-10-03-upgrade-gates-round-2.md
  - “We have a waiting period for each services. I think we should search for documentation for upgrade requirement when the notice to upgrade waiting period first appears. Then send notice to inform the user to wait for rikuri update and the waiting period to be over before upgrading. This will give us time to make any needed changes to rikurinode, during the waiting period.” — 2026-10-03-upgrades-cannot-break-a-service.md
  - Owner answer 1, which the record's section 0 gives as “Hold it, show why”; its R9 restates it as when the release notes show…, hold — 2026-10-03-upgrades-cannot-break-a-service.md
- **Port:**
  - `dashboard/backend/src/services/upgradeSafety.ts` (tests: dashboard/backend/src/tests/upgradeSafety.test.ts; dashboard/backend/src/tests/upgradeRound2.test.ts) — Port after re-check for Fedora/Pi: its settings-check containers are Docker; rebuild on Podman.
  - `dashboard/backend/src/services/upgradeRequirements.ts` (tests: dashboard/backend/src/tests/upgradeRequirements.test.ts) — Port with tests.
- **Superseded / caveat:** The lesson "release-note hold too broad (blocks patches that do not affect the node)" from 2026-10-03-upgrades-cannot-break-a-service.md was later superseded by 2026-10-03-upgrade-gates-round-2.md.

#### UPG-06 — Consensus safety of every bitcoind pin

- **Rule:** Every bitcoind release is classified for consensus change and fails closed (unreviewed means consensus-changing); a consensus-changing release is never offered through one-click upgrade; every bitcoind image pin is on a default-deny allow-list of reviewed builds (no floating tags), checked against primary release notes and at binary level in a throwaway container, and every reference in the repository agrees; a pinned daemon that does not track upstream carries a dated review with automatic re-open triggers (≤ 92 days, a new release on its base branch, end of life); the CI gate and the runtime guard share one list.
- **Why:** the pinned Knots build rejected mainnet block 961,642 and followed the BIP-110 fork although `consensusrules=rdts` was set nowhere (2026-09-20-knots-repin-and-gate.md); the Upgrades page offered a fork build as a "minor", ready, one-click upgrade (2026-09-20-consensus-upgrade-guard.md); a frozen pin lacked a fix for a chainstate bug that wears SSDs (2026-09-22-knots-pin-review.md).
- **Tripwire:** Consensus-classification and pin allow-list tests (proven red on the old pin); review-evaluator tests ("could not check" is unknown; re-pinning without a new review fails CI).
- **Port:**
  - `dashboard/backend/src/config/consensusBuilds.ts` (tests: dashboard/backend/src/tests/consensusBuilds.test.ts; dashboard/backend/src/tests/knotsConsensusPin.test.ts) — Port with tests.
  - `dashboard/backend/src/config/knotsPinReview.ts` (tests: dashboard/backend/src/tests/knotsPinReview.test.ts) — Port after re-check: vital only if Knots is offered; generalise the cadence to every frozen pin.

#### UPG-07 — One registry of what runs; no silent downgrade

- **Rule:** One registry lists every image per service (primary and lockstep siblings); version identity comes from the deployed image reference, never the service's own report; pin drift is detected from what is actually deployed, and the build fails on any unregistered image; no overlay or legacy file may override a pin, and LND or bitcoind is never downgraded unless explicitly requested.
- **Why:** mempool-web stayed on v3.2.1 beside mempool-api v3.3.1 for about 3.5 months, flooring fee estimates, because the checker knew one image (2026-08-22-mempool-page-stale-explorer-and-zero-fees.md); legacy overlay files would have downgraded LND three majors on a rollback (2026-08-22-rollback-consolidation.md); a service reported version "1.0.0" whatever image ran (2026-08-08-one-click-infra-upgrades.md).
- **Tripwire:** A CI test that every image line is registered (with a negative control); an hourly drift check that informs the owner (repinning is the owner's decision); an overlay-files-absent test.
- **Port:**
  - `dashboard/backend/src/tests/upgradeStaleRepo.test.ts` — Port after re-check for Fedora/Pi: its tag lookup is Docker Hub-specific; re-target to the registry and pin format the new node uses.
  - `dashboard/backend/src/tests/upgradeImageRegistry.test.ts` — Port after re-check for Fedora/Pi: parses compose image lines; re-target to Quadlet Image= lines.
  - `dashboard/backend/src/utils/composeControl.ts` (tests: dashboard/backend/src/tests/rollbackConsolidation.test.ts; dashboard/backend/src/tests/upgradeRound2.test.ts) — Port after re-check for Fedora/Pi: Docker Compose v2-specific; rebuild for Podman/Quadlet keeping the test assertions.

#### UPG-08 — Machine state never lives in tracked files

- **Rule:** The node's image versions and other machine state live outside version control; a code or image update never changes, blocks on or downgrades them (the newer of the node's pin and the shipped default runs); node-local settings that decide what runs apply by default to every invocation, never through an option each caller must remember; in-app upgrades change only the version pin.
- **Why:** an in-app upgrade wrote the new pin into the tracked compose file, so the code updater either refused (exit 128) or reset the pin, and the next start downgraded the service; a separate pins file was rejected because about 46 call sites would each have had to remember it (2026-10-10-upgrades-survive-code-updates.md).
- **Tripwire:** Planned but not built in the old repository: the effective image list is identical before and after a code update; scratch-clone tests that an upgraded node updates cleanly, keeps its pin and never downgrades.
- **Owner:** C1: option (a), the newer one runs (the node's pin is dropped once the default reaches or passes it); C2: “No other node exists now. So it's OK.”; parked: “Yes, you can park it” — 2026-10-10-upgrades-survive-code-updates.md
- **Superseded / caveat:** Open question C3 (may an in-app upgrade ever edit settings?) is handed to the new repository; the record recommends no.

#### UPG-09 — The node runs exactly the verified artifact

- **Rule:** The node runs from installed, versioned artifacts (images), never from a development checkout or live bind-mounted scripts, and never edits a script a running process is executing; builds come only from committed, clean revisions, with a clean output directory, in a step separate from test builds; after every deploy the running artifact is verified identical to the built one (digest, or `cmp /proc/<pid>/exe`), every process whose code changed is restarted or reported, the previous artifact is kept for rollback, and running services are rebuilt routinely so a security rebuild never carries months of untested changes.
- **Why:** deploys built from the shared working tree shipped another session's uncommitted code (2026-09-26-exact-container-target.md); a control-plane build made before a refactor went live (2026-09-26-memory-restart-asks-for-funds.md), and a release-mode test run replaced the release binaries with test-feature builds that the deploy steps would then have installed (they were rebuilt before any install) (2026-09-28-runtime-alerts-round-two.md); a start script edited in place shifted bytes under LND's running PID 1 (2026-09-25-lesson-gates.md) (+9 more).
- **Tripwire:** The deploy refuses a dirty tree and records the commit; a post-deploy digest or executable comparison; a check that no unit or container references a checkout path; a no-source-newer-than-build check.
- **Owner:** “ok with 2 rules” — 2026-09-25-lesson-gates.md

#### UPG-10 — Migrations and policy versions cannot mismatch

- **Rule:** Configuration migrations are keyed on (from, to), are no-ops inside a release line and are tested on frozen fixtures, never on the live configuration; safety-relevant policy data carries a schema version, the engine refuses unknown safety keys, and the enforcing engine is deployed before the data — including across an image rollback.
- **Why:** an old control-plane binary loaded runbook data carrying a new `hold_for_owner` field and ignored it (2026-09-26-memory-restart-asks-for-funds.md); a migration would have been attempted on every later 0.12.x patch and refused, because its exact-text edits could not match the already-migrated compose file, and its test used the live compose file, so the suite went red once the node was really upgraded (2026-10-03-electrs-0.12-support.md).
- **Tripwire:** Migration tests on a frozen "still on the old line" fixture; a deny-unknown-fields test on safety keys.
- **Port:** `dashboard/backend/src/config/upgradeMigrations.ts` (tests: dashboard/backend/src/tests/upgradeMigrations.test.ts) — Port after re-check: edits compose files; open question C3 (its record recommends that in-app upgrades change only the pin) decides whether it is needed at all.

#### UPG-11 — New versions are characterised against the real node first

- **Rule:** Before a switch, each new service version is characterised in an isolated scratch container against the real backend (kernel and descriptor limits, what it needs from bitcoind); the consumer's real calls are replayed and compared (unordered results as sets); every health-signal source is confirmed to still exist; an index-format change is built alongside the running service under a memory cap and switched only at tip; every other writer of shared data is verified gone; after the upgrade the persistent data path is confirmed to be the mounted volume with the data intact.
- **Why:** Electrs 0.12 exhausted the container's ephemeral ports within 13 s and dropped the metric three readers used for its height, so the health view and self-heal would have gone blind while the upgrade "succeeded" (2026-10-03-electrs-0.12-support.md); ChromaDB 1.x wrote outside the mounted volume, so the knowledge store was wiped on every recreate and a re-ingest hid it (2026-08-08-one-click-infra-upgrades.md).
- **Tripwire:** A scratch-container characterisation checklist per upgrade; a post-upgrade "expected collection or index present" check; the consumer-call replay kept in the repository (it lived only in a session scratchpad).
- **Owner:** “Yes, let it finish and plan upgrade around the ready index. Nice idea to let the test container build .12 index then upgrade onto it. For nodes with limited SSD, we'll have to add a plan around it, next time.” — 2026-10-03-electrs-0.12-support.md
- **Port:**
  - `dashboard/backend/src/services/serviceProbes.ts` (tests: dashboard/backend/src/tests/serviceProbes.test.ts) — Port with tests: add unit tests for the async probe runners (missing in the old repository).
  - `control-plane/src/electrs_phase.rs` (tests: test module) — Port with tests: x86 full node only.

#### UPG-12 — Update progress and outcome are reported truthfully

- **Rule:** Update status treats transitional unit states (activating, deactivating, reloading) as running and gives no verdict while the package or image tool holds its lock; every page shows the current step, elapsed time and steps done and to come, taken from the runner's own state, says "restarting, reconnecting" while the backend restarts, and marks failed or interrupted steps — never an all-green checklist for a failed run.
- **Why:** "Update Linux" reported "17/17 packages still pending" while apt was succeeding (2026-08-19-os-update-false-fail.md); during updates the node looked dead for minutes, and the first progress view showed all green for a failed update (2026-10-09-upgrade-deadlock-and-progress.md).
- **Tripwire:** Runner-state tests that include "activating"; progress-model tests built from a real runner state with failed and interrupted steps.
- **Owner:**
  - Owner spec (paraphrased in the record): a live progress view until a VERIFIED end state — 2026-08-19-os-update-false-fail.md
  - “It would be better to have an indicator showing ongoing update process if possible so the node doesn't look dead.” — 2026-10-09-upgrade-deadlock-and-progress.md
- **Port:**
  - `dashboard/backend/src/tests/runnerActiveState.test.ts` — Port after re-check for Fedora/Pi: apt/dpkg lock semantics; re-derive for bootc/rpm-ostree states.
  - `dashboard/frontend/src/utils/osUpdateProgress.ts` (tests: dashboard/frontend/tests/osUpdateProgress.test.tsx) — Port after re-check for Fedora/Pi: re-derive from bootc/rpm-ostree state.

<a id="fund"></a>
### FUND — Backup, restore and funds safety

*A backup is real only when every destination has it, it is encrypted, and it has been restored.*

#### FUND-01 — Backup health is per destination, by UUID

- **Rule:** Every backup records per-destination outcomes (synced, failed, not connected) for owner-selected destinations identified by filesystem UUID (attached / mounted / writable / free space / last success per drive, re-read on every check); a drive counts only if it received every file; a local copy never counts as a backup; with no drive selected every backup signal reads "unknown"; staleness is measured from the backup job's own last successful write per destination (and scheduler silence separately), never from a source file's mtime; removable media under `/run/media/<user>` are recognised.
- **Why:** backups reported success while drive copies were silently skipped and "Locations: N" counted the node's own disk (2026-09-16-backup-truth-and-alerts.md); the "mounted" signal tested /mnt/backup, a path that was never one of the node's drives, so its alert could never fire (2026-09-17-self-heal-p2-backup-drive-signals.md); after the OS upgrade udisks2 mounted the stick under /run/media and it vanished from detection (2026-10-05-usb-backup-run-media.md); staleness diagnosis read a systemd timer that existed under no name (2026-08-23-runbook-command-audit.md).
- **Tripwire:** Backup-health tests with a replay of the five-week silent failure; drive-signal tests on injected drive lists; a real `lsblk -J` fixture from the target OS.
- **Owner:** “Core fix + test (Recommended)”, “Leave it to the runbook (Recommended)”, “Include it now (Recommended)” — 2026-10-05-usb-backup-run-media.md
- **Port:**
  - `dashboard/backend/src/services/backupHealth.ts` (tests: dashboard/backend/src/tests/backupHealth.test.ts) — Port with tests.
  - `dashboard/backend/src/core/backupDriveSignals.ts` (tests: dashboard/backend/src/tests/backupDriveSignals.test.ts) — Port after re-check for Fedora/Pi: add /run/media and Fedora udisks2 fixtures.

#### FUND-02 — A backup is trusted only after it has succeeded and been restored

- **Rule:** Every backup kind exposes time since its last success and counted skip reasons, alarms when it has never succeeded or keeps skipping, is rehearsed end to end (on a test-network LND) before it is relied on, and a scheduled restore drill proves recovery finds the SCB on the actual selected drive.
- **Why:** the channel.db backup had never succeeded on the node (186 `skipped_no_key`, then 450 `skipped_no_channels`), so the first real channel would be its first run (2026-10-02-channel-backup-after-open-close.md); recovery searched `/media/usb{,1}` for the channel backup, a path the node never used (2026-10-05-usb-backup-run-media.md).
- **Tripwire:** A last-success-per-kind health check; a recorded restore drill.

#### FUND-03 — Only encrypted secrets leave the node

- **Rule:** Only encrypted archives of secrets and wallet material may leave the node (skipped with a visible status when encryption is off); local backup roots are owner-only (directories 0700, files 0600); a restore from the encrypted copy is exercised.
- **Why:** hourly config backups copied plaintext `.env` (RPC passwords, JWT secret, bot tokens) to the USB and SSD drives, and local LND wallet copies sat at 0644 (2026-09-16-backup-truth-and-alerts.md).
- **Tripwire:** "Encrypted-only", "encryption-off skip" and "local 0600" tests (red on the old engine); a live check that only encrypted files reach drives.
- **Owner:** the owner's decision as the record gives it (asked, not quoted): delete the remaining plaintext archives now; no secret rotation (the USB drive never left the owner's possession) — 2026-09-16-backup-truth-and-alerts.md

#### FUND-04 — Channel state is backed up through the SCB on every change

- **Rule:** Lightning channels are backed up through the static channel backup (SCB) immediately on every open, close or pending change and mirrored to the backup drives; SCB freshness is judged against channel changes (a channel-less node's SCB is not stale); channel.db copies never enter a restore path (and the owner is told an old channel.db can trigger a penalty that loses a channel's funds); any full-database copy is debounced, rate-limited, runs detached from its caller and always brings LND back up.
- **Why:** an SCB staleness signal read the file's mtime and was permanently "stale" on a node with zero channels (2026-09-14-guardian-scb-restart-loop.md); 96 plaintext channel.db copies sat on a backup drive (2026-09-16-backup-truth-and-alerts.md); a channel.db backup route stopped LND inside the request, so a hang-up mid-copy left LND stopped (2026-09-28-repairs-outlive-the-request.md); the full channel.db was copied only every 6 h (2026-10-02-channel-backup-after-open-close.md).
- **Tripwire:** Change-watch tests (first reading is a baseline, settle time, minimum spacing); a check that no channel.db copies exist on destinations and that restore tooling refuses them; a cancel-mid-copy test asserting LND is running again.
- **Owner:** “2. channel backup should be made when ever there's changes to its state so 15 min should be right ( also open and close channels).” Choice: “Also channel.db after open/close” — 2026-10-02-channel-backup-after-open-close.md
- **Port:** `control-plane/src/backup/channeldb.rs` (tests: inline Rust tests (files_to_prune, keep_count_from, ChangeWatch)) — Port after re-check: re-check under the current LND; this backup has never succeeded; its first real run is the first channel open.
- **Superseded / caveat:** Whether the new node should stop LND to copy channel.db at all is to be put to the owner again.

#### FUND-05 — Persistent stores never wipe themselves

- **Rule:** Every persistent config store serialises writes, writes atomically (temp file, fsync, rename, mode preserved), keeps a last-good copy, repairs from the first complete document or the last-good copy with an owner alert, and refuses to write a file it cannot read; "quarantine and return the default" is forbidden for such files.
- **Why:** two schedules wrote backup-config.json at 02:00 with no lock; 12 stray bytes made the drive-selection reader return an empty list (the others fell back to silent defaults) and drive backups stopped for five weeks (2026-09-16-backup-device-config-store.md).
- **Tripwire:** A replay of the exact corrupting bytes and of the racing update (both fail on the old code); a file-mode preservation test.
- **Port:** `dashboard/backend/src/services/backupDeviceConfig.ts` (tests: dashboard/backend/src/tests/backupDeviceConfig.test.ts) — Port with tests.

#### FUND-06 — Retention and cadence are explicit and shown truthfully

- **Rule:** Every backup writer prunes to an explicit, configurable retention count after a successful write, touching only its own file pattern and reporting prune failures; schedules and retention shown to the owner are rendered from the scheduler's own constants.
- **Why:** nothing ever deleted channel.db copies (about 229 MB each, in two folders), while Settings promised "every 15 min / 96 copies" and the code ran every 6 h (2026-10-02-channel-backup-after-open-close.md).
- **Tripwire:** Prune-selection and retention-range tests; a displayed-cadence test.
- **Owner:** “Newest 4 (Recommended)” — 2026-10-02-channel-backup-after-open-close.md
- **Port:** `control-plane/src/backup/channeldb.rs` (tests: inline Rust tests (files_to_prune, keep_count_from, ChangeWatch)) — Port after re-check: re-check under the current LND; this backup has never succeeded; its first real run is the first channel open.

#### FUND-07 — Backup drives are handled by what the tools say

- **Rule:** Each backup failure cause maps to its own remedy (scheduler stopped → restart the scheduler; drive attached but unmounted → remount that UUID; read-only or full → tell the owner; never delete on a backup drive automatically); automatic remount runs under an explicit, opt-in, minimal grant verified against the actual service process; eject and mount results are classified from the tool's own words and structured output (`findmnt -J`, `lsblk -J`) after removing labels and paths, never from substrings.
- **Why:** the backup rule proposed restarts for a full drive, and a cleanup runbook targeted `rikuri-backup-*` directories that did not exist while measuring `df /`, the wrong disk; polkit refused the service's remount (2026-09-17-self-heal-p2-backup-drive-signals.md); a stick labelled "not mounted" was reported ejected while still mounted, and `errors=remount-ro,` made a writable stick read as read-only (2026-10-06-eject-outcome-not-from-label.md).
- **Tripwire:** "A full drive is not fixed by a restart" scenario; a permission check against the service's own process; crafted-label eject tests.
- **Owner:** “Let's also fix S11, 13, and 8.” — 2026-10-06-eject-outcome-not-from-label.md
- **Port:** `scripts/rikuri-backup-remount.sh` and `scripts/install-backup-remount-polkit.sh` (tests: dashboard/backend/src/tests/backupRemountScript.test.ts) — Port after re-check for Fedora/Pi: udisks2/polkit on Fedora; never exercised live; the space-in-label follow-up is open.

<a id="ln"></a>
### LN — Lightning operations

*The old mainnet node had no channels whenever a record checked (its testnet LND held the test funds); these are the lessons about LND itself — FUND, SEC and EXEC hold more about money paths — and each must be re-proven on current LND.*

#### LN-01 — Money and chain daemons stop cleanly, and "safe to unplug" is proven

- **Rule:** bitcoind and LND (and Electrs, mempool, tapd) are stopped with their own full grace period on every path (UI, self-heal, cascade, compose), with a command timeout above it; entrypoint wrappers trap TERM and INT, forward the stop to the daemon in every phase (including before its PID is known), wait, pass on its exit status and use interruptible sleeps, and are tested as PID 1 in the real image under the production shell; exit 137 counts as an unsafe stop; the node says it is safe to cut power only when every service holding chain or channel data has stopped with a clean exit.
- **Why:** every stop or restart of LND killed it with SIGKILL — 14 forced kills since 2026-09-18 — because its wrapper forwarded no signal (2026-09-25-lnd-clean-stop.md); Electrs died in 0.1 s on a stop, risking an hours-long index rebuild (2026-09-25-electrs-mempool-clean-stop.md); `docker stop -t 15` overrode the 90 s grace of bitcoind and LND, and the page said "Safe to disconnect power" while testnet LND and tapd still ran (2026-09-30-node-power-buttons.md) (+2 more).
- **Tripwire:** Wrapper tests on the real scripts with fake daemons; a PID-1 probe in the real image (LND went from 10.2 s / exit 137 to 2.2 s / exit 0); safe-to-power-off tests with a running or killed data service.
- **Owner:**
  - “1. yes fix both” — 2026-09-25-electrs-mempool-clean-stop.md
  - “Go ahead and work on the fix for LND stop” — 2026-09-25-lnd-clean-stop.md
  - “Everything with data (Recommended)” — 2026-09-30-node-power-buttons.md
- **Port:**
  - `scripts/electrs-start.sh` (tests: dashboard/backend/src/tests/wrapperStop.test.ts) — Port after re-check for Fedora/Pi: prefer exec or an image-baked entrypoint; re-run the PID-1 probes under Podman.
  - `scripts/mempool-start.sh` (tests: dashboard/backend/src/tests/wrapperStop.test.ts; dashboard/backend/src/tests/mempoolApiMemory.test.ts) — Port after re-check for Fedora/Pi: Podman PID 1 and cgroup v2; x86 explorer only.
  - `scripts/lnd-start.sh` (tests: dashboard/backend/src/tests/lndStartScript.test.ts; dashboard/backend/src/tests/lndTorWait.test.ts) — Port after re-check for Fedora/Pi: production shell and Podman PID 1; re-check rpccookie and cookie-rotation behaviour on the current LND version.
  - `dashboard/backend/src/services/nodePower.ts` (tests: dashboard/backend/src/tests/nodePower.test.ts) — Port after re-check for Fedora/Pi: docker stop / compose calls become Podman and systemd TimeoutStopSec / Quadlet starts.

#### LN-02 — LND automation follows LND's mechanisms and the owner's hold policy

- **Rule:** LND automation uses LND's own mechanisms and stops on a missing precondition (wallet password file, registered watchtower) with the exact remediation for the owner; a stopped LND is restarted automatically, while restarting a running LND for resource reasons is held for the owner; generic resource remediations use an explicit allow-list that excludes funds daemons (LND, tapd) unless the owner opts in; the trusted policy core decides automatic vs held from the exact named target (a missing target is held) and re-checks the condition at run time.
- **Why:** the auto-executing memory runbook would restart whichever container was highest at ≥ 90 % of its limit, so LND was eligible (it did not fire) (2026-09-26-memory-restart-asks-for-funds.md, 2026-09-26-health-exact-container-names.md); runbooks called invented LND routes, one of them to tune watchtower sweep fees on a node with no registered tower (2026-08-23-runbook-command-audit.md).
- **Tripwire:** Owner-hold tests that load the real runbook data (lnd, lnd-testnet and tapd held; other containers automatic; missing target held); a whole-submit test harness (recorded as a gap).
- **Owner:**
  - “Why exclude. Shouldn't the runbook restart LND or is that a double restart?” then “2. Ok, use your suggestion” (2026-09-26): ask first when the picked container holds funds, automatic for everything else — 2026-09-26-memory-restart-asks-for-funds.md
  - “Don't wait for my approval to restart LND.” (2026-09-27) — 2026-09-26-memory-restart-asks-for-funds.md
- **Port:** `control-plane/src/proposal_engine.rs` (owner_hold_reason, runbook_route) (tests: control-plane/tests/runbook_owner_hold.rs) — Port with tests: add the whole-submit harness recorded as a gap.
- **Superseded / caveat:** The old node unlocked LND automatically when a password file existed on disk; the new node must make that choice explicitly.

#### LN-03 — LND health is a level, and starting is not down

- **Rule:** An LND stall is a level condition (synced_to_chain false AND LND's height below bitcoind's AND not advancing over N consecutive checks), followed by one restart and then the owner; a transient "syncing" edge never opens an incident; starting, wallet-locked and unlocking are states distinct from down, and self-heal never restarts LND inside a startup grace period.
- **Why:** momentary "syncing" while LND processed each new block caused 11 unneeded LND restarts (2026-09-24-lnd-sync-stall-misclassified.md); a starting, wallet-locked LND was reported "CRITICAL: down" and the control plane terminated it a fourth time that day (2026-10-08-tests-restarted-live-lnd.md).
- **Tripwire:** Stall-rule tests (12 of 14 failed on the old code; the suite later grew to 16); a test that a wallet-locked LND triggers no restart and no alert.
- **Owner:** “3. Fix without guardian to ask first” — 2026-09-24-lnd-sync-stall-misclassified.md

#### LN-04 — LND follows bitcoind's cookie, once

- **Rule:** LND is restarted after every bitcoind restart (it does not re-read the rotated cookie); exactly one mechanism owns that restart: the cascade skips a dependant whose start time is after the cookie change (unknown start time → restart), logs every skip, stops each container with its own grace, and reports restarted / skipped / failed by name; the behaviour is re-checked on every LND upgrade.
- **Why:** after each bitcoind restart LND restarted itself and the cascade restarted it again 6 s later, with a 30 s stop timeout below LND's 90 s grace (2026-09-26-cascade-skip-restarted.md); a regtest experiment showed LND 0.21.3 failing with HTTP 401 for 2.5+ minutes (3+ in the verifier's re-run) after the cookie rotated (2026-09-26-lnd-rpccookie.md).
- **Tripwire:** Cascade skip-rule tests; an integration test or monitor for LND's 401s after a bitcoind restart, re-run per LND version.
- **Owner:** “2. Ok let control plane skip” — 2026-09-26-cascade-skip-restarted.md
- **Port:** `control-plane/src/cascade.rs` (tests: inline Rust tests) — Port after re-check for Fedora/Pi: reads Docker start times; the live skip was not yet observed when the record closed.

#### LN-05 — LND's onion is verified, not assumed

- **Rule:** LND waits a bounded time (2 minutes) for Tor's control port before starting; if it still starts without its onion the node raises a high alert, and a monitor checks that LND's onion actually answers through Tor, not only that getinfo lists it.
- **Why:** the LND start script probed Tor once and silently started LND without its onion at a boot, at Start All and in Restart All (2026-09-30-node-power-buttons.md).
- **Tripwire:** A test of the Tor-wait block with stub tools; no onion for 10 minutes raises a high alert; two failed SOCKS probes raise an unreachable alert.
- **Owner:** “Wait for tor, then alert (Recommended)”; after a tor restart: “Alert you to restart LND (Recommended)” — 2026-09-30-node-power-buttons.md
- **Port:**
  - `scripts/lnd-start.sh` (tests: dashboard/backend/src/tests/lndStartScript.test.ts; dashboard/backend/src/tests/lndTorWait.test.ts) — Port after re-check for Fedora/Pi: production shell and Podman PID 1; re-check rpccookie and cookie-rotation behaviour on the current LND version.
  - `dashboard/backend/src/utils/lndOnion.ts` (tests: dashboard/backend/src/tests/lndOnionReach.test.ts) — Port with tests.

#### LN-06 — Money operations are never ambiguous

- **Rule:** Every request that pays, sends, opens or closes answers with its real outcome or a pending id the page can look up; no generic watchdog, proxy or client timeout cuts it (exemptions by exact method and path, derived from the handlers that move money, not from route names); the UI never aborts and re-sends a request without an idempotency key; state-changing commands never pass through a response cache.
- **Why:** payments, sends, channel opens and PSBT broadcasts slower than 8 s got "503 request stalled" while they carried on, inviting a double payment, and a rebalancing route that sends payments was not exempt (2026-10-07-money-routes-not-cut-by-watchdog.md, 2026-10-06-health-check-parallel-stats.md); testnet open, close and send were answered from a read cache within its window (2026-10-06-request-values-never-reach-a-shell.md).
- **Tripwire:** A money-routes test with the production lists (30 of 30 mutations red); a default-deny test over the real route table (proposed); a no-abort-and-resend test; a "repeat answered from cache" test.
- **Owner:** “Exempt money routes, own record now (Recommended)” — 2026-10-06-health-check-parallel-stats.md, 2026-10-07-money-routes-not-cut-by-watchdog.md
- **Port:** `dashboard/backend/src/middleware/stallWatchdog.ts` (tests: dashboard/backend/src/tests/stallWatchdogLateReply.test.ts; dashboard/backend/src/tests/moneyRoutesNotCut.test.ts) — Port after re-check: Express-specific; port the tests as the specification.
- **Superseded / caveat:** The lesson "money operation cut by a generic request timeout (ambiguous outcome, double-pay risk)" from 2026-10-06-health-check-parallel-stats.md was later superseded by 2026-10-07-money-routes-not-cut-by-watchdog.md.

#### LN-07 — Fee and price inputs fail loudly

- **Rule:** Code that spends sats (fee bumps, sweeps, channel opens) or converts fiat uses one validated fee or price source, checks HTTP status before parsing, keeps sub-sat/vB precision end to end, carries absence as an explicit null, has no numeric fallback defaults, and refuses when the source fails or the price is stale.
- **Why:** an anchor fee-bump runbook read a nonexistent endpoint whose 404 body was valid JSON, so it fell through to a default of 30 sat/vB against a real 2.11 (about 14×) (2026-08-23-runbook-command-audit.md); real 0.443 sat/vB estimates were rounded to 0 and displayed as "—" (2026-08-22-mempool-page-stale-explorer-and-zero-fees.md); a pricing advisor silently used $100,000 when the price fetch failed (2026-09-29-btc-price-exchanges-first.md).
- **Tripwire:** Tests on the exact live numbers (0.443 / 0.316 must not become 0 or null); no invented fee default in any runbook; USD-to-sats conversion refuses on a stale price.
- **Port:**
  - `dashboard/backend/src/tests/mempoolStalenessAndFees.test.ts` — Port with tests.
  - `dashboard/backend/src/tests/runbookCommandAudit.test.ts` — Port after re-check for Fedora/Pi: its rules name the old endpoints, ports and Docker Compose v1; rewrite the rules for the new catalogue.
- **Superseded / caveat:** A hard-coded fallback price still fed the channel-analytics break-even figure before the first price arrived (recorded, not fixed).

#### LN-08 — Peer data is untrusted, and the program that runs is fixed

- **Rule:** Data from Lightning peers (gossip addresses, aliases) is validated as untrusted before use (only a plain host:port is connected to); lncli and any rebalancer run as argv through one module; which executable runs is never settable by a request, and paths are stored absolute with `~` and globs expanded explicitly.
- **Why:** a gossip address reached an `lncli connect` built as shell text, and a request could set the path of the rebalancing program (2026-10-06-request-values-never-reach-a-shell.md).
- **Tripwire:** Gossip-address validation tests (mutations red); rebalancer-path tests for each legitimate form.
- **Port:** `dashboard/backend/src/services/lncliArgv.ts` (tests: dashboard/backend/src/tests/channelManagerLncliArgv.test.ts) — Port with tests: re-check against the current lncli/LND RPC.

#### LN-09 — Statements about where funds go match the protocol

- **Rule:** Every statement about where channel funds go matches the protocol: the cold (upfront-shutdown) address is paid only by a cooperative close of a channel opened while it was set; a force close pays the node's on-chain wallet after its timelock, and recovering that needs this node or its seed plus the channel backup; the assistant can answer this correctly.
- **Why:** texts in five languages said channel funds "ALWAYS return to your hardware wallet" (2026-09-30-dashboard-page-truth.md).
- **Tripwire:** Per-locale wording tests for "always"; backend reply and route-warning wording tests.
- **Owner:** “correct the language if force closes don't return funds to hardwallet” — 2026-09-30-dashboard-page-truth.md

<a id="exec"></a>
### EXEC — Untrusted input, execution and access control

*Every LAN client, drive, peer and model output is untrusted; nothing they send reaches a shell or a privileged path.*

#### EXEC-01 — No external value reaches a shell

- **Rule:** Every program runs with argv, never through a shell; every value from a request, drive (labels, paths, file names), backup, peer or model is validated at the boundary (allow-lists for enumerations, nothing starting with '-'); lookups never fall back to the raw input; runbook parameters can never become shell code; merges of request data copy own keys only and skip `__proto__`, `constructor` and `prototype`; shell-capable APIs are confined to one module, backed by a ratchet whose blind spots are written down beside it.
- **Why:** `GET /api/upgrades/status/:service`, served without login on the LAN, ran URL values inside `docker inspect` through a shell, and a sweep found 19 of 229 shell-text call sites reachable with untrusted input (2026-10-06-request-values-never-reach-a-shell.md); a drive's label reached shell strings in 8 places, one of them a loginless route (2026-10-05-usb-backup-run-media.md); a value inside a runbook's single quotes ended up unquoted in the shell (2026-09-17-self-heal-p2-honest-executor.md) (+1 more).
- **Tripwire:** Real-execution tests with a sentinel file (created on the old code); a shell-interpolation ratchet probed with alias forms; a syntax-tree sweep of every program launch.
- **Owner:**
  - “Fix all six now (Recommended)” — 2026-10-05-usb-backup-run-media.md
  - “Let's also fix S11, 13, and 8.” Then, on the two questions put to the owner: the assistant's Run = “Allow-listed, no shell (Recommended)”; code with no caller = “Delete after proving unused (Recommended)” — 2026-10-06-request-values-never-reach-a-shell.md
- **Port:**
  - `scripts/quality-ratchet.mjs` and `scripts/quality-ratchet.json` (tests: dashboard/backend/src/tests/requestValuesNoShell.test.ts) — Port with tests: re-baseline from zero and keep its recorded blind spots beside it.
  - `control-plane/src/runbook/templater.rs` (tests: control-plane/tests/fixtures/runbook-template-cases.json) — Do not port as is: the new node should run argv, never templated shell (EXEC-01); keep the fixture's cases as negative tests.
  - `dashboard/backend/src/tests/mountPathNoShell.test.ts` — Port with tests.

#### EXEC-02 — Route policy is default-closed and checked against the real router

- **Rule:** Security policy is a pure, importable, default-closed classifier tested route by route: execution, fund movement, AI spend, credentials (including onion addresses and connection strings) and the local/cloud privacy boundary need action-time owner authentication in every auth mode; it classifies exactly what the router dispatches (case, trailing slash, encoding, dot segments) or routing is strict; every path-based policy is checked against the real route table; loginless access is an exact METHOD /path allow-list of harmless reads reconciled against real callers; tiers follow the direction of risk (declining a change needs no password); every LAN client is untrusted.
- **Why:** re-cased paths such as `/api/Lightning-Mobile/zeus-connection` returned the admin LND macaroon without credentials (2026-08-23-auth-gate-case-bypass.md); fund routes and the AI executor matched no tier (2026-08-23-gate-executor-and-fund-twins.md); after hardening, changing the colour theme asked for the funds password (2026-08-23-loginless-over-gating.md); a public route listed every .onion and the OS username (2026-08-24-stepup-binding-onion-socket-redgate.md) (+3 more).
- **Tripwire:** Classifier tests with benign and negative tables; a re-cased and encoded probe table; a sweep over the real route table with several spellings per route.
- **Port:** `dashboard/backend/src/security/apiAccessPolicy.ts` (tests: dashboard/backend/src/tests/apiAccessPolicy.test.ts) — Port with tests: re-derive the tables from the new route table.

#### EXEC-03 — Action-time credentials are bound and usable

- **Rule:** Step-up tokens are bound to the exact method and path, single-use, and burned on a wrong-route attempt; any action that restarts a funds-adjacent daemon requires server-enforced step-up, derives its target server-side, refuses (409) when its precondition fails and runs one at a time; an expired session opens re-authentication and retries exactly once; every control is exercised end to end in a real browser in the auth mode the node actually runs, and a cancel says "nothing was changed".
- **Why:** a password entered for one benign action produced a token replayable against any step-up route (2026-08-24-stepup-binding-onion-socket-redgate.md); Safe Shutdown, Start All and Restart All were dead in loginless mode, with no initiation logged in 14 days (2026-09-30-node-power-buttons.md); the owner's first nine clicks got "401 Token expired" with no way to log in (2026-09-23-posture-restart-to-apply.md).
- **Tripwire:** Step-up binding tests; a headless check that each button sends its request and raises the confirmation; an expired-session retry-once test.
- **Owner:** “should require password” — 2026-09-23-posture-restart-to-apply.md
- **Port:** `dashboard/backend/src/middleware/stepUp.ts` (tests: dashboard/backend/src/tests/stepUpBinding.test.ts) — Port with tests.

#### EXEC-04 — The server is the only authority

- **Rule:** The UI never renders a security gate the server does not enforce, never recomputes a safety decision locally, and gates every action on the server's answer; each safety control exists in exactly one place; a removed feature takes its routes, navigation, text keys and assistant knowledge with it; warnings state the actual exposure, neither less nor more.
- **Why:** the Terminal page showed a password-and-2FA lock that unlocked itself while its backend had been deleted (2026-08-23-remove-terminal-page.md); the Upgrades page still rendered the green Upgrade button for a consensus-changing release the API had marked not ready, because it recomputed readiness locally (2026-09-20-consensus-upgrade-guard.md); unreachable tabs held a second copy of the AI emergency stop (2026-10-02-cleanups-dead-security-tabs-flaky-test.md).
- **Tripwire:** A render test that the button is absent when the server says not ready (with a control case); a test mapping each UI gate to a server tier (owed); a bundle check for removed features.
- **Owner:** “3. Dead code should be cleaned up if not needed.” — 2026-10-02-cleanups-dead-security-tabs-flaky-test.md

#### EXEC-05 — Authentication fails closed; privileged surfaces are pinned

- **Rule:** Authentication fails closed (a registration failure or an unconfigured secret rejects every request); no endpoint runs repair commands as root; unused privileged routes are deleted, not disabled; a test pins the exact route surface of every privileged process.
- **Why:** an agent's `POST /fix` ran `sh -c` as root behind a no-op auth middleware because no token was configured, and nothing called it (2026-09-17-self-heal-p3-one-monitor.md); websocket authentication shared an error boundary with notifications, so a notification failure would have left sockets unauthenticated (2026-08-24-stepup-binding-onion-socket-redgate.md).
- **Tripwire:** A route-surface test proven red by re-adding the old endpoint; a simulated registration-failure test (owed).

#### EXEC-06 — File routes read only known drives

- **Rule:** Routes that read the filesystem accept only identifiers of drives the node itself detected (404 otherwise, with no read); paths are contained by resolved real path with a separator-aware check, before and after symlink resolution; an out-of-scope target gets the same answer whether or not it exists; filesystem error text goes to the log only; query parameters are type-checked; reads require authorization too.
- **Why:** a drive-browse route listed any directory the backend could read to any LAN client (269 entries under /etc) behind a bare `startsWith` check (2026-10-07-storage-routes-known-drives-only.md, 2026-10-06-eject-outcome-not-from-label.md).
- **Tripwire:** Tests through the real router with real temporary folders (`/etc` → 404; `../BACKUP2` and a symlink out refused); existence-probe tests.
- **Owner:** “Fix now, own record (Recommended)” — 2026-10-06-eject-outcome-not-from-label.md, 2026-10-07-storage-routes-known-drives-only.md
- **Port:** `dashboard/backend/src/tests/storageKnownDrivesOnly.test.ts` — Port with tests.

#### EXEC-07 — Network trust is explicit and narrow

- **Rule:** Every network-trust decision goes through one tested helper that covers IPv4 and IPv6 forms; a loopback source behind a local proxy is never trusted; internal services authenticate with a narrowly scoped machine credential (exact routes, constant-time comparison, read from a 0600 file, failing closed) that cannot send actions or approval payloads; if the owner's nodes exchange messages at all (gap G10), each is authenticated by signature in the handler.
- **Why:** a Mac reaching the node over IPv6 link-local got 136 HTTP 429s while a correct IPv6 helper had no callers — the second incident in the same spot (2026-09-14-rate-limiter-ipv6-lan-trust.md); loopback trust was rejected because the proxy forwards LAN requests from 127.0.0.1 (2026-09-16-rust-alert-delivery-and-owner-token.md); peer node data was accepted with no signature check (2026-08-23-gate-executor-and-fund-twins.md).
- **Tripwire:** An IPv4/IPv6 trust table including the exact link-local address; an internal-token scope test (a valid token on another route gets 401); forged and replayed inter-node message tests (owed).
- **Port:**
  - `dashboard/backend/src/utils/trustedNetwork.ts` (tests: dashboard/backend/src/tests/rateLimiterLanTrust.test.ts) — Port with tests.
  - `dashboard/backend/src/security/internalServiceToken.ts` (tests: dashboard/backend/src/tests/internalServiceAuth.test.ts) — Port with tests.

#### EXEC-08 — Least privilege for the backend and its helpers

- **Rule:** The web backend holds no unrestricted container-runtime access (no docker group, no root socket), and container control goes through a narrow, audited interface; privilege is granted only as exact-path rules on small root-owned wrappers (or dedicated units) that re-validate their arguments; free text passed to a privileged command follows `--`, and a privileged step is proven permitted before an irreversible step such as stopping the stack; probe and sandbox containers are isolated (no network, no data, no new privileges, labelled, swept), and security-monitor exemptions never rest on a name anyone can choose.
- **Why:** the LAN shell injection was root-equivalent because the dashboard user was in the docker group, and a reboot reason of `-c` cancelled the reboot after the stack had already been stopped (2026-10-06-request-values-never-reach-a-shell.md); privilege rules written as argument globs would have stranded every drive operation under a different sudo implementation (2026-08-08-sudo-rs-sudoers-wrappers.md); any root container given the probe-name pattern is exempt from the root scan (2026-10-03-upgrades-cannot-break-a-service.md).
- **Tripwire:** A check that the backend's user cannot reach the runtime socket (owed); an argv test for the reboot command with `--`; a check that every privilege rule is an exact path (owed).

<a id="sec"></a>
### SEC — Secrets and credentials

*Secrets live in dedicated files, never in argv, logs or transcripts, and are rotated when exposed.*

#### SEC-01 — Credentials never leak

- **Rule:** No credential (RPC password, cookie value, token) appears on any command line, exported environment, unit file, log, history or assistant answer; services read secrets from 0600 files (environment files written under umask 077); LND reads bitcoind's cookie by path (`--bitcoind.rpccookie`); logs record templates or ids, never resolved commands; credentials are attached only for an allow-list of exact HTTPS hosts.
- **Why:** LND's command line carried bitcoind's RPC password, readable by `ps` (2026-09-25-lnd-clean-stop.md, 2026-09-26-lnd-rpccookie.md); the owner token gating approvals, chantools and channel.db restore sat in a world-readable unit drop-in (2026-09-16-rust-alert-delivery-and-owner-token.md); testnet RPC credentials reached an unauthenticated execution-history API and chat answers (2026-10-08-assistant-execution-paths.md) (+1 more).
- **Tripwire:** Fake daemons that log their argv and environment; name-only scans of unit files and process flags; a look-alike-host test; the execution log must contain entries, so the no-secret check cannot pass vacuously.
- **Owner:** “4. yes” (2026-09-26), to having LND read Bitcoin's cookie file itself — 2026-09-26-lnd-rpccookie.md
- **Port:** `scripts/lnd-start.sh` (tests: dashboard/backend/src/tests/lndStartScript.test.ts; dashboard/backend/src/tests/lndTorWait.test.ts) — Port after re-check for Fedora/Pi: production shell and Podman PID 1; re-check rpccookie and cookie-rotation behaviour on the current LND version.

#### SEC-02 — Secrets live in dedicated files the agents cannot read

- **Rule:** Secrets live only in dedicated secret files referenced by path, never inline in general configuration; the assistant and coding agents cannot read them and inspect configuration with name-only scans; redaction (tested against quoted, unquoted and export forms) is only a backstop; any secret that reaches a transcript or log is rotated.
- **Why:** an AI session printed the owner token because redaction missed the quoted form (2026-09-16-rust-alert-delivery-and-owner-token.md); a session printed LND's Tor control password while reading lnd.conf for ordinary settings (2026-09-30-node-power-buttons.md), and the password was then rotated (2026-10-02-tor-control-password-rotation.md).
- **Tripwire:** A CI check that non-secret config files contain no password or token keys; a redaction test suite; a guard rule that treats config files with embedded credentials as secret.
- **Owner:** “7. Is rotating LND's tor password is better for security, then yes.” — 2026-10-02-tor-control-password-rotation.md

#### SEC-03 — Secret files: one source, atomic writes, verified rotation

- **Rule:** Each secret has one source; writes to secrets and settings files are atomic (temp file and rename, same mode and owner), touch only the writer's own anchored keys, are serialised by one lock and refuse if the file cannot be read whole; rotation keeps the secret out of argv and output, updates every copy together (in place where a single-file bind mount is used), is verified by an authenticated end-to-end check, and deletes backups that hold the old value.
- **Why:** the Tor control password lived in three files, one of them a single-file bind mount that a new file would not reach (2026-10-02-tor-control-password-rotation.md); 12 scripts and the engine switch edited the root `.env` non-atomically with unanchored patterns (2026-10-10-upgrades-survive-code-updates.md).
- **Tripwire:** Temporary-file tests of the anchored writer (planned, not built, in the old repository); a post-rotation end-to-end check of every onion.

#### SEC-04 — Integrity alarms reach the owner

- **Rule:** Integrity alarms for protected files reach the owner through a delivered channel in plain words (what the file controls, what to do), once per new hash; a legitimate change re-baselines in the same change; the "notified" record is kept separate from the baseline.
- **Why:** every start since at least 2026-08-08 logged CONFIG_TAMPERED for a legitimate model upgrade, only in the log, so real tampering would have looked the same (2026-10-04-config-tamper-notifies-owner.md).
- **Tripwire:** A v1 → v2 → v1 → v2 sequence must notify; the mutant "notified store = baseline" is caught.
- **Owner:** “2. Yes, on both recommendation.” — 2026-10-04-config-tamper-notifies-owner.md
- **Port:** `dashboard/backend/src/security/integrity/configIntegrity.ts` (tests: dashboard/backend/src/tests/configTamperNotify.test.ts) — Port with tests.

#### SEC-05 — Authentication and crypto changes are test-pinned first

- **Rule:** Token verification requires `exp` and `iss`; refusal tests and a real issue-then-verify round trip exist before any auth-library upgrade (red on the old code, green on the new); a major or forced upgrade on an alert or TLS path is read in full and proven live on the real path (authenticate and send nothing), with direct-dependency floors raised.
- **Why:** the control plane accepted a token with no issuer although a comment promised an issuer pin (2026-09-28-runtime-alerts-round-two.md); a mail-library major upgrade was described as needing only a newer Node, though it was a full rewrite (2026-09-28-runtime-dependency-vulnerabilities.md).
- **Tripwire:** Auth refusal tests run against old and new library versions; a mail-transport verify that authenticates and sends nothing.
- **Owner:** “Ok yes” (2026-09-28), to: fix openssl and serde_with, upgrade jsonwebtoken properly with auth tests, record yamux as unreachable, and prove-then-remove ai-orchestrator — 2026-09-28-runtime-alerts-round-two.md
- **Port:** `control-plane/src/auth.rs` (tests: the auth::tests module) — Port with tests.

#### SEC-06 — The dependency audit cannot pass silently

- **Rule:** The dependency gate distinguishes clean (0), findings (1) and could-not-audit (2); it queries a merged advisory source (OSV: RustSec and GHSA) for each locked version, fails on "unsound" as well as vulnerabilities, allow-lists by any alias with a recorded reachability reason, prints allow-list entries that matched nothing, and scans only lockfiles that are actually built and runtime dependencies of code the node runs.
- **Why:** the audit printed "dep-audit clean" and exited 0 with cargo missing from PATH, and read only RustSec while GitHub listed advisories it lacked (2026-09-28-dep-audit-sees-what-github-sees.md); 315 alerts came from 14 lockfiles, two of them read by nothing, and none of the three criticals was in code running on the node (2026-09-28-runtime-dependency-vulnerabilities.md).
- **Tripwire:** Hermetic black-box tests with fake tools and a fake advisory server (13 of 15 red on the old script); run on every push.
- **Owner:** “fix the audit as well” (2026-09-28) — 2026-09-28-dep-audit-sees-what-github-sees.md
- **Port:** `scripts/dep-audit/run.js` and `scripts/dep-audit/allowlist.json` (tests: scripts/dep-audit/run.test.js) — Port with tests.

<a id="ai"></a>
### AI — The assistant and its knowledge layer

*The assistant only plans: it holds no keys or authority, runs nothing without the owner's click, sees exactly what the page sees, and answers from knowledge that is measured and true.*

#### AI-01 — One executor, one click, read-only

- **Rule:** Every path by which the assistant can cause a program to run goes through one executor: a fixed read-only allow-list (refusing names or option values that start with '-', host-switching, remote and follow flags, and reads that reveal secrets such as container environments), argv only, never a shell, and only after an explicit per-command owner click in every mode; labels in data ("autoApprove", "low risk") and claims in guides are never authority; every launch site is inventoried and routed through it.
- **Why:** beside the Run button, chat auto-ran database entries (one was a write), `/api/ai/execute` ran any entry including `docker restart lnd` with no validator, and the agent whitelist accepted reading a private SSH key through `../..` (2026-10-08-assistant-execution-paths.md); the read-only allow-list admitted a `systemctl` flag that opened SSH to another host (2026-10-06-request-values-never-reach-a-shell.md) (+1 more).
- **Tripwire:** Execution-path tests through the real routers with fake launchers (20 of 21 red on the old code); a policy probe table (the old one had 117 probes); nothing is sent on page load in any mode.
- **Owner:**
  - “Click required, auto off” — 2026-10-06-request-values-never-reach-a-shell.md
  - “Own record now (Recommended)” — 2026-10-08-assistant-execution-paths.md
- **Port:** `dashboard/backend/src/services/aiRunPolicy.ts` (tests: dashboard/backend/src/tests/aiRunPolicy.test.ts; dashboard/backend/src/tests/assistantExecutionPaths.test.ts) — Port after re-check: the new assistant is sandboxed; apply the policy to whatever bridge reaches the host.

#### AI-02 — The assistant is contained by the OS, not by parsing

- **Rule:** The assistant runs inside an OS-level sandbox (no secret files, no host shell, scoped writes, no keys or signing authority), and command-parsing guards are only tripwires on top; its tool surface is read-only with per-token scopes on a private network; every mutation is executed by the authoritative control plane, and "dangerous" tools are projected onto the owner's approval queue; private node data never goes to cloud models; no untrusted external text is ingested into assistant-reachable stores unless a reviewed feature needs it.
- **Why:** after eight verifier rounds the command guard still listed forms it cannot see (pipes into `xargs`, code strings, paths built at run time) and called itself a tripwire, not a sandbox (2026-10-04-guard-secret-searches-and-inline-targets.md); a collector pulled GitHub issue text into the assistant's area, raising 20 injection warnings at every start, for no consumer (2026-10-04-remove-mcp-data-collector.md); the agent-gateway plan required read-only defaults and approval-queue projection (2026-09-20-agent-mcp-gateway.md).
- **Tripwire:** A sandbox boundary test proving the assistant cannot read secret files by any command form (owed); a test that no exposed tool is both authoritative and dangerous (planned in the old repository, not built).
- **Owner:** “4. remove collector and unused endpoints.” — 2026-10-04-remove-mcp-data-collector.md
- **Superseded / caveat:** Clarified 2026-10-18 (owner, decision F3 of `docs/architecture/assistant-plan.md`): "private node data never goes to cloud models" stays the default, and the rule for chat and for every action. The owner may enable, off by default, a cloud model for the weekly reflection and for evaluation only; what leaves is redacted by the node's secret filter, bounded, and recorded before the send as a `data_egress` event the owner can see (that plan's contract B5). The code that implements the option is a high-risk change. Further clarified 2026-10-20 (owner, "accept all five."; ADR 0012): the rule still holds for chat and for every action. The one addition is that a typed, sanitized weekly report card, derived from private data as ratios, buckets and relabelled channels with no identifier or absolute amount, may leave in a separate opt-in review lane, shown before each send and recorded (or, after its shadow period and only by the owner's choice, sent automatically each week and still recorded); an optional public lane carries no node data; and a bigger local model on an owner-run machine counts as local only when it is the owner's own and recorded as such.

#### AI-03 — The emergency stop stops everything and needs no password

- **Rule:** The AI emergency stop is enforced at one choke point before every AI route and in every autonomous loop and execution path; it is reachable without a password while resuming needs the owner's step-up; it persists across restarts, fails safe on a corrupt flag, refuses new runs and kills running ones (every run carries a time limit), never reports success for a stopped run, installs a fresh abort signal on resume, and reconciles its audit trail when changed by another path.
- **Why:** with the stop set and status reading `aiOperational: false`, chat still answered and executed tools (2026-08-24-ai-emergency-stop-actually-stops.md); no test covered the stop on the agent path: a mutant of the agent executor that skipped the policy also dropped the stop, and an approved command ran to the end 5.9 s after it and reported success (2026-10-08-assistant-execution-paths.md); a brake that needs a password first is not a brake (2026-08-23-gate-executor-and-fund-twins.md).
- **Tripwire:** Stop tests (survives restart, resume never revives the old signal, corrupt flag fails safe, balanced audit); per-path stop and time-limit tests.
- **Owner:** “Once pressed, the AI should stop what it's doing.” “If reactivated, it shouldn't continue what it was doing.” “Should the activation have a matching deactivation?” — 2026-08-24-ai-emergency-stop-actually-stops.md
- **Port:** `dashboard/backend/src/services/ai/emergencyStop.ts` (tests: dashboard/backend/src/tests/emergencyStop.test.ts) — Port with tests: add mid-flight model-call cancellation (not done in the old node).

#### AI-04 — The assistant sees what the page sees

- **Rule:** The assistant reads node status through the same API and canonical functions as the page; every tool is contract-tested against the real route's response; advice is generated from the node's actual configuration (never "enable pruning" on a txindex node, never txindex-dependent fixes on a pruned node) using the shared severity bands; every issue reaches the context with its own advice exactly once; every value it states carries source and time, says STALE with date and age when old, and prints a missing figure as absent.
- **Why:** the Bitcoin Core tool told the model a synced node with 19 peers was "UNHEALTHY / Sync: down (0.00%) / Blocks: 0 / 0 / Peers: 0" because it read keys the route never had, and advised pruning on a txindex node (2026-09-30-dashboard-page-truth.md); the assistant had no tool that read the health score (2026-09-30-dashboard-measurements.md); it presented an old saved price row as "Current Bitcoin Price", with no date (2026-09-29-btc-price-exchanges-first.md).
- **Tripwire:** Tool wiring tests through the real routes; multi-issue context fixtures; stale-value wording tests.
- **Owner:** “Note doesn't degrade (Recommended)” (disk note); “Same rule (Recommended)” (mempool note) — 2026-09-30-dashboard-page-truth.md

#### AI-05 — Models and binaries are verified before use

- **Rule:** Every downloaded model or binary is fetched to a temporary name, verified against a pinned checksum, moved atomically into a cache outside dependency folders, verified again on load, and a failed load alerts.
- **Why:** an interrupted download truncated the embedding model to 15.0 of 23.0 MB; the canary failed with "Protobuf parsing failed" and 476 indexing failures followed (2026-09-16-self-heal-p0-live-repairs.md).
- **Tripwire:** A checksum-on-load test (planned, not built, in the old repository).

#### AI-06 — Knowledge items reach the model whole

- **Rule:** Every knowledge item shipped to the assistant loads (a dropped item fails CI and is named), fits its budget whole (no silent truncation; existing debt is listed and may only shrink), and the prompt records exactly which items reached the model; budgets are sized so the intended top items fit; no option is accepted but ignored.
- **Why:** the card loader silently dropped cards twice, the second time because the first fix added no gate (2026-08-10-upgrade-reboot-compose-race.md, 2026-09-02-os-update-banner-staleness.md); a 1,500-byte cut ended the reliability card mid-sentence, so the model read the opposite of the owner's rule (2026-09-30-reliability-uptime-truth.md); telemetry listed cards the budget had dropped (2026-10-02-slim-path-searches-docs-when-no-card.md) (+1 more).
- **Tripwire:** An integrity test (red when required fields are stripped); per-item and total budget tests through the real formatter; a telemetry test against the assembled prompt.
- **Owner:**
  - “Shorten cards to fit (Recommended)” — 2026-09-30-reliability-uptime-truth.md; then “Search docs when no card (Recommended)” — 2026-10-02-slim-path-searches-docs-when-no-card.md
  - “Shorten cards to fit (Recommended)” — 2026-10-02-concept-cards-fit-slim-budget.md
  - “We can increase the context window to 3000 bytes, if needed to fit the 2 relevant cars.” — 2026-10-02-slim-path-searches-docs-when-no-card.md
- **Port:**
  - `dashboard/backend/src/tests/conceptCardsIntegrity.test.ts` — Port with tests: if curated cards are kept.
  - `dashboard/backend/src/tests/conceptCardBudget.test.ts` — Port with tests: if curated cards are kept.
- **Superseded / caveat:** The lesson "silent truncation of context fed to the model" from 2026-09-30-reliability-uptime-truth.md was later superseded by 2026-10-02-slim-path-searches-docs-when-no-card.md.

#### AI-07 — Retrieval quality is measured, not assumed

- **Rule:** Retrieval is judged on a labelled question set with a held-out split and targets fixed before tuning, run through the same classifier and thresholds as production, gated in CI and on the node with the real model; thresholds are calibrated on measured score distributions for the specific model and corpus and re-measured when either changes; a missing or weak match triggers document search (a failed search is logged and stated); knowledge changes are verified with owner-phrased questions end to end.
- **Why:** thresholds of 0.5/0.6 assumed a score scale the embedding model never produced, discarding the live store for about 40–70 % of queries while a fallback hid it (2026-09-02-rag-relevance-calibration.md); 10 of 36 uptime questions reached the model with no grounding (first counted as 13; the record corrects it: 3 had a card) (2026-10-02-slim-path-searches-docs-when-no-card.md); "Where is the Terminal page?" got "no information" although retrieval ranked the answer first (2026-08-23-remove-terminal-page.md) (+1 more).
- **Tripwire:** A labelled question set (the old one: 242 questions, every third held out) with accuracy floors; when the embedder is down, ranking falls back to words and logs it; a full-pipeline evaluation (owed).
- **Owner:**
  - “We can increase the context window to 3000 bytes, if needed to fit the 2 relevant cars.  If better match is not ranked first, what does that mean?  Our ranking is wrong or is using some other criteria than match?” — then chose “Fix the word-matching (Recommended)” — 2026-09-30-reliability-uptime-truth.md
  - “Search docs when no card (Recommended)”; later “Card + docs when weak (Recommended)” — 2026-10-02-slim-path-searches-docs-when-no-card.md
  - “Blend word + meaning (Recommended)” — 2026-10-02-slim-path-searches-docs-when-no-card.md (the record notes that it supersedes the earlier "Fix the word-matching")
- **Port:**
  - `dashboard/backend/src/ai/retrievalRelevance.ts` (tests: dashboard/backend/src/tests/ragRelevanceCalibration.test.ts) — Port after re-check: the values belong to all-MiniLM-L6-v2 on the old corpus; port the calibration procedure and re-measure for the new model.
  - `dashboard/backend/src/ai/slimKnowledge.ts` (tests: dashboard/backend/src/tests/slimKnowledge.test.ts; dashboard/backend/src/tests/cardBlend.test.ts; dashboard/backend/src/tests/cardRanking.test.ts; dashboard/backend/src/tests/fixtures/card-questions.json; dashboard/backend/src/scripts/cardRankingCheck.ts) — Port after re-check: re-measure with the new model; the full-pipeline evaluation is still owed.

#### AI-08 — Knowledge is shaped for the retriever

- **Rule:** Knowledge is written as short sections under question-shaped headings that lead with the answer (history under its own heading), each within the embedder's window measured with its own tokenizer (target ≤ 450 tokens, never over 512).
- **Why:** a 751-token section lost the owner's new choices to truncation, and correction files without headings became single unretrievable chunks (2026-09-30-dashboard-measurements.md); "why is the volume so low" was buried inside a long chunk (2026-09-29-market-cap-volume-etf-warm.md) (+1 more).
- **Tripwire:** Per-section token counts from the embedding server's tokenizer; a top-3 retrieval table for named owner questions.

#### AI-09 — Knowledge is true to the code

- **Rule:** Every claim in the assistant's knowledge about the node is verified against the code with file and line, re-reviewed when that code changes and fixed in every store that carries it; every control it names exists, and its stated capabilities match its registered tools; commands come from one catalogue that CI checks against real scripts, units, endpoints and pins; when a safety-relevant fact changes, the live store is corrected and a query proves the old advice returns nothing; money-safety facts (where a force close pays) are answerable.
- **Why:** the assistant advised upgrading Knots to a fork build that leaves the Bitcoin chain (2026-09-20-knots-repin-and-gate.md); the command store cited downgrading overlays, and 42 of 77 entries were make targets with no Makefile (2026-08-22-rollback-consolidation.md); cards claimed closing channels sweeps to the cold wallet, and "Does a force close send my funds to my cold wallet?" got no answer (2026-10-02-concept-cards-fit-slim-budget.md); guides named controls that do not exist (2026-09-30-dashboard-page-truth.md).
- **Tripwire:** A search for each known-false phrase across every store; live queries for the safety questions; a knowledge lint resolving each named control to a UI label (suggested).
- **Superseded / caveat:** The lesson "assistant knowledge describes nonexistent or dangerous commands" from 2026-08-22-rollback-consolidation.md was later superseded by 2026-08-23-runbook-command-audit.md.

#### AI-10 — The index matches the deployed revision

- **Rule:** The knowledge index is built from the deployed revision as part of the same deploy (stamped with the commit), after the last edit; every document is keyed on a unique identity; deleted sources are removed and the store reconciled against the files, but a prune runs only on a complete view of the source; indexed and stored counts are compared after every ingest; a failed ingest is a visible health finding.
- **Why:** three files named glossary.md overwrote each other, so the Bitcoin and Lightning glossaries were missing (2026-10-02-knowledge-store-one-name-one-guide.md); the document watcher indexed working-tree text describing behaviour the running node did not have (2026-09-30-dashboard-page-truth.md, 2026-10-06-request-values-never-reach-a-shell.md); an ingest failed silently because the vector store had been stopped (2026-10-02-concept-cards-fit-slim-budget.md).
- **Tripwire:** A unique-names test; stale-source and safe-to-sweep tests; a post-deploy query (new text found, zero chunks of the old).
- **Owner:** “1. Make the 2 glossaries if that's what's needed.” — 2026-10-02-knowledge-store-one-name-one-guide.md
- **Port:**
  - `dashboard/backend/src/tests/docNamesUnique.test.ts` — Port with tests.
  - `dashboard/backend/src/ai/ragSources.ts` (tests: dashboard/backend/src/tests/ragSources.test.ts; dashboard/backend/src/tests/ragSweepSafety.test.ts) — Port with tests.

<a id="test"></a>
### TEST — Testing, verification and development discipline

*How the new node is built and verified: tests that cannot touch the node, checks that are proven to fail, and evidence taken from logs.*

#### TEST-01 — Tests can never reach the live node

- **Rule:** Before any test worker starts, the harness puts refusing stand-ins first on PATH for every node-changing program and points the container-runtime socket at a path that does not exist; production code resolves such programs through one overridable resolver (no absolute paths); every runtime file and lock resolves from one configurable root that tests point at a per-worker temporary directory; production write paths refuse under test outside it; tests have no production default endpoints and never mutate process-wide state concurrently; isolation is proven from a child started the way production code starts one; state-changing routes are verified by unit tests, never probed on a live node; mutation testing never runs on a production machine without this layer.
- **Why:** mutation runs of the assistant's Run tests terminated the live mainnet LND four times in one day (three by mutation runs, a fourth as a knock-on) (2026-10-08-tests-restarted-live-lnd.md); tests wrote 90 fake outcomes into the live outcomes database and 93 fake entries into the owner's Activity log (2026-09-16-backup-truth-and-alerts.md, 2026-10-06-request-values-never-reach-a-shell.md); a test rewrote the live Knots bitcoin.conf (2026-09-20-postures-per-engine.md) (+7 more).
- **Tripwire:** A global setup with stand-ins (exit 126) and a missing runtime socket, proven against the exact incident with an outer logging layer; a scan of tests for absolute paths to refused programs; a scan for lock-taking scripts run without their lock location; live data checksums unchanged across a full run.
- **Owner:** “5. Clean the flaky Rust test. If not needed then delete/clean.” — 2026-10-02-cleanups-dead-security-tabs-flaky-test.md
- **Port:**
  - `dashboard/backend/src/tests/setup.ts` — Port after re-check: Jest-specific; replicate in whatever harness the new node uses.
  - `dashboard/backend/tests/noLiveNode.globalSetup.js` (tests: dashboard/backend/src/tests/testsNeverReachTheLiveNode.test.ts) — Port after re-check: Jest-specific; the Rust test runner needs an equivalent; not network-hermetic.

#### TEST-02 — A check counts only after it has been seen to fail

- **Rule:** Every regression guard, gate and acceptance check is shown red against the pre-fix code (or a planted mutation) and against plausible broken fixes (commented out, short-circuited), and green on legitimate variants, before it counts; mutation runs happen on a scratch copy, never the live tree; surviving mutants are killed or recorded as equivalent with proof; every probe is shown to succeed against a known-positive case before its negative result is trusted; tests that pass both ways are labelled characterisation.
- **Why:** a verifier found 30 of 79 mutations still green (2026-09-30-dashboard-page-truth.md); the first button-style gate passed on the very bug it was written for (2026-09-20-invisible-buttons.md); "the port stays closed while indexing" came from a probe that could never succeed (2026-10-03-electrs-0.12-support.md); a live check for the missing WebSocket route could not fail because the broken config answered 200 (2026-10-06-nginx-socket-io-location.md) (+3 more).
- **Tripwire:** Red runs and mutation results recorded per change.

#### TEST-03 — Tests assert what the owner experiences, through the real entry point

- **Rule:** Tests assert effective behaviour ("this request requires step-up", "the legitimate command actually runs") through the entry point that applies it, assert that the path under test was reached, use fixtures from the producer's real outputs including failure shapes, use fixed data rather than today's, and use fakes that model descriptor inheritance, process parentage and timing; load and resolve checks use the production runtime's resolver; readiness after a restart requires evidence of the new process.
- **Why:** a test asserted a tier label and passed while the emergency stop still demanded a password (2026-08-23-gate-executor-and-fund-twins.md); a test pinned the hold function but not that the submit path called it (2026-09-26-memory-restart-asks-for-funds.md); the assistant's Run button ran nothing because of a wrong field name, and no test drove a legitimate command (2026-10-06-request-values-never-reach-a-shell.md); the test resolver found files plain Node would not (2026-10-04-remove-model-warmup-and-post-ibd.md) (+5 more).
- **Tripwire:** A bypass mutation must turn a test red; "path exercised" assertions; a simulated next periodic review passes the suite.
- **Port:** `dashboard/backend/src/tests/startupBrokenCodeRemoved.test.ts` — Port after re-check: Node-specific resolver check.

#### TEST-04 — Stop the line; never weaken a gate

- **Rule:** A red ratchet or required gate stops the line and is attributed per file at once; baselines move only through real fixes and only from HEAD's counts; a failing gate is satisfied by fixing the source, never by an exemption or a shrunk scope; every test runs in CI under the standard runner (excluded tests ratcheted to zero) and all test projects share one include/exclude source; an intentionally empty selection uses a never-matching sentinel; each gate asserts it examined a non-zero number of files per language, and a scan that finds nothing to guard fails.
- **Why:** a ratchet sat red across sessions and was called "pre-existing" (2026-08-24-stepup-binding-onion-socket-redgate.md), and 43 test files had been outside CI, one aiming 20 of 23 assertions at a deleted module (2026-09-14-script-style-test-conversion.md); frontend lint matched only .js/.jsx, so every "lint 0" proved nothing for TypeScript (2026-09-30-dashboard-page-truth.md); a pin gate nearly passed by exempting the very file it flagged (2026-09-20-relay-profiles-c1.md) (+1 more).
- **Tripwire:** A quality ratchet with locked floors; a file-count assertion per gate step; scans over git-tracked files that fail on zero matches.
- **Owner:** Owner decision (2026-09-14, same session): delete the file (fsmEngine.test.ts) — the record's account; before deleting, its 3 surviving assertions were checked to duplicate existing coverage — 2026-09-14-script-style-test-conversion.md
- **Port:** `scripts/quality-ratchet.mjs` and `scripts/quality-ratchet.json` (tests: dashboard/backend/src/tests/requestValuesNoShell.test.ts) — Port with tests: re-baseline from zero and keep its recorded blind spots beside it.
- **Superseded / caveat:** The lesson "test-runner projects diverge and a red gate is misattributed" from 2026-08-24-stepup-binding-onion-socket-redgate.md was later superseded by 2026-09-14-script-style-test-conversion.md.

#### TEST-05 — CI status is current, complete and proven

- **Rule:** CI installs every workspace package's locked dependencies from a fresh clone; the local gate fails when the branch's latest CI run is red, warns when it cannot tell, and accepts only a run for the current commit (re-querying before reporting failure); every scheduled gate is monitored for a recent successful run; the gate records which check failed, with its evidence; deploys are gated on the test runner's own exit code; every change is followed by the full gate, not a chosen subset.
- **Why:** CI was red for 7 weeks and nothing said so (2026-09-23-ci-shared-deps.md); a weekly audit lived on a non-default branch and never ran once (2026-09-28-runtime-dependency-vulnerabilities.md); the backend was deployed with a failing suite because the pipeline's status was that of `tail` (2026-09-26-mempool-api-memory.md); a one-word knowledge edit broke an unrelated ranking test (2026-10-02-channel-backup-after-open-close.md) (+3 more).
- **Tripwire:** A CI-status check with FAIL and WARN drills; a "scheduled gate ran within 8 days" check (proposed); a deploy script that runs the gate under pipefail.
- **Owner:** “Yes, go ahead with both 1 and 2 first” (2026-09-28) — (1) make cleanup/main the default branch, (2) fix the real runtime list as one tracked change — 2026-09-28-runtime-dependency-vulnerabilities.md

#### TEST-06 — Commit exactly what was tested

- **Rule:** Commit gates run on an export of exactly the index; commits stage by explicit path and are reviewed for deletions; one coherent change lands with its record in one commit, rebuilt on the current HEAD; when work is split across parallel agents, one coordinator owns shared manifests, and agents are told up front which files they may not touch.
- **Why:** broad staging swept in another session's deletion, so committed routing pointed at a deleted rule for 11 days (2026-09-17-drb-schema-gate.md); twice a gate passed locally and failed in CI because of another session's uncommitted edits (2026-10-04-gates-run-on-the-commit.md, 2026-10-03-upgrades-cannot-break-a-service.md) (+1 more).
- **Tripwire:** A pre-commit hook that exports the index (red on the old hook); a staged-deletion and out-of-scope check (suggested).
- **Owner:** “Ok to run gattes on the commit itself, not on working tree of other sessions and pre-commit step” — 2026-10-04-gates-run-on-the-commit.md
- **Port:** `.githooks/pre-commit` (tests: dashboard/backend/src/tests/precommitGatesOnIndex.test.ts) — Port with tests.

#### TEST-07 — Evidence is taken from logs, not memory

- **Rule:** Every change carries its build record and evidence in the repository at commit time; every time, count and status in a record is read from a log, transcript, mtime or command output (dated, with units and source), counted by script over the full output (never judged through `head`) and re-checked on the final text; an edit tool's success is not evidence the change applied; an unmet acceptance criterion is amended openly; a required check that could not run stays "not yet proven" with an owner, and only the owner may accept that risk.
- **Why:** the sudo-rs build record was written 25 days later by another session (2026-08-08-sudo-rs-sudoers-wrappers.md); verifier rounds 2 to 6 failed one record on its wording and figures alone (2026-09-26-mempool-api-memory.md); `head` hid one of 133 uses in a survey (2026-09-28-fix-lock-covers-inline-tests.md); an edit matched nothing yet reported success (2026-08-24-stepup-binding-onion-socket-redgate.md) (+2 more).
- **Tripwire:** An independent verifier re-reads every number; records carry a units and time-zone header.
- **Owner:** “Accept as is.  commit and push.” — 2026-10-04-guard-secret-searches-and-inline-targets.md

#### TEST-08 — Debug by evidence

- **Rule:** Before touching a broken system, preserve the broken artifact and capture its state; confirm a root cause by measurement before recording it, and correct a wrong diagnosis where it was first recorded; check every claim about architecture against the running system and the code that routes the behaviour; prove a fix by watching the mechanism decide correctly (a true positive and a true negative) when it is known to fire, over a window longer than the failure period; sweep a defect class by structure (syntax tree, data flow), not by names.
- **Why:** one quiet cycle was taken as proof that a dashboard restart loop was fixed; two days later its unit's restart counter read 75, with 56 more firings of the backup rule that day (2026-09-14-guardian-scb-restart-loop.md); a committed diagnosis blamed a formula that measurement showed was correct (2026-09-02-rag-relevance-calibration.md); name-based sweeps missed a regex form and an eighth loginless shell site (2026-10-05-usb-backup-run-media.md) (+2 more).
- **Tripwire:** A live monitor across the predicted firing time; class sweeps backed by a default-deny tripwire.
- **Owner:**
  - Decision Q0 of the owner-approved plan, as the record summarises it: repair all three by hand first (the plan, at 883d8285: Q0 — Repair the live breakages by hand first: YES) — 2026-09-16-self-heal-p0-live-repairs.md
  - “Include it now (Recommended)” — 2026-10-05-usb-backup-run-media.md

#### TEST-09 — Delete only what is proven dead

- **Rule:** Before deleting code, prove it dead symbol by symbol against every mount and import point, every name it goes by (folder, product name, environment variables, ports, units) and the live system; a global asset such as a stylesheet is deleted only after each selector is proven unused and the built bundle is diffed; a behaviour-neutral refactor is proven by identical suite and test counts and a clean build; code that existed only for a replaced dependency is removed with it.
- **Why:** three "that's dead" verdicts in one session were wrong, one of which would have deleted two live endpoints (2026-08-23-runbook-command-audit.md); deleting a dialog's stylesheet removed styles from 31 components (2026-09-30-dashboard-page-truth.md); a deadness proof missed port reservations (2026-09-28-runtime-alerts-round-two.md); a model warm-up written for the old model server logged a failure at every start after the switch (2026-10-04-remove-model-warmup-and-post-ibd.md) (+1 more).
- **Tripwire:** Test-count equivalence (stop on any drop); a rule-by-rule diff of the built stylesheet; a dead-export check (suggested).
- **Owner:** “1. Delete warm-up; why does it need warmup? … 3. Remove” — 2026-10-04-remove-model-warmup-and-post-ibd.md

#### TEST-10 — The UI is verified by real renders

- **Rule:** Owner-facing pages are checked by rendering tests through the real components (each guarded behaviour mutation-proven) and by headless renders at phone, tablet and desktop widths (nothing past the edge, no raw text key); tests check that every style variable used is defined by every theme and every button has a globally defined style; the build fails when any text key is missing from any shipped language, and wording and safety tests run in every language.
- **Why:** the relay-posture buttons were effectively invisible, so the owner concluded the choice did not exist (2026-09-20-invisible-buttons.md); a border colour variable was used 243 times but defined by no theme, and channel-open errors showed raw keys (2026-09-30-dashboard-page-truth.md); every visible defect the owner found in one panel was a rendering defect data tests could not see (2026-09-22-posture-panel-frontend-test.md) (+1 more).
- **Tripwire:** Headless renders at 320–1,920 px; theme-variable and text-key tests.
- **Owner:** Borders: “Turn them on (Recommended)”; phone menu: “Yes, in its own record (Recommended)” — 2026-09-30-dashboard-page-truth.md

#### TEST-11 — The AI-session guard covers every way around it

- **Rule:** The development guard protects every way of disabling it (local settings, its directories and state, wildcard deletes); covers test code inside source files and every write path (shell, interpreter heredocs, inline code) or forbids what it cannot see; judges what a recursive command will actually read (honouring excludes) but never reads the files a command runs; models the tool's exact edit behaviour; runs under a wall-clock budget that ends in ask or deny and never allows after a timeout; never drops a check the previous version made (a differential test against a frozen copy); is drilled live through the real hook; refuses or warns when a session edits a repository whose guard is not active; lists its known gaps beside it; and fixes are confirmed by comparing the "N passed" count before and after.
- **Why:** writing a local settings file or deleting the guard's state silently disabled it or released the lock (2026-09-25-guard-self-disable-hole.md); a rewrite silently dropped six money-move checks (2026-10-04-guard-secret-searches-and-inline-targets.md); interpreter heredocs wrote test code while the lock was engaged (2026-10-03-fix-lock-per-session.md, 2026-10-05-guard-interpreter-writes-inline-tests.md) (+3 more).
- **Tripwire:** Worked examples per repository replayed by the shared guard tests; a differential generator over every config example (the old one: about 70,000 variants, none looser); guard files byte-identical across repositories.
- **Owner:**
  - “Yes, go ahead and close the hole.” — 2026-09-25-guard-self-disable-hole.md
  - “Ok for fix to the gurad” (2026-09-28) — 2026-09-28-fix-lock-covers-inline-tests.md
  - “Add rikurinode's guard here (Recommended)” — 2026-09-30-dashboard-page-truth.md
  - “Yes, should not be allowed to search or look into .env without permission.” — 2026-10-04-guard-secret-searches-and-inline-targets.md
  - “5 Ok and fix false positive.” — 2026-10-04-guard-secret-searches-and-inline-targets.md
  - “2. Ok fix the Guard gap.” — 2026-10-05-guard-interpreter-writes-inline-tests.md
- **Port:** `.claude/hooks/guard.py` (tests: .claude/hooks/test_guard.py; .claude/hooks/guard-config.json (inline_tests rule)) — Port with tests: copy unchanged (byte-identical across Full-tier repositories) and write a repository-specific guard-config.json.
- **Superseded / caveat:** Development tooling for the rebuild repository, not node runtime. The lesson "guard can be switched off through an unprotected side channel" from 2026-09-25-guard-self-disable-hole.md was later partly relaxed by 2026-09-26-guard-owner-relaxations.md (the settings files still ask); the lesson "write hidden inside inline interpreter code bypasses a path-based guard" from 2026-10-03-fix-lock-per-session.md was later refined by 2026-10-04-guard-secret-searches-and-inline-targets.md (a false-positive fix; the bypass lesson stands).

#### TEST-12 — Guard strictness belongs to the owner, logged and scoped

- **Rule:** The guard is deterministic, fails to "ask" on its own errors, and has tests that routine commands stay silent; strictness is a one-command, logged profile in committed config in which money-moving, irreversible and secret-exposing asks always survive and denies never relax; relaxing is an explicit owner choice with its costs stated beforehand, scoped, reversible, with relaxed actions logged; test locks are per session, engaged only after the repository's preflight passes, released as their own step after an observed green run, and one session never releases another's lock.
- **Why:** every rule for AI coding sessions had been advisory (2026-09-22-ai-native-sdlc-controls.md); control-plane restarts waited about 11 h and 6 h in an approval prompt (2026-09-27-control-plane-restart-free.md); one shared lock file blocked parallel sessions and `off` released anyone's lock (2026-10-03-fix-lock-per-session.md); locks were released in the same command as the test run, before its result (2026-10-06-nginx-socket-io-location.md) (+4 more).
- **Tripwire:** Every worked example replayed under both profiles; "every release is logged" test; per-session lock tests; a failing preflight leaves no lock.
- **Owner:**
  - “implement Claude SDLC's procedure from now on for projects that make sense.” — 2026-09-22-ai-native-sdlc-controls.md
  - “ok with 2 rules” — 2026-09-25-lesson-gates.md
  - “Can we release the fix-lock, allow restart LND/bitcoin/tapd; edit guard, or CI from requiring permission?” … “We'll put these back on when appropriate” — 2026-09-26-guard-owner-relaxations.md
  - “Ok yes, make the one line change.” (2026-09-27) — 2026-09-27-control-plane-restart-free.md
  - “I think for now we'll just follow the Auto mode for Claude or Codex. It's too restrictive the way I set this up.” … “They need to be able to adjust this permission system easily. These restrictions are more suited for something close to completion.” Chosen: development still asks only before money moves (the option's description, the session's words: sending funds or payments, Iceman live trading, deleting wallet or chain data); all four repos switch now. — 2026-09-27-guard-profiles.md
  - “4. Let's not share fix-lock.” — 2026-10-03-fix-lock-per-session.md
- **Port:** `.claude/hooks/guard.py` (tests: .claude/hooks/test_guard.py; .claude/hooks/guard-config.json (inline_tests rule)) — Port with tests: copy unchanged (byte-identical across Full-tier repositories) and write a repository-specific guard-config.json.
- **Superseded / caveat:** Development tooling; the record says the funds-daemon restart gate should be raised again when mainnet channels open. The lesson "advisory-only rules for AI sessions" from 2026-09-22-ai-native-sdlc-controls.md was answered in that record (the guard replaced advisory rules), and 2026-09-26-guard-owner-relaxations.md later loosened some of the guard's asks; the lesson "approval gate latency stalls routine work" from 2026-09-27-control-plane-restart-free.md was later superseded by 2026-09-27-guard-profiles.md.

<a id="plat"></a>
### PLAT — Platform specifics: Fedora IoT, Raspberry Pi 5, bitcoind, Tor and containers

*Mechanics the old Ubuntu/Docker node got wrong, which must be re-verified on the new platforms.*

#### PLAT-01 — The host is defined by the image

- **Rule:** OS identity comes from /etc/os-release; every OS package the node relies on is declared in the image; every host configuration file it depends on is produced by the image and asserted (never hand-edited on one machine) and regenerated when hardware changes; mDNS publishes only on an allow-list of physical interfaces derived at runtime, refuses to write an empty list, and restores its config if the name resolves to anything but the LAN address.
- **Why:** the node's `.local` name resolved to a container bridge address after container churn, because the deny-list could never name bridges whose ids change, and the avahi config had been hand-edited outside the installer (2026-09-03-mdns-local-name-docker-bridge.md); code hard-coded an Ubuntu repository path and relied on a tool absent from minimal installs (2026-08-08-sudo-rs-sudoers-wrappers.md).
- **Tripwire:** Allow-list tests (mutation: a block-list fails); os-release fixtures for every supported OS; an image test asserting the shipped host config.
- **Port:** `scripts/rikuri-mdns-interfaces-fix.sh` (tests: dashboard/backend/src/tests/mdnsInterfaceAllowlist.test.ts) — Port after re-check for Fedora/Pi: should ship in the Fedora IoT image; verify interface naming under Podman.

#### PLAT-02 — Host probes are verified on the target OS and hardware

- **Rule:** Host probes use invocation forms verified on the target OS version, parse output with tested pure functions against fixtures captured there (structured JSON where available, both forms where versions differ), and treat empty output as a probe failure; CPU temperature comes from a CPU sensor (Pi 5 `cpu_thermal`; x86 k10temp or coretemp) with its own bands, never a Wi-Fi or ACPI zone; disk usage of an unreadable data path is read through its mount point, and every failure logs its real error.
- **Why:** the NTP probe printed nothing on that systemd version, so clock sync read false for months (2026-09-16-owner-notification-delivery.md); "Temp 60 °C" was the Wi-Fi card, a rewrite dropped Pi temperature, and the chain disk read "unknown" because its volume path was unreadable to the service (2026-09-30-dashboard-measurements.md); a newer util-linux printed booleans where the parser expected '1' (2026-10-05-usb-backup-run-media.md).
- **Tripwire:** Fixtures captured on Fedora IoT (x86 and Pi 5) for timedatectl, lsblk, findmnt, hwmon and thermal zones.
- **Owner:** “Yes, in fact, check all measurement on the Dashboard. Make sure every one of them is actually meansuring the right thing and is correctly measuring what it's suppose to.” Choices: “'No sensor', no cap”; Guardian heat alert uses the “Dashboard's 'hot' band” — 2026-09-30-dashboard-measurements.md
- **Port:** `dashboard/backend/src/services/hostMetrics.ts` (tests: dashboard/backend/src/tests/hostMetrics.test.ts) — Port after re-check for Fedora/Pi: capture fixtures on the Pi 5 and the new x86 hardware.

#### PLAT-03 — The runtime ships with the application

- **Rule:** The application runtime and its native modules ship together inside the image or container, not from host packages; every OS or image change is followed — as a boot health check that can trigger rollback — by loading each native module with the exact runtime and scanning for load-error signatures, replaced binaries and core dumps; a runtime major version passes the full suite before it reaches the node; each native dependency has one version across the repository; OS upgrades have a pre-flight (clean stop, fresh channel backup) and a post-check of privilege grants, firewall, runtimes, services and smoke.
- **Why:** the Ubuntu 26.04 upgrade replaced the Node runtime under a natively compiled database module; the node registry and incident closing failed while the health endpoint said 200 and smoke stayed green, and on the next runtime the old module core-dumped the dashboard (2026-10-03-ubuntu-26.04-upgrade.md, 2026-10-03-smoke-catches-broken-native-modules.md).
- **Tripwire:** The smoke native-module drills (red on the real failure lines), re-expressed as greenboot checks.
- **Owner:**
  - “5. Yes add smoke check.” — 2026-10-03-smoke-catches-broken-native-modules.md
  - Node 22 from NodeSource (the owner's choice as the record gives it); then “maybe we should have moved to Node 24” — 2026-10-03-ubuntu-26.04-upgrade.md
  - “We need to upgrade linux to 26.04.1 LTS with kernel 7.0.” — 2026-10-03-ubuntu-26.04-upgrade.md
- **Port:** `scripts/smoke.sh` (section 1b) (tests: drill overrides (SMOKE_NATIVE_DIRS, SMOKE_DASH_SINCE)) — Port after re-check for Fedora/Pi: Node/better-sqlite3-specific; re-express as greenboot boot checks.

#### PLAT-04 — Resources are sized from the hardware, in one place

- **Rule:** Container limits and runtime heaps are derived from the local hardware on every start path, from one documented source of truth (heap from the container's own cgroup memory.max); an operator override wins or is reported as ignored; memory decisions use the working set (excluding reclaimable cache) and also watch limit hits and swap; indexers and explorers have bounded growth rather than ever-higher ceilings; descriptor limits are explicit; whether the full explorer fits a memory tier is decided per node.
- **Why:** mempool-api crash-looped 305 times on a default heap, and then again at exactly the raised ceiling (2026-08-10-bip110-invalid-mark-leak.md, 2026-08-16-mempool-oom-recurrence.md); container size and heap were set in different places and the container hit its limit 21,921 times (2026-09-26-mempool-api-memory.md); six containers ran at default limits after partial recreates (2026-10-03-upgrade-gates-round-2.md) (+1 more).
- **Tripwire:** Heap-from-cgroup tests on a fake cgroup file; working-set tests (cgroup v1 and v2); a startup comparison of configured overrides with effective limits.
- **Owner:**
  - A standing rule in the record, which does not say who set it: if this OOMs again, stop raising ceilings and bound the growth instead — 2026-08-16-mempool-oom-recurrence.md
  - First approval “1. Ok with your proposal” (alert only at >=95% for 3 checks in a row; restart mempool-api itself, never the heaviest container; no CPU alert); after the investigation, chose “Heap follows limit” — 2026-09-26-mempool-api-memory.md
  - “Fine with 95% limit for now.” (2026-09-27, on measuring the 95% as docker stats shows it) — 2026-09-26-mempool-api-memory.md
  - “The original memory limit for each service depends on the size of RAM for a node … if there is only 8 or 16 GB, that needs to be limited or controlled. Not sure what .env has.” (2026-09-27) — 2026-09-26-mempool-api-memory.md
  - “Just leave them. We have enough RAM. If we were doing this as and upgrade for other nodes, then we'll need to keep RAM usage based on the local hardware. Keeping the node running as much as we can, while upgrading. Shotdown or reduce RAM usage if necessary.” — 2026-10-03-upgrade-gates-round-2.md
- **Port:**
  - `scripts/mempool-start.sh` (tests: dashboard/backend/src/tests/wrapperStop.test.ts; dashboard/backend/src/tests/mempoolApiMemory.test.ts) — Port after re-check for Fedora/Pi: Podman PID 1 and cgroup v2; x86 explorer only.
  - `scripts/auto-scale-memory.sh` (tests: dashboard/backend/src/tests/mempoolApiMemory.test.ts) — Port after re-check for Fedora/Pi: re-derive for Pi 5 RAM and Quadlet resource settings.
- **Superseded / caveat:** The lesson "runtime default heap too small for startup reindex" from 2026-08-10-bip110-invalid-mark-leak.md was later superseded by 2026-08-16-mempool-oom-recurrence.md.

#### PLAT-05 — Units are ordered so the node can always boot and report

- **Rule:** Optional units are ordered with After=/Wants=, never Requires=/BindsTo= that a disabled or restarting unit can break; the management UI does not hard-depend on the container runtime; best-effort boot repair units do not hold multi-user.target (DefaultDependencies=no, bounded timeout); state that other components rely on survives service restarts; startup never waits on external delivery; every outbound transport has explicit timeouts; drop-ins are validated with `systemd-analyze verify`.
- **Why:** the dashboard unit's hard dependency on Docker took it down on every Docker restart (2026-10-09-upgrade-deadlock-and-progress.md); control-plane restarts erased an update-freeze marker in /run (2026-09-16-rust-alert-delivery-and-owner-token.md); awaiting an email before readiness could have put the service in a systemd restart loop (2026-10-04-config-tamper-notifies-owner.md) (+1 more).
- **Tripwire:** A unit-file lint (no Requires= on the runtime from the UI unit); a startup test with a never-resolving send (returns in under 500 ms); a boot-time bound on reaching multi-user.target.

#### PLAT-06 — Tor is ordered, applied and verified

- **Rule:** Every service that routes through Tor is ordered after Tor on every start path (boot, UI start, watchdog, post-crash restart) and waits rather than exits; after every bitcoind start the node verifies the Tor proxy applied (getnetworkinfo); a Tor restart restarts bitcoind only when bitcoind's startup-resolved proxy address is no longer Tor's (unknown → skip and log "not restarting blind"); Tor recovery computes the expected hidden-service set from what should be running, probes each onion through SOCKS, never starts services during an owner stop, and serialises on its own lock idempotently; no probe depends on a binary absent from the image.
- **Why:** a liveness probe used `nc`, which the bitcoind image lacks, so Tor always read unreachable and 36 cascades restarted bitcoind and its dependants (2026-09-17-self-heal-p2-probes-and-selection.md); bitcoind started before Tor and exited on an unresolvable proxy, and Tor served only the dashboard's onion while recovery reported success (2026-09-30-node-power-buttons.md); two repair paths restarted Tor and LND twice on every Docker-restarting update (2026-10-09-upgrade-deadlock-and-progress.md) (+1 more).
- **Tripwire:** A start-order test over every Tor-routed service; restart-decision tests; recovery tests in which a second repair finds nothing to do.
- **Owner:**
  - “Bitcoin waits for tor to start (Recommended)” — 2026-09-30-node-power-buttons.md
  - “Restart tor now (Recommended)”; at Start All: “Repair: restart tor, then LND (Recommended)” — 2026-09-30-node-power-buttons.md
- **Port:**
  - `control-plane/src/tor_cascade.rs` (tests: Rust tests in the file) — Port after re-check for Fedora/Pi: reads Docker container addresses; a stable Tor address may remove the need.
  - `dashboard/backend/src/tests/composeStartOrder.test.ts` — Port after re-check for Fedora/Pi: express the ordering as Quadlet/systemd After= and cover post-crash restarts.
  - `scripts/rikuri-tor-recover.sh` (tests: dashboard/backend/src/tests/torRecoverMissing.test.ts) — Port after re-check for Fedora/Pi: Docker-based; put its lock under the data root.

#### PLAT-07 — bitcoind configuration has one source and is validated

- **Rule:** Each bitcoind setting lives in exactly one place (bitcoin.conf, in a node-managed marked block that is replaced, never stacked, with operator lines preserved); presets are explicit values per engine and version, with a test that a preset shared by engines resolves to the same effective options; an option the running engine cannot serve is refused and nothing is written; every config line is validated against the binary's own `-help`; every alternate configuration (other engine, network, full vs pruned profile) is rendered and parsed in CI; start commands carry no comment lines and no relay-policy flags; new bitcoind interfaces (REST, ZMQ, RPC binds) are costed owner choices kept on the internal network.
- **Why:** "Standard" meant "engine defaults", so Core and Knots "Standard" differed and the owner could not tell them apart (2026-09-20-postures-per-engine.md); the Knots configuration did not parse for 12 days while the node ran Core (2026-10-02-knots-overlay-parses.md); a Knots-only option sat in Core's config (2026-09-20-relay-profiles-c1.md); Electrs 0.12 required enabling bitcoind's unauthenticated REST interface (2026-10-03-electrs-0.12-support.md) (+1 more).
- **Tripwire:** Cross-engine equivalence tests; a parse test over every configuration variant; an option diff against `-help` on each bitcoind bump.
- **Owner:**
  - “Fix now, with a test (Recommended)” — 2026-10-02-knots-overlay-parses.md
  - “Do both now.” — 2026-10-03-electrs-0.12-support.md
- **Port:**
  - `dashboard/backend/src/config/relayProfiles.ts` (tests: dashboard/backend/src/tests/relayProfiles.test.ts) — Port after re-check for Fedora/Pi: only if relay postures are offered.
  - `dashboard/backend/src/tests/composeCommandBlocks.test.ts` — Port after re-check for Fedora/Pi: re-express for the Quadlet variants (x86 full, Pi pruned).
- **Superseded / caveat:** The copy "relay policy does not change your disk usage" was justified for an unpruned node and must be re-checked for the pruned Pi.

#### PLAT-08 — bitcoind state is read correctly

- **Rule:** "Synced" means blocks == headers, not in initial download, and a tip under 2 h old; heights while the block index loads are null; stall detection counts only progress (a new validated block, or headers at download speed; presync recognised), keeps its clock running while bitcoind cannot be asked, and fails toward alerting when the progress probe fails; "serving RPC" is separate from "caught up", so a node catching up after being off reads as syncing, not as an outage; RPC adapters are tested against the bitcoind version shipped; limits come from the node's own report (mempool usage against its own maxmempool).
- **Why:** "Synced" came from verificationprogress, so a stalled tip read Synced for about 50 h, and trickling headers and presync fooled the stall detector through four rounds (2026-09-30-dashboard-measurements.md); a wallet refresh threw about once a minute because, on Bitcoin Core 31, getwalletinfo carried no balances and getbalances had to be used (2026-09-30-dashboard-page-truth.md); Knots' health check read down for a whole first sync (2026-09-30-reliability-uptime-truth.md) (+1 more).
- **Tripwire:** Sync-state tests (Synced / Behind / Stale / Syncing); progress-tracking tests over multi-day timelines; version-pinned RPC fixtures refreshed at each bitcoind upgrade.
- **Owner:** “Show 'Syncing' instead”; after being told the stated cost was false and asked again, “Syncing, but serious → Warning (Recommended)” — 2026-09-30-dashboard-measurements.md
- **Port:** `dashboard/backend/src/tests/syncStuckStandDown.test.ts` — Port with tests.

#### PLAT-09 — Engine switching, if offered, cannot inherit another engine's verdicts

- **Rule:** If the node offers Core/Knots switching, engines do not share a block index (separate data directories avoid the class); otherwise a switch checks getchaintips for invalid entries, backs up blocks/index, keeps the old chainstate, treats "previously marked invalid" as the known signature whose remedy is `reconsiderblock` by the owner (never a reindex, never automated), ejects the divergent faction's peers, and keeps maintenance until the new engine is at tip.
- **Why:** after switching from Knots to Core, Core inherited Knots' invalid mark on a majority-chain block and crawled the 1–2 %-hashrate fork (9 blocks in 10 h) until the owner ran `reconsiderblock` by hand (2026-08-10-bip110-invalid-mark-leak.md, 2026-09-20-knots-repin-and-gate.md).
- **Tripwire:** A switch preflight (count of invalid chain tips); an engine-switch drill (not exercised as of those records).
- **Owner:** The owner's spec for the class fix, as the record quotes it: “eject wrong-faction peers, locate the right headers, self-heal stands down during the switch, rotate peers cleanly”; reconsiderblock was blocked from automation and run by the owner by hand — 2026-08-10-bip110-invalid-mark-leak.md

#### PLAT-10 — Hardware recovery helpers respect device policy

- **Rule:** Host-hardware recovery is an in-repository, tested boot oneshot that waits for the device to settle, touches only the affected device, retries a bounded number of times, always restores the device on exit, never overrides the owner's rfkill switch, re-authorizes only devices it de-authorized itself, leaves policy-de-authorized devices held, never resets a multi-function device with a non-target interface, reports its verdict visibly and can be disabled with one command.
- **Why:** after a power outage the USB Bluetooth adapter failed its firmware load at two boots, and the old local fix pointed at a deleted path and exited before its remedy; review then found the new script would authorize devices a USB policy had left de-authorized and could reset a combined Wi-Fi + Bluetooth dongle — possibly the node's network link (2026-09-30-bluetooth-revive-at-boot.md).
- **Tripwire:** Fake-sysfs tests that model the failure shape (a de-authorized device has no interfaces left).
- **Owner:** “Bluetooth is not working at all, can't even turn it on. This is a recurring issue.” then “Yes, build a boot service and reauthorize auto in rikurinode repo.” (2026-09-30) — 2026-09-30-bluetooth-revive-at-boot.md
- **Port:** `scripts/rikuri-bluetooth-revive.sh` and `systemd/rikuri-bluetooth-revive.service` (tests: dashboard/backend/src/tests/bluetoothRevive.test.ts) — Do not port as is: the record is still IN PROGRESS (no live revival run, no verifier) and the accepted review fixes (leave policy-held devices alone, re-authorize only what it de-authorized, never reset a multi-function device) were never committed; the hardware also differs.
- **Superseded / caveat:** The old record is IN PROGRESS and its accepted review fixes were never committed; see Port candidates.

#### PLAT-11 — Every proxy site serving the UI is generated and tested

- **Rule:** Every reverse-proxy site that serves the UI comes from one generated config (or a test pins its API and WebSocket locations); API and WebSocket paths never fall through to the single-page app's index with a 200; the deployed proxy config equals the tested repository copy; smoke performs a WebSocket handshake through each served URL.
- **Why:** the proxy site the owner actually used had no WebSocket location, so live updates never connected while the proxy answered 200 with the app's index page (2026-10-06-nginx-socket-io-location.md, 2026-09-28-runtime-dependency-vulnerabilities.md).
- **Tripwire:** A per-site location test (mutations red); a live check that the WebSocket upgrade answers 101.
- **Owner:** “Own small record, now (Recommended)” — 2026-10-06-nginx-socket-io-location.md
- **Port:** `dashboard/backend/src/tests/nginxSocketIo.test.ts` — Port after re-check: nginx-specific.

## 3. Owner decisions

Every distinct owner decision in the harvest (122), quoted verbatim from the `owner_decision` field, in record order. Some fields are the harvester's summary of a choice rather than the owner's own sentence; where the field says so, that is part of the quote. "Recommended" marks the option the session recommended when it asked. A note in *(…)* after a row says what its record shows (a summary, several answers joined, or the record's exact wording); the row's text stays the harvest's, except row 119, whose text was corrected (its note gives the harvest's).

| # | Owner decision (verbatim) | Record(s) | Feeds | Status |
|---|---|---|---|---|
| 1 | Owner spec for the class fix: "eject wrong-faction peers, locate the right headers, self-heal stands down during the switch, rotate peers cleanly". reconsiderblock was blocked from automation and run by the owner by hand. *(the record's summary, quoting the owner's spec)* | 2026-08-10-bip110-invalid-mark-leak.md | PLAT-09 | Current |
| 2 | "nothing should fail silently or be in a crash loop" | 2026-08-10-crashloop-detection.md | HEAL-10 | Current |
| 3 | Standing decision recorded in the record (not quoted as the owner's words): "if this OOMs again, we STOP raising ceilings and bound the growth instead". *(the record does not say who set this rule; the harvest listed it as the owner's)* | 2026-08-16-mempool-oom-recurrence.md | PLAT-04 | Current |
| 4 | Owner spec (paraphrased in the record): a live progress view until a VERIFIED end state. *(the record's summary)* | 2026-08-19-os-update-false-fail.md | UPG-12 | Current |
| 5 | Owner chose: consolidate, not repair-in-place. | 2026-08-22-rollback-consolidation.md | UPG-02 | Current |
| 6 | "Once pressed, the AI should stop what it's doing." "If reactivated, it shouldn't continue what it was doing." "Should the activation have a matching deactivation?" | 2026-08-24-ai-emergency-stop-actually-stops.md | AI-03 | Current |
| 7 | Owner decision (2026-09-14): delete the file (fsmEngine.test.ts), after its 3 surviving assertions were shown to duplicate existing coverage. *(the record's summary)* | 2026-09-14-script-style-test-conversion.md | TEST-04 | Current |
| 8 | Owner decision (asked): delete the remaining plaintext archives now; no secret rotation (the USB drive never left the owner's possession). | 2026-09-16-backup-truth-and-alerts.md | FUND-03 | Current |
| 9 | Budget spent: skip that hypothesis and continue down the ladder (escalate only when all are spent), with a 24-hour rolling window. *(the record's wording: "budget spent → skip that hypothesis … and a 24-hour rolling window")* | 2026-09-16-drb-attempt-budget-and-escalation.md | HEAL-03 | Current |
| 10 | Decision Q0 = "repair all three by hand first". *(the record's summary of the plan's decision; the plan, at 883d8285, reads: Q0 — Repair the live breakages by hand first: YES)* | 2026-09-16-self-heal-p0-live-repairs.md | TEST-08 | Current |
| 11 | The owner chose to fix the violations rather than baseline them; deleting DRB-NETWORK-OFFLINE-01 was owner-approved. *(the record's summary)* | 2026-09-17-drb-schema-gate.md | HEAL-04 | Current |
| 12 | Ok replace AI Fixes and Rust-side detectors write incidents | 2026-09-18-guardian-page-and-rust-detectors.md | HEAL-01, HEAL-06 | Current |
| 13 | I think we just have 2 different cards, each for each engine. … For a novice, we don't understand the technical things like datacarrier=1… | 2026-09-20-engine-cards.md | OWN-09 | Current |
| 14 | implement Claude SDLC's procedure from now on for projects that make sense. | 2026-09-22-ai-native-sdlc-controls.md | TEST-12 | Superseded by 2026-09-26-guard-owner-relaxations.md |
| 15 | let the restart button surface only after I click the switch from standard to strict (may be popup with authentication), then disappear after implementation. | 2026-09-23-posture-restart-to-apply.md | EVID-04 | Current |
| 16 | should require password | 2026-09-23-posture-restart-to-apply.md | EXEC-03 | Current |
| 17 | 3. Fix without guardian to ask first | 2026-09-24-lnd-sync-stall-misclassified.md | LN-03 | Current |
| 18 | 1. yes fix both | 2026-09-25-electrs-mempool-clean-stop.md | LN-01 | Current |
| 19 | Yes, go ahead and close the hole. | 2026-09-25-guard-self-disable-hole.md | TEST-11 | Superseded by 2026-09-26-guard-owner-relaxations.md |
| 20 | ok with 2 rules | 2026-09-25-lesson-gates.md | TEST-12, UPG-09 | Current |
| 21 | Go ahead and work on the fix for LND stop | 2026-09-25-lnd-clean-stop.md | LN-01 | Current |
| 22 | 2. Ok let control plane skip | 2026-09-26-cascade-skip-restarted.md | LN-04 | Current |
| 23 | So must pass along the name for health check. Refuse if container name doesn't match. | 2026-09-26-exact-container-target.md | IDEN-01 | Current |
| 24 | Can we release the fix-lock, allow restart LND/bitcoin/tapd; edit guard, or CI from requiring permission? … We'll put these back on when appropriate | 2026-09-26-guard-owner-relaxations.md | TEST-12 | Current |
| 25 | 4. yes | 2026-09-26-health-exact-container-names.md | IDEN-01 | Current |
| 26 | "4. yes" (2026-09-26), to having LND read Bitcoin's cookie file itself. | 2026-09-26-lnd-rpccookie.md | SEC-01 | Current |
| 27 | "Why exclude. Shouldn't the runbook restart LND or is that a double restart?" then "2. Ok, use your suggestion" (2026-09-26): ask first when the picked container holds funds, automatic for everything else. | 2026-09-26-memory-restart-asks-for-funds.md | LN-02 | Current |
| 28 | "Don't wait for my approval to restart LND." (2026-09-27) | 2026-09-26-memory-restart-asks-for-funds.md | LN-02 | Current |
| 29 | First approval "1. Ok with your proposal" (alert only at >=95% for 3 checks in a row; restart mempool-api itself, never "the heaviest container"; no CPU alert); after the investigation, chose "Heap follows limit". *(“the heaviest container” is the session's wording, not the owner's; PLAT-04's Owner line gives it unquoted)* | 2026-09-26-mempool-api-memory.md | PLAT-04 | Current |
| 30 | "Fine with 95% limit for now." (2026-09-27, on measuring the 95% as docker stats shows it) | 2026-09-26-mempool-api-memory.md | PLAT-04 | Current |
| 31 | "The original memory limit for each service depends on the size of RAM for a node … if there is only 8 or 16 GB, that needs to be limited or controlled. Not sure what .env has." (2026-09-27) | 2026-09-26-mempool-api-memory.md | PLAT-04 | Current |
| 32 | "Ok yes, make the one line change." (2026-09-27) | 2026-09-27-control-plane-restart-free.md | TEST-12 | Superseded by 2026-09-27-guard-profiles.md |
| 33 | "I think for now we'll just follow the Auto mode for Claude or Codex. It's too restrictive the way I set this up." … "They need to be able to adjust this permission system easily. These restrictions are more suited for something close to completion." Chosen: development still asks only before money moves ("sending funds/payments, Iceman live trading, deleting wallet or chain data"); all four repos switch now. *(the text in brackets after Chosen is the option's description, the session's words; TEST-12's Owner line gives it unquoted)* | 2026-09-27-guard-profiles.md | TEST-12 | Current |
| 34 | "fix the audit as well" (2026-09-28) | 2026-09-28-dep-audit-sees-what-github-sees.md | SEC-06 | Current |
| 35 | "Ok for fix to the gurad" (2026-09-28) | 2026-09-28-fix-lock-covers-inline-tests.md | TEST-11 | Current |
| 36 | "Let's fix the tor onion." (2026-09-28) | 2026-09-28-repairs-outlive-the-request.md | HEAL-08 | Current |
| 37 | "Ok yes" (2026-09-28), to: fix openssl and serde_with, upgrade jsonwebtoken properly with auth tests, record yamux as unreachable, and prove-then-remove ai-orchestrator. | 2026-09-28-runtime-alerts-round-two.md | SEC-05 | Current |
| 38 | "Yes, go ahead with both 1 and 2 first" (2026-09-28) — (1) make cleanup/main the default branch, (2) fix the real runtime list as one tracked change. | 2026-09-28-runtime-dependency-vulnerabilities.md | TEST-05 | Current |
| 39 | "rikurinode's Bitcoin price on Bitcoin section is wrong (showing 84,346, instead of 83,260). Are we not connected to the source or is the source compromised?" Chosen: "Exchanges first (Recommended)" — Kraken, then Coinbase, then the node's own mempool. | 2026-09-29-btc-price-exchanges-first.md | EVID-05 | Current |
| 40 | "Market cap and 24h volume: CoinGeko doesn't seem reliable. It goes down sometimes, same thing happens for CoinGeko app on its smartphone app. Any alternative?" Chosen: "Computed on the node (Recommended)" for market cap and "Regulated exchanges only" for 24h volume. | 2026-09-29-market-cap-volume-etf-warm.md | EVID-05 | Current |
| 41 | "1. Ok" (2026-09-29), approving keeping the ETF issuer fallback warm (cost stated: one extra headless-browser visit to iShares and etfdb plus a Yahoo call per day). | 2026-09-29-market-cap-volume-etf-warm.md | EVID-06 | Current |
| 42 | "Do we need fallback for other existing Market Intelligence? Can we know if data can't be updated or go stale?" Chosen: "Stale data: page + Guardian alert (Recommended)". | 2026-09-29-market-intel-freshness-arkb.md | EVID-05 | Current |
| 43 | AskUserQuestion choices (2026-09-29): "MAs + returns backup: Kraken daily candles, plus the node's own daily-close archive"; "funding: a second venue (Deribit, labelled)". *(the record bolds only the option labels, “MAs + returns backup:” and “funding: a second venue”; the rest of each is its own description)* | 2026-09-29-market-intel-freshness-arkb.md | EVID-06 | Current |
| 44 | "Need to replace GBTC as top 3 ETF, I think. There isn't much movement visible from GBTC. Looks like BITB or ARKB should be substituted." Chosen: "ARKB (Recommended)" and Total "all spot ETFs (Recommended)". | 2026-09-29-market-intel-freshness-arkb.md | EVID-05 | Current |
| 45 | "Bluetooth is not working at all, can't even turn it on. This is a recurring issue." then "Yes, build a boot service and reauthorize auto in rikurinode repo." (2026-09-30) | 2026-09-30-bluetooth-revive-at-boot.md | PLAT-10 | Current |
| 46 | "Yes, in fact, check all measurement on the Dashboard. Make sure every one of them is actually meansuring the right thing and is correctly measuring what it's suppose to." Choices: "'No sensor', no cap"; Guardian heat alert uses the "Dashboard's 'hot' band". | 2026-09-30-dashboard-measurements.md | PLAT-02 | Current |
| 47 | "Every mounted drive" (any drive over 90% caps the score at Good; cost stated: a full USB stick holds the score at Good). | 2026-09-30-dashboard-measurements.md | EVID-07 | Current |
| 48 | "Honest rework (Recommended)"; later "Rule decides the label (Recommended)", "Critical (Recommended)" for Docker not answering, "Over 95% = serious (Recommended)" for memory, "Score it, no issue (Recommended)" for CPU load, "All inactive = Good at most (Recommended)" for channels, "Show 'Syncing' instead" for initial sync. | 2026-09-30-dashboard-measurements.md | EVID-08 | The initial-sync choice "Show 'Syncing' instead" was asked again after its stated cost proved false; final choice "Syncing, but serious → Warning" (2026-09-30-dashboard-measurements.md) |
| 49 | "Show 'Syncing' instead"; after being told the stated cost was false and asked again, "Syncing, but serious → Warning (Recommended)". | 2026-09-30-dashboard-measurements.md | PLAT-08 | Current |
| 50 | "Critical (Recommended)" for Docker not answering (cost stated: a docker slower than 5 s twice in a row flashes Critical). | 2026-09-30-dashboard-measurements.md | EVID-08 | Current |
| 51 | Yes, in fact, check all measurement on the Dashboard. Make sure every one of them is actually meansuring the right thing and is correctly measuring what it's suppose to. | 2026-09-30-dashboard-page-truth.md<br>2026-09-30-reliability-uptime-truth.md | EVID-03, IDEN-01 | Current |
| 52 | 'Stopped by you' (Recommended) | 2026-09-30-dashboard-page-truth.md | OWN-04 | Current |
| 53 | Borders: "Turn them on (Recommended)"; phone menu: "Yes, in its own record (Recommended)" | 2026-09-30-dashboard-page-truth.md | TEST-10 | Current |
| 54 | correct the language if force closes don't return funds to hardwallet | 2026-09-30-dashboard-page-truth.md | LN-09 | Current |
| 55 | "Note doesn't degrade (Recommended)" (disk note); "Same rule (Recommended)" (mempool note) | 2026-09-30-dashboard-page-truth.md | AI-04 | Current |
| 56 | Add rikurinode's guard here (Recommended) | 2026-09-30-dashboard-page-truth.md | TEST-11 | Current |
| 57 | Everything with data (Recommended) | 2026-09-30-node-power-buttons.md | LN-01 | Current |
| 58 | Until I press Start All (Recommended) | 2026-09-30-node-power-buttons.md | OWN-04 | Current |
| 59 | Bitcoin waits for tor to start (Recommended) | 2026-09-30-node-power-buttons.md | PLAT-06 | Current |
| 60 | "Wait for tor, then alert (Recommended)"; after a tor restart: "Alert you to restart LND (Recommended)" | 2026-09-30-node-power-buttons.md | LN-05 | Current |
| 61 | "Restart tor now (Recommended)"; at Start All: "Repair: restart tor, then LND (Recommended)" | 2026-09-30-node-power-buttons.md | PLAT-06 | Current |
| 62 | Count it as downtime (Recommended) | 2026-09-30-reliability-uptime-truth.md | EVID-10 | Current |
| 63 | "Services only (Recommended)" (MTTR); "Show as 'stopped by you' (Recommended)"; "No: 'stopped by you' (Recommended)" (power-off after Safe Shutdown); "Stopped until up, 15-min cap (Recommended)"; "15-min rule, like Start All (Recommended)" (slow start after a crash); "Keep 'stopped by you' (Recommended)" (testnet4 stopped, then a reboot) | 2026-09-30-reliability-uptime-truth.md | EVID-10 | Current |
| 64 | Rebuild, labelled (Recommended) | 2026-09-30-reliability-uptime-truth.md | EVID-10 | Current |
| 65 | "Shorten cards to fit (Recommended)"; then "Search docs when no card (Recommended)" | 2026-09-30-reliability-uptime-truth.md | AI-06 | Superseded by 2026-10-02-slim-path-searches-docs-when-no-card.md |
| 66 | "We can increase the context window to 3000 bytes, if needed to fit the 2 relevant cars.  If better match is not ranked first, what does that mean?  Our ranking is wrong or is using some other criteria than match?" — then chose "Fix the word-matching (Recommended)" | 2026-09-30-reliability-uptime-truth.md | AI-07 | Superseded by the later choice "Blend word + meaning" (2026-10-02-slim-path-searches-docs-when-no-card.md) |
| 67 | Newest 4 (Recommended) | 2026-10-02-channel-backup-after-open-close.md | FUND-06 | Current |
| 68 | "2. channel backup should be made when ever there's changes to its state so 15 min should be right ( also open and close channels)." Choice: "Also channel.db after open/close" | 2026-10-02-channel-backup-after-open-close.md | FUND-04 | Current |
| 69 | 3. Dead code should be cleaned up if not needed. | 2026-10-02-cleanups-dead-security-tabs-flaky-test.md | EXEC-04 | Current |
| 70 | 5. Clean the flaky Rust test. If not needed then delete/clean. | 2026-10-02-cleanups-dead-security-tabs-flaky-test.md | TEST-01 | Current |
| 71 | Shorten cards to fit (Recommended) | 2026-10-02-concept-cards-fit-slim-budget.md | AI-06 | Current |
| 72 | Fix the guardian's daily telegram summary (is this sent to Telegram, I don't think I've been receiving any daily summary. Used to receive weekly summary from Groq, but not anymore). | 2026-10-02-guardian-summaries-reach-the-owner.md | HEAL-09 | Current |
| 73 | Restart All health services should read the flag, right? | 2026-10-02-guardian-summaries-reach-the-owner.md | OWN-05 | Current |
| 74 | Fix now, with a test (Recommended) | 2026-10-02-knots-overlay-parses.md | PLAT-07 | Current |
| 75 | 1. Make the 2 glossaries if that's what's needed. | 2026-10-02-knowledge-store-one-name-one-guide.md | AI-10 | Current |
| 76 | Search docs when no card (Recommended); later: Card + docs when weak (Recommended) *(two answers joined)* | 2026-10-02-slim-path-searches-docs-when-no-card.md | AI-07 | Current |
| 77 | We can increase the context window to 3000 bytes, if needed to fit the 2 relevant cars. | 2026-10-02-slim-path-searches-docs-when-no-card.md | AI-06 | Current |
| 78 | Blend word + meaning (Recommended) — supersedes the earlier choice 'Fix the word-matching (Recommended)' *(the owner's choice and the record's note joined)* | 2026-10-02-slim-path-searches-docs-when-no-card.md | AI-07 | Current |
| 79 | 7. Is rotating LND's tor password is better for security, then yes. | 2026-10-02-tor-control-password-rotation.md | SEC-02 | Current |
| 80 | Yes, let it finish and plan upgrade around the ready index. Nice idea to let the test container build .12 index then upgrade onto it. For nodes with limited SSD, we'll have to add a plan around it, next time. | 2026-10-03-electrs-0.12-support.md | UPG-11 | Current |
| 81 | Do both now. | 2026-10-03-electrs-0.12-support.md<br>2026-10-03-inline-patch-beside-held-line.md | PLAT-07, UPG-04 | Current |
| 82 | 4. Let's not share fix-lock. | 2026-10-03-fix-lock-per-session.md | TEST-12 | Current |
| 83 | 1. Remove it. | 2026-10-03-remove-community-issue-collection.md | EVID-06 | Superseded by 2026-10-04-remove-mcp-data-collector.md |
| 84 | 5. Yes add smoke check. | 2026-10-03-smoke-catches-broken-native-modules.md | PLAT-03 | Current |
| 85 | Node 22 from NodeSource (owner's choice as recorded); then 'maybe we should have moved to Node 24' *(the record's summary, with a quotation)* | 2026-10-03-ubuntu-26.04-upgrade.md | PLAT-03 | Superseded in the same record: the node moved to Node 24 (2026-10-03-ubuntu-26.04-upgrade.md) |
| 86 | We need to upgrade linux to 26.04.1 LTS with kernel 7.0. | 2026-10-03-ubuntu-26.04-upgrade.md | PLAT-03 | Current |
| 87 | Yes, count them | 2026-10-03-upgrade-gates-round-2.md | UPG-05 | Current |
| 88 | Auto-install, only if all gates pass | 2026-10-03-upgrade-gates-round-2.md | UPG-05 | Current |
| 89 | Just leave them. We have enough RAM. If we were doing this as and upgrade for other nodes, then we'll need to keep RAM usage based on the local hardware. Keeping the node running as much as we can, while upgrading. Shotdown or reduce RAM usage if necessary. | 2026-10-03-upgrade-gates-round-2.md | PLAT-04 | Current |
| 90 | 3. We should have a auto rollback.  Incidently, if the upgrade require a sequeced upgrade (for example, must upgrade to Bitcoin Core 31 before Electrs 0.12; then  our display should say Sequenced upgrad required: start from 1. Rikurinode 1.5; 2. Bitcoin Core 31; 3. Electrs 0.12 | 2026-10-03-upgrade-gates-round-2.md | UPG-04 | Current |
| 91 | 1. relax it | 2026-10-03-upgrade-gates-round-2.md | UPG-05 | Current |
| 92 | Roll back. Then close the three gaps. / Yes, roll back + tell me *(two answers joined)* | 2026-10-03-upgrades-cannot-break-a-service.md | UPG-01 | Current |
| 93 | Supported release lines / Hold it, show why *(answers to two questions joined)* | 2026-10-03-upgrades-cannot-break-a-service.md | UPG-04 | Current |
| 94 | We have a waiting period for each services. I think we should search for documentation for upgrade requirement when the notice to upgrade waiting period first appears. Then send notice to inform the user to wait for rikuri update and the waiting period to be over before upgrading. This will give us time to make any needed changes to rikurinode, during the waiting period. | 2026-10-03-upgrades-cannot-break-a-service.md | UPG-05 | Current |
| 95 | when the release notes show…, hold *(the record's R9 paraphrase of owner answer 1, which its section 0 gives as “Hold it, show why”)* | 2026-10-03-upgrades-cannot-break-a-service.md | UPG-05 | Superseded by 2026-10-03-upgrade-gates-round-2.md |
| 96 | 2. Yes, on both recommendation. | 2026-10-04-config-tamper-notifies-owner.md | SEC-04 | Current |
| 97 | Ok to run gattes on the commit itself, not on working tree of other sessions and pre-commit step | 2026-10-04-gates-run-on-the-commit.md | TEST-06 | Current |
| 98 | Yes, should not be allowed to search or look into .env without permission. | 2026-10-04-guard-secret-searches-and-inline-targets.md | TEST-11 | Current |
| 99 | 5 Ok and fix false positive. | 2026-10-04-guard-secret-searches-and-inline-targets.md | TEST-11 | Current |
| 100 | Accept as is.  commit and push. | 2026-10-04-guard-secret-searches-and-inline-targets.md | TEST-07 | Current |
| 101 | 4. remove collector and unused endpoints. | 2026-10-04-remove-mcp-data-collector.md | EVID-06, AI-02 | Current |
| 102 | 1. Delete warm-up; why does it need warmup? … 3. Remove | 2026-10-04-remove-model-warmup-and-post-ibd.md | TEST-09 | Current |
| 103 | 3. Remove | 2026-10-04-remove-model-warmup-and-post-ibd.md | OWN-09 | Current |
| 104 | 1. Delete the old index. | 2026-10-05-electrs-0.11-index-removed.md | UPG-03 | Current |
| 105 | 2. Ok fix the Guard gap. | 2026-10-05-guard-interpreter-writes-inline-tests.md | TEST-11 | Current |
| 106 | Core fix + test (Recommended); Leave it to the runbook (Recommended); Include it now (Recommended) *(three answers joined)* | 2026-10-05-usb-backup-run-media.md | FUND-01 | Current |
| 107 | Fix all six now (Recommended) | 2026-10-05-usb-backup-run-media.md | EXEC-01 | Current |
| 108 | Include it now (Recommended) | 2026-10-05-usb-backup-run-media.md | TEST-08 | Current |
| 109 | Let's also fix S11, 13, and 8. | 2026-10-06-eject-outcome-not-from-label.md | FUND-07 | Current |
| 110 | Fix now, own record (Recommended) | 2026-10-06-eject-outcome-not-from-label.md<br>2026-10-07-storage-routes-known-drives-only.md | EXEC-06 | Current |
| 111 | Fix it now (Recommended) | 2026-10-06-health-check-parallel-stats.md | EVID-09 | Current |
| 112 | Every route (Recommended) | 2026-10-06-health-check-parallel-stats.md | OWN-08 | Current |
| 113 | Exempt money routes, own record now (Recommended) | 2026-10-06-health-check-parallel-stats.md<br>2026-10-07-money-routes-not-cut-by-watchdog.md | LN-06 | Superseded by 2026-10-07-money-routes-not-cut-by-watchdog.md |
| 114 | Own small record, now (Recommended) | 2026-10-06-nginx-socket-io-location.md | PLAT-11 | Current |
| 115 | Let's also fix S11, 13, and 8. Sweep choices: the assistant's Run = 'Allow-listed, no shell (Recommended)'; code with no caller = 'Delete after proving unused (Recommended)' *(the owner's words, then the session's summary)* | 2026-10-06-request-values-never-reach-a-shell.md | EXEC-01 | Current |
| 116 | Click required, auto off | 2026-10-06-request-values-never-reach-a-shell.md | AI-01 | Current |
| 117 | Own record now (Recommended) | 2026-10-08-assistant-execution-paths.md | AI-01 | Current |
| 118 | Restart dashboard + fix (Recommended) | 2026-10-09-health-score-never-freezes.md | EVID-09, EVID-04 | Current |
| 119 | "OK" — the 55 s limit accepted, 2026-10-10 *(corrected: the harvest read "OK (55 s accepted, 2026-10-10)", as if all of it were the owner's words)* | 2026-10-09-health-score-never-freezes.md | EVID-09 | Current |
| 120 | Let's just fix it | 2026-10-09-upgrade-deadlock-and-progress.md | OWN-03 | Current |
| 121 | It would be better to have an indicator showing ongoing update process if possible so the node doesn't look dead. | 2026-10-09-upgrade-deadlock-and-progress.md | UPG-12 | Current |
| 122 | C1: (a), the newer one runs (the node's pin is dropped once the default reaches or passes it); C2: 'No other node exists now. So it's OK.'; parked: 'Yes, you can park it' *(the record's summary, with quotations)* | 2026-10-10-upgrades-survive-code-updates.md | UPG-08 | Current |

## 4. Port candidates

Deduplicated from the 131 lessons that name a file worth porting, plus one entry added so it is not ported by accident. Paths are relative to the old repository root. Verdicts: **Port with tests** — the logic and its test cases carry over as they are (rewritten if the language changes); **Port after re-check** — carry the tests as the specification but re-check the mechanics first, marked "for Fedora/Pi" where they were Ubuntu, apt or Docker-specific; **Do not port as is** — with the reason.

Totals: 90 entries — 42 port with tests, 45 port after re-check (27 of them for Fedora/Pi mechanics), 3 do not port as is.

**Explicitly: `scripts/rikuri-bluetooth-revive.sh` must NOT be ported as is.** Its record (2026-09-30-bluetooth-revive-at-boot.md) is still IN PROGRESS, it never had a live revival run (only a read-only `--check` against the real adapter and tests on a fake sysfs) or a verifier, and the review fixes accepted in its session (leave policy-de-authorized devices held, re-authorize only devices it de-authorized itself, never reset a multi-function device) were never committed — the committed script lacks them.

| # | Old path | Its tests | What it proves | Feeds | Verdict |
|---|---|---|---|---|---|
| 1 | `dashboard/backend/src/tests/upgradeStaleRepo.test.ts` | itself (a test file) | a dormant pinned image repository is detected when upstream is far ahead, and not otherwise; it fails open when upstream is unreachable; Tor version parsing | UPG-07 | Port after re-check for Fedora/Pi: its tag lookup is Docker Hub-specific; re-target to the registry and pin format the new node uses |
| 2 | `dashboard/backend/src/tests/syncStuckStandDown.test.ts` | itself (a test file) | the sync-stuck alert stands down while height advances; a failed progress probe still alerts | PLAT-08 | Port with tests |
| 3 | `dashboard/backend/src/utils/restartLoopDetector.ts` | dashboard/backend/src/tests/restartLoopDetector.test.ts | N restarts in M minutes are detected per container, with OOM classification (injected clock); slow restarts stay quiet; a recreated container starts a new window | HEAL-10 | Port after re-check for Fedora/Pi: feed it systemd NRestarts / Podman restart counts instead of Docker's |
| 4 | `scripts/compose-lock.sh` | dashboard/backend/src/tests/upgradeRebootBringup.test.ts; dashboard/backend/src/tests/upgradeNoDeadlock.test.ts | one advisory lock for every mutator of the stack; no lock held across a runtime restart | OWN-02, OWN-03 | Port after re-check for Fedora/Pi: Docker Compose-specific; with Quadlet units the single bring-up path may replace it; keep the race and deadlock scenarios as the specification |
| 5 | `dashboard/backend/src/utils/upgradeStateCheck.ts` | dashboard/backend/src/tests/upgradeRebootBringup.test.ts; dashboard/backend/src/tests/upgradeDoneBanner.test.ts | a persisted maintenance window with a bounded grace across reboots; success banners expire and never leak into alert suppression | EVID-04, OWN-05 | Port with tests |
| 6 | `dashboard/backend/src/tests/runnerActiveState.test.ts` | itself (a test file) | transitional unit states count as running (no test covers the package lock) | UPG-12 | Port after re-check for Fedora/Pi: apt/dpkg lock semantics; re-derive for bootc/rpm-ostree states |
| 7 | `dashboard/backend/src/tests/mempoolStalenessAndFees.test.ts` | itself (a test file) | explorer tip lag is its own alert; sub-sat/vB fees survive end to end (exact live numbers) | EVID-01, LN-07 | Port with tests |
| 8 | `dashboard/backend/src/tests/upgradeImageRegistry.test.ts` | itself (a test file) | every deployed image line is registered; sibling-pin drift is detected (with a negative control) | UPG-07 | Port after re-check for Fedora/Pi: parses compose image lines; re-target to Quadlet Image= lines |
| 9 | `dashboard/backend/src/utils/composeControl.ts` | dashboard/backend/src/tests/rollbackConsolidation.test.ts; dashboard/backend/src/tests/upgradeRound2.test.ts | one driver of the runtime (binary, profiles, lock, --no-deps, one environment loader); legacy overlays absent; failure reasons logged | OWN-01, UPG-02, UPG-07 | Port after re-check for Fedora/Pi: Docker Compose v2-specific; rebuild for Podman/Quadlet keeping the test assertions |
| 10 | `dashboard/backend/src/security/apiAccessPolicy.ts` | dashboard/backend/src/tests/apiAccessPolicy.test.ts | default-closed route classifier; re-cased paths; benign and negative tables; onion addresses as credentials | EXEC-02 | Port with tests: re-derive the tables from the new route table |
| 11 | `dashboard/backend/src/tests/runbookCommandAudit.test.ts` | itself (a test file) | runbook commands checked against real endpoints, ports and units; no invented fee default; read-only audit through a mutation denylist | HEAL-04, LN-07 | Port after re-check for Fedora/Pi: its rules name the old endpoints, ports and Docker Compose v1; rewrite the rules for the new catalogue |
| 12 | `dashboard/backend/src/services/ai/emergencyStop.ts` | dashboard/backend/src/tests/emergencyStop.test.ts | the stop persists, fails safe, aborts in-flight work, installs a fresh signal on resume, keeps a balanced audit | AI-03 | Port with tests: add mid-flight model-call cancellation (not done in the old node) |
| 13 | `dashboard/backend/src/middleware/stepUp.ts` | dashboard/backend/src/tests/stepUpBinding.test.ts | step-up tokens bound to method and path, single-use, burned on a wrong route | EXEC-03 | Port with tests |
| 14 | `dashboard/backend/src/tests/conceptCardsIntegrity.test.ts` | itself (a test file) | every knowledge card loads with required fields and unique ids; offenders named | AI-06 | Port with tests: if curated cards are kept |
| 15 | `dashboard/backend/src/ai/retrievalRelevance.ts` | dashboard/backend/src/tests/ragRelevanceCalibration.test.ts | retrieval thresholds calibrated on measured scores | AI-07 | Port after re-check: the values belong to all-MiniLM-L6-v2 on the old corpus; port the calibration procedure and re-measure for the new model |
| 16 | `dashboard/backend/src/tests/ragCanaryBypass.test.ts` | itself (a test file) | the canary fails when a fallback serves the request | EVID-06 | Port with tests |
| 17 | `scripts/rikuri-mdns-interfaces-fix.sh` | dashboard/backend/src/tests/mdnsInterfaceAllowlist.test.ts | avahi allow-list of physical interfaces; empty-list refusal; automatic restore | PLAT-01 | Port after re-check for Fedora/Pi: should ship in the Fedora IoT image; verify interface naming under Podman |
| 18 | `dashboard/backend/src/core/diagnosisEngine.ts` | dashboard/backend/src/tests/diagnosisEngine.test.ts | an empty predicate set never matches; persisted attempt budget; attempt recorded before running; escalation when exhausted | HEAL-03, HEAL-04 | Port after re-check: port the test scenarios as the specification; the engine design itself produced several incidents |
| 19 | `dashboard/backend/src/utils/trustedNetwork.ts` | dashboard/backend/src/tests/rateLimiterLanTrust.test.ts | one IPv4/IPv6 trust helper, including link-local | EXEC-07 | Port with tests |
| 20 | `scripts/quality-ratchet.mjs` and `scripts/quality-ratchet.json` | dashboard/backend/src/tests/requestValuesNoShell.test.ts | debt counters with locked floors, including backend_shell_interpolations, which may only fall | EXEC-01, TEST-04 | Port with tests: re-baseline from zero and keep its recorded blind spots beside it |
| 21 | `dashboard/backend/src/services/backupDeviceConfig.ts` | dashboard/backend/src/tests/backupDeviceConfig.test.ts | atomic, serialised config store with last-good copy; replay of the corrupting bytes | FUND-05 | Port with tests |
| 22 | `dashboard/backend/src/services/backupHealth.ts` | dashboard/backend/src/tests/backupHealth.test.ts | per-destination outcomes; absence-of-success alerts; encrypted-only off the node; 0600 local copies | FUND-01 | Port with tests |
| 23 | `dashboard/backend/src/tests/setup.ts` | itself (harness setup) | a per-worker temporary data root for every test | TEST-01 | Port after re-check: Jest-specific; replicate in whatever harness the new node uses |
| 24 | `dashboard/backend/src/tests/ownerNotificationDelivery.test.ts` | itself (a test file) | in-process delivery; severity normalisation; link filtering and resend; assistant alerts become notifications; caps count attempts | HEAL-03, HEAL-09 | Port with tests: as the specification of the alert path |
| 25 | `control-plane/src/dashboard_internal.rs` | Rust tests | one internal client; a 401 is an error, not a delivery | HEAL-09 | Port with tests |
| 26 | `dashboard/backend/src/security/internalServiceToken.ts` | dashboard/backend/src/tests/internalServiceAuth.test.ts | a scoped machine credential: 0600 token file, exact token and exact routes only, nothing accepted without the file, no privileged payloads (the constant-time compare is in the code, not asserted by the test) | EXEC-07 | Port with tests |
| 27 | `dashboard/backend/src/tests/drbSchemaGate.test.ts` and `ragdocs/drb-schema-baseline.json` | itself (a test file) | declarative self-heal definitions validated against the engine's vocabulary | HEAL-04 | Port after re-check: tied to the old rule schema; port if a declarative catalogue is kept |
| 28 | `dashboard/backend/src/core/backupDriveSignals.ts` | dashboard/backend/src/tests/backupDriveSignals.test.ts | backup health per selected drive by UUID; local copies never count | FUND-01 | Port after re-check for Fedora/Pi: add /run/media and Fedora udisks2 fixtures |
| 29 | `scripts/rikuri-backup-remount.sh` and `scripts/install-backup-remount-polkit.sh` | dashboard/backend/src/tests/backupRemountScript.test.ts | remount only selected UUIDs (the script's exit codes and its drive selection; the polkit grant was checked by hand with `pkcheck`, not by the test) | FUND-07 | Port after re-check for Fedora/Pi: udisks2/polkit on Fedora; never exercised live; the space-in-label follow-up is open |
| 30 | `control-plane/src/runbook/executor.rs` | module tests | honest step semantics, undo on failure, process-group kill on timeout | HEAL-02 | Port with tests |
| 31 | `control-plane/src/runbook/templater.rs` | control-plane/tests/fixtures/runbook-template-cases.json | quote-context-aware substitution of values into shell text | EXEC-01 | Do not port as is: the new node should run argv, never templated shell (EXEC-01); keep the fixture's cases as negative tests |
| 32 | `control-plane/src/tor_cascade.rs` | Rust tests in the file | bitcoind is restarted after Tor only if its resolved proxy address changed | PLAT-06 | Port after re-check for Fedora/Pi: reads Docker container addresses; a stable Tor address may remove the need |
| 33 | `control-plane/src/containers.rs` | none (no test covers the engine-aware lookup) | one engine-aware lookup of the bitcoind container | IDEN-03 | Port after re-check for Fedora/Pi: needed only if several engines or networks run; Podman container names |
| 34 | `dashboard/backend/src/config/consensusBuilds.ts` | dashboard/backend/src/tests/consensusBuilds.test.ts; dashboard/backend/src/tests/knotsConsensusPin.test.ts | fail-closed consensus classification; default-deny allow-list of reviewed builds; no floating tags | UPG-06 | Port with tests |
| 35 | `dashboard/backend/src/config/relayProfiles.ts` | dashboard/backend/src/tests/relayProfiles.test.ts | one typed relay-policy module; drift guard; a half-applied policy reads unknown | PLAT-07 | Port after re-check for Fedora/Pi: only if relay postures are offered |
| 36 | `.claude/hooks/guard.py` | .claude/hooks/test_guard.py; .claude/hooks/guard-config.json (inline_tests rule) | the deterministic AI-session guard: secret-read denies, protected-path asks, fix-lock incl. inline tests, profiles | TEST-11, TEST-12 | Port with tests: copy unchanged (byte-identical across Full-tier repositories) and write a repository-specific guard-config.json |
| 37 | `dashboard/backend/src/config/knotsPinReview.ts` | dashboard/backend/src/tests/knotsPinReview.test.ts | a dated pin review with automatic re-open triggers | UPG-06 | Port after re-check: vital only if Knots is offered; generalise the cadence to every frozen pin |
| 38 | `scripts/electrs-start.sh` | dashboard/backend/src/tests/wrapperStop.test.ts | the PID-1 wrapper forwards stops, exits 0 on a requested stop, sleeps interruptibly | LN-01 | Port after re-check for Fedora/Pi: prefer exec or an image-baked entrypoint; re-run the PID-1 probes under Podman |
| 39 | `scripts/mempool-start.sh` | dashboard/backend/src/tests/wrapperStop.test.ts; dashboard/backend/src/tests/mempoolApiMemory.test.ts | stop forwarding to the node child; heap derived from the container's cgroup memory.max | LN-01, PLAT-04 | Port after re-check for Fedora/Pi: Podman PID 1 and cgroup v2; x86 explorer only |
| 40 | `scripts/auto-scale-memory.sh` | dashboard/backend/src/tests/mempoolApiMemory.test.ts | mempool-api's memory limit and heap scaled from host RAM (the other containers' limits are not tested) | PLAT-04 | Port after re-check for Fedora/Pi: re-derive for Pi 5 RAM and Quadlet resource settings |
| 41 | `scripts/lnd-start.sh` | dashboard/backend/src/tests/lndStartScript.test.ts; dashboard/backend/src/tests/lndTorWait.test.ts | TERM forwarded to LND in every phase; rpccookie by path, no secret in argv or environment; bounded wait for Tor | LN-01, LN-05, SEC-01 | Port after re-check for Fedora/Pi: production shell and Podman PID 1; re-check rpccookie and cookie-rotation behaviour on the current LND version |
| 42 | `control-plane/src/cascade.rs` | inline Rust tests | dependants already restarted on the new cookie are skipped; per-container stop grace | LN-04 | Port after re-check for Fedora/Pi: reads Docker start times; the live skip was not yet observed when the record closed |
| 43 | `control-plane/src/proposal_engine.rs` (owner_hold_reason, runbook_route) | control-plane/tests/runbook_owner_hold.rs | restarting a funds-holding target is held for the owner, decided by the trusted core | LN-02 | Port with tests: add the whole-submit harness recorded as a gap |
| 44 | `scripts/dep-audit/run.js` and `scripts/dep-audit/allowlist.json` | scripts/dep-audit/run.test.js | could-not-audit is distinct from clean; OSV merge; allow-list by alias with reasons | SEC-06 | Port with tests |
| 45 | `control-plane/src/http_server.rs` (run_to_completion) | mod repair_lifetime_tests | repairs run detached from the caller; a panic returns as an error | HEAL-08 | Port with tests: also pin each handler's use of it (a bypass mutation survived) |
| 46 | `control-plane/src/auth.rs` | the auth::tests module | exp and iss required; refusal tests; issue-then-verify round trip | SEC-05 | Port with tests |
| 47 | `dashboard/backend/src/services/priceService.ts` | dashboard/backend/src/tests/priceService.test.ts; dashboard/backend/src/tests/priceFeedStale.test.ts | price source, age and stale flag; per-source backoff; no invented values | EVID-05 | Port after re-check: only if a price display is rebuilt; the freshness model applies generally |
| 48 | `dashboard/backend/src/services/btcSupply.ts` | dashboard/backend/src/tests/btcSupply.test.ts | issued supply computed from height and the subsidy schedule | EVID-05 | Port with tests: if market cap is shown; works on the pruned node |
| 49 | `dashboard/backend/src/services/marketFeeds.ts` | dashboard/backend/src/tests/marketFeeds.test.ts | per-feed freshness; the last value kept and marked stale | EVID-05 | Port after re-check: only if market intelligence is rebuilt |
| 50 | `dashboard/backend/src/services/btcDailyCloses.ts` | dashboard/backend/src/tests/btcDailyCloses.test.ts | source timestamp semantics established against a second source | EVID-05 | Port after re-check: only if moving averages or returns are rebuilt |
| 51 | `dashboard/backend/src/services/hostMetrics.ts` | dashboard/backend/src/tests/hostMetrics.test.ts | one host-metrics module; the right CPU sensor including Pi cpu_thermal; drives by mount point | EVID-07, PLAT-02 | Port after re-check for Fedora/Pi: capture fixtures on the Pi 5 and the new x86 hardware |
| 52 | `dashboard/backend/src/services/serviceProbes.ts` | dashboard/backend/src/tests/serviceProbes.test.ts | functional per-service judges; Electrs height via Electrum; probes settle on every socket outcome | EVID-01, EVID-09, UPG-11 | Port with tests: add unit tests for the async probe runners (missing in the old repository) |
| 53 | `dashboard/backend/src/services/healthScoring.ts` | dashboard/backend/src/tests/healthScoring.test.ts | honest, rule-decided, property-tested health score | EVID-08 | Port with tests |
| 54 | `dashboard/backend/src/services/healthScoreService.ts` | dashboard/backend/src/tests/healthScoreService.test.ts; dashboard/backend/src/tests/healthScoreRefresh.test.ts | single-flight score with its own deadline and a generation counter | EVID-08, EVID-09 | Port with tests |
| 55 | `dashboard/frontend/src/utils/topCards.ts`, `dashboard/frontend/src/utils/resources.ts` and `dashboard/frontend/src/utils/serviceCard.ts` | dashboard/frontend/tests/pageRound4.test.tsx; dashboard/frontend/tests/pageRound4Fixes.test.tsx; dashboard/frontend/tests/pageRound6.test.tsx | unknown carried as null, distinct from a real 0, on every card | EVID-02 | Port after re-check: the frontend is rebuilt; port the cases as the specification |
| 56 | `dashboard/backend/src/services/assistantFacts.ts` | dashboard/backend/src/tests/assistantFacts.test.ts | one sync-state definition consumed by every surface | EVID-07 | Port with tests |
| 57 | `dashboard/backend/src/services/nodePower.ts` | dashboard/backend/src/tests/nodePower.test.ts | full-grace stops with exit codes read; safe-to-unplug only after clean stops; Start All is the boot path | OWN-01, LN-01 | Port after re-check for Fedora/Pi: docker stop / compose calls become Podman and systemd TimeoutStopSec / Quadlet starts |
| 58 | `dashboard/backend/src/utils/maintenanceMode.ts` | dashboard/backend/src/tests/ownerStop.test.ts; dashboard/backend/src/tests/guardianHoldAllPaths.test.ts | one owner-stop state that every actor queries | OWN-04 | Port with tests: re-enumerate the actors of the new node |
| 59 | `dashboard/backend/src/tests/composeStartOrder.test.ts` | itself (a test file) | every Tor-routed service waits for Tor | PLAT-06 | Port after re-check for Fedora/Pi: express the ordering as Quadlet/systemd After= and cover post-crash restarts |
| 60 | `dashboard/backend/src/utils/lndOnion.ts` | dashboard/backend/src/tests/lndOnionReach.test.ts | LND's onion is probed through SOCKS, not just listed | LN-05 | Port with tests |
| 61 | `scripts/rikuri-tor-recover.sh` | dashboard/backend/src/tests/torRecoverMissing.test.ts | the expected onion set is repaired; serialised, idempotent repair | PLAT-06 | Port after re-check for Fedora/Pi: Docker-based; put its lock under the data root |
| 62 | `control-plane/src/uptime.rs` | inline Rust tests | exact component identity; gap classification; distinct uptime states; window edges (+899/+900/+901 s; the 900,000-case fuzz was a one-off verification run, not a committed test) | EVID-10, IDEN-01 | Port with tests: re-check the container-status source under Podman |
| 63 | `dashboard/backend/src/tests/conceptCardBudget.test.ts` | itself (a test file) | each knowledge card reaches the model whole; the debt list may only shrink | AI-06 | Port with tests: if curated cards are kept |
| 64 | `control-plane/src/backup/channeldb.rs` | inline Rust tests (files_to_prune, keep_count_from, ChangeWatch) | retention of channel.db copies; debounced backup on channel changes | FUND-04, FUND-06 | Port after re-check: re-check under the current LND; this backup has never succeeded; its first real run is the first channel open |
| 65 | `dashboard/backend/src/services/healthService.ts` (held-alert logic) | dashboard/backend/src/tests/healthHeldAlertsFlow.test.ts; dashboard/backend/src/tests/healthHeldAlertsEdges.test.ts | held alerts are delayed, not dropped; a dropped hold frees its cooldown | OWN-05 | Port after re-check: port the tests as the specification; the held map lived in memory |
| 66 | `dashboard/backend/src/tests/composeCommandBlocks.test.ts` | itself (a test file) | no comment lines inside any compose command block; Knots keeps its start options and no relay-policy flags (no parser is run) | PLAT-07 | Port after re-check for Fedora/Pi: re-express for the Quadlet variants (x86 full, Pi pruned) |
| 67 | `dashboard/backend/src/tests/docNamesUnique.test.ts` | itself (a test file) | knowledge source names are unique | AI-10 | Port with tests |
| 68 | `dashboard/backend/src/ai/ragSources.ts` | dashboard/backend/src/tests/ragSources.test.ts; dashboard/backend/src/tests/ragSweepSafety.test.ts | deleted sources are removed; a prune runs only on a complete view | AI-10 | Port with tests |
| 69 | `dashboard/backend/src/ai/slimKnowledge.ts` | dashboard/backend/src/tests/slimKnowledge.test.ts; dashboard/backend/src/tests/cardBlend.test.ts; dashboard/backend/src/tests/cardRanking.test.ts; dashboard/backend/src/tests/fixtures/card-questions.json; dashboard/backend/src/scripts/cardRankingCheck.ts | grounding falls back to document search; ranking judged on a labelled, held-out question set | AI-07 | Port after re-check: re-measure with the new model; the full-pipeline evaluation is still owed |
| 70 | `control-plane/src/electrs_phase.rs` | test module | Electrs height read from Electrum when the metric is gone | UPG-11 | Port with tests: x86 full node only |
| 71 | `dashboard/backend/src/services/revertPlan.ts` | dashboard/backend/src/tests/revertPlan.test.ts | revert restores the exact, hash-checked snapshot or refuses | UPG-03 | Port with tests |
| 72 | `dashboard/backend/src/config/upgradeMigrations.ts` | dashboard/backend/src/tests/upgradeMigrations.test.ts | migrations keyed on (from, to), tested on frozen fixtures | UPG-10 | Port after re-check: edits compose files; open question C3 (its record recommends that in-app upgrades change only the pin) decides whether it is needed at all |
| 73 | `dashboard/backend/src/config/upgradeSupport.ts` | dashboard/backend/src/tests/upgradeSafety.test.ts; dashboard/backend/src/tests/upgradeRound2.test.ts | supported release lines; newest in-line patch; sequences; one hold function | UPG-04 | Port with tests |
| 74 | `scripts/smoke.sh` (section 1b) | drill overrides (SMOKE_NATIVE_DIRS, SMOKE_DASH_SINCE) | native modules load under the real runtime; load-error, replaced-binary and core-dump signatures | PLAT-03 | Port after re-check for Fedora/Pi: Node/better-sqlite3-specific; re-express as greenboot boot checks |
| 75 | `dashboard/backend/src/services/upgradeSafety.ts` | dashboard/backend/src/tests/upgradeSafety.test.ts; dashboard/backend/src/tests/upgradeRound2.test.ts | isolated settings checks; stability watch; calibrated security classifier | UPG-01, UPG-05 | Port after re-check for Fedora/Pi: its settings-check containers are Docker; rebuild on Podman |
| 76 | `dashboard/backend/src/services/upgradeRequirements.ts` | dashboard/backend/src/tests/upgradeRequirements.test.ts | release-note review on first detection; range completeness; retry of unreadable reviews | UPG-05 | Port with tests |
| 77 | `dashboard/backend/src/security/integrity/configIntegrity.ts` | dashboard/backend/src/tests/configTamperNotify.test.ts | integrity alarms delivered once per hash; marked only on confirmed delivery | HEAL-09, SEC-04 | Port with tests |
| 78 | `.githooks/pre-commit` | dashboard/backend/src/tests/precommitGatesOnIndex.test.ts | commit gates run on an export of the index | TEST-06 | Port with tests |
| 79 | `dashboard/backend/src/tests/startupBrokenCodeRemoved.test.ts` | itself (a test file) | relative requires resolve under the production resolver | TEST-03 | Port after re-check: Node-specific resolver check |
| 80 | `ragdocs/runbooks/RB-ELECTRS-INDEX-REINDEX-01.json` | a runbook test (3 cases) | the runbook discovers the index volume from the running service | HEAL-05 | Port after re-check for Fedora/Pi: Docker volume names; x86 full node only |
| 81 | `dashboard/backend/src/tests/mountPathNoShell.test.ts` | itself (a test file) | drive labels never reach a shell; default-deny tripwire | EXEC-01 | Port with tests |
| 82 | `dashboard/backend/src/middleware/stallWatchdog.ts` | dashboard/backend/src/tests/stallWatchdogLateReply.test.ts; dashboard/backend/src/tests/moneyRoutesNotCut.test.ts | the watchdog owns the response once it answers; money routes are never cut | OWN-08, LN-06 | Port after re-check: Express-specific; port the tests as the specification |
| 83 | `dashboard/backend/src/tests/nginxSocketIo.test.ts` | itself (a test file) | every proxy site routes the WebSocket path | PLAT-11 | Port after re-check: nginx-specific |
| 84 | `dashboard/backend/src/services/aiRunPolicy.ts` | dashboard/backend/src/tests/aiRunPolicy.test.ts; dashboard/backend/src/tests/assistantExecutionPaths.test.ts | one read-only, argv-only, click-only executor for every assistant path | AI-01 | Port after re-check: the new assistant is sandboxed; apply the policy to whatever bridge reaches the host |
| 85 | `dashboard/backend/src/services/lncliArgv.ts` | dashboard/backend/src/tests/channelManagerLncliArgv.test.ts | lncli runs as argv; gossip addresses validated | LN-08 | Port with tests: re-check against the current lncli/LND RPC |
| 86 | `dashboard/backend/src/tests/storageKnownDrivesOnly.test.ts` | itself (a test file) | file routes read only node-detected drives; separator-aware containment | EXEC-06 | Port with tests |
| 87 | `dashboard/backend/tests/noLiveNode.globalSetup.js` | dashboard/backend/src/tests/testsNeverReachTheLiveNode.test.ts | refusing stand-ins and a missing runtime socket for every test worker | TEST-01 | Port after re-check: Jest-specific; the Rust test runner needs an equivalent; not network-hermetic |
| 88 | `scripts/rikuri-upgrade-runner.sh` | dashboard/backend/src/tests/upgradeNoDeadlock.test.ts | the apt-based OS update runner and its lock and restore rules | OWN-03 | Do not port as is: apt-based in-place OS updates; Fedora IoT updates whole images; keep the test's lock and restore rules as the specification |
| 89 | `dashboard/frontend/src/utils/osUpdateProgress.ts` | dashboard/frontend/tests/osUpdateProgress.test.tsx | update progress taken from the runner's state; failed and interrupted steps marked | UPG-12 | Port after re-check for Fedora/Pi: re-derive from bootc/rpm-ostree state |
| 90 | `scripts/rikuri-bluetooth-revive.sh` and `systemd/rikuri-bluetooth-revive.service` | dashboard/backend/src/tests/bluetoothRevive.test.ts | revival of a stuck USB Bluetooth adapter at boot (not a harvested port candidate; listed so it is not ported by accident) | PLAT-10 | Do not port as is: the record is still IN PROGRESS (no live revival run, no verifier) and the accepted review fixes (leave policy-held devices alone, re-authorize only what it de-authorized, never reset a multi-function device) were never committed; the hardware also differs |

## 5. Gaps — where the old repository has no evidence

The records are rich where the old node failed. They are thin, or silent, on several things the new node depends on. Nothing below may be treated as proven because a related requirement exists; each gap needs its own evidence first.

| # | Gap | What the records show | What must be proven before it can be trusted |
|---|---|---|---|
| G1 | **Lightning channel management with real funds** (rebalancing, fees, open/close, node search, analytics) | Only 20 of 475 lessons concern LND (13) or channel management (7). Mainnet LND had 0 channels whenever a record checked (2026-09-14-guardian-scb-restart-loop.md, 2026-09-23-posture-restart-to-apply.md, 2026-10-08-tests-restarted-live-lnd.md). The channel.db backup never once succeeded (2026-10-02-channel-backup-after-open-close.md). Rebalancing, fee setting and open/close appear only incidentally — in security sweeps (argv, gossip validation, writes served from a read cache, timeouts on money routes: LN-06, LN-08) and wording fixes (LN-09) — never as features exercised end to end; the channel-search screen appears only because it showed raw text keys on channel-open errors (2026-09-30-dashboard-page-truth.md), and analytics only because a hard-coded fallback price fed its break-even figure (2026-09-29-btc-price-exchanges-first.md). | On a test network first (regtest, signet or testnet4), then with a small owner-approved mainnet amount: open; cooperative close to the cold address; force close and sweep after the timelock; fee-policy update; circular rebalance; a payment that times out and is resolved through its pending id without paying twice; analytics figures bound to real LND fields (EVID-03). Every call checked against the current LND version's RPC. |
| G2 | **Restore drills on new hardware** | Restore was exercised only by decrypting the newest encrypted config archive (2026-09-16-backup-truth-and-alerts.md). The drill proving recovery finds the SCB on the backup stick was deferred (2026-10-05-usb-backup-run-media.md). No lesson records a node restored on clean hardware. | A full restore on a spare Pi 5 and on the x86 node: seed + SCB recovery of channels (on a test network), configuration and owner decisions restored, drives found by UUID, bitcoind re-sync time measured; all through the UI, with no command line (FUND-02). |
| G3 | **Fedora IoT, bootc and greenboot** | Every OS lesson comes from Ubuntu: apt, do-release-upgrade, sudo-rs, deb822 sources, a host Node runtime (2026-10-03-ubuntu-26.04-upgrade.md). No lesson covers image updates, greenboot health checks or automatic rollback. | Greenboot checks that implement PLAT-03 (runtime loads), OWN-06 (what ran is running), UPG-01 (services healthy) and LN-05 (onions answer); a deliberately broken image that rolls back by itself; machine state (pins, keys, channel data, owner decisions, maintenance window) intact across update and rollback (UPG-08, UPG-10, OWN-05); polkit and privilege rules re-verified (EXEC-08). |
| G4 | **The Raspberry Pi 5 pruned node** | No lesson comes from running the Pi. Pi facts are limited to recognising `cpu_thermal` (2026-09-30-dashboard-measurements.md), an estimated ~589–614 MB explorer heap on 8 GB (2026-09-26-mempool-api-memory.md), relay-policy disk copy not re-checked for a pruned node (2026-09-20-engine-cards.md), and advice keyed to a txindex full node (2026-09-30-dashboard-page-truth.md). | Initial sync time and stall detection on the Pi (PLAT-08); pruned-node behaviour (no txindex, no Electrs, own maxmempool); memory sizing per tier (PLAT-04); thermal bands and throttling (PLAT-02); power-loss recovery; LND on a pruned backend; assistant advice correct for a pruned node (AI-04). |
| G5 | **The sandboxed assistant (AISecurity policy + OpenShell)** | The old node's assistant was contained by an allow-list of argv-only commands, each run on the owner's click (2026-10-08-assistant-execution-paths.md); no record shows OS-level containment of the assistant as a whole — only its candidate-fix check ran in a container with no network. The AI-session guard's own record says command parsing is a tripwire, not a sandbox (2026-10-04-guard-secret-searches-and-inline-targets.md). Of the agent gateway, only its first refactor (G0) was built; the gateway itself (G1–G4) was not started (2026-09-20-agent-mcp-gateway.md). Mid-flight model calls were not cancelled by the emergency stop (2026-08-24-ai-emergency-stop-actually-stops.md). | A sandbox boundary test: no secret file readable by any command form, no host shell, network limited to what is allowed, no keys or signing authority (AI-02); planning output reaches the node only through the approval queue (HEAL-07); the emergency stop cancels in-flight model calls (AI-03); a full-pipeline retrieval evaluation (AI-07). |
| G6 | **Podman and Quadlet** | All container lessons are Docker/Compose mechanics: profiles that exit 0 on nothing (2026-08-22-rollback-consolidation.md), restart-counter semantics (2026-10-05-electrs-0.11-index-removed.md), `depends_on` ignored after a power loss (2026-09-30-node-power-buttons.md), single-file bind mounts (2026-10-02-tor-control-password-rotation.md), the docker group as root (2026-10-06-request-values-never-reach-a-shell.md). | Each re-verified on Podman/Quadlet: stop grace and PID-1 signal delivery (LN-01), restart counters (HEAL-05, HEAL-10), start ordering after a crash (PLAT-06), cgroup memory accounting (PLAT-04), rootless runtime access for the backend (EXEC-08). |
| G7 | **Live drills of recovery paths** | Never exercised live in the old node: the automatic rollback of a failed upgrade (a manual rollback was done by hand once; 2026-08-08-one-click-infra-upgrades.md, 2026-10-03-upgrades-cannot-break-a-service.md), an engine switch (2026-08-10-bip110-invalid-mark-leak.md), drive unmount and remount (2026-09-17-self-heal-p2-backup-drive-signals.md), the cookie-cascade skip (2026-09-26-cascade-skip-restarted.md), the deadlock fix on real systemd (2026-10-09-upgrade-deadlock-and-progress.md). | A non-mainnet stack on which each recovery path is drilled end to end and recorded before it is trusted on mainnet (UPG-03). |
| G8 | **Novice operation without a command line** | Several fixes took effect only after an owner sudo step: the proxy config (2026-09-28-runtime-dependency-vulnerabilities.md), a host-service restart (2026-10-02-knowledge-store-one-name-one-guide.md), token rotation (2026-09-16-rust-alert-delivery-and-owner-token.md), a unit reinstall (2026-10-09-upgrade-deadlock-and-progress.md). | Every maintenance and recovery action the node offers is reachable from the UI behind step-up (EXEC-03), and recovery from a failed update needs no shell. |
| G9 | **Watchtower and wallet unlock** | The node had no registered watchtower, and LND auto-unlock depended on a password file on disk (2026-08-23-runbook-command-audit.md). | An explicit owner choice for the unlock model; watchtower registration and its health shown and alerted (LN-02, EVID-06). |
| G10 | **Two-node coordination** | The route receiving another node's data (`/consensus/receive`) had no signature check in its handler and relied on the transport gate; in loginless mode a peer would have needed an owner password, so inter-node consensus was likely not working in that mode (2026-08-23-gate-executor-and-fund-twins.md). | A decision on whether the x86 and Pi nodes exchange anything; if they do, signed messages with forged- and replayed-message tests (EXEC-07). |
| G11 | **Index disk planning on small SSDs** | The owner asked for a plan "for nodes with limited SSD" when an Electrs index rebuild needed two indexes side by side; it is still owed (2026-10-03-electrs-0.12-support.md). | A disk-budget check before any index-format upgrade and a plan for nodes that cannot hold two indexes (UPG-11). |
| G12 | **Agent payments and the marketplace** (L402, agent mandates, the ledger, listings, reputation, auctions, discovery) | The previous repository's `commerce-service` (28,294 lines of Rust at 3bbbe392) has no build record covering its behaviour (the old records that name it do so in dependency or deployment notes), so no lesson of it reached sections 2 to 6; §7 below harvests it at module level. Its BLUEPRINT marks Tracks E, J, K, M and N complete, but its "AI agent payment safety" phase (Track L, phase D: a signed `agent_id` attestation and a cross-node agent payment test) was queued and never done, its two-node arc never passed, its two acceptance scripts drive mock settled-invoice lookups rather than Lightning settlement (their README: "End-to-end Lightning settlement" is not verified), and hold-invoice collateral returned errors on the node's own adapter path (`reconcile/mod.rs`: "holds are unbacked"). The agent identity is a self-asserted string behind one shared HMAC write key. | On a test network, through the real entry point: a mandate-bound payment within and above its allowance; revocation, forgery, expiry and replay refused; two requests racing for the same headroom; a reservation that survives an update and a rollback; a ledger-versus-LND divergence detected and the mandates suspended (the stage 9 drill); two nodes publishing, buying and reviewing, forged items refused, a wash-trading ring scored below the trusted tier, an auction settled with real hold invoices (the stage 10 drill). Plan: `docs/architecture/agent-payments-and-marketplace-plan.md`. |

## 6. Coverage

All 114 records, in date order, with the number of lessons harvested from each and the requirements they fed.

| # | Record | Lessons | Requirements fed |
|---|---|---|---|
| 1 | 2026-08-08-one-click-infra-upgrades.md | 3 | UPG-01, UPG-07, UPG-11 |
| 2 | 2026-08-08-sudo-rs-sudoers-wrappers.md | 3 | EXEC-08, TEST-07, PLAT-01 |
| 3 | 2026-08-10-bip110-invalid-mark-leak.md | 4 | EVID-06, PLAT-04, PLAT-08, PLAT-09 |
| 4 | 2026-08-10-crashloop-detection.md | 2 | HEAL-04, HEAL-10 |
| 5 | 2026-08-10-upgrade-reboot-compose-race.md | 5 | OWN-02, OWN-05, AI-06, TEST-02, TEST-03 |
| 6 | 2026-08-16-mempool-oom-recurrence.md | 1 | PLAT-04 |
| 7 | 2026-08-19-os-update-false-fail.md | 1 | UPG-12 |
| 8 | 2026-08-22-mempool-page-stale-explorer-and-zero-fees.md | 5 | EVID-01, HEAL-10, UPG-02, UPG-07, LN-07 |
| 9 | 2026-08-22-rollback-consolidation.md | 7 | EVID-06, IDEN-01, OWN-01, HEAL-02, UPG-02, UPG-07, AI-09 |
| 10 | 2026-08-23-auth-gate-case-bypass.md | 1 | EXEC-02 |
| 11 | 2026-08-23-gate-executor-and-fund-twins.md | 5 | EXEC-02, EXEC-07, AI-03, TEST-01, TEST-03 |
| 12 | 2026-08-23-loginless-over-gating.md | 2 | EXEC-02, AI-01 |
| 13 | 2026-08-23-remove-terminal-page.md | 3 | EXEC-04, AI-07 |
| 14 | 2026-08-23-runbook-command-audit.md | 7 | EVID-02, HEAL-04, FUND-01, LN-02, LN-07, TEST-09 |
| 15 | 2026-08-24-ai-emergency-stop-actually-stops.md | 3 | AI-03, TEST-01 |
| 16 | 2026-08-24-stepup-binding-onion-socket-redgate.md | 5 | EXEC-02, EXEC-03, EXEC-05, TEST-04, TEST-07 |
| 17 | 2026-09-02-os-update-banner-staleness.md | 2 | EVID-04, AI-06 |
| 18 | 2026-09-02-rag-relevance-calibration.md | 3 | EVID-06, AI-07, TEST-08 |
| 19 | 2026-09-03-mdns-local-name-docker-bridge.md | 2 | PLAT-01 |
| 20 | 2026-09-14-guardian-scb-restart-loop.md | 3 | HEAL-04, FUND-04, TEST-08 |
| 21 | 2026-09-14-rate-limiter-ipv6-lan-trust.md | 1 | EXEC-07 |
| 22 | 2026-09-14-script-style-test-conversion.md | 5 | HEAL-04, TEST-04, TEST-06 |
| 23 | 2026-09-14-settings-decomposition.md | 1 | TEST-10 |
| 24 | 2026-09-16-backup-device-config-store.md | 2 | FUND-05, EXEC-01 |
| 25 | 2026-09-16-backup-truth-and-alerts.md | 4 | FUND-01, FUND-03, FUND-04, TEST-01 |
| 26 | 2026-09-16-drb-attempt-budget-and-escalation.md | 3 | HEAL-03 |
| 27 | 2026-09-16-owner-notification-delivery.md | 6 | HEAL-03, HEAL-09, PLAT-02 |
| 28 | 2026-09-16-rust-alert-delivery-and-owner-token.md | 5 | HEAL-09, EXEC-07, SEC-01, SEC-02, PLAT-05 |
| 29 | 2026-09-16-self-heal-p0-live-repairs.md | 3 | OWN-06, AI-05, TEST-08 |
| 30 | 2026-09-17-drb-schema-gate.md | 3 | HEAL-04, HEAL-05, TEST-06 |
| 31 | 2026-09-17-self-heal-p2-backup-drive-signals.md | 4 | FUND-01, FUND-07 |
| 32 | 2026-09-17-self-heal-p2-honest-executor.md | 4 | HEAL-02, HEAL-04, EXEC-01 |
| 33 | 2026-09-17-self-heal-p2-probes-and-selection.md | 4 | IDEN-03, HEAL-05, PLAT-06 |
| 34 | 2026-09-17-self-heal-p3-approvals.md | 5 | HEAL-07, TEST-01 |
| 35 | 2026-09-17-self-heal-p3-one-monitor.md | 3 | OWN-07, EXEC-05 |
| 36 | 2026-09-18-guardian-page-and-rust-detectors.md | 4 | HEAL-01, HEAL-02, HEAL-06 |
| 37 | 2026-09-18-self-heal-p3-incident-record.md | 3 | HEAL-01, HEAL-06 |
| 38 | 2026-09-20-agent-mcp-gateway.md | 3 | AI-02, TEST-08, TEST-09 |
| 39 | 2026-09-20-consensus-decision-p2.md | 3 | IDEN-03, OWN-09, EXEC-02 |
| 40 | 2026-09-20-consensus-upgrade-guard.md | 2 | UPG-06, EXEC-04 |
| 41 | 2026-09-20-engine-cards.md | 1 | OWN-09 |
| 42 | 2026-09-20-invisible-buttons.md | 2 | TEST-02, TEST-10 |
| 43 | 2026-09-20-knots-repin-and-gate.md | 4 | UPG-06, AI-09, TEST-04, PLAT-09 |
| 44 | 2026-09-20-posture-clarity.md | 1 | OWN-09 |
| 45 | 2026-09-20-postures-per-engine.md | 2 | TEST-01, PLAT-07 |
| 46 | 2026-09-20-relay-postures-c2c3.md | 3 | OWN-09, PLAT-07 |
| 47 | 2026-09-20-relay-profiles-c1.md | 4 | TEST-04, PLAT-06, PLAT-07 |
| 48 | 2026-09-22-ai-native-sdlc-controls.md | 1 | TEST-12 |
| 49 | 2026-09-22-knots-pin-review.md | 4 | EVID-02, EVID-04, UPG-06, TEST-03 |
| 50 | 2026-09-22-posture-panel-frontend-test.md | 1 | TEST-10 |
| 51 | 2026-09-23-ci-shared-deps.md | 1 | TEST-05 |
| 52 | 2026-09-23-posture-restart-to-apply.md | 6 | EVID-04, EVID-09, OWN-05, EXEC-03, TEST-05 |
| 53 | 2026-09-24-lnd-sync-stall-misclassified.md | 5 | EVID-06, IDEN-03, HEAL-06, LN-03 |
| 54 | 2026-09-25-electrs-mempool-clean-stop.md | 2 | IDEN-01, LN-01 |
| 55 | 2026-09-25-guard-self-disable-hole.md | 1 | TEST-11 |
| 56 | 2026-09-25-lesson-gates.md | 2 | UPG-09, TEST-12 |
| 57 | 2026-09-25-lnd-clean-stop.md | 2 | LN-01, SEC-01 |
| 58 | 2026-09-26-cascade-skip-restarted.md | 1 | LN-04 |
| 59 | 2026-09-26-exact-container-target.md | 3 | IDEN-01, IDEN-02, UPG-09 |
| 60 | 2026-09-26-guard-owner-relaxations.md | 1 | TEST-12 |
| 61 | 2026-09-26-health-exact-container-names.md | 4 | EVID-01, EVID-08, IDEN-01, LN-02 |
| 62 | 2026-09-26-lnd-rpccookie.md | 3 | LN-01, LN-04, SEC-01 |
| 63 | 2026-09-26-memory-restart-asks-for-funds.md | 6 | HEAL-07, UPG-09, UPG-10, LN-02, TEST-03 |
| 64 | 2026-09-26-mempool-api-memory.md | 6 | UPG-09, TEST-05, TEST-07, PLAT-04 |
| 65 | 2026-09-27-control-plane-restart-free.md | 1 | TEST-12 |
| 66 | 2026-09-27-guard-profiles.md | 1 | TEST-12 |
| 67 | 2026-09-28-dep-audit-sees-what-github-sees.md | 3 | SEC-06, TEST-05 |
| 68 | 2026-09-28-fix-lock-covers-inline-tests.md | 4 | TEST-07, TEST-11 |
| 69 | 2026-09-28-repairs-outlive-the-request.md | 6 | OWN-08, HEAL-08, HEAL-09, FUND-04 |
| 70 | 2026-09-28-runtime-alerts-round-two.md | 3 | UPG-09, SEC-05, TEST-09 |
| 71 | 2026-09-28-runtime-dependency-vulnerabilities.md | 5 | UPG-09, SEC-05, SEC-06, TEST-05, PLAT-11 |
| 72 | 2026-09-29-btc-price-exchanges-first.md | 6 | EVID-05, LN-07, AI-04 |
| 73 | 2026-09-29-market-cap-volume-etf-warm.md | 4 | EVID-05, EVID-06, AI-08 |
| 74 | 2026-09-29-market-intel-freshness-arkb.md | 7 | EVID-05, EVID-06 |
| 75 | 2026-09-30-bluetooth-revive-at-boot.md | 5 | TEST-03, TEST-12, PLAT-05, PLAT-10 |
| 76 | 2026-09-30-dashboard-measurements.md | 14 | EVID-01, EVID-02, EVID-03, EVID-06, EVID-07, EVID-08, EVID-09, AI-04, AI-08, PLAT-02, PLAT-08 |
| 77 | 2026-09-30-dashboard-page-truth.md | 27 | EVID-01, EVID-02, EVID-03, EVID-06, EVID-07, OWN-02, OWN-04, OWN-08, UPG-01, UPG-09, LN-09, AI-04, AI-09, AI-10, TEST-02, TEST-04, TEST-09, TEST-10, TEST-11, PLAT-08 |
| 78 | 2026-09-30-node-power-buttons.md | 12 | OWN-01, OWN-02, OWN-04, OWN-08, UPG-09, LN-01, LN-05, EXEC-03, SEC-02, PLAT-06 |
| 79 | 2026-09-30-reliability-uptime-truth.md | 14 | EVID-02, EVID-10, IDEN-01, OWN-06, UPG-09, AI-06, AI-07, AI-08, TEST-07, TEST-11, PLAT-08 |
| 80 | 2026-10-02-channel-backup-after-open-close.md | 7 | EVID-06, FUND-02, FUND-04, FUND-06, LN-01, TEST-05 |
| 81 | 2026-10-02-cleanups-dead-security-tabs-flaky-test.md | 3 | EXEC-04, TEST-01 |
| 82 | 2026-10-02-concept-cards-fit-slim-budget.md | 3 | AI-06, AI-09, AI-10 |
| 83 | 2026-10-02-guardian-summaries-reach-the-owner.md | 5 | OWN-05, OWN-09, HEAL-09 |
| 84 | 2026-10-02-knots-overlay-parses.md | 2 | PLAT-07 |
| 85 | 2026-10-02-knowledge-store-one-name-one-guide.md | 4 | UPG-09, AI-10 |
| 86 | 2026-10-02-slim-path-searches-docs-when-no-card.md | 5 | IDEN-03, AI-06, AI-07 |
| 87 | 2026-10-02-tor-control-password-rotation.md | 2 | SEC-02, SEC-03 |
| 88 | 2026-10-03-electrs-0.12-support.md | 14 | OWN-02, HEAL-04, UPG-03, UPG-04, UPG-09, UPG-10, UPG-11, TEST-02, PLAT-04, PLAT-07 |
| 89 | 2026-10-03-fix-lock-per-session.md | 2 | TEST-11, TEST-12 |
| 90 | 2026-10-03-inline-patch-beside-held-line.md | 1 | UPG-04 |
| 91 | 2026-10-03-remove-community-issue-collection.md | 1 | EVID-06 |
| 92 | 2026-10-03-smoke-catches-broken-native-modules.md | 1 | PLAT-03 |
| 93 | 2026-10-03-ubuntu-26.04-upgrade.md | 4 | OWN-04, PLAT-03 |
| 94 | 2026-10-03-upgrade-gates-round-2.md | 8 | EVID-03, OWN-01, UPG-04, UPG-05, TEST-01, PLAT-04 |
| 95 | 2026-10-03-upgrades-cannot-break-a-service.md | 10 | UPG-01, UPG-03, UPG-04, UPG-05, EXEC-08, SEC-01, TEST-06 |
| 96 | 2026-10-04-config-tamper-notifies-owner.md | 5 | HEAL-07, HEAL-09, SEC-04, TEST-02, PLAT-05 |
| 97 | 2026-10-04-gates-run-on-the-commit.md | 1 | TEST-06 |
| 98 | 2026-10-04-guard-secret-searches-and-inline-targets.md | 5 | AI-02, TEST-07, TEST-11 |
| 99 | 2026-10-04-remove-mcp-data-collector.md | 2 | EVID-06, AI-02 |
| 100 | 2026-10-04-remove-model-warmup-and-post-ibd.md | 4 | OWN-09, UPG-09, TEST-03, TEST-09 |
| 101 | 2026-10-05-electrs-0.11-index-removed.md | 3 | HEAL-05, UPG-03 |
| 102 | 2026-10-05-guard-interpreter-writes-inline-tests.md | 2 | TEST-11 |
| 103 | 2026-10-05-usb-backup-run-media.md | 8 | HEAL-02, FUND-01, FUND-02, EXEC-01, TEST-02, TEST-05, TEST-08, PLAT-02 |
| 104 | 2026-10-06-eject-outcome-not-from-label.md | 5 | IDEN-01, FUND-07, EXEC-06, TEST-01 |
| 105 | 2026-10-06-health-check-parallel-stats.md | 4 | EVID-09, OWN-08, LN-06 |
| 106 | 2026-10-06-nginx-socket-io-location.md | 3 | TEST-02, TEST-12, PLAT-11 |
| 107 | 2026-10-06-request-values-never-reach-a-shell.md | 14 | IDEN-01, LN-06, LN-08, EXEC-01, EXEC-08, AI-01, AI-10, TEST-01, TEST-03 |
| 108 | 2026-10-07-money-routes-not-cut-by-watchdog.md | 3 | LN-06, EXEC-02 |
| 109 | 2026-10-07-storage-routes-known-drives-only.md | 3 | EXEC-02, EXEC-06 |
| 110 | 2026-10-08-assistant-execution-paths.md | 5 | IDEN-03, SEC-01, AI-01, AI-03, TEST-03 |
| 111 | 2026-10-08-tests-restarted-live-lnd.md | 7 | IDEN-02, OWN-05, OWN-06, LN-03, TEST-01 |
| 112 | 2026-10-09-health-score-never-freezes.md | 3 | EVID-04, EVID-09 |
| 113 | 2026-10-09-upgrade-deadlock-and-progress.md | 9 | OWN-01, OWN-03, UPG-09, UPG-12, TEST-01, TEST-03, PLAT-05, PLAT-06 |
| 114 | 2026-10-10-upgrades-survive-code-updates.md | 4 | UPG-08, SEC-03 |

## 7. The commerce service, a module-level harvest (2026-10-17)

**Why this section exists.** Sections 2 to 6 were harvested from the previous repository's build records. Its `commerce-service` (L402 payments, agent wallets, the marketplace, auctions, a signed registry, a DHT) has no build record covering its behaviour (the old records that name it do so in dependency or deployment notes): its work was tracked in `docs/plans/BLUEPRINT.md` as tracks marked complete, so nothing of it reached this register, and `git grep -c commerce-service` on this file gave 0 before today. The [agent payments and marketplace plan](../architecture/agent-payments-and-marketplace-plan.md) (stages 9 and 10) rests on what that code shows, so this section records it at module level: what each module's source says it does, the tests it has, and a provisional verdict. Per-file port verdicts in the form of section 4 are owed before stage 9 opens (that plan's decision E8). Nothing here is a requirement: requirements come from incidents, and this code has none recorded.

**Method.** Read with `git -C /home/junc/rikuri/rikurinode show HEAD:<path>` at 3bbbe392 (2026-10-10); lines by `wc -l`; inline tests by counting `#[test]` and `#[tokio::test]` in `src/`, integration tests the same way in `tests/`. The old CI workflow runs `cargo test --workspace`; whether its last run was green was not checked.

**Evidence, stated once.** No build record covering its behaviour; no payment on any network recorded; BLUEPRINT's Track L ("2-Node Validation Arc", opened 2026-05-12) lists the agent-payment-safety phase as queued and the two-node acceptance as not reached; the two acceptance scripts (`acceptance/wash_trading_ring.sh`, `acceptance/flyby_agent.sh`) run against a live HTTP surface but, by their README, use the mock settled-invoice lookup and do not verify Lightning settlement or at-rest encryption; `reconcile/mod.rs` says hold invoices were unbacked on the node's own adapter path. Everything below is therefore **Not yet proven** for the new node, whatever the old plan called it.

| Module (old path under `commerce-service/src/`) | Lines | Tests inline / integration | What its source says it does | Provisional verdict |
|---|---|---|---|---|
| `l402/` | 2,226 | 10 / 2 (`tests/registry_l402_settled_e2e.rs`) | Consumer and provider of L402 through the adapter trait: detects `402`, pays, retries with token and preimage, caches proofs; issues tokens and invoices for gated endpoints and validates proofs statelessly; a settled-invoice store that review verification consumes | Specification for stage 9's payment pipeline and stage 10's selling; re-check against the L402 documentation and the pinned LND; no code ported |
| `agent_wallet/` | 3,628 | 23 / 5 (`tests/agent_wallet_hmac_http.rs`) | Per-agent, per-currency daily budgets; spending and revenue logs; pending approvals for over-budget requests; a "net-positive" mode with a 14-day grace; one shared HMAC key gating every mutating route when configured, else the loopback bind; "similar buyers also bought" by Jaccard similarity; a yield-protocol trait with no implementation | Budgets, logs and approvals: specification for the treasury (plan §4.1), with the identity model replaced by signed mandates (plan E4); recommendations: stage 10 at most; yield protocol: do not port |
| `marketplace/` | 6,380 | 109 / 25 (`tests/marketplace_http.rs` 8, `tests/republish_hmac_http.rs` 11, `tests/bolt12_decode_http.rs` 6) | The AI operator surface: an append-only event stream for the AI to read; proposals (price change, listing edit, fraud flag, rebalance hint) the operator approves and Rust applies; re-sign-and-republish of listings; a rebalance executor with per-call and daily caps and five safety gates, and its history; BOLT12 offer decoding (paying one was blocked on the LND client) | Proposals and apply: specification for stage 7's controller and stage 9's approval queue; the executor's gates as stage 7 test cases, under gap G1; BOLT12 only when the pinned LND offers it |
| `auctions/` | 4,061 | 47 / 5 (`tests/auction_api_http.rs`) | Data model; sealed second-price settlement; a three-round premium auction; REST API with signed bids; agent auto-bid policies with caps; hold-invoice collateral per bid | Specification for stage 10's auctions; collateral proven against the pinned LND's hold invoices first, since it never was |
| `registry/` | 6,155 | 60 / 11 (`tests/registry_http_roundtrip.rs` 4, `tests/registry_funding_listings_http.rs` 4, `tests/registry_reviews_http.rs` 3) | The marketplace's security gate: secp256k1 signature recovery and LND's zbase32 signatures; pubkey ownership by challenge-response (60-second nonce); single-use nonces over a 24-hour window; funding proof against a UTXO; signed listings and reviews bound to settled payments; tiers with counterparty diversity; a 30-day key migration; an append-only audit trail; per-key rate limits | Keep as design (plan §4.4); its tests and the two acceptance scripts as stage 10 test cases; signature formats re-checked against the pinned LND |
| `service_registry/` | 2,904 | 3 / 0 | An earlier registry (entities, anchors, a Merkle tree, a listing signer, sync); `main.rs` says its routes are not mounted, "no callers" | Do not port: superseded by `registry/` in the old code itself |
| `dht/` | 1,688 | 14 / 5 (`tests/dht_routes_http.rs`) | libp2p Kademlia with mDNS; publishing and ingesting listings and reviews with signature verification before upsert | Specification for stage 10's discovery after the bootstrap decision (plan E3); two nodes at most in the old record |
| `reconcile/` | 87 | 0 / 0 | A status route and a sweep that expires stale pending approvals, freeing the budget they reserved by denying the spend, "the conservative default" | Keep the default: an unanswered approval releases its reservation (plan §4.1, pipeline step 5) |
| `hmac.rs`, `at_rest.rs`, `main.rs`, `lib.rs` | 1,165 | not counted | HMAC-SHA256 over path and body for write routes; an AES-256-GCM at-rest helper whose wiring into the L402 files was follow-up work; the binary on loopback 8089 speaking to the host node over an HMAC-authenticated HTTP adapter | At-rest encryption of cached proofs stays a requirement (plan §4.2); the HMAC write gate is replaced by signed mandates (plan E4) |
| `ln-host-adapter/` (a sibling crate) | 1,951 | 2 integration test files | The adapter trait (add and pay invoices, sign and verify messages, host pubkey, circular rebalance, hold invoices, BOLT12 decode) with LND-direct, Core Lightning, generic JSON-RPC, tapd and Bitcoin RPC adapters | Keep the trait's surface as the design of the treasury's door; the adapters are not ported, because the control plane generates its own LND client (platform plan D3) |

Totals: 28,294 lines in `commerce-service/src/`; 266 inline tests and 53 integration tests counted; 2 acceptance scripts. Plan documents read beside the code: `docs/plans/BLUEPRINT.md` (Tracks E, J, K, L, M, N), `docs/plans/UniversalAgenticPayment.md`, `docs/plans/AGENT-COMMERCE-VISION.md`, `docs/plans/MARKETPLACE-PLAN.md`, `docs/L402/`, `docs/knowledge/services/lightning-marketplace.md`.
