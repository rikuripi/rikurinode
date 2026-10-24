# Build Record — A greenboot wanted check for Podman's containers range

| | |
|---|---|
| **Date** | 2026-10-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/greenboot-subid-wanted`, from `main` at `6c6038c`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature (the OS image's health check) |

## Task Contract

1. **Outcome:** when `rikuri-containers-subid` does not succeed at boot, greenboot records it as a failed wanted check with the reason and where to look, instead of reporting a healthy node in silence; the boot still counts as good, so no rollback.
2. **Scope:**
   - `image/rootfs/usr/lib/greenboot/check/wanted.d/50-rikuri-containers-subid`, new: Python, `-I`, no shell.
   - `image/check_image_root.py`: require it, executable, in `wanted.d`, and in no `required.d`.
   - Tests in `image/tests/`.
   - `image/drill/vm_drill.py`: the first-boot range check also requires greenboot's "wanted script … success!" line for it.
   - Risk tier: **high-risk** (greenboot decides rollbacks).
   - **Not included:**
     - a required check, or any rollback on this failure (owner, 2026-10-24: a rollback cannot repair `/etc`);
     - Fedora's own `01_update_platforms_check.sh`, which fails on every boot without a route to Fedora (noted for the owner);
     - a repair action or a status page (later stages).
3. **Done when:**
   - the check's tests are committed failing first, then pass;
   - in `rikuri-drill`, an image with the check: (i) a normal boot logs the check's success; (ii) with `/etc/subuid` made unreadable to the unit (a `# comment` line), the boot logs the check failed with its reason, greenboot still passes, `boot_success=1`, and the booted deployment does not change;
   - the CI drill passes, with the new line in its first-boot check;
   - `Full gate (Ubuntu)` passes;
   - one `verifier` pass has no Important finding.
4. **Authority:**
   - the owner's "Ok Next" (2026-10-24), after the wanted-check design was put to them ("Say 'Next' and I'll start it on that basis");
   - edit the files in Scope;
   - use `rikuri-drill` as before;
   - push this branch and open the pull request; no merge;
   - CI drill development runs: at most 2;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 2 hours.

## 0b. Spec

- [x] **How greenboot runs a check** (`01-probe-wanted-python.out`):
  - greenboot 0.16.4 executes a `wanted.d` file by its shebang: the Python probe ran as `/usr/bin/python3`, its parent `greenboot`;
  - a failure logs "wanted script … failed!" and the script's output;
  - the health check still passes, and `boot_success=1` is set.
- [x] **Design:**
  - The check asks systemd for the unit's `ActiveState` and `Result` (`/usr/bin/systemctl show`, fixed arguments, no shell). It passes only on `active` and `success`: the unit is a `RemainAfterExit` oneshot, so `Result=success` alone would also be a unit that never ran (verifier, 2026-10-23).
  - On failure it prints one plain line: what failed, what it breaks, and the journal command.
  - It lives in `/usr/lib` (image-owned, not merged from `/etc`).
- [x] **Alternatives rejected:**
  - a required check (rolls back for a cause no image can fix);
  - reading the files again in the check (duplicates the unit's rules; the unit's own verdict is the single source).

## Evidence log

All test runs below were in `rikuri-drill` with `python3 -m unittest discover -s image/tests` (`safe-run.sh` refuses on macOS; the CI gate runs them through it). From evidence 06 on, `tar`'s "time stamp … in the future" warnings (the VM's clock against the Mac's) are filtered out of the kept output.

- **The check, red** (`02-red-tests.out`, commit `fca3c69`):
  - `test_greenboot_subid_wanted` could not import (the check does not exist);
  - two checker tests errored (three subtest errors) on the missing file or `check_subid_wanted`.
  - A first form of the "must not be disabled" test expected a new finding. It turned out the checker already pins `DISABLED_HEALTHCHECKS` to Fedora's DNS check alone, so the test now asserts that existing finding, and no new code is needed for it.
- **The check, green** (`03-green-tests.out`, commit `91803f1`): 176 tests, OK.
  - `50-rikuri-containers-subid`: `verdict` passes only on both `ActiveState=active` and `Result=success` as whole lines; `main` runs `/usr/bin/systemctl show` with fixed arguments, no shell, and a 30 s timeout. A non-zero exit, an `OSError` or a timeout fails with a plain line.
  - `check_subid_wanted`: the file present, regular, reached without links, and executable; the same name as a regular file in either `required.d` is a finding (a link there too, from repair 1).
