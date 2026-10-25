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
- [x] **The rule** (`check_quadlet_health`), over every file under `etc/containers/systemd` and `usr/share/containers/systemd`, whatever its name or depth:
  - a unit folder that is a link, is reached through one, or is not a folder: a finding;
  - a link or a non-regular file inside: a finding (Quadlet follows links; the checker would not see what one reaches on a node);
  - a line ending in `\`, a comment included: a finding (the checker reads one line at a time);
  - a `HealthCmd=` or `HealthStartupCmd=` line, its key in any case and spaces around `=` allowed: its value, trimmed, must be printable ASCII without tabs, and a JSON array of non-empty strings whose first is an absolute path. Each line is checked, so a later one cannot replace a good one unseen;
  - a `PodmanArgs=` line whose value names `health` in any case: a finding (set health with the keys above).
  - Comments (`#`, `;`), blank lines and sections are skipped.
- [x] **Stricter than Podman, on purpose:** `["CMD", …]` and non-ASCII items are exec form to Podman but findings here; `none` and `["NONE"]` need no shell, but a shipped unit has no reason to turn its check off. One form, which this check and Go's JSON reader read alike.
- [x] **Rejected:**
  - reading only `*.container` and `*.d/*.conf`: Quadlet's file types change between versions, and a `HealthCmd=` anywhere in its folders costs nothing to refuse;
  - parsing continuations: refusing them is simpler, and our units need none.
- [x] **Not checked here:** an image's own `HEALTHCHECK` (a container without `HealthCmd=` inherits it; part of the service-image contents check, ADR 0013).

## Evidence log

All test runs were in `rikuri-drill` with `python3 -m unittest discover -s image/tests` (`safe-run.sh` refuses on macOS; the CI gate runs them through it); every `tar:` line is filtered from the kept output.

- **Probes** (`01` to `04`, each with its script): as in 0b.
- **Red** (`05-red-tests.out`): 206 tests, `FAILED (failures=1, errors=53)`. Every error is the missing `check_quadlet_health`; the failure is `check_root` not running it. A first try ran 287 tests: the new class inherited the old class's tests and ran them twice; it now takes only `setUp` and `assertFinds`.
