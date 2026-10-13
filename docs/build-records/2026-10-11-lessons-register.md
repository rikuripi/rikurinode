# Build Record — the lessons register: what the previous repository taught

| | |
|---|---|
| **Date** | 2026-10-11 |
| **Author / session** | Claude Code (Opus 5.5); owner Henry |
| **Branch** | docs/lessons-register (2026-10-11, on the pre-GitHub root); re-landed on `main` as docs/plan-and-lessons (2026-10-12) |
| **Commits** | 32d0c58 on the old root; on `main`: its cherry-pick in the pull request that adds this line |
| **Status** | COMPLETE — verifier rounds 1–10 FAIL, round 11 PASS, round 12 FAIL (two names in row 69 never expanded; the commit message's "every mutation … is kept"); round 13 answers them, with no check round after it (the owner's stop rule); re-landed on `main` 5630ea0 with the checker and the full gate green; CI and the owner's merge Not yet proven when this line was written |
| **Change type** | documentation (requirements) |

## 0. Intent
- [x] Problem: the previous rikurinode "has been changed so many times,
      there are a lot of orphans and stale parts" (owner, 2026-10-10). Its
      114 build records hold what went wrong and what was learned; the
      rebuild must keep the lessons without carrying the code.
- [x] Outcome: `docs/requirements/lessons-register.md` — 107 requirements
      for the new node, each with the incidents behind it, the tripwire that
      must exist, the owner's decisions and the old code worth porting —
      every factual claim checked against its record.
- [x] Owner approved: "Go ahead with step 1-4" (2026-10-11); step 2 is
      "fact-check the lessons register and add it to the repo".

## 0b. Spec
- [x] Requirements: every lesson of the harvest feeds exactly one
      requirement; every claim is supported by the record it cites; the
      owner's words appear as quotations only where the record quotes the owner;
      every path named for porting exists; the gaps where the old records
      have no evidence are said, not filled.
- [x] Design: harvest (six readers, one lesson per defect class per record,
      475 lessons) → merge by class into 107 requirements in 12 themes →
      owner decisions (122), port candidates (90), gaps (11), coverage →
      fact-check by six more readers, by theme, claim by claim against the
      records, plus a script for everything mechanical. Rejected: porting the
      old records themselves (the history stays in the old repository, read
      by absolute path).
- [x] Policy applied: the old repository is where the live node runs — every
      read was by absolute path or `git -C … ls-tree/show`, never a checkout,
      never a run.

## 1. Plan
- [x] Files: `docs/requirements/lessons-register.md`, this record,
      `evidence/2026-10-11-lessons-register/` (the harvest, the
      requirement → lesson map, the six fact-check reports and their brief,
      the checker, its baseline of section 3's notes, its mutations and their
      output, the correction scripts).
- [x] I will know this works when: the checker reports only explained items;
      every fact-check finding is corrected or listed below with its reason;
      a verifier spot-checks claims against the records and finds them
      supported.

## 2. Build
- [x] The register was written on 2026-10-10 from the harvest
      (`lessons-harvest.json`). A spot-check that evening found one wrong
      figure ("12 of 16" for the record's "12 of 14"), so the whole register
      was fact-checked before it entered the repository.
- [x] Mechanical check (`check_register.py`, first run before the
      fact-check): the structure held — 475 lessons each feeding one
      requirement, theme counts, the coverage table, 114 cited records, 122
      owner decisions verbatim from the harvest, 90 port rows with their
      totals — but a third of the port cells used shorthand (`a + b`, a file
      name relative to the previous one); all are now full paths (two names
      in row 69 were missed until round 13).
- [x] Fact-check (`factcheck-brief.md`, reports A–F): about 830 claims; 44
      wrong, 13 not found in the cited record, 32 overclaims. Examples: a
      command that ran 5.9 s past the emergency stop — in a test mutant, not
      in the node; a backup path that "never existed" that was really "never
      one of the node's drives"; a runbook that "restarted LND" when the
      record says LND was only eligible; tripwires the old repository
      planned but never built, now marked "owed"; port rows claiming a test
      proves more than it asserts; 12 owner lines that were the record's
      summary or several answers joined, now unquoted or split, and marked
      in the owner-decision table. Two readers (C and E) found the known
      "12 of 16" (LN-03); it is counted once.
- [x] Corrections: by hand for A, D and F; by `apply_bce.py` (exact
      replacements, each required to match) for B, C and E. The register's
      opening now says how it was checked.
- [x] Not changed, with the reason: requirement wording that prescribes for
      the new node what the old one lacked (PLAT-02's Pi 5 sensors, AI-08's
      token target, AI-10's stamped index, LN-09's protocol statement) —
      requirements, not claims about the past; EVID-04's owner quote about a
      popup later overturned by the owner's own test (the quote is accurate;
      the overturn is in its record).

