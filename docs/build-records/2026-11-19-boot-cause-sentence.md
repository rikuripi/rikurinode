# Build Record — why the node restarted: the sentence (D22, task 2 of 3)

| | |
|---|---|
| **Date** | 2026-11-19 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-cause-sentence`, from `main` at `9b4bc2d`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `ea30d54` (contract), `113d082` (change), and this record |
| **Status** | IN PROGRESS |
| **Change type** | feature (OS image: the boot service names this boot's cause; control plane: reads it; setup pages: one sentence) |

## Intent: the owner's words

- "Choice 1: A; Choice 2: A; go" (2026-11-19): task 2 of 3 is "the sentence on the status page and SetupHub"; the control plane only reads the record the root boot service writes (record: `docs/build-records/2026-11-19-boot-cause-record.md`).
- "Next" (2026-11-19), starting this task.
- Asked where the sentence goes, as no status page exists in the interface yet: **"SetupHub + /api/status"**: the sentence on the SetupHub for the signed-in owner, and the same cause and times in `/api/status` for a later status page and alerts; no new page.
- Asked whether to keep the plan's "your funds and data were not affected": **"Leave it out for now"**: the sentence says only what the record shows; the clause returns when a check can prove it.

## What exists

- `rikuri-boot-cause` appends one entry per boot to `/var/lib/rikuri/boot-cause/history.jsonl` (mode 0644, folders 0755): `boot_id`, `at` (this boot), `cause`, `last_alive` (the boot that ended), and evidence.
- The control plane's sandbox (`ProtectSystem=strict`) can read `/var` and `/run`, and cannot write them outside its state folder. `ProcSubset=pid` hides `/proc/sys`, so it cannot read the boot id and cannot tell whether the history's last entry is this boot's.
- No status page in the interface; `/api/status` is JSON (loopback without a session, otherwise signed in). The SetupHub is `/home`, from `GET /api/hub`.

## Design

- **This boot's cause, proven to be this boot's.** After the history is written, the boot service also writes this boot's entry (`boot_id`, `at`, `cause`, `last_alive`) to `/run/rikuri-boot-cause/this-boot.json`. `/run` is a fresh tmpfs at every boot, so the file exists only if the service recorded this boot: no clock and no boot id are compared. A boot whose record failed has no file, and the node says it could not read why it restarted, never the previous boot's cause. The already-recorded branch (a second run in one boot) writes it too.
- **The control plane** reads that file on each request to `/api/hub` and `/api/status` (a path in `Config`, as the hostname file is): at most 4 KiB, a regular file, not followed if a link, exact JSON with a known cause and integer times. Anything else is "couldn't be read" (`null`), logged, and never a guess. The unit and its sandbox do not change.
- **The API:** `restart: { cause, at_unix, last_alive_unix } | null` in the hub report (a ts-rs type) and in the status report.
- **The sentence:** written by the page, from `en.json`, with the times in the browser's own time zone and locale (the node has no time zone setting). One per cause, with or without a `last_alive`; for example a power cut: "Power was lost around 14:02; the node started again at 14:40." No claim about funds or data (the owner's choice).

## Task Contract

1. **Outcome:** the signed-in owner sees on the SetupHub one plain sentence on why the node last restarted and when, and `/api/status` carries the same cause and times.
2. **Scope:** high-risk (the root boot service on the boot path; BUILD-PROCEDURE, "Risk tiers").
   - `image/rootfs/usr/libexec/rikuri/boot-cause` and `image/tests/test_boot_cause.py`: this boot's file in `/run`.
   - `control-plane/crates/rikuri-control/src/restart.rs` (new), `config.rs`, `boot.rs`, `http.rs`, `hub.rs`, `status.rs`, `lib.rs`, the integration tests (`tests/common`, `tests/hub_route.rs`), and the generated TypeScript types in `ui/src/generated/`.
   - `ui/src/lib/api.ts`, `ui/src/secure/Home.svelte`, `ui/src/i18n/en.json`, `ui/tests/owner.spec.ts`.
   - `image/drill/vm_drill.py` and `image/tests/test_vm_drill.py`: after case 3's power cut, `/api/status` on the VM's loopback says `power-cut` with the history's times.
   - `docs/architecture/platform-plan.md` §4.1 and D22's row: a dated clarification (where the sentence is shown; the funds clause left out until proven); `README.md`'s status.
   - **Not included:** a status page; alerts; the rollback rule (task 3); any change to the control plane's unit or sandbox; the history's older entries on a page.
3. **Done when:**
   - The full gate passes in CI: the image tests, the Rust steps (the reader's unit tests, the hub and status routes through the real router, the generated types unchanged), and the setup pages' build and Playwright tests at phone, tablet and desktop widths, with every cause's sentence and the unreadable case.
   - The image workflow's VM drill passes, with the new check: after the power cut, `/api/status` says `power-cut`, dated as the history says.
   - No red commit: a new feature, not a defect fix.
   - One verifier pass with hand mutations (high-risk).
4. **Authority:** the files above and this record. On the Mac: `scripts/cargo.sh fmt` and `clippy`, `ast` parse checks, `git diff --check`; the Python, Rust and UI tests and the drill run in CI only (`safe-run.sh` cannot run on this Mac). Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Change, `113d082`

- `boot-cause`: `write_this_boot` writes `boot_id`, `at`, `cause` and `last_alive` to `THIS_BOOT` after the history, the mark and the heartbeat, and in the already-recorded branch; a failed write is logged and the boot still exits 0. Nothing is written when the boot id or the history cannot be read.
- `restart.rs` (new): `RestartCause` (the boot service's eight causes), `LastRestart`, `parse` (exact keys, a boot id of the kernel's form, whole non-negative times; a clean shutdown and a power cut need `last_alive`, a first boot has none; the two times are never compared) and `read` (lstat a regular file, the same device and inode once open, at most 4 KiB). `now` logs why it could not tell.
- `Config.restart_file` (always `THIS_BOOT`, from no variable), `App`, `boot.rs`; `hub::report` and `status::report` take the restart; `restart` in both replies.
- Setup pages: `lib/restart.ts` (`parseRestart`, the same rules; `sentence`, the times by `toLocaleString`); `parseHub` refuses a hub whose `restart` is missing or not exactly the node's; `Home.svelte`: a "The last restart" card under the steps; `en.json`: fifteen texts.
- The VM drill: `boot_cause_told`, right after case 3: the history's last entry is the power cut, this boot's file says the same, and `/api/status` on the node's loopback (a Python script sent in base64, as greenboot's check asks) carries it with the same times.
- `platform-plan.md` §4.1 and D22's row: the dated clarification; `README.md`: the hub's sentence.
- On the Mac: `scripts/cargo.sh fmt` and `clippy --all-targets -D warnings` clean; the Python files parse; `git diff --check` clean. The tests run in CI.

### Test changes, with their reasons

- `test_boot_cause.py`: the `Node` helper gains `this_boot` and passes it to `boot()`, so no test writes the real `/run`; four new tests.
- `hub.rs` and `status.rs` unit tests: the calls gain the new argument (`None`), and the hub's JSON test expects `"restart":null`: the reply has a new field; each gains a case with a restart.
- `owner.spec.ts`: `HUB` gains a restart (its type requires it). The existing unread-hub cases each gain the node's restart, so that each still fails only for its own reason rather than also for a missing restart; ten new unread cases for the restart.
- `test_vm_drill.py`: `Verdict`'s expected set gains the new check, as each earlier check did.

### CI on `3061277`: Fail (repair 1)

- `Full gate (Ubuntu)`, [run 44665429198](https://github.com/rikuripi/rikurinode/actions/runs/44665429198): `restart::tests::the_file_is_read_as_the_boot_service_writes_it` and `a_link_a_folder_or_a_long_file_is_refused` panicked, `Os { code: 2, kind: NotFound }`: `Scratch::new()` names a folder and does not make it (`StateDir::open` does), and these two tests write into it directly. The UI tests and the Python tests passed.
- `Rust mutants (changed lines)`, [run 44665429444](https://github.com/rikuripi/rikurinode/actions/runs/44665429444): exit 4, the same two tests failing in the baseline, so no mutant ran.
- The VM drill, [run 44665429544](https://github.com/rikuripi/rikurinode/actions/runs/44665429544): every check passed but the new one: `FAIL the owner is told the power cut, with its time: the history's last: {... "cause": "clean" ...}; this boot's file: {... the same ...}; /api/status's restart: null`. Two causes, from the drill's evidence (`04-case3-told.out`: the file, then "(no answer)"):
  1. `vm()` reads ssh's output as text, whose universal newlines turn the reply's CRLF into LF; `parse_http` found the status line but not the blank line before the body, so the body read empty. The stand-in fed CRLF, which `vm()` never returns. The control plane was not shown to fail: its answer was never read.
  2. From `main`, the check ran after case 3's last, clean reboot (`never_applied`), so the last restart was that one, correctly `clean`; this boot's file said so.

