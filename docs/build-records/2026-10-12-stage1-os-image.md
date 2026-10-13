# Build Record — stage 1, change 1: the OS image, built and checked in CI

| | |
|---|---|
| **Date** | 2026-10-12 |
| **Author / session** | Claude Code (Opus 5.5); owner Henry |
| **Branch** | stage1/os-image (on docs/plan-and-lessons, pull request #4, until it merges) |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS — built and tested locally where it can be (the checker, its tests, 14 of 14 mutants); the image build in CI Not yet proven |
| **Change type** | feature (the first node code: the operating system) |

## 0. Intent — the owner's words, approved before design
- [x] Problem: three days of process work and no node code (owner,
      2026-10-12: "This whole thing seems to be taking a long time, before we
      even start to do the actual coding"). Stage 1 of the plan (§8) is the
      operating system: Fedora IoT as a signed bootc image, built in CI, that
      rolls itself back when an update fails.
- [x] Outcome of this change: `image/Containerfile` builds the node's OS image
      in CI on every pull request that touches it; the build fails if bootc's
      lint fails or if the built root lacks what the node relies on.
- [x] Who/what it affects: CI only. No node exists; nothing runs on this
      machine (AGENTS.md > Testing on this machine).
- [x] Open questions: answered by the owner on 2026-10-12 (AskUserQuestion),
      each with the recommended option: D6 public image on GHCR, D7 CI key on
      `main` only with an offline spare, D8 private repository with the VM
      drill on image changes and weekly, D9 Fedora's DNS boot check off (plan
      §7, ADR 0004). Earlier the same day: "Yes, start Stage 1
      (Recommended)"; the N150 is "Not yet" ready.
- [x] Owner approved the intent: the answers above.

## 0b. Spec — requirements + design, policy applied up front
- [x] Requirements: lessons register PLAT-01 (the host is defined by the
      image; an image test asserts the shipped host configuration); UPG-09
      (the node runs exactly the verified artifact: the base pinned by
      digest); TEST-01 (no test reaches the live node: the image is built only
      in CI); TEST-02 (a check counts only once seen to fail); D9 (the DNS
      check off, provably).
- [x] Design: a Containerfile on `registry.fedoraproject.org/fedora-iot`
      pinned by digest (quay.io drops old digests within a day — research);
      Fedora 44 while the pipeline is built, 45 after its release and a soak
      (plan §2; 45 had 8 open blockers); `RUN bootc container lint` as the
      last build step; host files under `image/rootfs/`; a Python checker run
      on the built root, mounted read-only, with fixture tests in the full
      gate. Rejected: running the check inside the image (the IoT image may
      have no Python, not confirmed); deleting Fedora's DNS check script from
      the image (its package owns it; greenboot's own setting is the
      supported way, and the VM test will show it was skipped); building on
      Fedora 45 now (pre-release); generic `fedora-bootc` (no greenboot).
- [x] Policy applied: every behaviour-changing default went to the owner (D6
      to D9); no secret in a public image (the checker refuses private keys
      and SSH host keys in the writable trees; the gate's secret scan covers
      `image/rootfs/`); the base and every action pinned.
- [x] Flagged concerns, routed: greenboot's open rollback bug (issue 217) and
      the uncounted hang before userspace mean rollback is unproven until the
      drill (change 4, then the N150); KVM on private runners is not
      confirmed, so this change probes it.

## 1. Plan — detailed enough that a new session could build from it alone
- [x] One sentence: build the OS image in CI from a pinned Fedora IoT base
      with the owner's greenboot settings, and fail the build if the image
      lacks what the node relies on.
- [x] Blast radius: new `image/`, `.github/workflows/image.yml`, one line in
      `scripts/quality/full-gate.sh` (step 3 also runs the image check's
      tests); docs (plan §2 and §7, ADR 0004, README, AGENTS.md). No auth,
      funds or execution path; nothing irreversible (the GHCR package is not
      created or made public by this change).
- [x] Current behaviour: no image, no workflow; the gate's step 3 runs the
      quality tools' tests only (`git show 50883a2:scripts/quality/full-gate.sh`).
- [x] Stage 1 in changes (each its own pull request and record):
      1. this one — build and check;
      2. sign with cosign (old format) and publish to GHCR from `main`; the
         node's `policy.json` and both public keys in the image; CI verifies
         with skopeo under that policy; owner steps first (the Environment,
         its secrets, the offline spare);
      3. boot it in a VM in CI (bcvk or image-builder, if the probe finds
         KVM): greenboot passes and its journal shows the DNS check skipped;
      4. the rollback drill in CI: a deliberately broken image is staged and
         must roll back by itself with a `/var` marker intact (on image
         changes and weekly, D8);
      5. install media for the N150; first boot without a command line;
      6. the N150 drill (§4.1), which closes stage 1.
- [x] Risks: the build fails on Ubuntu's Podman 4.9.3 (then: newer Podman,
      as bootc's CI does); `podman image mount` behaves differently there;
      the IoT image's os-release differs from the fixture (the check would
      say so). Riskiest: none touches a node.