## 3. Debug
- N/A — no defect in code.

## 4. Verify
- [x] Checker after the corrections (round 1; from round 3 on it reports
      0 — see below): 3 items,
      all explained — two quotations whose record wraps a label in bold
      (`**MAs + returns backup:** …`), which matches word for word without
      the markup, and one test cell that names a rule rather than a file.
- [x] **Verifier, round 1: FAIL.** Passed: the gate 7/7; the checker's
      three explained items; its own recount of the harvest's figures;
      `apply_bce.py` replayed on the earlier copy gives the committed register;
      about 46 corrections and 25 untouched claims re-checked against the
      records, and the 12 annotated owner rows. Failed: five corrections made
      in one place but not in its duplicate (port rows 42, 64 and 90, PLAT-10's
      Port line, TEST-04's owner line), TEST-04's "over a month" left resting
      on a record that gives no span, HEAL-03's "783 times" (the record: 841
      runs, 783 of them partial), two more owner lines that were summaries
      in quotation marks (PLAT-09, row 78), "33 overclaims" (the reports add up
      to 32) and wrong per-report figures for C and F, "one reader" for the
      "12 of 16" that two found, a receipt cut short by my `cut`, and a
      pointer to the platform plan, which is not on this branch.
- [x] Round 2 (`apply_r2.py`): each corrected; rows 1 and 78 annotated (14
      in all); the receipt rewritten in full (`register-check-final.out`, then
      the same three explained items; later rounds rewrote it).
- [x] **Verifier, round 2: FAIL.** Every round-1 item fixed, the counts and
      both scripts' replays confirmed, its own ~21 spot-checks supported but
      one. Failed: the class round 1 found was not swept — six more Owner
      lines (EXEC-01, SEC-01, SEC-05, EVID-06 twice, UPG-02) put the record's
      or the harvest's words inside the owner's quotation marks, against this
      record's own requirement; and the checker never looked at Owner-line
      quotations (that loop did nothing) and skipped quotes under 12
      characters, though the register and the commit message said every
      quotation is found. Smaller: EVID-09's Electrum cause stated as
      fact (its record: consistent with the logs, not proven); TEST-04's
      order of events and "each session"; `register-check3.out` unnamed.
- [x] Round 3. The checker now checks every “…” in every Owner line, at any
      length, against the records that line cites (Markdown emphasis
      ignored) — it found 37 lines, not 6 (first written "36": round 3's
      verifier). `fix_owner_quotes.py` unwrapped
      the 32 where the harvest had put a whole decision in quotation marks
      with the owner's words inside in straight quotes: the outer marks go,
      the owner's words become the quotation. Five by hand: two elisions
      split into separate quotations around the "…", one record heading
      unquoted, EXEC-01's session choices taken out of the owner's quotation,
      a trailing ellipsis moved outside. The Electrum cause, TEST-04's order
      and wording corrected. The checker also reads a test cell's note in
      brackets. Result (`register-check-final.out`): 0 problems.
      `register-check3.out` is the checker's run before the round-1
      corrections, kept as a receipt of that state.
