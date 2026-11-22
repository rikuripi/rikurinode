# Build Record — design note: the SetupHub's power-return step (stage 1, plan §4.1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `docs/power-return-design`, from `main` at `9345ee7`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | design note (documentation only) |

## Intent: the owner's words

- **"Next"** (2026-11-22), after the stage 1 analysis (in the session). Its Next: a design note for the power-return step: what the SetupHub says, what Linux can read on the N150 and the Pi, and which state it shows, with the owner's choice between "can't be checked here" and "done when the owner confirms".
- The plan, §4.1: every node "must start by itself when power returns (stage 1): the setup page explains the N150 firmware's power-on-after-power-loss setting once, and checks it where the firmware lets Linux read it."

## Task Contract

1. **Outcome:** the owner can choose how the power-return step works from one note that says what each choice shows and what Linux can and cannot read.
2. **Scope:** routine (documentation).
   - This record, holding the design note.
   - **Not included:** any code, page, string or test; the step itself (a task of its own, after the owner's choice); an experiment on the N150.
3. **Done when:** the note states what Linux can read on the N150 and the Pi with its sources, the options for the step's state with their costs, and a recommendation; link checks and `git diff --check` pass; CI's `Full gate (Ubuntu)` passes on the draft PR.
4. **Authority:** this file. Web searches (reading only; nothing downloaded). Commit and push this branch; a draft PR to `main`; the owner merges. No verifier pass: documentation only (AGENTS.md §5).
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; time is reported.
