# Build Record — 5c.3b: the claim, sign-in and sign-out pages

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/5c3b-claim-pages`, from `main` at `1265136`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature |

## Why

Stage 1's first UI slice "takes the owner's sign-in (D11)": the owner claims the node from a browser and signs in with a password set on the setup page; no Linux account, no shell (D11, "Decided: web sign-in only"). 5c.3a shipped the pipeline, the certificate screen and the secure page, which ends: "Next you'll claim the node with the code on its screen, and choose your password. That comes with the next update." The API behind it exists since B0.2 (`docs/build-records/2026-10-19-b0-2-sign-in.md`): `POST /api/claim` (code and password, rate-limited, `409` once claimed), `POST /api/session` (sign-in, rate-limited), `GET /api/session` (the CSRF token), `DELETE /api/session` (sign-out, CSRF-checked). Both openings answer `201` with an `HttpOnly; Secure; SameSite=Strict` cookie and `{csrf_token, issued_unix, expires_unix}`; refusals are `{error}`, and `429` adds `retry_after_seconds` and `Retry-After`. The password rule is 12 characters to 1024 bytes (`password.rs`). The code is normalized by the server (`claim::normalize`).

The owner (2026-11-11), after "Next":
- screens: "Claim, sign-in, sign-out (Recommended)". Changing the password (step-up first) waits for a later change;
- the password: "Length rule + passphrase tip (Recommended)": the 12-character rule as they type, a passphrase tip, and what losing it means; no new package;
- the look: "Reuse Sunrise (Recommended)": the 5c.3a tokens, fonts and components; no mockup round. The owner reviews the result in the PR.

## Task Contract

1. **Outcome:** on the secure page, the owner of an unclaimed node types the code from the node's screen and chooses a password, and the node is theirs; later they sign in with that password, see that they own the node, and sign out. Every refusal says what happened and what to do, in plain words.
2. **Scope:**
   - **The pages** (`ui/`, the secure app, served only over TLS):
     - `/claim`: the claim code (as the screen shows it, `K7QM-4XD9-TR`; any case, spaces or dashes accepted, as the server normalizes), a new password typed twice, the 12-character rule shown as they type, a passphrase tip, and what losing the password means, said plainly: today nothing resets it. Once the node is claimed, its claim screen offers no new code (`console.rs`: "on a claimed node, nothing happens"), and no reset exists yet, so the page tells the owner to write the password down or keep it in a password manager. A way to reset it at the node is not this change's (noted for the owner). Submit only when the rule holds and both match.
     - `/signin`: the password, for a claimed node.
     - `/home`: "You own this node", the session's end time, and **Sign out**. The SetupHub is 5c.4: say only that setup continues in a later update.
     - The secure page (`/`, `/setup`) leads on by the node's state: unclaimed, to the claim (with the claim states of 5c.3a); claimed and signed in, to `/home`; claimed, to `/signin`.
     - Every answer handled: `201`; `401` (wrong code, or wrong password); `409` (already claimed: go to sign-in); `422` (the password rule, the server's own words); `429` (wait, with the seconds counting down; the form disabled until then); `413`/`400`; a network failure; anything else is "unknown", never a guess.
     - Passwords: `type="password"` with a show toggle, `autocomplete="new-password"` on the claim and `current-password` on sign-in, never in the URL, never logged, never kept after the request; the form cleared after a refusal of the password.
     - Forms submit by `fetch` with JSON; no `<form action>` to another origin; the CSP stays as it is (`form-action 'self'`, `connect-src 'self'`).
     - Sign-out reads the CSRF token from `GET /api/session` and sends it as the API requires.
   - **`control-plane/`:**
     - the new page paths, `/claim`, `/signin` and `/home`, serve the secure app over TLS; in the clear they redirect to HTTPS like `/setup`;
     - ts-rs types, test-only as in 5c.3a, for the shapes the pages read and send: the claim and sign-in requests (their secrets typed as `string`), the session reply, and the refusal; the refusal becomes a typed struct whose JSON is byte-identical to today's;
     - no change to the API's behaviour, its limits or its cookies.
   - **Tests, red first:**
     - Rust: the new paths over TLS (each the secure app, with the pages' headers), each a `308` in the clear; the refusal's JSON unchanged for each kind; the generated types equal to the committed ones;
     - render tests (stubbed API, under the node's CSP, phone, tablet and desktop): each page's form and its every answer above, the 429 countdown, the password rule and the match, the show toggle, the autocomplete hints, no password in any URL or request but the one `POST`, the CSRF header on sign-out, the secure page's lead-on per state;
     - text keys as in 5c.3a;
     - the VM drill: over HTTPS with only the node's CA, `/claim` and `/signin` are the secure app; `POST /api/claim` with a wrong code is `401` and the node stays unclaimed; `/claim` in the clear is a `308` to HTTPS.
   - **The knowledge layer:** the install runbook's last steps (claim the node with the code, choose the password, sign in, sign out) and README's status.
   - Risk tier: **high-risk**. The first page that takes the owner's secret, and the act that makes someone the node's owner.
   - **Not included:**
     - changing the password (step-up), and its screen;
     - naming, the UUID and the SetupHub (5c.4);
     - languages other than English;
     - a strength meter or any new package;
     - any change to the API's rules, limits, cookies or the claim code itself;
     - the backlog: the weekly OSV audit of `ui/package-lock.json`, the exception's severity pin, the image's UI audit, drill case 1's timeout.
3. **Done when:**
   - red before green: Python in rikuri-drill through `safe-run.sh`; Rust and the UI's tests red in CI (the Mac runs no tests), recorded;
   - `Full gate (Ubuntu)`, the tools' py3.9 and py3.12 jobs, Rust mutants on the changed lines, and the OS image workflow with both VM drills pass on the PR;
   - one `verifier` pass has no Important finding;
   - Not provable in CI, so Not yet proven unless the owner runs it: claiming, signing in and signing out on a real phone and laptop against the N150.
4. **Authority:**
   - the owner's words above; this branch; a draft PR; no merge;
   - `scripts/cargo.sh` for `check`, `clippy` and `fmt` on the Mac, never a test;
   - rikuri-drill over its pinned SSH key for the Python tests;
   - no package added; Node is not installed on the Mac or rikuri-drill;
   - the claim code and any password appear only as test values in tests and the disposable VM, never from a real node;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; CI at most 8 runs on the PR.

## Evidence log
