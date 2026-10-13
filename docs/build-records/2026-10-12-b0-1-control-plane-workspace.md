# Build Record — B0.1: the control plane's workspace, the Rust gate, and a status route that reports unknown as unknown

| | |
|---|---|
| **Date** | 2026-10-12 |
| **Author / session** | Claude Code (Fable 5.1), a session opened in the worktree `/home/junc/claude-wip/b0/rn` in `auto` mode, inside the sandbox; owner Henry |
| **Branch** | b0/workspace (on `main` at 678b1b8 after PRs #4, #5 and #7 merged) |
| **Commits** | 9f94898 on `b0/workspace` (the whole change and this record); 2123c2c (the owner's answers of 2026-10-13); a third commit records CI on PR #8 |
| **Status** | COMPLETE — verifier round 1 FAIL on wording only (W1–W4, corrected here, in AGENTS.md and in PR #7's record; no further round, the owner's stop rule); code and tests: no defect, three nits for the owner (Skipped items; the owner: "ok", 2026-10-13). CI green on pull request #8 at 2123c2c: "Full gate (Ubuntu)" (CI run 38421806229, 1m 47s) and the guard tests on Python 3.9 and 3.12 (run 38421806872, 1m 11s); `ci-pr8.out`. Awaiting the owner's merge |
| **Change type** | feature (the first control plane code) |

## 0. Intent — the owner's words, approved before design
- [x] Problem: every later stage needs the control plane (plan §3.2), and
      there is no Rust code, no Rust gate and no way to build Rust in a
      session yet beyond PR #7's two unproven sandbox settings.
- [x] Outcome (the owner's handoff, 2026-10-12, B0.1): "a Cargo workspace
      (`control-plane/`, one binary crate and a library crate);
      `rust-toolchain.toml` pinned to 1.98.1, which is installed; Cargo.lock
      committed; the gate extended (fmt --check, clippy -D warnings, tests,
      and cargo-deny pinned with licences, advisories and bans); CI
      installing the same pinned tools, checksum-verified like gitleaks; a
      status endpoint that reports unknown as unknown (EVID-02)." And first:
      the two commands that prove PR #7 inside the sandbox, copied into this
      record and PR #7's.
- [x] Who/what it affects: the repository, its gate and CI. No node exists;
      nothing here reaches this machine's live node (the daemon binds
      loopback only and talks to nothing).
- [x] Open questions, answered here and flagged to the owner (§0b):
      (1) until B0.2 brings TLS and sign-in, the daemon serves plain HTTP on
      loopback only and refuses any other address — assumed from the
      owner's split, reversible in B0.2; (2) crate names `rikuri-control`
      (library) and `rikuri-control-plane` (binary); (3) the hygiene check
      learns that a `target` folder beside a `Cargo.toml` is build output.
- [x] Owner approved the intent: the handoff (`~/claude-wip/b0/HANDOFF.md`,
      2026-10-12) and the plan review's §3.2, §3.7, §3.8 with D10–D25
      "all as recommended" (owner, 2026-10-12).

## 0b. Spec — requirements + design, policy applied up front
- [x] Requirements: lessons register EVID-02 (a state that could not be
      read is `unknown`: never 0, healthy, down or all-clear; a check that
      could not run never reads as all-clear), EVID-04 (a reading carries
      its time; "not yet measured" is distinct), EVID-08 (the aggregate is
      honest); Rikuri-PI's evidence standard (versions and ids beside
      outcomes; unknown fields stay explicit); plan §3.8 (supply chain:
      `cargo deny`, every dependency pinned, lockfile committed); AGENTS.md
      "Verification by maturity" (the language's build, lint and test steps
      join with the first code) and "Testing on this machine" (tests run
      through `safe-run.sh`); D24 (`scripts/cargo.sh`, never plain `cargo`).
- [x] Design:
      - `rust-toolchain.toml` at the repository root (rustup reads it from
        any folder of the checkout): 1.98.1, rustfmt and clippy, minimal
        profile. The gate reads the version from this file, so it is spelled
        once, and refuses any other `cargo`.
      - `control-plane/Cargo.toml`: a workspace of `crates/rikuri-control`
        (the logic: `status`, `http`, `listen`) and
        `apps/rikuri-control-plane` (the daemon: logging, the listen
        address from `RIKURI_LISTEN`, SIGTERM/SIGINT). Direct dependencies
        pinned with `=`; `Cargo.lock` committed; `--locked` everywhere.
        Workspace lints: `unsafe_code` forbidden; `unwrap`, `expect`,
        `dbg!`, `todo!`, `unimplemented!`, `println!` and `eprintln!` are
        build errors outside tests (`clippy.toml` allows unwrap/expect in
        tests). The same shape as Rikuri-PI's workspace (ADR 0002: its
        gates can be shared).
      - Dependencies: axum 0.8.9 without its default features (`http1`,
        `json`, `tokio`), tokio 1.53.2, serde 1.0.229, tracing 0.1.44,
        tracing-subscriber 0.3.23 (`env-filter`); for tests only
        serde_json 1.0.154, tower 0.5.3 (`util`), http-body-util 0.1.5. The
        newest non-yanked of each on 2026-10-12 (the sparse index).
      - The status model: `State` is a closed four-state enum (`healthy`,
        `degraded`, `down`, `unknown`); `Component` a closed enum (`os`,
        `bitcoind`, `lnd`, `tor`); a `ComponentStatus` carries `state`,
        `checked_unix: Option<u64>` (`null` until a probe has run, never 0)
        and a plain-words `detail`; `overall()` folds states with `down` >
        `degraded` > `unknown` > `healthy`, and no components at all is
        `unknown`. The report carries `observed_unix`, the control plane's
        `version`, `pid`, `started_unix` and `uptime_seconds`. In B0.1 no
        probe exists, so every component is `unknown` with the detail "not
        probed: no interface to this component exists yet".
      - `GET /api/status` returns the report as JSON with
        `Cache-Control: no-store`; any other path is 404, any other method
        405. `serve()` runs axum with graceful shutdown.
      - `listen::parse` accepts only `ip:port` on loopback (127.0.0.0/8 or
        ::1); a host name, a fragment or any other address is refused with
        a message that names the variable and the default
        (`127.0.0.1:8080`).
      - `control-plane/deny.toml`: advisories (yanked, unmaintained and
        unsound all fail; `ignore` empty), licences (an allow list of
        permissive licences; the workspace's own crates ignored), bans
        (`multiple-versions = "deny"`, no wildcards), sources (crates.io
        only, no git); the graph limited to the two nodes' targets.
      - The gate (`scripts/quality/full-gate.sh`): step 1 also checks
        `cargo` is the toolchain file's version and cargo-deny is 0.20.2;
        step 8 fetches as locked, `fmt --check`, clippy on every target with
        warnings as errors, and `cargo test` through `safe-run.sh` with
        `--offline` (no network inside; a missing crate fails loudly instead
        of hanging); step 9 runs `cargo deny check`.
      - CI (`.github/workflows/ci.yml`): installs the toolchain from
        `rust-toolchain.toml` (`rustup toolchain install`; rustup checks each
        download against the signed channel manifest) and cargo-deny 0.20.2
        from its release archive, SHA-256 checked
        (`9f12ed4c…c8d5f`, the published `.sha256` and the archive itself,
        both read on 2026-10-12), then runs the same gate. Timeout 30 min.
      - `.gitignore` gains `/control-plane/target/`; the hygiene check
        refuses any path inside a `target` folder that sits beside a tracked
        `Cargo.toml` (Cargo's build output), with a test and its neighbour
        (`crate/src/target/mod.rs` stays a module).
      - Rejected: a workspace at the repository root (the owner's handoff
        names `control-plane/`); `cargo` run plain (D24); a time crate for
        RFC 3339 timestamps (Unix seconds carry the same fact without a
        dependency; the UI formats); tower-http for the cache header (one
        header, set in the handler); a `run_id` crate (the pid and start
        time identify the run until B0.2 brings randomness for the claim
        code); reading the listen address from a config file (none exists
        yet; the environment is what a systemd unit sets).
- [x] Policy applied — first principle: the one behaviour-changing default
      is **plain HTTP on loopback only until B0.2**, an assumption from the
      owner's split, stated in the daemon's start-up log line and held by
      a test that refuses any non-loopback address; reversible: B0.2
      replaces the listener (owner: "ok", 2026-10-13). Design rules: every dependency pinned,
      lockfile committed, runtime truth (the report is computed on each
      request, never cached). Security gates: the route carries no secret
      and no authority; it is open to any local process until the route
      policy lands (port 10, B0.3) — accepted for the skeleton, named here.
- [x] Flagged concerns: the loopback assumption above (owner to confirm or
      change at review); the `multiple-versions = "deny"` ban may need
      `skip` entries as the tree grows (each a reviewed change). **Owner,
      2026-10-13: "ok" to both, and to leaving the verifier's three nits as
      they are (Skipped items).**

## 1. Plan
- [x] One sentence: add the Rust workspace with a loopback-only status
      route that reports every component as unknown, and make the gate and
      CI build, lint, test and audit it with pinned tools.
- [x] Blast radius: new `control-plane/` and `rust-toolchain.toml`; the
      gate, CI, `.gitignore`, the hygiene check and its tests (protected
      paths: see the risk note); README and AGENTS.md; PR #7's record. No
      auth, funds, exec or private data: the daemon binds loopback and
      talks to nothing. Nothing irreversible.
- [x] Current behaviour characterized: no Rust anywhere in the tree
      (`find` for `Cargo.toml`, `rust-toolchain*`: none); the gate has 7
      steps and no Rust tool; CI installs gitleaks and shellcheck only;
      `rustup` has 1.98.1 installed with rustfmt and clippy beside a
      default `stable` 1.92.0 (`rustup show`); `cargo-deny 0.20.2` is on
      PATH; `safe-run.sh` starts inside the sandbox (private `/run`,
      loopback only, mapped root). PR #7's two proofs, inside the sandbox:
      see §4 and the evidence folder.
- [x] Files that change, in order: the two proof commands (evidence
      `d24-fetch.out`, `d25-stat.out`) → `git merge --ff-only origin/main`
      → `rust-toolchain.toml`, `control-plane/{Cargo.toml,clippy.toml,deny.toml}`,
      `control-plane/crates/rikuri-control/{Cargo.toml,src/lib.rs,src/status.rs,src/http.rs,src/listen.rs,tests/status_route.rs}`,
      `control-plane/apps/rikuri-control-plane/{Cargo.toml,src/main.rs}`
      → fetch, fmt, clippy, tests, deny (`Cargo.lock` produced) →
      `.gitignore`, `scripts/quality/repo_hygiene.py` and its test →
      `scripts/quality/full-gate.sh`, `.github/workflows/ci.yml` → README,
      AGENTS.md, PR #7's record → the full gate → verifier → PR.
- [x] Risks: the riskiest step is the gate inside the sandbox — `cargo
      test` under `safe-run.sh` (a user namespace inside bubblewrap) and
      `cargo deny` fetching the advisory database through the sandbox's
      proxy; either failing is reported, not worked around. Clippy's deny
      lints may reject idioms in the first code (fixed in the code, never
      by allowing the lint). `rustup toolchain install` with no argument on
      the CI runner needs rustup 1.28 or newer (Rikuri-PI's CI uses the
      same step).
- [x] Verification — I will know this works when: (a) the full gate passes
      locally with its two new steps and the three new tool checks, and
      the same gate is green in CI on the pull request; (b) `cargo test`
      runs inside `safe-run.sh` and the status route is exercised through
      a real loopback socket; (c) the daemon, started under `safe-run.sh`,
      answers `GET /api/status` with `overall: "unknown"` and four
      components each `unknown` with `checked_unix: null`, and refuses to
      start on `0.0.0.0:8080`; (d) a planted lint, a planted test failure
      and a planted unpinned licence each fail the gate (mutations,
      restored byte for byte).

### Risk note (REVIEW.md: protected paths)
`scripts/quality/full-gate.sh` gains the tool checks and two steps; nothing
existing is removed or loosened. `.github/workflows/ci.yml` gains two
install steps (checksum-verified, pinned) and a longer timeout; no step is
`continue-on-error`. `.gitignore` gains one line. `scripts/quality/repo_hygiene.py`
gains one rule (narrower than the folder name alone, with a neighbour test).
README.md and AGENTS.md describe the new state. No guard, hook, sandbox or
settings file changes.

## 2. Build
- [x] New code meets the bar: two closed enums and typed structs; the one
      input that crosses a trust line (`RIKURI_LISTEN`) is parsed and
      refused unless loopback; `unsafe` forbidden, `unwrap`/`expect`/
      `println` are build errors outside tests (the integration test crate
      allows `unwrap` at its top, with the reason: clippy's tests-only
      allowance covers `#[test]` functions, not their helpers); the largest
      file is `status.rs` at about 230 lines.
- [x] Clean as you go: nothing replaced; the D24 fetch probe lived in the
      scratchpad, never in the tree. The one deviation from the first
      design: the licence allow list trimmed to the four licences the tree
      uses (an unused allowance is reported by cargo-deny, so the list says
      what is true), and a reasoned `skip` for `syn 2.0.119` beside
      `syn 3.0.9` (proc-macro crates only: tracing-attributes 0.1.31 is still
      on syn 2 while serde_derive and tokio-macros moved to 3).
- [x] Security question: touches none of auth, money, exec or private
      data. The daemon binds loopback only (the `listen` tests and probe
      refuse `0.0.0.0`, a LAN address, `[::]` and a host name) and reads
      nothing but two environment variables. The status body holds the
      crate version, pid, times and four `unknown` states: no secret, no
      authority. Open to any local process until the route policy lands
      (port 10, B0.3) — named in §0b. Noted by the verifier: nine
      dependency build scripts (httparse, libc, proc-macro2, quote, serde,
      serde_core, serde_json, valuable, zmij) run during the gate's fetch
      and clippy steps outside `safe-run.sh` — inside Claude Code's sandbox
      in a session, unconfined when the gate runs from a plain terminal on
      this machine. D25 names the risk; `Cargo.lock` with `--locked` and
      the review of each new dependency hold it (`safe-run.sh` would add
      no file boundary: it isolates `/run`, the network and processes).

## 3. Debug
- N/A: no defect fixed (a new feature).

## 4. Verify
- [x] PR #7 inside the sandbox (the session's first two commands,
      2026-10-12, `evidence/…/d24-fetch.out`, `d25-stat.out`):
      `scripts/cargo.sh fetch` on a crate pinning `itoa = "=1.0.15"` →
      "Downloaded itoa v1.0.15", exit 0, into the checkout's
      `.cargo-home/registry/cache/index.crates.io-1949cf8c6b5b557f/itoa-1.0.15.crate`;
      `git status` clean. `stat -c %F ~/.git-credentials` → "character
      special file" (outside the sandbox PR #7's record saw a regular
      file). Both as the handoff required.
- [x] Unit tests, including failure paths: 14 in the library (`overall`
      at every boundary — empty, all healthy, one unknown among healthy,
      degraded over unknown, down over everything; `unknown` serializes as
      the word with a `null` time; the report before any probe; components
      keyed by name; the listen policy's accepted, refused and unparsable
      forms, and that its errors name the variable and the default) and 5
      through the router and a real loopback socket (200 with
      `no-store` and four `unknown` components; 404; 405 for POST, PUT and
      DELETE; served and stopped on request). Result inside `safe-run.sh`:
      `19 passed; 0 failed` (`gate.out`, step 8). The hygiene check: 2 new
      cases, 26 in its file, 80 in step 3.
- [x] Watched it work: the daemon built and run inside `safe-run.sh`
      (`probe-daemon.sh` → `probe-daemon.out`): `GET /api/status` → `200`,
      `content-type: application/json`, `cache-control: no-store`, body
      `overall: "unknown"`, four components `unknown` with
      `checked_unix: null`, `version "0.1.0"`; `GET /nope` → 404; `POST
      /api/status` → 405; SIGTERM → "SIGTERM received: stopping", "control
      plane stopped", exit 0. Refused with exit 1 and a plain message:
      `RIKURI_LISTEN=0.0.0.0:8080` ("is not a loopback address …") and
      `localhost:8080` ("is not an ip:port such as 127.0.0.1:8080"). An
      invalid `RUST_LOG` is logged at error and the daemon runs at info;
      SIGINT stops it with exit 0.
- [x] Recovery/fallback path: the only fallback is the log filter (an
      invalid `RUST_LOG` falls back to `info`), triggered in the probe above
      and reported at error level, never silently.
- [x] Regression guard proven to FAIL on a planted fault (`mutants.sh` →
      `mutants.out`; each file restored byte for byte, sha256 equal before
      and after): an unused variable in `report()` → clippy exit 101
      ("unused variable: `unused`"); `unknown` ranked like `healthy` in
      `severity()` → `one_unknown_among_healthy_is_unknown` FAILED, exit
      101; MIT dropped from the licence allow list → cargo-deny exit 4
      ("failed to satisfy license requirements"); the `syn` skip removed →
      bans FAILED, exit 2. The hygiene rule's command-line case plants a
      `control-plane/target/debug/app` beside a `Cargo.toml` in a scratch
      repository and sees it refused (step 3). Not planted: a wrong
      toolchain version (rustup would try to download it).
- [x] Independent verification — verifier round 1 (2026-10-13,
      `verifier-round1.md`; its gate output and scripts `verify-gate.out`,
      `verify-probe.sh`, `verify-mutants.sh`, `verify-mutant9.sh` beside
      it): **FAIL on wording only.** Passed: the full gate (all 9 steps,
      every number equal to `gate.out`); the toolchain check reads the file
      and fails closed on a wrong, a single-quoted and a missing channel;
      the daemon through `probe-daemon.sh` and its own probe (HEAD 200,
      OPTIONS 405, a trailing slash and a different case 404, HTTP/1.0
      200, a garbage request line 400, a 60 KB header 400 with the daemon
      still up, 50 concurrent GETs all 200, the report computed per request,
      a keep-alive connection served through SIGTERM, a busy port refused
      with exit 1; four accepted listen forms bound, thirteen refused forms
      each naming the variable and the default, a non-UTF-8 value refused);
      no secret in body or logs; PR #7's two proofs reproduced; nine
      mutations of its own, eight caught (unspecified addresses accepted,
      `no-cache`, `checked_unix: Some(0)`, an empty fold reading healthy,
      a changed lock checksum, the hygiene rule's name, a format drift,
      `unwrap` and `println!`) and one missed — dropping an `=` pin passes
      every step (N1); the diff matches the plan and the spec; the
      cargo-deny checksum equals the published one. Failed, wording: W1 §5
      claimed `.cargo-home/` is refused by the hygiene check (it is ignored
      only); W2 AGENTS.md still listed the sandboxed fetch and the D25
      stand-in as not yet proven; W3 the first gate run's failure had no
      evidence file; W4 PR #7's merge date. All four corrected here, in
      AGENTS.md and in PR #7's record, with no further round (the owner's
      stop rule: wording only). The nits N1–N3: Skipped items.