- **Built in the VM** (`04-vm-build.out`): the tree of `91803f1` by `git archive`, the check's SHA-256 `ea73ddbd…3d8d` equal on the Mac and inside the image; built offline on the aarch64 base by digest; `check_image_root.py` in the built image: "0 finding(s)".
- **Booted in the VM** (`05-vm-boots.out`): **Pass.**
  - (i) the switch to `gbw`, a trial boot: the unit `active`/`success` ("is present" for both files); greenboot "wanted script …/50-rikuri-containers-subid success!", "health-check passed", `boot_success=1`.
  - (ii) a `# a hand-written note` line added to `/etc/subuid`, then an update `gbw2` (a label on `gbw`) staged, and its **trial** boot: the unit `failed`/`exit-code` ("a line does not read as name:start:count; left as it is"); greenboot "wanted script … failed!" with the check's line "rikuri-containers-subid did not succeed in this boot (ActiveState=failed; Result=exit-code): containers with their own range of user IDs (UserNS=auto) will not start; see journalctl -b -u rikuri-containers-subid"; "health-check passed"; `boot_success=1`; booted `gbw2`, rollback entry `gbw`.
  - (iii) one more reboot: still `gbw2`; the same failure logged; `boot_success=1`.
  - (iv) the line removed by hand and the unit restarted: `active`/`success`; the check exits 0.
- **The drill, red** (`06-drill-red-tests.out`, commit `e47e110`):
  - the new `WantedCheck` test errored (no `wanted_passed`);
  - the three new step subtests failed;
  - `test_it_reads_this_boots_journal` failed. That existing test was changed on purpose: `subid_first_boot` now reads greenboot's journal as well, so the list of reads it pins grows by one.
- **The drill, green** (`07-drill-green-tests.out`, commit `0eca334`): 178 tests, OK.
  - `subid_first_boot` also reads `-b -u greenboot-healthcheck`, keeps it in `01a`, and requires `wanted_passed`, greenboot's exact line for the check.
- **Mutants** (`08-mutants.out`; each applied, checked to differ, then reverted):
  - drill: the requirement dropped: 3 failures; greenboot's journal read without `-b`: 2; the line matched by path alone: **survived**. A test case with the path under "required script" was then added (in `0eca334`, the reason for the test change after red), and the mutant failed: 1.
  - check: `Result=success` alone: 6; a non-zero `systemctl` exit ignored: 3.
  - checker: `required.d` never looked at: 2; the executable bit not checked: 1.
  - The first attempts at the two checker mutants did not apply (shell quoting); they are not counted and were redone by exact replacement.
- **Knowledge layer:** the repository has no help pages or runbooks yet; the repair steps for a node are in this record's conversation with the owner and belong to the status page's later stage.
- **For the owner, not in scope:** Fedora's wanted check `01_update_platforms_check.sh` fails on every boot of a node without a route to Fedora's servers ("There are problems connecting with the following URLs", `05`, every boot), so "wanted script … failed!" lines are not rare on a node. Disabling it would be a change to `greenboot.conf`'s pinned list, an owner choice like D9.

### Verifier pass 1, CI, and repair cycle 1

- **Verifier, pass 1: PASS**, no Important finding. Its nits:
  - **Nit 1, a link named `50-rikuri-containers-subid` in a `required.d` gave no finding.** `_lstat_in` returns None on any link. greenboot follows the link and would run the check as required, the rollback this design avoids. Fixed in repair 1, below.
  - **Nit 2:** "three checker tests errored" was two tests (three subtest errors); corrected above.
  - **Nit 3:** CI requires only the success line; the failure path is proven by `05` alone. Left as it is: a CI case that breaks `/etc/subuid` would cost a drill run per change for a path the unit tests and `05` already hold.
  - **Nit 4:** the record not yet closed (this close-out).
  - The local "179 tests" for `07` corrected to 178, as `07` shows.
- **CI on `9b5b364`:**
  - `Full gate (Ubuntu)` Pass (run 40119174308).
  - The drill Pass (run 40119174384), 7 of 7, with "the containers range at the first boot: added in boot 1 to both files: True; the range once in both: True; greenboot's wanted check passed: True".
- **Repair 1:**
  - **Red** (`09-repair1-red.out`): the new `test_subid_wanted_check_linked_into_required_is_still_required`, 2 subtests failed; 179 tests.
  - **Fix:** `check_subid_wanted` asks `os.path.lexists` for each `required.d` name, so a file, a link, or a link reached through a linked folder all count.
  - **Green** (`10-repair1-green.out`): 179 tests, OK.
