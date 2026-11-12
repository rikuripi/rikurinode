# Build Record — 5c.4a: the node's UUID and the SetupHub

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/5c4a-uuid-hub`, from `main` at `b46875b`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature |

## Why

Stage 1's first UI slice, after sign-in, "gives the node its UUID, then a SetupHub that lists what remains and marks done only what the node's real state shows" (platform plan, §5, stage 1). 5c.3b (`docs/build-records/2026-11-11-5c3b-claim-and-sign-in.md`, merged as `e4dba17`) left `/home` saying only "This node is yours", until when the session lasts, and "Setting up the rest of the node comes with the next update." Earlier records put "naming, the UUID and the SetupHub" in 5c.4.

The owner (2026-11-11), after "Next":
- the split: "Hub + UUID first (Recommended)". This task is 5c.4a, with nothing new running as root. 5c.4b is naming the node;
- for 5c.4b, not this task: the hostname is changed through a "Polkit rule (Recommended)" that lets only the control plane's user ask systemd-hostnamed; and the default name is found by "Check by name (Recommended)": the first of `rikuri01.local`, `rikuri02.local`, … that does not answer.

## Task Contract

1. **Outcome:** once signed in, the owner sees the node's own ID and a list of what setup remains. The list says what is done, what is next and what comes with a later update, and it marks a step done only when the node's real state shows it.
2. **Scope:**
   - **The UUID** (`control-plane/`, a new `node.rs`):
     - a random version-4 UUID from the OS's generator (`random.rs`), written once to its own file, `node-uuid.json`, in the state folder (`state.rs`: 0600, whole-file writes). *Clarified 2026-11-11, before any code: the contract first said `node.json`, which already holds B0.2's `instance_id`, the sessions' issuer (`boot.rs`). The UUID stays apart from it, so the claim never rewrites the file the sessions depend on, and the internal issuer is never shown;*
     - created when the node is claimed; a claimed node without one (a crash between the claim and the write) gets it on its next read;
     - never rewritten. An update never changes it, because the state folder is under `/var`. A file that cannot be read or is not a UUID is an error that is reported, never silently replaced: identity is never regenerated quietly.
   - **`GET /api/hub`** (a session required; `401` without one, as `GET /api/session`):
     - it answers `{node_id, steps: [{step, state}]}`;
     - the steps are a closed set, in order: `connection`, `owner`, `name`, `bitcoin`, `lightning`, `backup`;
     - each state is one of `done`, `next`, `later` or `unknown`, from the node's real state at the time of the request:
       - `connection` is done: the answer comes over the node's TLS;
       - `owner` is done if the owner file exists;
       - `name` is read from the running kernel (`/proc/sys/kernel/hostname`): `rikurisetup` is `next`, any other name is `done`, and a failed read is `unknown`;
       - `bitcoin`, `lightning` and `backup` are `later`;
     - no wizard state is stored. No step in 5c.4a takes input, and every state is read again on each request, so a refresh or a crash resumes by itself;
     - ts-rs types, test-only as before, for the reply.
   - **The page** (`ui/`): `/home` becomes the SetupHub. It shows:
     - the title, the node's ID and the session's end;
     - each step in plain words, with its state said in words (never by colour alone): `next` for the name says naming comes with the next update, and `unknown` says "could not be read";
     - sign-out as now.
     - Every answer of `/api/hub` is handled: `401` goes to sign-in, as the session read does; anything not of its shape is "unknown".
   - **Tests, red first:**
     - Rust: the UUID's format and version; created once and kept, never rewritten; an unreadable or malformed file refused, not replaced; created at the claim;
     - `/api/hub`: `401` without a session; the steps in order with each state, including `name` for `rikurisetup`, another name and an unreadable hostname; the types equal to the committed ones;
     - the UI's owner tests: the hub's list and its words for every state, the node's ID, a `401`, a reply that is not the hub's, and the fit and CSP check;
     - the VM drill: on the real image, `/home` over HTTPS with only the node's CA is the secure page, and `GET /api/hub` without a session is `401`.
   - **The knowledge layer:** the runbook's steps 12 and 13 (what the hub shows after the claim), and README's status.
   - Risk tier: **high-risk**. It adds an authenticated endpoint and changes the claim handler, which is on the sign-in path, and it creates the node's lasting identity.
   - **Not included:**
     - naming: the naming page, the polkit rule, the hostname change and the check by name (5c.4b);
     - back and next between wizard steps, and stored wizard state (they come with the first step that takes input);
     - a real claim in the VM drill: it would need the drill to press Enter on tty2, which it cannot yet;
     - any change to the API's existing replies, limits or cookies;
     - the backlog: M1, M2, a password reset at the node, and the earlier items.
3. **Done when:**
   - red before green, each seen: Python on rikuri-drill through `safe-run.sh`; Rust and the UI's tests in CI, on the red commit pushed on its own (5c.3b's lesson: its UI red was never seen);
   - `Full gate (Ubuntu)`, the tools' py3.9 and py3.12 jobs, Rust mutants on the changed lines, and the OS image workflow with both VM drills, all pass on the PR;
   - one `verifier` pass has no Important finding;
   - Not provable in CI, so Not yet proven unless the owner runs it: the hub on a real phone and laptop against the N150 after a claim.
4. **Authority:**
   - the owner's words above; this branch; a draft PR; no merge;
   - `scripts/cargo.sh` for `check`, `clippy` and `fmt` on the Mac, never a test;
   - rikuri-drill over its pinned SSH key for the Python tests;
   - no package added (the UUID is formatted by hand from 16 random bytes); Node is not installed on the Mac or rikuri-drill;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; CI at most 8 runs on the PR, one of them the red commit's.

## Evidence log

### Red (the commit after the contract)

- **What it holds:**
  - Rust: `node_id.rs` and `hub.rs` with stubs that compile and answer wrongly (an empty UUID, no steps, `unknown` for every name); `Config.hostname_file`, the plumbing the tests need (always `/proc/sys/kernel/hostname` on a node, set by no variable); `tests/hub_route.rs`; the types test with the four hub types; and their expected TypeScript in `ui/src/generated/`. The exported types carry plain `//` comments, not `///`, so ts-rs emits no JSDoc into the TypeScript.
  - UI: the SetupHub tests in `owner.spec.ts`. The stub helper answers `GET /api/hub` with a good hub unless a test says otherwise, because `/home` now reads it.
  - The drill: `SetupHubSteps` with its stand-in, and the two case names in the Verdict test's pinned list.
