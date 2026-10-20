# Build Record — the sandbox set to reach crates.io, cargo's cache in the checkout (D24), and to deny reads of 14 private paths (D25)

| | |
|---|---|
| **Date** | 2026-10-12 |
| **Author / session** | Claude Code (Opus 5.5), in a session opened in Rikuri-PI (outside the sandbox: the sandbox protects its own settings file, so this change cannot be made from inside it); owner Henry |
| **Branch** | sandbox/crates-io |
| **Commits** | 35c4f30 (D24); 70186d9 (after verifier round 1: the test fix, D25's first five paths, wording); 7aafa9b (after round 2: D25's nine more paths, wording); the commit after round 3 (wording) |
| **Status** | COMPLETE — verifier round 1 FAIL (a vacuous test; wording) fixed with D25 added; round 2 FAIL on wording only, D25 extended to fourteen paths by the owner; round 3 FAIL on wording only, corrected with no further round (the owner's stop rule). Merged as PR #7 (eff4ea9, 2026-10-12 22:50 PDT). The fetch and a denied path inside the sandbox: seen by B0.1's session, 2026-10-12 (§4) |
| **Change type** | ops (the session boundary) |

## 0. Intent — the owner's words, approved before design
- [x] Problem: the next change, B0 (the Rust control plane), cannot build in
      a session opened here: the sandbox reaches only GitHub, and cargo writes
      its download cache under `~/.cargo`, outside the repository.
- [x] Outcome: Rust sessions can fetch crates from crates.io inside the
      sandbox, writing nothing outside the checkout (to be seen in B0's
      first sandboxed fetch); and, added after verifier rounds 1 and 2 (D25),
      the sandbox is set to deny reads of fourteen private paths of the
      owner's (to be seen in B0's session); the rest of the home folder
      stays readable.
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
      cache inside the checkout and ignored by git. Corrected after verifier
      round 1: a plain `cargo` fails visibly only when it must download (the
      sandbox refuses the write to `~/.cargo`); with crates already in that
      shared cache it builds, its cache-bookkeeping writes refused without a
      message (the verifier's emulation: `~/.cargo` read-only, exit 0).
      `scripts/cargo.sh` is the documented way; nothing enforces it.
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
      **The read side** (verifier round 1): reads are open in the sandbox
      except its deny list, so a build script — like any sandboxed command —
      could read the owner's credential files and send them to GitHub. The
      owner chose to close it (D25, 2026-10-12, AskUserQuestion: "Yes, deny
      credential files (Recommended)"): `~/.ssh`, `~/.config/gh`,
      `~/.git-credentials`, `~/.docker` and `~/.claude/.credentials.json` are
      added to `denyRead`. Nine more private folders exist and were
      readable: verifier round 2 found six (`~/.gnupg`, `~/.bitcoin`,
      `~/.local/share/keyrings`, `~/.config/google-chrome`,
      `~/.config/chromium`, `~/.config/Code`), and the builder's wider check
      of usual places, by type only, three more (`~/.config/BraveSoftware`,
      `~/.config/Claude`, `~/.local/share/Trash`); the owner extended D25 to
      all nine (2026-10-12, AskUserQuestion: "Deny all 9 too
      (Recommended)"). Fourteen in all. `git push`, `fetch` and `pull` run
      outside the sandbox, so they keep their credentials; `gh` inside the
      sandbox already reported its token invalid (bootstrap round 18). Gaps:
      any other file in the home folder stays readable; `~/.netrc` and
      `~/.cargo/credentials.toml` are absent here and not listed (a deny on a
      missing path was not tried: the sandbox replaces some missing protected
      paths with placeholders, and a failure there would stop every
      command); a private path made later needs adding.
- [x] Verification: the gate (the check accepts the new block and refuses
      wider ones); the wrapper fetches into the checkout (proven outside the
      sandbox here); inside the sandbox — B0's first fetch, recorded there.

### Risk note (REVIEW.md: protected paths)
`.claude/settings.json`, `scripts/quality/check_guard_wiring.py`,
`scripts/quality/tests/test_guard_wiring.py`, `scripts/quality/full-gate.sh`,
`.gitignore` and `AGENTS.md` are protected. The settings and the check widen
the sandbox's network by exactly two hosts, chosen by the owner; nothing
else in the sandbox block changes, and the check still fails on any other
difference; D25 adds fourteen read denies (five in 70186d9, nine in
7aafa9b), a narrowing: each is a private path of the owner's, kept from
sandboxed reads. The test file changes
its fixture to the new block (necessary: the fixture is the expected block)
and adds two refusal cases. Round 1's verifier found that the fixture change
made an older case vacuous: the bare-`*` widening was a hard-coded list that,
once the fixture grew, failed for what it lacked rather than for the `*`. The
fix rebuilds it, and the two other cases that were not pure additions
(`example.com`; `docker *` in `excludedCommands`), as additions to the
current lists. The gate's lint list gains one file. `.gitignore` gains one
line. AGENTS.md says the new rule where the sandbox is described.

## 2. Build
- [x] Code meets the bar: `scripts/cargo.sh` is `set -euo pipefail`, finds
      the checkout with git, passes its arguments through; shellcheck clean.
- [x] Clean as you go: nothing replaced.
- [x] Security question: yes, it widens the session boundary — covered by
      the owner's decision, the closed-world check and its two new refusal
      cases, and the risk note.

## 3. Debug
- [x] A test defect, fixed in the fix round after verifier round 1: the
      bare-`*` widening case had gone vacuous. Reproduced with the
      verifier's mutant (passes the old tests); class: a refusal case
      written as a whole list instead of an addition to the current one;
      siblings swept (`example.com`, `docker *`; round 2 scanned all 132
      cases and found no other).

## 4. Verify
- [x] Outside the sandbox (this session, 2026-10-12, a scratch git repository
      in the session's scratchpad): `scripts/cargo.sh new`, a dependency
      pinned (`itoa = "=1.0.15"`), `scripts/cargo.sh fetch` → "Downloaded
      itoa v1.0.15", the cache at `<checkout>/.cargo-home/registry/` with
      `index.crates.io-…`; `scripts/cargo.sh build --offline` exit 0; the
      index's `config.json`: `"dl": "https://static.crates.io/crates"`;
      `cargo +1.98.1 --version` works with the moved cache.
- [x] Inside the sandbox — seen by B0.1's session (2026-10-12, a session
      opened in a worktree of this repository, `auto` mode; its first two
      commands; evidence
      `evidence/2026-10-12-b0-1-control-plane-workspace/d24-fetch.out` and
      `d25-stat.out`): `scripts/cargo.sh fetch` on a crate pinning
      `itoa = "=1.0.15"` → "Downloaded itoa v1.0.15", exit 0, into the
      checkout's `.cargo-home/registry/cache/index.crates.io-1949cf8c6b5b557f/itoa-1.0.15.crate`,
      nothing in `git status`; `stat -c %F ~/.git-credentials` → "character
      special file" (the sandbox's stand-in; a regular file outside, above).
      D24 and D25 act as set.
- [x] Full gate: all 7 steps passed on each tree — 35c4f30 (`gate.out`), the fix round (`gate2.out`), after round 2 (`gate3.out`); step 3's wiring tests include the refusal cases.
- [x] **Verifier, round 1: FAIL** (its evidence in
      `/home/junc/claude-wip/d24/verify/`). Passed: the block identical in
      settings, check and fixture, two hosts added and nothing else; the
      check refuses `crates.io`, `*.crates.io`, a third host, the old block;
      both hosts necessary and sufficient (the index's `"dl"`; no redirect
      from `static.crates.io`; a cargo fetch through a proxy allowing only
      the sandbox's hosts reached only those two); `scripts/cargo.sh` as
      stated, and rustup reading 1.98.1 read-only with no write outside the
      scratch repository (strace); the gate. Failed: **test** — the bare-`*`
      widening case went vacuous (a check tolerating `*` passed at HEAD,
      failed at 5630ea0); **wording** — "plain cargo is refused visibly";
      the PR headline and AGENTS.md stating the sandboxed fetch as fact.
      Noted: the read side of the risk (above, now D25); a force-added cargo
      cache passes the hygiene check (`.gitignore` is the only barrier);
      the record's status and commits lines.
- [x] **Fix round** (the owner's stop rule: a test finding gets a fix and
      a second check). The verifier's mutant (the check tolerating `*` in
      `allowedDomains`), applied to this tree's check: the round-1 tests
      pass it ("Ran 33 tests … OK"); the fixed tests fail it on exactly the
      `*` case (`fix-red.out`); the real check passes the fixed tests.
      Wording corrected in this record, AGENTS.md, the PR. D25 added.
- [x] **Verifier, round 2: FAIL on wording only** (evidence in
      `/home/junc/claude-wip/d24/verify2/`). Passed: the rebuilt cases are
      pure additions, each caught by a mutant tolerating exactly that
      addition (`*`, `example.com`, `docker *`), vacuous at 35c4f30; all 132
      cases scanned, no other mixed case; D25's five denies identical in
      settings, check and fixture, each path existing, each removal caught;
      the plain-cargo correction re-proven (an offline emulation: plain
      cargo exit 101 on a needed download, the wrapper exit 0); the gate;
      CI. Failed: the deny list described as "the owner's credential
      files" while nine more private folders exist and stay readable; the
      PR headline stating unproven sandbox behaviour; AGENTS.md calling the
      D25 denies "proven only outside the sandbox" (a deny acts only
      inside it). Nits: this §3 said N/A; §4/§5 cited the older gate
      receipt; a test name out of date; 35c4f30's commit message keeps the
      old plain-cargo claim (rewording it needs a force-push: left as is,
      corrected here and in AGENTS.md).
- [x] **After round 2:** the owner extended D25 to the nine (a code change:
      the stop rule gives it a check round); wording corrected in this
      record, AGENTS.md and the PR; the test renamed
      `test_every_read_deny_must_stay` (it covers every deny now, not only
      the previous checkout's — a name change, no assertion changed).
- [x] **Verifier, round 3: FAIL on wording only** (evidence in
      `/home/junc/claude-wip/d24/verify3/`). Passed: the nine denies
      identical in all three places, each path existing (`stat` type), each
      removal caught by a mutant tolerating exactly that path; the rename
      changed no assertion (same body by AST); the gate on 7aafa9b; CI on
      7aafa9b. Failed: this record's risk note still said "five read
      denies"; its title and the check's header comment still said
      "credential files hidden". Nits: the attribution of the nine (six
      were round 2's); the PR body's "denies reads" and "now fixed"; §5's
      scrap list. All corrected here, in the check's comment and in the PR,
      with no further round (the owner's stop rule: wording only). Left:
      7aafa9b's commit message ("the record says what is set"), which
      only a force-push could change.

## 5. Close Out
- [x] Full gate green: all 7 steps on the current tree (`evidence/2026-10-12-sandbox-crates-io/gate3.out`).
- [x] Scrap Sweep: nothing stray in the repository. Outside it: the
      session's scratchpad (the cargo probes) and `/home/junc/claude-wip/d24/`
      — the verifiers' `verify/`, `verify2/`, `verify3/`, the builder's
      `fix/`, the gate outputs (copied into the evidence folder), `pr-body.md`
      and `commit-msg-3.txt` (as published) — kept as evidence until merge.
- [x] Reviewed per `REVIEW.md`: three verifier rounds; the risk note above
      covers every protected path touched.
- [x] Knowledge layer: AGENTS.md; no help page or runbook exists.
- [x] Commit message explains why; record committed with the change.

## Skipped items — visible, never silent
- The in-sandbox proof: done by B0.1's session, 2026-10-12 (§4).
- A cargo cache force-added past `.gitignore` passes the hygiene check
  (verifier round 1). Owner: Henry. Reactivate: with B0's gate, if the
  cache is ever seen staged.

## Evidence log
```
2026-10-12  scratch: scripts/cargo.sh fetch → "Downloaded itoa v1.0.15"; build --offline exit 0;
            shellcheck --severity=style scripts/cargo.sh: clean
            full gate: all 7 steps passed (gate.out)
            verifier round 1: FAIL (vacuous `*` case; wording); fix: the mutant passes the old
            tests, fails the fixed ones on the `*` case (fix-red.out); D25 added
            full gate after the fix round: all 7 steps passed (gate2.out)
            verifier round 2: FAIL on wording only; owner extended D25 to 14 paths;
            full gate: all 7 steps passed (gate3.out)
            verifier round 3: FAIL on wording only; corrected, no further round
```
