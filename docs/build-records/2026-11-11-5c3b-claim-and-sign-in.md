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

### Red (`eba96ce`)

- Rust, on the Mac, `scripts/cargo.sh clippy --locked --all-targets`: the library's tests do not compile (5 errors: the ts-rs derives and `ErrorReply` they name do not exist yet). That is the red; CI runs the tests.
- UI: `ui/tests/owner.spec.ts` names pages, links and text keys that do not exist yet, so it fails by reading. Its red was **not observed**: no CI run exists for `eba96ce` (the branch was first pushed at `dea7dcb`), and the Mac and rikuri-drill have no Node. The Rust red above was seen on the Mac by clippy, not in CI. (Corrected in repair 1, verifier N5.)
- Python, rikuri-drill, `scripts/quality/safe-run.sh python3 -m unittest discover`:
  - `image/tests`: Ran 510, `FAILED (failures=1, errors=14)`, every one in `OwnerPagesSteps` and `OwnerPagesPost` (no `owner_pages`, `post_tls` or `WRONG_CODE`);
  - `scripts/quality/tests`: Ran 200, the 7 known errors of a copy without `.git` (`WholeRepository`, `test_this_checkout_reads_its_origin`);
  - `.claude/hooks`: Ran 91, OK.

### The fix (uncommitted at this entry)

- `http.rs`: `ErrorReply`, the refusal's typed body (JSON unchanged: `retry_after_seconds` only on a 429); ts-rs derives, test-only, on the claim and sign-in requests (secrets typed `string`), `SessionOpened` and `SessionInfo`. `ui.rs`: `/claim`, `/signin` and `/home` serve the secure page, over TLS only.
- `ui/`: `lib/api.ts` (every answer one outcome; anything not the API's shape is "unknown"), `lib/wait.svelte.ts` (the 429 countdown), `lib/says.ts`; `secure/Claim.svelte`, `SignIn.svelte`, `Home.svelte`; `Secure.svelte` leads on by the node's state (unknown: no way on is guessed); `main.ts` picks the page by path.
- `image/drill/vm_drill.py`: `owner_pages()`, run after `setup_pages()`: `/claim` and `/signin` over HTTPS with only the node's CA and a 308 in the clear; one `POST /api/claim` with `WRONG_CODE` (`0000-0000-00`, outside `claim::ALPHABET`) and a random password that is never kept, refused 401, and `/api/setup` still unclaimed. `post_tls` sends the `Origin` the node accepts.

### Test changes after red

- `image/tests/test_vm_drill.py`, `Verdict.test_every_check_names_a_step`: the three new case names added to the pinned set of checks. The red commit added each case's own tests but missed this list, which pins `EXPECTED` exactly; adding them is the same expectation, not a loosening (no case is removed or relaxed).

### Green so far

- Python, rikuri-drill, through `safe-run.sh`: `image/tests` Ran 510, OK; `scripts/quality/tests` Ran 200, only the 7 known errors above; `.claude/hooks` Ran 91, OK.
- Rust, the Mac: `scripts/cargo.sh fmt --check` clean; `clippy --locked --all-targets -- -D warnings` clean.
- Rust tests, the render and owner tests, the gate and the VM drills: Not yet proven; CI.

### CI run 1 (`dea7dcb`), and the verifier's first pass: FAIL

- `Full gate (Ubuntu)`: **Fail**, https://github.com/rikuripi/rikurinode/actions/runs/43106448504/job/130810920577:
  ```
  /ui/src/secure/Home.svelte:27:66
  Error: Property 'expires_unix' does not exist on type 'never'. (ts)
  svelte-check found 1 error and 0 warnings in 1 file
  ```
  `Rust mutants (changed lines)` failed in the same check, before any mutant ran. The tool tests (py3.9, py3.12) and the OS image build passed.
- Verifier, first pass at `dea7dcb`: FAIL.
  - **I1**: the svelte-check error above.
  - **I2**: owner.spec lacks the 413 and 400 cases, and sign-in's offline, 5xx and non-API cases, that "Done when" names; sign-out lacks offline.
  - Nits: N1 (the claim words on a claimed node); N2 (no fit or CSP check on the owner pages); N3 (named fields and no method: a missed `preventDefault` would put the password in a GET URL); N4 (sign-out's 401 said "went wrong"; an unreadable session led to sign-in, a guess); N5 (the record's red wording); and the countdown not stopped with its page.

### Repair 1 of 2

- **I1:** `$state<T>(undefined)` in place of `let x: T = $state(undefined)`. The annotated form lets TypeScript narrow the variable to `undefined` from its initializer, which makes the property `never` inside `$derived`. The same form is used on every page.
- **I2, test changes after red:** `owner.spec.ts` gains the claim's 413 and 400 cases; sign-in's 500, offline, 502 non-JSON, 413 and 400 cases; and sign-out's offline case. Each is a case "Done when" names and the red commit missed. They add to the tests and loosen none.
- **N2, a test added:** each owner page fits the screen, with every control (inputs included) at least 44 px, under the node's CSP with no violation or console error.
- **N4, tests added before the fix:** a sign-out answered 401 goes to sign-in, and an unreadable session leads nowhere. Both fail on `dea7dcb` by reading; they were not run before the fix (CI runs only on the pushed head).
- **The fix:**
  - N1: `secure.next` is shown only on an unclaimed node.
  - N3: the fields lose `name`, and the forms say `method="post"`, so a native submission sends no secret and never in a URL.
  - N4: sign-out's 401 goes to sign-in, and an unreadable session leads nowhere.
  - The countdown stops when its page goes.
