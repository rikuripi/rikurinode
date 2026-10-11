# Build Record — The shared guard notices Rust inline tests that no fix-lock rule covers

| | |
|---|---|
| **Date** | 2026-10-11 |
| **Author / session** | Claude Code (Opus 5.5) for Henry Chen; a side session of a Rikuri-PI session (worktree `musing-khayyam-31764d`) |
| **Branch** | `fix/guard-inline-tests-tripwire`, from `main` (`a443085`), in its own worktree; the main checkout is untouched. Rounds 1–2 were built stacked on `fix/guard-line-continuation` (`1aaa8bd`); round 3 re-applied the same change to `main` (owner, 2026-10-11) |
| **Commits** | one commit on this branch, this record included (owner: "Commit in rikuripi/rikurinode, and one sync commit per repository"); the four sync commits are on branch `fix/guard-inline-tests-tripwire-sync` in each repository |
| **Status** | COMPLETE locally — verifier round 1 FAIL (two defects), fixed in round 2 with tests first; round 2 PASS; round 3 (unstacked onto `main`) re-run in full, verifier PASS. Committed at the owner's request; push, PRs, CI and Python 3.12 Not yet proven |
| **Change type** | fix (a class tripwire for a defect found in Rikuri-PI) |

## 0. Intent — the owner's words, approved before design
- [x] Problem (as the owner would say it): on 2026-10-10 a Rikuri-PI session
      found its `guard-config.json` had no `inline_tests` rule, so a session
      holding a fix-lock could edit the Rust `#[cfg(test)]` tests that prove
      its fix — while `fix-lock on` said "test files, inline tests and
      baselines are now read-only". The shared guard learned inline tests on
      2026-09-28/30 (rikurinode `docs/build-records/2026-09-28-fix-lock-covers-inline-tests.md`),
      but each repository opts in through its own config, and nothing checked
      Rikuri-PI's again when Stage 00 added Rust on 2026-10-05.
- [x] Outcome: (1) the shared `test_guard.py` fails in any Full-tier
      repository whose tracked `.rs` files hold `#[cfg(test)]` tests that no
      `inline_tests` rule covers; (2) `fix-lock on` says only what it really
      makes read-only, and names the files whose inline tests it does not.
- [x] Who/what it affects: the shared `guard.py` and `test_guard.py` in all
      five Full-tier repositories (rikurinode, rikuripi/rikurinode, Iceman,
      AISecurity, Rikuri-PI). No policy file changes. The hook's verdicts do
      not change; only `fix-lock on`'s output and the test suite do.
