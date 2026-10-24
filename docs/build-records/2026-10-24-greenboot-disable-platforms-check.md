# Build Record — Disable Fedora's update-platforms check in greenboot

| | |
|---|---|
| **Date** | 2026-10-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/greenboot-disable-platforms-check`, from `main` at `0223018`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | ops (the OS image's health check configuration) |

## Task Contract

1. **Outcome:** a node's boot log no longer reports a failed wanted check on every boot for Fedora's update servers, so a real "wanted script … failed!" (the containers-range check) stands out.
2. **Scope:**
   - `image/rootfs/etc/greenboot/greenboot.conf`: add `01_update_platforms_check.sh` to `DISABLED_HEALTHCHECKS`, with its reason.
   - `image/check_image_root.py`: the pinned list becomes the two names.
   - `image/tests/test_check_image_root.py`: tests follow the new pinned list.
   - `image/drill/vm_drill.py`: the first-boot check also requires greenboot's "Skipping disabled script: 01_update_platforms_check.sh".
   - Risk tier: **high-risk** (greenboot's configuration decides rollbacks).
   - **Not included:**
     - any other check;
     - Fedora's ostree remote `fedora-iot` itself, which the node does not update from;
     - the status page.
3. **Done when:**
   - the changed tests are committed failing first, then pass;
   - in `rikuri-drill`, a boot of an image with the change logs "Skipping disabled script: 01_update_platforms_check.sh" and no "wanted script … 01_update_platforms_check.sh failed!", while the containers-range check still runs and passes;
   - the CI drill passes 7 of 7 with the new line in its first-boot check;
   - `Full gate (Ubuntu)` passes;
   - one `verifier` pass has no Important finding.
4. **Authority:**
   - the owner's choice "Disable it (Recommended)" (2026-10-24), to a question that put the cost and reversal in plain words;
   - edit the files in Scope;
   - use `rikuri-drill` as before;
   - push this branch and open the pull request; no merge;
   - CI drill development runs: at most 2;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 1 hour 30 minutes.

## 0b. Spec

- [x] **What the check tests:** `01_update_platforms_check.sh` (Fedora's, in `/usr/lib/greenboot/check/wanted.d`) reads every `http…` URL in `/etc/ostree/remotes.d/*` and fails unless each answers `curl -I` with 2xx or 3xx. The image has one remote, `fedora-iot` (`https://ostree.fedoraproject.org/iot` and its mirrorlist). A node follows a container image through bootc (`rikuri-drill`: `transport: containers-storage`; a registry in production), not that remote, so the check's answer is not the node's update path. On a node without a route to Fedora, it fails every boot (`2026-10-24-greenboot-subid-wanted.md`, evidence 01 and 05).
- [x] **Design:**
  - the same mechanism as the DNS check (D9): the name in `DISABLED_HEALTHCHECKS`;
  - the checker's pinned list holds both names, so neither can be dropped or added unnoticed;
  - the drill proves greenboot read it.
  - Reversible: remove the name from the list.
- [x] **Test changes and their reason:** the pinned value is the owner's decision, so the tests that name the expected list follow it:
  - the constant `D`, the expected line;
  - the probe cases 11 and 13, which write the list literally;
  - the messages "expected [...]";
  - the test of the wanted check's disabling.

  The probe cases keep their byte layouts (comments, whitespace, control bytes); only the names inside the parentheses change. The probes recorded how greenboot's INI reader handles those layouts; by reading, its handling does not depend on the names inside the value, but that is not re-probed. Keeping the old single-name `D` would make every probe case a finding for its value alone, and stop them testing the format, so they move with the expected value.

## Evidence log
