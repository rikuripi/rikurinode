# Build Record — the four mutants 5c.1's tests missed: tests through the binary, one reasoned exclusion

| | |
|---|---|
| **Date** | 2026-11-10 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `rust/mutants-survivors`, from `main` at `22f9b98`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | fix (test gaps) |

## Why

The run by hand of **Rust mutants** over 5c.1's lines ([run 42905996478](https://github.com/rikuripi/rikurinode/actions/runs/42905996478), `base` `f5584b6`; `docs/build-records/2026-11-06-ci-cargo-mutants.md`, Close-out) found `23 mutants tested in 2m: 4 missed, 9 caught, 10 unviable`:

- `crates/rikuri-control/src/console.rs:80:5`: `lan_address` → `None`;
- `apps/rikuri-control-plane/src/main.rs:31:5`: `main` → `Default::default()`;
- `apps/rikuri-control-plane/src/main.rs:83:5`: `run` → `Ok(())`;
- `apps/rikuri-control-plane/src/main.rs:181:5`: `claim_screen` → `Default::default()`.

The owner's rule (2026-11-06): survivors are their own task. The owner's answers (2026-11-10): "Exclude + drill check (Recommended)" for `lan_address`; then, after the plan for the other three proved impossible (below), "Exclude all four + drill (Recommended)".

**Why the first plan was dropped.** The plan first approved ("Yes, as described (Recommended)") was integration tests that run the built binary. The workspace forbids spawning a process, tests included: `clippy.toml` bans `std::process::Command` and `Command::new`, at `forbid` in `Cargo.toml`, so no `#[allow]` lifts it (ADR 0005, ADR 0014; `docs/build-records/2026-10-20-no-process-spawn.md`: "a process cannot be spawned from shipped code or tests without the gate failing"). A refactor would not help: the thin wrappers that read the environment or stdin (`main`, `run`, `claim_screen`) would survive in its place, and `std::env::set_var` is `unsafe` in edition 2024, where `unsafe_code` is forbidden. Lifting the ban was offered as its own control task, and not recommended.

## Task Contract

1. **Outcome:** each of the four mutants no `cargo test` can kill is excluded from mutation by name, with its reason, and is killed instead by a VM drill check at the real entry point, so **Rust mutants** passes over 5c.1's lines without hiding anything a test could catch.
2. **Scope:**
   - New `control-plane/.cargo/mutants.toml`: four `exclude_re` entries, each anchored (`^…$`) to exactly one survivor's name as cargo-mutants filters on it (`Mutant::name(false)`: the tree-relative path, no line or column; cargo-mutants 27.1.0's `src/mutant.rs` and `src/options.rs`), each with its reason and the drill check that kills it:
     - `main` → `Default::default()` and `run` → `Ok(())`: the daemon exits 0 at once; the drill's "the control plane runs as its own user" (active, running) and the HTTPS checks fail;
     - `claim_screen` → `Default::default()` and `lan_address` → `None`: tty2 shows no address; the new check fails.
     Every other mutant of these functions (a match arm, a guard) is still tested.
   - `image/drill/vm_drill.py`: a new check, **"the claim screen shows the node's address"**. Once the drill reaches the VM over SSH (the network is up), it restarts `rikuri-claim-screen.service`, then reads `/dev/vcs2` (what tty2 shows) up to `SCREEN_READS` times until it holds `Address:  http://<src>`, where `<src>` is the source address of `ip -4 route get 192.0.2.1` in the VM: the same probe `lan_address` makes. It joins `EXPECTED`. The restart is because the unit is not ordered after the network, so the screen drawn at boot may say "none yet", as the runbook allows ("press Enter to look again"); that behaviour is unchanged here.
   - Tests: `image/tests/test_vm_drill.py` (the check's reads, its step, its retries; the lists of every check); `scripts/quality/tests/test_workflows.py`, a new class: the file holds only `exclude_re`, exactly these four, each matching its one survivor and none of its neighbours, each with a `Why:` and naming a check that is in `EXPECTED`. That also narrows the cargo-mutants task's N3 (an exclude-everything config) for this file.
   - Risk tier: **high-risk** (a control: what mutation testing skips; and the drill, the stage's proof).
   - **Not included:** any change to `main.rs`, `console.rs`, the unit or the runbook; the spawn ban; the cargo-mutants backlog N2 and N5; making **Rust mutants** a required check.
3. **Done when:**
   - the Python tests are committed red first and seen failing in rikuri-drill through `safe-run.sh`, then pass;
   - a run by hand of **Rust mutants** on this branch with `base` `f5584b6` lists none of the four, has no missed mutant, and passes;
   - the OS image workflow's VM drill passes the new check on the PR, and CI's `Full gate (Ubuntu)` passes;
   - one `verifier` pass has no Important finding.
4. **Authority:** the owner's answers above; this branch; a draft PR; no merge. `gh workflow run mutants.yml --ref rust/mutants-survivors -f base=f5584b6`. rikuri-drill over its pinned SSH key (host key `SHA256:NtVMqX12NYeujT0KNVRasNSCtiVoLgh3+SqVUFD5938`, the one the owner checked) for the Python tests.
5. **Limits:** one task; two repair cycles; two review rounds; CI at most 3 runs on the PR plus 2 runs by hand.

## Evidence log
