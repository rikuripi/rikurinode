# Build Record — 5c.4b-2: the page that names the node

| | |
|---|---|
| **Date** | 2026-11-13 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/5c4b2-rename-page`, from `main` at `1e47e60`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature |

## Intent: the owner's words

- "Start 5c.4b-2" (2026-11-13). This is the second of "Two tasks (Recommended)": 5c.4b-1 built the engine (`docs/build-records/2026-11-13-5c4b1-rename-engine.md`); this task brings the page, the suggested free rikuriNN name and the runbook.
- Earlier, for 5c.4b: "Check by name (Recommended)", meaning suggest the first of `rikuri01.local`, `rikuri02.local`, … that does not answer. Also "No, new name only (Recommended)" and "Signed-in is enough (Recommended)".
- 2026-11-13, in one batch:
  - "Ask resolved (Recommended)": the control plane asks systemd-resolved over D-Bus whether a name answers on mDNS. It reuses 5c.4b-1's small client with one more fixed call, and needs no polkit rule and no multicast socket of its own.
  - "Go there, sign in (Recommended)": after the rename, the page names the new address and opens `https://<new>.local/signin`, where the owner signs in again. No session or token moves between names.
  - "Suggest, editable (Recommended)": the free rikuriNN is filled in and the owner may change it. A typed name goes through the same rules and the same free-name check.
  - "During setup only (Recommended)": the node can be renamed only while the hub's name step says Next. Renaming a named node later is a backlog task.

## Task Contract

