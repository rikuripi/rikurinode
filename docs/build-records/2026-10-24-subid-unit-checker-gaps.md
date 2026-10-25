# Build Record — The image checker reads rikuri-containers-subid.service as a closed world

| | |
|---|---|
| **Date** | 2026-10-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/subid-unit-checker-gaps`, from `main` at `6878ac4`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS (repair 2 pushed) |
| **Change type** | fix (the image checker, a control) |

## Task Contract

1. **Outcome:** an image whose `rikuri-containers-subid.service` would not run the range check once, early, and stay active (so that the greenboot wanted check reads its result) fails the image check in seconds, not after a CI drill or on a node.
2. **Scope:**
   - `image/check_image_root.py`, `check_containers_subid`:
     - the unit is read as a closed world: only its keys, each once, each with its exact value, in its section, in the one line form (the rules below);
     - its own drop-in folders and a mask in `/usr/lib` or `/etc`, and `rikuri-.service.d` prefix drop-ins, are findings.
     - Clarified in repair 1 (2026-10-24, verifier I1): every path systemd reads for the unit in a folder an image can ship (0b, "No override in the image"), and a link on the way to one.
   - Tests in `image/tests/test_check_image_root.py`.
   - Risk tier: **high-risk** (the checker is a control).
   - **Not included:**
     - Fedora's every-service drop-ins (`/usr/lib/systemd/system/service.d/`), which are Fedora's (the same folder under `/etc` and `/usr/local` is refused since repair 1); on 2026-10-24 only `10-timeout-abort.conf` (`TimeoutStopFailureMode=abort`), read in `rikuri-drill`;
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
- [x] **No override in the image** (as first written; superseded in repair 1, below): none may exist, as a file, folder or link (`os.path.lexists`):
  - `usr/lib/systemd/system/rikuri-containers-subid.service.d`;
  - `usr/lib/systemd/system/rikuri-.service.d`;
  - `etc/systemd/system/rikuri-containers-subid.service`, a mask or a copy;
  - `etc/systemd/system/rikuri-containers-subid.service.d`;
  - `etc/systemd/system/rikuri-.service.d`.
- [x] **No override in the image, repair 1** (`SUBID_OVERRIDES`, 23 paths, generated from the unit's name):
  - in each unit folder an image can ship (`etc/systemd/system.control`, `etc/systemd/system`, `etc/systemd/system.attached`, `usr/local/lib/systemd/system`, `usr/lib/systemd/system`; `systemd-analyze unit-paths`, evidence 05; the `/run` ones are not in an image):
    - `rikuri-containers-subid.service.d`, `rikuri-containers-.service.d`, `rikuri-.service.d`;
  - in each of those but `usr/lib/systemd/system`: the unit itself (a copy, or a mask) and `service.d`;
  - nothing may exist at any of them, as a file, folder or link, and no folder on the way to one may be a link (it could lead, on a node, where the checker's machine has nothing).
- [x] **systemd's own view in `rikuri-drill`** (this session, booted `gbp`):
  - `DropInPaths=/usr/lib/systemd/system/service.d/10-timeout-abort.conf` only;
  - `RemainAfterExit=yes`, `Type=oneshot`, `DefaultDependencies=no`;
  - `After=local-fs.target system.slice systemd-journald.socket` (the last two added by systemd itself);
  - `Before=sysinit.target shutdown.target`, `Conflicts=shutdown.target`.

## Evidence log

All test runs were in `rikuri-drill` with `python3 -m unittest discover -s image/tests` (`safe-run.sh` refuses on macOS; the CI gate runs them through it); `tar`'s clock warnings are filtered from the kept output (from 06 on, every `tar:` line; 01 to 04 keep its macOS metadata warnings, verifier nit 4).

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

### Verifier pass 1 and repair cycle 1

- **Verifier, pass 1: FAIL**, one Important finding.
  - **I1:** `SUBID_OVERRIDES` missed `rikuri-containers-.service.d`. systemd reads a drop-in folder for every dash prefix of the name.
  - **Probed** (`05-dropin-prefix-probe.out`): a throwaway `rikuri-probe-unit.service` in `rikuri-drill`, with a drop-in of a distinct name in each folder. systemd 259 read all three (`rikuri-probe-unit.service.d`, `rikuri-probe-.service.d`, `rikuri-.service.d`) and Fedora's `service.d`; removed after (`LoadState=not-found`). The same probe listed the unit folders and showed `/usr/local` is a folder, not a link, in this image.
  - CI at the time: the Full gate (run 40147119744) passed; the OS image run (40147119705) was still running. The repair push replaces it.
- **Repair 1:**
  - **Red** (`06-repair1-red.out`, commit `429acf8`): 194 tests, `FAILED (failures=20)`:
    - the list against every path systemd reads (one test);
    - each path as a finding: 18 of the 23 subtests (the 5 old paths passed);
    - a linked `etc/systemd` (one test).
    - The new empty-`Description=` case (nit 2) passed at red: the rule already required a value.
  - **Fix** (commit `c2b56ab`):
    - `SUBID_OVERRIDES` is generated from the unit's name and `SUBID_UNIT_DIRS` (0b, repair 1);
    - `_override_problem` walks each path: absent is fine, a link on the way is a finding ("reached through a link at …"), and anything at the end is one.
    - In the booted image of `rikuri-drill`: `/etc`, `/etc/systemd`, `/etc/systemd/system`, `/usr/local`, `/usr/local/lib` are folders; the rest of the paths are absent.
  - **Green** (`07-repair1-green.out`): 194 tests, OK.
  - **Mutants** (`08-repair1-mutants.out`, each with its diff), all red:
    - R1, the middle prefix dropped: 6 failures;
    - R2, `usr/local/lib/systemd/system` dropped: 6;
    - R3, the unit itself dropped outside `/usr/lib`: 7;
    - R4, a link on the way ignored: 1;
    - R5, `lexists` weakened to `exists` (a dangling link): 1;
    - R6, `service.d` dropped: 5.
- **Nits:**
  - **Nit 1** (a comment ending in `\`): probed (`09-comment-backslash-probe.out`). systemd 259 does not join a comment with the next line: `DefaultDependencies=no` after `# … \` reads as `no`. So the checker, which skips such a comment, reads it as systemd does.
  - **Nit 2:** an empty `Description=` is now a case, and a finding.
  - **Nit 3:** a link on the way is now a finding (above).
  - **Nit 4:** the wording above. The kept files are not edited.
  - **Nit 5:** `usr/local/lib/systemd/system`, `etc/systemd/system.control`, `etc/systemd/system.attached` and `etc/systemd/system/service.d` are now covered. Still not covered: `/usr/lib/systemd/system/service.d` (Fedora's own, Scope) and `/run` (not in an image).

### Verifier follow-up pass, the owner's decision and repair cycle 2

- **Verifier, follow-up pass: FAIL**, one new Important finding.
  - I1 and nits 1 to 5 are closed. The verifier reproduced the red count (20 failures at `429acf8`) and the green run, and checked the 23 paths against evidence 05.
  - **I2:** two weakened walks in `_override_problem` survived. **M1** (`n < len(parts) - 1`) ignores a link at the unit folder itself; **M7** (`n > 1 and`) ignores a link at the first folder. The one link test linked `etc/systemd`, a middle folder.
  - Backlog nits: `usr/local` becoming a link in a later base image would fail the image check loudly (safe); generators in the image could write overrides into `/run` (outside Scope); the each-path test leaves the parent folders it creates (harmless).
- **The owner's decision** (2026-10-24), asked because a new Important finding in the follow-up round goes to the owner: "Add tests in #43 (Recommended)". The question stated the cost: one more push, a **third CI drill run** beyond this contract's two, and a check of the new lines only.
- **Repair 2** (test only; the checker is unchanged):
  - `test_a_link_at_any_folder_on_the_way_is_a_finding`: a link at `etc`, `etc/systemd`, `etc/systemd/system` and `usr/local/lib/systemd/system`, each a subtest. Reason for a test change after the red commits: it adds cases and loosens none.
  - **Before and after** (`10-repair2-mutants.out`, each mutant with its diff): without the new test, M1 and M7 each gave 194 tests OK (the survival, reproduced); with it, M1 gives 2 failures and M7 1; unmutated, 195 tests OK.
