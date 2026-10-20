# Build Record — The control plane cannot spawn a process: a clippy ban and a cargo-deny feature ban

| | |
|---|---|
| **Date** | 2026-10-20 |
| **Author / session** | Claude (Opus 5.5, cloud session linked to the owner's Mac) for Henry Chen |
| **Branch** | `control/no-process-spawn`, from `main` at `adaf8c4`, in a clone at `/home/claude/rikurinode` in the cloud session (the owner's Mac cannot reach GitHub from that session) |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | ops (a control: lint and dependency policy) |

## Task Contract

1. **Outcome:** code in the control plane that spawns a process (`std::process::Command`, or tokio's process API) fails the gate, so ADR 0005's "never a shell" and ADR 0014's runbook executor are held by a check and not by review alone.
2. **Scope:** `control-plane/clippy.toml` (a `disallowed-types` and a `disallowed-methods` entry), `control-plane/deny.toml` (one `[[bans.features]]` entry denying tokio's `process` feature), and this record. Tier: **high-risk** (a control that enforces a security boundary; BUILD-PROCEDURE.md, "Risk tiers"). **Not included:** the full gate script, CI, the guard, any Rust source, the threat model's text (T26 already names this ban as owed).
3. **Done when:** clippy on every target passes on the unchanged tree with the ban in place; a scratch copy that adds `std::process::Command::new` fails clippy naming the ban (the red run, recorded below); `cargo deny check bans` passes on the tree and fails on a scratch copy that enables tokio's `process` feature; `cargo fmt --check`, `cargo test` inside `safe-run.sh` and `cargo deny check` pass; `git diff --check` and `repo_hygiene.py` pass; CI's `Full gate (Ubuntu)` is green on the pull request; the verifier's pass has no Important finding.
4. **Authority:** the owner, 2026-10-20: "Ok, to clippy ban. then commit, create branch, verify and make pull request." Edit the files in Scope on this branch; commit, push this branch and open one pull request. One verifier pass. Network: crates.io (locked fetch) and GitHub. No merge.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured; consumption reported at close-out.

## 0. Intent

- [x] **Problem, in the owner's words:** "Ok, to clippy ban." (2026-10-20), answering the proposal in ADR 0014 that `std::process::Command` and its async equivalents be banned by clippy's `disallowed-methods`, and that adding the ban be its own control change.
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** every future change to the control-plane crates; nothing running.
- [x] **Open questions:** none.
- [x] **Owner approved the intent:** the message above.

## 0b. Spec

- [x] **Requirements:** a process cannot be spawned from shipped code or tests without the gate failing; the ban says why and where to read; it does not weaken any existing lint.
- [x] **Design:** clippy's `disallowed-types` on `std::process::Command` (catches imports, annotations and `Command::new` paths) plus `disallowed-methods` on `std::process::Command::new` (belt and braces, and the clearest message). Tokio's process API exists only behind its `process` feature, which the workspace does not enable; a clippy entry for a path that does not resolve would be a configuration warning, so the door is closed in `deny.toml` instead, with `[[bans.features]]` denying `process` on tokio. Rejected: a `grep` in the gate (a second, weaker copy of what the compiler already resolves); banning `std::process` wholesale (the crate uses `std::process::id` and `ExitCode`, which spawn nothing).
- [x] **Policy applied:** the security baseline ("the assistant plans; it never holds authority"; no shell anywhere, threat model T6); "a control change is its own task" (AGENTS.md §2).
- [x] **Flagged concerns:** the pinned toolchain (1.98.1) cannot be downloaded in this session (the egress proxy refuses `static.rust-lang.org`), so local runs use the installed stable 1.97.0 and are recorded as such; CI's full gate with 1.98.1 is the reference run.

## 1. Plan

- [x] **One sentence:** add the two clippy entries and the tokio feature ban, show each red on a scratch copy and green on the tree.
- [x] **Blast radius:** lint and dependency policy only; no runtime behaviour.
- [x] **Current behaviour characterized:** `git grep -n -E 'process::Command|Command::new|tokio::process'` over `control-plane` finds none (the only `std::process` uses are `ExitCode` and `std::process::id`); tokio's features in `control-plane/Cargo.toml` are `io-util, macros, net, rt-multi-thread, signal, sync, time`.
- [x] **Files and order:** this record, `clippy.toml`, `deny.toml`, the red runs, the green runs.
- [x] **Risks:** a configuration path clippy cannot resolve becomes a warning that fails `-D warnings`; a stable-1.97 run differing from CI's 1.98.1.
- [x] **Verification defined up front:** I will know this works when the scratch copies fail with the ban's message and the tree passes, locally and in CI.

## 2. Build

- [x] New code meets the bar: two clippy entries and one cargo-deny entry, each with its reason and a pointer to this record.
- [x] Clean as you go: nothing replaced; no existing lint or ban changed.
- [x] Security question answered: yes, it touches the exec boundary (threat model T6). Gate: clippy with `-D warnings` and cargo-deny's bans, both in the full gate (steps 8 and 9). Proof: the red runs below.

## 3. Debug

- N/A: no defect fixed.

## 4. Verify

- [x] Unit tests: N/A (configuration); the red and green runs below are its tests. `cargo test` was run for regressions: 104 unit tests and `status_route` pass; `plain_listener` (3 tests) and `sign_in` (9 tests) fail identically on unmodified `main` in this session (each panics on its TCP connect in `tests/common/mod.rs`), so this environment causes it, not this change; CI is the reference run.
- [x] Watched it work: clippy green on the tree; cargo-deny `bans ok` on the tree.
- [x] Regression guard proven to FAIL: a scratch copy adding `std::process::Command::new("true")` fails clippy with both `disallowed_methods` and `disallowed_types`, each printing the ban's reason; a scratch copy enabling tokio's `process` feature fails `cargo deny check bans` with `feature-banned`. Both scratch copies were discarded.
- [ ] Independent verification: see the verifier's report below.
- [x] Diff matches the plan: `clippy.toml`, `deny.toml` and this record, nothing else.

## 5. Close Out

- [ ] Full gate:
- [ ] Scrap Sweep:
- [ ] Reviewed per `REVIEW.md`:
- [ ] Lesson loop: N/A
- [ ] Knowledge layer: N/A (no user-visible behaviour)
- [ ] Commit message explains why:

## Skipped items — visible, never silent

- **Full gate run locally as one script:** not possible here. Step 1 refuses any cargo but 1.98.1, and the session's egress proxy refuses `static.rust-lang.org`, so rustup cannot install it. Steps 2 to 9 were run one by one with stable 1.97.0 and `--ignore-rust-version` (the crates declare `rust-version = 1.98`). CI's `Full gate (Ubuntu)` is the run that counts.
- **Advisories:** `cargo deny check` fails on `main` today with RUSTSEC-2026-0382 (rustls-webpki 0.103.15). That is not caused by this change; the owner chose a separate fix (`docs/build-records/2026-10-20-rustsec-2026-0382.md`), and this branch is rebased on it so its CI can pass.

## Evidence log

All runs 2026-10-20 in the cloud clone, toolchain stable 1.97.0 (clippy 0.1.97), pinned gitleaks 8.30.1, shellcheck 0.11.0 and cargo-deny 0.20.2 installed with CI's checksums.

```
$ scripts/cargo.sh fetch --locked --manifest-path control-plane/Cargo.toml        -> rc 0
$ scripts/cargo.sh fmt --all --check --manifest-path control-plane/Cargo.toml     -> rc 0
$ scripts/cargo.sh clippy --workspace --all-targets --locked --offline \
    --ignore-rust-version --manifest-path control-plane/Cargo.toml -- -D warnings  -> rc 0

# red run, scratch copy with std::process::Command::new("true") added to random.rs
error: use of a disallowed method `std::process::Command::new`
    = note: the control plane never spawns a process (ADR 0005, ADR 0014)
error: use of a disallowed type `std::process::Command`
    = note: the control plane never spawns a process (ADR 0005, ADR 0014)
error: could not compile `rikuri-control` (lib) due to 2 previous errors          -> rc 101

$ cargo deny --manifest-path control-plane/Cargo.toml --locked check
advisories FAILED, bans ok, licenses ok, sources ok                               (RUSTSEC-2026-0382, pre-existing)

# red run, scratch copy with "process" added to tokio's features
error[feature-banned]: feature 'process' for crate 'tokio = 1.53.2' is explicitly denied
bans FAILED                                                                        -> rc 2

$ scripts/quality/safe-run.sh scripts/cargo.sh test --workspace --locked --offline --ignore-rust-version ...
test result: ok. 104 passed; 0 failed   (unit)
plain_listener: 3 FAILED; sign_in: 9 FAILED; both identical on unmodified main  -> environment
status_route: ok. 3 passed
```
