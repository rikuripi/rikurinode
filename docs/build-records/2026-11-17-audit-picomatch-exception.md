# Build Record — a recorded exception for the picomatch advisory

| | |
|---|---|
| **Date** | 2026-11-17 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/audit-picomatch-exception`, from `main` at `2c425eb`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `3259556` (contract), `b6f5e17` (change) |
| **Status** | IN PROGRESS |
| **Change type** | control change (the gate's npm audit exceptions) |

## Intent: the owner's words

- "1" (2026-11-17), choosing the first of three options put to the owner: "**Record an exception.** Add GHSA-fc5q-39xc-vjpf to `ui/audit-exceptions.json`, with the reasons above and a `review_by` date about 30 days out. The record would also say: remove the exception as soon as a fixed `picomatch` is published." The other options were to wait for a fixed `picomatch`, with every branch red until then, or to pin another version, which no published version allows.

## What happened

- The full gate's npm audit failed on `main` at `2c425eb` ([run 44155661337](https://github.com/rikuripi/rikurinode/actions/runs/44155661337)) and on PR #127 ([run 44156383591](https://github.com/rikuripi/rikurinode/actions/runs/44156383591)), verbatim:
  `npm_audit: FAIL GHSA-fc5q-39xc-vjpf in picomatch: an advisory with no recorded exception`
- `gh api /advisories/GHSA-fc5q-39xc-vjpf` (read 2026-11-17): CVE-2026-112366, severity **high**, "picomatch vulnerable to ReDoS through single-branch repeated extglobs"; `picomatch <= 4.0.7`; no patched version; published 2026-10-19, `github_reviewed_at` `2026-11-17T15:56:42Z`, not withdrawn. GitHub's review is why npm began reporting it; `main`'s run at 14:26 UTC ([44103128926](https://github.com/rikuripi/rikurinode/actions/runs/44103128926)) was green.

## Why an exception is acceptable

- `ui/package-lock.json` has `node_modules/picomatch` at `4.0.7`, marked `dev`. It is required by `vite` (`^4.0.7`), `tinyglobby` (`^4.0.4`) and `fdir` (peer, `^3 || ^4`): the build tools that find the setup pages' own source files.
- It is build-time only. It is not in the built pages, which the control plane embeds, and nothing on the node runs it.
- The patterns it matches come from the repository's own build configuration and the build tools, never from users or the network. A crafted pattern would first need a change to that configuration, which goes through review and the gate.
- No published version is unaffected, so neither an upgrade nor an override can remove it today.

## Task Contract

1. **Outcome:** the gate passes again with this one advisory allowed, named in every run until its review date, and still fails on any other advisory.
2. **Scope:** high-risk (an input of the full gate: BUILD-PROCEDURE, "Risk tiers").
   - `ui/audit-exceptions.json`: one entry, `GHSA-fc5q-39xc-vjpf`, with `package` `picomatch`, `why` giving the reasons above, `review_by` `2026-12-17` (30 days), and `record` this file.
   - `scripts/quality/tests/test_npm_audit.py`, `TheRepositorysExceptions`: the expected set changes from the empty set to `{"GHSA-fc5q-39xc-vjpf"}`, and its comment names this record. **The reason:** the owner's decision to record this exception. The test stays as strict: any other exception still fails it, and the per-entry checks (every field, a date, the record names the advisory) now run on this entry.
   - **Removal:** the exception is to be removed as soon as a fixed `picomatch` is published and the lockfile takes it, or by its review date. The audit itself fails the exception if npm stops reporting it, and fails the advisory once `review_by` passes.
   - **Not included:**
     - `npm_audit.py` and `ui.sh`;
     - the UI's packages and lockfile;
     - PR #127, which is rerun after this merges.
3. **Done when:**
   - The full gate passes in CI with the audit reading `allowed GHSA-fc5q-39xc-vjpf in picomatch until 2026-12-17: …` and "npm audit: 1 advisories, all recorded exceptions"; the quality tools' tests pass, `TheRepositorysExceptions` included; the OS image passes. The mutants run does not run (no Rust changes).
   - No red commit: this is not a defect in the code. The red is CI's own failure, cited above.
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** these two files and this record. On the Mac, `git diff --check` and a JSON parse of the file; the Python tests run in CI (they run only through `safe-run.sh`, which this Mac cannot provide). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Change, `b6f5e17`

- `ui/audit-exceptions.json`: one entry, `GHSA-fc5q-39xc-vjpf`, package `picomatch`, `review_by` `2026-12-17`, record this file; its `why` gives the reasons above and says to remove it once a fixed `picomatch` is published.
- `scripts/quality/tests/test_npm_audit.py`, `test_each_names_the_record_that_gives_its_reason`: `assertEqual(set(exceptions), {"GHSA-fc5q-39xc-vjpf"}, …)`, with its comment naming this record. **Test change, with its reason:** the owner's decision to record this exception. Any other exception still fails it, and the per-entry checks now run on this one.
- On the Mac: the file parses; `npm_audit.exception_problems` gives `[]` for the entry, and this record names the advisory; the test file parses; `git diff --check` is clean. The Python tests and the audit run in CI.
