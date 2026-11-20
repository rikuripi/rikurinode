# Build Record — why the node restarted: the record (D22, task 1 of 3)

| | |
|---|---|
| **Date** | 2026-11-19 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-cause-record`, from `main` at `a162f46`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `203d6df` (contract), `e5fe093` (change), and this record |
| **Status** | IN PROGRESS |
| **Change type** | feature (OS image: a root boot service; control plane: a heartbeat; the VM drill) |

## Intent: the owner's words

- "Next" (2026-11-19), answering the proposed task: "the boot-cause record, the first stage 1 build task left: the heartbeat, the cause worked out at each boot, and one sentence to you about it."
- "Choice 1: A; Choice 2: A; go" (2026-11-19), choosing:
  - **Choice 1, A: three tasks, in this order.** 1. **The record**: the control plane writes a heartbeat every minute; a boot service works out one cause per boot and saves it on the node; the VM drill checks the cause after a clean shutdown, a power cut, an update applied and an update never applied. 2. **The sentence** on the status page and SetupHub. 3. **The rollback rule**: greenboot told which boots not to count. Alerts wait until a way to send them exists.
  - **Choice 2, A: a small root boot service** reads the evidence and writes the cause to `/var/lib/rikuri`; the control plane only reads that record, so its sandbox stays as tight as it is. The plan's wording ("the control plane … records one cause") gets a dated clarification.

## What exists, and what the plan asks

- Plan §4.1, "Why the node restarted" (D22): a heartbeat to `/var` every minute; at each boot one cause from the evidence (clean shutdown, a shutdown the UPS ordered, a power cut dated by the last heartbeat, a kernel crash from pstore, a hardware-watchdog reset, an update applied or rolled back); evidence that fits none is unknown.
- Built: `greenboot-unapplied-update` (2026-10-22), which clears greenboot's trigger for an update never applied and appends to `/var/lib/rikuri/update-not-applied`.
- Not built: any heartbeat, any reader of that evidence, any shutdown reason (the control plane orders no shutdown yet), any alert.
- The control plane's unit is network-facing and tightly sandboxed (`ProtectKernelLogs`, `ProcSubset=pid`, one capability); Choice 2 keeps it so.

## Design

- **The heartbeat (control plane).** At start and every 60 s, the control plane writes the Unix time to `heartbeat` in its state folder (`/var/lib/rikuri/control-plane`), whole, by its existing synced write-and-rename. A failed write is logged and the daemon carries on.
- **The boot service (root), `rikuri-boot-cause.service`, running `/usr/libexec/rikuri/boot-cause`.**
  - **At boot** (before `sysinit.target`, so before the control plane's first heartbeat of this boot), it records one cause for the boot that ended, appended as one JSON line to `/var/lib/rikuri/boot-cause/history.jsonl` (the last 100 boots), then removes the shutdown mark.
  - **At the end of every clean shutdown** (its `ExecStop`, ordered after ostree's finalize, so after any update is applied, and before `/var` is unmounted), it writes the shutdown mark, `/var/lib/rikuri/boot-cause/shutdown`, naming the boot id. The plan said a clean shutdown is shown by the persistent journal; the mark replaces that, because journald hands `/var` back before the shutdown ends, and a power cut while an update is applied must not read as clean.
  - **The causes, in order of precedence:** `kernel-crash` (a pstore record not seen before); `watchdog` (a watchdog's boot status with the card-reset bit); `rolled-back` or `update-applied` (the booted ostree deployment differs from the last boot's: an image booted before it, or a new one); `clean` (the mark names the last boot); `power-cut` (no mark, and a heartbeat from the last boot, which dates it); `unknown` (anything else, including a missing record of the last boot); `first-boot` (no record and no trace of an earlier boot).
  - **Inputs:** the boot id; the history; the mark; the heartbeat; pstore (`/sys/fs/pstore`, `/var/lib/systemd/pstore`); watchdog boot status (`/sys/class/watchdog/*/bootstatus`); the booted deployment, from `/proc/cmdline`'s `ostree=` link under `/sysroot` (no command, no D-Bus: it runs before either is up).
  - **The heartbeat is untrusted input to root:** written by the network-facing control plane's user. It is opened without following a link, must be a regular file of at most 32 bytes, and must read as decimal digits; anything else is ignored and noted. No other input comes from a user or the network.
  - **It never fails the unit:** every error is logged and noted in the entry, and the boot step exits 0, because a failed oneshot never runs its `ExecStop`, and the next boot would then read a clean shutdown as a power cut.
- **The image check** (`check_image_root.py`) holds the unit as a closed world (like `rikuri-containers-subid.service`), the script present and executable, the unit enabled, and nothing overriding it.

## Task Contract

1. **Outcome:** after every boot the node keeps one recorded cause for the boot that ended (a clean shutdown, a power cut with its time, an update applied or rolled back, a crash, a watchdog reset, or unknown), for the next two tasks to show and to use.
2. **Scope:** high-risk (a root service on the boot and shutdown path; BUILD-PROCEDURE, "Risk tiers").
   - `image/rootfs/usr/libexec/rikuri/boot-cause` (new), `image/rootfs/usr/lib/systemd/system/rikuri-boot-cause.service` (new) and its `sysinit.target.wants` link.
   - `image/check_image_root.py` and `image/tests/test_check_image_root.py`: the new unit, script and link, closed-world.
   - `image/tests/test_boot_cause.py` (new): the classifier, the readers, the writes.
   - `control-plane/crates/rikuri-control/src/heartbeat.rs` (new), `lib.rs`, and `control-plane/apps/rikuri-control-plane/src/main.rs`: the heartbeat, with its unit tests.
   - `image/drill/vm_drill.py` and `image/tests/test_vm_drill.py`: the drill reads the record after the first boot (`first-boot`), after case 1 (`update-applied`, then `rolled-back`), after case 2b's shutdown (`clean`: the update was not applied, the shutdown was clean) and after case 3 (`power-cut`, dated between the last heartbeat before the shutdown and the cut); and checks the unit is active and the heartbeat fresh.
   - `docs/architecture/platform-plan.md` §4.1 and D22's row: a dated clarification (2026-11-19): the root boot service works out the cause, the control plane writes the heartbeat and only reads the record, and a clean shutdown is shown by the shutdown mark.
   - **Not included:** the sentence to the owner (task 2); the rollback rule and greenboot (task 3); alerts; a shutdown reason written by the control plane or a UPS (nothing orders a shutdown yet); enabling the hardware watchdog; reading the record from the control plane.
3. **Done when:**
   - The image workflow's VM drill passes with the five boot-cause checks above, on this branch's image.
   - The full gate passes in CI: the image tests (`test_boot_cause`, `test_check_image_root`, `test_vm_drill`), the Rust steps (fmt, clippy, `cargo test` with the heartbeat's tests); the OS image builds and its check passes. The Rust mutants run reports no surviving mutant in `heartbeat.rs`.
   - **Not yet proven, by design:** a kernel crash and a watchdog reset are unit-tested only; the CI VM has no pstore backend or hardware watchdog. They are proven on the N150 (stage 1's drill).
   - No red commit: a new feature, not a defect fix.
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** the files above and this record. On the Mac: `python3 -I -m py_compile`, `git diff --check`; the Python and Rust tests and the drill run in CI only (`safe-run.sh` cannot run on this Mac). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Change, `e5fe093`

- `image/rootfs/usr/libexec/rikuri/boot-cause` (new, 0755): the boot and shutdown steps; `classify` is one pure function over the evidence; the heartbeat read with `O_NOFOLLOW`, as a regular file of at most 32 bytes of decimal digits; every write whole (synced file, rename, synced folder), 0644; the boot step exits 0 on any error.
- `image/rootfs/usr/lib/systemd/system/rikuri-boot-cause.service` (new) and its `sysinit.target.wants` link: `DefaultDependencies=no`, `RequiresMountsFor=/var/lib/rikuri`, `After=local-fs.target systemd-pstore.service`, `Before=sysinit.target final.target ostree-finalize-staged.service`, `Conflicts=final.target`; oneshot, `RemainAfterExit=yes`, the boot step as `ExecStart`, the mark as `ExecStop`. The stop order follows ostree's own finalize unit: ordered before it, this unit stops after finalize's `ExecStop` has applied (or failed to apply) the update, and before `/var` is unmounted.
- `image/check_image_root.py`: `BOOT_CAUSE_KEYS`, a closed world read by the existing `unit_problems`; the script present and executable; the link; every override path (`unit_overrides`). `image/tests/test_check_image_root.py`: the fixture root ships the three files; `BootCause` covers each finding.
- `image/tests/test_boot_cause.py` (new): the readers (the heartbeat's link, FIFO, length and form; the mark; the history), pstore, the watchdog bit, the booted deployment from a fake `/sysroot`, the decision table and its precedence, whole boots and shutdowns in a temporary tree (first boot, clean, power cut, update applied, run twice in one boot, no boot id, the last 100 kept, file modes), and `main`.
- `control-plane/crates/rikuri-control/src/heartbeat.rs` (new): `beat` and `keep`, with six tests; `main.rs` spawns `keep` beside the address follower, stopped by the same signal.
- `image/drill/vm_drill.py`: four new checks, in `EXPECTED`: "the boot cause at the first boot", "… after an update and its rollback", "… after a clean shutdown, the update not applied", "… after a power cut, with its time"; their helpers tested in `image/tests/test_vm_drill.py`, whose `Verdict` set gains the four names (a test change, with its reason: the drill gains these checks).
- `docs/architecture/platform-plan.md`: the status paragraph, §4.1's "Why the node restarted" and D22's row, each with the dated clarification of 2026-11-19; earlier text unchanged.
- **On the Mac:** every Python file parses (`python3 -I`, `ast`); `scripts/cargo.sh fmt --check` clean after `fmt`; `scripts/cargo.sh clippy --workspace --all-targets --locked --offline -- -D warnings` clean; `git diff --check` clean. No test ran here: the Python and Rust tests and the drill run in CI.
