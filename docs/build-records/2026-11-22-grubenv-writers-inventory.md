# Build Record — experiment: which grubenv writers does the node's image ship and enable? (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `experiment/grubenv-writers`, from `main` at `96b22a4`, a draft PR marked do-not-merge, closed unmerged; this record lands on `main` by a docs-only PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | on the draft PR (#167, closed unmerged): `2ca577a` (contract and source inventory), `09678d6` (experiment); this record on `docs/grubenv-writers-inventory-record` |
| **Status** | DONE |
| **Change type** | experiment (no production change) |

## Intent: the owner's words

- **"Next"** (2026-11-22), after the analysis of grubenv's writers (in the session; recorded below). Its Next: a throwaway CI run on the built image that lists which Fedora grubenv writers it ships and enables, with the inventory recorded here.

## The inventory, from source (2026-11-22, before the run)

Read through GitHub's API, nothing downloaded or run: this repository's `main`; greenboot-rs v0.16.4 (`src/main.rs`, `src/lib/grub.rs`, `src/lib/handler.rs`, `grub2/08_greenboot.cfg`, its units); rhboot/grub2 `fedora-45` (`util/grub-set-bootflag.c`, `docs/grub-boot-success.{service,timer}`, `docs/grub-boot-indeterminate.service`, `util/systemd/systemd-integration.sh.in`); ostree `src/libostree/ostree-sysroot-deploy.c`; bootupd `src/grubconfigs.rs`.

| Writer, and when | Writes | Flushed after? | If a power cut makes GRUB read grubenv as before the write |
|---|---|---|---|
| The node's `edit_grubenv`: clear, arm, give-back | the trigger, `boot_counter` | Yes, the checkpoint call after each write (case 3b) | — |
| greenboot's healthcheck, success, at boot | `boot_success=1`; the counter and the trigger unset | Yes, `rikuri-grubenv-flush.service` after it | — |
| greenboot's healthcheck, failure: sets the counter, then `systemctl reboot` | `boot_success=0`, `boot_counter` | By the clean reboot that follows; a cut within its seconds is not | GRUB does not count that boot: one extra boot before the rollback |
| greenboot's rollback: `bootc rollback`, then the counter and the trigger unset, then a reboot | the counter, the trigger | The deployments' new order, yes (ostree freezes `/boot` when it deploys); greenboot's write after it, by the reboot only | GRUB sees `boot_counter=0` once and boots entry 1, the broken image now, one more time; Linux reads no counter, greenboot sets one and reboots; GRUB then boots the good default. One extra boot of the broken image |
| greenboot's set-rollback-trigger, at shutdown, before ostree's finalize | the trigger | Yes: ostree's freeze of `/boot`, then the node's arm, come after it | — |
| bootupd: `grub2-editenv grubenv create` | creates grubenv only when missing | At install, not at run time | — |
| `grub2-set-bootflag` (grub2-tools), from the user timer `grub-boot-success.timer` | `boot_success`, `menu_show_once` | No: a temporary file, fsync, rename | Menu display only. The timer is `ConditionUser=!@system`; the node has no human user |
| `grub-boot-indeterminate.service` | `boot_indeterminate` | — | Only for offline updates (`system-update-pre.target`), not used on a bootc node |
| `grub2-systemd-integration` | `menu_show_once` | By its reboot | Only on `systemctl reboot --boot-loader-menu`: menu display only |
| `grub2-reboot`, `grub2-set-default`, `grubby` | the default entry | — | Manual tools; nothing in the image runs them |

