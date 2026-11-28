# Build Record — the claim code, kept apart from the fingerprint: the page checks a code's shape before sending, and the screen says the fingerprint is not typed (stage 1, 5c)

| | |
|---|---|
| **Date** | 2026-11-26 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/claim-code-clarity`, from `main` at `fdefa4d`, with `main` at `f8d2e0e` merged in by the owner (`7d53ae7`); a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `051062a` (red tests), `9d61e72` (the fix), `c5d233d` (the red run recorded), `c6ffdac` (repair 1), `e926af7` (repair 2); the owner's merge of `main`, `7d53ae7`; this close-out: PR #182 |
| **Status** | DONE |
| **Change type** | fix |

## 0. Intent: the owner's words

- **"Next"** (2026-11-26), on the proposal that closed `docs/build-records/2026-11-26-n150-cert-steps.md`: label the fingerprint so it is never typed, make the claim page clearer when a code is refused, and keep system messages off the claim screen.
- The defect, in the owner's words: **"I thought the fingerprint was the claim code so never pressed the Enter key."** and **"Chrome and Safari keeps giving me code not the same when they are the same; then too many tries warning keeps coming up."** Each fingerprint typed was a counted wrong try against the code the control plane arms, unseen, at its first start (`main.rs`, "claim code armed and not shown"), so after 5 the node delayed (`claim.rs`, `DELAY_AFTER`). Twenty would have retired the code.

## Task Contract

1. **Outcome:** an owner who types the fingerprint, or anything else that cannot be a claim code, is told so on the page at once, and spends none of the node's 20 tries; the claim screen says the fingerprint is compared, never typed.
2. **Scope:** **high-risk** (the claim page is the authentication boundary's front; the node's own check is unchanged, but when unsure, high-risk).
   - `ui/src/secure/Claim.svelte`: the code is read as the node reads it (`claim.rs` `normalize`: drop `-` and space, upper-case) and must be 10 symbols of the node's alphabet (`ALPHABET`, `CODE_LEN`) before the form can submit; otherwise a hint under the field (`claim.not_a_code`). What is sent stays exactly what was typed, as now.
   - `ui/src/i18n/en.json`: `claim.not_a_code` (new), `claim.code_hint` and `claim.wrong_code` (each Enter at the node replaces the code; only the newest works).
   - `control-plane/crates/rikuri-control/src/console.rs`: the fingerprint's heading says it is compared, not typed, and is not the claim code; still plain ASCII within 80 columns.
   - `docs/runbooks/install-node.md`, steps 9 and 12: the same words.
   - Tests: `ui/tests/owner.spec.ts` and `console.rs`'s tests, red first.
   - **Not included:** the server's claim check, the limiter and its numbers, `normalize` itself; kernel messages on tty2 (an OS image change, its own task); the Mac's Keychain step on the certificate page; telling a replaced code from a typo (the node keeps only the newest code's hash, so it cannot know).
3. **Done when:**
   - a fingerprint, a code too short or too long, and a code with `0`, `1`, `O`, `I` or `L` keep the button disabled, show `claim.not_a_code`, and send no request (Playwright);
   - the right code typed with small letters, spaces or no dashes still submits, and is sent as typed (Playwright);
   - every claim screen state says the fingerprint is not the claim code, in ASCII within 80 columns (`cargo test`);
   - the tests are committed red first and seen red in CI; then `Full gate (Ubuntu)` passes on the fix; one verifier pass with no Important finding.
4. **Authority:** the files above; commit and push this branch; a draft PR to `main`; the owner merges. Local tests cannot run on this Mac (`safe-run.sh` needs Linux namespaces), so CI is the run of record. The verifier is required (code, high-risk).
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; time is reported.

## 0b. Spec: the rules applied

- **The node stays the judge.** The page's check only refuses more: any input the node could accept passes it, because a code the node arms is always 10 symbols of `ALPHABET`, and the page normalizes exactly as `normalize` does. Nothing the node accepts today is refused by the page.
- **No new information leaks.** The check uses only the code's public shape, never the node's state; the server's refusals stay uniform (`claim.rs`'s design: every refusal looks the same).
- **Nothing important fails silently.** The hint says why the button is disabled.

## 1. Plan

1. Red: Playwright tests for the shape check and for a lenient right code; a console test that every state says "not the claim code". Commit alone; push; CI red on those tests.
2. Fix: the check and the hint in `Claim.svelte`, the strings in `en.json`, the heading in `console.rs`, the runbook. Commit alone; push; CI green.
3. Verifier pass; at most one follow-up for corrections.

## 3. Debug

- **Reproduced** from the owner's report and the code (`main.rs` arms a hidden code at first start; `Claim.svelte` sends any non-empty code; `claim.rs` counts each wrong try). The red tests below prove the page's half.

## Evidence log

- **Red, `051062a`:** the tests alone, pushed to draft PR #182. `CI`, [run 45926398471](https://github.com/rikuripi/rikurinode/actions/runs/45926398471): `Full gate (Ubuntu)` Fail, as meant: Playwright `56 failed`, `507 passed`. The 56 are the 14 new page tests at each of the 4 widths and browsers, and nothing else. The owner then merged `main` into the branch (`7d53ae7`, after PR #181); [run 45927529012](https://github.com/rikuripi/rikurinode/actions/runs/45927529012) failed on the same tests.
- **Not yet proven red:** the console test `every_screen_says_the_fingerprint_is_not_the_claim_code`. The gate stops at the page step, which comes before the Rust steps, so `cargo test` did not run. It will run, green, with the fix.
- **Fix, held until the red run is seen:**
  - `Claim.svelte`: the code is normalized as `normalize` does (drop `-` and space, upper-case) and must be `CODE_LEN` symbols of `ALPHABET`; the button stays disabled otherwise. `claim.not_a_code` shows at once for a symbol outside the alphabet or more than 10, and for fewer than 10 only once the field is left. The code is sent as typed, as before.
  - `en.json`: `claim.not_a_code` (new); `claim.code_hint` names the fingerprint; `claim.wrong_code` says only the newest code works and each Enter replaces it.
  - `console.rs`: the fingerprint's heading, then "It is not the claim code: never type it." (42 columns with its indent).
  - Runbook steps 9 and 12: the same.
- **A test added with the fix, and why:** `a code half typed is not scolded until the field is left` in `owner.spec.ts`. The red tests did not fix when a too-short code is said; while writing the fix, saying it on every keystroke would scold a code half typed, so the hint waits for the field to be left, and this test holds that. No red test was changed or loosened.

## 4. Verify

### Verifier pass 1 (head `c5d233d`): FAIL, one Important

- Gate on `c5d233d`: `Full gate (Ubuntu)` Pass, [run 46044712755](https://github.com/rikuripi/rikurinode/actions/runs/46044712755): Playwright `567 passed`; `every_screen_says_the_fingerprint_is_not_the_claim_code ... ok`; Rust mutants on changed lines 2 of 2 caught (run 46044712862). The console test was never seen red (the gate stops at the page step first); it fails on `051062a` by reading.
- **Important I1:** the page's alphabet check (`NOT_IN_ALPHABET`) had no test that every symbol of `ALPHABET` is taken; dropping any of the 21 symbols not in `K7QM4XD9TR` survived, and nothing tied the page's copy to `claim.rs`. The Spec's "nothing the node accepts is refused by the page" had no test behind it.
- Nits: N1 a stale fixture in `image/tests/test_vm_drill.py:1088` (the old heading; nothing matches on it): not changed here, outside scope. N2 the record's column count and base: fixed. N3 a short code and Enter in the code field show nothing until the field is left (the disabled button is the signal): kept. N4 the runbook's wrong-code bullet in step 12: fixed. N5 the `code !== ''` mutant (a hint on an emptied field after leaving it; nothing sent): kept.

### Repair 1 (I1)

- **Tests added, and why:** `every symbol the node uses is taken` in `owner.spec.ts`, eight codes that between them use all 31 symbols, capital and small; and `the_claim_page_checks_the_same_alphabet_and_length` in `claim.rs`'s tests, which reads `ui/src/secure/Claim.svelte` and requires its `NOT_IN_ALPHABET` class, `CODE_LEN` and normalizing to match `ALPHABET`, `CODE_LEN` and `normalize`. Both close I1; neither changes or loosens another test. The page test needs no red run: it holds the fix already in place against a later drift, which the mutants show it would catch.
- The page tests' container sees only `ui/`, so the tie to `claim.rs` is on the Rust side, where the whole tree is checked out.

### Repair 2: repair 1 failed CI (`c6ffdac`)

- `CI`, [run 46045539955](https://github.com/rikuripi/rikurinode/actions/runs/46045539955): `Full gate (Ubuntu)` Fail at step 9, `cargo fmt --check`: three asserts in the new `claim.rs` test not laid out as rustfmt lays them. Playwright before it: `599 passed` (567 + the 8 new codes at 4 widths).
- `Rust mutants`, [run 46045539931](https://github.com/rikuripi/rikurinode/actions/runs/46045539931): exit 4, the baseline `cargo test` failed: `the_claim_page_checks_the_same_alphabet_and_length` could not read the page. cargo-mutants tests a copy of `control-plane/` with no `ui/` beside it, and the test built its path from `CARGO_MANIFEST_DIR`.
- **The repair:** the path comes from `RIKURI_UI_DIR`, which `build.rs` sets and the mutants workflow sets again (the way `http.rs`'s `the_ui_types_are_the_rust_types` already reads `ui/src/generated`); the asserts as rustfmt lays them (`rustfmt --edition 2024 --check` on the file, locally: no diff). The test's checks are unchanged.
- This is the second and last repair cycle (AGENTS.md §5).

### CI on `e926af7`: Pass

- `CI`, [run 46095218360](https://github.com/rikuripi/rikurinode/actions/runs/46095218360): `full-gate: all 11 steps passed`; Playwright `599 passed`; `the_claim_page_checks_the_same_alphabet_and_length ... ok`; `cargo test` `200 passed; 0 failed`.
- `Rust mutants`, run 46095218333: `2 mutants tested in 55s: 2 caught`. `OS image`, run 46095218270: success.

### Verifier pass 2 (the follow-up, `c5d233d..e926af7`): PASS

- I1 closed: a symbol dropped from the page, a changed `CODE_LEN` or a changed normalization fails `the_claim_page_checks_the_same_alphabet_and_length`, and a dropped symbol also fails `every symbol the node uses is taken`. The Rust test finds the page in the full gate and in the mutants copy (`RIKURI_UI_DIR`). No test or baseline loosened. N2 and N4 fixed.
- New nit N6: the tie checks the page's source text, not `normalize` itself. Kept: `normalize` has its own test (`claim.rs`, `normalize("k7qm-4xd9-tr")` and the others), and the Playwright tests hold the page's behaviour.

## Result

- **Pass (observed in CI):** what cannot be a claim code (the fingerprint, too few or too many symbols, `0`, `1`, `O`, `I`, `L`) is said on the page and never sent, so it spends none of the node's tries; every code the node could arm is taken, typed loosely, and sent as typed; every claim screen state says the fingerprint is not the claim code; the refusal says only the newest code works (run 46095218360; verifier PASS).
- **Not yet proven:** the console test seen red (the gate stops at the page step first; it fails on `051062a` by reading); the change on the N150 itself, which comes with the next image the owner publishes and installs.
- **Backlog, not started:** kernel audit lines over the claim screen on tty2 (an OS image change); the certificate page's Mac step on macOS 27; N1, the stale heading in `image/tests/test_vm_drill.py:1088`; N3, a short code and Enter in the code field show nothing until the field is left.
- Time: about 1 h of session time across 2026-11-26 and 2026-11-27; two repair cycles and two review rounds, both at the limit.
