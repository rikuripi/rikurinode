# Build Record — stage 1, change 1: the OS image, built and checked in CI

| | |
|---|---|
| **Date** | 2026-10-12 |
| **Author / session** | Claude Code (Opus 5.5); owner Henry |
| **Branch** | stage1/os-image, pull request #5, merged into main on 2026-10-13 before its fix round; the fix round was the follow-up pull request #15 from stage1/checker-fixes, merged 2026-10-19; this close-out of the record is on `stage1/record-close-out`, its own pull request (Claude Code, Fable 5.1, in the owner's desktop session) |
| **Commits** | PR #5, merged as 678b1b8. The fix round, on `stage1/checker-fixes`: a93133b (the failing tests, red), 2276986 (F6 wording), 2d7659e (the checker moved out of `image/tests/`), cd77e9e (the fix, under the lock), fc06a36 (the three tests after the release), 6b51deb (the close-out of the fix round: this record, `gate2-steps.out` regenerated, the docstring), 9cc098b (main merged into the branch on 2026-10-19: 25 commits behind, one conflict in the plan's status line, resolved by keeping main's line plus the clause that D8 and D9 are recorded in §7 only); PR #15 merged as ab99913 |
| **Status** | COMPLETE — change 1 of stage 1 is done. PR #5 (the image, built and checked in CI; run 38328363342, the red drill run 38328553937, `/dev/kvm` present on the runner) merged as 678b1b8 on 2026-10-13 before its fix round; the fix round, F1 to F6 (verifier round 2: pass, every claim reproduced), merged as ab99913 on 2026-10-19 through PR #15, whose CI was the proof the verdict waited for: CI run #40 `Full gate (Ubuntu)` and OS image run #8 both completed successfully on 9cc098b. Stage 1 is not closed: changes 2 to 6 and the §4.1 drill on the N150 remain |
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
      pinned by digest (quay.io drops old digests within days: a 2026-09-22
      digest was gone by 09-28, 404 on quay.io and 200 on
      registry.fedoraproject.org when verifier round 1 looked);
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
      to D9); no secret in a public image (the checker refuses the key forms
      listed in §2, in the writable and local trees; the gate's secret scan
      covers `image/rootfs/`); the base and every action pinned.
- [x] Flagged concerns, routed: greenboot's open rollback bug (issue 217) and
      the uncounted hang before userspace mean rollback is unproven until the
      drill (change 4, then the N150); KVM on private runners is not
      confirmed, so this change probes it.

## 1. Plan — detailed enough that a new session could build from it alone
- [x] One sentence: build the OS image in CI from a pinned Fedora IoT base
      with the owner's greenboot settings, and fail the build if the image
      lacks what the node relies on.
