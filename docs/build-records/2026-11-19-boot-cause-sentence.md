# Build Record — why the node restarted: the sentence (D22, task 2 of 3)

| | |
|---|---|
| **Date** | 2026-11-19 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/boot-cause-sentence`, from `main` at `9b4bc2d`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | this contract, then the change |
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
