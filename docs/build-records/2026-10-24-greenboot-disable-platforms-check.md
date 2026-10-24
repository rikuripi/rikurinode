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

- [x] **What the check tests:** `01_update_platforms_check.sh` (Fedora's, in `/usr/lib/greenboot/check/wanted.d`) reads every `http…` URL in `/etc/ostree/remotes.d/*` and fails unless each answers `curl -I` with 2xx or 3xx. The image has one remote, `fedora-iot` (`https://ostree.fedoraproject.org/iot` and its mirrorlist). A node follows a container image through bootc (`rikuri-drill`: `transport: containers-storage`; a registry in production), not that remote, so the check's answer is not the node's update path. Without a route to Fedora it fails (`2026-10-24-greenboot-subid-wanted.md`, evidence 01, one such boot); with a route it passes (`2026-10-21-greenboot-drill-parallels`, `04-booted-good.out`). So it fails on every boot of a node that cannot reach Fedora, which is what a node behind its own firewall or without internet is (verifier nit 2 corrected this citation). What the script tests and the image's one remote were read in `rikuri-drill` (this session), not kept as evidence (verifier nit 3).
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

All test runs were in `rikuri-drill` with `python3 -m unittest discover -s image/tests` (`safe-run.sh` refuses on macOS; the CI gate runs them through it); `tar`'s clock warnings are filtered from the kept output.

- **Red** (`01-red-tests.out`, commit `23c905f`): 182 tests, `FAILED (failures=7, errors=1)`, each from the old single-name pin or the missing drill constant:
  - `test_each_disabled_name_is_pinned`: 3 subtests;
  - `test_disabled_platforms_check_absent_from_image`;
  - `test_fedora_default_conf_keeps_dns_check`;
  - `test_typo_in_disabled_name`;
  - `test_subid_wanted_check_must_not_be_disabled`;
  - `SkippedChecks`: an error, no `PLATFORMS_SKIPPED`.

  The shipped-file and probe tests still passed at red, since the old file matched the old pin.
- **Change** (commit `68e0081`):
  - `greenboot.conf` lists both names, with the reason;
  - `GREENBOOT_EXPECTED` pins both;
  - the drill's first-boot check requires `PLATFORMS_SKIPPED` and reports it, and the docstring says so.
- **Green** (`02-green-tests.out`): 182 tests, OK.
- **Booted in the VM** (`03-vm-boot.out`): **Pass.**
  - The tree of `68e0081`, built offline; `greenboot.conf` has the same SHA-256 (`a68f7d74…0fbb`) in the tree and the image; `check_image_root.py` in the image: "0 finding(s)".
  - After `bootc switch` to it, an update's trial boot. greenboot's check lines, in order:
    - "Skipping disabled script: 01_repository_dns_check.sh";
    - the watchdog check, success;
    - "Skipping disabled script: 01_update_platforms_check.sh";
    - the containers-range check, success;
    - "health-check passed".
  - No "failed!" line; `boot_success=1`; booted `gbp`.

### Verifier pass 1 and repair cycle 1

- **Verifier, pass 1: FAIL**, one Important finding.
  - **I1:** `PLATFORMS_SKIPPED in journal` in `first_boot` had no test; no test called `first_boot`. So dropping it would pass the unit tests, and the CI drill too, since the real journal has the line. `DNS_SKIPPED` had the same gap.
  - CI at the time: the Full gate (run 40142745549) passed; the drill (run 40142745536) was still running. The repair push replaces that drill run.
- **Repair 1:**
  - **Red** (`04-repair1-red.out`, commit `31470f7`): `FirstBootChecks`, 3 tests, 6 errors, all for the missing `first_boot_checks`.
  - **Fix:**
    - `first_boot_checks(journal)` names the four greenboot conditions in the order the check reports them;
    - `first_boot` requires all of them and reports them in the same words as before.
  - **Mutants** (`06-repair1-mutants.out`): the four were run against the fix. Mutant 3 (`first_boot` ignoring the conditions) **survived**, because still no test reached `first_boot`.
    - So `FirstBoot` was added: `first_boot` runs through a stand-in (the boot wait, bootc's status and its three harmless commands answer in the test). It needs every greenboot line, and fails on an unreadable status.
    - Then all four failed: 2 failures and 1 error; 2; 4; 2.
    - Reason for this test after the repair's red commit: it adds a test, loosens none, and kills that survivor.
  - **Green** (`05-repair1-green.out`): 188 tests, OK.
- **Nits:**
  - **Nit 1** (the red count "8 failures" against `FAILED (failures=7, errors=1)`): corrected above.
  - **Nits 2 and 3:** the 0b citation, corrected above.
  - **Nit 4:** `greenboot.conf`'s "a node never updates from" is the design (bootc following the node's image), observed in the drill only; the production registry path does not exist yet, and the `fedora-iot` remote stays in the image. The comment is left as it is: changing it would change the image file behind evidence 03, for wording only.
  - **Nit 5**, backlog: `test_every_probe_case_but_the_shipped_file_is_a_finding` asserts some finding, not a format one. The verifier re-derived each case's findings by hand (format, except case 02 by design). This predates the change.
