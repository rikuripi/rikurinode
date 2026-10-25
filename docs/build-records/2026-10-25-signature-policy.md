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
- [ ] **Owner steps** (below, "Owner steps"): pending.
- [ ] **Remaining question** (to settle in design): how the CI job serves a signed image to the shipped policy, whose scope names `ghcr.io/rikuripi/rikurinode`, from a local registry (a mirror in `registries.conf`, with cosign's `--sign-container-identity`, or the job's own copy of the file), and which registry image, after its inspection.
- [ ] **Design:** after the probes.

## Evidence log

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
