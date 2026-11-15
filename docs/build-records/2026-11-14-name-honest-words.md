# Build Record — the naming page says what the name check can see

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-honest-words`, from `main` at `06b2e64`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `1889568` (contract), `6a0c3f7` (change); the owner merged `main` in as `2434c83` (only #107's close-out); merged as `b891a38` (#108) |
| **Status** | DONE |
| **Change type** | feature (text) |

## Intent: the owner's words

- "Next" (2026-11-14), to the proposed task on the backlog item from 5c.4b-2 (`docs/build-records/2026-11-13-5c4b2-naming-page.md`): "a network that drops mDNS replies makes every name look free."
- The owner's choice, 2026-11-14: "Honest words (Recommended)": no new checks. The naming page says the check found nothing answering right now, and the help text explains what to do if two devices share a name.

## Why

- `hostname::FREE` reads resolved's `DnsError.NXDOMAIN` and `DBus.Error.Timeout` as "nothing answers that name". Silence is all mDNS can give: a device that is switched off, or a network that does not pass multicast between devices, also gives silence. So "free" means "nothing answered now", and the page and the runbook should say that, not more.

## Task Contract

1. **Outcome:** an owner naming the node knows the check sees only devices that answer right now, and knows what to do if the name later reaches another device.
2. **Scope:** routine: text only; no answer, route or check changes.
   - `ui/src/i18n/en.json`: one new text, `name.seen`.
   - `ui/src/secure/Name.svelte`: shows `name.seen` in the form, under the name field, always.
   - `ui/tests/owner.spec.ts`: the first naming test also expects `name.seen` to be visible.
   - `docs/runbooks/install-node.md`, step 13: "that nothing on your network answers to" gains "right now", with why; one more bullet: if the name later opens another device, use the node's address.
   - **Not included:** asking twice; any change to `FREE`; the threat model and lessons register; other languages (there is only `en.json`).
3. **Done when:**
   - CI's full gate passes, including the setup pages' build and the Playwright tests at phone, tablet and desktop widths (`scripts/quality/ui.sh`); the mutants run and the OS image pass.
   - `git diff --check` is clean, and the runbook's links still resolve.
   - One verifier pass (the change has page and test code).
4. **Authority:** these files. The UI tests run in CI only. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Change

- `en.json`: `name.seen`: "The node checks that nothing on your network answers to the name right now. It can’t see a device that is switched off, or one your network keeps apart."
- `Name.svelte`: `<p class="hint">{t('name.seen')}</p>` under the field, in every form state; the existing hint (none free, or could not check) follows it.
- `owner.spec.ts`: the first naming test expects `name.seen` to be visible. This adds an assertion; none is changed.
- `install-node.md`, step 13: "answers to right now", why (a device switched off, or kept apart, "some guest Wi-Fi networks do"), and a new bullet for a name that later opens another device: use the node's address and report it.
- `git diff --check` is clean; `en.json` parses. The runbook gains no links. The UI build and Playwright tests run in CI.

### CI: Pass

- On `6a0c3f7`: `Full gate (Ubuntu)` [run 43653254230](https://github.com/rikuripi/rikurinode/actions/runs/43653254230) and OS image [run 43653254307](https://github.com/rikuripi/rikurinode/actions/runs/43653254307).
- On `2434c83`: `Full gate (Ubuntu)` [run 43655850299](https://github.com/rikuripi/rikurinode/actions/runs/43655850299) and OS image [run 43655849947](https://github.com/rikuripi/rikurinode/actions/runs/43655849947).
- In both: `svelte-check found 0 errors and 0 warnings`, the build, and Playwright `399 passed`. The first naming test passes at phone, phone-webkit, tablet and desktop.
- **A correction to "Done when":** it listed the mutants run, which cannot run here. `mutants.yml` triggers only on `control-plane/**`, `rust-toolchain.toml` or itself; no Rust changed, so no run exists: N/A, not passed.
- The owner merged #108 at `2434c83` (as `b891a38`) before the verifier ran.

### The verifier, at `2434c83`: PASS

- **The words match the code:** `FREE` reads NXDOMAIN and a timeout as free; the check runs at the suggestion and again at the rename (`http.rs:701-704`, `:764`); a named node gets 409 "the node already has a name" (`http.rs:750-752`), so "renaming the node comes with a later update" is accurate.
- **The page:** `name.seen` shows in every form state, before the existing hint and alert, which are unchanged and in their order. It reuses the global `.hint` class, so the CSP sees nothing new. The state tests and `text-keys.spec.ts` pass.
- **The test:** the one added assertion reads the text from `en.json`, so a missing element fails it; nothing loosened.
- **The runbook:** agrees with the page and the next bullet; no links added; `git diff --check` is clean.
- `2434c83` adds only #107's close-out of `2026-11-14-suggest-timeout-log.md`.
- **Findings:** no Important finding. Nits:
  1. the mutants line in "Done when" (corrected above);
  2. this close-out (answered here);
  3. in the could-not-check state the page shows "The node checks that nothing … answers" right above "The node couldn't check which names are free". A novice may read them as a contradiction;
  4. the runbook's new bullet assumes the other device keeps the name; mDNS conflict handling might rename one of them instead. The bullet says "If …", so it stays true, but incomplete.

### Close-out

- **Done when:** met. The gate, the page build and Playwright at every width, and the OS image passed; the mutants run does not apply; the verifier passed.
- **Repairs:** 0. Review rounds: 1.
- **Used:** no budget is configured. One CI push of mine, one merge of the owner's, one verifier pass.
- **Backlog, not started:** nit 3 (the two hints side by side), nit 4.
