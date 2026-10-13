# Verifier report — B0.1 (docs/build-records/2026-10-12-b0-1-control-plane-workspace.md)

Round 1, 2026-10-13, the `verifier` subagent (Claude Code, Fable 5.1), inside the
sandbox, on the staged tree at HEAD 678b1b8. Its own scripts and outputs
(`verify-gate.out`, `verify-probe.sh`, `verify-mutants.sh`, `verify-mutant9.sh`)
are copied beside this file. Reproduced verbatim from its hand-back.

---

Checkout: /home/junc/claude-wip/b0/rn, branch b0/workspace, HEAD 678b1b8; the change is staged (29 files, `git diff --cached` sha256 2e1da64c… unchanged from start to end of this run; `git diff --stat` between working tree and index empty at the end; no index operation, no commit, no push). Every test and the daemon ran through `scripts/quality/safe-run.sh`, cargo only as `scripts/cargo.sh`. The live-node start-time check: I did not run `docker inspect` (your instruction forbids docker here and the sandbox has no socket); `safe-run.sh` printed "no live node containers found here; the start-time check had nothing to compare" on every run — Not yet proven by me, by design of the sandbox.

## Acceptance line (§1 "I will know this works when")

- (a) full gate passes locally with its two new steps and three tool checks — **Pass** (below). Same gate green in CI on the PR — **Not yet proven** (no PR yet; the record says so itself).
- (b) `cargo test` inside `safe-run.sh`, status route through a real loopback socket — **Pass** (step 8: 14 + 5 tests; `serves_over_a_real_loopback_socket_and_stops_on_request ... ok`, followed by safe-run's "nothing to compare" line).
- (c) daemon under `safe-run.sh` answers `GET /api/status` with `overall: "unknown"`, four components `unknown` with `checked_unix: null`, refuses `0.0.0.0:8080` — **Pass** (reproduced).
- (d) planted lint, test failure and unpinned licence each fail the gate, restored byte for byte — **Pass** (record's `mutants.out` consistent; plus 9 mutations of my own, 8 caught, 1 missed — see step 3).

## 1. Gate — Pass

`scripts/quality/full-gate.sh` → exit 0, `full-gate: all 9 steps passed` (full output: /tmp/claude-1000/verify-gate.out). Step 2: `Ran 91 tests … OK`; step 3: `Ran 80 tests … OK`, `Ran 28 tests … OK`; step 7: `49 commits scanned … no leaks found`; step 8: `14 passed; 0 failed` (lib), `5 passed; 0 failed` (tests/status_route.rs), 0 in main.rs, 0 doc-tests; step 9: `advisories ok, bans ok, licenses ok, sources ok`. Matches `gate.out` in the evidence folder number for number. No failing line.

Pinned-tool checks (step 1), probed in a scratch git repo at /tmp/claude-1000/verify-gate-tc holding only `scripts/quality/full-gate.sh`, `scripts/cargo.sh` and a `rust-toolchain.toml`:
- `channel = "stable"` (installed) → exit 1, `full-gate: cargo stable required (rust-toolchain.toml; rustup installs it), found '1.92.0'` — the check reads the file. **Pass**
- `channel = '1.98.1'` (single quotes, valid TOML) → exit 1, `full-gate: rust-toolchain.toml names no channel` — fails closed. **Pass** (nit: TOML single quotes are not read).
- the real file → step 1 passed, step 2 failed on the missing guard files (expected in a scratch copy). **Pass**
- no file → exit 2, `sed: can't read rust-toolchain.toml: No such file or directory` — fails closed, with sed's message not the gate's. **Pass** (nit).

## 2. Real entry point — Pass

Built: `scripts/cargo.sh build --locked --offline --manifest-path control-plane/Cargo.toml -p rikuri-control-plane` → exit 0 (binary sha256 9de95d83…, unchanged after all mutations).

Record's probe (`safe-run.sh sh …/probe-daemon.sh <bin>`) → exit 0, output equal to `probe-daemon.out` except timestamps: `HTTP/1.1 200 OK`, `content-type: application/json`, `cache-control: no-store`, body with `"overall":"unknown"` and four `"state":"unknown","checked_unix":null` components, `"version":"0.1.0"`; `/nope` → 404; `POST /api/status` → 405; SIGTERM → `SIGTERM received: stopping`, `control plane stopped`, exit 0. Refused: `RIKURI_LISTEN=0.0.0.0:8080` → `ERROR … RIKURI_LISTEN=0.0.0.0:8080 is not a loopback address: until TLS and sign-in exist, the control plane listens only on 127.0.0.0/8 or ::1`, exit 1; `localhost:8080` → `… is not an ip:port such as 127.0.0.1:8080`, exit 1. Bad `RUST_LOG` → `ERROR … RUST_LOG is not a valid filter; logging at info error=invalid filter directive`, daemon runs, SIGINT → exit 0 (the record's one fallback, triggered and reported).

My probe (/tmp/claude-1000/verify-probe.sh, inside safe-run): HEAD → 200; OPTIONS → 405; `/api/status/` → 404; `/api/status?x=1` → 200; `/API/STATUS` → 404; `/` → 404; HTTP/1.0 → 200; garbage request line → `HTTP/1.1 400 Bad Request`; a 60 KB header → 400, daemon stays up (200 KB and 1 MB headers: Not yet proven, curl's `-H @file` could not read them); 50 concurrent GETs → all 200; two GETs 2 s apart → `uptime=1` then `uptime=3`, `observed_unix` moved (computed per request, not cached); keep-alive connection open at SIGTERM → client got `HTTP/1.1 200 OK`, daemon exit 0; second instance on the busy port → `ERROR … error=Address already in use (os error 98)`, exit 1. Listen policy accepted and bound: `127.0.0.1:0` (`bound=127.0.0.1:38101`), `127.255.255.255:8080`, `[::1]:8080`, `127.0.0.1:1`. Refused, exit 1, each with the message naming `RIKURI_LISTEN` and the default: `''`, `' '`, `'127.0.0.1:8080 '`, `127.0.0.1:65536`, `::1:8080`, `http://127.0.0.1:8080`, `127.0.0.1:8080,127.0.0.1:8081`, `0:8080`, `127.1:8080` (all "is not an ip:port"); `[::ffff:127.0.0.1]:8080` and `10.0.0.1:8080` ("is not a loopback address"); a non-UTF-8 value → `RIKURI_LISTEN is not valid UTF-8`.

Secrets in body or logs: the body holds `observed_unix`, `overall`, `control_plane{version,pid,started_unix,uptime_seconds}` and four component states/details; the logs hold the bound address, version and error text. No key, path, environment dump or credential. **Pass**, with two nits (code) below.

PR #7's proofs reproduced: `stat -c %F ~/.git-credentials` → `character special file` (type only); `scripts/cargo.sh fetch` on a scratch crate pinning `itoa = "=1.0.14"` → `Downloaded itoa v1.0.14`, exit 0, into `.cargo-home/registry/cache/index.crates.io-1949cf8c6b5b557f/`, nothing in `git status`. **Pass**

## 3. Trying to break it

Mutations of my own (/tmp/claude-1000/verify-mutants.sh and verify-mutant9.sh; each restored from a backup; sha256 before = after for listen.rs 1e8658f1…, http.rs a5e92ee2…, status.rs efd8451c…, lib.rs 233f69f3…, Cargo.lock 87c60d30…, Cargo.toml 65fa42d0…, repo_hygiene.py db214471…; git status afterwards shows only the staged states):
- V1 `listen` also accepts unspecified addresses → `other_addresses_are_refused` and `errors_say_what_to_fix` FAILED, exit 101. **Caught**
- V2 `no-store` → `no-cache` → `status_is_never_cached` FAILED. **Caught**
- V3 `unknown` carries `checked_unix: Some(0)` (EVID-02's tripwire) → `unknown_serializes_as_the_word_with_a_null_time` and `the_report_before_any_probe_is_unknown_throughout` FAILED. **Caught**
- V4 empty fold → `Healthy` → `no_components_is_unknown_not_healthy` FAILED. **Caught**
- V5 axum pin `"=0.8.9"` → `"0.8.9"` → `cargo fetch --locked` 0, clippy 0, `cargo deny check` 0 (`advisories ok, bans ok, licenses ok, sources ok`). **MISSED** — nothing in the gate enforces the `=` pins the design (§0b) states; the resolved version is still pinned by Cargo.lock + `--locked`.
- V6 one Cargo.lock checksum altered → `error: checksum for `aho-corasick v1.1.5` changed between lock files`, exit 101. **Caught**
- V7 hygiene rule `"target"` → `"targets"` → `FAIL: test_cargo_output_beside_any_manifest`, `FAIL: test_cargo_output_is_checked_through_the_command_line`, `Ran 26 tests`, `FAILED (failures=2)`. **Caught**
- V8 `pub  mod   http;` → `cargo fmt --check` exit 1, `Diff in …/lib.rs:7`. **Caught**
- V9 `unwrap()` and `println!` in `report()` → clippy exit 101: `error: used `unwrap()` on a `Result` value`, `error: use of `println!``. **Caught**

Hygiene rule through its command line on scratch repos (/tmp/claude-1000/verify-hygiene*): tracked `control-plane/target/debug/app` beside `Cargo.toml` → exit 1 `control-plane/target/debug/app: build output or dependencies`; `crates/x/src/target/mod.rs` and `docs/target/plan.md` → exit 0; a nested member's `crates/x/target/out` → refused; the real checkout → exit 0. **Pass**. A tracked `.cargo-home/` (`.global-cache`, `advisory-dbs/db`, `registry/cache/…/itoa-1.0.15.crate`) → **exit 0, not refused** (see finding W1).

## 4. Diff vs Plan and Spec

Files: every file §1 names changed; nothing planned is missing. Extra: `gate.out`, `mutants.sh/.out`, `probe-daemon.sh/.out` in the evidence folder — declared in §4 as deviations. **Pass**. Protected paths carry the risk note. No guard, hook, sandbox or settings file changed.

Claims checked against evidence: Cargo.lock 66 packages, all 64 external from crates.io — Pass. Direct pins match the lock; each is the newest non-yanked stable version in today's sparse index (axum 0.8.9, tokio 1.53.2, serde 1.0.229, serde_json 1.0.154, tracing 0.1.44, tracing-subscriber 0.3.23, tower 0.5.3, http-body-util 0.1.5) — Pass. cargo-deny 0.20.2: published `.sha256` = archive sha256 = CI's pin `9f12ed4c49936e09b48bf862b595cde2fe64fcbd9d74dfacac6131ca824c8d5f`; archive contains `cargo-deny-0.20.2-x86_64-unknown-linux-musl/cargo-deny`, the path CI installs — Pass. `syn@2.0.119` skip reason: Cargo.lock shows tracing-attributes 0.1.31 → syn 2.0.119, serde_derive 1.0.229 and tokio-macros 2.7.2 → syn 3.0.9 — Pass. `--locked` on fetch, clippy, test, deny (fmt takes none) — Pass. `.gitignore` `/control-plane/target/` and `/.cargo-home/` (git check-ignore) — Pass. `rustup show`: 1.98.1 active via the toolchain file, stable 1.92.0 default — Pass. CI runner ubuntu-24.04 image 20261004 lists Rustup 1.29.1 (README), so the no-argument `rustup toolchain install` is supported — the run itself Not yet proven. The §4/§5 numbers (91/80/28, 14+5, 26 hygiene tests, 2 new cases, status.rs 234 lines) — Pass. PR #7's record now states both proofs with the evidence paths — Pass. `[::ffff:127.0.0.1]` refused as not loopback: consistent with the stated "127.0.0.0/8 or ::1".

## Findings

**Code / test (no defect found; nits, owner's choice):**
- N1 (gate gap, V5): dropping an `=` pin passes every step. If "direct dependencies pinned with `=`" is meant as a rule, nothing holds it.
- N2 (code): `RUST_LOG=off RIKURI_LISTEN=0.0.0.0:8080` exits 1 with nothing on stderr — the refusal is visible only as the exit status when the operator silences logging.
- N3 (code): the Unparsable path logs the `RIKURI_LISTEN` value verbatim (`RIKURI_LISTEN="hunter2@127.0.0.1:8080" is not an ip:port …`); not a secret path today.
- Observation: nine dependency build scripts (httparse, libc, proc-macro2, quote, serde, serde_core, serde_json, valuable, zmij) run during the gate's fetch/clippy outside `safe-run.sh` (inside Claude's sandbox here; unconfined if the gate is run from a plain terminal on this machine). D25 acknowledges build scripts in the sandbox; the owner may want this named.

**Wording (claims vs evidence):**
- W1 (Important per REVIEW.md "claims match evidence"): record §5 Scrap Sweep says "`control-plane/target/` and `.cargo-home/` are ignored and refused by the hygiene check." `.cargo-home/` is ignored but **not** refused: a tracked cargo cache passes `repo_hygiene.py` with exit 0 (above). PR #7's own record lists exactly this as a skipped item ("A cargo cache force-added past .gitignore passes the hygiene check … Reactivate: with B0's gate, if the cache is ever seen staged"). Either the claim goes or a rule comes.
- W2: staged AGENTS.md (sandbox paragraph, lines 116–125) still lists "crates.io's two hosts (shown only outside the sandbox …) and the D25 read denies (not shown anywhere yet …); a sandboxed fetch and a credential path seen as the sandbox's stand-in … are B0's first steps" as Not yet proven — stale now that this record shows both.
- W3: §5 "A first run failed at step 6 on carriage returns in the probe's output" has no evidence file (narrative only; the fix is visible in `probe-daemon.sh`'s `tr -d '\r'`) — Not yet proven.
- W4 (nit): PR #7's record says "Merged as PR #7 (2026-10-13)" while git shows eff4ea9 at 2026-10-12 22:50 -0700; the same record dates the session 2026-10-12 (local). Mixed UTC/local convention.

**Not yet proven:** CI green on the PR; `--offline` turning a missing crate into a failure rather than a hang (would need plain cargo with another CARGO_HOME, which D24 forbids); headers above 60 KB; `rustup` auto-installing 1.98.1 on first use (already installed here).

VERDICT: FAIL — wording only: §5's claim that the hygiene check refuses `.cargo-home/` is false (a tracked cargo cache passes, exit 0, as PR #7's record already lists as a skipped item), and AGENTS.md still marks the sandboxed fetch and the D25 stand-in as not yet proven; code and tests: no defect, three nits (N1–N3) for the owner's choice; CI remains Not yet proven.

Evidence: /tmp/claude-1000/verify-gate.out (gate); /tmp/claude-1000/verify-gate-tc/out.{B,C,D} (toolchain check); /tmp/claude-1000/verify-probe.sh, verify-bighdr.sh (daemon probes; outputs in this report; daemon logs at /tmp/claude-1000/verify-probe.*.log, bighdr.log); /tmp/claude-1000/verify-mutants.sh with backups and per-mutant outputs in /tmp/claude-1000/verify-mutants.VnkV2O/ (v1.out … v8.out), /tmp/claude-1000/verify-mutant9.sh and /tmp/claude-1000/verify-m9.*/v9.out; /tmp/claude-1000/verify-hygiene and verify-hygiene2 (scratch repos); /tmp/claude-1000/verify-cargo-deny-dl/ (published.sha256, cargo-deny.tgz, runner-readme.md); /tmp/claude-1000/verify-index-dl/ and /tmp/claude-1000/newest.py (sparse-index check); /tmp/claude-1000/verify-d24/ (D24 scratch crate). Record's own evidence: /home/junc/claude-wip/b0/rn/docs/build-records/evidence/2026-10-12-b0-1-control-plane-workspace/{gate.out,mutants.sh,mutants.out,probe-daemon.sh,probe-daemon.out,d24-fetch.out,d25-stat.out}. Nothing was written inside the tree except the ignored build output (`control-plane/target/`, `.cargo-home/` gained itoa-1.0.14.crate).