- **Not yet proven before the run:** which of the Fedora writers the image ships and enables; whether anything else in the image names grubenv; the two "one extra boot" outcomes (from greenboot's code, not seen).

## The question

- Which grubenv writers does the built image ship and enable, at run time: the packages, the programs, the units and whether they are enabled (system and user), the human users, and every program or unit file in the image that names `grubenv` or `grub2-editenv`?

## Design

- An `experiment` method in `image/drill/vm_drill.py`, run by `main` after the first boot in place of the cases, as in the earlier experiments.
- **Read-only:** each command lists or reads (`rpm -q`, `rpm -qf`, `ls -l`, `systemctl is-enabled`, `systemctl --global is-enabled`, `systemctl cat`, `systemctl list-unit-files`, `getent passwd`, `grep -rl`), as root over the drill's SSH, in the CI VM. Nothing writes grubenv or changes a unit.
- Each command's output (its first 6000 characters) goes to the job's log, `vm-drill: exp: <name>`, and to `exp-inventory.txt` in the artifact. The log is enough: the artifact is not downloaded.
- The drill's checks do not run, so the job's verdict is not the result.

## Task Contract

1. **Outcome:** the owner knows which grubenv writers the node's image ships and enables, and the inventory is recorded with that evidence.
2. **Scope:** experiment (a disposable experiment; nothing reaches `main` but this record).
   - On the experiment branch only: `image/drill/vm_drill.py` (the `experiment` method; `main` runs it in place of the cases) and this record.
   - **Not included:** any change to the image, greenboot, or the drill on `main`; a fix, if the run finds a writer that matters (that is a task of its own).
3. **Done when:**
   - one CI run of the image workflow on the draft PR completes the listing, read from the job's log;
   - the result is recorded against the inventory above, ending in a recommendation;
   - the draft PR closed unmerged and its branch deleted (both made by this task);
   - this record on `main` by a docs-only draft PR.
4. **Authority:** the files above. Commit and push the experiment branch; a draft PR titled do-not-merge; close it and delete its branch; a docs-only PR for this record. On the Mac: `ast` parse checks and `git diff --check`. CI runs the VM; nothing runs against the live node. No verifier pass: no code reaches `main`.
5. **Limits:** one task; at most two CI runs (one repair); two review rounds. Budget: about 25 minutes of VM time per run.

## Evidence log

### The run, `09678d6`: the listings read

- The image workflow, [run 45074655917](https://github.com/rikuripi/rikurinode/actions/runs/45074655917), from the drill job's log (`vm-drill: exp: …`); the artifact was not downloaded. The build, the image check and the USB install passed; the drill job failed by design after the listings (its cases did not run), about 3 minutes of VM time.
- `CI`, [run 45074655925](https://github.com/rikuripi/rikurinode/actions/runs/45074655925): `Full gate (Ubuntu)` failed in `test_vm_drill` alone (`FAILED (failures=1, errors=2)`: `test_main_runs_it_after_the_first_boot`, `test_main_reads_the_record_right_after_its_step`, `test_main_renames_last`), because `main` runs the experiment in place of the cases, as on the earlier experiments' branches.

| Listing | Observed in the VM |
|---|---|
| Packages | `grub2-tools`, `grub2-tools-minimal`, `grub2-common` 2.12-81.fc45; `greenboot-0.16.4-0.fc45`; `bootupd-0.3.2-1.fc45`; `bootc-1.16.13-1.fc45`; `ostree-2026.4-1.fc45`; **`grubby` not installed** |
| `grub2-set-bootflag` | present, setuid root, from `grub2-tools-minimal` |
| Other grub2 tools | `grub2-editenv`, `grub2-reboot`, `grub2-set-default`, `grub2-mkconfig`, `grub2-install`, `grub2-switch-to-blscfg` and others, in `/usr/bin` and `/usr/sbin` |
| System units | `bootloader-update.service` enabled; `greenboot-healthcheck.service` enabled; `greenboot-set-rollback-trigger.service` enabled; `rikuri-grubenv-flush.service` listed `disabled` (see below) |
| User units | **none** matching `*grub*`: `grub-boot-success.timer` not found |
| `grub-boot-indeterminate.service` | **not found** |
| `grub2-systemd-integration.service` | **not found**; no `systemd-logind.service.d` drop-in; its script `/usr/libexec/grub2/systemd-integration.sh` is present, with nothing to run it |
| Human users (UID 1000–59999) | **none** |
| grubenv at the end of the first boot | `boot_success=1` |

- **Every file that names `grubenv`, `grub2-editenv` or `grub2-set-bootflag`** under `/usr/bin`, `/usr/sbin`, `/usr/libexec`, `/usr/lib/systemd`, `/usr/lib/kernel`, `/usr/lib/dracut`, `/usr/lib/bootupd` and `/etc`:
  - the grub2 tools above (both paths);
  - `/etc/grub.d/00_header`, `/etc/grub.d/10_linux`: `grub2-mkconfig`'s scripts, which write GRUB's configuration, run by `grub2-mkconfig` only;
  - `/usr/lib/kernel/install.d/20-grub.install`, `95-set-boot-entry.install`, `99-grub-mkconfig.install`: `kernel-install`'s plugins; on this node ostree deploys the kernel, so nothing in the boot or update path runs them (not observed);
  - `/usr/lib/bootupd/grub2-static/grub-static-pre.cfg` (GRUB's own script: it loads grubenv) and `/usr/libexec/bootupd` (the `create` above);
  - `/usr/libexec/greenboot/greenboot`; the node's `greenboot-unapplied-update`, `grubenv-flush` and the flush unit;
  - `/usr/libexec/grub2/systemd-integration.sh` (nothing runs it);
  - **`/usr/libexec/selinux/selinux-autorelabel`: not in the source inventory.**
- **`selinux-autorelabel`:** Fedora's package source could not be read (src.fedoraproject.org refused the automated fetch; not retried around). Two third-party copies of the script (microsoft/azurelinux, OpenMandrivaAssociation/policycoreutils) end the relabel with `grub2-editenv - incr boot_indeterminate`, then `sync` and a reboot. It runs only when a full SELinux relabel was requested (`/.autorelabel`). If so in the image: a menu flag, then a clean reboot. The image's own text: **Not yet proven** (not read in the VM).
- **`rikuri-grubenv-flush.service` listed `disabled`:** `systemctl list-unit-files` reports only links under `/etc`; the unit is pulled in by its link in `/usr/lib/systemd/system/multi-user.target.wants`, and it ran with success at every drilled boot (case 3b's check, for example run 45071509314). The state shown is systemd's, not a fault; noted because an owner reading `systemctl` would see `disabled`.

## Result

- **Observed:** the Fedora writers the source inventory held harmless are absent or idle on the image:
  - `grubby`: not installed;
  - `grub-boot-success.timer`: not shipped as a user unit; and the node has no human user;
  - `grub-boot-indeterminate.service` and `grub2-systemd-integration.service`: not shipped.
  - `grub2-set-bootflag`, `grub2-reboot` and `grub2-set-default` are present, with nothing in the image found to run them.
- **One writer the source inventory missed:** `selinux-autorelabel`, on a full relabel only; by the copies read, a menu flag and then a clean reboot.
- **So:** the writers that matter to a rollback are greenboot's and the node's, as the source inventory found; every other one writes menu flags at most, or is not run.
- **Not yet proven:** the image's own `selinux-autorelabel` text; the two "one extra boot" outcomes; the kernel-install plugins' never running (not observed, from how ostree deploys).

## Outcome

- **No change for rollback safety.** The inventory stands, with `selinux-autorelabel` added.
- **The experiment: drop.** The draft PR closed unmerged and its branch deleted; its commits stay reachable from the closed PR on GitHub.
