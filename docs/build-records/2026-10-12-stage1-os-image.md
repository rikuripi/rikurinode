# Build Record — stage 1, change 1: the OS image, built and checked in CI

| | |
|---|---|
| **Date** | 2026-10-12 |
| **Author / session** | Claude Code (Opus 5.5); owner Henry |
| **Branch** | stage1/os-image (on docs/plan-and-lessons, pull request #4, until it merges) |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS — the image builds and passes its checks in CI (run 38328363342), and a planted finding fails the job (red drill, run 38328553937); `/dev/kvm` present on the runner (no VM started yet); **verifier round 1 FAIL (code/test and wording): fix round handed to a session opened in this worktree (owner, 2026-10-12)** |
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

## 3. Debug — the fix round (verifier round 1's findings 1 to 4)
- [x] Reproduced before fixing (2026-10-12, the fix-round session, inside
      `safe-run.sh`): the verifier's 15 `greenboot.conf` cases run through
      its rust-ini 0.21.3 probe and through the checker. The checker passed
      cases 03 to 11, 14 and 15 with 0 findings; greenboot reads 03, 04, 06,
      07, 08, 09, 14 and 15 as `disabled=[]` (the DNS check on) and 05 as
      intended only because the indented comment became a key named
      `# owner`. Its link probe: with `usr` a link out of the root,
      `usr/local/host-only.key` was read and reported.
- [x] Failing tests written and SEEN failing (`red-tests.out`): 51 tests,
      40 failures and 7 errors on the unfixed checker; one test per probe
      case (the table in `test_check_image_root.py` carries what greenboot
      reads from each) and per missed mutant P2 to P9; then the fix-lock.
- [ ] Root cause is a CLASS, named here:
- [ ] Swept for siblings of the class (where else it lived):

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
- [x] Watched it work in CI (run 38328363342 on c60c324, 2026-10-13
      00:40Z, 1 min 1 s; `ci-image-run1.out`): the base pulled by digest;
      `bootc container lint` "Checks passed: 14, Checks skipped: 1"; the
      checker on the real root: "0 finding(s)"; the image 1,458,116,810
      bytes, base version 44.20261012.0. The other checks on #5 passed too
      (Full gate, guard tests on Python 3.12 and 3.9).
- [x] **The probe:** `/dev/kvm` is present on the private repository's
      runner (2 CPUs, 7,938 MiB, 13 GB free on `/` and on `/mnt`, Podman
      4.9.3) — the research could not confirm it. The VM boot test and the
      rollback drill (changes 3 and 4) can run on GitHub's runners.
- [x] **Red drill** (draft #6, closed; run 38328553937;
      `ci-image-red-drill.out`): `FEDORA_RELEASE` set to 45 on the 44 base.
      The job failed at "Check the built root" with "FAIL usr/lib/os-release:
      VERSION_ID is '44', expected '45'" and exit code 1: a finding blocks
      the job, not only the checker's tests.
- [ ] Recovery path: N/A until change 4 (the rollback drill).
- [x] Regression guard proven to fail: the mutants above.
- [x] **Verifier, round 1: FAIL** (2026-10-12; its evidence outside the
      repository, in `/home/junc/claude-wip/stage1/verify/`). Passed: the
      gate (step 3 runs the image tests, locally and in CI); `image.yml`
      (pinned, read-only, no secret, the red drill's failure in the real
      log); the base digest (both registries, and the config blob's version
      44.20261012.0 in the CI pull); the evidence files verbatim in the run
      logs; no test loosened c60c324..HEAD. Failed:
      1. **Code — the checker reads `greenboot.conf` differently from
         greenboot.** Built from rust-ini 0.21.3's parser, config 0.15.13
         and greenboot-rs 0.16.4's own code (`verify/ini-probe/`, 15 cases
         in `cases/`): a comment indented by a space or a tab, a vertical
         tab or NEL after a comment, a form feed after a value or before a
         `#`, a trailing `\x1f` — the checker passes with 0 findings while
         greenboot reads `DISABLED_HEALTHCHECKS` as empty (the DNS check
         stays on, against D9). Python's `splitlines()`/`strip()` and its
         indented-comment rule are wider than rust-ini's. The shipped file
         reads the same in both.
      2. **Code — "never follows a link" is false:** with `usr` a link out
         of the root, the key scan walks `usr/local` through it
         (`verify/linkprobe/usr_link.py`).
      3. **Test — 7 proposed mutants missed** (P2 walk a linked top folder,
         P3 read a linked file, P4 drop `var`, P5 drop `usr/local` and
         `opt`, P6 `SECRET_MAX_BYTES = 1 << 10`, P7 a missing
         `DISABLED_HEALTHCHECKS` unreported, P9 an unreadable file
         unreported); three of the 14 committed mutants do not change the
         verdict ("[section] allowed", "duplicate key allowed" — message
         only; "not KEY=VALUE allowed" crashes instead of failing).
      4. **Not yet proven / vacuous:** the scan reports no count, and in the
         ostree layout `root`, `opt`, `usr/local` may be links skipped
         silently; `GREENBOOT_MAX_BOOT_ATTEMPTS=3` is greenboot's default.
         Unstated scan gaps: PGP `PRIVATE KEY BLOCK`, Tor
         `hs_ed25519_secret_key`, WireGuard, age keys; `tmp`, `boot`.
      5. **Wording:** "the runner can run VMs" (only `/dev/kvm` seen); quay.io
         "within a day" (the cited case: a 2026-09-22 digest gone by 09-28;
         the verifier saw it 404 on quay.io, 200 on registry.fedoraproject.org);
         ADR 0004 "works over Tor" (not tried); research.md "a kernel panic
         … never counted" (contested: greenboot 0.16.4's
         `detect_grub_fallback` says it handles a panic); "refuses private
         keys" (only PEM forms); the plan's "(ADRs 0001 to 0004)" covers D8
         and D9, which have none; "one line" in `full-gate.sh` is two; and
         REVIEW.md's written risk note for protected-path edits
         (`AGENTS.md`, `.github/workflows/image.yml`,
         `scripts/quality/full-gate.sh`) is missing.