- [x] **Verifier, round 3: FAIL.** Every quotation was in its record (170
      checked by its own tool), the checker reported 0, caught four of six
      mutations and the round-2 items held. Failed: presence is not
      attribution — FUND-03 and HEAL-03 quoted the record's own prose as the
      owner's words, and the checker could not see it (its mutation M1b
      passed); smaller cases in PLAT-04 (a standing decision the record does
      not quote; "the heaviest container" was the session's words), EVID-06
      (the quotation ran past the record's bold option labels into its
      description), HEAL-10 (doubly quoted), EXEC-01 ("the session's" choices
      went to the owner); AI-07's "13 of 36" (its record corrects it to 10);
      "36 lines" (37); stale "3 items" lines here; the commit message's "only
      around the owner's own words", which nothing checked.
- [x] Round 4. The checker now also asks whose words they are: each quotation
      must lie inside a quotation in the record or in a bold option label (how
      the records mark the owner's choice). It flagged the six cases above,
      now corrected (the record's account given without quotation marks; the
      option labels alone quoted); PLAT-04's session words and EXEC-01's
      wording, AI-07's count and section 3's note on corrected rows fixed.
      Result: 0 problems (`register-check-final.out`); on copies, the
      record's prose put back in quotation marks and a changed option label
      are both caught. Its limits: a quotation broken over two lines is not
      checked, and it matches text, so a very short quotation ("OK") is a weak
      check — no such case is wrong today (round 3's verifier read all 170).
- [x] **Verifier, round 4: FAIL.** The register held: its own tool read all
      166 quotations, and every one is the owner's words or an option label
      the record shows the owner choosing; 15 further claims supported. The
      checker did not do what this entry said: it took every bold span as an
      option label and paired quotation marks across a whole file (in four
      records one empty `""` shifts the pairing, so 37–89% of the record
      counts as quoted), so round 3's M1b and its own V1–V2 (a record's and a
      session's prose quoted as the owner's) passed with 0 problems; V3 (the
      session's words, which the record also quotes) passed, since the
      checker cannot tell who spoke; V4 (row 9 changed) passed, because its
      note began "corrected:" though only row 119 was corrected. Smaller:
      TEST-12 quoted an option's description (the session's words); PLAT-04's
      standing rule sat under the owner though the record does not say who
      set it; line 174's "stay on Bitcoin" is not the record's wording; stale
      lines here; the commit message claimed what nothing checked.
- [x] Round 5. The checker now pairs quotation marks within one paragraph,
      top-level list item (with its sub-items) or table row, and skips a part
      with an odd number of them (2 parts in the 67 records it reads);
      accepts bold only as a label that opens a list item; matches whole
      words (so “OK” is no longer found inside "took"); joins an Owner item
      wrapped over lines; flags Markdown inside a quotation; and requires a
      "corrected" note in section 3 to give the harvest's text word for word.
      Row 9's note relabelled (the record's wording, not a correction);
      TEST-12's description, PLAT-04's rule and line 174 reworded; the
      register's opening now says the script cannot tell whose words a
      quotation is. `mutate_register.py` plants 15 defects on copies
      (`mutations-round5.out`): 13 caught, including M1b and V1–V2, V4 and
      the two limits of round 4 (a quotation wrapped over two lines, emphasis
      added inside one). **Missed, and stated as limits:** M3b (one of two
      cited records dropped — the quotation is still in the other) and V3
      (someone else's words that the record quotes, given as the owner's:
      the checker reads markup, not speakers). Whose words each quotation is
      was read by hand, by the round-3 and round-4 verifiers.
- [x] **Verifier, round 5: FAIL.** The register held again (165 “…” in
      Owner lines: 160 inside the record's quotations, 5 AskUserQuestion
      option labels); gate, replays and the five edits confirmed. The
      checker still claimed more than it does: any bold label opening a list
      item passed as an option label (2,128 such labels in the cited
      records), so the record's and the session's bold prose quoted as the
      owner's passed (A2–A4, C1); an empty `""` still mis-paired quotation
      marks inside one list item (A5, A6); and only “…” pairs were checked —
      straight, single or unbalanced marks passed (B1–B4). Also missed: a
      relabelled note or a changed corrected row in section 3 (E1–E3), and a
      contrived wrap (D3). IDEN-03's "the owner's decision" was the session's
      live test; the owner's choice was left open.
- [x] Round 6. Bold no longer counts: the five option labels the register
      quotes are listed in the checker, read by hand against their record
      ("Owner's choices (AskUserQuestion, 2026-09-29)"). An empty `""` is
      dropped before pairing. Every quotation mark in an Owner line is read
      (“…”, "…", ‘…’), and unbalanced or reversed marks are a problem. An
      Owner section ends at a blank line (it had run on into the next
      theme's anchor). Section 3's 14 notes and row 119's corrected text are
      a baseline read by hand (`owner-decision-notes.json`): any change
      fails until the row is read again. IDEN-03 reworded. The round-5
      verifier's 21 cases are added to `mutate_register.py`
      (`mutations-round6.out`): 34 of 36 caught. **Its limits, stated:** it
      cannot tell whose words a quotation is (V3: someone else's words that
      the record quotes pass); it does not check that every cited record is
      needed (M3b); a stray quotation mark that leaves a part's count even
      still mis-pairs that part; and it reads only Owner lines and section 3.
      Whose words each quotation is was read by hand, by the round-3, 4 and 5
      verifiers.
- [x] **Verifier, round 6: FAIL.** Gate, replays, the notes baseline and
      IDEN-03 held; the checker caught 31 of the verifier's 54 mutations.
      Missed in classes this entry claimed: an unpaired or reversed ‘…’, a
      reversed ”…“ after a good pair, an empty `""` in an Owner line (dropped
      only on the record's side), a quotation of a code span; and other
      quotation styles passed, though the register said "in any quotation
      marks". A content defect: section 3's row 43 still put the record's
      description inside the owner's quotation marks — the duplicate of
      round 3's EVID-06 finding, never annotated (round 1's class). The
      mutation receipt named a register from before the last edit.
- [x] Round 7. The checker reads an Owner line closed-world: it takes “…”,
      "…", ‘…’ and '…' outside code spans, and reports anything else that
      marks a quotation (an unpaired or reversed mark, another style, an
      HTML entity or `<q>`, an empty quotation or one of code only) instead
      of passing it. An Owner section now ends at a blank line only when no
      indented item follows. Section 3: every row must be in its five-cell
      form and cite the records the harvest has for it. Row 43 annotated
      like row 78; the baseline now holds 15 notes. The register's opening
      names the four styles. Receipts were written after the last edit and
      name the committed register's sha256: this record's 36 mutations
      (`mutations-round7.out`) 34 caught; the round-6 verifier's 54, kept as
      `mutate_register_v6.py` (`mutations-round7-v6.out`), 50 caught. The six
      misses are all in the stated limits. **Its limits:** it cannot tell
      whose words a quotation is (V3, L1); it does not check that every
      cited record is needed (M3b, L2); words given as the owner's without
      quotation marks pass (PU2); it reads only Owner lines and section 3
      (L3, a Why line); and a stray quotation mark that leaves a record
      part's count even still mis-pairs that part. Whose words each
      quotation is was read by hand, by the round-3 to round-6 verifiers.
- [x] **Verifier, round 7: FAIL.** Round 7's fixes held: gate, replays,
      receipts naming the committed register, row 43's note against its
      record, the Owner lines' 166 quotations. The claim did not: "closed-
      world" was a list of marks, so HTML5 entities (`&OpenCurlyDoubleQuote;`
      and others), Unicode quotation marks outside the list (‛ ‟ 〝 「 」 ❝),
      primes, a blockquote, escaped backticks and an unlisted opening mark
      closed by a possessive ’ all passed (53 of its 85 mutations); an Owner
      section still ended at a blank line before an indented `* `, `+ ` or
      `1. ` item or a continuation paragraph; a section-3 row without outer
      pipes or indented by a space went uncounted. Noted: row 3 lists a rule
      its record attributes to no one.
- [x] Round 8. Closed-world by alphabet, not by a list of marks: Owner lines
      today use printable ASCII and five other characters (“ ” — … →); any
      character outside that alphabet (with ‘ ’, a read style) is reported,
      and so are an HTML entity or tag, a blockquote line, a backslash, a
      lone backtick, curly quotation marks inside a code span, and an Owner
      label written any other way than `- **Owner:**`. An Owner section ends
      at the next field, a heading, or a blank line followed by a line at
      column 0. Matching is case-sensitive (no quotation changed case).
      Section 3: any line with two pipes counts as a row; rows are numbered
      1 to 122 in order; each row's Feeds cell must match the mapping. Row 3
      annotated (16 notes in the baseline). The round-7 verifier's 85 cases
      kept as `mutate_register_v7.py`. Receipts, written after the last edit
      of the register and naming its sha256: this record's 36 (34 caught,
      `mutations-round8.out`), the round-6 verifier's 54 (50,
      `mutations-round8-v6.out`), the round-7 verifier's 86 (85,
      `mutations-round8-v7.out`). The seven misses are the stated limits:
      whose words (V3, L1), every cited record needed (M3b, L2), words given
      as the owner's without quotation marks (PU2), Why lines not read (L3),
      section 3's Status cells not checked (S3e). Also stated: quotation
      marks inside a code span are reported only when curly, and a stray
      mark that leaves a record part's count even still mis-pairs it.