- [x] Blast radius: new `image/`, `.github/workflows/image.yml`, two lines in
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
      **2026-10-22:** changes 3 and 4 built together, before change 2, by
      the owner's choice: the `drill` job of `image.yml`
      (`docs/build-records/2026-10-22-ci-vm-drill.md`), on pull request #29;
      on the way it found and fixed greenboot-rs #218 and #219 in the image
      (`docs/build-records/2026-10-22-greenboot-218.md`,
      `docs/build-records/2026-10-22-d22-unapplied-update.md`).
      **2026-10-29:** change 2 built in three steps (owner, 2026-10-25):
      2a the node's signature policy, proven in CI
      (`docs/build-records/2026-10-25-signature-policy.md`); 2b publishing,
      signed with the real key
      (`docs/build-records/2026-10-28-publish-signed-image.md`); 2c the
      node's own `bootc switch` refusing an unsigned update in the VM drill
      (`docs/build-records/2026-10-29-node-refuses-unsigned.md`).
      **2026-10-29:** change 5 in three steps (owner, 2026-10-29): 5a the
      USB installer, built and installed in CI
      (`docs/build-records/2026-10-29-install-media.md`); 5b the install on
      the N150, by the owner (`docs/runbooks/install-node.md`); 5c the
      first-boot setup page.
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
- [x] Security question: the image will be public (D6) — the checker refuses,
      under `etc`, `root`, `var`, `usr/local`, `opt`, `tmp` and `boot`,
      exactly these forms (fix round, F4; before it, only the first two): a
      PEM private key (`-----BEGIN … PRIVATE KEY-----`, PGP's `PRIVATE KEY
      BLOCK` included); an SSH host key under `etc/ssh`, by name; a Tor
      onion service key by name (`hs_ed25519_secret_key`) or any file with
      Tor's `== ed25519v1-secret` header; an age secret key
      (`AGE-SECRET-KEY-1…`); a `PrivateKey =` line in a file under
      `etc/wireguard`. Not read: links (never), files over 1 MiB (counted
      and printed per tree); not scanned: Fedora's own files under `/usr`
      (they ship test keys); the project's own additions are covered by the
      gate's secret scan. No signing or publishing yet: no credential in
      the workflow, `permissions: contents: read`.
- [x] Protected paths changed, the written risk note REVIEW.md asks for
      (added in the fix round; verifier round 1 found it missing):
      `AGENTS.md` (the status line only; it changes no rule or gate);
      `.github/workflows/image.yml` (a new workflow: it runs `sudo podman`
      on GitHub's runner with `permissions: contents: read`, no secret and
      no publish step, and it is not a required check, so a failure there
      cannot block a merge until the owner makes it one);
      `scripts/quality/full-gate.sh` (step 3 gains the image check's tests;
      no step was removed or loosened, so the gate can only fail more).

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
- [x] **The checker moved to `image/check_image_root.py` before the lock**
      (owner, 2026-10-12, AskUserQuestion: "Move the checker out of
      image/tests (Recommended)"). The guard's test globs (`*/tests/*`)
      make every file under `image/tests/` read-only under the fix-lock: a
      simulated Edit of the checker there was denied, the same edit at
      `image/check_image_root.py` allowed. The checker is production code
      (CI runs it on the real root), so it leaves the tests' folder; its
      tests stay in `image/tests/`. Rejected: skipping the lock (the
      tripwire off for the very fix it exists for); an exception in the
      guard policy (the most work, on the shared policy). Protected path
      changed for it, the risk note: `.github/workflows/image.yml` gains
      only the checker's new path on its "Check the built root" step.
- [x] Root cause is a CLASS: **a checker looser than the reader it stands
      in for.** The checker read `greenboot.conf` with Python's
      `splitlines()` and `strip()`, wider than rust-ini's line and comment
      rules, so a file could pass here and read as "nothing disabled"
      there. The fix reads bytes and accepts one form only, the one both
      read alike, refusing everything else (F1). Second class: **a path
      check that looks at the last component only** (`usr/local` reached
      through a linked `usr`): one helper now lstat's every component, for
      files and folders alike (F2). Third: **a scan that cannot be told
      from an empty one** (F3): it prints what it read per tree and why a
      tree was skipped, and fails on an `etc` with nothing read.
- [x] Swept for siblings: every path the checker reads goes through
      `_lstat_in`; `check_os_release` keeps its lenient reading on purpose
      (Fedora's file, three fields compared by value, not a file another
      program reads differently); the forms the scan refuses are listed in
      its docstring and in ADR 0004 (F4). No other code reads a file for
      another program yet (stage 1 has no node software).

## 4. Verify
- [x] Unit tests: 28 in `image/tests/test_check_image_root.py` at PR #5;
      51 after the fix (`fix-tests.out`: "Ran 51 tests … OK"), 54 with the
      three added after the lock's release (`fix-tests2.out`: "Ran 54
      tests … OK"), one per verifier probe case and per proposed mutant;
      the committed `greenboot.conf` is checked as shipped. **Two of the 28
      were lost in the red commit's rewrite** (`test_conf_missing`,
      `test_greenboot_not_installed`; found by the mutant run below, not
      by the builder) and went back in after the release, with
      `test_a_folder_where_a_file_is_expected` for P1.
- [x] Mutants (`mutate_check.py`): 14 of 14 caught (`mutants.out`). The
      first run had one mutant whose pattern matched twice and did not run;
      it was made specific and rerun.
- [x] Mutants after the fix (`mutants2.out`): 33 in the set (the round's
      P1 to P9 and one per form the fix added; "[section] allowed" dropped
      as message-only; "not KEY=VALUE" now skipped silently rather than
      crashing, P8's form), 31 of 33 caught under the lock. Missed: P1
      (`_regular` accepting any file type: no test put a folder where a
      file is expected, and the use that caught it at PR #5 is now `_dir`)
      and "greenboot binary not required" (its test was lost, above). The
      owner released the lock (2026-10-13 00:16, AskUserQuestion; logged in
      `.claude/state/fix-lock.log`), the three tests went in, and the rerun
      reads **33 of 33 caught** (`mutants3.out`).
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
      4.9.3) — the research could not confirm it. Only the device was seen:
      whether a VM boots there is not yet proven (change 3 shows it, and
      change 4 needs it).
- [x] **Red drill** (draft #6, closed; run 38328553937;
      `ci-image-red-drill.out`): `FEDORA_RELEASE` set to 45 on the 44 base.
      The job failed at "Check the built root" with "FAIL usr/lib/os-release:
      VERSION_ID is '44', expected '45'" and exit code 1: a finding blocks
      the job, not only the checker's tests.
- [ ] Recovery path: N/A until change 4 (the rollback drill).
- [x] Regression guard proven to fail: the mutants above, and the fix
      round's red run (`red-tests.out`: 40 failures and 7 errors on the
      unfixed checker).
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
- [x] **Fix round (round 2), the plan** (done as written and in this order,
      §3; the one addition, the checker's move, is the owner's) — the owner's
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
- [x] **Verifier, round 2: F1 to F6 pass; verdict NOT YET PROVEN** until CI
      is seen (2026-10-13; its own evidence in its session's temporary
      folder, listed in its report, which goes into the pull request; round
      1's probes reused unchanged). Reproduced, line for line: the §3 table
      (the 678b1b8 checker on the 15 cases); the red run from a93133b's
      tree (51 tests, 40 failures, 7 errors); 51 OK at cd77e9e; 31 of 33
      there with exactly P1 and "greenboot binary not required" missed; 33
      of 33 at HEAD; the test files of a93133b and cd77e9e differ only by
      the import path, and fc06a36 only adds. Its rust-ini probe beside the
      new checker on the 15 cases and 19 of its own: the checker passes
      only the shipped file and five comment variants, each of which
      greenboot reads as intended, and every case greenboot reads as
      `disabled=[]` or a parse error is a finding (05, which greenboot
      reads right by luck, is refused too). The link probe: `usr/local`
      skipped as a link, nothing read through it; links inside `etc` to a
      key outside, a folder outside and the machine's `/etc` not read.
      Four mutants of its own (a tab allowed, several spaces between names,
      `.pub` as a host key, the last-component-only link check of round 1)
      all caught. Boundaries: a file of exactly 1,048,576 bytes read and
      its key found, one byte more skipped and said; a FIFO where a file is
      expected reported, no hang; `--fedora 45` on a 44 root; the ostree
      layout on a fixture (`root`, `usr/local`, `opt` skipped as links, the
      key under `var/roothome` found). Diff versus plan: all 18 changed
      files inside §1's blast radius; the fix-lock window consistent with
      the commits. Findings: (1) **Fail, evidence provenance:**
      `gate2-steps.out`'s step 3 had run outside `safe-run.sh` (no
      `safe-run:` line, and no `skipped=1`: that skip is for the mapped
      root the layer gives). The file is regenerated with every step inside
      the layer (§5); the outcomes are unchanged. (2) Not yet proven: CI's
      Full gate and the image workflow on the pull request — the stricter
      checker has not yet reported on the real root, nor its ostree notes;
      the docstring, which stated the layout as fact, now says CI's log
      shows it. (3) Not yet proven in that session: gate step 2 and the
      wiring test (the same stale mount, §5). (4) Minor: the simulated Edit
      denial under the lock (§3) and the two owner approvals have no
      evidence file; only `fix-lock.log` and `guard-relaxed.log` record the
      lock and its release — left as recorded. Under the owner's stop rule
      none is a code or test finding: no further round.
- [x] Diff matches the §1 plan: 18 files changed 678b1b8..HEAD, all inside
      §1's blast radius (verifier round 2); the one deviation, the checker's
      move out of `image/tests/`, is the owner's decision in §3.

## 5. Close Out
- [x] Full gate green (locally, 2026-10-12): all 7 steps; step 3 ran the
      image check's 28 tests (`gate.out`). The hygiene step refuses an
      unpinned base in `image/Containerfile`: a scratch copy with
      `FROM registry.fedoraproject.org/fedora-iot:44` gave "base image not
      pinned ('44' is a floating tag, not a version)".
- [x] Full gate, the fix round: locally it stops at step 2 (`gate2.out`).
      This session's sandbox mounted `.claude/settings.json` as it was on
      the old branch when the session opened, so the wiring check, and
      `test_this_repositorys_settings_pass` in step 3, read a stale file
      (git's copy is main's; the sandbox shows the old one and refuses to
      replace it). A session artefact, not a change: a session opened in
      this worktree now reads the right file. Steps 1 and 3 to 7, and the
      parts of step 2 that do not read the settings (the policy check; the
      guard's 91 tests), run one by one inside `safe-run.sh`, pass
      (`gate2-steps.out`, regenerated after verifier round 2: its first
      version had run step 3 outside the layer; the one failure in step 3
      is that same wiring test, beside the layer's `skipped=1`; the image
      check's 54 tests OK). **CI's gate on the pull request is the
      reference run: not green until seen.** Seen on 2026-10-19, pull
      request #15 at 9cc098b (main merged into the branch): CI run #40,
      `Full gate (Ubuntu)`, completed successfully in 1 min 51 s; OS image
      run #8, `Build and check the OS image`, completed successfully in
      1 min 12 s; "No conflicts with base branch"; merged by the owner as
      ab99913.
- [x] Scrap Sweep: nothing to delete. The tree holds only the ignored
      `.claude/state/` and `__pycache__`, and the sandbox's `/dev/null`
      placeholders (untracked, not files); the verifier's probes stayed in
      its temporary folder; the first `gate2-steps.out` was replaced, not
      kept beside the new one. `image/tests/check_image_root.py` is gone by
      the move, not as scrap.
- [x] Reviewed per `REVIEW.md`: the three passes by verifier round 2 —
      bugs (its own four mutants and the boundary runs, §4), security (the
      refused forms and the link handling probed; a `PrivateKey =` outside
      `etc/wireguard` not refused, as the docstring and ADR 0004 say),
      compliance (the diff inside §1's blast radius). Important findings:
      the evidence provenance, fixed (§5 above); none left under Skipped.
- [x] Lesson loop: two first occurrences, recorded here and not yet a rule
      (a rule follows the second). (1) `git switch -c` half-failed inside
      an `&&` chain (the sandbox's mount of `.claude/settings.json` could
      not be unlinked): the branch was made, HEAD stayed on
      `stage1/os-image`, and the red commit landed there; seen in `git
      log`, redone on the right branch, the old branch reset to its pushed
      commit. Check branch and HEAD after every switch; do not hide a
      switch in a chain. (2) The red commit's rewrite of the test file
      dropped two of the original 28 tests; the mutant run found it, not
      the builder. Diff the test names before and after a rewrite. The
      wiring check's failure on the stale mount is a session artefact, not
      a lesson for the rules.
- [x] Knowledge layer: README and AGENTS.md status; plan §2 and §7; ADR
      0004. No help page or runbook exists yet.
- [x] Commit message explains why: five commits, one per concern, each
      with its why (the Commits row); the record is committed with the
      change at each step and closed out in the last commit.

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
2026-10-12  fix round (a session in this worktree): the verifier's probe cases through
            its rust-ini probe and the checker (the §3 table); red run: Ran 51 tests,
            failures=40, errors=7 (red-tests.out); checker moved to image/ (owner);
            fix-lock engaged 23:53 (this session); after the fix: Ran 51 tests, OK
            (fix-tests.out); mutants 31 of 33 caught (mutants2.out: P1 and "greenboot
            binary not required" missed, tests to add after the release); local gate
            stops at step 2 on the stale settings mount (gate2.out), steps 1 and 3 to 7
            pass one by one (gate2-steps.out)
2026-10-13  fix-lock released 00:16 (owner); three tests added: Ran 54 tests, OK
            (fix-tests2.out); mutants 33 of 33 caught (mutants3.out)
2026-10-13  verifier round 2: F1 to F6 pass, every claim reproduced; verdict NOT YET
            PROVEN until CI is seen (its report in the pull request; its evidence in
            its session's temporary folder); finding 1 fixed: gate2-steps.out
            regenerated with every step inside safe-run.sh (guard: Ran 91 tests, OK;
            quality tools: Ran 78 tests, FAILED failures=1 the stale wiring test,
            skipped=1; image check: Ran 54 tests, OK; steps 4 to 7 exit 0)
2026-10-19  the branch pushed from the owner's desktop session (6b51deb; the owner: "I push, you open
            the PR"); PR #15 opened; main merged into the branch (9cc098b: 25 commits behind, one
            conflict, the plan's status line); CI on #15 at 9cc098b: CI run #40 Full gate (Ubuntu)
            1 min 51 s and OS image run #8 1 min 12 s, both completed successfully (the Actions page,
            read in the owner's browser); "No conflicts with base branch"; merged by the owner as
            ab99913; this record closed out on stage1/record-close-out, its own pull request
```
