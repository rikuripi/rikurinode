# Build Record — experiment: which grubenv writers does the node's image ship and enable? (D22, N1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `experiment/grubenv-writers`, from `main` at `96b22a4`, a draft PR marked do-not-merge, closed unmerged; this record lands on `main` by a docs-only PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at the end) |
| **Status** | IN PROGRESS |
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
