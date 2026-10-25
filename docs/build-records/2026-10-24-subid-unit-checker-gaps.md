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

All test runs were in `rikuri-drill` with `python3 -m unittest discover -s image/tests` (`safe-run.sh` refuses on macOS; the CI gate runs them through it); `tar`'s clock warnings are filtered from the kept output.

- **Red** (`01-red-tests.out`, commit `2b46a25`): 191 tests, 22 failures. Every one is a case the old presence rule passed:
  - 15 unit cases, among them `RemainAfterExit=yes` removed, a later `RemainAfterExit=no`, a second `ExecStart=`, an empty `Before=`, `Conflicts=` or `After=` removed, an extra key or condition, and an override section;
  - 7 override cases.

  Two unit cases already failed the old rule and passed at red (spaces around `=`, a continuation line in `ExecStart`), because the line no longer read as the required one. The first red run also had an error: a failed subtest skipped its cleanup, so the next one found the folder. The cleanup moved into `finally` before the red commit.
- **Fix:**
  - `subid_unit_problems(data)` reads the unit by the 0b rules and names each problem by its line;
  - `check_containers_subid` uses it, and refuses each path in `SUBID_OVERRIDES` that `os.path.lexists`;
  - the shipped unit reads as `[]`.
- **systemd's reading, probed** (`02-systemd-probe.out`): a throwaway unit in `rikuri-drill` (removed after, `LoadState=not-found`):
  - `Description=probe \` followed by `DefaultDependencies=no` gave `Description=probe  DefaultDependencies=no` and `DefaultDependencies=yes`;
  - two `ExecStart=/usr/bin/true` lines gave two commands.

  So a line-by-line reading that ignores continuations would pass a unit that systemd runs after `sysinit.target`.
- **Mutants** (`03-mutants.out`, each kept as its diff):
  - ten mutants of the new rules. Mutants 1 (the duplicate-key rule), 4 (the duplicate-section rule), 5 (the continuation rule) and 9 (`lexists` weakened to `exists`) **survived** the first tests.
  - Four cases were added, after the red commit, to kill them. Reason: each adds a stricter case and loosens none.
    - the same `ExecStart=` twice;
    - a second, empty `[Install]`;
    - the continuation that swallows `DefaultDependencies=no`;
    - a link to a path the checker's machine lacks and a node may have.
  - Then all ten failed (1, 5, 15, 1, 1, 5 errors, 3, 1, 1, 1).
- **Green** (`04-green-tests.out`): 191 tests, OK.
