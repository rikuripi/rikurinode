# Build Record — Stage 1 change 2b: publish the OS image to GHCR, signed with the real key

| | |
|---|---|
| **Date** | 2026-10-28 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/publish`, from `main` at `ce93c07`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature (the OS image's release path; a control) |

## Task Contract

1. **Outcome:** the owner can publish a node OS image with one click on `main`. The image that gets signed is the one that was built, checked and drilled, and the job proves under the real `ghcr.io` name that the node's own policy refuses that image before it is signed and accepts it after.
2. **Scope:** stage 1 change 2, second of three steps (owner, 2026-10-25).
   - A new workflow, `.github/workflows/publish.yml`, started only by `workflow_dispatch` and only on `main`. Three jobs:
     1. **build:** no secret. Build once, the checker, the throwaway-key signature proof (2a), the VM drill, then push to `ghcr.io/rikuripi/rikurinode:<fixed tag>` with the job's `GITHUB_TOKEN`.
     2. **sign:** in the Environment `image-publish`. The pulled image must equal the one built. The image's own skopeo, under its own policy, refuses the digest as unsigned. cosign signs it by digest in the older format, with the key read from the Environment in that one step only. The same skopeo then accepts it by digest and by tag.
     3. **anonymous:** no credential. A node's read: pull and verify with no login.
   - `image/drill/publish.py` holds those steps, as pure functions tested in `image/tests/test_publish.py`. `image/drill/signature_policy.py`'s `sign_argv` gains an option to drop `--allow-http-registry`. Workflow tests are in `scripts/quality/tests/test_workflows.py`.
   - Docs: a dated clarification in ADR 0004 (the owner starts each publish; fixed tags), a runbook `docs/runbooks/publish-os-image.md`, and README's status.
   - Risk tier: **high-risk** (signing key, supply chain, an irreversible public package).
   - **Owner choices** (2026-10-28):
     - "Fixed names only (Recommended)": each publish gets a tag that never moves, `<Fedora release>.<UTC date>.<run number>`, for example `44.20261028.3`. The moving tag nodes follow is decided in 2c.
     - "Yes, drill every publish (Recommended)".
   - **Not included:**
     - a moving tag;
     - a node following an update, and refusing an unsigned one (2c, with M1 and M2 from 2a);
     - the version rule against downgrades (stage 6);
     - signatures and provenance of the CI tools (backlog);
     - making the package public (the owner's step, below);
     - sharing steps between `image.yml` and `publish.yml` (see the design).
3. **Done when:**
   - tests committed failing first, then pass in `rikuri-drill`; a hand mutant of each new rule turns them red;
   - on the pull request: `Full gate (Ubuntu)` and the image workflow pass;
   - one `verifier` pass has no Important finding;
   - **after the owner merges** (the workflow can only be started from `main`), the owner starts one publish, and its `build` and `sign` jobs pass: the pulled image equals the one built; unsigned, refused for "no signature exists"; signed, accepted by digest and by tag;
   - the owner makes the package public, and the `anonymous` job passes on a re-run.

   The last two items go in the docs-only close-out. If either fails, the repair is a new pull request within this task's limits.
4. **Authority:**
   - the owner's "Ok 2b" (2026-10-28) and the two choices above;
   - edit the files in Scope. `.github/workflows/publish.yml` is a new CI workflow, named here: it is the task, not a convenience change to CI;
   - `rikuri-drill` for tests: throwaway keys only;
   - push this branch and open the pull request, as a **draft** until the verifier and CI pass; no merge;
   - an independent check is required.
   - The real private key and its password never enter this session: only the Environment's job sees them. The publish run, and making the package public, which cannot be undone (ADR 0004, D6), are the owner's actions.
5. **Limits:** one task; two repair cycles; two review rounds; at most 2 publish runs before close-out; time budget 3 hours.

## 0b. Spec

- [x] **Facts** (2026-10-28, GitHub's documentation):
  - A package published from a workflow is private at first ("When you first publish a package, the default visibility is private").
  - It cannot be made private again once public.
  - The publishing repository gets admin on it, and the job needs `packages: write`.
- [x] **Probe 5** (`rikuri-drill`, `01-probe.sh`, `01-probe.out`; throwaway key, a registry on `127.0.0.1`; folder and names removed, "left: 0", the earlier image `gbp` kept):
  - **(a)** after `podman push`, the manifest's config digest equals the built image's ID, for a tiny image and for the OS image (`EQUAL` both). So "the image pulled is the one built" is one comparison: the pulled image's ID against the build job's.
  - **(b)** cosign v3.1.4 signs with `--key env://COSIGN_PRIVATE_KEY` and a password, in the older format, with no key file on disk. A wrong password is refused ("decryption failed"). The shipped policy accepts the result by digest and by tag, and refuses the unsigned OS image for "no signature exists".