- **Rust, on the Mac:** `scripts/cargo.sh clippy --locked --all-targets -- -D warnings` exits 0, and `fmt --check` exits 0. The red is in the tests' assertions; CI runs them.
- **Python, rikuri-drill, through `safe-run.sh`:**
  - `image/tests`: Ran 514, `FAILED (failures=2, errors=12)`, every one in `SetupHubSteps` (no `setup_hub`) and `Verdict.test_every_check_names_a_step`;
  - `scripts/quality/tests`: Ran 200, only the 7 known errors of a copy without `.git`;
  - `.claude/hooks`: Ran 91, OK.
- **Rust and the UI in CI:** this commit is pushed on its own, so that CI's run of it shows the red (see "CI run 1").

### CI run 1 (`67f3c87`, the red commit alone): red, as wanted

- `Full gate (Ubuntu)`: **Fail** at step 3, the drill's tests, https://github.com/rikuripi/rikurinode/actions/runs/43120088021. In `image/tests` (Ran 514), every failure is a new one: 13 in `SetupHubSteps` (no `setup_hub`) and `Verdict.test_every_check_names_a_step`. The hooks (91) and the quality tools (200) passed. The gate stops at its first failing step, so steps 8 (the UI) and 9 (Rust) did not run.
- `Rust mutants (changed lines)`: **Fail** in its unmutated baseline, https://github.com/rikuripi/rikurinode/actions/runs/43120088034: `test result: FAILED. 141 passed; 5 failed`. The 5 are `hub::tests::every_step_in_order_with_its_state_from_the_node`, `hub::tests::the_name_is_done_only_when_the_kernel_has_another_name`, `node_id::tests::a_file_that_is_not_a_uuid_is_refused_and_never_replaced`, `node_id::tests::it_is_made_once_and_kept` and `node_id::tests::the_form_is_rfc_9562_version_4`. `the_ui_types_are_the_rust_types` passed: the hand-written TypeScript is ts-rs's output. Cargo stopped at the library's failure, so `tests/hub_route.rs` did not run.
- **What is not yet seen red:** `tests/hub_route.rs` and the UI's hub tests. So the fix goes in two pushes. Part 1 holds the drill's `setup_hub` and the self-contained logic of `node_id.rs` and `hub.rs`, with no route and no claim wiring. The gate then gets past step 3 and runs the UI's tests (red: no hub on the page), and the mutants baseline gets past the library and runs `hub_route.rs` (red: no route, no UUID at the claim). Part 2 holds the route, the claim's UUID, the page and the docs.

### Test changes after red

- `ui/tests/owner.spec.ts`: one case added to "the hub unread when …", "a step listed twice". The page keys its list by step, and Svelte refuses a repeated key, so the parser must refuse such a reply; the red commit did not ask that. It adds a case and loosens none.

### CI run 2 (`a4f8d1e`, fix part 1): the rest of the red, as wanted

