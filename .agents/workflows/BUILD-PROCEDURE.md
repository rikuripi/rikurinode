# BUILD PROCEDURE — Rikuri Node

How changes are built here: planning, building, debugging, testing, review, incidents and release. [`AGENTS.md`](../../AGENTS.md) governs how an agent carries out one assignment: the Task Contract, the limits of two repair cycles and two review rounds, the outcomes `DONE`, `BLOCKED` and `NEEDS_OWNER_DECISION`, and stopping. This document governs what each step must contain. Where the two differ on how many times to try, `AGENTS.md` applies. Where they differ on what counts as evidence, this document applies.

The goal is a system where mistakes cannot travel. Every defect is caught by the nearest gate, made loud, and turned into a check. The depth of each step follows the change's risk tier.

This copy was condensed for Rikuri Node on 2026-10-13. It differs from the other repositories' BUILD-PROCEDURE.md, and Git history keeps the full earlier text. "rikurinode" below means the previous repository at `/home/junc/rikuri/rikurinode`.

---

## The Five Laws

1. **Nothing is silent.** Every component runs and is gated by a test, or it is deleted. A fallback that engages is an alert, never just a save.
2. **Stop the line.** A red required gate halts dependent work. It does not authorize unlimited repair: after the task's two repair cycles, report `BLOCKED` with the exact failure, and the owner decides. Never disable or weaken the check. Skipped or excluded code is counted, scheduled debt.
3. **Standard work.** The Per-Change Loop applies to every change, at its tier's depth.
4. **Alert on the absence of success.** Last-success times and heartbeats, not only error handlers.
5. **Turn defects into tripwires.** Every fixed defect gets a regression test. A class-wide tripwire (a test, invariant, monitor, ratchet or refusal) follows the risk tier. Every incident ends with one.

---

## Phase 0 — Project Bootstrap (before the first feature)

A project is a prototype until it has:

- a protected `main` with CI that gates: build, typecheck, tests, lint and secret scan, none allowed to fail, proven by a red-test drill;
- a pre-commit hook with a secret scan;
- a smoke script: one command that probes every service, port and page the system claims to provide, with distinct content markers (not only "the port answers"), and echoes the active configuration;
- a debt ratchet with committed baselines;
- no secret in the repository: secrets live outside the tree, and where each one lives is documented;
- every dependency and image pinned, with lockfiles committed;
- status and version shown from the running process.

Here, the smoke script and the ratchet come with B0.3 (`AGENTS.md`, "Verification by maturity").

---

## Risk tiers

**High-risk** changes touch any of:

- funds, keys, seeds, macaroons or credentials;
- anything that talks to bitcoind or LND;
- backup, restore, update, rollback, migration or deletion;
- the OS image, its signing or its boot checks;
- a trust or security boundary: network exposure, authentication, the assistant's authority;
- anything irreversible;
- a control that enforces these: CI, the full gate, the sandbox settings, the guard and its policy, `safe-run.sh`, `REVIEW.md`, the verifier, and the agent rules themselves (`AGENTS.md`, `CLAUDE.md`, this procedure and its Build Record template).

**Routine** changes are everything else: other documentation and process text, tooling, tests, scaffolding, refactors that leave high-risk behaviour unchanged, messages and wording.

How to tier a change:

- The Task Contract's Scope names the tier.
- When unsure, choose high-risk.
- A routine change found to touch high-risk behaviour is re-tiered in its Build Record.
- A change to a protected path (the paths listed in `.claude/hooks/guard-config.json`) gets its risk note whatever its tier.

| Step | Routine | High-risk |
| --- | --- | --- |
| Intent and spec | The Task Contract's Outcome | The intent in the owner's words, approved by the owner; the spec applies the design rules and the security baseline up front |
| Build Record | Brief: Task Contract, plan, verification, disposition | Full, with risk and negative-test evidence |
| Tests during the work | Targeted tests, and a regression test for every defect fixed | The same, plus the boundary, recovery and failure tests the change affects |
| Fix-lock | Opt-in; seldom worth it | Opt-in; worth engaging for a defect in high-risk code. It becomes the default before the first code that talks to LND or bitcoind, or handles keys, seeds or macaroons (`AGENTS.md` §6) |
| Fix the class | A search of the module touched | One repository-wide search for the same pattern; directly affected siblings fixed, the rest to the backlog |
| Class tripwire, beyond the regression test | Only for a defect seen twice | For the failure class, where practical |
| Independent review | Documentation only: the `AGENTS.md` §5 checks and the owner's pull-request review, no verifier. Code: one verifier pass | One verifier pass, including the mutation run its instructions name |

Either tier may get one follow-up pass on corrected findings.

