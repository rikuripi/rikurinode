# Build Record — The fix-lock covers Rust test modules kept in their own file, and files that start `#![cfg(test)]`

| | |
|---|---|
| **Date** | 2026-10-11 to 2026-10-12 |
| **Author / session** | Claude Code (Opus 5.5) for Henry Chen; a side session of a Rikuri-PI session (worktree `sad-moore-14776b`) |
| **Branch** | `fix/guard-rust-test-layouts`, on `fix/guard-inline-tests-tripwire` (`aa51a24`, the committed tripwire, not yet in `main`), in its own worktree under `~/claude-wip/guard-rust-test-layouts/` (owner's choice after the crash, below); the main checkout is untouched |
| **Commits** | `6410bb4` (rounds 1–4; owner, 2026-10-11: "let's commit and continue tomorrow"), `86db3e9` (round 5; owner, 2026-10-12: "commit and push") and the round-6 commit that follows them, on `fix/guard-rust-test-layouts`, pushed; Rikuri-PI's sync `7103ec5`, `dc7e327` and its round-6 commit on `fix/guard-rust-test-layouts-sync`, pushed |
| **Status** | Round 6 (the owner's recalibration after verifier round 3) built, tested, committed and pushed here and in Rikuri-PI; verifier round 4 next; PRs and merges are the owner's call |
| **Change type** | fix (two gaps the inline-test tripwire's verifier found) |

## 0. Intent — the owner's words, approved before design
- [x] Problem (as the owner would say it): the fix-lock keeps Rust tests
      read-only only where a file holds a `#[cfg(test)]` line. Two layouts
      escape it, and the tripwire of `2026-10-11-guard-inline-tests-tripwire.md`
      (its Skipped) does not flag them: (1) a tests-only file declared from
      its parent with `#[cfg(test)] mod tests;` (`src/tests.rs`,
      `src/foo/tests.rs`), which holds no marker; (2) a file that starts with
      the inner attribute `#![cfg(test)]`, which no repository's `starts_at`
      matches. Under a lock, an Edit to either is allowed
      (`gap_probe_before.out`).
- [x] Outcome: under the fix-lock, (1) the guard follows `mod x;`
      declarations made under `cfg(test)` and refuses edits to the file they
      name, and (2) a file that starts `#![cfg(test)]` is test code from that
      line; the tripwire (`uncovered_inline_tests`, its test and
      `fix-lock on`) names any such file the lock would still miss.
- [x] Who/what it affects: the shared `guard.py` and `test_guard.py` in this
      repository and Rikuri-PI, Rikuri-PI's `inline_tests` rule and its
      `_inline_tests_doc`, and Rikuri-PI's `.claude/settings.json` (its guard
      hook blocks when it fails, round 6). **Scope narrowed by the owner, 2026-10-11:** "Just
      those 2 repo for shared code" — rikurinode, AISecurity and Iceman are
      not synced now (AISecurity and OpenShell are security tools to consult
      later). Until a later sync those three keep the previous shared files,
      though the owner's global CLAUDE.md and `guard.py`'s header say the
      files are identical in all five (Skipped). This repository tracks no
      `.rs` and has no rule.
- [x] Open questions — answered by the owner, 2026-10-11 (this session):
      - Test-module files: **1(a) the guard follows the declaration** (not a
        per-repository `test_globs` convention; not "tripwire only"). A
        `mod x;` under `#[cfg(test)]` makes `x.rs`, `x/mod.rs` and any
        `#[path]` target read-only under the lock.
      - `#![cfg(test)]`: **2(a) widen both** — each Rust repository's rule
        and the tripwire's marker (not the marker only).
      - Predecessors not landed when the work began: **stack now**; nothing
        is committed without the owner. Where it starts:
        **rikuripi/rikurinode**.
      - After the PC crash: **a persistent folder** outside every repository,
        `~/claude-wip/guard-rust-test-layouts/`, deleted at close-out.
      - Verifier round 1, D3: **"Lock both places"** (below, R3).
      - Scope: **Rikuri-PI and rikuripi/rikurinode only** (above).
      - Stop rule, as the owner set for E1: the first verifier round with no
        Critical or Important finding ends this change; Minor findings become
        documented limits (proposed in this session, 2026-10-11; the owner
        asked to finish under it).
      - After verifier round 3, **"Recalibrate, then finish"** (2026-10-12):
        anything that stalls the hook stays Important; a deliberate
        multi-step evasion counts as Minor and is documented — the guard's
        own model is "a tripwire, not a wall"; Rikuri-PI's hook gets
        `"onFailure": "block"`, so a stall closes the gate; the older rule's
        slow patterns (round 3, I5) go to their own change.
- [x] Owner approved the intent: "Us 1 (a) and 2 (a)"; "Stack now
      (Recommended)"; "rikuripi/rikurinode (Recommended)"; "Persistent
      folder (Recommended)"; "Lock both places (Recommended)"; "We can finish
      this"; "Just those 2 repo for shared code" (2026-10-11); "Ok, commit and push. Conti.
      with round 5"; "Recalibrate, then finish (Recommended)" (2026-10-12).

## 0b. Spec — requirements + design, policy applied up front
- [x] Requirements:
      - R1 Under the fix-lock, an Edit, MultiEdit or Write to a file that an
        `inline_tests` rule's glob names is refused when the file is a
        **test module**: some Rust file declares it with a `mod NAME;` item
        that is test code there.
      - R2 A declaration is test code when an attribute that applies to it
        matches the `starts_at` of a rule naming the declaring file — its
        own outer attributes, those of an inline module or other block
        around it, or an inner attribute (`#![…]`) of the file or of a module
        around it — or when the declaring file is itself a test module (so a
        test module's own `mod fixtures;` is test code too). A production
        `mod b;` stays editable wherever it sits, also below a test marker.
      - R3 The places rustc may read a declaration's file from are all locked,
        existing or not: a `#[path = "p"]` on a declaration at file level
        names `p` beside the declaring file; otherwise `NAME.rs` and
        `NAME/mod.rs`, under the inline modules around the declaration (an
        inline module's `#[path]`, or the `#![path]` inside it, replaces its
        name), from the declaring file's folder for `mod.rs`, `lib.rs` and
        `main.rs`, and for any other file from both the folder named after it
        (a module) and its own folder (a crate root such as
        `src/bin/tool.rs`, or a file loaded by `#[path]`) — the guard cannot
        tell which without Cargo.toml. (Verifier round 1, D3, owner's choice
        "Lock both places": choosing by which file exists let a locked
        session write a decoy in one place to unlock the other. Cost: a
        production file that shares a test module's name in the other place
        is read-only too while a lock is held.)
      - R4 Comments, strings (also raw, byte and C strings) and character
        literals are not code: a `mod x;`, a brace or an attribute inside
        them changes nothing. A lifetime (`'a`) is not a character literal.
        Block comments nest, as in rustc. A comment or string never closed
        runs to the end of the file, as rustc reads it.
      - R5 The declaring file is looked for in the edited file's folder and
        every folder above it up to the repository root — where rustc's own
        lookup comes from, except a `#[path]` that climbs out with `..`. It
        reads the working tree (untracked files count; no git needed). A file
        there that cannot be read as UTF-8 is skipped (rustc cannot compile
        it either; the tripwire names a tracked one). A folder that cannot be
        listed refuses the edit.
      - R6 A file starting with the inner attribute `#![cfg(test)]` (spaces
        allowed between `#`, `!` and `[`) holds tests: the tripwire's marker
        matches it, and Rikuri-PI's rule (starts_at and attached_above) takes
        `#!` as well as `#`, so the whole file is read-only and an attribute
        added above it (`#![cfg(any())]`, which switches the file off)
        changes the tests.
      - R7 The tripwire (`uncovered_inline_tests`) also names: (a) a tracked
        test module (found with the generic marker, from tracked files) that
        the lock does not protect — no rule's glob names it (a shell write to
        it would not be refused), R1–R5 do not find it (a `#[path]` with `..`,
        a rule that does not recognise the declaration), or the lookup fails;
        (b) a tracked file with a test declaration whose module file exists
        in none of its places. Untracked files still do not count.
      - R8 Every rule a repository configures for `.rs` files finds the
        tests of a file that starts `#![cfg(test)]`, the attributes and doc
        comments above it included.
      - R9 `fix-lock on`'s warning and the generic test's message cover the
        new cases.
      - R10 (verifier round 1, D2) A declaration is the word `mod`, a name
        and `;` (`{` for an inline module) with nothing between them but
        comments and Rust's whitespace — which includes U+200E, U+200F,
        U+2028 and U+0085, unlike Python's `\s` (`mod /* c */ tests;`). A
        `mod $n;` in a macro's pattern is not one.
      - R11 (verifier round 1, D4) Under the lock, an edit to a Rust file may
        not remove or change (its attributes included) the `mod` declaration
        of a module whose file is tests as a whole: one of that file's own
        inner attributes — any outside a block, wherever it stands — matches
        the starts_at of a rule naming that file (`#![cfg(test)]`). Deleting
        `mod whole;` or adding `#[cfg(any())]` above it switched every test
        in it off. (Round 2, F2: the first form compared the file's whole
        text with its locked region, so an allowed blank line at its top
        unlocked the declaration. Round 3, I4: an item written above
        `#![cfg(test)]` — rustc then rejects the file — made it look partly
        code; every inner attribute outside a block now counts.)
      - R12 (verifier round 1, D1; round 2, F1) The lookup reads each file
        once, in time that grows with its length, and keeps to the guard's
        check budget (4 s): past it the hook asks the owner. No pattern puts
        two `\s*` side by side (`#\s*!?\s*\[`): their time grows with the
        square of a run of spaces inside a single regex call, where no
        deadline can stop it — the scanner's attribute and path patterns, the
        tripwire's marker, and every Rust rule's patterns (a generic test
        checks the repository's own against runs of spaces). Each attribute
        is kept once, at most 256 distinct ones apply to a declaration — past
        that it counts as test code, the safe side — and each is matched
        against the rules once. (40,000 unclosed `/*` took 16 s; a file of
        `#` and 120,000 spaces held a locked edit 13.6 s, a crafted edit
        27 s; 2,000 attributes on each of 2,000 declarations 13.7 s — all past
        the hook's 10 s limit.) Other slow inputs of the rule's older
        patterns (round 3, I5) are split into their own change.
      - R13 (owner, 2026-10-12) Every guard hook blocks when it fails or runs
        out of time (`"onFailure": "block"`, Claude Code 2.1.295 or later): a
        stalled guard closes the gate instead of opening it. A generic test
        reads the repository's own settings.
- [x] Design: a token scanner, `rust_file_modules(text, deadline)`, steps
      over comments (nested, `rust_comment_end`), strings and characters, and
      reads words, attributes (`rust_attr_end`) and braces; a small state
      machine finds
      `mod` + name + `;`/`{` with only Rust's whitespace or comments between
      (R10). `module_files()` gives the places rustc may use (R3);
      `test_modules(root, files, is_test, deadline)` closes over a set of
      files and maps each place to its declaring file and every place of
      that declaration. `test_module_parent(rel, root, cfg, deadline)` is the
      enforcement (R1, R5), called from `inline_edit_hit`, which then checks
      R11 with `test_file_declarations()` — reading each module file's own
      inner attributes with `rust_file_attrs()` — before the in-file region
      check. In-scope attributes are deduplicated and capped
      (`RUST_MAX_ATTRS`, `RUST_TOO_MANY`); each distinct one is matched once
      per file.
      The tripwire calls the same `test_module_parent` for every test module
      it finds, so the two cannot disagree about what is covered.
      Alternatives rejected: everything below the first test marker counts
      as test code (it would lock production modules declared below a test
      module); a full scan of every `.rs` file on each locked edit (git or a
      tree walk per Edit, to reach only `#[path = "../…"]`, which the
      tripwire names instead); Cargo.toml parsing to know crate roots (Python
      3.9 has no TOML reader, and the owner chose to lock both places
      instead); a per-repository `test_globs` convention (owner chose 1(a)).
- [x] Policy applied: the hook can only add denies, only under a held
      fix-lock, and only for files an `inline_tests` glob already names.
      Behaviour choices put to the owner: 1(a), 2(a), D3, the round-3
      recalibration. Limits are listed under Skipped, each marked "named by
      the tripwire" or "silent".
- [x] Flagged concerns resolved: stacked on unlanded changes, routed to the
      owner; they moved during the work (§3).

## 1. Plan
- [x] One-sentence statement: the fix-lock follows `mod x;` declarations made
      under `cfg(test)`, treats `#![cfg(test)]` as a test marker and locks such
      a file's declaration, and the tripwire names any Rust test module or
      inner-attribute file the lock would miss.
- [x] Blast radius: `.claude/hooks/guard.py` (scanner, resolution,
      enforcement inside `inline_edit_hit`, the tripwire, the `fix-lock on`
      wording, the header) and `.claude/hooks/test_guard.py` in this
      repository and Rikuri-PI; Rikuri-PI's `inline_tests` rule and
      `_inline_tests_doc`. No funds, auth or exec path; nothing irreversible.
      Bash verdicts do not change: a shell write to any file an
      `inline_tests` glob names was already refused (verifier round 1: 2,058
      Bash, Read and Grep decisions, old guard against new, 0 differ).
- [x] Current behavior characterized: the committed tripwire passes, 107 OK
      (`base.out`). `gap_probe_before.out`: with Rikuri-PI's rule and the
      lock held, an Edit inside `src/tests.rs` (declared
      `#[cfg(test)] mod tests;`) is allowed, an Edit inside a file starting
      `#![cfg(test)]` is allowed, adding `#![cfg(any())]` above it is allowed,
      and the tripwire finds nothing.
- [x] Files and order: this record → tests (red) → `guard.py` (green) →
      mutants → Rikuri-PI's clone with its rule change → Python 3.9 → the
      full gates on committed copies → verifier → Rikuri-PI's sync record.
- [x] Risks: a scanner mistake (a brace in a literal) misplaces a
      declaration — R4/R10 tests and a corpus probe; locked edits read a few
      more files — measured, and bounded by the check budget (R12); the copy
      to Rikuri-PI — `cmp`.
- [x] Verification defined up front — I will know this works when: the new
      tests fail on the committed tripwire and pass with the change; mutants
      of each requirement are caught; both repositories pass with their own
      policies on Python 3.14 and 3.9.25; the files are byte-identical; the
      gap probe flips to deny; the verifier passes under the stop rule.

## 2. Build
- [x] New code meets the bar: `rust_file_modules` reads text only (no code
      runs); every loop advances (each token is at least one character; a
      comment or attribute ends at its closer or at the file's end); every
      token checks the deadline (R12), and no pattern puts two `\s*` side by
      side. `test_module_parent` raises `OSError` only when a folder cannot
      be listed, which `inline_edit_hit` turns into a deny and the tripwire
      into "uncovered"; `_TooSlow` becomes the hook's "ask". Measured cost of
      a locked Edit's decision on Rikuri-PI's 56 tracked `.rs` files: mean
      6.3 ms, worst 42 ms (`real_repos_probe.out`); the crafted files and
      edits of D1, F1 and I1 are decided well inside their tests' 4 s (the
      verifier's I1 reproducer through the real hook: 0.07–0.10 s, at 3,000
      attributes × 3,000 declarations too). guard.py is 2,296 lines
      (`aa51a24`: 1,978; +332/−14); it is one file shared across
      repositories, reviewed as one unit.
- [x] Clean as you go: the old warning text and marker are replaced, not
      kept beside the new ones; round 4 replaced rounds 1–3's regex-only
      declaration matcher and the "first place that exists" choice, and
      round 5 the region-equality test of R11, round 6 its "before the first
      item" boundary, instead of adding beside
      them; `guard_base.py` (the frozen previous guard) is unchanged, as it
      must stay identical.
- [x] Security question: touches no auth / money / exec / private data. It
      tightens an AI-session tripwire under a held fix-lock only; no new deny
      fires without one (verifier rounds 1 and 2, through the real hook
      process).

## 3. Debug
- [x] Reproduced before fixing: `gap_probe_before.out` (above).
- [x] Failing tests written and SEEN failing, then the fix, in rounds (the
      first rounds' evidence files were lost in the crash, below; their
      figures are from this session's transcript, which printed each run;
      verifier round 1 checked them against it):
      - Round 1, on the tripwire's then-uncommitted files (with line
        continuation): red 1 at 14:38 (135 run, 11 failures, 2 errors;
        test_guard.py `d56751cd…`). Two failures were the tests' own: in
        `TestModuleFiles` the repository's `test_globs` (`*/tests/*`,
        `*/fixtures/*`) denied some fixture paths by name, so a deny came
        from the wrong mechanism, and the "production edit" appended a
        comment at the file's end — inside the file's own in-file test
        region, which the existing rule rightly refuses. Changed before any
        guard code (reasons, nothing loosened): the class runs with
        `test_globs` emptied, and its changes prepend the comment above the
        first line. Red 2 at 14:43 (12 failures and errors, every one the
        missing feature; `4e823c3c…`). Green at 14:50 with test_guard.py
        unchanged (135 OK; guard.py `54cdb411…`).
      - Round 2: a corpus probe found an inline module that names its folder
        from inside, `#![path]` (cargo-mutants' fixture of the Rust
        reference). Red at 15:00 (1 failure; `22877c94…`); fix; green at
        15:01 with test_guard.py unchanged (136 OK; guard.py `fbdf108e…`).
      - Restack, 15:15: the owner committed the tripwire as `aa51a24`
        directly on this repository's `main` root, without line continuation
        (another session reworked that as `92c39a2`). This change needs only
        the tripwire, so it moved onto `aa51a24`: the same diff, applied with
        offsets only. Red there (125 run, 13 failing), green 125 OK.
      - Round 3, tests for the ten round-1 mutants that survived: all
        additions or a stricter fixture, nothing loosened. Green at 15:19,
        128 OK (guard.py `27f9a272…`, test_guard.py `e3893aca…`).
      - **PC crash, 15:21** (the boot log's last entry): `/tmp`, which held
        this work (uncommitted, as the owner asked), was cleared. Rebuilt from
        this session's transcript in `~/claude-wip/…` (owner's choice): both
        files came back byte-identical (`27f9a272…`, `e3893aca…`), and every
        check was run again on them: red on `aa51a24`'s guard.py at 17:11
        (`red.out`: 128 run, 12 failures, 4 errors); green at 17:11
        (`green.out`, 128 OK). An orderly reboot followed at 18:43; nothing
        of this work was lost or running.
      - **Verifier round 1: FAIL** (report summarized in §4): D1 hook time
        past 10 s; D2 declarations split by comments or Rust whitespace; D3 a
        decoy flips the place; D4 a `#![cfg(test)]` file switched off from
        its parent; D5 a false "none is silent" claim; D6 sync records
        claiming review; D7 six surviving mutants of its own; nits.
      - **Round 4**, tests first. Red 1 at 21:49 (`round4-red1.out`: 134 run,
        6 failures, 1 error). The error was the test's own: on `aa51a24`,
        `test_guard.py` has no module-level `import time` (only the
        line-continuation version added one); the timing test imports it
        locally, as the file's other timing test does. Red 2 at 21:58
        (`round4-red2.out`: 7 failures, every one the missing behaviour —
        the crafted-file test took 54.8 s against its 4 s limit). Green at
        22:12 with test_guard.py unchanged (134 OK; guard.py `5a1f0136…`).
        After green: two assertions added for mutants (a file with code and
        tests keeps its declaration editable, the documented boundary; an
        unclosed plain string runs to the end) and the R11 check simplified
        (code only; it compared counts that valid Rust never repeats);
        134 OK (`round4-green.out`, guard.py `553f5f37…`, test_guard.py
        `ccd5cb4b…`). Every other test_guard.py change in round 4 is an
        addition or a fixture extension, except: `src/fixtures.rs` moved from
        the "stays editable" list to the "locked" one, by the owner's D3
        choice (R3's cost), and `test_production_modules_stay_open`'s comment
        lost the clause about it.
      - **Verifier round 2: FAIL** (2026-10-11, after the round-4 commit;
        summary in §4): two Important findings. F1: `#\s*!?\s*\[` — in the
        scanner, the tripwire's marker, the path pattern and Rikuri-PI's
        widened rule — backtracks with the square of a run of spaces inside
        one regex call, where no deadline can stop it: a crafted file held a
        locked edit 13.6 s, a crafted edit 27 s, and Rikuri-PI lets a
        timed-out call through. F2: a blank line added at the top of a
        `#![cfg(test)]` file (allowed: its region does not change) made
        R11's region-equality test fail, and the declaration could then be
        deleted. Nine Minor findings, M1–M9.
      - **Round 5**, 2026-10-12, tests first. Red at 14:02
        (`round5-red.out`: 138 run, 4 failures — the tripwire took 61.7 s on
        a crafted file, a locked edit 36.7 s, the scanner 3.1 s on one line
        of spaces, and the F2 bypass was allowed; test_guard.py
        `c975020c…`). Rikuri-PI's red (`round5-red-Rikuri-PI.out`): its rule
        as committed in `7103ec5` fails the new generic linear-time test
        (`starts_at`, 1.47 s). Fix: the linear form `#\s*(?:!\s*)?\[`
        everywhere (and in Rikuri-PI's `guarded_lines`, whose `\s*!?\s*\(`
        predates this change: the generic test found it, 1.31 s); R11 reads
        the module file's own inner attributes (`rust_file_attrs`). Green
        at 14:04 with test_guard.py unchanged (138 OK; guard.py
        `98e5584c…`). After green, each with its reason, nothing loosened:
        three assertions added so that three new mutants are caught (a line
        comment and a byte-order mark above `#![cfg(test)]`; an outer
        `#[cfg(test)]` on a production file's first item does not make the
        file all tests); and guard.py's byte-order-mark literal rewritten as
        the escape text `\ufeff` — the Edit tool had written the invisible
        character itself (no behaviour change). 138 OK (`round5-green.out`,
        guard.py `6531423f…`, test_guard.py `0825965e…`). The fixture rule's
        three regex lines in test_guard.py are in the linear form too (same
        matches); the generic test guards the repository's own rule.
      - **Verifier round 3: FAIL** (2026-10-12; summary in §4): F1 and F2
        fixed, everything else PASS, but five Important findings: I1, my
        regression — one allowed locked Write of a production file with
        2,000 inner attributes and 2,000 `mod` lines made every later locked
        edit take 13–14 s (the fixpoint matched every attribute of every
        declaration on every pass, with no deadline); I2–I4, deliberate
        multi-step evasions (an opener `/*` added above a parent's code
        while its test module is edited; a declaration wrapped in a
        never-expanded `macro_rules!`; an item written above `#![cfg(test)]`,
        then the declaration deleted); I5, the rule's older patterns still
        super-linear on other inputs (16–18 s; the old guard the same).
      - **The owner's recalibration** (2026-10-12, "Recalibrate, then
        finish"): stalls stay Important; deliberate multi-step evasions are
        Minor and documented; Rikuri-PI's hook gets `"onFailure": "block"`;
        I5 goes to its own change (proposed as a separate session).
      - **Round 6**, tests first. Red at 16:15 (`round6-red.out`: 141 run,
        3 failures — the I1 file took 41.4 s, the 256-attribute cap absent,
        the I4 evasion allowed; test_guard.py `afe8dcde…`). Rikuri-PI's red
        (`round6-red-Rikuri-PI.out`): the new generic test finds its guard
        hook without `"onFailure": "block"`. Fix: attributes kept once and
        capped in scope, each matched once, the fixpoint on the deadline;
        R11 counts every inner attribute outside a block; Rikuri-PI's
        settings block on failure. Green at 16:17 with test_guard.py
        unchanged (141 OK; guard.py `c884a868…`); the verifier's I1 and I4
        reproducers through the real hook: 0.07–0.10 s, and the declaration
        stays locked. After green, four assertions added so that new mutants
        are caught (a comment holding a brace above `#![cfg(test)]`; an
        inner attribute inside a block is not the file's; a repeated
        attribute counts once; a closed block's or a declared item's
        attributes leave the scope), nothing loosened: 141 OK
        (`round6-green.out`, test_guard.py `ecad50c1…`).
      The fix-lock was not engaged: this session's hook is Rikuri-PI's
      guard, rooted in its own worktree, so a lock written here would bind
      nothing. Evidence stands in for it: the test file's hash at each red,
      and every test change after a red, with its reason, above.
- [x] Root cause is a CLASS: the guard modelled one Rust test layout (tests
      at the end of the file they test), while the language offers others —
      the protection was a convention, not the language's own rule. The fix
      follows rustc's module lookup instead of a layout.
- [x] Siblings: listed under Skipped, each marked whether the tripwire names
      it.

## 4. Verify
- [x] Unit tests: `TestModuleFiles` (21 tests: every test-module shape
      refused under the lock and allowed without it; production modules —
      one below a test module — open; both places locked, a decoy unlocking
      nothing (D3); a tests-only file's declaration locked in its parent,
      whatever blank lines, comments, byte-order mark or inner attributes
      precede its `#![cfg(test)]`, or items (I4), production declarations
      open (D4, F2); a
      missing module's every place; the deny names the declaring file; the
      repository's rules decide — the declaring file's for test modules, the
      module file's for R11; an unlistable folder refuses; crafted files and
      edits cannot stall the hook, nor 2,000 attributes on 2,000
      declarations, and a check past its budget asks (D1, F1, I1); past 256
      attributes in scope a declaration is test code; the scanner takes
      linear time and keeps to its deadline; shell writes as before; the
      scanner over comments (nested), strings (raw, byte, C), chars,
      lifetimes, escapes, unclosed openers, nested attributes, inner
      attributes, `#![path]`, `#[path]` before or after the cfg and written
      with spaces, raw and non-ASCII names, and declarations split by
      comments or Rust whitespace (D2); where a module file is looked for),
      `InlineTests.test_a_file_that_starts_cfg_test_is_tests` and
      `test_marker_shapes`' inner-attribute cases, 10 new
      `InlineTestCoverage` tests (a crafted file cannot stall the tripwire),
      and three generic tests that read the repository's own files: every
      Rust rule finds a `#![cfg(test)]` file's tests (R8) and takes linear
      time on runs of spaces (R12), and the guard hook blocks on failure
      (R13). Suite 142 OK on Python 3.14 (`round6-green.out`) and 3.9.25
      (`py39-origin.out`).
- [x] Watched it work through the real entry point: `guard.decide` with real
      PreToolUse events (`gap_probe_after.out`): with Rikuri-PI's rule as
      before this change, the test-module edit is refused and the tripwire
      names the `#![cfg(test)]` file (the cue to widen); with the widened
      rule all three test edits are refused and the production edit is
      allowed. Rikuri-PI (`real_repos_probe.out`, its own rule): the scanner
      finds exactly the 25 declarations a line regex finds, no file is a
      test module, the tripwire is `[]`. Real Rust (`corpus_probe.out`): the
      standard library, 1,844 of 1,845 declarations resolved; crates.io
      sources in ~/.cargo/registry, 31,943 of 32,081 — the misses are files
      left out of published crates (generated protobuf, isle examples,
      excluded tests), paths inside `cfg_attr` (34) and two declarations
      inside a `macro_rules!` body; and 432 declarations a line regex misses
      the scanner finds.
- [x] Recovery/fallback: N/A — no fallback path; a guard crash still asks
      (`FailureModes`, unchanged, green); a check past its budget asks
      (`test_a_check_that_runs_out_of_time_asks`).
- [x] Regression guard proven to FAIL on the old code: round 6's tests on
      the round-5 guard (`round6-red.out`, 3 failing) and Rikuri-PI's
      settings (`round6-red-Rikuri-PI.out`); round 5's on round 4's
      (`round5-red.out`, 4 failing; `round5-red-Rikuri-PI.out`); round 4's
      on round 3's (7 failing, §3); round 3's on `aa51a24` (`red.out`, 16
      failing). Mutants of every requirement against the final guard.py,
      restored and checked by sha256 (`mut_layouts.py`, `mut_layouts.out`):
      **79 of 79 red** — enforcement and its budget E1–E10, the parent
      declaration and the module file's own attributes F1–F4 and F7–F11,
      the attribute cap C1–C6, attributes A1–A5, places P1–P13, literals and
      comments L1–L14, declarations D1–D9, patterns that square S1–S3,
      tripwire T1–T9, warning W1 (round 1: 37 of 47; round 3: 47 of 47;
      round 4: 64 of 64; round 5: 72 of 72; round 6's first run 77 of 78 —
      E9 survived behind the new fixpoint deadline until a direct deadline
      test pinned it).
- [x] Rikuri-PI, a clean clone of `main` `1ea439d` (which holds exactly
      `aa51a24`'s guard files, PR #32), the shared files copied in
      (`cmp`-equal, guard_base.py unchanged), its rule changed and its hook
      blocking on failure: 142 OK on Python 3.14 (`sync-Rikuri-PI.out`) and
      3.9.25 (`py39-Rikuri-PI.out`).
      With the shared files but the rule as on `main` it fails the R8 test
      and the linear-time test (`sync-Rikuri-PI-rule-not-widened.out`:
      `main`'s own `guarded_lines` took 1.31 s). The rule change is three
      pattern spellings — `starts_at` and `attached_above` take `#!` in the
      linear form, `guarded_lines` the same matches in the linear form — and
      in `_inline_tests_doc` one sentence added and the "copied unchanged"
      clause corrected, by a checked replacement (each text found once; the
      parsed rule equals the old one but for the three spellings; no
      invisible character added): two lines of the file change. Python 3.12
      (CI's newer entry) is not installed here: Not yet proven until CI.
- [ ] Independent verification: rounds 1–3 FAIL (below); round 4 (pending)
- [x] Diff matches the §1 plan: guard.py (+332/−14 against `aa51a24`),
      test_guard.py (+548/−7: the seven removed lines are an assertion
      message reworded, a comment, the fixture rule's three regex lines —
      `!?` added and in the linear form — and a setUp list gaining
      `inner.rs`), this record and its evidence; in Rikuri-PI two lines of
      `guard-config.json`, one line of `.claude/settings.json` and a sync
      record. `guard_base.py` and every other file untouched.

Verifier round 1 (2026-10-11, 20:14–21:15), summarized: R1–R9 PASS through
the real hook process (Edit, Write, MultiEdit refused with the lock held,
allowed without it or under another session's lock; production files open;
2,058 Bash/Read/Grep decisions unchanged); tests first PASS (the 16 failing
tests of `red.out`, the earlier rounds checked against the transcript, no
test loosened); 47 of 47 recorded mutants red, 6 of its own 11 survived; five
repositories PASS on Python 3.14 and 3.9.25; full gates PASS (Rikuri-PI's
dependency step offline). FAIL: D1–D7 (§3); nits fixed in round 4.

Verifier round 2 (2026-10-11 23:40 to 2026-10-12 00:25), summarized: D2, D3,
D5, D6 PASS; R1–R10 PASS through the real hook (11 test-module shapes
refused with the lock and allowed without it; Rikuri-PI's real tree with the
lock: 33 of 33 production edits allowed, 13 of 13 in-file test edits and 23
of 23 `test_globs` files denied; 1,896 Bash/Read/Grep decisions unchanged);
tests first PASS; 64 of 64 recorded mutants red, 4 of its own 8 survived;
both repositories PASS on 3.14 and 3.9.25; gates PASS (Rikuri-PI's dependency
step offline). FAIL: F1 and F2, Important (§3). Minor: M1–M9 — fixed in
round 5: M2's O4, O5, O6, OM9a (now pinned), M6–M8 (figures, record fields,
"every step passes", Rikuri-PI's `_inline_tests_doc`), M9 (the tripwire's
time, with F1); listed under Skipped: M1 (answered in round 6), M2's O1 and
OM3, M3, M4 (its claim corrected), M5.

Verifier round 3 (2026-10-12, 14:56–16:05), summarized: F1 and F2 fixed
through the real hook (13.6 s → 0.10 s; 27.3 s → 0.08 s; the declaration
denied); R1–R10, R7, R9 PASS (21 of 21 rows through the real hook; Rikuri-PI's
real tree: 33 of 33 production edits allowed, 13 of 13 in-file test edits
and 23 of 23 `test_globs` files denied, 5.6 ms mean); 5,280 Bash/Read/Grep
decisions unchanged; tests first PASS (the red files rebuilt exactly from the
committed one); 72 of 72 recorded mutants red, 6 of its own 17 red; both
repositories PASS on 3.14.4 and 3.9.25; gates PASS (Rikuri-PI's dependency
step offline). FAIL: I1–I5, Important (§3); Minor: M-a (11 surviving
mutants of its own — test gaps; the real code handles each, checked
in-process), M-b (M7 listed twice in this section; fixed). The owner then
recalibrated (§0, §3): round 6 fixes I1 and I4 and makes Rikuri-PI's hook
block on failure; I2 and I3 are documented deliberate evasions; I5 has its
own change.

## 5. Close Out
- [x] Full gate green: this repository's, 7 of 7, inside `safe-run.sh` on a
      private clone at `86db3e9` with every file of round 6 committed (never
      pushed) (`gate-committed.out`). Rikuri-PI's own gate on a private clone
      of `dc7e327` with round 6 committed (`gate-Rikuri-PI.out`): tools,
      self-tests, guard, format, build, clippy, test, smoke and crash matrix
      PASS; the script then stops at its dependency step — `cargo deny`
      cannot fetch its advisory database inside the no-network layer — so
      that step and the five after it ran one by one: deny offline against
      the database cached 2026-10-09 (advisories, bans, licenses, sources
      ok); secrets, ratchet, contracts, crate-policy, scrap PASS. CI Not yet
      proven.
- [x] Scrap Sweep: the evidence scripts are kept with their outputs; the
      clones for rikurinode, AISecurity and Iceman were deleted when the
      owner narrowed the scope, with their outputs (their round-3 runs
      passed; §3); the helper tools, Rikuri-PI's clone and the gate copies
      live in `~/claude-wip/guard-rust-test-layouts/`, outside every
      repository, deleted at close-out (after the merges).
- [ ] Reviewed per `REVIEW.md`: by the verifier (round 3 pending).
- [x] Lesson loop: the class tripwire covers the two layouts on every suite
      run; R8 keeps each Rust rule's inner-attribute form; the generic
      linear-time test keeps runs of spaces from stalling a repository's
      rule; the generic `onFailure` test keeps a stalled guard from opening
      the gate. Process lesson (the crash): hours of uncommitted
      work belong in a folder that survives a reboot, not in `/tmp`.
- [x] Knowledge layer: `guard.py`'s header; Rikuri-PI's `_inline_tests_doc`
      (with the `..` limit, and when its copy of the rule changed); no
      AGENTS.md change (they say tests are read-only under the lock, which
      stays true and now holds for these layouts).
- [x] Commit message explains WHY; record committed with the change; pushed
      (owner, 2026-10-11 and 2026-10-12).

## Skipped items — visible, never silent
- **PRs and merges**: the owner's call. Order: here, after `aa51a24` (this
  branch sits on it; `main` has moved since — bootstrap rounds 11–14 — and
  holds neither `aa51a24` nor line continuation `92c39a2`); in Rikuri-PI,
  directly on `main` (`1ea439d` holds exactly `aa51a24`'s guard files, PR
  #32). Line continuation changes the same two files; whichever lands second
  is re-applied and rerun. Owner: Henry.
- **rikurinode, AISecurity, Iceman not synced** (owner, 2026-10-11): they
  keep the previous shared files; the global CLAUDE.md and `guard.py`'s
  header still say "identical in every full-tier repo". Their rules keep
  `guarded_lines`' slow `\s*!?\s*\(` (F1's sibling), and their hooks were
  not checked for `"onFailure": "block"`. Reactivate: when the owner widens
  the scope again. Owner: Henry.
- **The rule's older patterns** (verifier round 3, I5): `starts_at`'s
  `(?:.*[(,]\s*)?…test….*\)` and `guarded_lines`' `\(.*\btest\b` still take
  16–18 s on crafted inputs (`#[cfg(any(` + 30,000 × `(test)`; a line of
  20,000 × `cfg(`), as before this change. Split into their own change by
  the owner (proposed as a separate session, "Make Rikuri-PI's inline_tests
  rule patterns linear"). Rikuri-PI's hook now blocks on failure (R13), so
  such a stall closes the gate. Owner: Henry.
- **Deliberate multi-step evasions** (Minor by the owner's recalibration,
  2026-10-12 — the guard is "a tripwire, not a wall"): an opener `/*` (or
  `mod hidden {`) added above a parent's code, the test module edited, the
  opener removed (verifier round 3, I2: three allowed edits, the scanner then
  reads the rest of the parent as a comment); a tests-only file's
  declaration wrapped in a `macro_rules!` that is never expanded (I3). Both
  are silent. Reactivate: if a session is ever seen doing either. Owner:
  Henry.
- **Limits the tripwire names** (a tracked file is flagged, never silent):
  a `#[path]` that climbs out of the declaring file's folder with `..`
  (rustc follows it; the lock looks only in the module's folder and those
  above — the owner's 1(a) said "any #[path] target"); a test declaration
  whose file is in none of its places.
- **Limits that are silent** (neither locked nor named; none is used in
  Rikuri-PI or this repository): `#[cfg_attr(test, path = "…")]` without a
  plain `cfg(test)`; a `mod x;` produced by a macro (`macro_rules!`, whose
  expansion the guard does not run); `include!("…")` inside a test module; an
  attribute written with a comment inside it (`#/*c*/[cfg(test)]`, also
  missed by the in-file rule); an absolute `#[path]` into the repository
  (left out with paths outside it; verifier round 2, M3); a symlinked folder
  (`ln -s src/b bl`, then an Edit of `bl/t.rs` — `test_globs` has the same
  weakness; on a case-insensitive filesystem a differently-cased name may be
  its sibling, untested on Linux); a file that holds both code and tests
  switched off from its parent (`#[cfg(any())] pub mod outer;`): callers
  break unless the code is reachable another way — `pub mod foo2; pub use
  foo2 as foo;` with a copy leaves 0 tests and is allowed (verifier round 2,
  M4; this class predates the change). Reactivate any of them when a
  repository adopts the layout. Owner: Henry.
- **The safe side, at a cost**: while a file declares a tests-only module,
  a change to that file's own inner attributes (`#![allow(unused)]` at the
  top of `lib.rs`) is refused under the lock, since they apply to the
  declaration too (verifier round 2, M5); a declaration with more than 256
  distinct attributes in scope counts as test code (round 6), so its module
  is locked even if it is production code.
- **Not pinned by a test** (verifier rounds 2 and 3): the fixpoint's and
  R11's own deadline checks, and `\u{…}` character escapes, are equivalent
  in tests today (the scanner meets the deadline first and raises; a
  `\u{…}` escape's braces are balanced); verifier round 3's other surviving
  mutants of its own (M-a: a space after `!`, an unclosed `#[`, comments
  inside an attribute, an unreadable module file) are test gaps the real
  code handles (it checked each in-process).
- **Python 3.12 and CI**: Not yet proven until a CI run is observed.
- **Fix-lock not engaged** during the fix: this session's hook is
  Rikuri-PI's, so a lock here would bind nothing; the red runs, hashes and
  the reasons for every test change after a red stand in for it (§3).
- **Independent verification and REVIEW.md** boxes: open until verifier
  round 4 reports; the stop rule, as recalibrated, decides.

## Evidence log
Files in `evidence/2026-10-11-guard-rust-test-layouts/`; every run inside
`safe-run.sh`. Every file here was written after the crash, by a run of the
rebuilt or later files; the earlier rounds are summarized in §3.
```
base     base.out: 107 OK (the committed tripwire aa51a24: guard.py c1d54b73…, test_guard.py 08e00cb4…)
gap      gap_probe.py: gap_probe_before.out (aa51a24: both layouts editable; tripwire silent),
         gap_probe_after.out (round 5, from Rikuri-PI's clone: refused with the old rule for test
         modules, with the widened rule for both)
survey   survey_mods.py / survey_mods.out (Rikuri-PI main 1ea439d)
red      red.out: round 3's tests on aa51a24 (16 failing); round4-red1.out, round4-red2.out (round 4);
         round5-red.out (4 failures), round5-red-Rikuri-PI.out (its committed rule: the linear-time test);
         round6-red.out (3 failures), round6-red-Rikuri-PI.out (its settings: the onFailure test)
green    green.out (round 3, 128 OK); round4-green.out (134 OK); round5-green.out (138 OK);
         round6-green.out: 142 OK (guard.py c884a868…, test_guard.py 42a7d741…); py39-origin.out: 142 OK on 3.9.25
mutants  mut_layouts.py / mut_layouts.out: 79 of 79 red, guard.py restored (sha256 c884a868aaef)
probes   real_repos_probe.py / .out (Rikuri-PI, its own rule); corpus_probe.py / .out (Rust standard
         library; crates.io sources in ~/.cargo/registry)
sync     sync-Rikuri-PI.out, py39-Rikuri-PI.out: 142 OK each; sync-Rikuri-PI-rule-not-widened.out:
         2 failures (R8, linear time)
gate     gate-committed.out: 7 of 7 (round 6); gate-Rikuri-PI.out: its script stops at the dependency step
         (no network); that step and the five after it pass one by one offline
lnd      every run: StartedAt unchanged within it (2026-10-11T22:24:44Z until the 18:43 reboot,
         2026-10-12T01:46:20Z after it); it changed only with the machine's own restarts
```
