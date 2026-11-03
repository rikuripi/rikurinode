# Build Record — publish's USB installer: the signed image by a local name

| | |
|---|---|
| **Date** | 2026-11-03 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/publish-iso-payload`, from `main` at `6c1a55e`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | PR #59, merge `2aafcd7`: `e504638` (red), `ac80d87`, `77bcd77` |
| **Status** | COMPLETE (2026-11-03) |
| **Change type** | fix |

## Task Contract

1. **Outcome:** a publish makes the install stick for 5b, holding the signed image (its content: the same image, pulled by the signed digest).
2. **Scope:**
   - `.github/workflows/publish.yml`, job `iso`, and its test in `scripts/quality/tests/test_workflows.py`;
   - this record, and the 5a record's "Not yet proven" note on the job.
   - Risk tier: **high-risk** (the release pipeline; the stick erases a disk).
   - **Not included:** the installer, `image.yml`, 5b itself.
3. **Done when:**
   - a workflow test fails first, then passes, in `rikuri-drill`;
   - `Full gate (Ubuntu)` passes on the PR;
   - one `verifier` pass has no Important finding.
   - Not provable before merge: `publish.yml` runs only on `main`, by hand. The owner's next publish is the proof; it is recorded in this record's close-out.
4. **Authority:** the owner's "Yes, fix it (Recommended)" (2026-11-03); this branch; a draft PR; no merge. An independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; development CI at most 3 runs.

## 3. Debug

- **Seen:** Publish the OS image #2, [run 41705388378](https://github.com/rikuripi/rikurinode/actions/runs/41705388378) on `6c1a55e`. The first three jobs pass; `44.20261103.2` (`sha256:d487ae32…c16f`) is published and signed. The job `iso` fails in image-builder's `org.osbuild.skopeo` stage:
  > `Copying this image would require changing layer representation, which we cannot do: "Destination specifies a digest"`
- **Cause:** the job passes the payload as `"$PUBLISHED@$DIGEST"`. image-builder copies it into the stick's store under that name; containers-storage keeps layers unpacked, so the copy cannot keep the manifest byte-identical, which a digest name requires.
- **Why CI did not catch it:** `image.yml`'s install job passes the payload by a local name (`$IMAGE`, `localhost/rikuri-os:ci`), and `publish.yml` never runs on a pull request.
- **Fix:** after the anonymous pull, give the same image a local name, `"$PUBLISHED:$TAG"` (in the runner's store only; nothing is pushed); stop unless that name's digest is `$DIGEST`; pass that name to image-builder, as `image.yml` does.

## Evidence log

- **Red** (rikuri-drill, `safe-run.sh`, before the fix): `test_workflows.py` `Ran 26 tests` `FAILED (failures=1)`: `test_the_iso_job_builds_the_stick_from_the_signed_digest_with_no_login`, `'podman tag "$PUBLISHED@$DIGEST" "$PUBLISHED:$TAG"' not found`.
- Test change: the old line asserted the digest as the payload; that is the defect, so it goes.
- The drill VM had a new address (`10.37.129.3`, from Parallels) and the pinned host key was lost from the scratchpad; the key was accepted on first use and recorded: `SHA256:NtVMqX12NYeujT0KNVRasNSCtiVoLgh3+SqVUFD5938` (ED25519).
- **Fix:** a step after the pull names the digest `"$PUBLISHED:$TAG"` in the runner's store and stops unless `podman image inspect` gives `$DIGEST` for that name; image-builder takes the name.
- **Green** (rikuri-drill, `safe-run.sh`): `test_workflows.py` `Ran 26 tests` `OK`.
- **Hand mutants: 3 of 3 red**, baseline passing first: no local name; no digest check; the payload by digest again.
- **Not yet proven:** the job on a real publish (it runs only on `main`, by hand).

## Verify

**Pass 1** (`verifier`, head `ac80d87`): **FAIL.** It confirmed the cause, the credential-free job, red and green, no test loosened, and 3 of 3 mutants; CI's `Full gate (Ubuntu)` passed (run 41709495906). Of its 14 mutants of the changed lines, 4 survived:
- **Important:** `=` to `!=` in the digest check (the test's regex accepted both), and `sudo` dropped from `podman image inspect` (a substring matched), which would read the runner user's store, not root's.
- Nits: `sudo` dropped from `podman tag` (fails closed); `continue-on-error: true` on the check step.
- Nit, not yet proven: the copy into the stick's store changes the layers' representation, so the manifest digest on the stick, and what an installed node reports, is very likely not `$DIGEST`; the content (image ID, config, layers) is the same. The record's and the job summary's "holds `$PUBLISHED@$DIGEST`" claimed more than was shown.

**Repair 1** (of 2):
- the test now asserts both command lines whole, with `sudo`, and refuses `continue-on-error` in the job (a test change after the red commit, stricter only: the earlier asserts let two mutants through);
- the summary line and the Outcome say "the signed image, pulled as …".
- **Not yet proven, for 5b:** what digest the installed node reports (`bootc status`) against `$DIGEST`, and whether a node's later checks need the signed digest itself.
- After repair 1, in rikuri-drill (`safe-run.sh`): 26 tests `OK`; **hand mutants 9 of 9 red**, baseline passing first: the 3 above, the check inverted, `sudo` dropped from the inspect and from the tag, `continue-on-error`, `exit 0`, `{{.ID}}` for `{{.Digest}}`.

**Pass 2** (over repair 1, `77bcd77`): **PASS.** Each of pass 1's four survivors now fails on an assertion; 9 of 9 reproduced; no test loosened; the wording and the Not yet proven items corrected. Minor, backlog: no test pins the summary line's wording.

## Close Out

**DONE** (2026-11-03). `Full gate (Ubuntu)` passed on the PR. The real proof: [publish run 41712055209](https://github.com/rikuripi/rikurinode/actions/runs/41712055209) on `2aafcd7`, all four jobs passed, and the job made `rikuri-node-44.20261103.3.iso`; the owner checked its SHA-256. Repairs 1 of 2, reviews 2 of 2, development CI 2 runs.

Still not yet proven, for 5b: the digest an installed node reports against the signed digest.