- [x] Open questions — answered by the owner, 2026-10-11 (Rikuri-PI session,
      four choices put to him):
      - Where it starts: **this repository** (the rebuild; no live LND here),
        then copied unchanged to the other four.
      - Sequencing: **stacked on the line-continuation fix**
        (`docs/build-records/2026-10-11-guard-line-continuation.md`, commit
        `1aaa8bd`), which changes the same two files and has not landed yet.
        In every repository this change merges after that one.
        **Changed by the owner at 14:35 — unstacked.** `main` had been
        re-rooted at 13:32 (`a443085`, a new root commit carrying the
        committed guard `c47b67d1…`, without the continuation fix), and the
        continuation fix was being redone, uncommitted, on top of it;
        committing the stacked files would have committed an outdated copy
        of that unfinished work. Choice: "Unstack, commit now" — this
        change is re-applied to the committed guard and lands first; the
        continuation fix rebases onto it. Sync commits: "A branch in each
        repo" — committed in a clean clone, fetched into the real repository
        as branch `fix/guard-inline-tests-tripwire-sync` (Rikuri-PI: on the
        session's own worktree branch); no other working tree touched,
        nothing pushed.
      - Rikuri-PI: its own `inline_tests` rule (record
        `2026-10-10-fix-lock-covers-inline-tests.md`, now its PR #31)
        **lands first**; this change's Rikuri-PI PR waits for it. Until then
        Rikuri-PI's `main` is the real red case.
      - `fix-lock on` with uncovered inline tests: **engage, say so and name
        them** (not refuse; not wording only).
- [x] Owner approved the intent: "Yes, rikuripi/rikurinode", "Stack on it",
      "Rule lands first", "Say so and name them"; later "Commit in
      rikuripi/rikurinode, and one sync commit per repository", "Unstack,
      commit now", "A branch in each repo" (2026-10-11).

## 0b. Spec — requirements + design, policy applied up front
- [x] Requirements:
      - R1 A generic `GenericPolicy` test lists the tracked `.rs` files
        (`git ls-files '*.rs'` in `guard.ROOT`) and fails, naming them, when a
        file holding a `#[cfg(test)]` marker is not covered by an
        `inline_tests` rule.
      - R2 "Covered" means: a rule's `glob` names the file **and** its
        `starts_at` finds a region that reaches the file's first
        `#[cfg(test)]` marker — a rule that matches the name but never finds
        the tests (or finds only a later block) protects nothing.
      - R3 Only tracked files count (untracked scratch does not); a tracked
        file that cannot be read as UTF-8 counts as uncovered (it cannot be
        checked); any file name git can list is checked; a git failure is an
        error, never "nothing found".
      - R4 The listing reads the repository at the given root whatever git
        environment the caller runs in (a git hook exports `GIT_DIR` and
        `GIT_INDEX_FILE`, which would point `git -C <root>` elsewhere).
      - R5 `fix-lock on` prints "test files, inline tests and baselines are
        now read-only" only when the config has `inline_tests` rules, else
        "test files and baselines are now read-only".
      - R6 `fix-lock on` still engages when tracked inline tests are
        uncovered, and names them on stderr ("NOT read-only"; the first ten
        and a count of the rest); when the check itself cannot run it says
        so on stderr. Exit code 0 in both cases.
- [x] Design: one function in `guard.py`, `uncovered_inline_tests(root, cfg)`,
      used by both the test and `fix-lock on`, so the two can never disagree.
      The marker is a line starting (after spaces or tabs) with
      `#[cfg(test)]`, spaces allowed inside — the form the brief names and
      every repository uses; broader forms (`cfg(any(test, …))`) stay the
      rules' own business. git's output is read as raw bytes (`-z`) and each
      name decoded as the filesystem does (`os.fsdecode`).
      Alternatives rejected: a test-only helper (then `fix-lock on` could
      not reuse it); refusing to engage (owner's choice: a config gap would
      block every lock); walking the working tree instead of git's index
      (scratch and build output would count).
- [x] Policy applied: no behaviour-changing default added — the hook's
      verdicts are unchanged; `fix-lock on` gains a warning, chosen by the
      owner. The test can only add a red, never hide one.
- [x] Flagged concerns resolved: two in-flight changes touch the same ground
      (line-continuation; Rikuri-PI's rule) — both routed to the owner above.

## 1. Plan
- [x] One-sentence statement: the shared guard gets a class tripwire —
      tracked Rust inline tests must be covered by an `inline_tests` rule —
      and `fix-lock on` stops claiming inline tests are read-only when they
      are not.
- [x] Blast radius: `.claude/hooks/guard.py` (one new function and its
      helper, the `fix-lock on` output, the header), `.claude/hooks/test_guard.py`
      (one generic test, one new test class). No funds, auth or exec path;
      nothing irreversible. The hook's decision path is not touched.
- [x] Current behavior characterized: guard suite 102 OK here inside
      `safe-run.sh` (`tripwire-base.out`). Survey of the five repositories
      (clean clones, `survey.out`, `survey_probe.py`): rikurinode 222 `.rs`,
      133 with `#[cfg(test)]`, all 133 covered by its rule (glob and region);
      AISecurity 50 / 29 / 29; Iceman and this repository 0 `.rs`; Rikuri-PI
      `main` (`be979e3`) 53 / 11 / **0** — no rule; with the rule from its
      PR #31, 11 of 11. The old `fix-lock on` says "inline tests" with no
      rule (`rpi-fix-lock-on.out`, first block).
- [x] Files and order: this record → tests (red) → `guard.py` (green) →
      mutants → the other four repositories' clean clones with their own
      policies → verifier → sync records.
- [x] Risks: the generic test reads git in `guard.ROOT`; a run outside a git
      work tree errors (by design: never "nothing found"). CI checks out with
      git. The riskiest step is the five-way copy: confirmed with `cmp`.
- [x] Verification defined up front — I will know this works when: the new
      tests fail on the current guard and pass on the new one; the generic
      test is red in a clean clone of Rikuri-PI `main` with the new files and
      green once its rule is applied; mutants of each requirement are
      caught; all five repositories pass the suite with their own policies;
      the files are byte-identical (`cmp`).

## 2. Build
- [x] New code meets the bar: `uncovered_inline_tests` takes nothing from
      outside but git's own output, read as bytes; a git failure (non-zero
      exit, timeout, missing binary) raises `OSError`, which `fix-lock on`
      reports and the test surfaces as an error. `git_env()` drops the
      variables `git rev-parse --local-env-vars` lists. The config is loaded
      before the lock file is written, so a config error cannot leave a lock
      behind without a message. The ENGAGED line is flushed before the
      warning, so a piped run shows them in order.
- [x] Clean as you go: the old unconditional message is gone from `guard.py`
      (`guard_base.py`, the frozen previous guard, still has it and is never
      reached from this CLI — left unchanged, as it must stay identical).
- [x] Security question: touches no auth / money / exec / private data. It
      strengthens an AI-session tripwire; the hook's verdicts do not change.

## 3. Debug
- [x] Reproduced before fixing: Rikuri-PI `main` has 11 tracked `.rs` files
      with inline tests and no rule, and its guard suite is green on the old
      files; the old `fix-lock on` there says inline tests are read-only
      (`rpi-fix-lock-on.out`).
- [x] Failing test written and SEEN failing, round 1: red at 11:19:44
      (`tripwire-red.out`: 14 errors — the function does not exist yet;
      `test_guard.py` `7c943ac7…`). Green at 11:28:24 with `test_guard.py`
      unchanged (`tripwire-green.out`, 116 OK). The fix-lock was not engaged:
      this session's hook is Rikuri-PI's guard, rooted in its own worktree,
      so a lock written in this worktree would bind nothing (this
      repository's procedure asks for it; the owner's call). Evidence stands
      in for it: the test file's hash at each red, and every test change
      after a red, below, with its reason. Behavioural reds: the mutants (§4)
      and the real case — Rikuri-PI `main` with the final files fails exactly
      the new generic test, naming its 11 files (`sync-Rikuri-PI-main.out`);
      the old message is mutant W1.
- [x] Test change after the round-1 red, with its reason:
      `test_tracked_inline_tests_have_a_rule` keeps its assertion
      (`gaps == []`) but its message now lists every file on one line.
      unittest's summary line cut the list (`'crat[358 chars].rs'`); its diff
      below did list all 11, but unittest cuts that too past its length
      limit, and a repository adopting Rust with no rule could have more
      (rikurinode would show 133). `test_guard.py` `7c943ac7…` → `4d7b7f1d…`;
      nothing loosened (`tripwire-green2.out`, 116 OK).
- [x] **Round 2 — verifier round 1 FAIL** (report summarized in §4):
      D1 evidence with trailing spaces (fixed: every output rewritten with
      trailing spaces stripped on every line, and the gate run on a copy
      with everything committed); D2 `fix-lock on` crashed (traceback, exit
      1, after the lock was written) on a tracked `.rs` file whose name is
      not UTF-8: `text=True` decoding raised `UnicodeDecodeError`, a
      `ValueError` the CLI does not catch. Tests first: red at 13:02:28
      (`round2-red.out`: 118 run, 1 error, the `UnicodeDecodeError`;
      `test_guard.py` `a03e4e2d…`, guard.py round 1 `7854c211…`); fix: git's
      output read as bytes and each name decoded with `os.fsdecode`; green
      at 13:02:55 with `test_guard.py` unchanged (`round2-green.out`, 118 OK; guard.py
      `7725a437…`).
- [x] Test changes in round 2 (all additions; nothing loosened): a test for
      D2 (`test_a_name_that_is_not_utf8_is_checked`, skipped with its reason
      where the filesystem refuses such a name — macOS), and cases for the
      verifier's five surviving mutants: a tab before the marker;
      `src/café.rs`, which git quotes without `-z`
      (`test_a_name_git_would_quote_is_checked`); a rule whose region starts
      inside the marker; an empty rule list (`inline_tests: []`) saying
      "test files and baselines"; and the non-UTF-8 name, which a swallowed
      listing error would hide.
- [x] **Round 3 — unstacked onto `main`** (owner, 14:35): the round-2 diff
      (`git diff 1aaa8bd -- .claude/hooks/`) applied to `main` `a443085`
      with a three-way merge, cleanly; its added and removed lines are
      identical to the stacked change's. `main`'s committed guard is
      `c47b67d1…` / `29e160d3…`, the same as the other four repositories'.
      Red at 14:36:57 (`round3-red.out`: the change's tests on that guard,
      107 run, 16 errors — all 16 new tests; `test_guard.py` `08e00cb4…`);
      green at 14:37:17 with `test_guard.py` unchanged (`round3-green.out`:
      107 OK on Python 3.14 and on 3.9.25; `guard.py` `c1d54b73…`). 107 =
      `main`'s 91 + the 16 new; rounds 1–2 counted 116 / 118 because the
      stacked base had the continuation fix's 11 more.
- [x] Root cause is a CLASS: per-repository guard policy drifts behind the
      repository's stack — the shared guard learns a protection, each
      repository opts in through its config, and nothing re-checks the
      config when a repository adopts a new language.
- [x] Siblings: the same opt-in shape exists for `test_globs` (a new test
      layout, e.g. Rikuri-PI's test-only crate `rikuri-testkit`, already
      routed to the owner in its own record) and `fix_lock_preflight`;
      neither has a language marker a generic test could check without false
      alarms. Two Rust layouts the inline-test rule itself does not cover are
      listed under Skipped (verifier round 1). Iceman and this repository
      track no `.rs` today; the new test covers them the day they do.

## 4. Verify
- [x] Unit tests: `InlineTestCoverage`, 15 tests in scratch git repositories
      (a file needs a rule; every folder counts; the rule must name the file;
      the rule must find the tests from the first marker; only real markers
      count; a name git would quote is checked; a name that is not UTF-8 is
      checked; untracked files do not count; an unreadable file counts; a
      git failure is an error; a git hook's environment does not redirect
      the listing; `fix-lock on` says what it covers, names what it does
      not, cuts a long list but counts it, says when it cannot check), plus
      `GenericPolicy.test_tracked_inline_tests_have_a_rule`. Stacked (round
      2): 118 OK (`round2-green.out`). On `main` (round 3): 107 OK on
      Python 3.14 and 3.9.25 (`round3-green.out`).
- [x] Watched it work through the real entry point: `python3 .claude/hooks/guard.py fix-lock on …`
      in a clean clone of Rikuri-PI `main` (`rpi-fix-lock-on.out`): the old
      guard says "test files, inline tests and baselines"; the new one says
      "test files and baselines" and warns that the tests inside 11 tracked
      files are NOT read-only, naming ten and "1 more"; with PR #31's rule
      it says "test files, inline tests and baselines" and warns nothing.
      Speed: the check takes 0.04 s over rikurinode's 222 `.rs` files.
- [x] Recovery/fallback: N/A — no fallback path; a guard crash still asks
      (`FailureModes`, unchanged, green).
- [x] Regression guard proven to FAIL on the old code: the generic test
      fails on Rikuri-PI `main` (`sync-Rikuri-PI-main.out`); the old
      message fails `test_fix_lock_on_says_what_it_covers` (mutant W1); the
      round-1 decoding fails the D2 test (mutant U14). Mutants, each
      restored and checked by sha256 (`mut_tripwire.py`, `mut_tripwire.out`):
      U1 no rule needed, U2 glob ignored, U3 starts_at ignored, U4 any
      region enough, U5 untracked files count, U6 git's environment passes
      through, U7 git failure is nothing found, U8 unreadable file skipped,
      U9 marker in column 0 only, U10 marker anywhere on a line, U11 a tab
      before the marker, U12 no `-z`, U13 the region need only reach the
      marker's end, U14 strict decoding, U15 non-ASCII names skipped, W1 the
      old message, W2 no warning, W3 a failed check silent, W4 uncovered
      files refuse the lock, W5 the list uncut, W6 a check error crashes
      `fix-lock on`, W7 an empty rule list claims inline tests — **22 of 22
      red** (round 1: 16 of 16; U11–U15 and W7 are the verifier's five
      survivors and the round-1 decoding); round 3, on `main`: **22 of 22
      red** again, `guard.py` restored to `c1d54b73…`.
- [x] The other four repositories (round 3, the unstacked files), clean
      clones, each with its own policy; their committed `guard.py` and
      `test_guard.py` equal `main`'s, so the same two files apply to all
      five, `cmp`-equal, `guard_base.py` unchanged: rikurinode
      (`cleanup/main` `3bbbe392`), AISecurity and Iceman 107 OK each on
      Python 3.14 and 3.9.25 (`sync-*.out`); Rikuri-PI `main` 1 failure on
      both — the new tripwire, naming its 11 files — and 107 OK on both
      with PR #31's rule (`sync-Rikuri-PI-main.out`,
      `sync-Rikuri-PI-with-rule.out`). Rounds 1–2 ran the same checks on the
      stacked files (116 / 118). 3.12, CI's newer entry, is not installed
      here: Not yet proven until CI. Every run inside `safe-run.sh`; lnd's
      StartedAt `2026-10-09T20:20:27.903167252Z` before and after each.
- [x] Independent verification, round 1: **FAIL**. Passed: R1–R5, the hook's
      verdicts unchanged (AST comparison; 1aaa8bd's 102 tests against the
      new guard in all five repositories), suite counts and `cmp` in all
      five, 16 of 16 mutants, the survey, Python 3.9, the gate as the tree
      stood, no security issue. Failed: D1 and D2 (§3, fixed). Nits: (1) a
      tests-only file declared with `#[cfg(test)] mod tests;` or starting
      `#![cfg(test)]` is not covered by any `inline_tests` rule and is not
      flagged — an older gap of the rule, now under Skipped; (2) five
      surviving mutants — now caught (U11–U15, W7); (3) this record
      overstated why the failure message changed — corrected in §3; (4) the
      fix-lock was not engaged — disclosed in §3, the owner's call; (5)
      `guard_base.py` still prints the old message — §2.
- [x] Independent verification, round 2: **PASS**. D2 reproduced on the
      round-1 `guard.py` (rebuilt by reversing the round-2 edits; it hashes
      to `7854c211…`) and fixed now (exit 0, the file named, lock written;
      a name with a newline also named); D1 fixed (no whitespace errors;
      the full gate on its own committed copy, 7 of 7). Nothing loosened:
      removing exactly the round-2 additions from `test_guard.py` gives the
      round-1 file's hash `4d7b7f1d…`. 22 of 22 mutants red, plus its own
      (names dropped, replaced or read as latin-1; `is not None` for the
      empty list) red. Hook verdicts unchanged (AST; 1aaa8bd's 102 tests).
      Five repositories `cmp`-equal; 118 OK on 3.14 and 3.9.25 (Rikuri-PI
      with PR #31's rule, its head `8e2ddc2`); Rikuri-PI `main` red only on
      the tripwire; TMPDIR inside a git work tree 118 OK. Not yet proven:
      Python 3.12, CI, macOS. Nits under Skipped. lnd unchanged.
- [x] Diff matches the §1 plan: two tracked files plus this record and its
      evidence; `guard_base.py`, the config and settings untouched
      (verifier, both rounds).
- [x] Independent verification, round 3 (the unstacked change): **PASS**.
      The diff on `main` reproduces the round-2 change (the patch applied to
      1aaa8bd's files gives `7725a437…` / `a03e4e2d…`; added and removed
      lines identical); AST: only `fix_lock_cli` and the docstring changed
      plus four new definitions, and `a443085`'s own 91 tests pass on the
      new guard, so the hook's verdicts are unchanged. `cmp` equal in all
      five; the committed bases match `a443085`'s. 107 OK on 3.14 and 3.9.25
      in all five (Rikuri-PI with PR #31's rule); the red reproduced (16
      errors); 22 of 22 mutants; its own committed-copy gate 7 of 7; no
      whitespace errors. Noted: Rikuri-PI's `origin/main` has moved to
      `5bc2948`, where the tripwire finds 13 uncovered files (0 with PR #31's
      rule). lnd unchanged.

## 5. Close Out
- [x] Full gate green: 7 of 7 inside `safe-run.sh` on a private copy with
      every file of this change committed, so step 6 sees the evidence too
      (`gate-committed.out`; round 3, on `main` `a443085`: guard suite 107
      OK, the quality tools' 61 OK, hygiene, shell lint, whitespace, secret
      scan).
- [x] Scrap Sweep: the survey probe is kept as evidence (`survey_probe.py`);
      superseded runs made with earlier files were deleted (their final-file
      runs are `round3-green.out`, `sync-*.out`, `mut_tripwire.out`,
      `rpi-fix-lock-on.out`, `gate-committed.out`; `py39.out` folded into
      `sync-*.out`). Rounds 1–2's red and green receipts stay, as history.
      The clean clones, the gate copy and this worktree live in the
      session's scratchpad, outside every repository; removed after the
      branches are fetched.
- [x] Reviewed per `REVIEW.md`: bugs, security and plan compliance by the
      verifier, two rounds (above): the Important finding (D1) and the
      defect (D2) fixed; the Nits fixed or listed under Skipped.
- [x] Lesson loop: the class tripwire is the lesson's entry — the generic
      test now runs in every Full-tier repository on every gate run.
- [x] Knowledge layer: `guard.py`'s header describes the tripwire and the
      `fix-lock on` warning. No document quotes the old message (searched
      the five repositories' Markdown outside build records); AGENTS.md
      files say tests become read-only, which stays true.
- [x] Commit message explains WHY; record committed with the change
      (owner, 2026-10-11).

## Skipped items — visible, never silent
- **Push, PRs and CI**: left for the owner; nothing pushed. Rikuri-PI's
  commit waits for PR #31 before its PR (its guard suite is red without
  the rule, by design). The line-continuation fix, being redone on `main`,
  now lands after this change and must be re-applied on top of it in every
  repository, so the files stay identical. Owner: Henry.
- **Two Rust test layouts the `inline_tests` rule does not cover**
  (verifier round 1, an older gap of the rule, not of this change): a
  tests-only file declared from its parent with `#[cfg(test)] mod tests;`
  (`src/tests.rs`), and a file that starts `#![cfg(test)]`. Neither holds a
  `#[cfg(test)]` line, so this tripwire does not flag it, and an Edit to it
  under the lock is allowed. No repository uses either layout today (`git
  grep`, verifier). Proposed: count `#![cfg(test)]` as a marker and treat a
  `mod x;` declared under `#[cfg(test)]` as test code, each with a rule
  change in the repositories that have Rust. Reactivate: before either
  layout is adopted, or at the next shared-guard change. Owner: Henry.
- **Wider markers are not checked**: a file whose only inline tests sit
  under `#[cfg(any(test, …))]` or `#[cfg(all(test, …))]` is not flagged
  (every repository's rule already covers those forms; none uses one
  without a plain `#[cfg(test)]` today: rikurinode 133/133, AISecurity 29/29).
  Reactivate if such a file appears. Owner: Henry.
- **Other opt-in keys** (`test_globs` for a new test layout,
  `fix_lock_preflight`) and other languages' in-file tests: no generic
  marker to check without false alarms. Rikuri-PI's `rikuri-testkit` is
  already an owner choice in its 2026-10-10 record. Owner: Henry.
- **A non-UTF-8 file name cannot be tested on macOS** (APFS refuses it):
  `test_a_name_that_is_not_utf8_is_checked` skips there with its reason,
  counted in the run's "skipped". Linux CI runs it.
- **Verifier round 2 Nits** (accepted, reasoned): (1) the defensive
  `errors="replace"` when decoding git's error text has no test of its
  own — it matters only when git's message is not UTF-8 (a repository
  folder with a non-UTF-8 name), and the strict form would raise
  `UnicodeDecodeError` instead of the `OSError` `fix-lock on` reports;
  (2) under `PYTHONIOENCODING=ascii` the ENGAGED line's em dash raises
  `UnicodeEncodeError` — the base guard prints the same dash, older than
  this change. Reactivate either at the next shared-guard change. Owner:
  Henry.
- **Noise in test output**: the existing `fix-lock` CLI tests run in temp
  folders that are not git repositories, so they now print "WARNING: could
  not check …". That is the designed message for that case; left as is.

## Evidence log
Files in `evidence/2026-10-11-guard-inline-tests-tripwire/`, outputs as
written with trailing spaces stripped from every line; every run inside
`safe-run.sh`.
```
base     tripwire-base.out: 102 OK (stacked base: guard 4a04d288…, this repository's policy)
survey   survey.out (survey_probe.py): rikurinode 133/133 covered, AISecurity 29/29, Iceman 0,
         Rikuri-PI main 0/11, with its rule 11/11, this repository 0
round 1  (stacked on 1aaa8bd) red 11:19:44 tripwire-red.out: 14 errors; guard.py 4a04d288…, test_guard.py 7c943ac7…
         green 11:28:24 tripwire-green.out: 116 OK; guard.py 7281fc0e…, test_guard.py unchanged
         tripwire-green2.out: 116 OK; test_guard.py 4d7b7f1d… (failure message names every file)
         then guard.py 7854c211… (ENGAGED line flushed); 16/16 mutants; verifier round 1: FAIL (D1, D2)
round 2  (stacked) red 13:02:28 round2-red.out: 118 run, 1 error (D2); guard.py 7854c211…, test_guard.py a03e4e2d…
         green 13:02:55 round2-green.out: 118 OK; guard.py 7725a437…, test_guard.py unchanged;
         22/22 mutants; verifier round 2: PASS
round 3  (unstacked onto main a443085, owner 14:35) the same diff, three-way applied, lines identical
         red 14:36:57 round3-red.out: 107 run, 16 errors on main's guard c47b67d1…; test_guard.py 08e00cb4…
         green 14:37:17 round3-green.out: 107 OK on 3.14 and 3.9.25; guard.py c1d54b73…, test_guard.py unchanged
mutants  mut_tripwire.py / mut_tripwire.out: 22 of 22 red on main, guard.py restored (sha256 c1d54b73f32e)
demo     rpi-fix-lock-on.out: old vs new fix-lock on in Rikuri-PI main, then with PR #31's rule
sync     sync-{old-rikurinode,AISecurity,Iceman}.out: 107 OK each on 3.14 and 3.9.25, own policy
         sync-Rikuri-PI-main.out: 1 failure on both, the new tripwire (11 files);
         sync-Rikuri-PI-with-rule.out: 107 OK on both
gate     gate-committed.out: 7 of 7 on a private copy with every file of this change committed
lnd      StartedAt 2026-10-09T20:20:27.903167252Z before and after every run
```