- [x] Verification defined up front: the checker's tests pass and each of
      its checks is seen to fail (mutants); the gate passes; in CI the image
      builds, `bootc container lint` passes, and the checker reports 0
      findings on the real root; the probe's answer about KVM is recorded.

## 2. Build
- [x] New code meets the bar: the checker reads paths only inside the root
      and never follows a link (an absolute link would read the CI machine);
      the greenboot file is closed-world (only the two keys, once each, no
      `[section]`), because greenboot falls back to its defaults silently.
- [x] Clean as you go: nothing replaced.
- [x] Security question: the image will be public (D6) — the checker refuses
      private keys and SSH host keys under `etc`, `root`, `var`, `usr/local`,
      `opt`. Not scanned: Fedora's own files under `/usr` (they ship test
      keys) and files over 1 MiB; the project's own additions are covered by
      the gate's secret scan. No signing or publishing yet: no credential in
      the workflow, `permissions: contents: read`.

## 3. Debug
- [ ] N/A — no defect fixed.

## 4. Verify
- [x] Unit tests: 28 in `image/tests/test_check_image_root.py`, all pass;
      the committed `greenboot.conf` is checked as shipped.
- [x] Mutants (`mutate_check.py`): 14 of 14 caught (`mutants.out`). The
      first run had one mutant whose pattern matched twice and did not run;
      it was made specific and rerun.
- [x] The pre-commit secret scan refused the first commit: two fake private
      keys in the test fixtures. As the hook says, not allowlisted: the
      fixtures now assemble their PEM text at run time (`pem()`), and the
      tests and mutants were rerun (28 OK; 14 of 14).
- [ ] Watched it work in the running system: the CI build — Not yet proven.
- [ ] Recovery path: N/A until change 4 (the rollback drill).
- [x] Regression guard proven to fail: the mutants above.
- [ ] Independent verification: pending.
- [ ] Diff matches the §1 plan: at close-out.

## 5. Close Out
- [x] Full gate green (locally, 2026-10-12): all 7 steps; step 3 ran the
      image check's 28 tests (`gate.out`). The hygiene step refuses an
      unpinned base in `image/Containerfile`: a scratch copy with
      `FROM registry.fedoraproject.org/fedora-iot:44` gave "base image not
      pinned ('44' is a floating tag, not a version)".
- [ ] Scrap Sweep:
- [ ] Reviewed per `REVIEW.md`:
- [ ] Lesson loop:
- [x] Knowledge layer: README and AGENTS.md status; plan §2 and §7; ADR
      0004. No help page or runbook exists yet.
- [ ] Commit message explains why; record committed with the change.

## Skipped items — visible, never silent
- The image's own boot (greenboot passes, the DNS check skipped in its
  journal): change 3. Until then D9 is held by the checker on the file, not
  by greenboot itself.
- `image.yml` is not a required check (path-filtered, so it does not run on
  every pull request); making it one is the owner's choice once it is stable.
  Owner: Henry. Reactivate: after change 4.
- aarch64: waits for D1.

## Evidence log
```
2026-10-12  research: evidence/2026-10-12-stage1-os-image/research.md
            base digest checked: fedora-iot:44-x86_64 = sha256:29d16f4c…be1c3
            unit tests: Ran 28 tests, OK (safe-run.sh)
            mutants: 14 of 14 caught (mutants.out)
            full gate: all 7 steps passed (gate.out)
```
