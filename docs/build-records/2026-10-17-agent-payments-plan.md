# Build Record — Agent payments and marketplace plan

| | |
|---|---|
| **Date** | 2026-10-17 |
| **Author / session** | Claude Code (Fable 5.1), owner Henry Chen |
| **Branch** | `docs/agent-payments-plan` |
| **Commits** | `13bb618` (the change, on the owner's "Yes, commit and push", 2026-10-17); this record's update follows it; branch pushed to `origin/docs/agent-payments-plan` after that |
| **Status** | COMPLETE (committed and pushed; the pull request is the owner's to open) |
| **Change type** | feature (documentation only) |

## Task Contract

1. **Outcome:** the platform plan says how the node becomes a treasury for
   the owner's agents and a host of a marketplace, in which stages, behind
   which security layer, and which choices are the owner's.
2. **Scope:** a new plan document,
   `docs/architecture/agent-payments-and-marketplace-plan.md`, beside the
   platform plan; in `docs/architecture/platform-plan.md` one stage row for
   the treasury and agent payments, one for the marketplace, the order-of-work
   line and a pointer to the new document; a module-level harvest of the
   previous repository's `commerce-service` appended to
   `docs/requirements/lessons-register.md` as a new section, with one new gap
   row; this record. The security layer (AISecurity policy, OpenShell
   enforcement, Sentry as a research input) is a section of the new document,
   per the owner's message of 2026-10-17 ("along the way OR a separate
   dedicated plan"); splitting it out later is an owner choice recorded in
   the document. Tier: **routine** (documentation; no code, no control, no
   boundary changes). **Not included:** code, ADRs, any change to stages 1 to
   8's content, per-file port verdicts of the old commerce code, `AGENTS.md`,
   `README.md`.
3. **Done when:** every link and anchor in the changed Markdown files
   resolves (checker in the session scratchpad, as in
   `2026-10-14-trim-agent-rules.md`); `git diff --check` is clean; every
   behaviour-changing default in the new document appears as a costed,
   reversible owner choice with no decision recorded as taken; the facts
   table carries its check date and sources; one `verifier` pass with no
   Important finding open (the owner's contract asked for one although the
   procedure needs none for documentation).
4. **Authority:** edits under `docs/`; reads of the previous checkout by
   absolute path only (`git -C /home/junc/rikuri/rikurinode show|grep|ls-files`),
   of `/home/junc/Rikuri-PI` and `/home/junc/AISecurity` the same way; web
   reads of vendor documentation for the facts table; one branch,
   `docs/agent-payments-plan`; **no commit, push or pull request until the
   owner says so.** One verifier pass.
5. **Limits:** one task; at most two repair cycles and two review rounds.

## 0. Intent — the owner's words, approved before design

- [x] Problem (as the owner would say it): "The agent payment and lightning
  market place needs more concrete plan based on a clear future vision"; the
  old concept "is not complete and never tested"; "I think this thread gives
  a much more robust role for a bitcoin node. An easy to run node with
  revenue generation roadmap." (owner, 2026-10-17, referring to the ChatGPT
  thread "OpenShell Sentry Watch").
- [x] Outcome — what is true when this is done: a plan document places the
  treasury, agent payments and the marketplace after the stages that prove
  the node, states the security layer they sit behind, and lists the owner's
  decisions with costs.
- [x] Who/what it affects: planning documents only. No node behaviour.
- [x] Open questions (answered 2026-10-17 by the owner): (1) agent payment
  must work with or without the marketplace; the marketplace may be hosted by
  the nodes and joined by non-Rikuri nodes through an add-on; (2) owner-signed
  mandates, automatic within an allowance, the owner signing once to issue and
  once when an amount exceeds authority, renewable; (3) the pruned tier gets
  revenue features too, simpler if hardware demands it; (4) include the
  vision in the plan now, update before the stage starts; (5) the security
  layer is part of it, with AISecurity as the example and OpenShell and
  Sentry as the owner's running analysis.
- [x] Owner approved the intent: "Yes" to the Task Contract, conversation of
  2026-10-17, with the security-layer addition in the same message.

## 0b. Spec — requirements + design, policy applied up front

- [x] Requirements derived from the intent: the document must (a) separate
  identity, mandate and proof of payment; (b) keep one door to LND, in the
  control plane; (c) make the marketplace a separable service that is a
  client of the treasury; (d) state the security layer's three parts and what
  each is proven to do today; (e) place the work as stages after the node is
  proven, with drills; (f) put every default to the owner as a costed,
  reversible choice; (g) rest on facts checked today, with sources; (h) carry
  the old commerce code's behaviour into the lessons register at module level
  so the plan rests on what exists, with its evidence stated honestly.
- [x] Design: one document in the platform plan's shape (one page, facts,
  architecture, stages, owner decisions, sources). Alternatives rejected:
  editing the platform plan in place (it would double in size and mix proven
  stages with a vision); a separate security plan now (two documents to keep
  aligned before any of it exists; left as an owner choice); adding the
  commerce code's lessons as new numbered requirements (the register's
  requirements come from harvested build records with incidents behind them;
  the commerce code has none, so it gets a harvest section and a gap, not
  requirements).