## Repair 1

- **Test change, with its reason:** the two `restart.rs` tests make their folder (`fs::create_dir_all`), as every test that writes into a `Scratch` directly must.
- **Red tests, for the drill's defect:** `BootCauseTold`'s stand-in answers as `vm()` does, with LF (and a test for both endings); `test_case3_tells_right_after_the_power_cut` replaces `test_main_tells_right_after_case3`, whose placement was the defect.
- **The fix, its own commit:** the reply is read with either line ending; `boot_cause_told` runs in case 3, right after the power cut's record check and before its clean reboot.

### CI on `3223466` (red): Fail, as expected

- `Full gate (Ubuntu)`, [run 44667205874](https://github.com/rikuripi/rikurinode/actions/runs/44667205874): the Python tests failed on the three new drill tests only: `test_passes` and `test_the_reply_reads_with_either_line_ending` (`newline='\n'`) with `/api/status's restart: null`, and `test_case3_tells_right_after_the_power_cut` (`substring not found`: no `boot_cause_told()` in `case3`). The gate stops there, so its Rust steps did not run.
- `Rust mutants (changed lines)`, [run 44667205753](https://github.com/rikuripi/rikurinode/actions/runs/44667205753): the baseline passed this time (the reader's tests make their folder), and three mutants of `restart::read` were missed, hidden on `3061277` by the failing baseline:
  - `|| !open.is_file()` → `&&`: the clause was redundant (the same device and inode as a regular file, once open, is that file), so no test could tell.
  - `take(MAX + 1)` → `MAX - 1` and `MAX * 1`: the size from the metadata refused every long file first, so the read's own bound was never reached.
- The VM drill, [run 44667205751](https://github.com/rikuripi/rikurinode/actions/runs/44667205751): as on `3061277`, the new check failed (the drill unchanged) and every other check passed.

### Fix, its own commit

- `vm_drill.py`: `status_now` turns the reply's line endings back to CRLF before `parse_http`, so it reads either ending; `boot_cause_told` runs in `case3`, after the power cut's record check and before `never_applied`'s clean reboot; `main` no longer calls it.
- `restart.rs`: `read` drops the redundant `is_file` clause and the size from the metadata; `take(MAX + 1)` and the check after it are the one bound, which also holds for a file that grows once open. The existing tests (the long file, the file of exactly `MAX` bytes, every normal read) now kill all three mutants. No test changed.
