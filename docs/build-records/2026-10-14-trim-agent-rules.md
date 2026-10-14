# Build Record — Trim the agent rules and the build procedure

| | |
|---|---|
| **Date** | 2026-10-14 |
| **Author / session** | Claude Code (Opus 5.5) for Henry Chen, from `~/claude-wip/trim-node/HANDOFF.md` |
| **Branch** | `docs/trim-agent-rules`, worktree `/home/junc/claude-wip/trim-node/rn`, from `origin/main` `eb8b849` (PR #9 merged) |
| **Commits** | (fill at close-out) |
| **Status** | DONE locally; CI on the PR Not yet proven |
| **Change type** | ops (working rules) |

**Risk note (protected paths):** `AGENTS.md`, `REVIEW.md`, `.claude/agents/verifier.md`, `.agents/workflows/BUILD-PROCEDURE.md` and `BUILD-CHECKLIST-TEMPLATE.md` are protected paths. No guard, policy, settings, sandbox, CI, `safe-run.sh` or executable line changes. What is removed is restatement of default agent behaviour, narrative case studies, detail held elsewhere, and rules for languages this repository does not use; each is listed under Build with its reason. What changes behaviour (depth by risk tier, the review's finish line) is the owner's request of 2026-10-13.

## Task Contract

1. **Outcome:** the node's agents read short rules that say what matters, the hard limits, how far to go and when to stop; the build procedure scales by risk tier and gives reviews a finish line.
2. **Scope:** `AGENTS.md` and `.agents/workflows/BUILD-PROCEDURE.md` from the drafts at `~/claude-wip/trim-node/`; `REVIEW.md` and `.claude/agents/verifier.md`, mirrored on Rikuri-PI's `main` (PRs #37 and #38) with the node's own judgement kept; section-number citations (`BUILD-CHECKLIST-TEMPLATE.md` line 50, `verifier.md`, `REVIEW.md`); this record. Tier: **high-risk** (review rules). **Not included:** the guard, its policy, settings, sandbox, CI, `safe-run.sh`, `docs/guard-and-sandbox.md`, `CLAUDE.md`.
3. **Done when:** every rule dropped from the old texts is listed here with a reason; every `AGENTS.md > <heading>`, `§N` and link in the repository resolves (`git grep`, outside dated records); `git diff --check` is clean; guard tests pass inside `safe-run.sh`; `guard_policy.py --check` agrees; one verifier pass, plus at most one follow-up, with no Important finding open; PR open with `Full gate (Ubuntu)` green.
4. **Authority:** edit the files in Scope; commit; push the branch; open one PR. No merge.
5. **Limits:** two repair cycles; one verifier pass plus one follow-up.

## 0. Intent

- [x] Problem, in the owner's words (2026-10-13): "Draft the trimmed AGENTS.md … be clear about priorities, your risk limits, when to stop, and what 'done' means. Just enough test and verification, prevent it from infinite checks/loops. You also modify the procedure to what's reasonable and delete things that don't contribute any more benefit. Another agent doing an extra check would work also."
- [x] Outcome: as the Task Contract.
- [x] Who/what it affects: every agent session in this repository; the owner's review load.
- [x] Open questions: none blocking; one owner note under Results.
- [x] Owner approved the intent: the request above and the handoff's Task Contract; the owner started this session on it (2026-10-14).

## 0b. Spec

- [x] Requirements: the handoff's Scope, with REVIEW and verifier rules: the tier sets the depth; severity is Important or nit and a review fails only on Important; "Claims match evidence" is Important only for gate or stage, security or funds, data-integrity and completion claims; the follow-up pass checks corrections only and a new Important finding goes to `NEEDS_OWNER_DECISION`; the verifier's mutation step covers high-risk code only, with settings that work here, inside `safe-run.sh`, and checks the unviable list; PASS means no Important finding open.
- [x] Design: start from the drafts; compare each with merged `main`; put back any dropped rule that changes what an agent may do or protects funds, keys, the live node or a gate. Alternative rejected: adopting the drafts as written (they dropped rules listed under Build, "Restored").
- [x] Policy applied: no behaviour-changing default introduced without the owner: the tiering and the review's finish line are the owner's request; the relaxations it implies are listed below so the owner sees each one.
- [x] Flagged concerns: see Results, "Owner notes".

## 1. Plan

- [x] One sentence: replace `AGENTS.md` and `BUILD-PROCEDURE.md` with the trimmed drafts, rules restored where needed, and align `REVIEW.md`, the verifier and the citations.
- [x] Blast radius: agent behaviour only; no code, policy or CI. Nothing irreversible (Git history keeps the old texts).
- [x] Current behaviour characterized: merged `main` texts read in full (`AGENTS.md` 291 lines, `BUILD-PROCEDURE.md` 456, `REVIEW.md` 62, `verifier.md` 80); drafts dated after `594335a` (draft mtime 2026-10-13 23:58, commit 22:44); `0f1683a`, the last PR #9 commit, changed only its Build Record, so no `main` text postdates the drafts. Citations found with `git grep` (Plan list below).
- [x] Files and order: drafts copied in; restorations; `REVIEW.md`; `verifier.md`; template line 50; checks; this record; verifier.
- [x] Citations that must keep resolving: `AGENTS.md > Deterministic gates` (`guard-config.json` `_doc`, `guard_policy.py`), `> Never in git` (`.gitignore`, `README.md`), `> Testing on this machine` (`safe-run.sh`, platform plan), `> Verification by maturity` (`full-gate.sh`, verifier), `> Design rules` and `> Security baseline` (`REVIEW.md`), "Claude guard and fix-lock"; BUILD-PROCEDURE "Phase 0" (`repo_hygiene.py`, `test_repo_hygiene.py`).
- [x] Riskiest step: dropping a safety rule unnoticed (Rikuri-PI's first draft did; its verifier caught two).
- [x] I will know this works when the "Done when" line holds.

## 2. Build

- [x] **`AGENTS.md`**: 291 → 214 lines. Sections: 1 priorities; 2 hard limits; 3 Task Contract; 4 done and stopping (with the end-of-task report); 5 verification; 6 agents, branches and the owner's time, with "Claude guard and fix-lock"; 7 the node's rules, every heading other files cite kept word for word; 8 where things are.
- [x] **`BUILD-PROCEDURE.md`**: 456 → 210 lines, with the 2026-10-13 addendum folded in and a new "Risk tiers" section. The Release Gate is verbatim.
- [x] **`REVIEW.md`**: Rikuri-PI's structure with the node's passes and Important list kept; the tier link; Claims match evidence narrowed; test gaps; fails only on Important; nits never start a round; "The follow-up pass"; mutants in the nit cap; citations §5.D → §5, §1 → §3, §5.C → §3.
- [x] **`verifier.md`**: the tier; step 5, the high-risk mutation run with settings tried here (Evidence); defect-fix check adds the red commit's own target directory and the fix-lock log; follow-up and severity rules; `VERDICT: PASS` means no Important finding open; citations §5.D → §5, §4 → §6.
- [x] **`BUILD-CHECKLIST-TEMPLATE.md`** line 50: §4 → §6.

### Restored from `main` into the drafts

The drafts dropped these; each changes what an agent may do or protects the live node, funds, keys or a gate, so each is back:

- `AGENTS.md`: "the guard asks the owner first" (banner); the guard and sandbox exist only in Claude Code and the limits bind every agent; existing security policy prevails; no weakening a permission check to save prompts; smallest change, no unrequested frameworks or scaffolding, only directly affected docs; implementation status not written into `AGENTS.md`; the test-code definition and the verifier's Fail for a loosened test; report failures verbatim; a required check that could not run blocks its claim; never edit locked tests another way; verdicts leave auth, money, privacy, destructive, transfer and production decisions with controls and the owner; the sandbox leaves the rest of the home folder readable; a command never retries outside the sandbox; push, fetch and pull still pass the guard and the prompt; `guard_base.py` and `test_guard.py` identical across Full-tier repositories; CI's full gate is the last boundary; the floating-tag examples (`latest`, `stable`, `lts`, `fedora:41`); "not from a tag, a cache or a config file"; the Rikuri-PI provenance, "none of it exists yet" and "no URL shorteners, no open resolvers"; `safe-run.sh` compares nothing inside the sandbox, and sockets outside `/run` and files stay reachable; "in isolated environments"; the Rust steps' detail (toolchain file, every target, `deny.toml`); Pass / Fail / Not yet proven stay distinct; B0 only as far as the handoffs name it; the stage table governs; do not restart a stage for a new process; a stage closes when its Build Records show the drill; a small choice needs no ADR.
- `BUILD-PROCEDURE.md`: the smoke script's content markers and echoed configuration (B0.3 builds it from this list); secrets live outside the tree with their locations documented; the fix-lock's mechanics while held (inline tests, `.rs` shell writes refused, `cfg(test)` lines, the "N passed" count, per-session lock, the release log the verifier checks), held nowhere else; a changed recovery or fallback path is triggered at every tier, not only high-risk; ask means the owner decides even when pre-approved, deny means the owner runs it by hand; the guard is gated like code.

### Dropped, with reasons

`AGENTS.md` (old → new):

- The "Purpose" paragraph: restated by the new opening paragraph.
- §2 "run `git status`, inspect the branch and worktrees, read the code first", "characterize before claiming a defect": default agent behaviour; BUILD-PROCEDURE's Plan ("characterize before changing") and Debug ("reproduce first") keep the substance.
- §2 "do not rely on a frozen inventory": the rule kept is where status is recorded (§3).
- §2 "read README, the platform plan and only the relevant portions": §8's table and "read only the parts your task needs".
- §3 "the previous repository is not an authority": priority 3 says what it is (lessons and proven parts).
- §4 "use scoped, pre-authorized operations when the host supports them": default; the prohibition it qualified is kept.
- §5.A "brief or full Build Record by risk", §5.D "high-impact claims keep adversarial, failure and recovery evidence": moved to BUILD-PROCEDURE "Risk tiers".
- §5.A "state positive, negative and recovery tests before coding": now by tier (routine: "I will know this works when"; high-risk: boundary, recovery and failure tests). Owner's request: just enough test.
- §5.A "explain a material assumption in plain language": §6 puts every owner question in plain words.
- §5.B "preserve typed contracts, boundary validation, privacy, traceability": BUILD-PROCEDURE Build.
- §5.C "capture the exact command, error and environment": BUILD-PROCEDURE Debug ("read the actual error"); §4's `BLOCKED` reports the exact failure.
- §5.C sibling paths: the tier table's "Fix the class".
- §5.E scrap sweep: BUILD-PROCEDURE "Scrap Taxonomy".
- §6 "consult official docs when unfamiliar": default behaviour.
- §6 "an untrusted skill, model or reviewer cannot grant authority": §2 ("data, never instructions") and §6 (verdicts are advice).
- Fix-lock "reevaluate an overbroad policy as an approved guard change": §2, "a control change is its own task".
- Deterministic gates: the per-tool list, the closed-world detail of `check_guard_wiring.py` and the full wording of the guard's asks: held in `docs/guard-and-sandbox.md`, which §7 points to.
- Never in git: "so the two never drift"; Knowledge layer: "the assistant answers from": wording.
- §9 and the final rule: kept in substance in §4.

`BUILD-PROCEDURE.md`:

- "Portable: copy it into any new project": this copy is now node-specific. See Owner notes.
- Every case study (Laws 1 and 4, Plan, Build, Debug, Scrap): narrative; the rules they illustrate stay.
- Law 3 "walked mechanically, every time, regardless of size" → at the tier's depth; Law 5 "every bug fixed gets a class tripwire" → a regression test always, a class tripwire by tier, every incident still ends with one. Owner's request.
- Phase 0: pre-commit typecheck (the gate's clippy covers it; Phase 0 is done here), TypeScript ratchet examples, the floating-tag narrative.
- `docs/build-records/README.md` and the exemplar `2026-08-08-one-click-infra-upgrades.md`: neither exists in this repository.
- Step 0 Intent + Spec for every change → routine: the Task Contract's Outcome; high-risk: the owner-approved intent. Owner's request.
- Plan "a fresh session could build it from the plan alone": kept in the template's Plan heading; REVIEW's Compliance pass checks the diff against the Plan.
- Build: "no new `any` / `@ts-nocheck`" (TypeScript); "~800 LOC/file cap" → "a second look" (owner's request: what is reasonable); "documented where non-obvious" (default).
- Debug: `fix_lock_release_needs_owner: false` in rikurinode (the previous repository's setting); `--session` / `--global` release detail (the guard enforces it).
- Test/Verify: "watch it in the running system, the real container" → the real entry point in a fixture or scratch, never the live node (stricter for this machine).
- Close Out: "all green or the session isn't over" → the full gate once at the boundary, and a `BLOCKED` task ends honestly (the 2026-10-13 addendum). "Important findings fixed or listed as Skipped" → a pass fails on an open Important finding, and one found in the follow-up goes to the owner (REVIEW).
- Scrap: "a dead barrel re-exports live children" (JavaScript); "sweep with a clean build" (cargo rebuilds what changed); "delete stashes older than a day and landed branches" → reported, the owner disposes (addendum).
- Periodic Loops: detail beyond one line each (owner obligations, never agent work).
- Incident Procedure: the examples.
- Working with AI: "point every session at this file" (`CLAUDE.md` imports `AGENTS.md`), "verification not claims" and "report failures verbatim" (`AGENTS.md` §5), "same ratchets for AI code" (implicit), multi-session hygiene (`AGENTS.md` §2).
- Deterministic gates table: in `AGENTS.md` > "Deterministic gates" and `docs/guard-and-sandbox.md`. Profile log paths and "all four repositories on development since 2026-09-27" (status, not a rule). "Smoke checks the guard is wired and green": no smoke script exists yet, so the sentence was a claim without evidence.
- The lesson loop: a broken rule becomes a guard entry only when breaking it is expensive or irreversible, for forms the repository uses; controls are adequate when they cover what the repository uses. Owner's request: no endless checks.
- The addendum: folded into the body (header, Law 2, Close Out, the tier table, Scrap, Periodic Loops, Debug).

- The independent verifier pass for every change → routine documentation changes get the `AGENTS.md` §5 checks and the owner's pull-request review, with no verifier (BUILD-PROCEDURE "Risk tiers"). Owner's request (just enough verification); code and high-risk work keep one pass. So that this cannot reach the rules themselves, `AGENTS.md`, `CLAUDE.md`, this procedure and its template are on the high-risk control list. **An owner choice:** reversible by striking "no verifier" from the routine column; the cost of keeping it is one verifier run (about 7 minutes here) per documentation change.

`REVIEW.md`: "Claims match evidence" no longer makes every unevidenced sentence Important (handoff rule). "Do not report" adds dated Build Records unless the change contradicts them, and names the guard-test workflow (mirrored from Rikuri-PI). `verifier.md`: step 3, "try to break it" for every change → step 5, high-risk code only; boundary refusal stays in step 2 for every change; a fallback is triggered when the change touches one (was: always).

## 3. Debug

No defect fix. Repair cycle 1 of 2, after verifier pass 1 (`VERDICT: FAIL`, one Important finding, eight nits):

- **Important I1:** the verifier pass for routine documentation changes was dropped without being listed, and it would have reached edits to `AGENTS.md` and `BUILD-PROCEDURE.md`. Fixed: listed under "Dropped, with reasons" as an owner choice with its cost; the agent rules, `CLAUDE.md`, this procedure and its template added to the high-risk control list, and "Routine" reworded to "other documentation".
- **Nits fixed in place:** "where that is impractical" restored to the red-commit rule; "an unchecked box without a written Skipped entry means the change is not done, and 'to save time' is not a reason" restored; REVIEW's "Do not report" additions listed; the `cargo fetch` step added to the Evidence log; the protected-path wording ("the paths listed in"); experiment evidence kept; "other disguised cheats are left to review".
- **Nit left for the backlog:** `guard.py` and `guard_base.py` line 2 cite "the deterministic gates of BUILD-PROCEDURE.md", which now live in `AGENTS.md`. Those files must stay identical across repositories and are out of Scope.

## 4. Verify

- [x] Links and anchors in every tracked Markdown file outside dated records (checker in the session scratchpad; GitHub heading slugs and HTML `id`s): `47 links checked, 0 unresolved`. **Pass**.
- [x] `§N` and `AGENTS.md > <heading>` citations (`git grep` outside `docs/build-records`): each `§2`, `§3`, `§5`, `§6` points at the section that holds it; every cited heading exists. **Pass**.
- [x] `git diff --check`: exit 0. **Pass**.
- [x] `python3 scripts/quality/guard_policy.py --check`: exit 0. **Pass**.
- [x] Guard tests inside `safe-run.sh`: `Ran 91 tests`, OK. Quality tests inside `safe-run.sh`: `Ran 80 tests`, OK (skipped=1). **Pass**.
- [x] Verifier pass 1: `VERDICT: FAIL` (Important I1; dispositions in Debug). Its gate: `git diff --check` exit 0; `guard_policy.py --check` exit 0; guard tests `Ran 91 tests`, OK; quality tests `Ran 80 tests`, OK (skipped=1); links 47/0; Release Gate block identical (diff exit 0). Its lnd start-time read was refused by the sandbox (Docker socket): Not yet proven, as `safe-run.sh` says inside the sandbox. **Fail, repaired.**
- [x] Verifier follow-up (the one allowed): `VERDICT: PASS`, no Important finding open. I1 and the seven nits corrected; gate rerun: `git diff --check` exit 0, `guard_policy.py --check` exit 0, guard tests `Ran 91 tests`, OK, links 47/0. No new nits. **Pass.**
- [ ] CI on the PR: Not yet proven until a run is observed.

## 5. Close Out

- [x] Scrap sweep: the tracked changes are the files in Scope. The mutation trial's scratch output is removed. Its cargo cache, `.cargo-home/` (86 MB, gitignored), stays in the worktree: `rm` was refused by the sandbox ("Read-only file system"), so it is the owner's to remove.
- [x] Repair cycles: 1 of 2. Review rounds: 2 of 2.
- [ ] Committed, pushed, PR opened:

## Results and limitations

### Owner notes

- The global rule for a new Full-tier repository says to copy BUILD-PROCEDURE.md "from rikurinode". This copy is now node-specific; the previous repository's copy is still the portable one.
- `CLAUDE.md` calls `AGENTS.md` "this repository's Bounded Agent Operating Standard"; the file's title is now "Agent Rules". Left as it is (out of Scope); the substance of the standard is kept.

### Backlog (not started)

- `guard.py` and `guard_base.py` line 2 cite "the deterministic gates of BUILD-PROCEDURE.md"; they now live in `AGENTS.md`. A cross-repository change, since the files are identical everywhere.
- The `cargo mutants` trial found five surviving mutants in B0.1's code (Evidence log).

## Evidence log

```
cargo-mutants trial (verifier step 5 settings), on B0.1's Rust diff (9f94898):
  scripts/cargo.sh fetch --locked --manifest-path control-plane/Cargo.toml   (needed: the run is --offline)
    ... Downloaded tokio v1.53.2 ... (exit 0)
  git diff --relative=control-plane 9f94898^ 9f94898 > <scratch>/b01.diff
  scripts/quality/safe-run.sh scripts/cargo.sh mutants --manifest-path control-plane/Cargo.toml \
    --in-diff <scratch>/b01.diff --test-workspace=true --timeout 600 --output <scratch>/out \
    --cargo-arg=--offline --cargo-arg=--locked
  Found 17 mutants to test ... 17 mutants tested in 21s: 5 missed, 7 caught, 5 unviable
  toolchain used: /home/junc/.rustup/toolchains/1.98.1-x86_64-unknown-linux-gnu/bin/cargo
  unviable: five `Default::default()` replacements for types without Default (genuine)
  the same command with a diff from the repository root: "No mutants to filter"
  missed (B0.1's own, reported here, not pursued): status.rs:95 unix_now -> Some(1);
    status.rs:117 uptime -> Default; main.rs:17 main -> Default; main.rs:31 init_logging -> ();
    main.rs:49 run -> Ok(())
```
