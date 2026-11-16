# Build Record — remove the withdrawn deepmerge exception

| | |
|---|---|
| **Date** | 2026-11-16 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/audit-stale-exception`, from `main` at `d79ae74`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `d679a39` (contract), `b4357d2` (change) |
| **Status** | IN PROGRESS |
| **Change type** | control change (the gate's npm audit exceptions) |

## Intent: the owner's words

- "Next" (2026-11-16), answering the proposed task: "remove the stale `GHSA-gcqx-w48m-w2h4` exception from `ui/audit-exceptions.json`, as its own task in its own PR, and note in the 5c.3a record that npm no longer reports it. Then rerun #124's CI to see the red".

## What happened

- On PR #124 (head `4fa07c2`), the full gate's step 8 failed in [run 43967988915](https://github.com/rikuripi/rikurinode/actions/runs/43967988915), and the mutants run's UI build in [run 43967988871](https://github.com/rikuripi/rikurinode/actions/runs/43967988871). Both failed before any Rust test, verbatim:
  `npm_audit: FAIL GHSA-gcqx-w48m-w2h4: excepted, but npm no longer reports it; remove the exception`
- GitHub's advisory database (`gh api /advisories/GHSA-gcqx-w48m-w2h4`, read 2026-11-16) shows the advisory **withdrawn** at `2026-11-16T18:55:38Z`, summary "Withdrawn Advisory: deepmerge mergeObject() allows prototype poisoning of returned objects". npm no longer reports a withdrawn advisory.
- `scripts/quality/npm_audit.py` fails on an exception npm no longer reports, by design, so a stale exception cannot cover a later advisory. The gate now fails on every branch, `main` included, until the exception goes.

## Task Contract

1. **Outcome:** the gate's npm audit passes again with no exceptions, and still fails on any advisory npm reports.
2. **Scope:** high-risk (an input of the full gate: BUILD-PROCEDURE, "Risk tiers").
   - `ui/audit-exceptions.json` becomes `{}`.
   - `scripts/quality/tests/test_npm_audit.py`, `TheRepositorysExceptions`: the expected set of exceptions changes from `{GHSA}` to the empty set. **The reason:** the owner's decision to remove the withdrawn exception. The test stays as strict: any exception added later, recorded or not, still fails it, and its message still says a new exception is an owner decision. The other tests use their own fixture `EXCEPTIONS` and do not change.
   - `docs/build-records/2026-11-11-5c3a-ui-pipeline.md`: a dated clarification. The advisory was withdrawn on 2026-11-16, and its exception was removed by this record. No earlier text is rewritten.
   - **Not included:**
     - `npm_audit.py` and `ui.sh`;
     - the UI's packages and lockfile: `deepmerge 4.3.1` stays, as no advisory covers it now;
     - PR #124's own work, which resumes after this merges.
3. **Done when:**
   - The full gate passes in CI with the audit step reading "npm audit: 0 advisories, all recorded exceptions"; the quality tools' tests pass, `TheRepositorysExceptions` included; the mutants run and the OS image pass.
   - No red commit: this is not a defect in the code. The red is CI's own failure on #124, cited above.
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** these three files and this record. On the Mac, `git diff --check` and a JSON parse of the file; the Python tests run in CI (they run only through `safe-run.sh`, which this Mac cannot provide). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Change, `b4357d2`

- `ui/audit-exceptions.json`: `{}`.
- `scripts/quality/tests/test_npm_audit.py`, `test_each_names_the_record_that_gives_its_reason`: `assertEqual(set(exceptions), set(), …)`, with a comment naming the withdrawal and this record. **Test change, with its reason:** the owner's decision to remove the withdrawn exception. A later exception still fails it; the per-entry checks have nothing to iterate until one is recorded.
- `docs/build-records/2026-11-11-5c3a-ui-pipeline.md`: a dated clarification at the end; nothing earlier rewritten.
- On the Mac: the file parses as `{}` (`python3 -I`); `git diff --check` is clean. The Python tests and the audit run in CI.