- [x] Policy applied: every behaviour-changing default is an owner choice in
  §6 of the new document; AGENTS.md > Design rules and > Security baseline
  are cited where the design relies on them; claims about the old code are
  stated as what its source and tests show, never as proven behaviour.
- [x] Flagged concerns: the old BLUEPRINT marks commerce tracks "complete"
  with no build record covering its behaviour and no end-to-end payment
  evidence; the document
  says so and the gap row records what must be proven.

## 1. Plan

- [x] One sentence: write the agent-payments and marketplace plan, add two
  stage rows and the pointer to the platform plan, append the commerce
  harvest and a gap row to the lessons register.
- [x] Blast radius: three Markdown files under `docs/` plus this record. No
  code, no settings, no funds path.
- [x] Current behaviour characterized: platform plan stage table has stages
  1–8 and no agent, marketplace or treasury item; `git grep -c
  commerce-service docs/requirements/lessons-register.md` = 0; the old
  repository at 3bbbe392 holds `commerce-service/` (28,294 lines of Rust in
  `src/`, 10 integration test files with 53 `#[tokio::test]`/`#[test]`
  functions, 2 acceptance scripts) and no build record covering its
  behaviour; "AI Passport"
  appears in none of the owner's repositories.
- [x] Files and order: this record → the new plan document → platform plan
  rows and pointer → lessons register section and gap row → checks →
  verifier → close out.
- [x] Risks: overstating what the old code or OpenShell is proven to do
  (mitigated by the facts table and the register's Pass / Not yet proven
  wording); a stage placement the owner did not intend (stated as a choice).
- [x] Verification defined up front, "I will know this works when": link
  checker 0 unresolved; `git diff
  --check` exit 0; a read of §6 finds every default as an open choice; the
  verifier's compliance pass finds the diff inside this Scope.

## 2. Build

- [x] Documentation only: no code. Files written: the new plan (440 lines),
  stage rows 9 and 10, the order-of-work line and a pointer paragraph in the
  platform plan (+13/-1), gap G12 and §7 in the lessons register, this record.
- [x] Clean as you go: the link checker lives in the session scratchpad
  (`linkcheck.py`), not in the repository. Untracked files that appeared in
  the working tree during the session and were not created by this task are
  listed under Skipped items for the owner; none is added.
- [x] Security question: touches auth / money / exec / private data? No code
  does. The document describes a future funds boundary; every claim in it is
  labelled plan or Not yet proven, the old code's behaviour is stated as what
  its source and tests show, and the facts table carries sources and the
  check date.

## 3. Debug

N/A — no defect fixed.

## 4. Verify

- [x] Link and anchor check (scratchpad `linkcheck.py`, GitHub heading
  slugs and HTML `id`s, code blocks skipped): the four changed files
  `28 links checked, 0 unresolved`; every tracked Markdown file outside dated
  build records `52 links checked, 0 unresolved`. **Pass.**
- [x] `git diff --check`: exit 0. **Pass.**
- [x] Owner-choice read of §6: ten decisions E1 to E10, each with options,
  costs and a recommendation; the "Recommended" column records none as
  decided, and the stage rows cite them as open. **Pass.**
