# Build Record — the README's status names the naming step as built

| | |
|---|---|
| **Date** | 2026-11-17 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/readme-naming-status`, from `main` at `e3b07a5`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `566248b` (contract), `3a426d7` (change) |
| **Status** | IN PROGRESS |
| **Change type** | documentation |

## Intent: the owner's words

- "Fix the README sentence" (2026-11-17), answering the note that README.md's status still says "Naming the node comes next", though the naming page's record (`docs/build-records/2026-11-13-5c4b2-naming-page.md`) is DONE.

## What is wrong

- README.md's status paragraph ends the SetupHub's description with "Naming the node comes next; the rest of setup is still to come." It was written in 5c.4a (`3e8cd5d`, 2026-11-11), before the naming work.
- 5c.4b-1 (the rename engine) and 5c.4b-2 (the page at `/name`) are DONE, and README's later paragraph already describes them; 5c.4b-2 updated that paragraph but not this sentence.
- The hub's steps today (`control-plane/crates/rikuri-control/src/hub.rs`, `STEPS`): connection, owner, name, then bitcoin, lightning and backup, which are always `later` ("Comes with a later update").

## Task Contract

1. **Outcome:** a reader of the README's status learns that the owner can name the node from the SetupHub today, and that Bitcoin, Lightning and backup come later.
2. **Scope:** routine; documentation only.
   - README.md: that one sentence, replaced by one saying that from the hub the owner names the node (the first of `rikuri01` to `rikuri99` nothing on the network answers, or a name of their own), and that its Bitcoin, Lightning and backup steps come with later updates.
   - **Not included:** any other README text; the runbook (already updated by 5c.4b-2); code; the platform plan.
3. **Done when:**
   - Link and citation checks: the sentence's claims match `hub.rs` and README's naming paragraph; `git diff --check` is clean.
   - CI's full gate passes on the PR.
   - No verifier pass: documentation only (AGENTS.md §5).
4. **Authority:** README.md and this record. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Change, `3a426d7`

- README.md: "Naming the node comes next; the rest of setup is still to come." becomes "From the hub the owner names the node: the first of `rikuri01` to `rikuri99` that nothing on the network answers, or a name of their own. Its Bitcoin, Lightning and backup steps come with later updates."
- **Citation checks, each against the tree at `e3b07a5`:**
  - the hub's steps: `control-plane/crates/rikuri-control/src/hub.rs`, `STEPS` (connection, owner, name, bitcoin, lightning, backup), and `tests/hub_route.rs` (bitcoin, lightning and backup `later`);
  - the suggestion's range and "nothing answers": README's own naming paragraph (`GET /api/node/name/suggestion`, 5c.4b-2);
  - "a name of their own": the page's words, `ui/src/i18n/en.json` `name.lead` ("Keep the suggestion, or choose your own") and `name.none_free`.
- No link added or changed; `git diff --check` is clean.