- **The review's finish line.** Severity is `REVIEW.md`'s: Important or nit. Only an Important finding fails a pass. Nits never fail a pass and never start another one: they are fixed in place or listed in the Build Record. A wording finding gets its fix, not a new gate. An overstated sentence is Important only when it claims a gate or stage result, a security or funds property, data integrity or completion that the evidence does not support.
- **Test adequacy.** In routine code, a missing test is Important only when the change's own "Done when" depends on it.
- **The mutation run (high-risk code).** The first verifier pass mutates the changed lines inside `safe-run.sh`: `cargo mutants` for Rust, a few hand mutations of the changed checks for other code, with the settings in `.claude/agents/verifier.md`.
  - A surviving mutant in a refusal, validation, recovery, funds or integrity check is Important; other survivors are nits.
  - The run surfaces the untested conditions the tool can reach in one pass, instead of one per round.
  - It does not find missing rules; the reviewer finds those by reading the change against its Plan.
- **The follow-up pass.** It checks the corrections and reruns that mutation scope; it does not search for new findings. A new Important finding it happens to see ends the task in `NEEDS_OWNER_DECISION`, and the owner decides whether it is fixed now, as its own task, or recorded as debt.
- **Controls are adequate when they cover what the repository uses.** A gap for a form the repository does not contain is owned debt, not a new task.

---

## The Per-Change Loop (every change, at its tier's depth)

One Build Record per change, from [BUILD-CHECKLIST-TEMPLATE.md](BUILD-CHECKLIST-TEMPLATE.md), at `docs/build-records/YYYY-MM-DD-<slug>.md`, begun during planning and committed with the change. An unchecked box without a written Skipped entry means the change is not done, and "to save time" is not a reason.

### 1. PLAN
- [ ] Task Contract, with the tier (`AGENTS.md` §3). A change you cannot state in one sentence gets split.
- [ ] The blast radius: which modules, data, funds, keys or node paths it touches, and whether any of it is irreversible.
- [ ] Characterize before changing: run or read the current behaviour; do not plan against assumed behaviour.
- [ ] "I will know this works when ___". If the answer is "it compiles", there is no plan yet.
- [ ] The files that change, the order of work and the riskiest step.

### 2. BUILD
- [ ] Smallest coherent increment; one concern per commit.
- [ ] Typed code, with inputs validated at trust boundaries. Files over about 800 lines get a second look.
- [ ] Clean as you go: the old version of anything replaced goes in the same change.
- [ ] Ask whether the change touches authentication, money, execution or private data. If it does, it is high-risk; name the gate that covers it and the test that proves the gate. Hardening that breaks a legitimate path is also a defect, so check both directions.