- [x] **Verifier, round 8: FAIL.** Replays and receipts held; the seven
      misses were the stated limits. About 25 of its own mutations in
      claimed classes passed: `_'…'_` (Python's `\w` holds `_`), a quotation
      between backtick runs of unequal length, a blockquote after `1)` or a
      nested marker, a column-0 `#` line that is not a heading, Owner labels
      written with a homoglyph, an entity, an invisible character or HTML,
      Owner lines under a `####` that is no requirement, section-3 rows
      starting `#` or `---`, rows with no or one pipe that GFM still renders,
      free text in a Records cell. Content: rows 29 and 33 still quoted the
      session's words with no note (their requirement lines were corrected
      in rounds 3–5); TEST-08 and row 10 quoted the record's summary of
      decision Q0 as the owner's; UPG-05 and row 95 quoted a paraphrase the
      record's own section 0 gives differently. Minor: "85 cases" (86).
- [x] Round 9. Content: TEST-08 and UPG-05 reworded from their records (the
      plan, at 883d8285, reads "Q0 — Repair the live breakages by hand
      first: YES"; the record's section 0 gives answer 1 as "Hold it, show
      why"); rows 10, 29, 33 and 95 annotated (20 notes in the baseline).
      The new checks found two placeholders that rendered as HTML tags and
      vanished (`/run/media/<user>`, `Stopped by you since <time>`), now in
      code spans. Checker: the register's alphabet is closed for the whole
      file (printable ASCII and 14 characters it uses), and so are its HTML
      tags (`<a id>`, `</a>`, `<br>` outside code spans) — no entities; every
      `####` heading is a requirement and its body holds only its six fields
      at column 0; an Owner label in any other spelling or case is reported;
      code spans pair backtick runs of equal length; a quotation in
      emphasis is read; a blockquote after any list marker is reported; an
      Owner section ends only at a real heading; section 3's table runs to
      its first blank line and every line in it must be a five-cell row,
      with record names alone in the Records cell. The round-8 verifier's
      cases kept as `mutate_register_v8a.py` and `_v8b.py`. Receipts after
      the last edit, naming its sha256 (`mutations-round9*.out`): 213 of 223
      caught (written with trailing spaces removed — the pre-commit hook
      refuses them — so a replay is compared after `sed 's/[ \t]*$//'`).
      **The ten misses, stated:** whose words (V3, L1); every cited
      record needed (M3b, L2); words as the owner's without quotation marks
      (PU2); Why lines and section 3's introduction not read (L3, S9); Status
      cells not checked (S3e); straight quotation marks inside a code span
      (E0t); a mark glued to the word before it read as an apostrophe (A4).
      The register now says the script is a helper, not a proof.
- [x] **Verifier, round 9: FAIL.** Held: the gate, the replays (213 of
      223, the ten stated misses), the receipts naming the committed
      register, and the content: TEST-08, UPG-05, the four new notes, the
      two placeholders, and a full survey of Owner lines and section 3 found
      no record or session prose inside the owner's quotation marks without
      a note. Failed: round 9's record named classes as "reported" or
      "read" that its own mutations got past — a straight quotation between
      backticks inside link destinations (`[](x`)"…"[](y`)`, C3, C6); a
      heading nested in an Owner item ending the checker's Owner section
      while the rendered field goes on (O1–O3); `<q>` or `<i>` behind
      escaped backticks or link destinations (T1–T4); an indented or empty
      `####` (H1, H1b, H4); a `#x` line cutting a requirement's body (H2);
      Owner labels such as `0wner:` or `Ovvner:` (L1, L1b, L2); and the commit
      message said, unqualified, that such forms are reported.
- [x] Round 10. Nine rounds have shown that a checker reading Markdown text
      can be fooled by Markdown written to fool it, and each round's claim
      about the checker grew past what it does. So the checker is not
      extended again: the register's opening now says it reports *many*
      forms it does not read, names them, and says Markdown written to hide
      a quotation can still get past it. **The forms known to pass** (the
      round-9 verifier's): C3, C6, O1–O3, T1–T4, H1, H1b, H2, H4, L1, L1b,
      L2, with the ten misses of round 9. The evidence that the register's
      quotations are the owner's words is not the script: it is the reading,
      quotation by quotation, by the verifiers of rounds 3 to 9; the script
      guards against an accidental change. Receipts rewritten after this
      round's one-sentence change to the register (`mutations-round10*.out`,
      the same 213 of 223; trailing spaces removed as in round 9).
- [x] **Verifier, round 10: FAIL.** Held: the gate, all six replays (213 of
      223, the ten stated misses), the receipts' hash, and the content (a
      seeded sample of 12 Owner items, about 20 quotations, and 8 section-3
      rows, each the owner's words or chosen option; the one-sentence diff).
      Failed: the claims again — the record listed 16 of the round-9
      verifier's passing forms by hand, but 34 pass (H3, H5, H6, L3–L10,
      S1, R1–R3, A3, A1b, A1c were missing); the register named "a
      character outside the alphabet" and "an Owner label written another
      way" as reported, yet a carriage return (read as a line break before
      the alphabet check) and labels such as `***Owner:***` or a plain
      `Owner:` pass; "the counts" and "every path named for porting" were
      wider than the checker (counts outside the Contents rows, test paths
      in Port lines are not checked).
