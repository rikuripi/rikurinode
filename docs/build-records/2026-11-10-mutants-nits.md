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

- **Red: the weakenings the new tests catch** (rikuri-drill, `safe-run.sh`, each applied to a fresh copy). Eight weakenings: in `mutants.toml`, `claim_screen`'s `:\d+:\d+:` made optional (M1), `lan_address`'s loosened to `:.*:` (M2), `run`'s to `.*` (M3), `main`'s column made optional (M4); in `vm_drill.py`, awk's `$1` (M5), `scope global` dropped (M6), `-4` dropped (M7), the route sent to `lo` (M8). Against `main`'s tests (`6b6e5cc`), **7 of 8 survive**: M1 to M3 leave only the 7 known errors, M5 to M8 give `OK`, and only M4 was already caught. Against this branch's (`76cd7b7`): **8 of 8 fail**.
- **Green** (`76cd7b7`): `image/tests` `Ran 443 tests` `OK`; `.claude/hooks` `Ran 91 tests` `OK`; `scripts/quality/tests` `Ran 176 tests` with only the 7 known errors (the archive copy has no git checkout).
- **N1:** the `main` reason no longer says a test "would have to spawn the binary". It now says that spawning is barred, that `main()` called in a test's own process sees whatever arguments the test runner was given (with none, it starts the daemon), and that telling the mutant apart reliably costs what `run`'s does. A comment only; the four regexes are unchanged, so there was no run of **Rust mutants** by hand.

## Verifier, and CI run 1

- **Verifier, one pass** (on `195733b`, high-risk depth): **PASS, no Important or Minor finding.**
  - It reproduced the red: M1 to M8 against `main`'s tests, 7 of 8 survive; against the branch's, 8 of 8 fail.
  - It found the `main` reason true (`main.rs:31-48`, the spawn ban at `forbid`, `unsafe_code` forbidden), and the four regexes byte-identical to `main`'s.
  - It checked the stand-in `ip` against real iproute2 6.17.0 on Fedora 44: the same fields, `\` continuation and order (loopback first without `scope global`).
  - It ran 20 weakenings of its own: 12 caught. Of the 8 that survived, two widen only to names cargo-mutants never emits; five, such as awk's `exit` dropped or the interface hard-coded, would fail the VM drill's address check or are equivalent; one (`"$dev"` unquoted) behaves the same for real interface names.
  - Tests in rikuri-drill: `image/tests` `Ran 443` `OK`; hooks `Ran 91` `OK`; `scripts/quality/tests` `Ran 176` with only the 7 known errors.
  - **Nits, for the backlog:** N-a, `\d*` in place of `\d+`, or `:\d+:.+:`, survives `MutantsExclusions`; N-b, awk's `exit` dropped or the interface hard-coded survives the route test (a second global address in the stand-in would catch both); N-c, `&&` as `;` and an unquoted `$dev` survive, with no difference in behaviour.
- **CI run 1 of 2** (on `195733b`): `Full gate (Ubuntu)` ([run 42920689624](https://github.com/rikuripi/rikurinode/actions/runs/42920689624): hooks `Ran 91` `OK`, `scripts/quality/tests` `Ran 176`, `image/tests` `Ran 443` `OK`, so the `sh` test passes under Ubuntu's dash and mawk), py3.9, py3.12, the image build and Rust mutants passed; the VM drill and the installer were still running at this writing.
