# Build Record — Experiment: health without a shell (ADR 0013, criterion 3)

| | |
|---|---|
| **Date** | 2026-10-23 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `exp/shellless-health-probe`, from `main` at `6db7a53`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `e19bde4`; `main` merged in `324c2c2`; this close-out |
| **Status** | COMPLETE but for the merge: criterion 3 kept; verifier PASS on the follow-up pass; pull request #32 green after `main` (with #33's advisory fix) was merged into the branch: `Full gate (Ubuntu)` [run 40052461157](https://github.com/rikuripi/rikurinode/actions/runs/40052461157) (the first run, 40043855134, failed on RUSTSEC-2026-0385 and -0386, unrelated to this change) |
| **Change type** | ops (an experiment; evidence and documentation only) |

## Task Contract

1. **Outcome:** before stage 2 depends on it, the owner knows whether a container with no shell can still be health-checked and ordered by `Notify=healthy` (ADR 0005) on our Fedora IoT image, the criterion that can sink ADR 0013 on its own.
2. **Scope:** ADR 0013's criterion 3 only, run early, as one experiment answering one question: *on our image, does a Quadlet unit with `Notify=healthy` and an exec-form `HealthCmd=` become ready only when the probe in a from-nothing image passes, and never when it fails?* Files: this record and its evidence folder `docs/build-records/evidence/2026-10-23-shellless-health-probe/` (the stand-in's source, the Containerfile, the unit files, the outputs). Risk tier: **routine** (an experiment in a disposable VM; no code enters the product). **Not included:** Nix (the owner's choice: `FROM scratch` now, Nix after criterion 8's adoption inspection); the other seven criteria; Bitcoin Core; any change to `image/`, `control-plane/`, CI, the gate or the plan (a result that changes ADR 0013 or D20 is reported for the owner's decision).
3. **Done when:** in `rikuri-drill`, on `localhost/rikuri-os:fix4`, with the evidence kept:
   - the image holds the stand-in binary and nothing else, and `/bin/sh` cannot run in it;
   - **case A (healthy):** `systemctl start` returns only after the probe passes (the stand-in delays its readiness), the container's health check is recorded as exec form (`CMD`, not `CMD-SHELL`), and a unit ordered after it starts only then;
   - **case B (probe fails):** the unit never becomes ready, fails at its start timeout, and the unit ordered after it does not start;
   - **case C (shell form):** the same unit with a plain-string `HealthCmd=` never becomes ready, because Podman runs it through `/bin/sh -c`;
   - the stage 2 hardening flags of criterion 2 (`ReadOnly`, all capabilities dropped, `NoNewPrivileges`, `UserNS=auto`) are set as far as they run, and any that does not is recorded;
   - the conclusion is one of keep, simplify or drop for criterion 3, with one `verifier` pass on the record's claims against the evidence (no Important finding).
4. **Authority:** the owner's "Ok, let's test criterion 3 first." and choices of 2026-10-23 ("FROM scratch now (Recommended)", "rikuri-drill VM (Recommended)", "3 hours (Recommended)"); SSH into `rikuri-drill` as before (the owner's decisions of 2026-10-21; host key checked against the fingerprint the owner saw on its console); the VM stays on its host-only network (no outside network); on the Mac, add the Rust target `aarch64-unknown-linux-musl` to the pinned toolchain (rustup verifies it against the signed channel manifest) and build the stand-in with the toolchain's own `rust-lld`; commit, push and open a pull request; no merge. Independent check required (one pass).
5. **Limits:** one task; two repair cycles; two review rounds; **time budget 3 hours** (the owner's), started 2026-10-23; stop and report if exceeded.

## 0. Intent

- [x] **Problem, in the owner's words:** "After testing rollback on Fedora IoT, are we able to test the no shell, no tool feature using Nix in Fedora IoT." (2026-10-23); "Ok, let's test criterion 3 first."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** no node; the stage 2 design (ADR 0005, ADR 0013).
- [x] **Open questions:** whether Quadlet passes a JSON-array `HealthCmd=` to Podman intact (its page says only "Equivalent to the Podman `--health-cmd` option"); whether `UserNS=auto` works for rootful Podman on this image without a `containers` entry in `/etc/subuid`.
- [x] **Owner approved the intent:** the messages above.

## 0b. Spec

- [x] **Facts relied on (read 2026-10-23):** `podman-run(1)`, `--health-cmd`: a JSON array is the exec form; a plain string "is interpreted as an argument to /bin/sh -c". `--sdnotify=healthy` "sends READY when the container has turned healthy; requires a healthcheck to be set". `podman-systemd.unit(5)`: `Notify=healthy` "will postpone startup notifications until such time as the container is marked healthy".
- [x] **Design:**
  - One static binary, `standin` (Rust, standard library only, `aarch64-unknown-linux-musl`), with two modes: `serve` (after a set delay, answers on `127.0.0.1:8080` with `ok` or, when `STANDIN_STATE=sick`, `sick`) and `probe` (connects, reads, exits 0 only on `ok`; 2 s limits on the connect and on each read).
  - The image: `FROM scratch`, the one binary, `ENTRYPOINT ["/standin", "serve"]`, built in the VM with `podman build` (no network needed).
  - The units: `standin.container` (Quadlet, `Network=none`, which still gives the container its own loopback) and `after-standin.service` (`Requires=` and `After=` it; its start time is the journal's).
- [x] **Rejected:** Nix for this run (owner's choice); the CI drill (a control change to CI, its own task); a probe from outside the container (rejected by ADR 0013, it would break `Notify=healthy` ordering).
- [x] **Policy applied:** untrusted content: no third-party code is run (the Rust target is the pinned toolchain's own); the VM holds no secret and has no outside network; the experiment's code is evidence and never becomes production code by itself (AGENTS.md §6).

## 1. Plan

- [x] **One sentence:** build a from-nothing image with a stand-in service and its probe, run it under Quadlet with `Notify=healthy` in `rikuri-drill`, and observe cases A, B and C.
- [x] **Blast radius:** the experiment VM only; one Rust target added on the Mac.
- [x] **Files and order:** this record; the stand-in and its build; the image and its contents; the units; cases A, B, C; the verifier; the pull request.
- [x] **Risks:** a false pass, if readiness came from something other than the probe (hence case A's delay, case B's failure and case C's shell form: a pass needs all three to differ as predicted).
- [x] **Verification defined up front:** the Task Contract's "Done when".

## Evidence log

Run 2026-10-23 in `rikuri-drill` (aarch64, Parallels, host-only network, no outside network), booted on `localhost/rikuri-os:fix4` (this project's image, built from `19bca35` per `2026-10-22-greenboot-218.md`; digest `sha256:9fceb6b2…c258b`, version 44.20261021.0): Podman 5.8.9, crun 1.28, conmon 2.2.1, systemd 259.10, kernel 7.2.11 (`00-vm-state.out`, captured after the run in the same boot: boot ID `37d50312…`, the only boot since 2026-10-22 17:59, uptime 96,584 s, past the run's last event at 96,202 s). The VM's host key checked against the fingerprint the owner saw on its console (`SHA256:NtVMqX12…5938`), pinned in a session-only `known_hosts`. The VM's clock is 13 hours off (as in the 2026-10-21 record); the monotonic times below are unaffected.

- **Build.** `standin.rs` built on the Mac by the pinned toolchain (rustc 1.98.1) for `aarch64-unknown-linux-musl` with `rust-lld`, `+crt-static`, `-D warnings`: a static, stripped ELF of 451,328 bytes, SHA-256 `2a4913a5…a91b1` (`00-build-mac.out`); the same hash in the VM (`01-unit-tests.out`). Its two unit tests ran **in the VM** (`01-unit-tests.out`: "2 passed"; the capture kept the last lines only, so one test's name shows), not on the Mac: `safe-run.sh` refuses without Linux namespaces, and its override is for CI only.
- **Contents** (`02-image-contents.out`): `podman build --network=none` from `FROM scratch`; the image is one layer of 455,089 bytes; `podman export` lists one file, `standin`; `--entrypoint /bin/sh` and `/bin/ls` both refused by crun ("executable file `/bin/sh` not found", exit 127). **Pass.**
- **What Quadlet hands Podman** (`03-quadlet-generated.out`, the generator's `--dryrun`): `HealthCmd=["/standin", "probe"]` becomes `--health-cmd "[\"/standin\",\x20\"probe\"]"`, which systemd unescapes to the JSON array; `Notify=healthy` becomes `--sdnotify=healthy` with `Type=notify` and `NotifyAccess=all`. This answers the open question: Quadlet passes the exec form through intact.
- **Finding 1, `UserNS=auto`** (`04a-case-a-userns-auto-refused.out`): on our image the unit failed at once: "Cannot find mappings for user \"containers\": no subuid ranges found for user \"containers\" in /etc/subuid", then "not enough unused IDs in user namespace"; the dependant was correctly not started. The image has no `containers` range in `/etc/subuid` or `/etc/subgid`. For the cases below, Podman's documented range (`containers:2147483647:2147483648`) was added to **this VM's** `/etc` only, and removed afterwards. Not a criterion 3 result: it belongs to criterion 2 and stage 2 (the image must ship that range before any unit uses `UserNS=auto`).
- **Case A, healthy** (`04b-case-a.out`): `systemctl start after-standin.service` returned 0 after 7,207 ms. Monotonic times: the container started at 95944.44 s ("ready in 5 s"); it listened at 95949.44 s; health turned `healthy` at 95951.14 s (`05b-case-b-health-events.out`); systemd marked `standin.service` started at 95951.26 s; the dependant started at 95951.27 s. Podman recorded the check as `["CMD","/standin","probe"]` (exec form; not `CMD-SHELL`); the container ran as `10001:10001`, user namespace reported as `private` (Podman's report for `auto`; an inference, not shown separately), read-only root, no effective capabilities; `podman healthcheck run` returned 0; `podman exec standin /bin/sh` refused (exit 127). **Pass.**
- **Case B, probe fails** (`05-case-b.out`, `05b-case-b-health-events.out`): with `STANDIN_STATE=sick` (a drop-in, `case-b/50-sick.conf`) the stand-in listened and answered `sick`; health stayed `starting` through the 30 s start period, then counted failures and was `unhealthy` from the third on; it was never `healthy`; the unit failed with `Result=timeout` at its 45 s start limit (the `ActiveEnterTimestampMonotonic` in `05-case-b.out` is case A's, left from the earlier start, not a case B activation); the dependant was not started ("Dependency failed for after-standin.service"). **Pass.**
- **Case C, shell form** (`06-case-c.out`, `06b-service-lines-all-cases.out`): with `HealthCmd=/standin probe` (a plain string, `case-c/50-shell-form.conf`), Quadlet passed `--health-cmd "/standin\x20probe"`; Podman recorded `["CMD-SHELL","/standin probe"]`; the stand-in was healthy in itself (answering `ok` from 96107.01 s), yet the probe run by hand exited 1 with status `starting`, and the unit never became ready (no health-event capture was kept for this case), the unit timed out and the dependant was not started. **Pass**: readiness came from the exec-form probe and nothing else.
- **Finding 2, stopping after a start timeout** (`05-case-b.out`, `06-case-c.out`): each took about 55 s in two phases. First 45 s: systemd's SIGTERM to the unit's main process (most likely the `podman run` still waiting for `healthy`; its log line has `m=+100.3`) went unanswered until "State 'stop-sigterm' timed out. Aborting." Then about 10 s, Podman's default stop timeout, before "container stop": consistent with the stand-in, PID 1 in its namespace with no SIGTERM handler, ignoring SIGTERM until killed. The cause of each phase is not isolated by this run. Not a criterion 3 result; for stage 2: each shell-less image's program must handle SIGTERM itself (Bitcoin Core and LND do) or the unit runs Podman's init (`RunInit=`), and the kill-and-restart drill times both phases.
- **Cleanup** (`07-cleanup.out`, unlabelled counts: `containers` lines in `/etc/subuid` and `/etc/subgid` 0, `standin` images 0, `standin` units 0): the units, the drop-ins, the image, the experiment folder and the `subuid`/`subgid` line removed from the VM; `rikuri-drill` kept for later experiments (the owner's choice of 2026-10-21).

**Deviations:** the run tagged the image `localhost/standin:exp`; the committed `standin.container` names `localhost/standin:0.1-exp`, because the hygiene check refuses a tag without a version; the image itself is identified by its ID `0be50788…` in `02-image-contents.out`, and the run's own unit text is in `03-quadlet-generated.out`. Trailing blanks of the command output were stripped from two evidence files.

**Verification:** `git diff --cached --check` and `repo_hygiene.py` pass; the `verifier`'s first pass FAIL (Important: the booted image and versions had no output), follow-up pass **PASS** with three nits: two corrected here; the third, `07-cleanup.out`'s last two counts being unlabelled in the file itself, left as is (the record labels them).

**Time used:** about 30 minutes of the 3-hour budget. Repair cycle 1 of two: the verifier's first pass failed on one Important finding, the booted image and versions claimed without an output (now `00-vm-state.out`, `00-build-mac.out`); its nits corrected above (finding 2's two phases, case C's probe count, the probe's limits, case B's stale timestamp, the dependant, the unit tests' capture, the cleanup counts).

## Conclusion

**Criterion 3: keep.** On our Fedora IoT image, Quadlet's `HealthCmd=` accepts the exec form (a JSON array), Podman runs it without a shell, and `Notify=healthy` holds a unit, and every unit ordered after it, until that probe passes, and never when it fails. The probe can be one static binary in a from-nothing image. The one rule: `HealthCmd=` must always be written as a JSON array; a plain string silently needs `/bin/sh` and can never pass in such an image (case C). That rule can be checked by reading the unit files; no check does so yet (for the backlog, beside the contents check for service images that ADR 0013 lists).

This settles criterion 3 for the `FROM scratch` image only; Nix's image (criterion 1, 8) is untested, and the other criteria are unchanged. The two findings go to stage 2, not to ADR 0013's decision: a `containers` range in `/etc/subuid` and `/etc/subgid` for `UserNS=auto`, and a stop after a failed start that takes 55 s in two phases, which stage 2's kill-and-restart drill must time (each image's program handling SIGTERM, or `RunInit=`, may shorten only the second).