- `Full gate (Ubuntu)`: **Fail** at step 8, https://github.com/rikuripi/rikurinode/actions/runs/43120587030. Steps 1 to 7 passed, the drill's tests among them. Playwright: `36 failed`, `231 passed`; the 36 are the 9 SetupHub tests at each of the 4 widths (`tests/owner.spec.ts › the SetupHub › …`); no other test failed. The UI's red is seen.
- `Rust mutants (changed lines)`: **Fail** in its baseline, https://github.com/rikuripi/rikurinode/actions/runs/43120587101. The library: `test result: ok. 146 passed; 0 failed`. `tests/hub_route.rs`: `test result: FAILED. 0 passed; 5 failed`, its 5 tests. The route's red is seen.
- The rollback drill, https://github.com/rikuripi/rikurinode/actions/runs/43120587044/job/130860881887:
  - `PASS the SetupHub over HTTPS only, with only the node's CA`;
  - `FAIL the hub refuses a browser without a session: GET /api/hub without a session: 404`: the drill's red on the real image (no route yet);
  - and, **not this change's**: `FAIL drill: timed out after 600s waiting for the broken update to roll back`. This is case 1, the same timeout as 5c.3a's run 3, which passed on a re-run and was recorded as a one-off. It has now happened twice. Nothing here touches the update, greenboot or the variants. Recorded for the owner; if it recurs in the next run, the decision is theirs.
- The USB installer drill and the image build passed.

### CI run 3 (`3e8cd5d`, fix part 2), and the verifier's first pass: FAIL

- `Full gate (Ubuntu)`: **Pass**, run 43123211807. That covers the UI's tests and every Rust test, `tests/hub_route.rs` included.
- `Rust mutants (changed lines)`: **Fail**, run 43123211701: `39 mutants tested in 4m: 3 missed, 28 caught, 8 unviable`. The 3 missed, all in `node_id.rs`:
  - `MISSED …node_id.rs:43:9: replace <impl fmt::Display for NodeIdError>::fmt -> fmt::Result with Ok(Default::default())`
  - `MISSED …node_id.rs:56:34: replace | with ^ in format_v4`
  - `MISSED …node_id.rs:57:34: replace | with ^ in format_v4`
- The image build passed. The two drills had not finished when the verifier read them.
- **Verifier, first pass at `3e8cd5d`: FAIL.**
  - **I-1:** on the real node, the name step can never be read. The service unit sets `ProcSubset=pid`, which hides `/proc/sys`, and `ProtectHostname=yes`, which gives the service its own copy of the kernel's name, frozen at its start. Both are pinned by `image/check_image_root.py`. So `/proc/sys/kernel/hostname` gives ENOENT, and the hub would say "Couldn't be read" on every real claim. The tests pointed `hostname_file` at an ordinary file and could not see it. The design read the wrong source; it was never a false "Done".
  - **I-2:** two equivalent mutants. `(b & mask) | bit` and `(b & mask) ^ bit` agree, because the mask has cleared that bit, so no test can tell them apart.
  - **I-3:** the `Display` of `NodeIdError`, the journal's only record of why the hub answers 500, has no test.
  - Nits: (1) the hub makes a UUID without a log line; (2) `parseHub` accepts an empty, partial or reordered list and any non-empty node ID; (3) the drill's `/home` check passed already at red, so it proves the page shell, not the hub; (4) the "a step listed twice" UI case was never seen red; (5) the contract says `node.rs`, the code `node_id.rs`.
  - On case 1's timeout in run 2, it found nothing in this change that could affect it.
- **The owner, on I-1** (2026-11-11): "/etc/hostname (Recommended)". The name step reads the static hostname file, which systemd-hostnamed keeps and 5c.4b's rename will write. The sandbox is not changed. Reading the live name from hostnamed can come with 5c.4b.

### Repair 1 of 2

- **Tests, committed before the fix** (each a change after red; the reasons):
  - `config.rs`: the default `hostname_file` is `/etc/hostname`, by the owner's choice above. Changed, not loosened: the source changed.
  - `hub.rs`: comment lines in `/etc/hostname` (hostname(5)) are skipped, and a file of only comments is `unknown`. Added.
  - `node_id.rs`, `each_error_says_what_went_wrong`: I-3. It passes on the code as it is; its job is to kill the `Display` mutant. Added.
  - `owner.spec.ts`: no steps, some missing, out of order, a node ID that is not a UUID (nit 2). Added.
  - `test_vm_drill.py`: a third hub case, "the control plane reads the node's name in its sandbox". It reads `/etc/hostname` as the service's user, inside the service's mount namespace, on the real image. The no-CA case now expects that check to pass, because it needs no CA. The Verdict test pins the new name. Added.
- **Red:**
  - rikuri-drill, `image/tests`: Ran 514, `FAILED (failures=4, errors=13)`, every one in `SetupHubSteps` and the Verdict pin.
  - On the Mac, `clippy --all-targets` exits 0: the Rust red is in the assertions (`config.rs`, `hub.rs`).
  - The UI's red cannot be seen in CI while the drill's tests fail at the gate's step 3; it is red by reading.
