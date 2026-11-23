# Build Record — the SetupHub's power-return step, explained and never shown done (stage 1, plan §4.1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/power-return-step`, from `main` at `ec991a6`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature |

## Intent: the owner's words

- **"A, then Next"** (2026-11-22), after `docs/build-records/2026-11-22-power-return-design.md`: option A, "Explained, never done". The step shows how to find the firmware setting, with "Can't be checked on this machine", a state of its own so it is not mistaken for a failed read.
- The plan, §4.1: every node "must start by itself when power returns (stage 1): the setup page explains the N150 firmware's power-on-after-power-loss setting once".

## Design

- **`hub.rs`:** a new step `SetupStep::Power` (`"power"`), after the name and before Bitcoin; and a new state `StepState::Manual` (`"manual"`): the node cannot read it, the owner checks it, and it is never shown as done. `report` gives the power step `Manual` always: nothing on the node is read for it (the design note: Linux cannot read the setting on the N150).
- **The generated types** (`ui/src/generated/SetupStep.ts`, `StepState.ts`): as ts-rs writes them; the gate's drift test holds them.
- **The page:** `api.ts`'s closed sets gain `power` and `manual`; `Home.svelte` shows the power step's explanation and its own mark while it is `manual`; `en.json` gains the step's name, the state's words and the explanation.
- **The runbook** (`docs/runbooks/install-node.md`): the hub's list gains the step, and a new last step sets the firmware once, reporting the setting's name as found on the N150 (not yet proven).
- **Not changed:** the other steps and their states; sign-in; the restart sentence; the Pi (D1).

## Task Contract

1. **Outcome:** the owner sees, on the SetupHub, that the node must start again by itself after a power cut, how to set that once in the firmware, and that the node cannot check it.
2. **Scope:** routine (a setup step's text and an enum; no auth, funds or keys).
   - `control-plane/crates/rikuri-control/src/hub.rs` and its tests; `control-plane/crates/rikuri-control/tests/hub_route.rs`.
   - `ui/src/generated/SetupStep.ts`, `ui/src/generated/StepState.ts`, `ui/src/lib/api.ts`, `ui/src/secure/Home.svelte`, `ui/src/i18n/en.json`, `ui/tests/owner.spec.ts`.
   - `docs/runbooks/install-node.md`; this record; the design record's CI line.
   - **Not included:** reading any firmware value (option C, a task of its own after an N150 check); stored wizard state; the Pi.
3. **Done when:**
   - the hub lists seven steps, the power step `manual` in every node state, at the route and on the page; the page shows the explanation and never "Done" for it; an unknown state is still refused;
   - the full gate passes in CI (the Rust and the UI tests at phone, tablet and desktop widths);
   - one `verifier` pass (code; AGENTS.md §5).
4. **Authority:** the files above. On the Mac: `git diff --check` and reading; the tests run in CI only. Commit and push this branch; a draft PR to `main`; the owner merges.
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; time is reported.

## Evidence log

### The change

- As designed. The page's explanation (`hub.power_how`) names the setting's usual names and the keys Delete or F2. Neither is proven on the owner's N150; the runbook's new step 15 asks for the name and menu as found. Its mark is `i`, not the `?` of a failed read.
- **Reasons for the test changes** (a feature, not a defect fix: no red commit; AGENTS.md §5 asks for a reason for each change):
  - `hub.rs`, `every_step_in_order_with_its_state_from_the_node`: the expected list gains `Manual` in fourth place, the new step's place. No other expectation changes.
  - `hub.rs`, `the_json_is_the_api_the_page_reads`: a second step, `power` with `manual`, so the new names' JSON is held. The first step is kept as it was.
  - `hub.rs`, new `the_power_step_is_manual_whatever_the_node_s_state`: with or without an owner, under the setup name, a name of its own or an unread hostname, the power step is listed once, `manual`.
  - `tests/hub_route.rs`: the route's list gains `("power", "manual")`. After the rename and after the unread hostname the step is still `manual` (two added asserts).
  - `ui/tests/owner.spec.ts`: the fixture `HUB` and the hub's `STEPS` gain the step; a count of 6 becomes 7. New: the power step shows its name, `Can’t be checked on this machine`, the explanation and the mark `i`, and never `Done` or `Couldn’t be read`. The tests that refuse an unknown state (`finished`) and a partial or reordered list are unchanged and still hold.
- On the Mac: `git diff --check` clean; `scripts/cargo.sh fmt --check` passed (formatting only, no tests run).
