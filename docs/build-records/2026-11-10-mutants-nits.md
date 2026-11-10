# Build Record — the mutants survivors' three verifier nits

| | |
|---|---|
| **Date** | 2026-11-10 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `rust/mutants-nits`, from `main` at `6b6e5cc`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | fix (test gaps, one comment) |

## Why

The verifier's follow-up pass on the mutants survivors (`docs/build-records/2026-11-10-mutants-survivors.md`, "Verifier, round 2") left three nits for the backlog. The owner (2026-11-10): "go".

## Task Contract

1. **Outcome:** the reasons in `control-plane/.cargo/mutants.toml` are all true, and the tests that hold the exclusion list and the drill's probe route catch the weakenings the verifier found surviving.
2. **Scope:**
   - **N1.** `control-plane/.cargo/mutants.toml`, the comment on the `main` exclusion only: a test need not spawn the binary to call `main()`; it would have to set the environment of every control-plane test, the same cost as for `run`. No regex changes.
   - **N2.** `scripts/quality/tests/test_workflows.py`, `MutantsExclusions.NEAR`: for each of the four survivors, its name with no line and column, and with a line but no column, so a regex whose `:\d+:\d+:` is made optional or loosened to `.*` fails.
   - **N3.** `image/tests/test_vm_drill.py`: `PROBE_ROUTE_ADD` run in `sh` with a stand-in `ip` function: the route goes to the interface of the guest's global IPv4 address (`enp0s2`), not to loopback or a field other than the name, so awk's `$1` or a dropped `scope global` fails.
   - Risk tier: **high-risk** (the tests of a control: what mutation testing skips, and the drill).
   - **Not included:** any regex, drill or product change; any other backlog item.
3. **Done when:**
   - the tests pass in rikuri-drill through `safe-run.sh`. They test code that is already right, so their red is the weakenings they catch: each of the verifier's four N2 and N3 survivors applied to a copy, seen failing (recorded here);
   - CI's `Full gate (Ubuntu)` and the tools' py3.9 and py3.12 jobs pass on the PR;
   - one `verifier` pass has no Important finding.
4. **Authority:** the owner's "go"; this branch; a draft PR; no merge; rikuri-drill over its pinned SSH key.
5. **Limits:** one task; two repair cycles; two review rounds; CI at most 2 runs on the PR. No run of **Rust mutants** by hand: no regex changes.

## Evidence log
