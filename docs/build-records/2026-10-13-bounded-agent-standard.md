# Build Record — Adopt the Bounded Agent Operating Standard in the node repository

| | |
|---|---|
| **Date** | 2026-10-13 |
| **Author / session** | Claude Code (Opus 5.5) for Henry Chen, in the worktree `/home/junc/claude-wip/bounded-agents/rn` |
| **Branch** | `docs/bounded-agent-standard`, from `main` `a064741` |
| **Commits** | 594335a on `docs/bounded-agent-standard` (the whole change and this record); a second commit records CI on PR #9 |
| **Status** | COMPLETE — verifier rounds FAIL, FAIL, then PASS in the third, narrow round the owner authorized; three nits for the owner (Skipped items). CI green on pull request #9 at 594335a: "Full gate (Ubuntu)" (CI run 38518343922, 1m 47s) and the guard tests on Python 3.9 and 3.12 (run 38518343919, 58s). Awaiting the owner's review and merge |
| **Change type** | ops (agent rules and the documents that cite them; no code) |

**Risk note (protected paths):** `AGENTS.md`, `CLAUDE.md`, `REVIEW.md`,
`.claude/agents/verifier.md`, `.agents/workflows/BUILD-PROCEDURE.md` and
`.agents/workflows/BUILD-CHECKLIST-TEMPLATE.md` are protected paths
(`PROTECTED_GLOBS` in `scripts/quality/guard_policy.py`), and so, after
the owner's amendment, are `scripts/quality/guard_policy.py` and
`scripts/quality/tests/test_guard_claims.py` (`scripts/quality/*`; the
test file also matches `test_globs`). In the `development` profile each
edit is a logged allow. No guard, settings, hook or CI file changes; the
policy source and the claims test change in comments and the test's
docstring only (their code is AST-identical to main's), and
`guard-config.json` is byte-identical, so no guard verdict changes. The
behaviour that changes is the agents' procedure: the fix-lock becomes
opt-in (owner, 2026-10-13), and repair cycles and review rounds get a
limit.

## Task Contract (the owner's handoff, 2026-10-13, verbatim)

1. **Outcome:** the node repo's agents follow the Bounded Agent Operating
   Standard without losing a node rule, and every file that cites or
   implements AGENTS.md agrees with it.
2. **Scope:** `AGENTS.md`, `CLAUDE.md`, `REVIEW.md`,
   `.claude/agents/verifier.md`, `.agents/workflows/BUILD-PROCEDURE.md` (a
   dated addendum, additions only),
   `.agents/workflows/BUILD-CHECKLIST-TEMPLATE.md` (the fix-lock box only),
   and this Build Record. **Not included:** `guard.py`, `guard_base.py`,
   `test_guard.py` (frozen, shared), `guard_policy.py` and
   `guard-config.json` (headings are kept, so `_doc` stays true),
   `.claude/settings.json`, CI, the main folder's working copy, Rikuri-PI.
3. **Done when:** every link and `AGENTS.md > <heading>` citation in the
   repo resolves (the 10 citing files checked, unchanged); `git diff
   --check` clean; guard tests pass inside `scripts/quality/safe-run.sh`;
   one verifier pass with no Important finding; one PR open with `Full gate
   (Ubuntu)` observed green.
4. **Authority:** edit the files in Scope inside the worktree; commit; push
   the branch; open one PR. No merge, no settings, guard, policy or CI
   change.
5. **Limits:** two repair cycles; one verifier pass plus at most one
   follow-up.

**Owner amendment (2026-10-13, after this session started).** Relayed by
the session that wrote the handoff (rikuri-pi-b8) and written into the
handoff's "Owner amendment" section; confirmed by the owner in this
session before any change ("Yes, apply the split"). Split the guard and
sandbox detail out of AGENTS.md: a short `Deterministic gates` section
under the same heading (so every `AGENTS.md > Deterministic gates`
citation, including `guard-config.json`'s `_doc`, still resolves); the
rest verbatim in `docs/guard-and-sandbox.md`; the citations that mean the
detail repointed — `scripts/quality/tests/test_guard_claims.py`
(docstring and comments only) and `scripts/quality/guard_policy.py`
(comments near lines 391 and 405 only). No rule, pattern, example or test
change; `guard-config.json` byte-identical. **Scope widens** by
`docs/guard-and-sandbox.md` and those comment lines; the limits are
unchanged. The owner's reason (the handoff): the form-by-form prose feeds
a review loop, each wording finding adding prose, tests and claims.

## 0. Intent — the owner's words, approved before design

- [x] Problem: the owner's draft AGENTS.md (the Bounded Agent Operating
      Standard, `/home/junc/claude-wip/bounded-agents/AGENTS.owner-draft.md`,
      sha256 `77e811b440bd10c4dcb4957ca897b830e0e550d09ab0a2852203186ff13821ca`,
      checked) is Rikuri-PI's text. Adopted as is, it links a `doc/` folder
      this repository does not have, drops every node rule, and orphans the
      section citations in ten files. BUILD-PROCEDURE.md's fix-lock and
      "stop the line" read as unbounded repair against it.
- [x] Outcome: the Task Contract's Outcome, above.
- [x] Who/what it affects: every agent session in this repository (Claude
      Code imports AGENTS.md through `CLAUDE.md`); the verifier subagent;
      reviewers. No node, funds, runtime or code.
- [x] Open questions: none. The owner's decisions (2026-10-13) are final:
      **AGENTS.md is the node version** (the draft's bounded rules §1–§6,
      §9 and the final rule word for word where general; Rikuri Pi's
      references swapped for the node's; the node sections back under
      their existing heading text in place of the draft's §7–§8); **the
      fix-lock is opt-in**, like Rikuri-PI, off by default while no node
      code touches keys or funds, with evidence standing in, and the
      default again before the first code that talks to LND or bitcoind or
      handles keys, seeds or macaroons.
- [x] Owner approved the intent: the handoff's "Owner decisions
      (2026-10-13)" and the session prompt ("The owner's decisions there
      are final").

## 0b. Spec

- [x] Requirements: the handoff's "Plan, file by file", applied to the
      seven files in Scope.
- [x] Design: AGENTS.md keeps the draft's numbering §1–§9 so that §1, §4,
      §5.C, §5.D and §9 mean the same thing here and in Rikuri-PI (and the
      session prompt's "AGENTS.md §9" stays true). The node's seven
      sections sit under one §7, "Preserve Rikuri Node's non-negotiable
      rules" (the draft's §7 title, the node's name), each as a level-3
      heading whose text is unchanged, so every `AGENTS.md > <heading>`
      citation still names a heading that exists. §8 is "Stage
      guardrails". Rejected: numbering the seven sections 7–13, which
      would move the end-of-task report to §15 while the handoff and the
      prompt call it §9.
- [x] Policy applied: the fix-lock default is a behaviour-changing default;
      the owner chose it (2026-10-13), and AGENTS.md states its cost
      (evidence instead of a lock) and its reversal condition. Main's
      Deterministic gates text stays byte for byte except the fix-lock
      bullet, because `test_guard_claims.py` holds the forms it lists
      (after the owner's amendment: byte for byte in
      `docs/guard-and-sandbox.md`, with a short form left in AGENTS.md).
- [x] Flagged concerns: three additions beyond the handoff's literal
      wording, each to keep a node rule (the Outcome): main's "Stage only
      your own change; never commit another session's work" (§2), "Ask
      the owner about conflicts, design decisions and security; otherwise
      proceed" (§3), and the draft's general fix-lock sentences kept
      beside the owner's opt-in rule (§4). Listed again at Verify.

## 1. Plan

- [x] One sentence: AGENTS.md becomes the node's Bounded Agent Operating
      Standard, and CLAUDE.md, REVIEW.md, the verifier, BUILD-PROCEDURE.md
      (an addendum) and the template's fix-lock box agree with it.
- [x] Blast radius: agent procedure only. No code, guard, settings, CI,
      funds, auth or exec path. Reversible by reverting the commit.
- [x] Current behavior characterized: `CLAUDE.md` imports `AGENTS.md`
      (`@AGENTS.md`). `git grep` finds the `AGENTS.md > <heading>`
      citations in the ten files the handoff names (README.md, REVIEW.md,
      `.gitignore`, `.claude/agents/verifier.md`,
      `.claude/hooks/guard-config.json` `_doc`,
      `scripts/quality/guard_policy.py`, `scripts/quality/full-gate.sh`,
      `scripts/quality/safe-run.sh`,
      `scripts/quality/tests/test_guard_claims.py`,
      `docs/architecture/platform-plan.md`) and one in
      `docs/build-records/2026-10-12-stage1-os-image.md`. The headings they
      name: Deterministic gates, Never in git, Testing on this machine,
      Verification by maturity, Design rules, Security baseline, Standard
      work (REVIEW.md only). No `AGENTS.md#` anchor link exists. Guard:
      `profile: development`; `fix-lock not engaged`;
      `fix_lock_release_needs_owner` unset in `guard-config.json` (default
      true). Worktree clean at `a064741`; the untracked dotfiles `git
      status` lists are the sandbox's `/dev/null` placeholders.
- [x] Files, in order: this record; AGENTS.md; CLAUDE.md; REVIEW.md;
      `.claude/agents/verifier.md`; BUILD-PROCEDURE.md (addendum);
      BUILD-CHECKLIST-TEMPLATE.md (lines 49–51).
- [x] Riskiest step: AGENTS.md's Deterministic gates section, which the
      guard-claim tests and the wiring check describe; it must move
      without a changed byte except the one bullet the handoff names.
- [x] I will know this works when: a link and citation check over the repo
      reports every link and `AGENTS.md > <heading>` citation resolving;
      a diff of main's node sections against their new copy shows only
      the fix-lock bullet and the heading level changed; `git diff
      --check` is clean; the guard tests pass inside `safe-run.sh`; the
      one verifier pass has no Important finding; CI's `Full gate
      (Ubuntu)` is observed green on the PR.
- [x] Amended by the owner's amendment (above): add
      `docs/guard-and-sandbox.md` and the comment lines in
      `guard_policy.py` and `test_guard_claims.py` to the files. The
      Deterministic gates detail now moves to the reference rather than
      staying in AGENTS.md, so the acceptance checks become: the reference,
      without its added headings, equals main's lines byte for byte; the
      rest of main's node sections differ only by heading level and the
      fix-lock bullet; `guard-config.json` byte-identical; the two scripts
      changed in comments and the docstring only; and the follow-up
      verifier pass has no Important finding.

## 2. Build

- [x] AGENTS.md: assembled by a script (scratchpad `assemble.py`, not
      committed) from main's AGENTS.md (`git show a064741:AGENTS.md`) and
      the owner's draft, each replacement asserted to match exactly once,
      so everything else is copied, not retyped. Title "Rikuri Node —
      Bounded Agent Operating Standard". Top: main's banner verbatim;
      main's product paragraph with `Status: see [README.md](README.md).`;
      Priorities and "Evidence decides" verbatim; the draft's Purpose line
      (Rikuri Node; the platform plan, the ADRs, BUILD-PROCEDURE, the
      security baseline (§7), CI). §1 verbatim plus one sentence: the Task
      Contract sits at the top of the Build Record made from the template.
      §2 verbatim except the documentation-index bullet (README, the
      platform plan, only the relevant ADR, lessons-register and Build
      Record parts), plus main's "Stage only your own change; never commit
      another session's work" and "Changes land on `main` by pull request;
      the `Full gate (Ubuntu)` check must pass". §3: the node table
      (BUILD-PROCEDURE with its addendum, the template and record path, the
      platform plan, `docs/adr/`, the lessons register, REVIEW.md); the
      previous repository is a source of lessons and proven parts, not an
      authority; the material-conflict paragraph verbatim; main's
      behaviour-changing-default rule with "Ask the owner about conflicts,
      design decisions and security; otherwise proceed". §4 verbatim except
      "Claude guard and fix-lock": the guard and the sandbox are described
      under Deterministic gates (§7); the draft's sentence "this document
      cannot grant permissions or change hook behavior" kept; the owner's
      opt-in fix-lock rule (red commit or recorded red run, fix in its own
      commit, a reason for every test or baseline change from red to head,
      the verifier checks it, a session may engage the lock, release needs
      the owner, the default again before code that talks to LND or
      bitcoind or handles keys, seeds or macaroons); then the draft's
      second fix-lock paragraph verbatim (general and bounded). Release
      wording adds "ask in the conversation and wait for a clear yes: in
      the `development` profile the guard only logs `fix-lock off`" —
      checked in `guard.py` lines 1698–1703: a session's own release is an
      ask that is not kept, so the `development` profile relaxes it. §5
      verbatim except: A's record path → the template and
      `docs/build-records/`; B adds `safe-run.sh`; D names
      `scripts/quality/full-gate.sh`, "BUILD-PROCEDURE and the platform
      plan", and b7b2ef6's REVIEW.md / verifier sentence; E's "Stage Gate
      Records, requirements, traceability" → "the platform plan, the
      lessons register, … help pages" (Rikuri Pi's references swapped for
      the node's). §6 verbatim plus: never against the live node; the
      sandbox is the boundary. §7 "Preserve Rikuri Node's non-negotiable
      rules": main's seven sections, one heading level down, text
      unchanged except the fix-lock bullet in Deterministic gates, now a
      pointer to §4 (then shortened by the owner's amendment: see
      "Repair cycle 1" below). §8 "Stage guardrails": stage 1 and B0; later stages
      (2 to 8) not pulled in; the release gate; task done is not stage
      done. §9 and the final rule verbatim.
- [x] CLAUDE.md: "agent standard work" → "Bounded Agent Operating
      Standard"; `@AGENTS.md` kept.
- [x] REVIEW.md: the header says this is the review pass §5.D requires
      (one pass, at most one follow-up, a third round ends
      `NEEDS_OWNER_DECISION`), replacing its pointer to main's former
      "Standard work" section; the judgement stays "Design rules" and "Security
      baseline"; Compliance checks the Task Contract's Scope (§1); a review
      starts no work, findings outside the task go to the backlog or the
      owner (§5.C), the independent reviewer never fixes.
- [x] `.claude/agents/verifier.md`: the one pass §5.D allows or its single
      follow-up; reads the Task Contract and Plan first; the gate by change
      type (implementation: `full-gate.sh` once, again only after a
      gate-affecting repair; documentation-only: links and citations, `git
      diff --check`, guard tests inside `safe-run.sh`, changed JSON, CI's
      full gate on the PR); the diff against the Task Contract's Scope;
      step 5, the defect-fix check that stands in for the opt-in lock;
      "Report once…". The live-node rules are unchanged, word for word.
- [x] BUILD-PROCEDURE.md: additions only (+66 −0): a pointer under the
      introduction and "Addendum 2026-10-13 — bounded agent operation,
      Rikuri Node" at the end: which governs what; Law 2 with bounded
      repair; the full gate at the acceptance boundary; standard work in
      the brief form; fix the class within the task; stale state
      dispositioned by the owner; periodic loops as owner obligations; the
      fix-lock opt-in until its reactivation condition. **This copy now
      differs from the other Full-tier repositories' BUILD-PROCEDURE.md by
      this addendum and its pointer** (BUILD-PROCEDURE.md is not one of the
      three guard files that must stay identical).
- [x] BUILD-CHECKLIST-TEMPLATE.md: lines 49–51 only, the handoff's text.
      Like BUILD-PROCEDURE.md, this copy now differs from main's and (not
      checked) from the other repositories' templates.
- [x] The owner's amendment (repair cycle 1, with the verifier's
      corrections; scratchpad `split.py`, not committed):
      - AGENTS.md > Deterministic gates keeps a short form: the sandbox is
        the boundary; the guard is a tripwire on command text, not a
        boundary, and what always asks (money and key-exposing commands,
        node and container tools, the previous checkout, the pre-commit
        hook's bypasses and files); a deny means stop and ask; the §4
        fix-lock pointer; the one gate and the hook install, unchanged; a
        link to the reference. §4 also points to the reference; §7's
        intro says the headings, not the bodies, stay as they are.
      - `docs/guard-and-sandbox.md` (new): main's AGENTS.md lines 47–274
        (the sandbox and its drill, the guard and its closed-world node
        and container reads, the previous checkout, the pre-commit hook's
        forms, "Held by tests", "What gets through the guard") byte for
        byte, under six headings added for navigation, with a short
        introduction.
      - `scripts/quality/guard_policy.py`: the two comments near lines 391
        and 405 now name `docs/guard-and-sandbox.md`. The module docstring
        ("AGENTS.md > Deterministic gates": the tripwire, not a sandbox)
        and the generated `DOC` stay true and unchanged.
      - `scripts/quality/tests/test_guard_claims.py`, test code changed
        for this reason: its docstring and three comments named AGENTS.md
        as the list of forms and path spellings the test holds; that list
        now lives in `docs/guard-and-sandbox.md`, so they name it. No
        case, form, assertion or expected verdict changes (the module's
        AST, docstring aside, is identical to main's). The comment at line
        115, "round 10's verifier: listed in AGENTS.md, held by no test",
        is history and stays.
- [x] New code meets the bar: N/A, no code.
- [x] Security question: no auth, money, exec or private-data path. The
      rules that guard them (the live-node banner, the sandbox, the
      guard's asks, Security baseline) move unchanged.

## 3. Debug

N/A: not a defect fix.

## 4. Verify

Documentation-only change: the checks AGENTS.md §5.D names, on the working
tree at `a064741` plus these edits. No full gate locally; CI's `Full gate
(Ubuntu)` runs it on the pull request.

**Round 1, before the amendment** (these results stand for that tree; the
verifier's pass reproduced every one but the link check, see below):

- [x] Link and citation check (scratchpad `linkcheck.py`, not committed;
      every tracked file plus this record): 41 local Markdown links (with
      `#anchor`s, GitHub slugs and HTML `id`s), 13 `AGENTS.md > <heading>`
      citations (README.md, REVIEW.md, `.gitignore`, verifier.md,
      `guard-config.json`, `guard_policy.py` twice, `full-gate.sh`,
      `safe-run.sh`, `test_guard_claims.py`, `platform-plan.md`,
      `2026-10-12-stage1-os-image.md`; wrapped comment lines joined) and 17
      `§` citations in the six changed rule files: 0 problems, exit 0,
      **Pass**. Negative control: in a scratch copy, a renamed heading
      ("Never in Git"), a broken link and `§5.F` gave 4 problems, exit 1,
      so the check can fail. Of the ten citing files, only REVIEW.md and
      verifier.md changed (both in Scope); the other eight are unchanged.
- [x] Node sections unchanged: `diff` of main's lines 45–368 against the
      new §7 shows only the seven heading levels (`##` → `###`) and the
      fix-lock bullet, **Pass**.
- [x] `git diff --check`: exit 0, **Pass**. BUILD-PROCEDURE.md `+66 −0`;
      the template's only hunk is `@@ -49,3 +49,3 @@`.
- [x] Guard tests inside `safe-run.sh`: `scripts/quality/safe-run.sh
      python3 -m unittest discover -s .claude/hooks -p 'test_*.py'` → `Ran
      91 tests … OK`, exit 0; the quality tools' tests (guard claims,
      baseline, policy, wiring, hygiene, safe-run) → `Ran 80 tests … OK
      (skipped=1)`, exit 0 (skipped: one wiring subtest, "root reads a
      mode-000 file", because the namespace runs as root; CI runs it);
      `check_guard_wiring.py`, `guard_policy.py --check` and
      `repo_hygiene.py .` exit 0. Python 3.14.4. Afterwards `guard.py
      profile` → `development`, `fix-lock status` → `not engaged`
      (unchanged). **Pass**.
- [x] Independent verification, pass 1 (`verifier` subagent):
      **`VERDICT: FAIL`** on one Important finding. Checks 1–3, 5 and 6
      Pass: Scope, no node rule lost (main's Standard work rules each
      placed; node sections differ only by heading level and the fix-lock
      bullet), the draft's text word for word where general with every
      deviation named or listed, the gate (91 OK; 80 OK, one skip; wiring,
      policy, hygiene exit 0; profile and lock unchanged), no
      contradiction among the five documents; and §4's claim about
      `fix-lock off` exercised through `guard.decide()` (`development`:
      own release allowed and logged, `--global` asks; `stable`: both
      ask). Its mutations (two renamed headings, a broken link, `§5.F`)
      were each caught. **I1 (Important)**: this record's link-check
      claim did not reproduce — the record, edited after the check, had a
      relative `README.md` link that resolves to
      `docs/build-records/README.md` and quoted REVIEW.md's replaced
      citation of the former "Standard work" heading; `linkcheck.py` rerun: 2 problems, exit
      1. Nits: CLAUDE.md line 4 unwrapped; §7's intro could read as
      freezing the section bodies; the template has no Task Contract slot
      (backlog); this Evidence log empty; verifier.md's
      documentation-only list called "the whole local gate (§5.D)" while
      adding to it and leaving out its version check.
- [x] **Repair cycle 1 of 2**, one coherent group: I1 (the link now inline
      code, the quote reworded), nits 1, 2, 4 and 5 corrected, nit 3 to
      the backlog, and the owner's amendment applied (Build, above).
- [x] Round 2 checks, on the amended tree:
      - Links and citations: 45 local links, 15 `AGENTS.md > <heading>`
        citations (12 in other files — `test_guard_claims.py`'s now names
        the reference — and 3 in this record), 17 `§` citations (the
        seven rule files, now with `docs/guard-and-sandbox.md`): 0
        problems, exit 0, **Pass**, rerun after this record's last edit.
      - `git diff --check`: exit 0, **Pass**.
      - `guard-config.json` byte-identical to `a064741` (`git diff
        --quiet`, exit 0), **Pass**.
      - `guard_policy.py` and `test_guard_claims.py`: the AST, module
        docstring aside, equal to `a064741`'s, so only comments and the
        docstring changed, **Pass**.
      - `docs/guard-and-sandbox.md` without its six added headings equals
        main's AGENTS.md lines 47–274 byte for byte, **Pass**.
      - Inside `safe-run.sh`: guard tests `Ran 91 tests … OK`, exit 0;
        quality tests `Ran 80 tests … OK (skipped=1)`, exit 0, the same
        skip; `check_guard_wiring.py`, `guard_policy.py --check`,
        `repo_hygiene.py .` exit 0. Profile `development`, fix-lock not
        engaged. **Pass**.
- [x] Independent verification, the one follow-up pass on the corrections
      and the amendment (`verifier` subagent): **`VERDICT: FAIL`** on one
      Important finding. Pass: the reference equals main's lines 47–274
      byte for byte (16089 bytes); `guard_policy.py` and
      `test_guard_claims.py` changed in comments and the test's docstring
      only (identical non-comment token streams, docstring aside);
      `guard-config.json` byte-identical; every link and citation
      resolves (checked by hand too); Scope is exactly the widened set;
      the gate (91 OK; 80 OK, one skip; wiring, policy, hygiene exit 0;
      profile and lock unchanged); the record's round-2 numbers
      reproduce; every pass-1 correction holds. **I2 (Important)**: the
      new short Deterministic gates said the guard always asks before
      "writes to [the pre-commit hook's] files", while in `development`
      file-tool edits of them are logged allows — `guard.decide()`:
      `development` Edit/Write of `scripts/quality/hooks/pre-commit` and
      `.git/hooks/pre-commit` → allow, logged; `stable` → ask — as the
      reference itself says. Nits: "the owner's private paths" (the
      reference: fourteen, the rest of the home folder readable); the
      wiring check "exactly as committed" (it accepts a timeout of 1–10 s
      and does not read user settings); "except reads and copies out of
      it" loose, and the parent folder omitted; this record's risk note
      stale after the amendment; the scratchpad checker's blind spots
      (prefix matching of citations, the reference's linked-form
      citation not checked, `§` checks only with `CHECK_SECTIONS` set).
- [x] **Repair cycle 2 of 2** (the last): I2 — the short form now says
      the guard always asks before git's bypasses of the hook "and the
      commands the reference lists that write, move or delete the hook's
      files", and that file-tool edits of them are protected-path writes
      (ask in `stable`, logged in `development`); nits 1–4 corrected in
      AGENTS.md and the risk note above; nit 5 recorded here (the
      verifier checked every citation by hand, so the results stand).
- [x] Round 3 checks, after cycle 2: links and citations 45 / 15 / 17
      (`CHECK_SECTIONS` set to the seven rule files), 0 problems, exit 0;
      `git diff --check` exit 0; `guard-config.json` unchanged; the
      reference byte-identical to main's lines 47–274 (`cmp`, exit 0);
      inside `safe-run.sh` guard tests `Ran 91 tests … OK` and quality
      tests `Ran 80 tests … OK (skipped=1)`, exit 0; wiring, policy and
      hygiene exit 0; profile `development`, fix-lock not engaged.
      **Pass**. No independent review of cycle 2: both review rounds are
      used, and a third is the owner's decision (REVIEW.md).
- [x] Third review round, **authorized by the owner** in this session
      (2026-10-13, "Narrow 3rd pass, then PR"): one verifier pass limited
      to the cycle-2 edits; if it finds anything, stop with nothing pushed
      (no repair budget left): **`VERDICT: PASS`**, no Important finding.
      I2 and nits 1–4 resolved, checked with `guard.decide()` in both
      profiles: the command forms the reference lists on the hook's files
      and git's bypasses ask in `development`; file-tool edits of
      `scripts/quality/hooks/pre-commit`, `.git/hooks/pre-commit` and
      `.git/config` are logged allows in `development` and asks in
      `stable`. Since the follow-up pass only the two cycle-2 hunks of
      AGENTS.md changed, and in this record only the risk note, Verify,
      the backlog and the Evidence log. The mechanical checks and the gate
      reproduce (91 OK; 80 OK, one skip; wiring, policy, hygiene exit 0);
      its own link checker's negative control fails as it should. Three
      nits, not fixed (no repair budget left) and listed under Skipped
      items: `.git/config.worktree`, and the shared `.git` seen from a
      linked worktree, are not protected paths, so "file-tool edits of the
      hook's files … ask in `stable`" does not hold for them (main's
      reference text says the same); "with the keys, rules, modes and
      variables it lists" reads wider than the wiring check, which refuses
      allow rules for six tools only; the risk note does not say the moved
      detail is now outside the protected set. "Finds anything" is read as
      the Contract's bar, an Important finding: the verdict is PASS, so
      the change goes to a pull request, and the owner can close it if
      the nits should have stopped it.
- [x] Diff matches the §1 plan; deviations explained: ten files, the
      Plan's seven plus the amendment's `docs/guard-and-sandbox.md`,
      `guard_policy.py` and `test_guard_claims.py`; nothing else tracked
      changed. Deviation: the Plan's "one verifier pass has no Important
      finding" took three rounds — FAIL, FAIL, then PASS in the round the
      owner authorized.

## 5. Close Out

- [x] Full gate: CI's `Full gate (Ubuntu)` on the PR: seen green on pull
      request #9 (opened by this session, 2026-10-13), commit 594335a —
      "Full gate (Ubuntu)" succeeded (CI run 38518343922, "CI #26", job
      115702117824, 1m 47s), and the guard and quality-tool tests on
      Python 3.9 and 3.12 (run 38518343919, 58s; two warnings, both the
      runner's Node.js 20 deprecation notice for `actions/setup-python`),
      read from GitHub's pages in the owner's browser. **Pass**.
- [x] Scrap Sweep: task-scoped. The task created this record and
      `docs/guard-and-sandbox.md`, both kept. Its scratch (assembly and
      check scripts, test outputs, the commit message) is in the
      session's scratchpad outside the repository, and the third pass's in
      `/tmp/claude-1000/r3verify.S7AXLA/`; that pass reports it first
      wrote its copies of the old files into another session's
      `/tmp/claude-1000/v3` by mistake and moved them out at once. The
      untracked entries `git status` lists are the sandbox's `/dev/null`
      placeholders, not the task's. **Pass**.
- [x] Reviewed per `REVIEW.md`: three verifier rounds (FAIL, FAIL, PASS),
      the third authorized by the owner; every Important finding fixed,
      the remaining nits listed below.
- [x] Knowledge layer: the documents in Scope are the knowledge layer for
      this change; no help page or runbook exists.
- [x] Commit message explains WHY; record committed with the change

## Skipped items — visible, never silent

Backlog and owner items surfaced by this task, none started:

- The template has no Task Contract slot; AGENTS.md §1 says the Contract
  sits at the top of the Build Record (verifier nit 3). The template is out
  of Scope beyond lines 49–51. Owner: Henry.
- Nothing mechanical turns the fix-lock back on: its reactivation
  condition ("before the first code that talks to LND or bitcoind…")
  likely arrives with B0.3 (`control-plane/crates/rikuri-control/src/lib.rs`
  lines 6–7: interfaces to systemd, Podman, LND and bitcoind come with
  B0.3). The owner decides when; the guard is unchanged. Owner: Henry.
- §2 forbids a frozen inventory in AGENTS.md, while §7 keeps main's status
  text (Verification by maturity, the sandbox drill's evidence, now in the
  reference). Kept by the owner's decision; noted. Owner: Henry.
- `test_guard_claims.py` line 115 and
  `docs/build-records/evidence/2026-10-10-bootstrap/mut_r11.py` line 2
  still say AGENTS.md about the forms: history, left as written.
- README's "How the work is done" does not list `docs/guard-and-sandbox.md`
  (README is out of Scope). Owner: Henry.
- The guard and sandbox detail no longer reaches a session at start
  (`CLAUDE.md` imports only AGENTS.md): the owner's choice in the
  amendment; AGENTS.md links it.
- From the third pass (nits, not fixed: no repair budget left):
  `.git/config.worktree`, and the shared `.git/config` and
  `.git/hooks/pre-commit` seen from a linked worktree, are not protected
  paths, so file-tool edits of them are allowed and not logged in either
  profile, while the reference (main's text) and the short form say
  file-tool edits of the hook's files ask in `stable`. Protect them (a
  guard-policy change, with guard tests) or reword both. Owner: Henry.
- From the third pass: the short form's "with the keys, rules, modes and
  variables it lists" reads as closed-world for permission rules; the
  wiring check refuses allow rules for six tools only (`"allow":
  ["Bash(*)"]` passes). The reference's wording is exact. Owner: Henry.
- From the third pass: `docs/guard-and-sandbox.md` is not a protected
  path (an edit is allowed and not logged in either profile), where the
  same text in AGENTS.md was; no test reads it. Whether it joins
  `PROTECTED_GLOBS` is a guard-policy change. Owner: Henry.
- From the third pass, main's text, older than this task: the sandbox
  bullet's "writes only inside this repository and the temporary folder"
  omits the other writable paths this session's sandbox lists
  (`~/.npm/_logs`, `~/.claude/debug`, the main checkout's `.git`); and
  the settings' edit deny for the previous checkout covers the checkout,
  not the parent folder the reference names. Owner: Henry.

## Evidence log

```
base:                      a064741 (main), branch docs/bounded-agent-standard
draft sha256:              77e811b440bd10c4dcb4957ca897b830e0e550d09ab0a2852203186ff13821ca (matches the handoff)
guard state:               profile: development / fix-lock not engaged (before, between and after every run)
round 1
  links/citations:         41 links, 13 heading citations, 17 § citations: 0 problems (negative control: 4 problems, exit 1)
  node sections:           diff main 45-368 vs new §7: 7 heading levels + the fix-lock bullet only
  git diff --check:        exit 0; BUILD-PROCEDURE.md +66 -0; template hunk @@ -49,3 +49,3 @@
  guard tests (safe-run):  Ran 91 tests in 23.126s  OK  exit=0  Python 3.14.4
  quality tests (safe-run): Ran 80 tests in 14.168s  OK (skipped=1: root reads a mode-000 file)  exit=0
  wiring/policy/hygiene:   exit 0 / 0 / 0
verifier pass 1:           VERDICT: FAIL — I1, this record's link check (2 problems, exit 1); 5 nits
repair cycle 1:            I1 + nits 1, 2, 4, 5 + the owner's amendment
round 2
  links/citations:         45 links, 15 heading citations (12 elsewhere, 3 in this record), 17 § citations: 0 problems, exit 0
  git diff --check:        exit 0
  guard-config.json:       identical to a064741
  comment-only changes:    guard_policy.py, test_guard_claims.py AST (docstring aside) equal to a064741
  moved text:              docs/guard-and-sandbox.md minus headings == main AGENTS.md lines 47-274
  guard tests (safe-run):  Ran 91 tests in 23.700s  OK  exit=0
  quality tests (safe-run): Ran 80 tests in 14.914s  OK (skipped=1)  exit=0
  wiring/policy/hygiene:   exit 0 / 0 / 0
verifier follow-up pass:   VERDICT: FAIL — I2, the short form overclaimed what always asks for the hook's files; 5 nits
repair cycle 2 (last):     I2 + nits 1-4; nit 5 recorded
round 3
  links/citations:         45 links, 15 heading citations, 17 § citations: 0 problems, exit 0
  git diff --check:        exit 0
  guard-config.json:       identical to a064741
  moved text:              cmp with main AGENTS.md lines 47-274: exit 0
  guard tests (safe-run):  Ran 91 tests in 23.083s  OK  exit=0
  quality tests (safe-run): Ran 80 tests in 14.408s  OK (skipped=1)  exit=0
  wiring/policy/hygiene:   exit 0 / 0 / 0
  guard state:             profile: development / fix-lock not engaged
review rounds:             2 of 2 used; a third is the owner's decision
third pass (owner):        VERDICT: PASS — no Important finding; 3 nits (backlog); guard tests 91 OK, quality tests 80 OK (skipped=1), wiring/policy/hygiene exit 0; AGENTS.md, reference and record sha256 unchanged by the pass
PR #9 on 594335a:          CI run 38518343922 (Full gate (Ubuntu), 1m 47s) and run 38518343919 (guard tests, py3.9 and py3.12, 58s) completed successfully
```
