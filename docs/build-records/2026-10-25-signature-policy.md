# Build Record — Stage 1 change 2a: the node's signature policy, proven in CI

| | |
|---|---|
| **Date** | 2026-10-25 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/signature-policy`, from `main` at `9371205`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature (the OS image's update trust; a control) |

## Task Contract

1. **Outcome:** the image carries the rule a node uses to refuse an OS image this project did not sign, and every pull request proves in CI that the rule accepts a signed image and refuses an unsigned or tampered one. 2b (publishing) and 2c (the node's refusal in a VM drill) then rely on a tested rule.
2. **Scope:** stage 1 change 2, first of three steps (the owner, 2026-10-25: "Three steps (Recommended)").
   - The signature policy for `ghcr.io/rikuripi/rikurinode` (`/etc/containers/policy.json`, `registries.d`), per ADR 0004 (D6, D7): cosign's older format, the main and the spare key, only for this image.
   - `image/check_image_root.py` pins it; tests in `image/tests/`.
   - A CI job, on every pull request that touches the image: a throwaway key signs a test image in a local registry, and skopeo or podman, under the shipped policy, accepts it and refuses an unsigned and a tampered one.
   - Risk tier: **high-risk** (update trust; supply chain).
   - **Not included:**
     - publishing to GHCR, the real signing key, the GitHub Environment (2b);
     - a node refusing an unsigned update in the VM drill (2c);
     - the version rule against downgrades (plan §4.2, stage 6);
     - keyless signing (not enforceable on a node; rechecked 2026-10-25, below).
3. **Done when:**
   - the probes in 0b are run in `rikuri-drill` and kept;
   - tests committed failing first, then pass; hand mutants of the new rules each turn the suite red, kept as diffs;
   - the CI job accepts the signed image and refuses the unsigned and the tampered ones, on the pull request;
   - the shipped image passes the checker (0 findings) and the CI drill passes;
   - `Full gate (Ubuntu)` passes;
   - one `verifier` pass has no Important finding.
4. **Authority:**
   - the owner's choice of signing and publishing as the next task, and of the three steps (2026-10-25);
   - edit the files in Scope and `.github/workflows/image.yml` for the new job (a CI change inside this task's Scope, named here);
   - use `rikuri-drill` for the probes: throwaway keys and images only, no real key;
   - adopt a local registry image for CI only, after the inspection AGENTS.md §2 requires, pinned by digest;
   - push this branch and open the pull request as a **draft** until the verifier and CI pass; no merge;
   - CI drill development runs: at most 2;
   - an independent check is required.
   - If 2a needs the two **public** keys before 2b, I stop and ask the owner for them. Private keys never enter this session.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 3 hours.

## 0b. Spec

- [x] **Facts rechecked 2026-10-25** (the 2026-10-12 research, `docs/build-records/evidence/2026-10-12-stage1-os-image/research.md`, "Signing and publishing"):
  - containers/image still cannot read cosign's new bundle format: container-libs issue 388 is open, and its fix is in progress (comments of 2026-10-10).
  - Keyless signatures from GitHub Actions still cannot be enforced: container-libs issue 34 and pull request 625 are open (last design comment 2026-09-02).
  - cosign's latest release is v3.1.4 (2026-10-20); the 3.1 line signs in the new format by default and can still sign in the old one.
- [x] **Probes 1 and 2** (`rikuri-drill`, booted `gbp`; reads, and a throwaway policy file with `skopeo --policy`; `/etc` not changed; the tiny image and folder removed, "left: 0"):
  - Fedora IoT 44 ships `/etc/containers/policy.json` with `default: insecureAcceptAnything`: any image, signed or not. This node has not changed it (`ostree admin config-diff` lists no `containers` file; it equals `/usr/etc`), so a policy the image ships reaches a node by the `/etc` merge, unless the node edits it. `registries.d` has Red Hat's two lookaside files only; no `/etc/pki/containers`. skopeo 1.22.3, podman 5.8.9, bootc 1.17.1; no cosign on the node (`01-probe.out`).
  - A policy naming a key file that does not exist still copies a local image of another scope: the key is read only for its own scope (skopeo 1.22.3). A `reject` default with `containers-storage` allowed copies a local image; `reject` for everything refuses it. `podman run` of a local image does not apply the policy (`02-probe.out`).
  - Not probed in the VM: a signed image in a registry (the VM has no network for a registry image); that is the CI job's.
- [x] **The owner's choice** (2026-10-25): "Make the keys now (Recommended)": the owner makes the main and the spare key pairs and the GitHub Environment now, 2b's steps moved earlier, and gives this session the two public keys only. 2a then tests the node's exact policy file inside the built image, with the image's own skopeo.
- [x] **Owner steps** (below, "Owner steps"): done 2026-10-28, restarted from clean.
- [x] **Probes 3 and 4** (`rikuri-drill`; the shipped `policy.json` with only its two key paths rewritten to throwaway keys, the shipped `registries.d` file, skopeo 1.22.3, cosign v3.1.4, distribution's registry 3.1.2 on `127.0.0.1:5000`; a `registries.conf` prefix rewrite reads `ghcr.io/rikuripi/rikurinode` from it; folder and images removed, "left: 0"):
  - **Probe 3:** every image in the scope was refused with "no signature exists", the signed ones too. containers/image looks up `use-sigstore-attachments` by the address it reads from, not by the name the policy scopes; a node reads `ghcr.io` itself, so the two agree there, but a mirror or a rewrite leaves the node without its signatures, and it refuses (fails closed).
  - **Probe 4**, with the same setting for the local address: signed by main and by spare, accepted (also by digest); unsigned, refused ("A signature was required, but no signature exists"); an untrusted key, refused ("cryptographic signature verification failed"); the main key claiming another repository, refused ("Signature for identity … is not accepted": the identity is checked against the policy's name, not the address read from); another image's valid signature at this digest, refused ("Signature for digest … does not match"); another repository, unsigned, accepted (the policy covers only this image). Without the setting, signed, refused.
  - **Case 10:** with `$HOME/.config/containers/policy.json` present and no `--policy`, skopeo used it instead of `/etc`'s: root's own config would replace the node's policy.
  - cosign 3.1.4 hides `--new-bundle-format`, `--tlog-upload`, `--use-signing-config` and `--sign-container-identity` from its help but takes them, and they signed in the format containers/image reads. Hidden flags may go in a later cosign: the pin holds them, and the CI proof fails if they stop working.
- [x] **Design** (2026-10-28):
  - **The image ships:**
    - `etc/containers/policy.json`: Fedora's own policy (`insecureAcceptAnything` by default, `docker-daemon` as Fedora has it) plus one scope, `ghcr.io/rikuripi/rikurinode`: `sigstoreSigned`, `keyPaths` the two keys, `signedIdentity` `matchRepository`. Every other image is as Fedora has it (ADR 0004, D7: "only for this image").
    - `etc/containers/registries.d/rikuri.yaml`: `use-sigstore-attachments: true` for the scope.
    - `usr/share/rikuri/signing/rikuri-main.pub` and `rikuri-spare.pub`, the owner's. The keys live under `/usr`, which only an image changes, so a key can be replaced by an update; the policy lives in `/etc`, where a node that never edited it takes each image's copy by the `/etc` merge (probe 1).
  - **The checker** (`check_signature_policy`, in `check_root`): the policy parsed as JSON with no key twice, equal to `POLICY_EXPECTED` (so an unknown key such as `Default`, which containers/image would refuse, a second requirement, any other scope, transport, key path or identity rule are findings); the registries.d file exactly its three lines, comments in column 0 and blank lines aside, in printable ASCII (YAML may read NEL as a line break); no other file in `registries.d` naming `rikuripi` (containers/image fails every pull of a scope two files configure), and no link there; the keys by SHA-256, pinned to the fingerprints above; and no `.config/containers` under `var/roothome` or a real `root`, and `root` a link only to `var/roothome`.
  - **The CI proof** (`image/drill/signature_policy.py`, in the build job after the checker, on the image just built): the registry's and cosign's release binaries, checked by SHA-256; throwaway keys; tiny test images, each with its own content; cosign signs by digest in the older format, with no transparency log. The image's own skopeo, under the image's own `policy.json` and `rikuri.yaml`, reads each case as `ghcr.io/rikuripi/rikurinode`. Into its container go only, read-only: the two throwaway public keys over the owner's (the policy's key paths stay), a `registries.conf.d` prefix rewrite to the local registry (never a mirror, which would fall back to ghcr.io), and the shipped `rikuri.yaml` with the local registry's name, made from the image's own file. A refusal passes only with containers/image's "Source image rejected:" and the case's own reason; any other failure is a miss.
  - **Rejected:**
    - a registry container image: distribution's release binary needs no digest of an image from Docker Hub, and the job already downloads from GitHub;
    - mounting the owner's keys and signing with a test key the policy trusts by rewriting `policy.json`: the proof would then not run the shipped file;
    - serving the local registry as `ghcr.io` with a test certificate, which would also prove `rikuri.yaml` under its real name: more setup on the runner (hosts file, CA) for one three-line file the checker pins.
  - **Not proven here, and whose it is:**
    - the shipped `rikuri.yaml` under the real `ghcr.io` name: 2b, by reading the published image with the image's skopeo;
    - that `bootc` applies the policy on a node, and refuses an unsigned update: 2c's drill;
    - a node whose admin edited `/etc/containers/policy.json` keeps that edit (the `/etc` merge): ADR 0004 and the update runbook, later;
    - a registries.conf mirror for ghcr.io on a node would leave it without signatures, so it refuses updates (probe 3): fails closed.

## Evidence log

All test runs were in `rikuri-drill` (`safe-run.sh` refuses on macOS; the CI gate runs them through it). The pre-commit hook is not installed in this clone (`core.hooksPath` unset) and gitleaks is not on the Mac: before each commit its other two checks ran by hand (`git diff --cached --check`, `repo_hygiene.py`), and CI's gate runs the secret scan.

- **Probes 3 and 4** (`03-probe.*`, `04-probe.*`): as in 0b. Trailing spaces were stripped from both outputs (one line each) for the whitespace check.
- **Red, the checker** (commit `9f694df`, with the shipped files): 112 tests, `FAILED (failures=1, errors=47)`, every one in `SignaturePolicy` (the missing `check_signature_policy`; the failure is `check_root` not running it).
- **Test changes after red, with their reasons:**
  - `scan etc: 2 file(s) read` became `4` in two existing tests (`test_main_exit_codes`, `test_scan_report_names_every_tree`): the fixture root now ships the policy and the registries.d file in `etc`, so the scan reads two more files. In the red commit.
  - A mutant added after red, "a NEL in a comment" (registries.d): no test reached the printable-ASCII rule on a comment line. In `c3a2c53`.
  - `test_signature_policy.py`: the mounts' options are read rather than matched as `:ro` (in `d43afab`): the VM run (below) needed SELinux's `z` as well.
- **Green, the checker** (commit `c3a2c53`): 112 tests, OK.
- **Mutants, the checker** (`05-mutants.py`, `05-mutants.out`; `05-mutants-run1.out` is the first run): eleven mutants, each weakening one rule. First run: ten failed; **m4 survived**, the policy's printable-ASCII rule: a byte outside ASCII already fails the decode, and JSON's other whitespace (tab, CR) Go and Python read alike. The rule went (in `c3a2c53`). Second run, the ten: each failed (m1, a key twice; m2, only the scope compared; m3, the registries.d file's ASCII rule; m5, another file naming the image; m6, a link; m7, the keys' SHA-256; m8, any link for `root`; m9, root's containers config; m10, not in `check_root`; m11, the registries.d file not compared), and the restored file passed.
- **Red, the CI proof** (commit `2d0c0bf`): `test_signature_policy.py` fails to import the missing `signature_policy`.
- **The CI proof in the VM** (`06-proof-vm.out`; an image made `FROM localhost/rikuri-os:gbp` with this change's three folders copied in, arm64 cosign and registry checked by SHA-256): first run, every case a miss with "permission denied" on the mounted files (SELinux; the pass rule counted the setup failure as a miss, not a refusal); with `z`, **8 of 8** as expected, exit 0.
- **The proof against Fedora's policy** (`07-proof-vm-fedora-policy.out`; the same image without this change's `policy.json`): the four refusal cases each a MISS ("accepted; expected a refusal"), 4 of 8, exit 1.
- **Green, all image tests** (on `d43afab`): `python3 -m unittest discover -s image/tests`, 243 tests, OK.
- **The VM after:** this task's test images, folders and throwaway keys removed; earlier tasks' images left as they were.
- **Knowledge layer:** nothing a user sees changes until 2b publishes; no help page or runbook covers updates yet, and the README's status stays as it is.
- **CI:** (to fill: the pull request's runs.)

### Verifier pass 1 and repair cycle 1 (2026-10-28)

- **CI, first run** (run 40776852353 at `dc83b1f`): `Full gate (Ubuntu)` passed; the build job's checker passed on the built image (`check_image_root: 0 finding(s)`); the proof failed: "signature_policy: the registry did not start (…/registry.log)", nothing more.
- **Verifier pass 1: FAIL**, one Important finding.
  - **I1:** the proof fails on the pull request, and its cause is not captured (the wait never polls the registry, and its log is not printed).
  - **Minor:**
    - **M1:** the policy keeps Fedora's `insecureAcceptAnything` default, which bootc's `--enforce-container-sigpolicy` and `ostree-image-signed:` refuse (research of 2026-10-12, lines 99 to 102), so a node can use only bootc's unverified path, whose use of the scoped policy is not yet confirmed;
    - **M2:** the policy applies only when the node tracks exactly `ghcr.io/rikuripi/rikurinode`.
  - **Nits:**
    1. the registries.d search for `rikuripi` misses a YAML-escaped name, and a folder named `*.yaml`: both fail closed;
    2. six surviving verifier mutants, each judged equivalent; one, `miss()` taking the reason anywhere in the output, is in the proof's refusal rule;
    3. two imprecise test names;
    4. `sha256sum -c` without `--strict`;
    5. the tools trusted through GitHub's asset digests only.
- **Cause, reproduced** (`08-registry-env-repro.out`, `rikuri-drill`): the workflow's `REGISTRY_VERSION: 3.1.2` reached the registry, which reads every `REGISTRY_*` variable as a config override: "parsing environment variable REGISTRY_VERSION: strconv.ParseUint: parsing \"1.2\": invalid syntax", exit 1. Without it, the registry serves. The VM run (06) had no such variable.
- **Red** (repair 1): three tests in `test_signature_policy.py`, `Registry`: the registry's environment has no `REGISTRY_*`; a failed start reports its exit and its log; the workflow names no `REGISTRY_*` variable. `FAILED (failures=1, errors=2)` in `rikuri-drill`.
- **Fix** (repair 1):
  - `registry_env()` starts the registry without any `REGISTRY_*` variable;
  - `registry_failure()` reports its exit code (or that it is still running) and its log;
  - the workflow's pins are renamed `DISTRIBUTION_VERSION` and `DISTRIBUTION_SHA256`.
  - Also, from the verifier's points:
    - a test that a reason before "Source image rejected:" does not count (nit 2's `miss()` mutant now fails; a stronger test);
    - `sha256sum --strict` (nit 4);
    - the two test names corrected (nit 3), and the design's wording here.
- **Left as they are, with reasons:**
  - nit 1: both cases fail closed, and refusing every registries.d file but Fedora's own would tie the checker to Fedora's file names;
  - nit 2's other five mutants: equivalent, as the verifier found;
  - nit 5: release signatures and provenance for CI-only tools, a backlog item.
- **For 2c, recorded now (M1, M2):**
  - 2c's drill must show whether bootc's default path applies the scoped policy to an update from `ghcr.io/rikuripi/rikurinode`, and that `bootc status` names exactly that reference.
  - If it does not apply it, the remedy is a stricter default (`reject`, with exceptions for local storage and the images the node runs), a behaviour-changing default and the owner's choice.

## Owner steps (2026-10-25, given to the owner; private keys never enter this session)

1. Install cosign 3.1 on the Mac and check `cosign version`.
2. Create the GitHub Environment `image-publish`: required reviewer the owner (self-review allowed, as the only reviewer); deployment branches `main` only; administrators may not bypass.
3. The main key, in an empty folder outside any synced folder: `cosign generate-key-pair --output-key-prefix rikuri-main`, with a password from a password manager. Put `rikuri-main.key` and the password into the Environment's secrets `COSIGN_PRIVATE_KEY` and `COSIGN_PASSWORD` (`gh secret set … --env image-publish`), then delete the `.key` file.
4. The spare key, on removable media: `cosign generate-key-pair --output-key-prefix rikuri-spare`; the `.key` file and its password kept offline, in two places, never in a cloud folder.
5. Give this session `rikuri-main.pub` and `rikuri-spare.pub` (public halves only).

### Owner steps, session of 2026-10-25 (paused by the owner: "Let's do this tomorrow. We'll start over.")

- **The Environment** `image-publish` exists: deployment branches `main` only (`custom_branch_policies`, one rule `main`, read back through the API). Required reviewers are not offered for a private repository on this plan (GitHub's documentation: only public repositories), so the owner chose **"You start each publish (Recommended)"**: 2b's publish job runs only on `workflow_dispatch` from `main`, never on a merge. `can_admins_bypass` stays `true`; the page does not offer the switch on this plan, and the owner is the only admin. A dated clarification of the Task Contract's 2b plan and of ADR 0004's "only a job on `main`" follows in 2b.
- **The keys: not finished; start over.** Several runs overlapped: commands started from this session's terminal pane begin in the repository folder, and some key pairs were written there (git ignores `*.key`; this session never opened a private file). At the pause, by file name only:
  - GitHub: `COSIGN_PRIVATE_KEY` (04:27:07 UTC) and `COSIGN_PASSWORD` (04:27:38 UTC), whose match is unknown; both to be replaced.
  - `~/rikuri-keys`: one main pair (21:25:51 local); the repository folder: one stray `rikuri-main.pub`; the stick `/Volumes/Rikuri`: one spare pair (21:38:48 local).
- **Lesson for the restart:** the owner runs the key steps as one short list in Terminal.app, outside this session, with full paths, and tests the password (`cosign public-key --key …`) before storing it.

### Owner steps, restarted 2026-10-28 (done; Terminal.app, one step at a time; checked here by file name, time and secret name only)

- **Clean-up:** both old Environment secrets deleted; the old main pair in `~/rikuri-keys` and the stray `rikuri-main.pub` in the worktree removed; the stick's spare folder was already empty. Old passwords retired in the owner's password manager.
- **Main key:** a new pair made 14:21:14 local with a new password-manager password; the password tested on that file with `cosign public-key --key` before storing; `COSIGN_PASSWORD` set 21:23:45 UTC and `COSIGN_PRIVATE_KEY` 21:25:34 UTC, in `image-publish` only (no repository-wide secrets); the `.key` file then deleted from the Mac.
- **Spare key:** a new pair made 14:29:24 local on the stick `Rikuri`, with its own, different password, tested the same way; never uploaded. A second offline copy: pending, the owner's.
- **Public keys** (not secret), SHA-256 of the `.pub` files:
  - `rikuri-main.pub`: `605548bfcc3a4d6f0a85b17ef7ccb8af20507ddbd22d1473b84a769d4a990c0d`
  - `rikuri-spare.pub`: `49dc526a92bceec51a81fda2e99b17546d1f142f1d4ccc84e76c513424fc0ba8`
