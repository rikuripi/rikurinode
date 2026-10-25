# Build Record — The image checker refuses a Quadlet HealthCmd= that needs a shell

| | |
|---|---|
| **Date** | 2026-10-25 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/healthcmd-exec-form`, from `main` at `c002545`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature (the image checker, a control) |

## Task Contract

1. **Outcome:** an image that ships a Quadlet unit whose `HealthCmd=` Podman would run through `/bin/sh -c` fails the image check in seconds. In a shell-less image such a probe can never pass, so its unit never becomes ready, and nothing says why (`2026-10-23-shellless-health-probe.md`, case C).
2. **Scope:**
   - `image/check_image_root.py`: a new check over the Quadlet folders an image can ship: every `HealthCmd=` must be the exec form (0b).
   - Tests in `image/tests/test_check_image_root.py`.
   - Risk tier: **high-risk** (the checker is a control).
   - **Not included:**
     - a check that a `Notify=healthy` unit has a `HealthCmd=` at all;
     - the contents check for service images (no shell in them; ADR 0013);
     - any stage 2 unit (none ships yet, so the shipped image has nothing for the check to find);
     - `/run` (not in an image);
     - the drill.
3. **Done when:**
   - Quadlet's folders and Podman's reading of each form are probed in `rikuri-drill` and kept as evidence;
   - tests committed failing first, then pass;
   - hand mutants of the new rules each turn the suite red, each kept as its diff;
   - the shipped image passes the checker in CI (0 findings) and the CI drill passes;
   - `Full gate (Ubuntu)` passes;
   - one `verifier` pass has no Important finding.
4. **Authority:**
   - the owner's "Ok, next" (2026-10-25), to this task named as the next one ("the backlog check that every `HealthCmd=` is a JSON array");
   - edit the files in Scope;
   - use `rikuri-drill` to run the tests and to probe Quadlet and Podman (create and inspect containers only; nothing run there);
   - push this branch and open the pull request; no merge;
   - CI drill development runs: at most 2;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; time budget 2 hours.

## 0b. Spec

- [x] **Facts, probed in `rikuri-drill`** (Podman 5.8.9, systemd 259; throwaway units in `/etc/containers/systemd`, containers created and inspected, never started, all removed after: "left … 0"):
  - **The folders** (`04-man-page.out`, `podman-systemd.unit(5)` as shipped): rootful units come from `/run/containers/systemd/`, `/etc/containers/systemd/` and `/usr/share/containers/systemd/`. An image can ship the last two.
  - **What Quadlet reads in them** (`01-probe.out`, `02-probe.out`):
    - subfolders (`sub/hcprobe-sub.container`);
    - drop-ins by the unit's name, by each dash prefix (`hcprobe-.container.d`), and by type (`container.d`, read for every container);
    - a linked file and a linked folder (both loaded, from `/var/tmp`).
  - **What Podman records** (`podman inspect … .Config.Healthcheck.Test`), by form:

    | `HealthCmd=` (case) | Quadlet passes | Podman records |
    |---|---|---|
    | `["/standin", "probe"]` (hc01) | as written | `["CMD","/standin","probe"]` |
    | spaces around the array, around `=` (hc05, hc10, hc16, hc17) | trimmed | `CMD` |
    | `/standin probe` (hc14) | as written | `CMD-SHELL` |
    | `["CMD-SHELL", "/standin probe"]` (hc02) | as written | `CMD-SHELL` |
    | `["CMD", "/standin", "probe"]` (hc03) | as written | `CMD` |
    | `[/standin, probe]`, not JSON (hc04) | as written | `CMD-SHELL` |
    | quoted, `"[\"/standin\", …]"` (hc07) | changed escapes | `CMD-SHELL` |
    | `["/standin", "probe"] # trailing` (hc15) | with the comment | `CMD-SHELL` |
    | `none`, `["NONE"]` (hc06, hc13) | as written | `NONE` (no check) |
    | `[]` (hc12) | as written | refused by `podman create` |
    | a continuation line (hc08) | joined to the next | as joined |
    | exec, then a plain string (hc09) | the last one | `CMD-SHELL` |
    | `healthcmd=` (hc11) | the unit is not generated | — |

  - `HealthStartupCmd=` has the same two forms (hs01: a plain string recorded as `CMD-SHELL`).
  - `PodmanArgs=--health-cmd …` reaches Podman as its own option (hs02, hs03), and after an exec-form `HealthCmd=` it wins (hs04: `CMD-SHELL`).
