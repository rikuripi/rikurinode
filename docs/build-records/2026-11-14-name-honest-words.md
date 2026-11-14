# Build Record — the naming page says what the name check can see

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/name-honest-words`, from `main` at `06b2e64`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
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
