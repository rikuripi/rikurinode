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
