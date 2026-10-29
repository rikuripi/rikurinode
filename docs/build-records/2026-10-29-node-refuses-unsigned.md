# Build Record — Stage 1 change 2c: a node refuses an unsigned update, in the VM drill

| | |
|---|---|
| **Date** | 2026-10-29 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/node-refuses-unsigned`, from `main` at `463e28e`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
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

## Verify

## Close Out
