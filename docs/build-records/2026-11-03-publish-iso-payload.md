# Build Record — publish's USB installer: the signed image by a local name

| | |
|---|---|
| **Date** | 2026-11-03 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/publish-iso-payload`, from `main` at `6c1a55e`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | fix |

## Task Contract

1. **Outcome:** a publish makes the install stick for 5b, holding exactly the signed image.
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
