# Build Record — 5c.4b-1: the engine that renames the node

| | |
|---|---|
| **Date** | 2026-11-13 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/5c4b1-rename-engine`, from `main` at `a59755d`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `dd66328` and `283bc43` contract, `0e7adec` red, `d0072f9` fix, `7e02605` record, `568bd1c` repair 1, `628b573` repair 2, `18c21c6` nit 5 dropped, and this close-out |
| **Status** | DONE |
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

### CI on `7e02605` (the fix): one racy test; the drill passed

- `Full gate (Ubuntu)`: **Fail**, run 43488038984 (job 132101595466). Every Rust test passed but one, `tests/rename.rs` `anything_but_an_answer_is_an_error`:
  `Hangs: Err(Io(Os { code: 32, kind: BrokenPipe, message: "Broken pipe" }))`.
  The Rust mutants job failed on the same test in its unmutated baseline (run 43488039124, job 132101596315), so no mutant was tested.
- **Cause: the test, not the client.** The stand-in's `Hangs` closed the socket right after `OK`. The client's write of `BEGIN` and its two calls then races its read: EPIPE gives `Io`, end of file gives `Protocol`. Both are correct failures, and the test pinned one.
- The image workflow: **Pass**, run 43488038824. The rollback drill (job 132102951899) ran the new step on the image, and all three checks passed:
  - `PASS the owner renames the node, and no other user can`: as nobody, `exit 1`, `Call failed: Access denied as the requested operation requires interactive authentication…`. `/etc/hostname` was still `rikurisetup`. Claimed; `PUT /api/node/name: 200 {"name":"rikuri01","host":"rikuri01.local"}`. Then `/etc/hostname` and the kernel's name were both `rikuri01`.
  - `PASS the new name only, at once and with no restart`: as `rikuri01.local`, `200` and claimed. As `rikurisetup.local`, refused: `Hostname mismatch`. `Host: rikurisetup.local`: `421`. `MainPID=695` before and after.
  - `PASS the new name only, after a restart`: the same answers, `MainPID=695 -> 1643`.
  - So the daemon's own D-Bus client, polkit's rule and hostnamed work together on the image, in the service's sandbox.

### Repair 1 (of 2): the stand-in's `Hangs` made deterministic

- **Test change after red, and its reason:** `tests/common/bus.rs`: `Hangs` now reads `BEGIN` and both calls, then closes with no answer, so the client always reads the end. No assertion changed: `Hangs` must still be `BusError::Protocol`. The race was in the stand-in, and the client is right on both of its paths.
- On the Mac: clippy and fmt exit 0.

### CI on `568bd1c` (repair 1): Pass

- `Full gate (Ubuntu)`, run 43493692900: success (`tests/rename.rs`: `8 passed; 0 failed`).
- OS image, run 43493692877: success. The rollback drill shows 38 PASS and 0 FAIL, the three rename checks among them (`MainPID=688` before and after; `688 -> 1646` across the restart).
- Rust mutants, run 43493692858: success, with 178 mutants: 139 caught, 14 missed, 23 unviable, 2 timeouts. See the verifier's note on the job's exit codes below.

### The verifier's first pass, at `568bd1c`: FAIL, on test adequacy only

- **No defect in the code.** The trust boundary, the polkit rule and its image check, the D-Bus client against the specification, the locks, and the drill's secrecy were all checked and found sound. The route's refusals and the live drill: Pass.
- **Important, each a surviving mutant in a refusal or a validation (REVIEW.md, high-risk):**
  1. and 2. `hostname.rs` `read += n` -> `*=`, and `>` -> `==`: no test sent more than `MAX_READ`.
  3. The arm refusing an error name of type `u32`: the test meant for it failed on later bytes, by accident.
  4. The arm refusing an error to `Hello`: no stand-in sent one.
  5. `vm_drill.py` `named_only` with `old` dropped: no case kept the old name in the certificate.
- **Nits:**
  1. Survivors that only tighten a limit, or touch message text or a log line (the limits' values; `>` -> `>=` at the read limit; the auth line's `>`; the three `Display` impls; a method call as `Kind::Call`; the start warning's condition). In Python, the claim and rename status checks are equivalent, and the restart retry is a timing gap.
  2. README.md:89 still said `RIKURI_NAMES` lists the node's names.
  3. `own_uid()` relies on who owns `/proc/self`: it fails closed if the process becomes non-dumpable.
  4. Nothing observes mDNS answering the new name. The drill reads the kernel's name, which resolved announces.
  5. A reload that loses the node's name logs only at info level, and the start warning could fire wrongly.
- **A defect outside this task, for the owner:** `.github/workflows/mutants.yml:86` accepts cargo-mutants' exit code 3. Here 2 timeouts produced exit 3 and masked 14 missed mutants, so the check went green. Fixing it is its own control task.

### Repair 2 (of 2): the tests the verifier asked for

- **Test changes after red, each with its reason (verifier, first pass):**
  - `hostname.rs` `an_error_name_that_is_a_u32_is_refused`: a well-formed `u32` error name reaches its own refusal (Important 3).
  - `the_limits_are_what_the_design_says` pins `MAX_MESSAGE`, `MAX_READ` and `BUS_TIMEOUT` (nit 1).
  - `tests/rename.rs` and `tests/common/bus.rs`:
    - `Answer::Flood` answers `Hello`, then sends signals in 4093-byte writes, past `MAX_READ`, and never answers. The client must stop with `Protocol("more than a rename's answer")` well inside the time limit (Important 1 and 2).
    - `Answer::HelloError` answers `Hello` with an error, which must be `Refused` at once (Important 4).
  - `test_vm_drill.py`:
    - the stand-in gains `cert_keeps_old`, a certificate holding both names (Important 5);
    - its `/api/setup` now lists the names its Host check uses, as the daemon's does, not the certificate's. Without this second change, the new case failed through the names list, and the certificate check was still not the deciding one: dropping `old` survived (`Ran 155 tests … OK`, rikuri-drill). With it, that mutant fails `cert_keeps_old`, and every earlier case gives the same results.
  - No assertion was loosened.
- **Code (nit 5), later dropped:** `LiveNames` warned whenever the file named no node name, at the start and on a reload that lost it. See "CI on `628b573`" below.
- **Docs (nit 2):** README.md says the name comes from `/etc/hostname` and names `PUT /api/node/name`.
- **Not changed, recorded:**
  - nit 1's other survivors, which only tighten a limit or change log text;
  - nit 3: `own_uid` fails closed, and the drill proves it works on the node; `AUTH EXTERNAL` with an empty response is the alternative, noted for later;
  - nit 4: mDNS answering the new name is **inferred** from the kernel's name, not observed. 5c.4b-2's mDNS check of a name is where it can be seen.
- On rikuri-drill, through `safe-run.sh`: `image/tests`, `Ran 549 tests`, `OK`. Important 5's mutant now fails (`FAILED (failures=1)`, in `cert_keeps_old`). On the Mac: clippy and fmt exit 0. The Rust kills are for CI's mutants job and the follow-up pass.

### CI on `628b573` (repair 2, PR #91): mutants Fail on nit 5 only; nit 5 dropped

- PR #90 was merged at `568bd1c` before repair 2 was pushed, so repair 2 went to draft PR #91.
- `Full gate (Ubuntu)`: **Pass**, [run 43504349040](https://github.com/rikuripi/rikurinode/actions/runs/43504349040). The image build, the USB installer drill and the rollback drill: **Pass**, [run 43504349146](https://github.com/rikuripi/rikurinode/actions/runs/43504349146).
- `Rust mutants (changed lines)`: **Fail**, [run 43504348895](https://github.com/rikuripi/rikurinode/actions/runs/43504348895), `7 mutants tested in 76s: 3 missed, 4 unviable`. All three missed mutants are nit 5's warning:
  - `names.rs:128:12: delete ! in LiveNames::load`;
  - `names.rs:167:16: delete ! in LiveNames::reload`;
  - `names.rs:192:5: replace warn_unnamed with ()`.

  No test in the repository can see log output, so no test could catch them.
- Both repair cycles were used, so this went to the owner. The owner chose "Drop nit 5": `names.rs` is back to `main`'s text (as merged in #90), and nothing else changes. This removes a change that was outside the verifier's Important findings; it is not a third repair.
- Backlog, not started: a warning when a reload loses the node's name, with a test that captures logs.

### CI on `18c21c6` (nit 5 dropped): Pass

- `Full gate (Ubuntu)`: **Pass**, [run 43509784804](https://github.com/rikuripi/rikurinode/actions/runs/43509784804). The log shows the four new Rust tests `ok`.
- The image build, the USB installer drill and the rollback drill: **Pass**, [run 43509784874](https://github.com/rikuripi/rikurinode/actions/runs/43509784874).
- `Rust mutants (changed lines)`: **Pass**, [run 43509784821](https://github.com/rikuripi/rikurinode/actions/runs/43509784821), but with `No mutants to filter`: the diff touched no non-test Rust code. **It proves no kill.**

### The verifier's follow-up, at `18c21c6`: PASS

- No Important finding is open. The pass checked only repair 2's corrections and the drop of nit 5.
- **Important 1 to 4 (Rust): their kills are established by reading the code, not by a run.** Rust tests do not run on the Mac, and CI's mutants job had nothing to mutate.
  - Important 1 and 2: every mutant of `read += n` or `read > MAX_READ` either never cuts the flood off (a timeout, failing the test's kind and its 10 s bound) or underflows and panics. The `==` mutant's kill rests on how Linux splits Unix-socket reads, so it is reasoned, not observed.
  - Important 3: the arm deleted, the 24-byte message parses as `Ok`.
  - Important 4: the arm deleted, the error falls through and the call times out.
- **Important 5 (Python): Pass by trace,** with the evidence of this record's run on rikuri-drill (repair 2 above). rikuri-drill could not be reached for this pass, so the kill was not re-run.
- Nit 1's values, the README (nit 2), the reasons for each test change, and `names.rs` being identical to `main`: Pass.
- PR #91 was merged (`f014252`, 2026-11-13 21:40 UTC) while this pass was running; the pass reviewed code already on `main`. It found nothing to change.

## Close-out

- **Done when:**
  - Red then green: Pass. The red was seen in CI, the fix is in its own commit, and every later test change has a recorded reason.
  - `Full gate (Ubuntu)`: green on `568bd1c` and `18c21c6`.
  - The live drill: Pass, in runs 43488038824 and 43493692877.
    - polkit refused `nobody`;
    - `PUT /api/node/name` renamed the node: `/etc/hostname` and the kernel's name became the new name;
    - only the new name answered, with the same process and after a restart.
  - The verifier: Pass after a first-pass FAIL on test adequacy and the follow-up above.
  - **Not yet proven:**
    - mDNS answering the new name is inferred from the kernel's name, not observed (5c.4b-2);
    - the Rust kills of Important 1 to 4 are by reading only.
- **Used:** both repair cycles and both review rounds. Nit 5 was dropped on the owner's choice rather than repaired.
- **Merged:**
  - PR #90 at `568bd1c`, as `30ae17a`;
  - PR #91 at `18c21c6`, as `f014252`.

  This close-out comes after both.
- **Backlog, not started:**
  - `.github/workflows/mutants.yml` accepts cargo-mutants' exit 3 (timeouts), which can hide missed mutants: its own control task;
  - a warning, with a test that captures logs, when a reload loses the node's name.
- **Next (not started):** 5c.4b-2: the page, the suggested free rikuriNN name, the mDNS check of a name, and the runbook.
