# Build Record — CI mutates the control plane's changed Rust lines (cargo-mutants)

| | |
|---|---|
| **Date** | 2026-11-06 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `ci/cargo-mutants`, from `main` at `f190669`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
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
   - Risk tier: **routine.** It adds a check and weakens none. The third-party binary runs on a CI runner with a read-only token, no secret and no network (inside `safe-run.sh`).
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