- [x] Round 11. No more lists written by hand: every verifier's mutation
      script is kept (`mutate_register_v9a.py`, `_v9b.py` from round 9's,
      `_v10.py` from round 10's, beside the earlier ones), and the forms the
      kept scripts try that pass are exactly the MISSED lines of
      `mutations-round11*.out` — 238 of 288 caught, 50 passing. The checker
      now reads the register with `newline=""`, so a carriage return is
      reported (A1b, A1c caught). The register's opening no longer names
      classes the checker reports: it says what the script re-checks (the
      mapping, the per-theme counts and the Coverage table, the cited records,
      section 3, section 4's paths and each Port line's main path, Owner-line
      quotations), that it is not a proof, that it does not check everything,
      and that Markdown written to fool it can get past it.
- [x] **Verifier, round 11: PASS.** Every item the register's opening
      lists has a mutation the checker catches (the verifier's own MP1–3,
      PT1, CV1–4, CR1–6, S3a–c, S4a–b, PL1–2, beside the kept sets); all
      nine replays match receipts naming the committed register; the 50
      MISSED lines are every tried form that passes; a fresh content sample
      (seed 271011: 12 Owner items, about 22 quotations, 8 section-3 rows)
      holds; only the opening paragraph changed. Findings, none failing the
      round: F1 "the paths in section 4" reads wider than the table the
      checker reads (a path in section 4's prose passes); F2 section 3's
      Status cells are not checked (S3e, in the receipts); F3 a deleted or
      reformatted Contents row passes (N5, N6, in the receipts); F4 a
      missing record in an Owner line is caught by a crash rather than a
      reported problem; F5 other untried forms pass (a swapped Port path
      that exists, swapped Why records, the record count in the opening,
      section 3's introduction count, a malformed duplicate Coverage row)
      — "the forms that pass" holds for the forms the kept scripts try.
- [x] Round 12. F1: the register says "the paths in section 4's table". F5:
      this record says "the forms the kept scripts try". F2–F4 stay as
      noted. Receipts rewritten after the change (`mutations-round12*.out`).
- [x] **Verifier, round 12: FAIL.** Held: the gate, all eight replays
      against the round-12 receipts, the diff, the summary of round 11 (two
      small omissions: F1's "would fail" caveat, and that round 9's "Status
      cells are not checked" left the opening). Failed: the register's new
      "the paths in section 4's table" — row 69's test cell still named
      `cardBlend.test.ts` and `cardRanking.test.ts` without their folder,
      and the checker skips a name without a `/` (T69a, T69b), against this
      record's "all are now full paths"; and the commit message's "every
      mutation the verifiers tried is kept" — round 11's set (mut27.py) was
      not kept, and its six misses (S4c, PL3, U1–U4) were in no receipt.
- [x] Round 13. Row 69's two names written as full paths, both checked to
      exist at the old HEAD (`git -C … ls-tree`); the register's phrase
      now reads "the paths in section 4's table (outside its bracketed
      notes)", since a path inside a note is not checked (T69d). Round 11's
      and round 12's sets kept (`mutate_register_v11.py`, `_v12.py`; v12's
      T69a and T69b anchors updated for the full paths, as its header
      says). The commit message says the sets the verifiers wrote are kept
      and the receipts list every form those sets try that the checker
      misses. Receipts after the last edit (`mutations-round13*.out`): 264
      of 321 caught over ten sets.
- [x] Verifier, round 13: not run. Round 12's findings were wording (two
      names, one phrase); the owner's stop rule (2026-10-11, recorded in
      the bootstrap record) fixes wording without a further check round.