1. **Outcome:** during setup, a signed-in owner opens the hub's name step and sees a free `rikuriNN` suggested. They keep it or type their own. Once the node is renamed, the owner's browser goes to the new name to sign in, and the hub's name step says Done.
2. **Scope:** high-risk. It adds a new call from the control plane over the system bus, and it changes when the trust boundary's names may change (the rename route gains two refusals). Files:
   - `control-plane/crates/rikuri-control/src/`:
     - `hostname.rs`: one more fixed call, `org.freedesktop.resolve1.Manager.ResolveHostname(i 0, s "<name>.local", i AF_UNSPEC, t flags)`.
       - The flags: mDNS over IPv4 and IPv6 only, with no synthesis and no cache. Their values are pinned against systemd's documented constants.
       - Its outcome is **taken** (a method return), **free** (resolved's own not-found or timeout errors, named exactly) or **unknown** (any other error, a refusal, a bad reply, or our time limit). Unknown is never read as free.
       - It goes through the same reader, the same limits and the same `Hello`, with no new crate and no `unsafe`.
     - `http.rs`:
       - `GET /api/node/name/suggestion` (session needed) returns the first free name from `rikuri01` to `rikuri99`. It checks them in order and stops at the first free one, at most one at a time, with an overall time limit.
         - `{"name": "rikuriNN"}`;
         - `{"name": null}` when all are taken or the time limit runs out. The page then asks the owner to type one.
         - 503 when resolved cannot be asked: never a guess.
       - `PUT /api/node/name` (5c.4b-1) gains two refusals before hostnamed is called:
         - 409 `"the node already has a name"` unless the static name is `rikurisetup` (during setup only);
         - 409 `"that name is already in use on this network"` when the name is taken, and 503 when that is unknown.
     - `names.rs`, `hub.rs` and `config.rs` (the bus socket): only as needed. Plus their tests, against the stand-in bus (`tests/common/bus.rs`), which learns resolved's answers.
   - `ui/`:
     - a naming page at `/name` (served by `src/ui.rs`, like `/home`): it fills in the suggestion, lets the owner change it, checks it against the name's rules, and renames;
     - on success it shows the new name and `https://<new>.local`, then opens `https://<new>.local/signin`;
     - on a refusal it says why in words. A reply it does not understand shows "couldn't rename", never success;
     - the hub's name step links to `/name` while it says Next;
     - `en.json` texts, the generated types, and the Playwright tests at phone, tablet and desktop widths under the node's CSP.
   - `image/drill/vm_drill.py` and its tests, extending 5c.4b-1's rename step:
     - the suggestion on the drill's network, where no other node answers, is `rikuri01`, and the drill renames to it;
     - a second rename is refused with 409;
     - inside the guest, `resolvectl query -p mdns --synthesize=no rikuri01.local` answers. This shows resolved's mDNS zone holds the new name. It does not show another device receiving it (the drill's network has no peer), so that part stays Not yet proven until the N150. **Dropped at repair 1** (see the amendment below).
   - `docs/runbooks/install-node.md`: the naming step for a novice (the suggested name; signing in again at the new name; what to do if the new name isn't found), and what README.md says about naming.
   - this record.

   **Not included:**
   - renaming a named node (backlog);
   - moving a session or token between names;
   - an mDNS responder or multicast socket in the control plane;
   - any other privileged action;
   - the hub's other steps;
   - any change to the CA, the polkit rule or the engine's D-Bus call to hostnamed.
3. **Done when:**
   - red tests, committed and seen failing in CI, then passing after the fix:
     - the `ResolveHostname` call's bytes on the wire, and its three outcomes from each kind of answer;
     - the suggestion's order, stop and limits, and its 503;
     - the rename's new refusals (named already; taken; unknown), and that hostnamed is never called after any of them;
     - the page: suggestion, edit, the rules, success and the redirect, each refusal, and an unreadable reply;
     - the drill's step against a stand-in VM;
   - `Full gate (Ubuntu)` green on the PR, including the UI's build, audit and Playwright steps;
   - the VM drills on the PR: the suggestion is `rikuri01`, the rename and the second rename's refusal happen as above, ~~resolved's mDNS answers the new name in the guest~~ (dropped at repair 1), and every earlier check passes as before;
   - one verifier pass with hand mutations of the new checks, and the follow-up if needed.
4. **Authority:** the owner's choices above. Edit the files in Scope.
   - Tests: Rust and UI tests run only in CI; on the Mac, only `scripts/cargo.sh` check, clippy and fmt. Python tests run on `rikuri-drill` through `scripts/quality/safe-run.sh` (host key pinned, as before).
   - Network: read systemd's documentation of resolve1 for the method's signature and flag values (data only).
   - Git: commit, push this branch, open a draft PR.
   - No change to CI workflows, the gate, the guard, `deny.toml`'s bans, `clippy.toml`, npm dependencies or `ui/audit-exceptions.json`.
   - Verifier: required.
5. **Limits:** this task only; at most two repair cycles and two review rounds. No budget configured: CI minutes used are reported.

### Amendment, 2026-11-13, at repair 1: the owner's choice

- The drill's check "resolved's mDNS answers the new name" (`resolvectl query -p mdns --synthesize=no` in the guest) is dropped from Scope and from Done when. The owner chose "Drop it, N150 (Recommended)".
- **Why:** on the PR's drill, resolved answered `No appropriate name servers or networks for name found`. Recalled from resolved's source, not observed: it never looks up the machine's own hostname over mDNS, since its own names are what synthesis is for. So the node cannot ask itself. The drill's network has no second device to ask from.
- So **another device finding the new name stays Not yet proven** until the N150 install, as in 5c.4b-1.

## Design notes (before any edit)

- **resolved's call** (`org.freedesktop.resolve1(5)`, systemd 262, read as data):
  - `ResolveHostname(in i ifindex, in s name, in i family, in t flags, out a(iiay) addresses, out s canonical, out t flags)` on `/org/freedesktop/resolve1`, interface `org.freedesktop.resolve1.Manager`.
  - The flags are `SD_RESOLVED_MDNS_IPV4` (1 << 3), `MDNS_IPV6` (1 << 4), `NO_SYNTHESIZE` (1 << 11) and `NO_CACHE` (1 << 12): 6168, or `0x1818`. `NO_ZONE` is left off, so the node's own name answers from its own zone.
  - The page documents no polkit check on `ResolveHostname`.
  - The client reads only the reply's kind. A method return means the name is taken; it never parses the addresses.
- **Not documented, so the drill must observe it:** which error resolved gives for an mDNS name that nothing answers.
  - The man page lists `DnsError.NXDOMAIN` and others, but names no timeout error.
  - From memory of resolved's source, not from the page: a lookup that runs out of attempts answers `org.freedesktop.DBus.Error.Timeout`.
  - `FREE` holds both names. The drill keeps the real answer for an unused name (`rikuri98.local`, as `nobody`, through `busctl`) in its evidence.
  - If the real name is neither, the suggestion is `Unknown`, so the API answers 503 and the drill's check fails. That is a visible failure, never a guess.
- **Unknown is never free.**
  - Any other error, a transport failure or the time limit is `Unknown`.
  - The suggestion stops at the first `Unknown` (503), and the rename refuses with 503 before hostnamed is asked.
  - A node with no network sees every name as free (resolved times out), and could take a name a node out of reach already has. That is accepted: such a node has no peer to clash with.
- **During setup only** is enforced by the API, not only by the page: `PUT /api/node/name` refuses with 409 unless the static name is `rikurisetup`. A node named by mistake cannot be renamed until the backlog task "rename a named node" is done.
- **The page** reads the session (401 goes to `/signin`) and the hub. If the name step is not Next, it says the node is named and links back to `/home`, with no form and no suggestion asked.
  - Otherwise it asks for the suggestion and fills it in; the owner may change it.
  - The name's rules are checked in the page before sending: one label, letters, digits and inner hyphens, at most 63 characters, not `localhost`. It is sent in lower case.
  - On success the page shows the new address and a link to `https://<host>/signin`, then opens it. A reply that is not exactly `{name, host}` is a failure, never success.
- **Old tests changed in the red commit itself, each with its reason:**
  - `RenameSteps.CASES` and `Verdict`'s list of checks gain the three new checks;
  - the good-node test's write list gains the second, refused rename;
  - "hostnamed did not keep the rename" lists the new checks' results;
  - the stand-in `RenameDrill` answers the suggestion and refuses a named node, as the daemon now will.

  No assertion is loosened. The Rust and UI tests of 5c.4b-1 are untouched. The stand-in bus answers lookups "free" by default, so the old route tests keep their meaning.

## Evidence log

### Red (the tests with stubs)

- **Rust:**
  - `hostname.rs`: stubs for `resolve_hostname_call` (sends nothing), `lookup` and `name_answers` (always `Unknown`), `candidates` (none) and `suggest` (an error). `SUGGEST_LIMIT` is 1 s, against the 30 s the test wants.
  - `http.rs`: `GET /api/node/name/suggestion` always answers `{"name": null}`, and the rename has no new refusal.
  - `ui.rs`: no `/name`.
  - On the Mac: clippy (`--all-targets`, `-D warnings`) and fmt exit 0. The tests run in CI.
- **UI:** the new Playwright tests, with no page yet. The types `Renamed` and `NameSuggestion` are generated by hand, and the Rust test of the types compares them.
- **Drill:** `LOOKUP_UNUSED`, `MDNS_QUERY`, `mdns_answers` and `again_refused` are stubs. On `rikuri-drill`, through `safe-run.sh`: `test_vm_drill.py` gives `Ran 159 tests`, `FAILED (failures=14, errors=19)`, all in `RenameSteps`, `RenameSetupReads` and `Verdict`'s list.
- **CI on `bd06b80`** ([PR #93](https://github.com/rikuripi/rikurinode/pull/93)):
  - `Full gate (Ubuntu)`: **Fail**, as wanted, [run 43522244517](https://github.com/rikuripi/rikurinode/actions/runs/43522244517). It failed at step 3, on the drill's tests: `KeyError: 'the node suggests the first free name'`, the stubs' assertions, and `Verdict`'s list.
  - The gate stops at its first failing step, so the UI's red (step 8) and the Rust integration tests (step 9) did not run there. **The UI's red is Not yet proven in CI.**
  - `Rust mutants (changed lines)`: its unmutated baseline is the Rust red, [run 43522244564](https://github.com/rikuripi/rikurinode/actions/runs/43522244564): `test result: FAILED. 164 passed; 9 failed`. The 9 are:
    - the eight new `hostname.rs` unit tests;
    - `the_ui_types_are_the_rust_types`. This was a fault in the red's plumbing, not a red test: ts-rs copies a `///` comment into the type it writes. The comment is now `//`, in the fix.

### Fix

- **Rust:**
  - `hostname.rs`: `resolve_hostname_call` (with `Wire::u64`), `lookup`, `name_answers`, `candidates` and `suggest`, with `SUGGEST_LIMIT` at 30 s. The call path is shared with the rename (`call`, `exchange` taking the call's bytes).
  - `http.rs`: the suggestion route, and the rename's two refusals before hostnamed is asked.
  - `ui.rs`: `/name`.
- **UI:**
  - `Name.svelte`;
  - `api.ts`: `nodeName`, `parseSuggestion`, `parseRenamed`, `readSuggestion` and `renameNode`;
  - `main.ts`: the page at `/name`;
  - the hub's link to it;
  - fifteen texts.
- **Drill:** `LOOKUP_UNUSED`, `MDNS_QUERY`, `mdns_answers`, `again_refused`, and the three checks in `rename()`.
  - **Found by the tests:** the second rename first asked for `rikuri02`. On a node that wrongly allowed it, every later check would then see the wrong name. It now asks for `rikuri01` again, which changes nothing on such a node, so only its own check fails.
- **Docs:** the runbook's new step 13 (naming the node, signing in again at the new name, and what to do when a name is taken, unchecked or not found), and README.md.
- **Test changes after red, each with its reason** (`test_vm_drill.py` only; no assertion is loosened):
  - `kernel_follows=False` now fails "resolved's mDNS answers the new name" too. resolved publishes the kernel's name, so a kernel that did not follow leaves mDNS on the old name. That is a real second failure, not a looser test.
  - `other_renames=True` moved to its own test. A node another user renamed is named, so the node now refuses the owner's rename too, and only the suggestion (asked first) passes. The test says exactly that.
  - For `rename_status` 503 and 403, the suggestion passes: it is asked before the rename, so a failed rename does not make it fail.
- On `rikuri-drill`, through `safe-run.sh`: every `image/tests` test, `Ran 554 tests`, `OK`. On the Mac: clippy and fmt exit 0, and `git diff --check` is clean. The Rust and UI tests run in CI.

### CI on `6dc3d7c` (the fix): Fail, three causes

- [PR #93](https://github.com/rikuripi/rikurinode/pull/93).
- **`Full gate (Ubuntu)`: Fail**, [run 43522909588](https://github.com/rikuripi/rikurinode/actions/runs/43522909588), at step 8.
  - `svelte-check found 0 errors and 0 warnings`.
  - Playwright: `4 failed`, `383 passed`. The failure is the same at every width: `a name the node would refuse is not sent: "64 letters"`.
  - **Cause:** the field's `maxlength="63"` cut the typed 64 letters to 63, a valid name, which was then sent. A real defect, caught by the test.
  - Step 9 (Rust) did not run there.
- **`Rust mutants (changed lines)`: Fail**, [run 43522909688](https://github.com/rikuripi/rikurinode/actions/runs/43522909688).
  - The unmutated baseline (every Rust test, the integration tests included) passed.
  - `41 mutants tested in 5m: 3 missed, 24 caught, 14 unviable`.
  - The three missed mutants are all `hostname.rs:233`, `replace | with ^` in `LOOKUP_FLAGS`. With bits that do not overlap, `^` is `|`: equivalent mutants that no test can catch.
- **The rollback drill: Fail on one check**, [run 43522909610](https://github.com/rikuripi/rikurinode/actions/runs/43522909610).
  - **Pass:** the owner renames the node, and no other user can (`PUT /api/node/name: 200 {"name":"rikuri01","host":"rikuri01.local"}`).
  - **Pass:** the node suggests the first free name (`200 {"name":"rikuri01"}`). resolved's answer for a name nothing answers, through `busctl`, was `Call failed: All attempts to contact name servers or networks failed`. That is the timeout error `FREE` counts as free, so **the design's one assumption from memory held on a real node.**
  - **Pass:** a named node is not renamed again (`409 {"error":"the node already has a name"}`, `/etc/hostname` still `rikuri01`).
  - **Pass:** the new name only, at once and after a restart.
  - **Fail:** resolved's mDNS answers the new name: `rikuri01.local: resolve call failed: No appropriate name servers or networks for name found`. See the amendment above.
  - Every earlier check passed, with cases 1, 2b and 3 among them.
- The USB installer drill and the image build: Pass.

### Repair 1 (of 2)

- **The page:** no `maxlength`. A name over 63 characters reaches the page's rule check, which refuses it with `name.rule`, as the test wants.
- **`LOOKUP_FLAGS`** is written as `0x1818`. Reason for this test change after red: its test also checks the value equals `MDNS_IPV4 | MDNS_IPV6 | NO_SYNTHESIZE | NO_CACHE`, and each flag's bit. This adds assertions and loosens none.
- **The drill:** the mDNS check, `MDNS_QUERY` and `mdns_answers` are removed, on the owner's choice. Reason for these test changes after red: the stand-in's `mdns_follows`, the readers' tests, and `kernel_follows`' and "hostnamed did not keep" expectations of that check go with it. The check no longer exists; no other assertion changed.
- On `rikuri-drill`, through `safe-run.sh`: `image/tests`, `Ran 552 tests`, `OK`. On the Mac: clippy and fmt exit 0, and `git diff --check` is clean.
