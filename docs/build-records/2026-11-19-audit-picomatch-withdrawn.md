# Build Record — remove the withdrawn picomatch exception

| | |
|---|---|
| **Date** | 2026-11-19 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/audit-picomatch-withdrawn`, from `main` at `96e546f`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled in as they land) |
| **Status** | IN PROGRESS |
| **Change type** | control change (the gate's npm audit exceptions) |

## Intent: the owner's words

- "1" (2026-11-19), choosing the first of two options put to the owner: "**(Recommended)** Remove the exception, so `ui/audit-exceptions.json` becomes `{}`. […] `TheRepositorysExceptions` would then expect the empty set." The other option was to wait in case GitHub republishes the advisory, with `main` and every PR red until then.

## What happened

- On PR #131 (docs only), the full gate's npm audit failed in [run 44436652769](https://github.com/rikuripi/rikurinode/actions/runs/44436652769), verbatim:
  `npm_audit: FAIL GHSA-fc5q-39xc-vjpf: excepted, but npm no longer reports it; remove the exception`
- `gh api /advisories/GHSA-fc5q-39xc-vjpf` (read 2026-11-19): summary "Withdrawn Advisory: picomatch vulnerable to ReDoS through single-branch repeated extglobs"; `withdrawn_at` `2026-11-18T15:38:56Z`; `picomatch <= 4.0.7`; no patched version. npm no longer reports a withdrawn advisory.
- `main`'s last green gate ran at `2026-11-18T03:46Z`, before the withdrawal; the gate now fails on every branch, `main` included, until the exception goes.
- A withdrawal is not a fix: `ui/package-lock.json` still has `picomatch 4.0.7`, and nothing in the code changes. The exception goes because there is nothing left for it to allow. The 2026-11-17 record's reasons (build-time only, the build's own patterns) still describe how picomatch is used.

## Task Contract

1. **Outcome:** the gate's npm audit passes again with no exceptions, and still fails on any advisory npm reports.
2. **Scope:** high-risk (an input of the full gate: BUILD-PROCEDURE, "Risk tiers").
   - `ui/audit-exceptions.json` becomes `{}`.
   - `scripts/quality/tests/test_npm_audit.py`, `TheRepositorysExceptions`: the expected set changes from `{"GHSA-fc5q-39xc-vjpf"}` to the empty set, and its comment names the withdrawal and this record. **The reason:** the owner's decision to remove the withdrawn exception. The test stays as strict: any exception added later still fails it, and its message still says a new exception is an owner decision.
   - `docs/build-records/2026-11-17-audit-picomatch-exception.md`: a dated clarification at the end. The advisory was withdrawn on 2026-11-18, and its exception was removed by this record. No earlier text is rewritten.
   - **Not included:**
     - `npm_audit.py` and `ui.sh`;
     - the UI's packages and lockfile: `picomatch 4.0.7` stays;
     - PR #131, which is updated from `main` after this merges.
3. **Done when:**
   - The full gate passes in CI with the audit step reading "npm audit: 0 advisories, all recorded exceptions"; the quality tools' tests pass, `TheRepositorysExceptions` included; the OS image passes. The Rust mutants run does not run (its path filter does not match).
   - No red commit: this is not a defect in the code. The red is CI's own failure on #131, cited above.
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** these three files and this record. On the Mac, `git diff --check` and a JSON parse of the file; the Python tests run in CI (they run only through `safe-run.sh`, which this Mac cannot provide). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log