- [x] Diff matches the §1 plan. Deviations: `mutants.sh`, `probe-daemon.sh`
      and their outputs added to the evidence folder (the plan named the
      proofs, not the files); the licence list trimmed and the `syn` skip
      added (§2); `Cargo.lock` holds 66 packages.

## 5. Close Out
- [x] Full gate green inside the sandbox: `full-gate: all 9 steps passed`
      (`gate.out`; step 2: 91 guard tests, step 3: 80 quality-tool tests
      and 28 image tests, step 8: 19 Rust tests under `safe-run.sh`, step 9:
      "advisories ok, bans ok, licenses ok, sources ok"). A first run
      failed at step 6 on carriage returns in the probe's output (HTTP's
      line endings: `probe-daemon.out:7: trailing whitespace`); that run's
      output was overwritten by the green run and is not kept, so this
      rests on the session's word; the probe now strips them (`tr -d '\r'`
      in `probe-daemon.sh`). The verifier's own run: `verify-gate.out`, all
      9 steps. CI: seen green on pull request #8 (opened by the owner,
      2026-10-13), commit 2123c2c — "Full gate (Ubuntu)" completed
      successfully (CI run 38421806229, "CI #23", 1m 47s), and the guard
      tests on Python 3.9 and 3.12 (run 38421806872, 1m 11s); `ci-pr8.out`,
      read from GitHub's pages in the owner's browser.
