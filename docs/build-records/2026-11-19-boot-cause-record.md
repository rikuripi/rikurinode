# Build Record — why the node restarted: the record (D22, task 1 of 3)

| | |
|---|---|
| **Date** | 2026-11-19 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-cause-record`, from `main` at `a162f46`, merged as `8b05fa0` (#135); repair 2 on `stage1/boot-cause-repair`, from `main` at `8b05fa0`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `203d6df` (contract), `e5fe093` (change), `b683dec` (record), `d6bc5ad` (repair 1), and this record |
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
   - The image workflow's VM drill passes with the four boot-cause checks above (corrected from "five" in repair 2: the unit and the heartbeat are part of the first), on this branch's image.
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

### CI on `b683dec`: Fail (repair 1)

- `Full gate (Ubuntu)`, [run 44645184378](https://github.com/rikuripi/rikurinode/actions/runs/44645184378): step 3 failed, `FAILED (failures=9)`, all in `test_vm_drill`: `FirstBoot` (3 tests, 6 failures with its subtests) with `AssertionError: unexpected VM command: 'cat /var/lib/rikuri/boot-cause/history.jsonl'`, and `Case1Steps` (3 tests) with `AssertionError: cat /var/lib/rikuri/boot-cause/history.jsonl`. The existing stand-ins of `first_boot` and `case1` answer only their own commands, and `Case1Steps` expects one result.
- The rest of that run, on the same image: the VM drill, [run 44645184401](https://github.com/rikuripi/rikurinode/actions/runs/44645184401), **passed**, the four boot-cause checks included; the image build and check, and the USB install, passed; the Rust mutants run, [run 44645184281](https://github.com/rikuripi/rikurinode/actions/runs/44645184281), passed.

### Repair 1, `d6bc5ad`

- `image/drill/vm_drill.py`: the first-boot and case 1 boot-cause checks move out of `first_boot()` and `case1()` into `main()`, right after each (`boot_cause_first_boot()`, and `boot_cause_case1(before)` with `before` read before `case1()`). Neither step reboots after the boot it waited for, so each check reads the same record as before. Cases 2b and 3 keep theirs inline: they must read before `never_applied` reboots.
- `image/tests/test_vm_drill.py`: two tests added (`BootCauseCase1`: the boots since the update, and the order of the calls in `main()`). No existing test changed.

### CI on `d75a425`: Pass

- `Full gate (Ubuntu)`, [run 44647260197](https://github.com/rikuripi/rikurinode/actions/runs/44647260197): the image tests `Ran 609 tests … OK`; Rust `189 passed; 0 failed`.
- The image workflow, [run 44647260762](https://github.com/rikuripi/rikurinode/actions/runs/44647260762), the VM drill on the real image:
  - `PASS the boot cause at the first boot: recorded: ['first-boot']; the unit active: True; the heartbeat fresh: True ('1795135329' at 1795135339)`
  - `PASS the boot cause after an update and its rollback: recorded since the update was staged: ['update-applied', 'clean', 'clean', 'clean', 'rolled-back']`
  - `PASS the boot cause after a clean shutdown, the update not applied: recorded for the shutdown whose finalize failed: ['clean']`
  - `PASS the boot cause after a power cut, with its time: recorded: ['power-cut']; last alive 1795135608, the reboot asked for at 1795135620`
- Rust mutants, [run 44647260514](https://github.com/rikuripi/rikurinode/actions/runs/44647260514): `Found 2 mutants to test`, `2 mutants tested in 69s: 2 caught` (the bodies of `beat` and `keep`).
- The owner merged #135 at `d75a425` (as `8b05fa0`, the same tree) before the verifier ran.

### The verifier, round 1, at `d75a425`: FAIL

- **I-1, Important:** in `boot()`, the branch for a history it cannot read (a folder, or over 4 MiB) returns 0, and no test reaches it; mutated to return 1 (in a scratch copy), `boot()` returned 1, and the unit would fail, so its next `ExecStop` (the mark) would not run. A surviving mutant in a recovery path.
- **I-2, Important:** `classify` took a heartbeat as the last boot's when it was at least the last boot's record time, a wall-clock comparison. A clock behind at boot (a Pi 5 without an RTC battery, a dead CMOS battery) lets an older boot's heartbeat pass: boot N cut before the control plane's first beat, then boot N+1 records `power-cut` dated by boot N-1. Verbatim: `classify([e(A,1_790_000_000), e(B,1_700_000_000)], None, 1_790_050_000, [], [], img)` gives `('power-cut', 1790050000)`. The record claimed "a heartbeat from the last boot" without a check that proves it.
- **Nits, for the backlog unless repair 2 takes them:**
  1. §4.1 and the status paragraph of the plan were edited in place with "(clarified 2026-11-19)" inline; the change log above said "earlier text unchanged", which holds only for D22's row. **Corrected here:** D22's row keeps its earlier text and appends the clarification; §4.1 and the status paragraph were reworded in place, each marked with the date.
  2. Surviving low-value mutants: `booted_deployment`'s `startswith` check (the regex refuses the same input); in `keep`, `biased;` and `set_missed_tick_behavior`. cargo-mutants made only 2 mutants for `heartbeat.rs`.
  3. The heartbeat has no upper bound: the control plane's user can turn `unknown` into a dated `power-cut`, nothing more. `StateDir::write` syncs the file, not the folder, so after a cut the heartbeat may be one beat older.
  4. A boot back into an image that ran earlier, by hand, is recorded `rolled-back`; a history over 4 MiB stops the record until repaired (only logged).
  5. "Done when" says five drill checks; there are four (the unit and the heartbeat are part of the first). **Corrected here.**

## Repair 2 (the verifier's I-1 and I-2)

- **The fix, for I-2:** each boot removes the heartbeat it read, as it removes the shutdown mark, so a heartbeat found at boot was written by the boot that ended, whatever the clock says. Each entry keeps the value it read (`heartbeat_seen`), so a heartbeat whose removal failed is never used twice. The wall-clock comparison goes. The removal unlinks the name only: a link the control plane's user planted is removed, never followed.
- **For I-1:** a test for the unreadable history (a folder, too long): `boot()` returns 0 and leaves the file. It passes on the current code; the gap was a missing test, not wrong behaviour, so it has no red.
- **Test change, with its reason:** `Classify.test_no_heartbeat_from_the_last_boot_is_unknown` loses its second half (a heartbeat of 99 under a record of 100 was "unknown"); `test_a_heartbeat_counts_whatever_the_clock_says` replaces it, expecting `power-cut` at 99: with the heartbeat removed at each boot, its presence, not its value, ties it to the last boot, and a clock corrected back during that boot must not lose the date. `History.test_lines_that_do_not_read_are_counted_and_skipped` gains three lines (`heartbeat_seen` as a string, a bool, an int).
- **Red tests first**, committed alone, to be seen failing in CI; the fix in its own commit.

### Red, `6f2eb3a`: Fail, as expected

- `Full gate (Ubuntu)`, [run 44650101501](https://github.com/rikuripi/rikurinode/actions/runs/44650101501): `FAILED (failures=6)`, exactly the six new or changed tests: `Classify.test_a_heartbeat_counts_whatever_the_clock_says`, `Classify.test_a_heartbeat_seen_at_the_last_boot_is_stale`, `History.test_lines_that_do_not_read_are_counted_and_skipped`, `BootAndShutdown.test_the_heartbeat_is_read_once_and_removed`, `BootAndShutdown.test_a_clock_behind_at_boot_does_not_reuse_an_old_heartbeat`, `BootAndShutdown.test_a_heartbeat_link_is_removed_not_followed`. `test_an_unreadable_history_records_nothing_and_never_fails` (I-1) passed, as the record expected.

### Fix, `75784d3`

- `boot-cause`: `classify` takes a heartbeat as the last boot's unless it equals the last entry's `heartbeat_seen`; the wall-clock comparison and its message are gone. `boot()` records `heartbeat_seen` and, after the history and the mark, unlinks the heartbeat (`remove_heartbeat`: a missing file is fine; any other error is logged, and `heartbeat_seen` keeps the next boot from reusing it). `parse_entry` refuses a `heartbeat_seen` that is not an integer. The docstring says so. No test changed in this commit.