- [x] **Re-landed on `main`** (2026-10-12). The branch sat on the
      pre-GitHub root (2075218), with no merge base with `main`; 32d0c58
      cherry-picked onto `main` 5630ea0 without conflict. The checker on
      the re-landed register, against the previous repository's HEAD
      3bbbe392 (unchanged): output identical to `register-check-final.out`,
      0 problems (`register-check-reland.out`).

## 5. Close Out
- [x] Full gate green: all 7 steps on the re-landed tree (2026-10-12,
      `../2026-10-11-platform-plan/reland-gate.out`)
- [x] Knowledge layer: N/A — no runtime behaviour.
- [x] Commit message explains why; record committed with the change

## Skipped items — visible, never silent
- **One fact-checker broke the brief** (report F): its first commands
  `cd`-ed into the previous checkout to read (`git show`, `grep`,
  `ls-tree`, one `git status`). Nothing was written or run there; the
  checkout's status and its index file's time were unchanged afterwards
  (checked 2026-10-11), and LND, bitcoind and Tor kept their start times.
  The brief already forbade it; the next brief repeats it first.
- `check_register.py` reads the previous repository at its path on the
  owner's machine; elsewhere it cannot check citations and ports. Owner:
  Henry. Reactivate: if the register is ever checked off this machine.