- [x] Scrap Sweep: nothing stray in the tree (`git status`: only this
      change and the sandbox's placeholders). Outside it: the D24 fetch
      probe and the mutants' backups under `TMPDIR`
      (`rikuri-mutants.cgRk1o`), the session's scratchpad.
      `control-plane/target/` is ignored and refused by the hygiene check;
      `.cargo-home/` is ignored only — a cache force-added past
      `.gitignore` passes the check (the verifier saw exit 0; PR #7's
      skipped item, still open: Skipped items).
- [x] Reviewed per `REVIEW.md`: verifier round 1, the three passes (§4).
      The risk note covers every protected path touched. Important: W1, a
      claim without evidence, corrected; none on funds, keys or authority.
- [x] Lesson loop: N/A — no mistake twice, no rule broken. (One for the
      gate, not the guard: HTTP output in an evidence file must have its
      CR LF stripped, or step 6 refuses it; the probe script says so.)
- [x] Knowledge layer: README (requirements, the control plane, how to run
      it), AGENTS.md (status; verification by maturity), PR #7's record
      (the in-sandbox proofs). No help page or runbook exists yet.
- [ ] Commit message explains WHY; record committed with the change

## Skipped items — visible, never silent
- The owner's choice, found by the verifier (round 1), left as is:
  **N1** nothing in the gate holds the `=` form of the direct pins
  (dropping one passes every step; the resolved version stays pinned by
  `Cargo.lock` and `--locked`) — a check that every version under
  `[workspace.dependencies]` starts with `=` would hold it. **N2** with
  `RUST_LOG=off` a refused listen address exits 1 with nothing on stderr.
  **N3** the "is not an ip:port" message repeats the `RIKURI_LISTEN` value
  verbatim (not a secret today). Owner: Henry — "ok", left as is
  (2026-10-13). Reactivate: any of the three on request; N2 and N3 with
  B0.2, where the listener changes.
- A cargo cache force-added past `.gitignore` passes the hygiene check
  (`.cargo-home/`; PR #7's skipped item, re-seen by the verifier). Owner:
  Henry. Reactivate: a hygiene rule for `.cargo-home/` if the cache is
  ever seen staged.
- Seen since: the gate in CI on pull request #8 (CI run 38421806229; its
  step 1 passed there, so the toolchain file's version was active on the
  runner after `rustup toolchain install` with no argument). Still not yet
  proven: `--offline` turning a missing crate into a failure rather than a
  hang; headers above 60 KB; rustup installing 1.98.1 on first use here
  (already installed).

## Evidence log
```
2026-10-12  d24-fetch.out: scripts/cargo.sh fetch → Downloaded itoa v1.0.15, exit 0, into .cargo-home/
            d25-stat.out: stat -c %F ~/.git-credentials → character special file
            git fetch origin; git merge --ff-only origin/main → 08b4ddb..678b1b8 (PRs #4, #5, #7 in the tree)
            workspace: fetch (66 packages locked); fmt; clippy -D warnings clean after the test crate's allow
            safe-run: cargo test → 19 passed; cargo deny → advisories ok, bans ok (the syn skip), licenses ok, sources ok
            probe-daemon.out: 200, no-store, unknown ×4; 404; 405; SIGTERM exit 0; 0.0.0.0 and localhost refused, exit 1;
            a bad RUST_LOG said; SIGINT exit 0
            mutants.out: 4 planted faults caught (clippy 101, tests 101, licences 4, bans 2); restored byte for byte
            gate.out: full-gate: all 9 steps passed (a first run failed at step 6: CR in the probe output; not kept)
2026-10-13  verifier round 1: FAIL on wording only (verifier-round1.md; verify-gate.out: all 9 steps;
            9 mutations, 8 caught, 1 missed = N1); W1–W4 corrected
            committed 9f94898 on b0/workspace, pushed; the owner opens the pull request
            owner: "ok" to the three choices (loopback until B0.2; deny with reasoned skips; N1–N3 left as is)
            PR #8 opened by the owner; on 2123c2c: CI run 38421806229 (Full gate (Ubuntu), 1m 47s) and
            run 38421806872 (guard tests, py3.9 and py3.12, 1m 11s) completed successfully (ci-pr8.out)
```
