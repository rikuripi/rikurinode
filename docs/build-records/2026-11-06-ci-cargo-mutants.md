# Build Record — CI mutates the control plane's changed Rust lines (cargo-mutants)

| | |
|---|---|
| **Date** | 2026-11-06 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `ci/cargo-mutants`, from `main` at `f190669`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `46c61e1` (red), `ba5e786` (fix), `f2802fb` (red), `dfcf0bf` (fix), `b33d63e` (red), `939d8a8` (fix); merged as `22f9b98` (#71) |
| **Status** | DONE |
| **Change type** | ops (a new CI check) |

## Why

5c.1 (`docs/build-records/2026-11-06-5c1-control-plane-on-node.md`) closed with `cargo mutants` Not yet proven. Rust tests may not run on the Mac, rikuri-drill has no toolchain, and CI ran the tests but not mutants. BUILD-PROCEDURE ("The mutation run") asks for `cargo mutants` on high-risk Rust. The owner chose (2026-11-06: "Record it, follow-up task (Recommended)", then "Next"): this task.

## Task Contract

1. **Outcome:** every pull request that touches the control plane has its changed Rust lines mutated in CI, and a mutant the tests miss fails the run, so the "mutation run" no longer depends on a machine that can run Rust tests.
2. **Scope:** a CI check, done as its own task (AGENTS.md §2, "Controls").
   - New `.github/workflows/mutants.yml`, job **Rust mutants (changed lines)**:
     - it runs on pull requests to `main` that touch `control-plane/**`, `rust-toolchain.toml` or the workflow itself, and by hand (`workflow_dispatch`) with a `base` commit;
     - the token is `contents: read` only, and the checkout keeps no credential;
     - cargo-mutants **27.1.0** comes from its GitHub release, `cargo-mutants-x86_64-unknown-linux-gnu.tar.gz`, checked against SHA-256 `dfe6dc37d0342c891d2829b5a695aa57c2d0edecef7e7d0399a30cc6e206411e`, as `cargo-deny` is in `ci.yml`;
     - the toolchain is `rust-toolchain.toml`'s, named in `RUSTUP_TOOLCHAIN`, because cargo-mutants builds a copy of `control-plane/` that has no toolchain file;
     - crates are fetched as locked through `scripts/cargo.sh`; then `cargo mutants --in-diff`, over `git diff --relative=control-plane <base>...HEAD`, runs inside `scripts/quality/safe-run.sh`, offline and `--locked`;
     - exit 0 passes, as does 3 (timeouts: the tests did not pass under the mutant); any other exit, above all 2 (missed mutants), fails;
     - missed and timed-out mutants are written to the job summary, and `mutants.out` is kept as an artifact.
   - Tests: `scripts/quality/tests/test_workflows.py`, a new class.
   - Knowledge layer: one sentence in `.agents/workflows/BUILD-PROCEDURE.md`, "The mutation run": where no machine can run the Rust tests, this workflow's run is that run.
   - Risk tier: **high-risk** (corrected after verifier round 1; it was "routine"). BUILD-PROCEDURE's "Risk tiers" lists CI and the procedure itself as controls, and this change touches both. The third-party binary runs on a CI runner with a read-only token, no secret, and cargo offline inside `safe-run.sh`. On a runner without user namespaces, `safe-run.sh` has only its stand-ins, so the network itself is not cut there (verifier round 1, Minor 1).
   - **Not included:**
     - making it a required check (branch protection is the owner's);
     - an exclusion file: none is needed yet. The owner's rule for one: each exclusion only in `control-plane/.cargo/mutants.toml`, each with its reason; a test comes with the first;
     - fixing any survivor that the 5c.1 run below finds (its own task);
     - the 5c.1 record's close-out PR (#70).
3. **Done when:**
   - the new tests in `test_workflows.py` are committed red first and seen failing in rikuri-drill, then pass;
   - `Full gate (Ubuntu)` passes on the PR;
   - the PR's own **Rust mutants** run installs the checksummed binary and passes. This PR changes no Rust, so cargo-mutants finds nothing to mutate and exits 0: the run proves the install and the plumbing, not the mutation;
   - after the owner merges, one run by hand with `base` `f5584b6` (5c.1's base) mutates 5c.1's lines, and its result is recorded here and in 5c.1's record;
   - one `verifier` pass has no Important finding.
4. **Authority:** the owner's words above; the answers (2026-11-06): "Fail the job (Recommended)", "Yes, after merge (Recommended)". This branch; a draft PR; no merge. Reading cargo-mutants' release metadata and source through `gh api`; no binary downloaded to this machine. After the merge, one `gh workflow run`.
5. **Limits:** one task; two repair cycles; two review rounds; CI at most 3 runs on the PR, plus the one run by hand.

## Third-party code: cargo-mutants 27.1.0

- **Source and provenance:** `github.com/sourcefrog/cargo-mutants`, MIT, not archived, last pushed 2026-10-19. v27.1.0 was released on 2026-06-02, five months ago. The Linux archive was uploaded by `github-actions[bot]` from the project's `release.yml` (`taiki-e/upload-rust-binary-action`, which packs the binary at the archive's root). GitHub records its digest as `sha256:dfe6dc37…411e`, the pin above.
- **Behaviour read from its source at `v27.1.0`:**
  - exit codes 0 success, 2 missed mutants, 3 timeouts, 4 baseline failed, 5 a diff that does not match the tree, 6 an invalid diff (`src/exit_code.rs`);
  - an empty diff, or one with no Rust source or no mutants, exits 0 (`src/in_diff.rs`).
- **Side effects:** it copies the tree to a temporary folder, writes `mutants.out`, and runs `cargo build` and `cargo test`. On the runner that happens inside `safe-run.sh`, with no network and no secret.

## Evidence log
- **Red** (rikuri-drill, `safe-run.sh`): `test_workflows.py` `Ran 38 tests` `FAILED (errors=8)`, each `No such file or directory: '.../.github/workflows/mutants.yml'`. That only shows the workflow is missing; the hand mutants after green show that each test bites. Test changes: a new class `Mutants` and two path constants; nothing existing changed.
- **Fix** (its own commit):
  - `.github/workflows/mutants.yml`, as in the contract;
  - one bullet in `.agents/workflows/BUILD-PROCEDURE.md`, "The mutation run". The job fails on any missed mutant, which is stricter than the procedure's own rule, where only a survivor in a refusal, validation, recovery, funds or integrity check is Important. The owner chose it.
- **Green** (rikuri-drill, `safe-run.sh`): `scripts/quality/tests` `Ran 168 tests`, with only the 7 known `git` errors (Not yet proven locally; CI's gate); `.claude/hooks` `Ran 91 tests` `OK`; `image/tests` `Ran 435 tests` `OK`. The workflow parses as YAML (Ruby's `YAML.load_file` on the Mac, a syntax check only): two triggers, eight steps, `contents: read`. `git diff --check`: clean.
- **Two layout fixes before green, in the workflow, not the tests:** the toolchain line had a trailing comment, and the fetch was a one-line `run:`. The tests read each command as its own line.
- **Hand mutants of the workflow: 16 of 16 red.** Each was restored byte for byte (sha256 the same before and after):
  - the digest changed;
  - a write token;
  - the credential kept;
  - a `push` trigger;
  - the base not checked;
  - the base put into the shell;
  - the diff not relative to `control-plane/`;
  - out of `safe-run.sh`;
  - online;
  - exit 2 passing;
  - `continue-on-error`;
  - an exclusion on the command line;
  - the toolchain `stable`;
  - the missed list hidden;
  - no `control-plane/**` path;
  - not `--locked`.
- **Not yet proven:**
  - the workflow on a runner: the PR's own run, with no Rust in the diff, must install the binary, pass the checksum and exit 0;
  - the run by hand over 5c.1, after the merge.
- **CI run 1 of 3** (on `ba5e786`): Rust mutants job 128288915034 **failed** at the install step. The download and `sha256sum -c` passed, then `cargo-mutants --version` gave `error: unexpected argument '--version' found`, exit 1. Cause: the binary parses its arguments as `cargo mutants ...` (`src/main.rs` at v27.1.0, `#[command(name = "cargo")] enum Cargo { Mutants(Args) }`), so run directly it needs `mutants` first. The mutation step was never reached. Through `cargo`, as the mutation step calls it, the arguments are right.
- **Repair cycle 1:**
  - **Red** (`test_workflows.py`, a new test `test_the_installed_binary_is_asked_as_cargo_would_ask_it`, additions only): `Ran 39 tests` `FAILED (failures=1)`.
  - **Fix** (its own commit): `cargo-mutants mutants --version`.
  - **Green:** `scripts/quality/tests` `Ran 169 tests`, with only the 7 known errors.
  - Why the tests missed it: they read the workflow's text, and nothing ran the binary. Only a runner can show that.

## Verifier, round 1, and the rest of repair cycle 1

- **Verifier, one pass** (on `ba5e786`, at high-risk depth): **FAIL**.
  - **Important 1:** `cargo-mutants --version` exits 1 on the runner (run 42334715705), so the job can never pass. It was already repaired above (`f2802fb` red, `dfcf0bf` fix).
  - **Important 2:** the tier was routine, and four weakenings passed the line checks: a `2) ;;` before `0|3) ;;`, `if: false` on the mutation step, `exit 0` after `rc=0`, and a negated `paths:` entry.
  - **Minor 1:** "no network" is not true on a runner that refuses user namespaces. Only cargo is offline there.
  - **Minor 2:** the run lacked the verifier's `--test-workspace=true --timeout 600`.
  - **Nit 1:** `printf … | grep -Eqx` passes a base of many lines if any one line is a commit id.
  - **Nit 2:** `--relative=control-plane` has no trailing slash. Left as it is: it is harmless, and git reads the argument as a path prefix.
  - **What it found sound:** the supply-chain pin (digest and uploader); the token; the injection path; and, from the v27.1.0 source, `--dir` with `--relative`, `--output`, the exit codes, `RUSTUP_TOOLCHAIN` and `CARGO_HOME`.
  - It reran the red (`Ran 38` `FAILED (errors=8)`) and the green (`Ran 38` `OK`).
- **Repair** (the same cycle; nothing was pushed between the two):
  - **Red** (`test_workflows.py`):
    - new `test_the_mutation_step_is_exactly_this` (the step's whole lines), `test_only_the_two_reports_have_a_condition` and `test_the_trigger_paths_are_exactly_these`;
    - two pinned lines changed, each stricter:
      - the base check becomes `[[ "$BASE" =~ ^[0-9a-f]{7,40}$ ]]`, and `grep -Eqx` is refused (Nit 1);
      - the run line gains `--test-workspace=true --timeout 600` (Minor 2).
    - Result: `Ran 42 tests` `FAILED (failures=3)`. The two condition and path tests already pass on the old workflow; the mutants below show that they bite.
  - **Fix** (its own commit):
    - the bash match;
    - the verifier's two settings;
    - the header comment now says only cargo is offline, and why the stand-ins cannot cut the network;
    - the risk tier above.
  - **Green:**
    - `scripts/quality/tests` `Ran 172 tests`, with only the 7 known errors;
    - YAML parses;
    - `git diff --check` clean;
    - a two-line base is refused by the new match (`two-line base refused`).
  - **Hand mutants: 24 of 24 red.** That is the first 16 again, plus:
    - the verifier's four survivors;
    - `if: false` on the job;
    - the old `grep -Eqx` base check;
    - no `--test-workspace`;
    - the bare `cargo-mutants --version`.
    - The sha256 of the workflow was the same before and after.

## Verifier, round 2 (the corrections only), and CI run 2

- **Verifier, follow-up pass** (`git diff ba5e786..939d8a8`): **PASS**. Both Important findings are closed:
  - its M1 to M4 are now killed;
  - red and green held at each pair: `f2802fb` `Ran 39` `FAILED (failures=1)`, then `dfcf0bf` `OK`; `b33d63e` `Ran 42` `FAILED (failures=3)`, then `939d8a8` `OK`;
  - the base match refuses a multi-line base, `F190669` and `f190669\;id`.
- **Minor, for the backlog:** three added weakenings outside the pinned step still pass the tests: N2, a step that replaces `scripts/cargo.sh` with `exit 0`; N3, a step that writes `exclude_globs = ["**"]`; N5, a line that empties the diff. A text test can only narrow this. The narrowing proposed is to pin the list of step names, and the diff step exactly.
- **Nits:**
  - **The repair count.** This record counts the CI repair and the verifier repair as one cycle (nothing was pushed between them); counted strictly, they are two, which is the limit. Either way, no further repair is allowed in this task.
  - **The runner bullet.** "Not yet proven: the workflow on a runner" is now proven (below).
- **CI run 2 of 3** (on `939d8a8`), all passed:
  - [CI, Full gate (Ubuntu)](https://github.com/rikuripi/rikurinode/actions/runs/42335247616);
  - [Rust mutants](https://github.com/rikuripi/rikurinode/actions/runs/42335247777). Its log, read by the verifier: `cargo-mutants.tgz: OK`, `cargo-mutants 27.1.0`, `rustc 1.98.1`, `safe-run: namespace isolation unavailable — stand-ins only`, `Diff file is empty`, then success. That proves the install, the checksum, the toolchain and the empty-diff path, not a mutation;
  - [OS image](https://github.com/rikuripi/rikurinode/actions/runs/42335247783);
  - [the guard and quality tools](https://github.com/rikuripi/rikurinode/actions/runs/42335247704).
- **Not yet proven at that point:** a run that mutates. That was the run by hand with `base` `f5584b6`, after the owner merged (below).

## Close-out

- **Merged** by the owner as `22f9b98` (#71, 2026-11-07T03:50:52Z), after CI run 2 of 3 and verifier round 2's PASS. The round 2 record (`c0ef067`, held back so as not to spend the last CI run) and this close-out land in their own PR.
- **The run by hand** (the owner's "Yes, after merge (Recommended)"): `gh workflow run mutants.yml --ref main -f base=f5584b6`, 1 of 1. `f5584b6` is an ancestor of `main`; the diff from it under `control-plane/` is 5 files, 618 lines added. [Run 42905996478](https://github.com/rikuripi/rikurinode/actions/runs/42905996478), on `22f9b98`, **failed, as designed**:
  - `Found 23 mutants to test`; `Unmutated baseline in 26s build + 5s test`;
  - `23 mutants tested in 2m: 4 missed, 9 caught, 10 unviable`;
  - `cargo-mutants exited 2: missed mutants (2) or an error`, then `Process completed with exit code 2`;
  - the summary and `mutants-out` steps ran after the failure (`if: always()`).
- **What that proves:** on real Rust lines the job installs the pinned binary, builds the baseline offline and `--locked` inside `safe-run.sh`, mutates only the diff, and fails on a missed mutant. Every item in "Done when" has now been seen.
- **The four missed mutants** (5c.1's; each is a recorded result here, not repaired here, by the owner's rule):
  - `crates/rikuri-control/src/console.rs:80:5`: `lan_address` → `None` (the UDP route probe for the node's address);
  - `apps/rikuri-control-plane/src/main.rs:31:5`: `main` → `Default::default()` (the subcommand dispatch);
  - `apps/rikuri-control-plane/src/main.rs:83:5`: `run` → `Ok(())` (the daemon's start: config, runtime, signals, boot);
  - `apps/rikuri-control-plane/src/main.rs:181:5`: `claim_screen` → `Default::default()` (the tty2 claim-screen loop).
  All four are where the code meets the operating system: `cargo test` never runs the binary or opens the probe socket. Whether each gets a test (for example one that runs the built binary) or a reasoned exclusion in `control-plane/.cargo/mutants.toml` is the follow-up task's choice, with the owner.
- **Used:** CI 2 of 3 runs on the PR, plus the 1 run by hand; repair cycles, one by this record's count (two counted strictly); two review rounds.
- **Not in this task:** making **Rust mutants** a required check (branch protection is the owner's).
- **Backlog, from this task:** the verifier's Minor N2, N3 and N5 (pin the list of step names, and the diff step exactly).