- [x] Verifier pass 1: `VERDICT: FAIL`. Its gate: links 28/0 and 52/0,
  `git diff --check` exit 0, numbers reproduced from the old checkout, guard
  tests `Ran 91 tests`, OK (extra). One Important finding, I1 (compliance,
  claims match evidence): plan §4.2 said the previous code "encrypted the
  cache at rest"; its `at_rest.rs` helper was never wired into the L402
  cache (the acceptance README lists at-rest encryption as not verified),
  and register §7 in the same change said so. **Fail, repaired** (repair
  cycle 1 of 2): §4.2 now says the previous code cached proofs as plain
  JSON and the encryption is a new requirement. Nits, all fixed in place:
  the blast-radius row cited a "reserve" the platform plan does not name
  (now: funds beyond the operating balance, like the seed and SCB, off the
  node); "already" claims about the control plane and stage 7 (now: "in the
  platform plan's design", "is planned to deliver", approval path per
  HEAL-07); the auction form was fixed outside §6 (now stage 10's choice);
  the identity-key fallback and the quiet expiry (now an option under E4,
  and expiry shown in the app and ledger); E2, E6, E9 and E10 markers in
  "In one page" and §4.6; "no build record" narrowed to "no build record
  covering its behaviour" in the plan, the register and this record; the
  template's "I will know this works when" phrase; the untracked files
  listed under Skipped items.
- [x] Verifier follow-up (the one allowed), corrections only: `VERDICT:
  PASS`. Gate rerun: links 28/0 and 52/0, `git diff --check` and `git diff
  main --check` exit 0, file set unchanged. I1 confirmed against the old
  source (`l402/client.rs` writes `l402_proofs.json` as plain JSON; nothing
  in `l402/` references `at_rest`); every nit confirmed fixed. One backlog
  nit it happened upon, the §0b "no build records" wording, fixed in place
  here. No new Important finding. **Pass.**
- [x] Diff matches the §1 plan: the four files named there and no other
  (`git diff main --stat`: `platform-plan.md` +13/-1, `lessons-register.md`
  +25/-1, two new files); the verifier's compliance pass confirmed the
  Scope.

## 5. Close Out

- [x] Documentation-only checks (AGENTS.md §5): links 28/0 and 52/0 after
  the corrections; `git diff --check` exit 0. CI's full gate runs on the pull
  request when the owner opens one; not run here (documentation only).
- [x] Scrap sweep: the link checker stays in the session scratchpad; no
  scratch file, draft or probe in the repository (`git status`: the four
  files of this change plus the pre-existing untracked items listed under
  Skipped items).
- [x] Reviewed per `REVIEW.md`: one verifier pass (`FAIL`, Important I1)
  and one follow-up (`PASS`); the Important finding fixed, the nits fixed in
  place, none skipped; repair cycles used: 1 of 2; review rounds: 2 of 2.
- [x] Knowledge layer: n/a (no user-visible behaviour).
- [x] Commit: on the owner's word ("Yes, commit and push", 2026-10-17):
  `13bb618` carries the four files; the pre-commit hook's secret scan
  reported "no leaks found"; this record's update is the next commit, and
  the branch is pushed with `git push -u origin docs/agent-payments-plan`
  as a command on its own. The pull request: the owner opens it from
  https://github.com/rikuripi/rikurinode/pull/new/docs/agent-payments-plan
  with the body at `~/claude-wip/agent-payments-plan/pr-body.md`. CI's full
  gate on the PR is **Not yet proven** until its run is observed.

## Skipped items — visible, never silent

- No box skipped. For the owner, not this task's to touch: `.codex/`
  (`config.toml`, `agents/verifier.toml`) is untracked and predates this
  session (it was in the session's opening `git status`); the other
  untracked dotfiles `git status` shows inside the sandbox (`.bashrc`,
  `.gitconfig`, `.mcp.json`, `.claude/skills`, …) are the sandbox's
  `/dev/null` placeholders described in `docs/guard-and-sandbox.md`, not
  files on the host. Nothing was added, removed or committed.

## Evidence log

```
$ python3 -I $SCRATCH/linkcheck.py docs/architecture/agent-payments-and-marketplace-plan.md docs/architecture/platform-plan.md docs/requirements/lessons-register.md docs/build-records/2026-10-17-agent-payments-plan.md
28 links checked, 0 unresolved
$ python3 -I $SCRATCH/linkcheck.py $(git ls-files '*.md' | grep -v -E '^docs/build-records/[0-9]{4}-')
52 links checked, 0 unresolved
$ git diff --check; echo exit=$?
exit=0
Previous repository, read-only at 3bbbe392 (git -C /home/junc/rikuri/rikurinode show HEAD:...):
  commerce-service/src: 28,294 lines (l402 2,226; agent_wallet 3,628; marketplace 6,380;
  auctions 4,061; registry 6,155; service_registry 2,904; dht 1,688; reconcile 87;
  hmac.rs 151; at_rest.rs 253; main.rs 708; lib.rs 53); inline #[test]/#[tokio::test]
  by module 10/23/109/47/60/3/14/0; tests/: 10 files, 53 test functions;
  ln-host-adapter/src: 1,951 lines. git grep -c commerce-service on the register
  before the change: 0. "AI Passport" in the owner's repositories: no match
  (only "passport" as a sensitive-data pattern in AISecurity).
Verifier pass 1: VERDICT: FAIL (I1: plan §4.2 "encrypted the cache at rest" unsupported;
  old at_rest.rs lines 29-33: wiring into the L402 load/save sites was follow-up work);
  5 nits + 3 summarised. Repaired.
Verifier follow-up: VERDICT: PASS; links 28/0, 52/0; git diff --check exit 0;
  git diff main --check exit 0; I1 and all nits confirmed fixed; no new Important.
Web facts (2026-10-17): OpenShell releases page lists v0.1.4 (13 Oct, Latest),
  v0.1.3 (09 Oct), v0.1.2 (28 Sep); repository licence Apache-2.0; support matrix
  lists Debian/Ubuntu x86_64 and aarch64, macOS, Windows experimental; drivers
  Docker, Podman, Kubernetes, MicroVM. LND PR 5154 "build+lncfg: support pruned
  bitcoind backends", merged 2021-04-08, milestone 0.13.0. Lightning Labs L402 and
  Taproot Assets operational-safety pages as quoted in the plan's §2.
```