## Evidence log
```
2026-10-10  register written from the harvest; spot-check: "12 of 16" wrong
2026-10-11  mechanical check: structure holds; shorthand paths expanded
            fact-check A 131/7/1/2, B 112/14/2/3, C ~112/6/5/5, D 82/7/0/4,
            E ~165/6/1/12, F 232/5/4/6 (claims / wrong / not found / overclaims; LN-03 found by C and E)
            all corrected; checker: 3 explained items (round 1); 0 problems from
            round 3 on (register-check-final.out); round 5: 13 of 15 planted
            defects caught (mutations-round5.out); round 6: 34 of 36
            (mutations-round6.out); round 7: 34 of 36 and the round-6
            verifier's 50 of 54 (mutations-round7.out, mutations-round7-v6.out);
            round 8: 34/36, 50/54, and the round-7 verifier's 85/86
            (mutations-round8*.out); round 9: 213 of 223 over five sets,
            the ten misses stated (mutations-round9*.out); round 10: the same
            (mutations-round10*.out); round 11: 238 of 288 over eight sets,
            every miss a MISSED line (mutations-round11*.out); verifier: PASS;
            round 12: the same 238 of 288 (mutations-round12*.out); verifier:
            FAIL; round 13: 264 of 321 over ten sets (mutations-round13*.out)
2026-10-12  re-landed on main 5630ea0; checker: 0 problems, identical to round 13's
            (register-check-reland.out); full gate: all 7 steps passed
```
