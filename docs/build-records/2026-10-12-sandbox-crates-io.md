# Build Record — the sandbox reaches crates.io; cargo's cache stays in the checkout (D24)

| | |
|---|---|
| **Date** | 2026-10-12 |
| **Author / session** | Claude Code (Opus 5.5), in a session opened in Rikuri-PI (outside the sandbox: the sandbox protects its own settings file, so this change cannot be made from inside it); owner Henry |
| **Branch** | sandbox/crates-io |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | ops (the session boundary) |

## 0. Intent — the owner's words, approved before design
- [x] Problem: the next change, B0 (the Rust control plane), cannot build in
      a session opened here: the sandbox reaches only GitHub, and cargo writes
      its download cache under `~/.cargo`, outside the repository.
- [x] Outcome: Rust sessions fetch crates from crates.io inside the sandbox,
      and nothing is written outside the checkout.
- [x] Who/what it affects: every session opened in this repository; CI
      unaffected (its runners already reach crates.io).
- [x] Open questions: none left. Owner, 2026-10-12 (AskUserQuestion, D24):
      "Allow crates.io, cache in repo (Recommended)", over vendoring crates
      or building Rust only in CI.
- [x] Owner approved the intent: the answer above.

## 0b. Spec — requirements + design, policy applied up front
- [x] Requirements: two hosts only — crates.io's sparse index
      (`index.crates.io`) and its download host (`static.crates.io`, the
      index's own `"dl"`); not its API (`crates.io`), no wildcard; cargo's
      cache inside the checkout and ignored by git; a plain `cargo` that
      tries `~/.cargo` fails visibly (the sandbox refuses the write), not
      silently.
- [x] Design: the two hosts added to `.claude/settings.json`'s
      `sandbox.network.allowedDomains` and to the wiring check's exact copy;
      `scripts/cargo.sh` sets `CARGO_HOME` to `<checkout>/.cargo-home` and
      runs cargo (toolchains still come from rustup's folder, read-only);
      `/.cargo-home/` in `.gitignore`. Rejected: `CARGO_HOME` in the
      settings' `env` (the wiring check's variable list would widen, and an
      absolute path differs per worktree; a relative one depends on the
      command's folder); allowing writes to `~/.cargo` (shared with the
      owner's other projects: a session could change sources other builds
      use); vendoring; Rust only in CI (the owner's choice).
- [x] Policy applied: the change is the owner's (D24); the check stays
      closed-world (any other host, a wildcard, or crates.io's API fails the
      gate — two new cases in its tests).
- [x] Flagged concerns: see the risk note.

## 1. Plan
- [x] One sentence: allow crates.io's two hosts in the sandbox and keep
      cargo's cache in the checkout.
- [x] Blast radius: the session boundary (`.claude/settings.json`), the
      gate's closed-world check and its tests, `.gitignore`, the gate's lint
      list, AGENTS.md, a new `scripts/cargo.sh`. No node, funds or runtime.
- [x] Current behaviour: `allowedDomains` is GitHub's three entries
      (`git show 5630ea0:.claude/settings.json`); `.gitignore` has `/target/`
      and nothing for cargo's home.
- [x] Risks: a crate's build script or procedural macro runs at compile
      time inside the sandbox — it can write in the checkout and reach
      GitHub and the two crates.io hosts (GitHub was already reachable;
      crates.io's download host takes no uploads). Held by `Cargo.lock`
      committed, `cargo deny` with B0, and review of each new dependency.
- [x] Verification: the gate (the check accepts the new block and refuses
      wider ones); the wrapper fetches into the checkout (proven outside the
      sandbox here); inside the sandbox — B0's first fetch, recorded there.

### Risk note (REVIEW.md: protected paths)
`.claude/settings.json`, `scripts/quality/check_guard_wiring.py`,
`scripts/quality/tests/test_guard_wiring.py`, `scripts/quality/full-gate.sh`,
`.gitignore` and `AGENTS.md` are protected. The settings and the check widen
the sandbox's network by exactly two hosts, chosen by the owner; nothing
else in the sandbox block changes, and the check still fails on any other
difference. The test file changes its fixture to the new block (necessary:
the fixture is the expected block) and adds two refusal cases; no assertion
was loosened. The gate's lint list gains one file. `.gitignore` gains one
line. AGENTS.md says the new rule where the sandbox is described.

## 2. Build
- [x] Code meets the bar: `scripts/cargo.sh` is `set -euo pipefail`, finds
      the checkout with git, passes its arguments through; shellcheck clean.
- [x] Clean as you go: nothing replaced.
- [x] Security question: yes, it widens the session boundary — covered by
      the owner's decision, the closed-world check and its two new refusal
      cases, and the risk note.

## 3. Debug
- [ ] N/A — no defect fixed.

## 4. Verify
- [x] Outside the sandbox (this session, 2026-10-12, a scratch git repository
      in the session's scratchpad): `scripts/cargo.sh new`, a dependency
      pinned (`itoa = "=1.0.15"`), `scripts/cargo.sh fetch` → "Downloaded
      itoa v1.0.15", the cache at `<checkout>/.cargo-home/registry/` with
      `index.crates.io-…`; `scripts/cargo.sh build --offline` exit 0; the
      index's `config.json`: `"dl": "https://static.crates.io/crates"`;
      `cargo +1.98.1 --version` works with the moved cache.
- [ ] Inside the sandbox: Not yet proven — B0's first `scripts/cargo.sh
      fetch` in a session opened in its worktree; B0's record carries it.
- [x] Full gate: all 7 steps passed (`gate.out`); step 3's wiring tests include the two new refusal cases.
- [ ] Independent verification: pending.

## 5. Close Out
- [x] Full gate green: all 7 steps (`evidence/2026-10-12-sandbox-crates-io/gate.out`).
- [ ] Scrap Sweep: the scratch projects live in the session's scratchpad,
      outside the repository.
- [ ] Reviewed per `REVIEW.md`: the risk note above.
- [x] Knowledge layer: AGENTS.md; no help page or runbook exists.
- [x] Commit message explains why; record committed with the change.

## Skipped items — visible, never silent
- The in-sandbox proof waits for B0's session (above).

## Evidence log
```
2026-10-12  scratch: scripts/cargo.sh fetch → "Downloaded itoa v1.0.15"; build --offline exit 0;
            shellcheck --severity=style scripts/cargo.sh: clean
            full gate: all 7 steps passed (gate.out)
```