### 3. DEBUG
- [ ] Reproduce first, and read the actual error or log.
- [ ] Commit the failing test before the fix (`AGENTS.md` §5); the fix-lock is opt-in (`AGENTS.md` §6). While a session holds the lock:
  - test files and baselines are read-only to it, and so are tests inside a source file (Rust's `#[cfg(test)]` module or a test-only helper, from the marker to the end of the file; `inline_tests` in `guard-config.json`). An Edit to such a file must leave the tests unchanged, and a shell write to any `.rs` file is refused, so use Edit or Write;
  - lines with `cfg(test)`, `cfg!(test)`, `cfg_attr(test, …)` or an assert-macro shadow cannot be added, removed or changed;
  - this is a tripwire, not a wall: compare the "N passed" count before and after the fix, since a disguised switch-off shows as a drop there; other disguised cheats are left to review;
  - the lock binds only the session that took it (owner, 2026-10-03); taken in the owner's terminal it binds every session. `fix-lock off` releases only your own, every release is logged to `.claude/state/fix-lock.log`, and the verifier checks the log against the Build Record.
- [ ] Fix the class at the tier's depth.
- [ ] Before a restart, a delete or a config change, check that the evidence supports this action.

### 4. TEST / VERIFY
- [ ] Unit tests for the logic added, including its failure paths.
- [ ] A regression test for a fixed bug, shown failing on the old code.
- [ ] Watch it work through the real entry point, in a fixture or scratch environment, never on the live node.
- [ ] A changed recovery or fallback path is triggered, in a fixture or scratch copy: one never exercised is a hope, not a feature.
- [ ] High-risk only: test the boundary in both the allowed and the denied direction.

### 5. CLOSE OUT
- [ ] Run the full gate (`scripts/quality/full-gate.sh`) once, at the acceptance boundary. Targeted checks are enough during the work. A documentation-only change runs the `AGENTS.md` §5 checks. A `BLOCKED` task ends with an honest report, not a green gate.
- [ ] Scrap Sweep (below).
- [ ] Help pages and runbooks updated in the same change (`AGENTS.md`, "Knowledge layer").
- [ ] Review per `REVIEW.md`.
- [ ] A commit message that explains why.
- [ ] Deploy equals build: one scripted path from source to the running system, with no hand-copied artifacts.

---

## The Scrap Taxonomy (Scrap Sweep)

Scrap is anything that helped you reach the change but is not the change. Remove what this task created, in the same session:

- probe scripts and temporary harnesses;
- applied one-shot scripts, which are dangerous to re-run;
- the old version left beside the new;
- debug residue and temporarily loosened checks;
- stray files this task made (`.bak`, swap files, editor leftovers);
- proven orphans, after checking imports, scripts, units, runbooks and dynamic loading.

Keep user data, reproducible migrations, rollback tools, fixtures and evidence.

An untracked file this task did not create is reported, not deleted: age or an unknown purpose is not deletion authority.

Other sessions' work, stale stashes, branches whose work landed and leftover worktrees are reported, not removed: the owner disposes (`AGENTS.md` §2).

Anything excluded from CI or skipped is counted, scheduled debt with a named stage in which it is fixed or deleted.

---

## Periodic Loops (owner obligations)

These are scheduled by the owner. They are never an agent's self-assigned work, and they never run against the live node without the owner's instruction. After each one, findings become fixes, and fixes become tripwires.

- **Weekly:** smoke run; a scan for engaged fallbacks and repeated warnings; no uncommitted drift older than a week.
- **Monthly, rotating drills:**
  - restart with zero manual steps;
  - failover, where recovery must be loud;
  - mode switch, with state and funds integrity checked at each hop;
  - restore of a real backup into scratch.
- **Quarterly:**
  - a security pass over authentication, funds and execution paths;
  - a dead-code sweep;
  - a dependency and image audit (living sources, end-of-life dates);
  - an architecture check of documents against tested invariants;
  - a fresh-eyes review, plus a human external audit before any public exposure.

---

## Incident Procedure (when something breaks in production)

1. Stabilize with the least destructive action the evidence supports.
2. Capture the state before fixing erases it.
3. Find the cause down to its class, not just the symptom.
4. Add a tripwire that makes the class loud or impossible.
5. Record the incident, including the false leads, where the next session will find it.
6. Sweep for siblings of the same class.

---

## Working with AI Assistants

AI sessions follow `AGENTS.md`.

- **Rules that must not be skipped are enforced, not written down.** The rules whose violation is expensive or irreversible are enforced by Claude Code's sandbox and by the PreToolUse guard (`AGENTS.md`, "Deterministic gates"; detail in `docs/guard-and-sandbox.md`). Prose carries judgement; hooks carry rules.
- **Ask means the owner decides**, in the UI, every time, even in auto mode and even when the tool is pre-approved. **Deny means no one does from inside a session**: the owner runs it by hand.
- **The guard is code, gated like code.** `test_guard.py` replays every worked example in its policy plus generic and failure-mode cases, and the full gate runs it.
- **The guard's lesson loop.** A rule an agent breaks becomes a guard entry with a worked example, but only when breaking it is expensive or irreversible, and only for forms the repository uses.
- **Repeated mistakes.** A mistake an agent repeats becomes one line in `AGENTS.md`.
- **Profiles.** The guard has two:
  - `development` (current): asks only before money moves and secret files; other asks are allowed and logged.
  - `stable`: asks at every gate.
  - Switch with `python3 .claude/hooks/guard.py profile development|stable`. Loosening asks the owner; tightening is free.
- **Deferred, named:** CI evals that re-run real past tasks whenever `AGENTS.md` or `.claude/` changes. Revisit when an instruction regression is seen twice.

---

## Release Gate — Definition of Done for public exposure

A project may be shown, shipped, or opened to others only when:

- [ ] N× clean restart drill passes with zero manual steps.
- [ ] Fresh-clone deploy on a clean machine works from documentation alone
      and comes back as the same system (same identities, same data).
- [ ] CI is fully gating; the ratchet baselines are at their floor targets.
- [ ] Every mutation endpoint has a named gate and a test proving it.
- [ ] No secrets in history (full-history scan), all credentials rotated.
- [ ] Docs describe the system as it IS; a stranger can operate it from them.
- [ ] The system has run unattended through a soak period (48h+) with every
      scheduled job, backup, and monitor verified to have fired.
- [ ] An adversarial review (automated + human for security-critical paths)
      has run against the release candidate.

Until every box is checked, the honest label is "prototype" — and prototypes
don't take deposits, hold keys, or accept strangers' trust.
