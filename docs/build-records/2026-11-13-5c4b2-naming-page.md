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
     - inside the guest, `resolvectl query -p mdns --synthesize=no rikuri01.local` answers. This shows resolved's mDNS zone holds the new name. It does not show another device receiving it (the drill's network has no peer), so that part stays Not yet proven until the N150.
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
   - the VM drills on the PR: the suggestion is `rikuri01`, the rename and the second rename's refusal happen as above, resolved's mDNS answers the new name in the guest, and every earlier check passes as before;
   - one verifier pass with hand mutations of the new checks, and the follow-up if needed.
4. **Authority:** the owner's choices above. Edit the files in Scope.
   - Tests: Rust and UI tests run only in CI; on the Mac, only `scripts/cargo.sh` check, clippy and fmt. Python tests run on `rikuri-drill` through `scripts/quality/safe-run.sh` (host key pinned, as before).
   - Network: read systemd's documentation of resolve1 for the method's signature and flag values (data only).
   - Git: commit, push this branch, open a draft PR.
   - No change to CI workflows, the gate, the guard, `deny.toml`'s bans, `clippy.toml`, npm dependencies or `ui/audit-exceptions.json`.
   - Verifier: required.
5. **Limits:** this task only; at most two repair cycles and two review rounds. No budget configured: CI minutes used are reported.
