# Build Record — The image checker reads rikuri-containers-subid.service as a closed world

| | |
|---|---|
| **Date** | 2026-10-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/subid-unit-checker-gaps`, from `main` at `6878ac4`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | fix (the image checker, a control) |

## Task Contract

1. **Outcome:** an image whose `rikuri-containers-subid.service` would not run the range check once, early, and stay active (so that the greenboot wanted check reads its result) fails the image check in seconds, not after a CI drill or on a node.
2. **Scope:**
   - `image/check_image_root.py`, `check_containers_subid`:
     - the unit is read as a closed world: only its keys, each once, each with its exact value, in its section, in the one line form (the rules below);
     - its own drop-in folders and a mask in `/usr/lib` or `/etc`, and `rikuri-.service.d` prefix drop-ins, are findings.
   - Tests in `image/tests/test_check_image_root.py`.
   - Risk tier: **high-risk** (the checker is a control).
   - **Not included:**
     - Fedora's every-service drop-ins (`/usr/lib/systemd/system/service.d/`), which are Fedora's; on 2026-10-24 only `10-timeout-abort.conf` (`TimeoutStopFailureMode=abort`), read in `rikuri-drill`;
     - `/run` (not in an image);
     - any other unit;
     - the drill.
3. **Done when:**
   - tests committed failing first, then pass;
   - hand mutants of the new rules each turn the suite red, each kept as a diff;
   - the shipped image passes the checker in CI (0 findings) and the CI drill passes;
   - `Full gate (Ubuntu)` passes;
   - one `verifier` pass has no Important finding.
4. **Authority:**
   - the owner's "Next" (2026-10-24), after this task was named ("close the image checker's remaining gaps on `rikuri-containers-subid.service` … Say 'Next'");
   - edit the files in Scope;
   - use `rikuri-drill` to run tests and to read systemd's view of the unit;
   - push this branch and open the pull request; no merge;
   - CI drill development runs: at most 2;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 1 hour 30 minutes.

## 0b. Spec

- [x] **Why presence is not enough** (systemd.unit(5), systemd.service(5)):
  - a later assignment of a single-value key replaces an earlier one (`RemainAfterExit=no` after `=yes`);
  - a oneshot may have several `ExecStart=` lines, each run;
  - an empty assignment resets a list (`Before=`).

  The present rule only requires each line to exist, so each of these passes it.
- [x] **The closed world** (each a finding otherwise):
  - each line is empty, a comment starting with `#` or `;` in column 0, `[Unit]`, `[Service]` or `[Install]`, or `KEY=VALUE` with no space around `=`, printable ASCII, not ending in `\` (a continuation);
  - each section appears once;
  - each key belongs to its section and appears once:
    - `[Unit]`: `Description=` (any value), `DefaultDependencies=no`, `After=local-fs.target`, `Before=sysinit.target shutdown.target`, `Conflicts=shutdown.target`;
    - `[Service]`: `Type=oneshot`, `RemainAfterExit=yes`, `ExecStart=/usr/libexec/rikuri/containers-subid`;
    - `[Install]`: `WantedBy=sysinit.target`;
  - every key is present.
- [x] **No override in the image:** none may exist, as a file, folder or link (`os.path.lexists`):
  - `usr/lib/systemd/system/rikuri-containers-subid.service.d`;
  - `usr/lib/systemd/system/rikuri-.service.d`;
  - `etc/systemd/system/rikuri-containers-subid.service`, a mask or a copy;
  - `etc/systemd/system/rikuri-containers-subid.service.d`;
  - `etc/systemd/system/rikuri-.service.d`.
- [x] **systemd's own view in `rikuri-drill`** (this session, booted `gbp`):
  - `DropInPaths=/usr/lib/systemd/system/service.d/10-timeout-abort.conf` only;
  - `RemainAfterExit=yes`, `Type=oneshot`, `DefaultDependencies=no`;
  - `After=local-fs.target system.slice systemd-journald.socket` (the last two added by systemd itself);
  - `Before=sysinit.target shutdown.target`, `Conflicts=shutdown.target`.

## Evidence log
