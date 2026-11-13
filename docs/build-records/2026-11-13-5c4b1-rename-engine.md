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
   - `image/drill/vm_drill.py` and its tests, a new last step (amended 2026-11-13, below):
     - polkit refuses the rename to another unprivileged user (`nobody`, through `busctl`, never interactive), and the name stays;
     - the drill claims the node with a code armed at the console (`rearm-claim`, run as the service's user; the code is kept in memory, never in the evidence) and renames it through `PUT /api/node/name`: the daemon's own D-Bus client, polkit's rule and hostnamed together. `/etc/hostname` and the kernel's name (which resolved's mDNS answers, as 5c.2's check reads it) are then the new name;
     - with the same service process, the node serves HTTPS as the new name with only its CA and lists only it, and refuses `rikurisetup.local` by its certificate and by its `Host` check;
     - after a restart of the control plane, the same.
   - the specs or ADR text this changes, if any, and this record.

   **Not included:**
   - the page, the suggested free name and the mDNS check of a name, the hub's name step turning Done in the browser, and the runbook (5c.4b-2);
   - any other privileged action (D13's root helper);
   - lifting the ban on spawning processes;
   - any change to the CA.
3. **Done when:**
   - red tests, committed and seen failing in CI, then passing after the fix: the name's rules; the D-Bus client's bytes on the wire and its handling of a return, an error, a refusal, a short or odd reply and a timeout; the route's refusals (no session, no CSRF, a bad name, hostnamed refusing) and its success (the names swapped, the certificate re-issued, the old name refused); names from `/etc/hostname` at start and on a tick; the image check of the rule and the unit; the drill step against a stand-in VM;
   - `Full gate (Ubuntu)` green on the PR;
   - the VM drills on the PR: the new step passes, with every earlier check as before;
   - one verifier pass with hand mutations of the new checks, and the follow-up if needed.
4. **Authority:** the owner's choices above. Edit the files in Scope.
   - Tests: Rust and UI tests run only in CI; on the Mac only `scripts/cargo.sh` check, clippy and fmt. Python tests run on `rikuri-drill` through `scripts/quality/safe-run.sh` (host key pinned, as before).
   - Git: commit, push this branch, open a draft PR.
   - No change to CI workflows, the gate, the guard, `deny.toml`'s bans or `clippy.toml`.
   - Verifier: required.
5. **Limits:** this task only; at most two repair cycles and two review rounds. No budget configured: CI minutes used are reported.

### Amendment, 2026-11-13, before the red commit

The contract first left "a real claim in the drill" out, so the route on a node would have been Not yet proven, and the drill would have shown polkit's rule only through `busctl`. The survey then found that `rearm-claim` prints a fresh code at the console. So the drill can claim the node itself, and call the route as the owner's browser will. This proves the daemon's own D-Bus client against the real bus, inside the service's real sandbox and SELinux context, which `busctl` from an SSH shell would not. The amendment adds no authority and no file outside Scope. It only moves a check from Not yet proven to the drill. The owner is told in the report.

## Design notes (before any edit)

- **Why the name comes from `/etc/hostname` and is read on each tick:** hostnamed writes the static name there. If the daemon reads it rather than remembering what it asked for, a rename by any route ends with the same names: runtime truth over declared truth. The unit's `ProtectHostname=yes` gives the daemon its own UTS namespace, so `uname` would not show the change. The file does.
- **Why D-Bus with no new crate:** the client sends one message whose shape never changes, and reads one reply. The wire format is fixed by the D-Bus specification: a 12-byte header, a field array and a body, little-endian. A stand-in bus checks every byte. A crate would bring a whole async D-Bus stack to audit for one call.
- **Why the polkit rule names one user and one action:** it grants exactly what the route needs. The rule returns nothing for any other subject or action, so polkit's defaults stay in force for them. Since the D-Bus call takes `interactive = false`, a refusal comes back as an error, never as a prompt.
- **Known gap, recorded:** a rename changes the certificate's names, not the CA. The browser keeps trusting the node, but a page open under `rikurisetup.local` stops working there. 5c.4b-2's page moves itself to the new name.

## Evidence log

### Red (`0e7adec`, the tests with stubs)

- **What it holds:**
  - Rust: `hostname.rs` as a stub with the public surface (every answer wrong), `LiveNames` that never reads the hostname file, and, as plumbing, the follower, `Config.bus_socket` and `PUT /api/node/name`. Tests: `hostname.rs`'s unit tests (the name's rules, golden bytes for `Hello` and `SetStaticHostname`, the reader), `names.rs`'s `LiveNames` tests, `tests/rename.rs` against a stand-in bus (`tests/common/bus.rs`).
  - `tests/address_change.rs` now passes the booted follower to `follow`, whose signature changed. The assertions are the same.
  - Python: the image check's tests (the polkit rule, the unit without `RIKURI_NAMES`) and the drill's rename step against a stand-in node. None of the image's files, checks or drill code.
- **Rust, on the Mac:** `scripts/cargo.sh clippy --locked --all-targets -- -D warnings` and `fmt --check` exit 0. The Rust red is CI's.
- **Python, rikuri-drill, through `safe-run.sh`:** `image/tests`: `Ran 549 tests`, `FAILED (failures=4, errors=30)`. Every one is a new or changed 5c.4b-1 test: `RenameReads`, `RenameSteps`, the two polkit-rule tests, the unit's two tests, and `Verdict.test_every_check_names_a_step`.
- **CI on `0e7adec`:**
  - `Full gate (Ubuntu)`: **Fail**, as wanted, [run 43485803729](https://github.com/rikuripi/rikurinode/actions/runs/43485803729) (job 132093787987). The gate stopped at `image/tests`, `Ran 549 tests`, `FAILED (failures=4, errors=30)`, the same as on rikuri-drill. So it never reached the Rust steps.
  - The Rust red is the mutants job's baseline, [run 43485803869](https://github.com/rikuripi/rikurinode/actions/runs/43485803869) (job 132093786592): `test result: FAILED. 151 passed; 11 failed`. The failures are the nine `hostname::tests` that need a real answer, and two of `names::tests`.
  - Four new library tests pass on the stub, as they should: the refusal tests, which a stub that refuses everything meets (`what_this_client_does_not_read_is_refused`, `a_message_over_the_limit_is_refused_before_it_is_read`, `anything_else_is_not_a_name`, `no_file_or_no_node_name_leaves_the_configured_names`). They prove their worth against the fix and the mutations.
  - **Not seen red:** the `--lib` failure stopped cargo before the integration tests, so `tests/rename.rs` was not run on the stub. The same gap 5c.2's verifier noted (its nit 1). Its tests are proven only green, after the fix, and by the verifier's mutations.
  - The image workflow passed on the red commit. Its drill runs the old drill code, which the red commit did not change.

### Fix (`d0072f9`)

- `hostname.rs`, `names.rs` (`compose` reads the file), `check_image_root.py`, `vm_drill.py`, the polkit rule, and the unit without `RIKURI_NAMES`.
- **No test changed after red.** The test modules of `hostname.rs` and `names.rs` are identical to `0e7adec`'s, compared by `diff`.
- On the Mac: clippy and fmt exit 0.
- On rikuri-drill, through `safe-run.sh`:
  - `image/tests`: `Ran 549 tests`, `OK`.
  - `scripts/quality/tests`: `FAILED (failures=1, errors=15, skipped=1)`, the same list as `main`'s copy at `a59755d` run the same way: the copy has no `control-plane/`, `ui/`, `.claude/` or git. CI runs them on a checkout.
