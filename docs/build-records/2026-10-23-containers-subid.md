# Build Record — Stage 1: every node keeps a `containers` range in `/etc/subuid` and `/etc/subgid`

| | |
|---|---|
| **Date** | 2026-10-23 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/containers-subid`, from `main` at `860c9f5`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature (stage 1, the image; a prerequisite stage 2 named) |

## Task Contract

1. **Outcome:** on every node, fresh or updated, Podman can give each container its own range of user IDs (`UserNS=auto`, the hardening stage 2's units use), instead of refusing to start it, as it did on our image in `docs/build-records/2026-10-23-shellless-health-probe.md` (finding 1).
2. **Scope:** `image/rootfs/usr/libexec/rikuri/containers-subid` (new; Python, standard library), its unit `image/rootfs/usr/lib/systemd/system/rikuri-containers-subid.service` and the link enabling it under `sysinit.target.wants`; `image/check_image_root.py` asserts all three; tests in `image/tests/`; the CI drill's first boot (`image/drill/vm_drill.py`) also checks the range and starts one `--userns=auto` container; this record. Risk tier: **high-risk** (a root service writing `/etc` at every boot; the drill is a control). **Not included:** any stage 2 unit; a greenboot check for the range (backlog if wanted); `deny.toml`, the gate, other workflows.
3. **Done when:**
   - the script's and the checker's tests are committed failing first (red), then pass;
   - the CI drill on `bootc install`'s layout (a fresh install, `/etc/subuid` empty) passes its first boot with the range present and a `--userns=auto` container started, and cases 1, 2b and 3 still pass;
   - in `rikuri-drill` (Anaconda's layout, an installed node whose `/etc/subuid` was changed at install, holding the `drill` user's range), after `bootc switch` to an image of this branch, the range is added beside the existing entry, the next boot leaves the files unchanged, and a `UserNS=auto` container starts;
   - `Full gate (Ubuntu)` and the OS image build pass on the pull request; one `verifier` pass has no Important finding.
4. **Authority:** the owner's "Ok" (2026-10-23) to adding the range to the image, and the choice "Boot-time check (Recommended)" over shipping `/etc` files; edit the files in Scope; use `rikuri-drill` as before (the owner's decisions of 2026-10-21; its host key checked against the fingerprint the owner saw); push this branch (CI runs the drill on the pull request); open the pull request; no merge. Development runs of the drill: at most 3. Independent check required.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 4 hours.

## 0. Intent

- [x] **Problem, in the owner's words:** "Ok" (2026-10-23), to "add the `containers` range to the image, with a check and a test"; then "Boot-time check (Recommended)".
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** every node's `/etc/subuid` and `/etc/subgid`; every future container unit with `UserNS=auto`.
- [x] **Open questions:** none blocking.
- [x] **Owner approved the intent:** the messages above.

## 0b. Spec

- [x] **Facts (2026-10-23):**
  - `podman-run(1)`, `--userns=auto`: rootful Podman needs "the user name containers be specified in the /etc/subuid and /etc/subgid files" with "an unused range of subordinate user IDs"; its example is `containers:2147483647:2147483648`.
  - In `rikuri-drill`: `ostree admin config-diff` lists `subuid` and `subgid` as modified (`M`): creating the install's user appended its range (`drill:524288:65536`). The image's `/usr/etc/subuid` is empty. bootc's three-way merge keeps a locally modified `/etc` file, so a range shipped as an `/etc` file would reach a fresh install but **never** an installed node's update, silently (the owner's choice above).
  - `login.defs`: `useradd` allocates from 524288 to 600100000, below 2147483647, so the ranges do not meet.
  - Both files are `system_u:object_r:etc_t:s0`, root, 0644; `matchpathcon` gives a new file in `/etc` the same label.
- [x] **Design:**
  - `containers-subid`, run by `rikuri-containers-subid.service` (`Type=oneshot`, `DefaultDependencies=no`, after `local-fs.target`, before `sysinit.target`, so before every ordinary service, every container unit included), enabled by a link in `/usr/lib/systemd/system/sysinit.target.wants/`.
  - For each of `/etc/subuid` and `/etc/subgid`: a file that cannot be read, or a line that is not `name:start:count` (blank lines allowed), is left alone and logged, and the unit fails. A `containers` entry already present is left as it is (exactly the range: nothing to do; another range: logged, someone chose it). Otherwise, if the range overlaps any entry, nothing is written, logged, and the unit fails. Otherwise the line is added by writing the whole file anew beside it (`O_EXCL`, 0644, fsync) and renaming it over the old one, so a power cut leaves the old file or the new, never half a line.
  - Rejected: shipping `/etc/subuid` (above); a `containers` system user and `usermod --add-subuids` (an account nobody logs into, for a line); explicit `UIDMap=` per unit (a stage 2 decision against the plan's `UserNS=auto`).
- [x] **Policy applied:** nothing fails silently (every decision is logged; a refusal fails the unit, seen in `systemctl --failed` and the journal); no shell, no command run at all; no network.
- [x] **Flagged concerns:** a failed unit does not stop the boot or roll the image back; containers that need the range fail to start, visibly. A greenboot check is backlog.

## 1. Plan

- [x] **One sentence:** a boot-time oneshot adds Podman's `containers` range to `/etc/subuid` and `/etc/subgid` when it is missing, and the drill proves a `UserNS=auto` container starts.
- [x] **Blast radius:** two files in `/etc` on every node, written only when the line is missing; nothing irreversible (the line can be removed).
- [x] **Current behaviour characterized:** the experiment's `04a-case-a-userns-auto-refused.out` ("no subuid ranges found for user \"containers\"").
- [x] **Files and order:** this record; the tests (red); the script, unit, link and checker; the drill's step; tests in `rikuri-drill` and the run there; CI; the verifier; the pull request.
- [x] **Risks:** a malformed write locking every container out (hence the whole-file rename and the refusal to touch a file it cannot parse); the unit ordered too late (hence before `sysinit.target`); the link lost by `COPY` (hence the checker).
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] Red: the tests, committed failing first (run in `rikuri-drill`, Python 3.14 of the image: `test_containers_subid` cannot load, the checker's five new tests error, the other 119 pass).

## Evidence log
