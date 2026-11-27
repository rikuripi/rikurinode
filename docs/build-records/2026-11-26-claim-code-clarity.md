# Build Record — the claim code, kept apart from the fingerprint: the page checks a code's shape before sending, and the screen says the fingerprint is not typed (stage 1, 5c)

| | |
|---|---|
| **Date** | 2026-11-26 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/claim-code-clarity`, from `main` at `fdefa4d`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at close-out) |
| **Status** | IN PROGRESS |
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

- **Red, `051062a`:** the tests alone, pushed to draft PR #182. CI's result: (to come).
- **Fix, held until the red run is seen:**
  - `Claim.svelte`: the code is normalized as `normalize` does (drop `-` and space, upper-case) and must be `CODE_LEN` symbols of `ALPHABET`; the button stays disabled otherwise. `claim.not_a_code` shows at once for a symbol outside the alphabet or more than 10, and for fewer than 10 only once the field is left. The code is sent as typed, as before.
  - `en.json`: `claim.not_a_code` (new); `claim.code_hint` names the fingerprint; `claim.wrong_code` says only the newest code works and each Enter replaces it.
  - `console.rs`: the fingerprint's heading, then "It is not the claim code: never type it." (45 columns).
  - Runbook steps 9 and 12: the same.
- **A test added with the fix, and why:** `a code half typed is not scolded until the field is left` in `owner.spec.ts`. The red tests did not fix when a too-short code is said; while writing the fix, saying it on every keystroke would scold a code half typed, so the hint waits for the field to be left, and this test holds that. No red test was changed or loosened.