- [x] **The rule, as first written** (superseded in repair 1, below; `check_quadlet_health`), over every file under `etc/containers/systemd` and `usr/share/containers/systemd`, whatever its name or depth:
  - a unit folder that is a link, is reached through one, or is not a folder: a finding;
  - a link or a non-regular file inside: a finding (Quadlet follows links; the checker would not see what one reaches on a node);
  - a line ending in `\`, a comment included: a finding (the checker reads one line at a time);
  - a `HealthCmd=` or `HealthStartupCmd=` line, its key in any case and spaces around `=` allowed: its value must be printable ASCII without tabs, and a JSON array of strings whose first is an absolute path (spaces around it are JSON's own). Each line is checked, so a later one cannot replace a good one unseen;
  - a `PodmanArgs=` line whose value names `health` in any case: a finding (set health with the keys above).
  - Comments (`#`, `;`), blank lines and sections are skipped.
- [x] **Stricter than Podman, on purpose:** `["CMD", …]` and non-ASCII items are exec form to Podman but findings here; `none` and `["NONE"]` need no shell, but a shipped unit has no reason to turn its check off. (As first written this said "one form, which this check and Go's JSON reader read alike". Verifier pass 1 showed that was not so: a one-item array passed here and is `CMD-SHELL` to Podman. Corrected in repair 1.)
- [x] **The rule, repair 1** (2026-10-25, verifier pass 1, I1 to I4; probe `08`):
  - every line of every file in the unit folders is printable ASCII (Quadlet trims bytes such as `0xA0` before `=` as spaces, hr02 and hr03);
  - a `HealthCmd=` or `HealthStartupCmd=` value has no backslash, is printable ASCII, and is a JSON array of **two or more** items (Podman takes the exec form only then, hr01; `pkg/specgenutil/specgen.go`, `len(cmdArr) > 1`, read by the verifier), each item of `[A-Za-z0-9_./:=,+@-]` only, the first an absolute path. So no space or quote that Quadlet escapes, and no `%` or `$` that systemd expands in `ExecStart=` after Quadlet (from the verifier's reading of Quadlet's `escapeString`; not probed);
  - a `PodmanArgs=` value naming `health` in any case, or holding `"`, `'`, `\`, `%` or `$`, is a finding (Quadlet unquotes and unescapes it, hr04 and hr05, and systemd expands the last two);
  - the rest as first written: the folders, links, non-regular files, continuation lines.
- [x] **Rejected:**
  - reading only `*.container` and `*.d/*.conf`: Quadlet's file types change between versions, and a `HealthCmd=` anywhere in its folders costs nothing to refuse;
  - parsing continuations: refusing them is simpler, and our units need none.
- [x] **Not checked here:**
  - an image's own `HEALTHCHECK` (a container without `HealthCmd=` inherits it; part of the service-image contents check, ADR 0013);
  - a `.kube` unit's YAML probes, which Podman turns into shell commands (`curl … || exit 1`, `nc -z`; verifier pass 1, nit 1). No `.kube` unit is planned;
  - a systemd drop-in for the service Quadlet generates (it could replace `ExecStart=` whole). A general override check, not this one's.

## Evidence log

All test runs were in `rikuri-drill` with `python3 -m unittest discover -s image/tests` (`safe-run.sh` refuses on macOS; the CI gate runs them through it); every `tar:` line is filtered from the kept output.

- **Probes** (`01` to `04`, each with its script): as in 0b.
- **Red** (`05-red-tests.out`): 206 tests, `FAILED (failures=1, errors=53)`. Every error is the missing `check_quadlet_health`; the failure is `check_root` not running it. A first try ran 287 tests: the new class inherited the old class's tests and ran them twice; it now takes only `setUp` and `assertFinds`.
- **Fix** (commit `2bfe529`):
  - `check_quadlet_health(root)` walks both unit folders by the 0b rule, and `quadlet_health_problems(data)` reads each file, naming each problem by its line;
  - `check_root` runs it; the module's docstring states the one form.
- **Mutants** (`06-mutants.out`, each kept as its diff): sixteen mutants of the new rules, first on `2bfe529`. Fourteen failed. Two **survived**, and each showed a rule that guards nothing, so the rule went, not a test added (commit `e5c16bb`):
  - Q3, empty items allowed: only an empty item after the first one reaches it, and Podman passes an empty argument without a shell;
  - Q13, the value not trimmed: Python's JSON reader already skips spaces around the array (probe hc05, hc16, hc17 show Podman does too).
  - The other fourteen, run again on `e5c16bb`, all failed: Q1, ASCII not required (1 failure); Q2, the absolute path (5); Q4, an empty array (1 error); Q5, continuations (3); Q6, `PodmanArgs=` (4); Q7, `HealthStartupCmd=` (1); Q8, the key's case (1); Q9, `usr/share/containers/systemd` (4); Q10, a link inside (2); Q11, a link on the way (2); Q12, subfolders (6); Q14, a `#` inside a line taken as a comment (1); Q15, an array not required (1 failure, 1 error); Q16, a unit folder that is a file (1).
- **Green** (`07-green-tests.out`, on `e5c16bb`): 206 tests, OK.

### Verifier pass 1 and repair cycle 1

- **Verifier, pass 1: FAIL**, four Important findings. It read Podman v5.8.9's source and ran the tests and mutants in a copy.
  - **I1:** a one-item array, `HealthCmd=["/standin"]`, passed, and a test said it should; Podman records `CMD-SHELL`. The 0b claims "stricter than Podman" and "read alike" were not supported.
  - **I2:** `%` specifiers and `$` variables inside the array passed; systemd expands them in `ExecStart=` after Quadlet. By reading the source; not probed.
  - **I3:** three ways the line reading differed from Quadlet's: a `0xA0` or `0x85` byte before `=`; C escapes in `PodmanArgs=` (`--\x68ealth-cmd`); quotes inside a word (`--hea""lth-cmd`).
  - **I4:** the non-regular-file rule survived a mutant; no test had a FIFO.
  - **Nits:** a `.kube` unit's probes (now under "Not checked here"); three skip rules that guarded nothing (the comment, section and `\r` handling, removed in the fix); the record's open fields.
  - CI at the time, on `0264166`: the Full gate passed (run 40156195362); the image check found 0; the drill was still running. The repair's push replaces it.
- **Probed** (`08-repair1-probe.out`, throwaway units, removed after: "left … 0"): hr01, a one-item array, is `["CMD-SHELL","/standin"]` and a two-item one `CMD`; hr02 and hr03, `0xA0` before `=`, reach Podman as `--health-cmd`; hr04 and hr05 reach it as `--health-cmd` too.
- **Repair 1:**
  - **Red** (`09-repair1-red.out`, commit `2f16e42`): 209 tests, `FAILED (failures=18)`: 8 forms (the one-item array, for both keys; `%i`, `${X}`, `$X`, a JSON escape, a quote and a space inside an item), 5 hidden `PodmanArgs=` options, 5 lines outside printable ASCII. The FIFO test passed at red: the rule existed and had no test.
  - **A test changed after the red commit of the first round:** `HealthCmd=["/standin"]` moved from the passing forms to the findings. Reason: verifier I1, probe hr01; it is stricter, nothing is loosened.
  - **Fix** (commit `a57f4a3`): the rule of 0b, repair 1. The line's ASCII rule stands on its own, and `_exec_form` also refuses a non-printable value, so the earlier test of a tab inside the array still gets its exec-form finding. `%` and `$` are refused by the item characters, not by a separate test (a separate one would guard nothing). The three dead skip rules are gone.
  - **Green** (`10-repair1-green.out`, on `a57f4a3`): 209 tests, OK.
  - **Mutants** (`11-repair1-mutants.out`, each with its diff), all red: R1, one item allowed (2 failures); R2, any item characters (4); R3, a backslash allowed (1); R4, non-printable values (1); R5, the line's ASCII rule (5); R6, `PodmanArgs=` by `health` only (5); R7, without `%` and `$` (2); R8, without quotes (2); R9, without the backslash (1); R10, the non-regular-file rule (1, verifier I4).
