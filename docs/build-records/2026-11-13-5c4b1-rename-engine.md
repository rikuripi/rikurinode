# Build Record — 5c.4b-1: the engine that renames the node

| | |
|---|---|
| **Date** | 2026-11-13 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/5c4b1-rename-engine`, from `main` at `a59755d`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature |

## Intent: the owner's words

- "5c.4b: rename the node (Recommended)" (2026-11-13), as the next item after 5c.4a's hub, whose name step says **Next**.
- Earlier choices for 5c.4b: "Polkit rule (Recommended)": only the control plane's user may ask systemd-hostnamed to set the name, so no new code runs as root. "Check by name (Recommended)": suggest the first free `rikuriNN.local`.
- 2026-11-13, in one batch:
  - "Small built-in client (Recommended)": the control plane talks to hostnamed over D-Bus with its own small client, not the zbus crate. It may not run other programs (ADR 0005, ADR 0014; `clippy.toml` forbids `std::process::Command`).
  - "Two tasks (Recommended)": this task is the engine. 5c.4b-2 is the page, the suggested name and the runbook.
  - "No, new name only (Recommended)": once renamed, the node no longer answers `rikurisetup.local`.
  - "Signed-in is enough (Recommended)": no step-up for a rename. The session, Origin and CSRF checks still apply.

## Task Contract

1. **Outcome:** a signed-in owner's request renames the node. After that, the hostname, mDNS, the certificate and the `Host`/`Origin` checks all use the new name, and only it, with no restart. They keep using it after a restart.
2. **Scope:** high-risk (a privileged action through polkit, and the trust boundary's names). Files:
   - `control-plane/crates/rikuri-control/src/`:
     - a new `hostname.rs`: the name's rules (one DNS label: lower-case letters, digits and inner hyphens, 1 to 63 characters) and a minimal D-Bus client over the system bus's Unix socket. It does SASL EXTERNAL from the socket's peer credentials and sends one fixed method call, `org.freedesktop.hostname1.SetStaticHostname(s name, b false)`. It reads back only a method return or an error, within a time limit. No `unsafe`, no new crate.
     - `names.rs`, `http.rs`, `address.rs`, `boot.rs`, `config.rs`, `tls.rs` and `lib.rs` as needed: the node's name read from `/etc/hostname` (the static name hostnamed writes) at start and on each of the address follower's ticks. The names the `Host`/`Origin` checks and the certificate use become `<name>.local` plus `localhost`, shared and swapped together. A new route, `PUT /api/node/name`, needs a session and the CSRF header. It checks the name, calls hostnamed, then swaps the names and re-issues the certificate at once. Its answer says what the node is now called.
     - their tests, against a stand-in bus on a socket pair.
   - `image/rootfs/`:
     - a polkit rule under `usr/share/polkit-1/rules.d/` that allows `org.freedesktop.hostname1.set-static-hostname` for the user `rikuri-control` only, and says nothing about anyone else;
     - `rikuri-control-plane.service` no longer sets `RIKURI_NAMES=rikurisetup.local` (the name comes from `/etc/hostname`), plus any key the bus needs, each pinned;
     - `image/check_image_root.py` and its tests: the rule's exact content and the unit's keys.
   - `image/drill/vm_drill.py` and its tests, a new last step:
     - polkit allows `rikuri-control` to set the static name and refuses another unprivileged user (through `busctl` in the guest, as each user);
     - after the rename, within one follower tick and with no restart, the node serves HTTPS as the new name with only its CA, refuses `Host: rikurisetup.local`, and resolved answers the new name;
     - after a restart of the control plane, the same.
   - the specs or ADR text this changes, if any, and this record.

   **Not included:**
   - the page, the suggested free name and the mDNS check of a name, the hub's name step turning Done in the browser, and the runbook (5c.4b-2);
   - a real claim in the drill;
   - any other privileged action (D13's root helper);
   - lifting the ban on spawning processes;
   - any change to the CA.
3. **Done when:**
   - red tests, committed and seen failing in CI, then passing after the fix: the name's rules; the D-Bus client's bytes on the wire and its handling of a return, an error, a refusal, a short or odd reply and a timeout; the route's refusals (no session, no CSRF, a bad name, hostnamed refusing) and its success (the names swapped, the certificate re-issued, the old name refused); names from `/etc/hostname` at start and on a tick; the image check of the rule and the unit; the drill step against a stand-in VM;
   - `Full gate (Ubuntu)` green on the PR;
   - the VM drills on the PR: the new step passes, with every earlier check as before. The route itself, called by a signed-in browser on a node, is Not yet proven here (no claim in the drill); 5c.4b-2 proves it end to end;
   - one verifier pass with hand mutations of the new checks, and the follow-up if needed.
4. **Authority:** the owner's choices above. Edit the files in Scope.
   - Tests: Rust and UI tests run only in CI; on the Mac only `scripts/cargo.sh` check, clippy and fmt. Python tests run on `rikuri-drill` through `scripts/quality/safe-run.sh` (host key pinned, as before).
   - Git: commit, push this branch, open a draft PR.
   - No change to CI workflows, the gate, the guard, `deny.toml`'s bans or `clippy.toml`.
   - Verifier: required.
5. **Limits:** this task only; at most two repair cycles and two review rounds. No budget configured: CI minutes used are reported.

## Design notes (before any edit)

- **Why the name comes from `/etc/hostname` and is read on each tick:** hostnamed writes the static name there. If the daemon reads it rather than remembering what it asked for, a rename by any route ends with the same names: runtime truth over declared truth. The unit's `ProtectHostname=yes` gives the daemon its own UTS namespace, so `uname` would not show the change. The file does.
- **Why D-Bus with no new crate:** the client sends one message whose shape never changes, and reads one reply. The wire format is fixed by the D-Bus specification: a 12-byte header, a field array and a body, little-endian. A stand-in bus checks every byte. A crate would bring a whole async D-Bus stack to audit for one call.
- **Why the polkit rule names one user and one action:** it grants exactly what the route needs. The rule returns nothing for any other subject or action, so polkit's defaults stay in force for them. Since the D-Bus call takes `interactive = false`, a refusal comes back as an error, never as a prompt.
- **Known gap, recorded:** a rename changes the certificate's names, not the CA. The browser keeps trusting the node, but a page open under `rikurisetup.local` stops working there. 5c.4b-2's page moves itself to the new name.

## Evidence log

(Filled as the work runs.)