- [x] **Where the fix round runs** (owner, 2026-10-12, AskUserQuestion:
      "Hand off to a node-repo session (Recommended)"). This change was
      built from a session opened in Rikuri-PI, so the node repository's
      guard, fix-lock and OS sandbox did not apply to it (Rikuri-PI's guard
      did); no container, node-tool or previous-checkout command was run,
      and local tests ran only inside `safe-run.sh`. The fix round runs in a
      session opened in this worktree, where they apply.
- [ ] **Fix round (round 2), the plan for the next session** — the owner's
      stop rule: code/test findings are fixed with a test and checked again.
      Order: write the failing tests and commit them (red commit, the run
      recorded); `python3 .claude/hooks/guard.py fix-lock on
      docs/build-records/2026-10-12-stage1-os-image.md`; fix in its own
      commit; release the lock (the owner approves); verifier round 2.
      - F1 parser: read bytes; allow only printable ASCII and `\n`; split on
        `\n` only; blank lines exactly empty; a comment is `#` in column 0;
        key lines exactly `GREENBOOT_MAX_BOOT_ATTEMPTS=[0-9]+` and
        `DISABLED_HEALTHCHECKS=("name" "name" …)` or `=()`, names
        `[A-Za-z0-9_.-]+`, one space between them, no other whitespace;
        anything else is a finding. A test per verifier case (`verify/
        ini-probe/cases/`): every case greenboot would read differently
        must be a finding. Rename `test_shipped_conf_as_greenboot_reads_it`
        (it tests the checker's parser, not greenboot's); greenboot's own
        reading is proven in change 3 (its journal: "Skipping disabled
        script: 01_repository_dns_check.sh").
      - F2 links: a `_dir(root, rel)` helper (no link in any component) for
        each scanned top; a test with `usr` linked out of the root, holding
        a key: no finding from it, nothing read there.
      - F3 not vacuous: print the files scanned per tree, and which tops
        were skipped as links or absent; a finding if `etc` yields no
        regular file.
      - F4 scope: PGP `PRIVATE KEY BLOCK`; `AGE-SECRET-KEY-1`; Tor's
        `hs_ed25519_secret_key` (by name, and its `== ed25519v1-secret`
        header); WireGuard `PrivateKey` under `etc/wireguard`; add `tmp`
        and `boot`. Say exactly which forms are refused.
      - F5 tests and mutants: tests that catch P2 to P9; drop the two
        message-only mutants from the set or say why they stay; make "not
        KEY=VALUE" fail rather than crash; all mutants caught.
      - F6 wording: each item of finding 5, and REVIEW.md's risk note for
        the three protected paths in this record.
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
2026-10-13  CI run 38328363342: lint 14 passed / 1 skipped; check 0 findings; KVM present
            (ci-image-run1.out); red drill run 38328553937: job failed on the planted
            finding (ci-image-red-drill.out)
```
