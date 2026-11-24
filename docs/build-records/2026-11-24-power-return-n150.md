# Build Record — the N150's power-return setting, found and set by the owner; the page and runbook name it (stage 1, plan §4.1)

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/power-return-n150`, from `main` at `41b870d`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `3449889` (record and contract), `c1f688e` (the text): PR #172, merged by the owner at `c1f688e` (`5ad035d`); this close-out on `docs/power-return-n150-record`, a docs-only PR |
| **Status** | DONE |
| **Change type** | documentation and page text |

## Intent: the owner's words

- **"Next"** (2026-11-24), after `docs/build-records/2026-11-22-power-return-step.md` ended DONE. Its Next: run the install runbook's step 15 on the N150 and report the setting's name, menu and key, and whether the node started by itself after the unplug.

## What the owner saw on the N150 (2026-11-24)

- **Not found under the runbook's names:** "Couldn't find anything selection related to AC Power loss/recovery".
- **Found:** "Menu is Chipset --> PCH-IO-->State After G3-->S0 or S5; Delete opened the BIOS." The owner "just set it to S0".
- **The unplug test:** "The mini PC restarted automatically after plugging back in", showing GRUB's line "Booting 'Fedora Linux 45 (IoT Edition) (ostree:0)'".
- **Not observed:** what **The last restart** said after the unplug (not reported); the setting's default before the change (the owner set it without saying what it was); the firmware's maker and version.

## Task Contract

1. **Outcome:** an owner of this N150 finds the power-return setting by the path the firmware shows, the first time.
2. **Scope:** routine (text).
   - `ui/src/i18n/en.json`: `hub.power_how` names Delete first and the N150's path, **Chipset**, **PCH-IO**, **State After G3**, **S0**; the other names stay for other machines; the safety lines stay.
   - `docs/runbooks/install-node.md`, step 15: the same, and the check's result as the owner saw it.
   - This record.
   - **Not included:** the step's state (`manual`, the owner's option A, unchanged); option C; any code or test.
3. **Done when:** the page and the runbook name the path the owner found; the page test, which compares the whole string, passes unchanged in CI's `Full gate (Ubuntu)`; `git diff --check` clean.
4. **Authority:** the files above. Commit and push this branch; a draft PR to `main`; the owner merges. No verifier pass: no code changes (AGENTS.md §5); the one string is held by the unchanged page test.
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; time is reported.

## Evidence log

- `ui/src/i18n/en.json`, `hub.power_how`: Delete first, F2 for some machines; "On the N150, open Chipset, then PCH-IO, and set “State After G3” to S0"; the other names for other machines; "Change nothing else" and "If you can’t find it, change nothing and report it" kept. The JSON still parses. It contains neither "Done" nor "Couldn’t be read", which the page test requires it not to.
- `docs/runbooks/install-node.md`, step 15: the N150's path first, S5's meaning, the other names for other machines, and the GRUB line the owner saw after the unplug.
- No test changes: the page test compares the whole string through `t('hub.power_how')`.
- The menu's label is as the owner typed it, "PCH-IO"; the firmware may show it as "PCH-IO Configuration". Not yet proven: the exact label.

## CI, `c1f688e`: Pass

- `CI`, [run 45489813255](https://github.com/rikuripi/rikurinode/actions/runs/45489813255): `Full gate (Ubuntu)` Pass, `full-gate: all 11 steps passed`; the page's Playwright tests `507 passed`, the power step's whole string among them, unchanged.
- The image workflow, [run 45489813229](https://github.com/rikuripi/rikurinode/actions/runs/45489813229): Pass.

## Result

- **Pass (observed):** the owner's N150 starts by itself when power returns, with **State After G3** set to **S0** under **Chipset**, **PCH-IO** (the owner's unplug test, 2026-11-24). The page and runbook step 15 name that path, and Delete (run 45489813255).
- **Not yet proven:** **The last restart**'s sentence after the unplug; the menu's exact label; the setting's value before the change.
