# Build Record — the shared guard reads a continued command as one command

| | |
|---|---|
| **Date** | 2026-10-11 |
| **Author / session** | Claude Code (Opus 5.5); owner Henry |
| **Branch** | fix/guard-continuation, rebased onto `main` 0f407f3 in round 4 (rounds 1 and 2 were on fix/guard-line-continuation, 1aaa8bd on the bootstrap's round 5, which `main` replaced; that branch is superseded) |
| **Commits** | round 3: 7c77ce4 (was 92c39a2 before the rebase); round 4: 944fe55, 517e385, 7390125 (receipt); round 5: 6b9be19, the merge of `main` 7ecc958, 0d50bb4 (receipt); round 6: 5d4999d, eaa8333 (receipt); round 7: 8404ed0, and the commit that adds this line (receipt) (rounds 1-2: 1aaa8bd, superseded); the four sync commits follow the verifier |
| **Status** | IN PROGRESS — rounds 1 to 5 FAIL (rounds 4 and 5: review only, the owner's choice); round 6's final check FAIL on wording only (the owner's stop rule, 2026-10-11), fixed in round 7 with no check round after it; then the sync, after the other session's shared-guard change lands (the owner's choice, 2026-10-11: that one first, this one on top), with `main` merged in and the gate rerun on the merged tree; known, before the sync: round 4's "Final run" found a few denies of `main`'s guard this one does not give (Skipped items) |
| **Change type** | fix (security gate, shared by five repositories) |

## 0. Intent — the owner's words, approved before design
- [x] Problem: the AI-session guard (`.claude/hooks/guard.py`, identical in
      every Full-tier repository) splits a command at every newline, even
      when the line ends in a backslash — which the shell reads as "the
      command continues on the next line". So `lncli \⏎ sendcoins …` was
      judged as two harmless lines. Found by the bootstrap's round-1
      verifier (`docs/build-records/2026-10-10-bootstrap.md`, I3); this
      repository's policy asks before any continued node command meanwhile.
- [x] Outcome: every repository's guard reads a continued command as the
      shell does — one command — so each rule judges it whole.
- [x] Who/what it affects: the guard in all five Full-tier repositories
      (this one; the previous rikurinode; Rikuri-PI; Iceman; AISecurity).
      Nothing on the running node.
- [x] Owner approved, 2026-10-11: "Yes, please fix the bug in the shared
      guard" (the recommended option: fix in every repository; Rikuri-PI's
      copy arrives by pull request, beside another session's open work).

## 0b. Spec
- [x] Requirements:
      - R1 Outside quotes and inside double quotes, a backslash followed by
        a newline joins the two lines (the shell removes both characters).
      - R2 Inside single quotes it stays literal (the shell keeps it).
      - R3 An escaped backslash before a newline (`\\⏎`) is not a
        continuation: the newline still ends the command.
      - R4 A backslash at the end of a comment does not continue it: the
        next line is its own command (`# note \⏎ git push --force` runs the
        push).
      - R5 Inside double quotes, `\"` does not end the quote (needed for R1
        and R3 there: the parser must know which backslashes are escaped).
      - R6 Nothing the guard caught before is lost: `guard_base.py` (the
        previous guard, run unchanged beside the new code) stays as is, and
        every repository's own worked examples still pass. Amended in round
        5 (round 4's verifier): except, by the owner's choice (R10), the
        previous guard's asks on the separate lines of a continued command;
        its denies there stand. And (round 5's verifier; amended in rounds 6
        and 7) its asks on a backslash that ends the command (R9; since round
        5 a comment's too, since round 6 a comment's whole last run): the
        joined text it is given has none, and on its line-by-line reading,
        which still has it, only a deny counts. That no deny is lost is not
        shown, and round 4's "Final run" found a few lost, not analysed
        (Skipped items).
      - R7 (this repository's policy; a sibling found while narrowing the
        stopgap rule) A rule reads every line of a segment: a command on the
        second line of a quoted script is judged like one on the first.
        Segments that only read or describe (commit messages, `echo`,
        searches) stay exempt from their start.
      - R8 (round 2; a sibling the verifier found; made concrete in round 3)
        The guard answers within its time, because Claude Code lets a call
        through when its hook times out (unless `"onFailure": "block"`): a
        command longer than 16,000 characters asks before any check, and a
        decision that runs out of its 7 s (the hook has 10) asks — in every
        profile. A deny the previous guard finds in time still stands.
      - R9 (round 3; the round-2 verifier's regression) A backslash that ends
        a command continues onto nothing and is dropped (zsh drops it; bash
        keeps it as a character, which changes no command here): `sh -c 'git
        push --force origin x' \` is judged as the force push it runs. Round
        4 (round 3's verifier): an escaped blank at the end stays a word,
        and a backslash that ends a comment is the comment's text. Rounds 5
        and 6: at the command's end that text is dropped, a comment's whole
        last run of backslashes (none is an escape there), so neither the
        new checks' segments nor the joined text end in one (round 4's
        verifier, V16; round 5's, a run of two); the previous guard's
        line-by-line reading still sees it, where only a deny counts.
      - R10 (round 4; the owner, 2026-10-11: "Judge as one line") A command
        continued over lines is judged as the same command on one line, by
        the new checks and by the previous guard, which is given the joined
        text.
- [x] Design: fix the one tokenizer every check uses (`split_segments`), so
      the money rules, secret reads, pushes, fix-lock and test-write checks,
      and nested `sh -c` text all see the joined command. Rejected: joining
      continuations in a pre-pass over the whole text (it cannot tell quotes
      and comments apart); a policy rule in each repository (that is the
      stopgap this replaces — it can only ask, and only for the commands it
      names).
- [x] Policy applied: a security gate. Not "the change can only make the
      guard see more" (said until round 3, and false — round 3's verifier):
      the guard now sees a continued command whole, and judges it as its
      one-line form, so whatever gets through on one line also gets through
      continued (the owner's choice, R10). This repository's stopgap rule
      is narrowed, not dropped: a command broken across lines inside program
      code (a backslash-newline inside single quotes, which Python and other
      languages join, or the escapes `\\` and `\n` in a code string) is
      still invisible to a shell parser.
- [x] Flagged concerns: Rikuri-PI's working tree holds another session's
      uncommitted work and that session's fix-lock; its copy is changed in a
      separate worktree on a branch from `main`, by pull request, so that
      work is untouched.

## 1. Plan
- [x] One sentence: `split_segments` follows the shell's backslash rules, and
      the five copies of the guard stay identical.
- [x] Blast radius: `.claude/hooks/guard.py` and `test_guard.py` (shared,
      copied to five repositories, `cmp`-identical), this repository's
      policy (`scripts/quality/guard_policy.py` → `guard-config.json`: the
      stopgap rule, R7, examples), `AGENTS.md` (the guard's limits), the
      bootstrap record's Skipped item (a pointer here), this record and its
      evidence folder. No auth, money or exec path of the node; the guard is
      a security gate.
- [x] Current behaviour characterized (`cont-before.out`, unmodified guard,
      a synthetic money rule, profile stable): `movemoney \⏎ --amt 5`,
      `cat \⏎ .env`, `git push \⏎ --force origin x`, `git push origin \⏎
      main`, `echo x >> \⏎ tests/test_something.py` under the fix-lock,
      `guard.py fix-lock \⏎ off` and `sh -c 'movemoney \⏎ --amt 5'` are all
      **allowed**; `echo hi # note \⏎git push --force origin x` is denied
      (correctly — it must stay denied). `split_segments` returns
      `['movemoney \\', '--amt 5']`.
- [x] Order: this record → tests in `test_guard.py` (red on the unmodified
      guard; sha256 recorded) → the fix → all five repositories' guard tests
      against their own policies → this repository's policy and examples →
      gate → verifier → commit here, then a sync commit in each repository
      naming this record.
- [x] Risks: a parser change that splits differently elsewhere and loses a
      check — every repository's worked examples (598 here, the others'
      own) and the shared tests replay it, and `guard_base.py` still runs;
      R4's comment case.
- [x] I will know this works when: the eight cases above get ask or deny as
      the joined command would (the comment case stays deny); the shared
      tests and every repository's examples pass in all five repositories;
      the five copies are `cmp`-identical; and a mutant that removes the
      join turns the new tests red.

## 2. Build
- [x] New code meets the bar: one function changed (`split_segments`, 26 →
      39 lines in round 1; 54 after round 3; 78 after round 5; 85 after round 6) and one named
      constant (`WORD_BREAK`); the header names the fifth repository and
      continued lines. `guard_base.py` unchanged (sha256 `1ef6f5cc…`, as in
      all five repositories). Rounds 2 and 3 add the length limit and the
      time bound (`decide` 70 lines after round 6, `_alarm` 21, `_timed`
      13; round 3's `_base_in_child` was removed in that round); round 4
      adds `_end_segment` (13), `_joined` (17 after round 6) and `_all_segments` (15), and
      grows `_balanced` (28) and `_substitutions` (15). `guard.py` is 2,147
      lines after round 6 (round 4's verifier found this paragraph's numbers stale: they
      were measured before round 4's last changes), past the 1,200 to
      justify: it is one file on purpose, copied unchanged to five
      repositories and run as one script by the hook, and splitting it is
      its own change.
- [x] Clean as you go: the stopgap rule's reason said the shared guard
      "judges each line on its own" — rewritten for what it still covers;
      `AGENTS.md`'s limits paragraph rewritten the same way.
- [x] Security question: a gate that decides what an AI session may run.
      Proven by `LineContinuation` (6 tests) and this repository's worked
      examples (611) in round 1; after round 4, by `LineContinuation` (8),
      `LineContinuationRound3` (5), `LineContinuationRound4` (5),
      `TimeBound` (11), `TimeBoundRound4` (3), `JudgedAsOneLine` (5) and
      `LoneAmpersand` (2), and 959 examples.
- [x] This repository's policy. The stopgap rule now asks only for a node,
      container or system command broken inside program code: a backslash
      before a newline *inside* the text (only quoted text keeps one), or the
      escapes `\\` and `\n`. It must not fire on a backslash at a segment's
      end: `guard_base.py`, the previous guard that runs beside `guard.py`
      and can only add asks, still cuts a continued line after its
      backslash — with that pattern, `lncli \⏎ getinfo` kept asking through
      it (seen: 4 example failures, `lncli \⏎ getinfo` and `docker \⏎ ps` in
      both profiles; that run's output was overwritten by the next and is not
      kept). R7: every rule's read exemption is anchored at the segment's
      start (`\A`), the rule searches all of its lines (`[\s\S]*?`), and
      `(?m)` makes each other `^`/`$` a line's. A code string's `\n` escape
      also starts a line (`LINE`, used by the word-start fragment `W` and by
      the rules that look for a line's start): a shared test wraps every
      must-ask example in `subprocess.run("…")`, where a newline becomes the
      two characters `\n`. The lncli and bitcoin-cli money rules' help
      exemptions now apply to the line that runs the command. 13 worked
      examples added (611): commands on a later line of `python3 -c`,
      `node -e` and `ssh` strings; a command broken inside code; `\ncd` into
      the previous checkout inside a code string; a bitcoin-cli spend on one
      line of a script that mentions help on another; continued reads
      (`lncli \⏎ getinfo`, `docker \⏎ ps`) allowed; a multi-line commit
      message allowed; help text allowed.

## 3. Debug
- [x] Reproduced before fixing: `cont-before.out` (above). For R7,
      `multiline-before.out`: `python3 -c 'import os⏎os.system("lncli
      sendcoins …")'`, the same with `docker restart lnd`, and `node -e
      '⏎…execSync("bitcoin-cli sendtoaddress …")'` were **allowed** by this
      repository's policy; the one-line form asked.
- [x] Failing test written and seen failing: `LineContinuation` (4 tests)
      red at 02:23:49 on the unmodified guard — 3 failures and 1 error, the
      hook letting `cat \⏎ .env` through (`cont-red.out`). `test_guard.py`
      sha256 `d66c9461…` recorded then, unchanged at green 02:24:51
      (`cont-green.out`, 95 OK). The fix-lock was not engaged: this session
      was opened in Rikuri-PI, so its hook is Rikuri-PI's guard, which
      neither reads this repository's lock nor these paths — the recorded
      sha256 stood in for it.
- [x] Root cause is a class: the guard's tokenizer disagreed with the shell
      about backslashes, comments and quotes. Its sibling in this
      repository's policy: rules that read only a segment's first line.
- [x] Swept for siblings (`cont-siblings.out`, old guard vs new, same
      policy): every other line-based reader either feeds `split_segments`
      (heredoc shell lines) or reads Python code under the fix-lock, where
      the probes stayed deny. Found and fixed: **an apostrophe inside a
      comment opened a "quote" that hid the following lines** — `x=1 # it's
      fine⏎git push --force origin x` was allowed, and `# don't⏎cat .env`
      asked instead of denying; also a continued command in a heredoc fed to
      `sh`, and a heredoc started on a continued line under the fix-lock.
      These tests (`test_siblings`) were written after the fix and shown red
      on the old guard and green on the new; `cont-oldguard.out` is the final
      class run against the old guard: all 6 `LineContinuation` tests fail
      (5 failures, 1 error).
- [x] **Said plainly — the gate caught me.** My first commit of this change
      failed the full gate (`cont-gate.log`, one failure in
      `test_round3_money_and_secrets_in_heredocs_still_ask`). I had added the
      `ssh` example after my last full guard run and run only the mutants
      after it; this record then said 609 examples passed, on the strength of
      a run with 608. The failure was real coverage: the shared test wrapped
      the `ssh` example in `subprocess.run("…")`, where the old-checkout rule
      did not count a `\n` escape as a line start — fixed by `LINE` (above),
      with the `\ncd` example and mutant P7. Every count in this record was
      rerun after the last change (`cont-policy4.out`).

## 4. Verify
- [x] Unit tests: `LineContinuation`, 6 tests (joined lines; what the shell
      does not join; ten continued commands judged whole; siblings; comment
      boundaries; through the hook). Guard suite 97 OK here with the 611
      examples (`cont-policy4.out`), and in clean clones of the other four,
      each with its own policy (`sync-*.out`: Rikuri-PI at `origin/main`,
      Iceman, AISecurity, the previous rikurinode — 97 OK each; their
      policies are not touched by this repository's).
- [x] Watched it work through the real hook entry point:
      `test_through_the_hook` runs `guard.py` as Claude Code does (JSON on
      stdin) and gets deny for `cat \⏎ .env`.
- [x] Recovery/fallback: N/A — no fallback path changes; a guard crash still
      asks (`FailureModes`, unchanged, green).
- [x] Regression guard proven to fail on the old code: the red run above.
      Mutations, each restored and checked by sha256: M1 no join, M2 join
      inside single quotes, M3 join inside a comment, M4 no comments, M5
      quotes open in comments, M6 `\"` ends a double quote — red at once;
      M7 a comment never ends and M8 a `#` inside a word starts a comment
      **survived** (`mut_cont.out`) → a test of comment boundaries added →
      8 of 8 red (`mut_cont2.out`). Policy mutants: P1 rules read only the
      first line, P2 the read exemption on every line, P3 no multi-line mode
      (it needed the `ssh` example), P4 the code-escape rule on a backslash
      at a segment's end, P5 the lncli money rule on the first line only, P6
      a help word anywhere exempts bitcoin-cli — 6 of 6 red
      (`mut_policy.out`); after `LINE`, P7 a `\n` escape is not a line start
      — red — and P6 **survived** (the example that caught it was now also
      asked by another rule: `mut_policy2.out`) → the help-on-another-line
      example → 7 of 7 red (`mut_policy3.out`).
- [x] Speed (round 1): a 29 KB multi-line script is judged in 0.11 s
      (`multiline-after.out`; the hook allows 10 s). Since round 2 a command
      over 16,000 characters is not judged: it asks.
- [x] **Verifier, round 1: FAIL.** Passed: the gate 7/7 (97, 46), 611
      examples, `--check`; every acceptance case through the real hook (the
      old guard allowed `cat \⏎ .env` and a continued locked-test write; the
      new one denies them), continued reads free; the R7 cases; the four
      other repositories 97 OK each against their own policies, their
      `guard_base.py` identical; every number it could check in the record.
      Failed: (1) **a regression** — `split_segments` started a comment at a
      `#` that followed an escaped character (`a\ #b`, `\;#`, `\(#`) or a
      `$(…)`, where bash and zsh keep it inside the word; so it did not join
      the continuation after it, and the narrowed stopgap no longer caught the
      dangling backslash: `lncli --metadata=k:a\ #b \⏎sendcoins …` and, in
      `stable`, `git -c user.name=a\ #b \⏎push origin main` were allowed where
      the previous guard asked — against R6 and "the change can only make the
      guard see more"; (2) three mutants that weaken verdicts survived — `\\`
      dropped from the double-quote escapes, TAB dropped from the word breaks,
      a comment ending at any separator — and one policy mutant (`echo` no
      longer exempt); (3) "a code string's `\n` escape counts as a line start"
      was true only for the rules that look for a line's start: a command
      word right after `\n` (`subprocess.run("ls\nlncli sendcoins …")`) was
      allowed, as by the old guard; (4) a 69 KB one-line command took 14 s
      through the hook (12 s in the old guard), past its 10 s timeout; (5)
      evidence: `cont-gate.log` named but not in the folder (git ignores
      `*.log`); `multiline-before.out` shows 4 allowed commands, the record
      said 3; the mutation receipts were made against a `guard.py` before its
      last docstring edit. Holes older than this change, in both guards:
      ANSI-C quoting (`$'…'`), a `"` inside `'…'` inside `$(…)` inside
      `"…"`, an apostrophe in a heredoc body, a lone `&` not read as a
      separator. Evidence: its `rn-verify5/`.
- [x] **Round 2** (tests first; `test_guard.py` sha256 `ea19d761…` at red).
      Red at 04:52:37 (`cont2-red.out`: the `#`-inside-a-word cases fail,
      and the time-bound tests error — no limit existed). The tokenizer now
      tracks whether a word has started (`word_start`): an escaped character,
      a quote or the `)` of a `$(…)` continue a word, so a `#` after them is
      text, and only an unquoted, unescaped break starts a new word. R8:
      `MAX_COMMAND_CHARS` = 16,000 — measured with this repository's policy,
      the slowest of the five, the worst case found (the lncli rules over a
      line of repeated `lncli getinfo`) took 1.3 s at 16,000 characters,
      2.5 s at 24,000 and 4.2 s at 32,000 (time grows with the square of the
      length); a longer command asks in every profile, before any check runs.
      Green at 04:53:59 (102 OK), the test file unchanged since red. This
      repository's code rule also asks for a node, container or system
      command right after a `\n` escape in code (R7's claim now holds for
      every rule). 9 worked examples (6 ask, 3 free, `echo` and `printf`
      exempt): red at 04:54:27, 8 failures (`cont2-policy-red.out`); green at
      04:54:58, 637 examples (`cont2-policy-green.out`). Mutants, Python's
      bytecode cache off, inside an outer layer (`mut_cont3.py`): M1–M8 again,
      the verifier's S1–S3, W1 (an escaped character starts a word), W2
      (`$(…)` not tracked), T1 (no length bound), P1–P7 again, P8 (no command
      after a `\n` escape), P9 (`echo` not a read) — 22 of 23 red; S2 (TAB)
      **survived** (the money pattern matched the merged text anyway) → its
      case became a secret read, which is judged by its verb → 23 of 23 red
      (`mut_cont4.out`). After moving onto the bootstrap's round 5: 102 OK
      with 664 examples (`cont2-rebased.out`), 23 of 23 red again
      (`mut_cont5.out`), and the four other repositories 102 OK each against
      their own policies (`sync2-*.out`). Evidence fixes: `cont-gate.log`
      kept as `cont-gate.out`; `multiline-before.out`'s fourth allowed
      command (`subprocess.run(["cd", …])`, a list, not a line) is not a
      line-structure case. Not fixed here, listed under Skipped items: the
      older holes the verifier found.
- [x] **Verifier, round 2: FAIL** (on 1aaa8bd; its `rn-verify8/`). Passed:
      the gate 7/7 (102, 52), 664 examples, the hashes, the eleven new tests
      red on 2075218, the four other repositories 102 OK each against their
      own policies, and the guard change alone: over about 225,000 fuzzed
      commands in each repository's policy, nothing became looser that bash
      or zsh would run. Failed: (1) **a regression in this repository** — a
      backslash at the very end of a command made `shlex` fail, so the `sh
      -c`/`eval` reading and the push check no longer saw the command, and
      the narrowed stopgap no longer asked: `sh -c 'git push --force origin
      x' \` and `eval "git push --force origin x" \` were allowed in both
      profiles, pushes to `main` in `stable` (zsh and Claude Code's Bash
      tool drop a trailing backslash and run them); (2) R8 not met: below
      16,000 characters, `eval` chains took 15–23 s through the hook and a
      117-character `git -a -a …` 21 s (`guard_base.py` has no budget, the
      `eval` checks had no time check between them, one rule backtracked);
      (3) "R7's claim now holds for every rule" was false for 15 rules
      after a `\n` escape; (4) 6 of its 13 mutants survived (G1 `<>` and G2
      `&` dropped from the word breaks, G4 the limit raised to 24,000, G7 a
      flag for nested `$(`, G9 the limit on the first line only, P1 `\\n`
      without the indentation after it); (5) evidence: the R8 timings had no
      receipt, the 22-of-23 mutant output was not kept, and §2 and the Speed
      line were stale. It also found a continuation plus a word the shell
      assembles (`docker'' \⏎restart lnd`, `git $( true ) \⏎push --force`)
      allowed where the stopgap had asked — both guards allow the same on
      one line — and older holes not listed: `|&`, and process substitution
      after `echo`.
- [x] **Round 3**, rebuilt on `main` a443085. The bootstrap's round 9
      replaced the history 1aaa8bd stood on, so 1aaa8bd's `guard.py`,
      `test_guard.py`, examples, record and evidence were carried over, and
      its policy changes ported to round 9's `guard_policy.py` (`LINE`,
      `NR`'s `(?m)\A`, `rx`'s `[\s\S]*?`, the code-string rule; round 9 had
      already rewritten the backtracking rule: `git -a`×38 now takes 0.10 s
      through the hook). One verdict in the bootstrap's baseline changed, a
      tightening (`baseline.diff`): a heredoc written to `/tmp/msg` whose
      body says `rm -rf scripts/quality/hooks` now asks, as every rule reads
      every line.
      - Tests first: red at 13:43:40 (`cont3-red.out`, 10 tests, 4
        failures: the two trailing-backslash tests, the crafted slow
        commands, the time-out test). Three tests in
        `LineContinuationRound3` pin the verifier's surviving mutants G1,
        G2, G4, G7 and G9; they pass on the code, which those mutants break.
      - R9: `split_segments` drops a backslash that ends the command.
      - R8, first design: a budget check before each policy rule, and the
        previous guard in a forked child process, stopped when the
        decision's 7 s ran out. Mutants (`mut_cont6.py`): **C5, a stopped
        child counted as allow, survived** (`mut-cont6.out`) — the time-out
        test reached the stopped child only after the new checks had timed
        out, which already gives ask. A test where the new checks finish
        late with allow: C5 red (`c5-red.out`), 7 of 7 (`mut-cont7.out`).
      - R8, measured through the real hook with the verifier's 20 slow
        commands in both profiles (`hooktime9.out`): all under 10 s, but
        `'~/'` repeated to 16,000 characters took 9.12 s — one rule's
        single search took 9.8 s on it (a first run, printed, not kept;
        10.5 s in the kept rerun, `prof3.out`, which calls the new checks
        directly, outside `decide()`'s timer, to time each rule), and a
        budget checked between rules cannot stop one search.
      - R8, final design: **a timer** (`_alarm`, `signal.setitimer`;
        Python's `re` checks for signals while it searches) stops the new
        checks at their 4 s and the previous guard at the decision's 7 s,
        even inside one search; the answer is then ask, and a deny the
        previous guard finds in time stands. Its exception is a
        `BaseException`, so no `except Exception` on the way swallows it; a
        timer that fires as it is disarmed counts as out of time (`_timed`);
        `run_hook` asks if it ever escaped. Without a timer (not the main
        thread; the hook runs in it, as observed on Linux — "and macOS"
        corrected in round 7) only the new
        checks' own budget checks bound them. Test first: one search that
        never ends gave no answer within 15 s (`cont4-red.out`); with the
        timer, ask within 3 s, in the new checks and in the previous guard.
        **The first green run found a race** (`cont4-green.out`, kept): the
        timer fired inside its own disarm — the checks' deadline is the same
        moment — and escaped `decide()` → `_timed`; 111 OK twice
        (`cont4-green1.out`, `cont4-green2.out`); tests that fire the timer
        inside its disarm every time, and for `run_hook`, written after.
        Mutants (`mut_cont8.py`, `mut-cont8.out`): 10 of 13 red; C2 (no
        budget check between rules), C3 (the previous guard always in this
        process) and T3 (the timer's exception an `Exception`) survived. The
        first two were now redundant with the timer, so the per-rule check
        and the child process were removed (less code, one mechanism); T3 is
        pinned by a test of the exception's class. And a test that new
        checks out of time never give allow, even when the previous guard
        allows (mutant N1).
      - **Said plainly — tests changed after red.** The red-time test
        `…_previous_guard_is_skipped_and_the_answer_is_ask` asserted that,
        out of time, the previous guard is not run at all. Building it
        showed that skipping it loses a deny it would have found (round 7's
        `test_round7_no_override_after_a_timeout` failed), so the previous
        guard runs, stoppable, and the test became
        `…_is_stopped_and_the_answer_is_ask`: ask within the overall budget,
        with the previous guard sleeping 30 s. And at 13:52 I dropped the
        `eval eval eval` case from `test_crafted_slow_commands_are_answered_in_time`
        without recording why; the suite was green with it (7.00 s, under
        the test's 8 s), so it bought no green. It is restored. No test or
        baseline was loosened otherwise: against `main`, `test_guard.py`
        only gains lines, the worked examples go from 807 to 830 with none
        removed or changed, and the one baseline change is the tightening
        above.
      - **Said plainly — probes ran on a mutated file.** My first runs of
        the verifier's probes and the R7 check took their copy of the tree
        while the mutants ran in it; the copy held mutant C4. They were
        rerun on copies checked with `cmp` against the restored files, and
        again on the final guard (`probe10-*.out`, `r7check10.out`); no
        verdict changed. Probes now run only on copies made while no mutant
        runs.
      - The round-2 verifier's probes through the real hook
        (`probe10-*.out`, `probe10-compare.out`; its synthetic secret
        `*.sekrit` added to the `stable` copy, as it had): the force pushes
        with a trailing backslash now deny. Still looser than 2075218 only:
        pushes to `main` in `development` (that profile allows them on one
        line), the legitimate continued reads, a CR LF (bash does not join
        it), and the assembled words, which both guards allow on one line
        (`probe10-oneline.out`).
      - Round 2's evidence points: the R8 timings now have receipts
        (`hooktime9.out` to `hooktime11.out`); the 22-of-23 run's output
        (`mut_cont3.out`) was overwritten and cannot be recovered —
        `mut_cont4.out`, the 23-of-23 run after its fix, stands; §2 and the
        Speed line are brought up to date.
      - R7 with its script (`r7check10.out`): in `development`, every
        must-ask example still asks on a script's second line and after a
        `\n` escape; in `stable`, 12 are allowed on the second line, 4 after
        a `\n` escape, and the same 12 on one line inside code — the shared
        guard's own checks (secret reads, pushes, protected paths) do not
        read program code on any line (Skipped items).
- [x] **Verifier, round 3: FAIL** (on 92c39a2; its `rn-verify34/` was lost
      with `/tmp` when the machine crashed a second time; its report is in
      the session's transcript). Passed: the gate 7/7 (115, 61, 830
      examples), the record's hashes, R1–R5, R7, the R8 time bound (70
      timings, at most 7.10 s; over 16,000 characters asks in 0.07 s), the
      pinned survivors G1, G2, G4, G7, G9 and P1, and the shared suite in
      the four other repositories. Failed: (1) **R9 only for a backslash
      that is literally last** — an escaped blank at the end (`sh -c 'git
      push --force origin x' \ `, also `\<TAB>`, and before `;`, `|`, `&&`
      or a newline) and a comment ending in a backslash (`eval "cat .env" #
      note \`) became a trailing backslash when the segment was stripped:
      allowed in both profiles, while 2075218 asked; (2) **a `#` inside a
      backtick or `$(…)` read as a comment**: its newline split the command
      inside the substitution, which was then never judged — under all five
      repositories' policies, force pushes and `.env`/`tls.key` reads that
      bash and zsh run went from deny to allow (its fuzzer and shell oracle:
      3 to 8 such commands per policy with the shared guard alone); also a
      quote in a heredoc's body swallowing the commands after it; (3) **the
      timer turned a deny the new checks had found into ask** when the
      previous guard was then stopped; (4) eight surviving mutants that are
      not equivalent (V2, V10, V16, V18, V20, V21, Q7, Q9); (5) claims: "as
      zsh and bash drop it" (bash keeps it), "the three verifier rounds'
      surviving mutants" (two had run), "the change can only make the guard
      see more" and "no path from untrusted input gains a verdict it did not
      have" (false: the record's own probes showed `docker'' \⏎restart lnd`,
      `git $( true ) \⏎push --force …` and `env git|&git \⏎push --force …`
      go from ask to allow, and its fuzzer found more); Close Out's "a
      decision out of time asks instead of being let through by the hook's
      time-out" (here, `"onFailure": "block"` made a time-out block); §2's
      numbers stale; six hashes in the Evidence log that no receipt holds;
      round 3 silent on the fix-lock.
- [x] **Round 4.** First rebuilt on `main` 0f407f3 (the bootstrap's round
      10): round 3 is now 7c77ce4 (was 92c39a2), round 4's first commit
      944fe55 (was 9768c9c). The policy is round 10's, with this change's
      multi-line reading applied to it again (`LINE`, `NR`'s `(?m)\A`,
      `rx`'s `[\s\S]*?`, the closed-world rule's `[\s\S]*`, the money rules'
      help exemptions per line, the code-string rule; in the node and
      container rule a read is the whole segment, `\Z`, not a line's end);
      AGENTS.md likewise; round 10's worked examples and this change's 23
      merged (957), and the replayed commit's message corrected (bash keeps
      a trailing backslash; two verifier rounds, not three).
      - **Tests first**: red at 17:12:03 (`r4-red.out`: 8 tests, 5
        failures — the escaped blank, the comment's backslash, a `#` inside
        a substitution, a quote in a heredoc's body, the deny lost to the
        timer; the other three pin the verifier's survivors V2, V10, V18,
        V20 and V21 and passed on the code they protect). `test_guard.py`
        at red, rebuilt exactly from 92c39a2's file and the tests as first
        written: sha256 `e17fe565…`; every change since is in
        `r4-tests-since-red.diff` and below.
      - **The fixes**: a segment keeps a blank its backslash escapes, and a
        backslash that ends a comment is dropped as the comment's text
        (`_end_segment`); a `#` opens a comment only outside a `$(…)` or a
        backtick, as the guard before this fix, and a `#` that starts a word
        inside one asks — bash may read a comment there, which the guard
        does not model; an unclosed `$(…)`'s text is judged to its last
        character (it lost one: `cat .env` became `cat .en`); a command is
        also judged without its heredoc bodies, and each body line on its
        own (`_all_segments`, only adds); a deny the new checks found in time
        stands when the previous guard is stopped.
      - **The owner's choice** (2026-10-11, asked when the merge kept round
        10's rule that asked before every continued command: "Judge as one
        line"): a command continued over lines is judged as the same
        command on one line — by the new checks, and by the previous guard,
        which `decide()` now gives the joined text (`_joined`, from the same
        scan as `split_segments`; `guard_base.py` itself is unchanged).
        Cost, as put to the owner: the forms that get through on one line
        get through continued too — `docker'' \⏎restart lnd`, `git $( true
        ) \⏎push --force …` and `env git|&git \⏎push --force …` (round 3's
        verifier) are allowed, as they are on one line (Skipped items). The
        policy's continued-line rule now fires only on a backslash-newline
        the shell keeps — inside single quotes, in program code; its comment
        and reason say so. Its tests were written after the code (the
        choice came after round 4's code): `JudgedAsOneLine`, 3 tests, all
        red on 944fe55 (`join-red.out`).
      - **Round 4's own fuzzer and shell oracle, first run** (the round-3
        verifier's tools, rebuilt; `fuzz-r4-run1.out`, `oracle-r4-run1/`),
        on the code with the join: commands bash or zsh ran that the guard
        stops when written plainly, now allowed where main's guard denied —
        under every policy, 7 to 17 per policy: (1) a lone `&` before a
        continuation (`true & \⏎git push -f origin x`): joined, the lone
        `&` hides the push, an older one-line hole, where the previous
        guard's line-by-line view had denied it; (2) zsh's `{\⏎git push
        --force \⏎origin x; }`, which zsh runs as a group; (3) **a
        regression of mine**: an escaped quote inside a `$(…)` (`$(head
        -\"c 99 .env)`) made the substitution look unclosed, and since this
        round an unclosed one keeps its last character, so the file's name
        ended in `.env)` and no longer matched. Answers: the previous guard
        also reads the command line by line, as it always did, and **a deny
        it finds there stands** — its asks there do not, as the owner chose
        (`JudgedAsOneLine`); `_balanced` reads a substitution with the
        shell's escapes, and `_substitutions` judges that reading and the
        one before it where they differ (only adds: a shared test's `cd
        "$(… \)"` escapes the `)` the shell would close on). Tests for
        these, written after the code, red on the checkpoint before it
        (`fuzz4-red.out`).
      - **Second run** (`fuzz-r4-run2.out`, `oracle-r4-run2/`): no command
        that main's guard denied and this one allows remained under the four
        other repositories' policies, but for a carriage return before the
        newline (bash passes it into the word: git is given `-f<CR>`, which it
        refuses; the round-3 verifier excluded such cases). What remained were
        asks lost to older one-line holes — most of them **a lone `&`**, which
        the guard did not read as the end of a command, so `true & git push
        -f origin x` was allowed **even on one line**. That older hole (listed
        below until now) is closed in this round: `split_segments` ends a
        command at a lone `&`, and `|&` is a pipe (`>&`, `<&`, `&>` and `2>&1`
        stay redirections). Tests first (`LoneAmpersand`, 2 tests, red at
        19:40:07, `amp-red.out`). One baseline verdict tightened, ask → deny:
        `echo x & cat <the previous checkout>/…/admin.macaroon` (the guard
        now sees the `cat` of a macaroon; `r4-baseline.diff`). This
        repository's policy keeps its lone-`&` alternative in `MORE`: the
        previous guard does not split there.
      - **Final run, and where this stopped.** The last run still found, under
        each policy, a few commands that bash or zsh runs, that main's guard
        stopped and this one does not — most of them asks lost to older
        one-line holes, a few of them denies. They were not analysed further:
        Claude's safety classifier stopped my own analysis of them twice, as
        it stopped both of round 10's verifiers in the bootstrap. The owner
        then chose (2026-10-11) to stop searching for ways past the guard: the
        guard is an early warning, the boundary is the OS sandbox (its drill,
        now possible, follows) and CI on a protected `main`. **Not yet
        proven: that this change never loses a deny main's guard gave.** The
        fuzzer (the round-3 verifier's, rebuilt from the session's
        transcript), the oracle and their outputs are kept outside the repository
        (`/home/junc/claude-wip/guard-continuation/scratch/fz/`), not
        committed: their outputs are lists of generated commands of that
        kind.
      - **Test and example changes after red**, each with its reason: (a)
        round 1's `test_what_the_shell_does_not_join` expected `echo hi #
        note \` and now `echo hi # note`: the comment's last backslash is
        its text, dropped on purpose (the split at the newline, which the
        test is about, is unchanged); (b) two cases added to round 4's tests
        (an unclosed substitution's last character; a heredoc body fed to a
        shell) — stricter, pinning mutants S1 and H2; (c) `JudgedAsOneLine`
        added — and, after the fuzzer, its capture test expects the previous
        guard to be called twice for a continued command (joined, then line
        by line, where only a deny counts), and its substitution test takes
        the shell's reading as the first of two, by design; (d) in the
        merge, `sh -c 'git push --force origin x' \` went from ask to
        **deny** (round 10's example and claim: the fixed guard
        sees the force push), and the continued reads `lncli \⏎ getinfo` and
        `docker \⏎ ps` asked while round 10's rule was kept and are allowed
        again after the owner's choice — as in round 3; (e) `LoneAmpersand`
        added, tests first, and the baseline's row 757 tightened (above); (f)
        two worked examples pin the verifier's policy survivors: Q7 (the
        previous checkout named on a script's second line) and Q9 (a payment
        in a script with `-h` on a later line), 959 examples. Q9 is equivalent
        after the merge: round 10's node rule asks for any command naming
        `lncli` that is not a listed read.
      - **Mutants** (`mut_cont10.py`, in a scratch clone, never the
        worktree): the first set, 22 (D3 removed as equivalent before it), 20
        red (`mut-cont10-first-run.out`); the final set on the final code, 32
        — with mutants of the line-by-line deny, the substitution's two
        readings and the lone `&` — 29 red (`mut-cont10.out`). The three
        green: A2 (`|&` keeps its `&`) is equivalent — the `&` left after a
        `|` ends an empty command (round 4's verifier agreed, by reading);
        V16 (the end-of-command rule also in a comment) is **not**
        equivalent, as I had written — round 4's verifier showed it changes
        the text the previous guard is given; round 5 adopts it and pins it;
        J4 (the overrides read the command as written) — I wrote "can only
        make an override rarer"; that is not shown (the secret-file override
        re-splits the raw text), so it stays an untested survivor. D3 (a
        backtick inside double quotes not tracked) was removed as equivalent
        by my reading only; it is not shown either.
      - **The four other repositories** (clean clones; `guard.py` and
        `test_guard.py` copied in; `guard_base.py` byte-identical): the
        suite OK in each, against each repository's own policy — 126 tests
        in the committed receipts, copied before round 4's last tests
        (round 4's verifier; the number corrected in round 6)
        (`sync4-*.out`; Rikuri-PI at its `origin/main` 1ea439d, Iceman
        21eac0b, AISecurity 12ff2e8, the previous rikurinode 3bbbe392).
      - **Corrections to earlier entries.** §2's numbers are brought up to
        date (above). The hashes `d66c9461…`, `ea19d761…`, `f27b20c7…`,
        `e076fc01…` and `94ada3e7…` in the Evidence log were computed and
        printed in the session at the time, not saved in a receipt; they
        cannot be shown now beyond what the commits hold. Round 3 did not
        say why the fix-lock was not engaged: the reason is round 1's — this
        session runs under Rikuri-PI's hook, which reads neither this
        repository's lock nor its paths — and the recorded hash and the diff
        since red stand in for it, here too. The claims the verifier found
        false are narrowed in Close Out and Skipped items.
- [x] **Verifier, round 4: FAIL** (review only, the owner's choice after
      the safety classifier stopped the generated-test verifiers; its
      `rn-verify38/`, persistent). Passed: the gate on 7390125 (130, 68, no
      leaks); `git diff --check`; the receipt commit; the hashes (it rebuilt
      the red test file at `e17fe565…`); AGENTS.md's numbers; each of the
      round-3 verifier's findings answered by code and a test; no test
      loosened (test_guard.py loses no line against `main`; the one changed
      expectation's reason holds); the rebased policy keeps `main`'s 39
      rules; `mut_cont10.py` 29 of 32 red as recorded; the shared suite
      passes in all four other repositories on the final code (130 each).
      Failed: §2's numbers stale; the committed `sync4-*.out` and Close Out's
      citations were not of the final code (126 tests: copied before the last
      sync, which did show 130); V16 is not equivalent; J4's and D3's
      equivalence claims are not shown; R6 ticked as "nothing lost" against
      R10; the shared `guard.py`'s docstrings still said "the new code can
      only add" and "nothing it caught can be lost"; AGENTS.md named macOS,
      which no test runs on; `r4-tests-since-red.diff` stopped before the
      last test changes. **And Rikuri-PI's `main` carries a newer shared
      guard** (another session's "notice Rust inline tests that no fix-lock
      rule covers", synced there as c72ad91 from this repository's
      unmerged branch `fix/guard-inline-tests-tripwire`): copying this
      change there would remove that work (`uncovered_inline_tests`, 16
      tests). The five copies already differ: Iceman, AISecurity, the
      previous rikurinode and this repository's `main` hold the older
      guard. Also seen: **the live node's tor container restarted** during
      its mutant run (20:49:25; lnd and bitcoin did not); `safe-run.sh`
      caught it and failed that run. The node's own `control-plane` logged
      at that second that it saw tor start; the tests run with no path to
      Docker. Cause not proven; reported to the owner.
- [x] **Round 5** (2026-10-11). Tests first: V16's behaviour pinned (a
      backslash that ends a comment at the command's end is not given to the
      previous guard either), red at 21:20:51 (`r5-red.out`), then adopted
      (`split_segments`: the end-of-command backslash is dropped in a
      comment too). The docstrings of `decide` and `base_decide`, R6,
      AGENTS.md's macOS, §2's numbers, Close Out's citations and the mutant
      claims corrected (above and below); `r4-tests-since-red.diff` replaced
      by a diff from red to round 5's test file; the final sync's receipts
      committed. Mutants (`mut_cont11.py`, round 4's set with V16 turned
      round): 32, 30 red (`mut-cont11.out`) — V16b (round 4's behaviour
      restored) red; A2 and J4 green as recorded. The shared suite in the
      four other repositories on round 5's guard: 130 OK each
      (`sync5-*.out`). Then `main` (bootstrap round 11, and round 10's
      record-only commits) was merged in (7ecc958; no conflict); on the
      merged tree the full gate passed, all 7 steps (`gate6.out`: 130 guard
      tests, 72 quality-tool tests).
- [x] **Verifier, round 5: FAIL** (review only; its `rn-verify40/`; not
      stopped). Passed: the gate on 0d50bb4 (130, 72, no leaks); `git diff
      --check`; the receipt commit; §2's numbers; V16 pinned (the test is
      red on 7390125 and green on 0d50bb4, its verdict too); the docstrings
      of `decide` and `base_decide`, AGENTS.md's timer sentence and Close
      Out's citations; the merge 7ecc958 (redone in a scratch clone: no
      conflict, the same tree); the test changes (no line lost against
      `main`; the one changed expectation's reason holds); `mut_cont11.py`
      replayed twice, row for row as committed; the shared suite in all four
      other repositories (130 each). Failed: V16 did more than stated — of a
      comment's run of two backslashes at the command's end, one was left
      for the previous guard, unstated and untested; R6 and `decide`'s
      docstring scoped the previous guard's dropped asks narrower than the
      code (its asks on a backslash that ends the command, R9, too); stale:
      round 4's `sync4` numbers ("130"; the receipts show 126), the
      Evidence log's "V16 equivalent; J4 stricter only", AGENTS.md's "934
      worked examples" (959), `_alarm`'s "Linux and macOS", a test
      comment's "the new code only adds"; J4 and "no deny lost" without a
      Skipped-items entry. Not yet proven: the five copies `cmp`-identical
      — the sync waits on the owner, as Rikuri-PI has diverged.
- [x] **The owner's choices after round 5** (2026-10-11). The stop rule:
      findings in code or tests are fixed with a test and checked again,
      findings only in wording are fixed without another check round, and
      each branch gets one final check. The sync order: the other session's
      shared-guard change (`fix/guard-rust-test-layouts`) lands first; this
      change then goes on top, and one combined guard is copied to all five.
- [x] **Round 6** (2026-10-11). Tests first: a comment's run of two, three
      and four backslashes at the command's end — the previous guard is
      given none of them (`_joined`), the new checks' segment ends at the
      comment's text, and the verdict under a rule that asks on a line end
      is allow; the denies stand with runs of two and four; outside a
      comment an escaped backslash that ends the command stays. Red at
      23:20:34 (`r6-red.out`: 1 failure, of a run of two one was left; both
      files' hashes at red), then the fix: `split_segments` drops a
      comment's whole last run, and `_joined` removes one character for each
      index, two where a newline follows (130 OK, `r6-green.out`). R6, R9,
      `decide`'s and `_alarm`'s docstrings, the test comment, §2's numbers,
      AGENTS.md's count, round 4's `sync4` numbers and the Evidence log
      corrected; J4 and "no deny lost" given Skipped-items entries. Mutants
      not rerun: the red run on round 5's code is this change's mutant. The
      shared suite in clean clones of the four other repositories on round
      6's guard: 130 OK each, the copies `cmp`-identical (`sync6-*.out`;
      the node's container start times, read before and after in the
      session, were the same — not saved in a receipt). The
      full gate on 5d4999d, all 7 steps (130, 72; `gate7.out`, in the next
      commit, which changes only it and three record lines).
- [x] **Final check, round 6 (review only; the owner's stop rule): FAIL,
      wording only** (its `rn-verify45/`; not stopped). No code or test
      finding. Passed: the gate on eaa8333 (130, 72, no leaks); `git diff
      --check`; the receipt commit; §2's numbers; the red run rebuilt (1
      failure) and green; on 4,957 distinct committed inputs (test-file
      strings, 884 worked examples, 1,070 baseline rows, 2,168 claims cases)
      only 6 outputs differ between 0d50bb4 and 5d4999d, every one a comment
      that ends the command in a run of 2 to 4 backslashes, and no worked
      example, baseline row, claims case or backslash-newline join changed;
      `_joined`'s new step changes no output by itself; the denies with
      runs of 2 to 4 stand; every finding of round 5's review answered; no
      test loosened; the four other repositories replayed (130 each).
      Failed (wording): the "no deny lost" Skipped item said no differential
      run was made — round 4's "Final run" was one, and it found a few
      denies lost, not analysed; "so no reading sees a line end" (R9, the
      docstring) and R6's "no longer given" — the previous guard's
      line-by-line reading still gets the raw text and asks there (only its
      denies count); the round-6 entry's node start times have no receipt,
      and the `sync6` receipts do not show `safe-run.sh`; Close Out cited
      `sync5`; the J4 item described the mutant, not the code. Minor: a
      126-character docstring line, `_joined`'s docstring broken mid-line,
      no word on the fix-lock, round 3's "Linux and macOS". Also: `main` has
      moved on (bootstrap rounds 12–16) past this branch's merge base.
- [x] **Round 7** (2026-10-11): wording only, no behaviour changed
      (`guard.py`: two docstrings). The "no deny lost" item now says what
      round 4's run found; R6, R9 and `split_segments`' docstring say which
      readings lose the line end and that the line-by-line one keeps it;
      Close Out cites `sync6`; the J4 item describes the code; the round-6
      entry's node times are marked unsaved, and the script that made the
      `sync6` receipts is committed (`sync6.sh`: clean clones, `cmp`, the
      suite inside `safe-run.sh`); round 3's macOS. The fix-lock was not
      engaged in rounds 6 and 7, for round 1's reason (this session runs
      under Rikuri-PI's hook, which reads neither this repository's lock nor
      its paths); the hashes at red and the diff since red stand in for it.
      `mut_cont11.py`'s J2 no longer applies to round 6's code (its target
      line changed); the set was not rerun. `sync6` was run on 5d4999d's
      `guard.py`, which round 7 changes only in docstrings; the sync reruns
      the suite anyway. The gate on 8404ed0, all 7 steps (130, 72;
      `gate8.out`, in the next commit, which changes only it and three
      record lines). No check round follows (the owner's stop rule).
- [ ] Diff matches the plan: pending the verifier.

## 5. Close Out
- [x] Full gate green: round 3's `gate3.out`/`gate4.out` (115, 61); round
      4's `gate5.out` (130, 68); round 5's `gate6.out` (130, 72); round 6's
      `gate7.out` (below).
- [x] Scrap Sweep: the probe copies, clones and working files live in the
      session's scratch folder, not the repository; the receipts and scripts
      kept here are listed in the Evidence log. Code removed in the same
      change: the forked child process and the per-rule budget check (the
      timer replaced them); the stopgap rule narrowed to program code, its
      reason rewritten. `git status`: only this change's files.
- [x] Reviewed per `REVIEW.md` (self-review; the independent review is the
      verifier, pending). Bugs: the timer's race, found by the suite, is
      pinned by a test that fires it inside its disarm. Security: the guard
      reads more of each command; a continued command is judged as its
      one-line form, so what gets through on one line gets through continued
      (the owner's choice, R10; Skipped items); a decision out of time asks
      — in the four repositories without `"onFailure": "block"` the hook's
      time-out used to let it through, in this one it used to block. Round
      3's claim that no path gains a verdict it did not have was false
      (round 3's verifier); round 4's fuzzer and shell oracle results are in
      its entry. Compliance: the diff is
      the Plan's files plus the time bound (R8, R9). **Risk note — protected
      paths changed:** `.claude/hooks/guard.py`, `test_guard.py`,
      `guard-config.json`, `scripts/quality/guard_policy.py`, the baseline
      and `AGENTS.md`. The guard is shared by five repositories: a wrong
      verdict here is a wrong verdict in all of them. Held by: the shared
      suite and each repository's own examples in all five (round 6's
      `sync6-*.out`, made by `sync6.sh`),
      `guard_base.py` unchanged beside it, the mutant sets, and the verifier.
      **Defaults chosen for the owner** (each asks, never allows; each one
      constant): a command over 16,000 characters asks; a decision over 7 s
      asks. Cost: a long inline script, or a long command that is slow to
      check, needs your approval (write it to a file instead) — and it is
      asked, not denied, even when it holds what the guard would deny: a
      command over 16,000 characters is not checked at all, and a deny is
      kept only when the new checks found it in time.
- [x] Lesson loop: (1) a budget checked between steps cannot stop one slow
      step — the timer, with a test whose single search never ends; (2) a
      timer and a deadline set for the same moment race — a test fires the
      timer inside its disarm every time; (3) probes must not read a tree
      that mutants are rewriting — said plainly above, and now done on
      copies checked with `cmp`; (4) every change to a test after red is
      recorded when it is made — the dropped case, found only by reading
      the session back, is restored; (5) round 4: a change to the guard's
      tokenizer is differentially tested against real bash and zsh in the
      same round, not only by the verifier — round 4's own run found three
      problems, one of them its own regression; (6) a search for ways past
      the guard is stopped by Claude's safety classifier, so the guard's
      completeness cannot be established that way: the boundary has to be
      one that does not read command text (the OS sandbox).
- [x] Knowledge layer: `AGENTS.md` (the time bound and its defaults;
      continued lines; program code, which the shared guard's own checks do
      not read; assembled words); the guard's own comments. No README or
      runbook text describes the guard's limits.
- [x] Commit message explains why; record committed with the change (the four sync commits follow the verifier)

## Skipped items — visible, never silent
- **Holes older than this change** (verifiers, rounds 1 and 2, in both the
  previous and the new guard): ANSI-C quoting (`$'…'`) read as a plain
  quote; a `"` inside `'…'` inside `$(…)` inside `"…"`; an apostrophe in an
  unquoted heredoc body opening a "quote" (round 4 judges the lines after a
  heredoc on their own, too); process substitution after an exempt `echo`
  (`echo <(…)`, `echo x > >(…)`); a word the shell assembles (`docker''
  restart lnd`, `git $( true ) push --force origin x` are allowed on one
  line); zsh's `{` before a continued line, which zsh runs as a group (`{\⏎git
  push origin main; }` asks no more: the previous guard's line-by-line view
  keeps only its denies). Closed in round 4: a lone `&` and `|&`. They are the same class —
  the tokenizer disagreeing with the shell — and get their own change, tests
  first, so this one stays reviewable. Since round 4 they also apply to a
  command continued over lines, which is judged as its one-line form (the
  owner's choice, R10): `docker'' \⏎restart lnd`, `git $( true )
  \⏎push --force origin x` and `env git|&git \⏎push --force origin x` are
  allowed, as they are on one line; this repository's policy used to ask
  before every continued command. Owner: Henry. Reactivate: the next guard
  change (recommended: next).
- **The shared guard does not read program code** (older; round 3's R7
  rerun): `python3 -c 'subprocess.run("cat .env", shell=True)'`, a force
  push or a protected-path delete written inside a code string get through
  its own checks, on any line; this repository's policy rules read every
  line of such code, so its money, node, container and system rules still
  ask. Owner: Henry. Reactivate: with the holes above.
- **J4, an untested survivor** (round 4's mutants): the two overrides
  are given the joined command (`_overridable(r, base_event, …)`); the
  mutant that gives them the command as written instead turns no test red,
  so which of the two they read is held by no test (the secret-file
  override also re-splits the raw text). Owner: Henry. Reactivate: the next
  change to the overrides or to `_joined`.
- **A few denies of `main`'s guard are lost, not analysed** (R6; round 4's
  "Final run"). The previous guard is given the joined command and each of
  its lines, and only its asks are dropped there; but round 4's last run
  against `main`'s guard, on generated commands, found under each policy a
  few that `main`'s guard denied and this one does not. They were not
  analysed: Claude's safety classifier stopped that analysis twice, and the
  owner then chose (2026-10-11) to stop searching for ways past the guard —
  the guard is an early warning; the boundary is the OS sandbox (its drill
  still Not yet proven) and CI on a protected `main`. No such run since; the
  generated commands are kept outside the repository
  (`/home/junc/claude-wip/guard-continuation/scratch/fz/`). Owner: Henry.
  Reactivate: before the sync to the five repositories — the owner's
  decision, with the sandbox drill's result (recommended: the drill passes
  first); or a deny seen lost in practice.
- **Commands longer than 16,000 characters ask** (R8): a long script run
  inline needs the owner's approval; writing it to a file first does not.
  Reversible: one constant. Owner: Henry.
- **A long command that is slow to check asks** (R8): about 16,000
  characters of `git ` or `~/` take the whole 7 s and ask (`hooktime10.out`);
  this repository's slowest rules on such text are the pre-commit rule and
  the previous-checkout write rule (10.5 s and 6.5 s in one search,
  `prof3.out`). Reversible: making those rules faster on long text. Owner:
  Henry. Reactivate: when a real command hits it.

## Evidence log
Files in `evidence/2026-10-11-guard-line-continuation/`: the outputs as
written, with trailing spaces removed (the whitespace gate) and, from round 3,
the scratch folder's path shortened to `<scratch>`; the mutation scripts; and
the round-2 verifier's probe scripts and case files that round 3 reran
(`probe9h.py` is its `probe8.py` and `hooktime9.py` its `hooktime8.py`,
unchanged; `r7check9.py` is its `r7check8.py`, changed to take a folder and a
profile; `cases-*.json` are its case files; `cmp9.py` compares two guards'
verdicts). A receipt without a hash in it ran on the guard of its step below.
```
before   cont-before.out: 7 of 8 continued commands allowed by the unmodified guard
         multiline-before.out: 3 commands on a script's second line allowed by this policy (a 4th
         allowed probe passes `cd` as a list item: not a line-structure case)
red      02:23:49 cont-red.out: LineContinuation 3 failures, 1 error; test_guard.py d66c9461…
green    02:24:51 cont-green.out: 95 OK, test_guard.py unchanged
siblings cont-siblings.out (old vs new); cont-oldguard.out: all 6 LineContinuation tests red on the old guard
mutants  mut_cont.out 6/8 red → comment-boundary test → mut_cont2.out 8/8 red
policy   cont-policy.out 97 OK with 608 examples; mut_policy.out 6/6 red; multiline-after.out
gate     cont-gate.out: FAIL — the 609th example (ssh) wrapped in subprocess.run("…") was allowed
policy   LINE; mut_policy2.out 6/7 (P6 survived) → example → mut_policy3.out 7/7 red
final    cont-policy4.out 97 OK, 611 examples; guard.py f27b20c7…, test_guard.py e076fc01…
sync     sync-{Rikuri-PI,Iceman,AISecurity,old-rikurinode}.out: 97 OK each, own policy
         verifier round 1: FAIL — `#` after an escaped char or $(…) read as a comment; S1-S3 survived;
         \n escape not a line start for every rule; 14 s on 69 KB
round 2  red 04:52:37 (cont2-red.out), green 04:53:59 102 OK; policy red 04:54:27, green 04:54:58
         mutants 22/23 → S2 case strengthened → 23/23 (mut_cont3.py, mut_cont4.out)
         rebased on bootstrap round 5: 102 OK, 664 examples (cont2-rebased.out); 23/23 (mut_cont5.out)
         sync2-{Rikuri-PI,Iceman,AISecurity,old-rikurinode}.out: 102 OK each, own policy
         final: guard.py 4a04d288…, test_guard.py 94ada3e7…
         verifier round 2: FAIL — a trailing backslash let force pushes through; 15-23 s below
         16,000 characters; R7 false for 15 rules after a \n escape; 6 of its 13 mutants survived
round 3  on main a443085; red 13:43:40 (cont3-red.out): 10 tests, 4 failures; baseline.diff: 1 tightening
         first design (per-rule check, previous guard in a child; guard.py 91bf2dd2…):
         mut_cont6.py → mut-cont6.out 6/7 (C5 survived) → test: c5-red.out, c5-green.out → mut-cont7.out 7/7
         probe9-*.out, r7check9.out (clean copies), hooktime9.out: slowest 9.12 s ('~/' to 16,000)
         prof3.py → prof3.out: one rule's single search 10.5 s
         the timer: cont4-red.out (no answer within 15 s); cont4-green.out: 1 error, the race (guard.py
         56804be5…) → _timed: cont4-green1.out, cont4-green2.out 111 OK (19e5c6e8…); hooktime10.out <= 7.11 s
         mut_cont8.py → mut-cont8.out 10/13 (C2, C3, T3 survived) → per-rule check and child removed
final    guard.py 9271baee…: cont5-green1.out, cont5-green2.out 114 OK (test_guard.py c85447f1…);
         + the N1 test (test_guard.py f3512e8a…): mut_cont9.py → mut-cont9.out 12/12 red
         probe10-*.out, r7check10.out: same verdicts as probe9/r7check9; hooktime11.out: all 40 <= 7.10 s
         sync3-{Rikuri-PI,Iceman,AISecurity,old-rikurinode}.out: 115 OK each, own policy
         gate3.out: full gate 7/7 (guard 115 OK, quality 61 OK); gate4.out: the same after this record's last edit
         verifier round 3: FAIL — escaped blank / comment backslash / `#` in a substitution looser than before;
         a deny lost to the timer; 8 surviving mutants; claims wider than shown
round 4  rebased onto main 0f407f3 (round 3 = 7c77ce4); red 17:12:03 (r4-red.out): 8 tests, 5 failures;
         test_guard.py at red e17fe565… (rebuilt), every change since: r4-tests-since-red.diff
         the owner's "Judge as one line": JudgedAsOneLine, red on 944fe55 (join-red.out)
         round 4's fuzzer and shell oracle (not committed; kept in the working folder): line-by-line deny,
         shell escapes, both readings — red on the checkpoint before (fuzz4-red.out)
         the lone &: LoneAmpersand red 19:40:07 (amp-red.out); baseline row 757 ask -> deny (r4-baseline.diff)
         mutants: mut_cont10.py → mut-cont10-first-run.out 20/22 → final mut-cont10.out 29/32 (A2
         equivalent; V16 not equivalent, adopted in round 5; J4 an untested survivor — corrected in round 6)
         sync4-{Rikuri-PI,Iceman,AISecurity,old-rikurinode}.out: 126 OK each, own policy (copied before
         round 4's last tests; corrected in round 6)
         gate5.out: full gate 7/7 on 517e385 (guard 130 OK, quality 68 OK), added in the next commit
         verifier round 4 (review only): FAIL — stale receipts and counts, V16 not equivalent, wider claims;
         Rikuri-PI carries a newer shared guard
round 5  V16 pinned: r5-red.out (red 21:20:51); mut_cont11.py → mut-cont11.out 30/32 (A2, J4 as recorded);
         sync5-{Rikuri-PI,Iceman,AISecurity,old-rikurinode}.out: 130 OK each, own policy
         main merged in (7ecc958); gate6.out: full gate 7/7 on it (guard 130 OK, quality 72 OK)
         verifier round 5 (review only): FAIL — V16 also cut a comment's run of two to one, unstated, untested;
         R6 and decide's docstring narrower than the code; stale numbers and comments
round 6  a comment's whole last run dropped: r6-red.out (red 23:20:34, 1 failure), r6-green.out (130 OK);
         sync6-{Rikuri-PI,Iceman,AISecurity,old-rikurinode}.out: 130 OK each, own policy, cmp-identical;
         gate7.out: full gate 7/7 on 5d4999d (guard 130 OK, quality 72 OK), added in the next commit
         final check (review only): FAIL, wording only — "no differential run" (round 4's was one, a few
         denies lost); "no reading sees a line end"; unsaved node times; sync5 cited; J4 described as mutated
round 7  wording only; sync6.sh committed; gate8.out: full gate 7/7 on 8404ed0 (guard 130 OK, quality 72 OK);
         no check round (the owner's stop rule)
```