- [x] **Design** (2026-10-28):
  - **`publish.yml`**: `workflow_dispatch` only, and every job also has `if: github.ref == 'refs/heads/main'`, so a dispatch from any other branch runs nothing. The Environment's own rule (`main` only) holds the key the same way. Top-level `permissions: {}`; each job names its own. One publish at a time (`concurrency`, never cancelled).
  - **Job `build`** (`contents: read`, `packages: write`; no Environment, no secret):
    - refuse a re-run (`GITHUB_RUN_ATTEMPT` above 1): a re-run would build a new image under the same fixed tag, so the tag would move;
    - the tag `<FEDORA_RELEASE>.<UTC date>.<run number>`;
    - build with two labels, `org.opencontainers.image.source` (it links the package to this repository) and `org.opencontainers.image.revision` (the commit);
    - the checker, the 2a proof and the VM drill, on this one local image, as in `image.yml`;
    - push it to `ghcr.io/rikuripi/rikurinode:<tag>` with the job's token;
    - outputs: the tag, the pushed digest, the image ID.
    - The fixed tag is unsigned for the minutes until `sign` ends. No node follows a fixed tag, and an unsigned one is refused (the proof), so this fails closed.
  - **Job `sign`** (Environment `image-publish`; `contents: read`, `packages: write`). One step per action, so the key is in one step's environment only:
    1. pull by digest; the pulled image's ID must equal the build job's (probe 5a);
    2. the pulled image's own skopeo, under its own policy and `rikuri.yaml`, no override mounted, reads the digest from `ghcr.io`: refused, for "no signature exists" (`signature_policy.miss`). This is also the first proof of the shipped `rikuri.yaml` under the real name: without it the reason would be the same, so step 4 is the proof that the signature is found;
    3. **the only step with the secrets:** cosign, pinned by SHA-256 as in `image.yml`, signs the digest. It runs with an environment holding only `PATH`, `HOME`, `DOCKER_CONFIG` (its registry login), `COSIGN_PASSWORD` and `COSIGN_PRIVATE_KEY`; it uses `--key env://COSIGN_PRIVATE_KEY`, the older format, no transparency log, identity `ghcr.io/rikuripi/rikurinode:<tag>`, and no `--allow-http-registry`;
    4. the same skopeo accepts the digest, and then the tag.
    - The package is private until the owner makes it public, so these reads use a read-only mounted copy of the job's login (`--src-authfile`). A login does not change the policy's checks.
  - **Job `anonymous`** (`contents: read` only; no login): as a node reads. Pull by digest, then the image's skopeo accepts it with no credential. While the package is private this job fails and says so: making it public is the owner's step. It can be re-run alone ("Re-run failed jobs").
  - **`image/drill/publish.py`**: subcommands `tag`, `same`, `refused`, `sign` and `accepted`. Their pure parts (the tag's form, the digest's form, the command lines, the signing environment) are tested in `image/tests/test_publish.py`. `scripts/quality/tests/test_workflows.py` holds the workflow's shape:
    - the trigger;
    - the `main` rule on every job;
    - the permissions;
    - the Environment on `sign` only;
    - `secrets.` named only in `sign`'s signing step;
    - the re-run refusal;
    - cosign's pin the same as `image.yml`'s.
  - **Rejected:**
    - **Signing in the build job:** the Environment's secrets would sit in a job that runs the base image's and the drill's code.
    - **Publishing on every merge:** the owner chose to start each publish (2a, Owner steps).
    - **A reusable workflow shared with `image.yml`:** it is a refactor of a working, required workflow. The duplicated steps are five; a test holds the tool pins equal.
    - **Pushing by digest with no tag:** podman needs a tag to push, and a fixed tag is wanted anyway.
    - **`cosign verify`:** it passes on signatures the node cannot read (ADR 0004). The node's own skopeo and policy decide.

## Evidence log

- **Probe 5:** as in 0b. tar's clock-skew warnings (the VM's clock) are left out of `01-probe.out`.

## Owner steps (after the merge)
- **Red** (`rikuri-drill`): `image/tests/test_publish.py` fails to import the missing `publish`; `scripts/quality/tests/test_workflows.py` ran 21 tests, `FAILED (errors=10)`, the ten new `Publish` tests (no `publish.yml`). The 11 existing tests pass. The module's docstring names the new tests.
- **Green** (`rikuri-drill`, on the fix commit): `image/tests`, 259 tests, OK (`test_publish.py`, 13); `scripts/quality/tests/test_workflows.py`, 21 tests, OK; `test_osv_audit.py` OK (it audits every `uses:`, `publish.yml`'s included). The quality suite's other tests need git and `.claude/`, which the VM copy lacks; CI's gate runs them. `publish.py tag` by hand: attempt 1 printed `44.20261028.3`; attempt 2 refused, exit 1.
- **Mutants** (`02-mutants.py`, `02-mutants.out`): seventeen, each weakening one rule of `publish.py` (m1 to m8) or `publish.yml` (m9 to m17). Each is KILLED by a failing test, and both suites pass once restored. A first run counted every workflow mutant as killed because `-m unittest <path>` could not import the test file. The script now runs the file directly, and counts a kill only when the tests ran.
- **Protected paths, the risk note REVIEW.md asks for:**
  - `.github/workflows/publish.yml` is new. It is the only workflow with `packages: write` and the only one in the Environment. It runs only by hand, on `main`, and holds the key in one step.
  - `.github/workflows/image.yml`: one comment line.
  - No gate, check or test was removed or loosened.
- **Knowledge layer:** `docs/runbooks/publish-os-image.md` (new; the owner's steps, the package made public, what to do when a job fails); ADR 0004's clarification; README's status. A node user sees nothing new: no node follows a fixed name.

1. Merge the pull request once CI is green.
2. Start one publish (`docs/runbooks/publish-os-image.md`, "Publish").
3. When its third job fails for "not public yet", make the package public and re-run that job (the runbook's "The first publish only"). It cannot be undone; D6 decided it.
4. Send this session the run's link. The run's evidence then goes in the close-out.
