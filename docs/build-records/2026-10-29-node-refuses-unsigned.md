# Build Record — Stage 1 change 2c: a node refuses an unsigned update, in the VM drill

| | |
|---|---|
| **Date** | 2026-10-29 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/node-refuses-unsigned`, from `main` at `463e28e`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | record `465a500`; red `2df92e9`, fix `7570bda`; repair 1: red `a0aed68`, fix `d36556f`; repair 2: red `83b3ddd`, fix `6575655`; merged as `7715d05` (#53); this close-out |
| **Status** | DONE: #53 merged by the owner; on its final commit the drill ([run 40935486256](https://github.com/rikuripi/rikurinode/actions/runs/40935486256)) passed every case, 4 and 5 included, and `Full gate (Ubuntu)` passed (run 40935486263). Verifier pass 1 FAIL on one ADR sentence (Important, wording), corrected in this close-out by the owner's choice; follow-up pass PASS |
| **Change type** | feature (the node's update path; a control) |

## Task Contract

1. **Outcome:** CI proves, on a booted node in a VM, that the node's own update command (`bootc switch`) refuses an OS image this project did not sign and stages one it did sign, under the real name `ghcr.io/rikuripi/rikurinode`, on every image pull request and every publish.
2. **Scope:** stage 1 change 2, the last of three steps (owner, 2026-10-25).
   - `image/drill/vm_drill.py`:
     - the VM's restricted network gains one forwarded destination, a registry on the CI machine;
     - two drill-only files on the VM's disk point the image's name at that registry;
     - two new cases, run after the existing ones: an unsigned image refused, and the first published image (`44.20261029.1`, signed in 2b) staged.
   - `image/drill/signature_policy.py`: its registry start and its registries.d rewrite become reusable. 2a's proof keeps its behaviour.
   - Tests: `image/tests/test_vm_drill.py`, `image/tests/test_signature_policy.py`, `scripts/quality/tests/test_workflows.py`.
   - Workflows: `image.yml`'s `drill` job fetches the pinned registry, and both drill runs (`image.yml`, `publish.yml`) pass it to the drill.
   - Docs: ADR 0004 (a dated clarification: fixed names only, the node's check proven), the stage 1 record's change list, README's status line, the runbook only if a step changes.
   - Risk tier: **high-risk** (the update path's signature check; CI is a control).
   - **Owner choices** (2026-10-29, AskUserQuestion):
     - "Fixed names only (Recommended)": nodes follow no moving tag. A node is switched to each release's fixed name, in 2c by the drill and later by the control plane. ADR 0004's open point ("the moving name … is decided … in 2c") is settled: there is none.
     - "A mirror inside CI (Recommended)": the unsigned image lives only in a registry on the CI machine; nothing unsigned goes into the public package.
     - "Stop and ask me (Recommended)": if bootc's normal path does not apply the policy, 2c ends `NEEDS_OWNER_DECISION` with the evidence; no stricter default is built in this task.
   - **Not included:**
     - a stricter policy default (`reject`) or bootc's `--enforce-container-sigpolicy` (see 0b);
     - booting the signed update (staging is where the node's check happens: plan §4.1, "verifies the signature before it stages");
     - the version rule against downgrades (stage 6), and how a node learns of a new release (the control plane);
     - a wrong-key or tampered case through bootc (2a proved those through the same library and policy);
     - the backlog items from 2b (M4, the earlier ID compare, N2, CI tool provenance, the spare key's second copy).
3. **Done when:**
   - tests committed failing first, then pass in `rikuri-drill`; a hand mutant of each new rule turns them red;
   - on the pull request: `Full gate (Ubuntu)` and the image workflow pass; the drill's summary shows case 4 (the unsigned update refused for "no signature exists", nothing staged) and case 5 (the signed update staged, with exactly the published digest and name in `bootc status`) as Pass, beside the existing cases;
   - one `verifier` pass has no Important finding.
   - The publish workflow's drill runs the same code; it is proven at the owner's next publish, not in this task.
4. **Authority:**
   - the owner's "Ready for 2c" (2026-10-29) and the three choices above;
   - edit the files in Scope; the workflow edits are this task's, named here, not a convenience change to CI;
   - `rikuri-drill` for tests; the CI machine copies the public signed image anonymously from `ghcr.io` (a named destination); the VM still has no outbound network;
   - push this branch and open the pull request, as a **draft** until the verifier and CI pass; no merge;
   - an independent check is required. No key, password or credential is used: the signed image was signed in 2b.
5. **Limits:** one task; two repair cycles; two review rounds; at most 4 CI drill runs before the verifier; time budget 3 hours.

## 0b. Spec

- [x] **Facts** (bootc's source, `bootc-dev/bootc` `main`, read 2026-10-29; `crates/ostree-ext/src/container/mod.rs`, `store.rs`, `skopeo.rs`, `crates/lib/src/cli.rs`):
  - `bootc switch` without `--enforce-container-sigpolicy` uses `ostree-unverified-registry:`, which is `SignatureSource::ContainerPolicyAllowInsecure`: "Fetches will defer to the `containers-policy.json` default". The source reads as if the node's policy, scoped requirement included, is still applied on this path. Not yet proven: case 4 is the proof (2a's M1).
  - With `--enforce-container-sigpolicy` (`ContainerPolicy`), bootc first refuses any policy whose default is `insecureAcceptAnything` ("refusing usage"). The node's policy has that default, so enforce mode needs the stricter default 2a recorded as the owner's choice. Not in this task.
- [x] **Design:**
  - **The network:** QEMU's user network keeps `restrict=on` and its one SSH forward, and gains `guestfwd=tcp:10.0.2.100:5000-tcp:127.0.0.1:5000`. QEMU's `restrict` does not affect explicit forwards, so the VM reaches that one address and nothing else.
  - **The registry** (distribution's pinned release, as in 2a) serves on the CI machine's `127.0.0.1:5000`. Into it go:
    - the published `ghcr.io/rikuripi/rikurinode@sha256:c984d651…` as tag `44.20261029.1`, with its signature tag `sha256-c984d651….sig`, both copied with digests kept, anonymously, by the image's own skopeo;
    - the image under test, unsigned, as tag `drill-unsigned`.
  - **In the VM, on the drill's disk only:** a registries.conf.d file rewriting the prefix `ghcr.io/rikuripi/rikurinode` to `10.0.2.100:5000/rikuripi/rikurinode` (a rewrite, never a mirror, as in 2a), and a copy of the shipped registries.d file naming that address (2a's probes 3 and 4: the attachment setting is looked up by the address read from). The policy and keys are the image's own, untouched.
  - **Case 4:** `bootc switch ghcr.io/rikuripi/rikurinode:drill-unsigned` fails with `Source image rejected: A signature was required, but no signature exists` (`signature_policy.miss`), and `bootc status` shows nothing staged.
  - **Case 5:** `bootc switch ghcr.io/rikuripi/rikurinode:44.20261029.1` succeeds, and `bootc status` shows it staged with exactly `sha256:c984d651…` and the name `ghcr.io/rikuripi/rikurinode:44.20261029.1` (2a's M2), in the spec and in the staged deployment. The staged image's signature field is recorded as seen.
  - Cases 4 and 5 run last, after the containers-range checks, so the staged update meets no later reboot.
  - **Rejected:**
    - the VM reading `ghcr.io` directly: it would give the drill VM an outbound network;
    - an unsigned tag in the public package: the owner's choice;
    - booting the signed image: it is the 2b image, older than the one under test; the check under test happens at staging;
    - `--enforce-container-sigpolicy`: it refuses the node's current policy outright (Facts).

## Evidence log

- **Red** (`rikuri-drill`, commit `2df92e9`; `01-red.out`): `test_vm_drill.py` stops at import (`vm_drill` has no `SIGNED_REF`); `test_signature_policy.py`, 22 tests, 2 errors (no `registry_config`; `ci_registries_d` takes no address); `test_workflows.py`, 22 tests, 2 failures (no `--registry` in either drill step). `image/tests` as a whole: 218 tests, 3 errors.
- **Green** (`rikuri-drill`, on the fix commit): `test_vm_drill.py` 67 tests OK; `test_signature_policy.py` 22 OK; `test_workflows.py` 22 OK; `image/tests` 284 tests OK. `git diff --check` clean.
- **Test code changed after the red commit, with reasons:**
  - `Verdict.test_every_check_names_a_step` lists every step the drill must pass; it gains cases 4 and 5, as designed (an existing test, so recorded here).
  - `SignatureCases.test_case5_passes_only_when_the_signed_image_is_staged` gains a successful switch that stages another digest: mutant m14 survived without it (below). A stronger test.
  - The test module's docstring names cases 4 and 5 and this record.
- **Mutants** (`02-mutants.py`; run 1 `02-mutants.out`, run 2 `02-mutants-run2.out`): 22 mutants, each weakening one new rule, run in a copy of the tree; a kill counts only when the tests ran and failed. Run 1: 21 of 22 killed; **m14 survived** (case 5 judged by `rc == 0` alone). Run 2, after the stronger test: **22 of 22 killed**, and the restored tree passes.
- **Not covered by a unit test, and why it fails closed:** `main()` calling `serve_registry`, `configure_mirror`, `case4` and `case5`. If any were skipped, `verdict()` fails the drill, because `EXPECTED` requires both cases' passes (`Verdict` tests).
- **CI run 1** (PR #53 at `7570bda`): `CI` and the guard tests passed; **OS image failed** in the drill, [run 40932208792](https://github.com/rikuripi/rikurinode/actions/runs/40932208792), at the first VM start, before any case ran:
  `qemu-system-x86_64: -netdev user,…,guestfwd=tcp:10.0.2.100:5000-tcp:127.0.0.1:5000: Failed to connect to '127.0.0.1:5000': Connection refused` and `Could not open guest forwarding device 'guestfwd.tcp.5000'`. A `tcp:` target is a character device QEMU connects once, at its start; the drill's registry starts only before case 4. Reported by the owner, confirmed in the log.
- **Repair cycle 1** (1 of 2):
  - red `a0aed68` (`03-red-repair1.out`): the forward must be `guestfwd=tcp:10.0.2.100:5000-cmd:nc -N 127.0.0.1 5000` (QEMU starts the command for each connection the guest opens), and both drill jobs must install `netcat-openbsd` with QEMU and record its version. Two failures, as expected.
  - fix: the `cmd:` forward; `netcat-openbsd` beside QEMU and OVMF in `image.yml`'s drill job and `publish.yml`'s build job, from Ubuntu 24.04's archive like them, its version in the summary.
  - test code changed, with reasons: `QemuArgv`'s forward assertion (the form changed, as above); a new workflow test for nc; its version-line assertion corrected before the red commit (image.yml records versions inside a `{ … }` block).
  - green (`rikuri-drill`): `image/tests` 284 OK; `test_workflows.py` 23 OK.
  - mutants (`04-mutants-repair1.out`): 25, with m2b (the forward back to `tcp:`), m23 and m24 (either job without nc): **25 of 25 killed**; the restored tree passes.
- **CI run 2** (at `d36556f`): the drill, [run 40933775613](https://github.com/rikuripi/rikurinode/actions/runs/40933775613), ran every case (`ci-40933775613-06-case4.out`, `ci-40933775613-07-case5.out`):
  - first boot, cases 1, 2b and 3, and the containers-range checks: **Pass** (the forward changes none of them);
  - **case 5: Pass.** `bootc switch ghcr.io/rikuripi/rikurinode:44.20261029.1` exit 0, "Queued for next boot", staged `('ghcr.io/rikuripi/rikurinode:44.20261029.1', 'sha256:c984d651db4f15be5dac56fcd974d230bc248536fade4ceee29323abadfdecfd')`, and the spec follows that name: **2a's M2 answered**;
  - **case 4: Fail, the harness's rule, not the node.** bootc refused: exit 1, `error: Switching: Switching (ostree): Preparing import: Fetching manifest: failed to invoke method OpenImage: A signature was required, but no signature exists`, staged `None`. **2a's M1 answered: bootc's default path applies the node's scoped policy.** The rule required skopeo's `Source image rejected: ` before the reason; bootc's image proxy does not print it. The test's line had been guessed, not observed. Reported by the owner, confirmed in the evidence.
- **Repair cycle 2** (2 of 2, the last):
  - red `83b3ddd` (`05-red-repair2.out`): the fixture is now the line CI printed; new tests require the reason directly after the proxy's `OpenImage` error (not anywhere, not after another method), and a refusal for another reason after `OpenImage` fails. Two failures, both the observed refusal judged a miss, as in CI.
  - fix: `unsigned_refused` requires a non-zero exit, `failed to invoke method OpenImage: A signature was required, but no signature exists` (`BOOTC_REFUSED`), a readable status and nothing staged. `signature_policy.miss`, for skopeo, is unchanged.
  - test code changed, with reasons: the `REFUSED` fixture (observed, above); two anchoring tests; after the fix, a success carrying the line must fail (mutant m7c survived run 1, `06-mutants-repair2.out`).
  - green (`rikuri-drill`): `image/tests` 285 OK; `test_workflows.py` 23 OK.
  - mutants: 27, with m7b (the reason anywhere) and m7c (exit code ignored); run 2 (`06-mutants-repair2-run2.out`): **27 of 27 killed**, the restored tree passes.
  - Repair cycles are now used up. Any further failure ends this task `BLOCKED`.
- **CI run 3** (at `6575655`, the commit merged): OS image [run 40935486256](https://github.com/rikuripi/rikurinode/actions/runs/40935486256), all jobs pass. The drill: first boot, cases 1, 2b and 3, both containers-range checks, **case 4 Pass** (`bootc switch exit 1: … failed to invoke method OpenImage: A signature was required, but no signature exists; staged: None`), **case 5 Pass** (staged `('ghcr.io/rikuripi/rikurinode:44.20261029.1', 'sha256:c984d651db4f15be5dac56fcd974d230bc248536fade4ceee29323abadfdecfd')`, the spec follows that name). 2a's proof in the same run: 8 of 8. CI run 40935486263: `Full gate (Ubuntu)` pass (`image/tests` 285 OK, `scripts/quality/tests` 153 OK). CI drill runs used: 3 of 4.
- **The staged image's signature field** (`ci-40933775613-07-case5.out`, from CI run 2; run 3's log shows the same staged name and digest): bootc records none, only `{"image": "ghcr.io/rikuripi/rikurinode:44.20261029.1", "transport": "registry"}`: its default origin, `ostree-unverified-registry`. The check that refuses an unsigned image is the node's `policy.json`, through bootc's image proxy (case 4), not an ostree signature.
- **Protected paths changed, the risk note REVIEW.md asks for** (added at close-out; verifier nit 1): `.github/workflows/image.yml` and `publish.yml` (the drill gets a pinned registry, checked by SHA-256 before use, and `netcat-openbsd` from Ubuntu's archive with its version recorded; no permission, secret or trigger changed) and `scripts/quality/tests/test_workflows.py` (two tests added; none loosened). Risk: the drill now depends on reading the public package from `ghcr.io` anonymously; if that read fails the drill fails closed. The VM's network gains one fixed forward to the runner's loopback registry.

## Verify

- **Verifier pass 1** (2026-10-29, on `6575655`; finished after the owner merged #53): **FAIL**, one Important finding, no code defect.
  - **Important:** ADR 0004's new clarification said "whoever can move a tag cannot point nodes at an older signed image". The node's policy (`matchRepository`) accepts any signed image under any tag of the repository, and GHCR does not freeze tags, so this was an unsupported security claim. Confirmed by the builder.
  - Checks it saw pass: the full gate and the drill on `6575655` (runs 40935486263, 40935486256); 2a's proof unchanged; the network (one fixed forward); case 4 and 5's rules (anchored, compared with the CI output); the seed copies' `--insecure-policy` (bytes only; the digest kept and compared); no test loosened after any red commit; the workflows' pins. Not yet proven by it: its own test and mutant runs (the sandbox blocks the local network to `rikuri-drill`; it did not route around it).
  - Nits: (1) no protected-path risk note; (2) "every publish" stated as seen; (3) the signature field not recorded; (4) the record's last CI run, Commits and Status unfilled; (5) the runbook's "Nodes do not follow these fixed names" reads against the ADR's "a node is switched to a release's fixed name". Backlog, from 2a: `start_registry` would accept another process already answering on `127.0.0.1:5000`.
- **The owner's decision** (2026-10-29, AskUserQuestion; repair cycles used up and #53 merged, so `NEEDS_OWNER_DECISION`): "Fix it in the close-out (Recommended)". This close-out corrects the ADR sentence and nits 1 to 5; the `start_registry` point goes to the backlog.

- **Follow-up pass** (review round 2 of 2, on this close-out's corrections only): **PASS**. Each correction is accurate and supported (the policy's `matchRepository`, `publish.yml`'s re-run refusal, plan §4.2 and stage 6, runs 40935486256 and 40935486263 re-read, the commits listed); `git diff --check` clean; the guard tests not required (nothing under `.claude/`). Its two nits are fixed here (this Status, the run named for the signature field); `start_registry` stays on the backlog.

## Close Out

- **Outcome:** `DONE`. On a booted node in the VM drill, the node's own `bootc switch` refuses an unsigned image named `ghcr.io/rikuripi/rikurinode` for "no signature exists" and stages nothing, and stages the first published signed image with exactly its digest and name. 2a's M1 and M2 are answered; the owner settled "fixed names only".
- **Limits used:** repair cycles 2 of 2; review rounds 2 of 2; CI drill runs 3 of 4; time about 2 hours, within the 3-hour budget.
- **Not yet proven:** the publish workflow's drill runs the same code; it is seen at the owner's next publish.
- **Backlog, not started:** the never-downgrade rule (stage 6; the real protection against an older signed image); `start_registry` accepting another process on `127.0.0.1:5000`; from 2b: M4, the earlier ID compare, N2, CI tool provenance, the spare key's second copy.
