# Build Record — the naming page no longer says "checks" above "couldn't check"

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-hint-clash`, from `main` at `412549d`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | fix |

## Intent: the owner's words

- "Next" (2026-11-14), answering the proposed task: "when the node couldn't check, the page should show only its 'couldn't check' message and leave out the new sentence, so the two don't read as a contradiction."
- The verifier's nit 3 in `docs/build-records/2026-11-14-name-honest-words.md`: in the could-not-check state the page shows "The node checks that nothing … answers" right above "The node couldn't check which names are free".

## Task Contract

1. **Outcome:** an owner whose node could not check sees only "couldn't check … You can still type one", not a sentence saying it checks.
2. **Scope:** routine: one page's text, by state.
   - `ui/src/secure/Name.svelte`: `name.seen` shows once the suggestion is read: with a suggestion, or with none free. It does not show while the suggestion loads, or when it could not be read, so there is no flash of it before "couldn't check".
   - `ui/tests/owner.spec.ts`:
     - the four "a suggestion that fails" cases expect `name.seen` absent (the red);
     - "no free name" expects it visible.
   - **Not included:** the texts themselves; the runbook (it describes the check, not the page's states); nit 4.
3. **Done when:**
   - The failing-suggestion assertion is seen failing in CI on the current page (a red commit, pushed alone), then passing on the fix.
   - CI's full gate passes, with the page build and Playwright at every width; the OS image passes. No Rust changes, so the mutants run does not apply.
   - One verifier pass.
4. **Authority:** these files. The UI tests run in CI only. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Red (the current page)

- `owner.spec.ts`: in the four "a suggestion that fails" cases, after `name.check_failed` is visible, `name.seen` must have count 0. "no free name" also expects `name.seen` visible.
- **Expected on the current page:** `name.seen` shows in every form state, so the four failing cases fail at every width; "no free name" passes.
- Pushed alone, so CI shows the red before the fix.

### CI on `a94e912` (the red): Fail, as expected

- `Full gate (Ubuntu)`, [run 43659577369](https://github.com/rikuripi/rikurinode/actions/runs/43659577369): `16 failed`, `383 passed`. The 16 are the four "a suggestion that fails" cases (`owner.spec.ts:602`) at phone, phone-webkit, tablet and desktop, each at the new assertion: `no "checks" above "couldn’t check"`, `Expected: 0`, `Received: 1`. "no free name" passed.
- OS image [run 43659577366](https://github.com/rikuripi/rikurinode/actions/runs/43659577366) passed.

### Fix

- `Name.svelte`: `let checked = $state(false)`, set true only when the suggestion is read (`kind === 'ok'`), whether it holds a name or `null`. `name.seen` renders inside `{#if checked}`.
- No test changed after red. `git diff --check` is clean; the build and tests run in CI.
