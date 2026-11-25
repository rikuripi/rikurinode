# Build Record — the drill's check tells its own start of sshd from an enablement (stage 1, plan §8)

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/no-shell-login` (PR #174, draft), at `89e70fe`: the check exists only there. #174 merged by the owner at `d260504` (`d163001`) with I-1 open; repair 1 on the same branch, draft PR #177; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | defect fix (test tooling: the drill's check) |

## Intent: the owner's words

- **"Next"** (2026-11-24), after `docs/build-records/2026-11-24-no-shell-login.md` ended BLOCKED. Its Next: "the check accepts `enabled-runtime` for sshd only when the drill's argument is on the kernel command line and every sshd link is in systemd's generator folders under `/run`. A red test comes first, then one verifier pass." A new task, so its own two repair cycles and two review rounds.

## The defect

- **Seen:** the drill on `eeb38a5`, [run 45519943959](https://github.com/rikuripi/rikurinode/actions/runs/45519943959): `FAIL no shell login by default: sshd.service: enabled-runtime; …` with every other reading closed.
- **The cause, reasoned:** the drill boots with `systemd.wants=sshd.service`; systemd's debug generator then links sshd into a target's `.wants` folder in a generator folder under `/run`, for that boot only, and `systemctl` reports that as `enabled-runtime`. `shell_login_closed` accepts only `disabled`, `masked` or not installed. Where the link lies is not yet read.

## Design

- **A new reading,** `SSHD_LINKS`: every entry named `sshd.service` or `sshd.socket` in a `.wants`, `.requires` or `.upholds` folder under `/etc/systemd`, `/run/systemd` and `/usr/lib/systemd` (`find`, links not followed), then `rc=$?`. The drill keeps it with the others in `01e-shell-login.out`.
- **The rule** in `shell_login_closed`, a new argument `links` before `drill_key`:
  - `sshd.service` at `enabled-runtime` is closed only when the kernel command line holds `systemd.wants=sshd.service`, the search finished (`rc=0`), at least one link was found, and every link found is `sshd.service` in `/run/systemd/generator/`, `/run/systemd/generator.early/` or `/run/systemd/generator.late/`. Its detail says so: `enabled-runtime, by the drill's kernel argument`.
  - Any link found anywhere else, or any `sshd.socket` link, fails whatever the units' states; a search that did not finish fails.
  - Everything else is unchanged: `enabled`, `static`, no state, an unreported unit, `enabled-runtime` for the socket or the debug shell all still fail.
  - The detail gains `enablement links: …` (the paths, or `none`), after the units.
- **Why the generator folders only:** `systemctl enable --runtime` writes to `/run/systemd/system`, which this rule refuses; only a generator writes into the generator folders, and the drill's kernel argument is the one generator input the check allows for sshd (`DRILL_KARGS`).
- **Not changed:** the other readings; the image; the drill's own arguments; `EXPECTED`.

## Task Contract

1. **Outcome:** the drill's "no shell login by default" passes on a node whose only sshd enablement is the drill's own one-boot start, and still fails on any other.
2. **Scope:** routine (a test tool's check; no node behaviour, auth, funds or keys).
   - `image/drill/vm_drill.py` (`SSHD_LINKS`, `GENERATOR_DIRS`, `shell_login_closed`, `Drill.shell_login`); `image/tests/test_vm_drill.py` (red first).
   - This record; `docs/build-records/2026-11-24-no-shell-login.md`'s close-out.
   - **Not included:** the verifier's backlog nits from #174 and #175; the N150's state after an update.
3. **Done when:**
   - Red: the tests committed alone and seen failing in CI's full gate.
   - Then the fix in its own commit; the full gate passes, and the image workflow's drill passes "no shell login by default" with its detail naming the generator link.
   - One `verifier` pass (code; AGENTS.md §5).
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`; the tests run in CI only. Commit and push this branch; #174 stays a draft; the owner merges.
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; VM time is reported.

## Evidence log

### Red

- `image/tests/test_vm_drill.py` only; `vm_drill.py` unchanged.
- **Reasons for the test changes** (a defect fix, red first):
  - The fixtures gain the new reading: `NO_LINKS` (`rc=0`, nothing found), `DRILL_LINK` (the debug generator's link, in `generator.early`), `SSHD_RUNTIME` (sshd.service at `enabled-runtime`). `LOGIN_CLOSED` and `READING_NAMES` gain `links` before the drill's key, as the new argument.
  - `test_the_commands`: `SSHD_LINKS` and `GENERATOR_DIRS` exactly.
  - `test_a_closed_node_passes_and_says_what_it_read`: the detail gains `enablement links: none` after the units. Nothing else in it changes.
  - New `test_the_drill_s_own_start_at_run_time_passes`: `enabled-runtime` with the drill's argument and a link in each of the three generator folders passes, and says so.
  - New `test_a_start_at_run_time_that_is_not_the_drill_s_fails`: no link; a link in `/run/systemd/system` (`systemctl enable --runtime`); a link in `/etc` or `/usr/lib` beside the generator's; the socket linked too; no `systemd.wants=sshd.service` on the command line; the search not finished, or no answer: each fails.
  - New `test_an_enablement_link_fails_whatever_the_state`: with every unit `disabled`, a link for sshd in `/etc`, a socket link in `/usr/lib` or in a generator folder, or an unfinished search, fails.
  - `ShellLoginSteps`: its command list, now built in `setUp` because it names the new constant, gains `SSHD_LINKS`; its slices of `LOGIN_CLOSED` follow the new length (`[:7]` to `[:8]`, `[1:7]` to `[1:8]`, `[3:7]` to `[3:8]`), the same readings as before plus `links`. New: the drill's own start passes the step, and the link is kept.
  - Unchanged and still held: `test_sshd_enabled_fails`, its "enabled at run time" case among them (the socket at `enabled-runtime`, which no link explains); every other case.
- Expected in CI: the full gate fails in the image tests. `ShellLoginReads` errors with a `TypeError` (the check takes eight readings, not nine); `ShellLoginSteps` errors with an `AttributeError` (no `SSHD_LINKS`). Nothing else in the file changes.

### The red run, `37396c4`: Fail as expected

- `CI`, [run 45523530424](https://github.com/rikuripi/rikurinode/actions/runs/45523530424): `Full gate (Ubuntu)` failed in the image tests with `FAILED (errors=85)`, all in `ShellLoginReads` and `ShellLoginSteps`: 78 `TypeError: shell_login_closed() takes 8 positional arguments but 9 were given`, 7 `AttributeError: module 'vm_drill' has no attribute 'SSHD_LINKS'`. No other test failed.

### The fix

- `image/drill/vm_drill.py`: `SSHD_LINKS`, `GENERATOR_DIRS` and `DRILL_WANTS`, with the reason; `shell_login_closed` takes `links` and applies the Design's rule, its detail gaining `enablement links: …`; `Drill.shell_login` reads `SSHD_LINKS` and its docstring no longer says the drill leaves sshd's enablement alone.
- No test changes after the red.

## Verification

- **The verifier**, pass 1 on `89e70fe..d260504` (routine): **Fail**, one Important finding.
  - **I-1:** `SSHD_LINKS` misses enablement links systemd reads, so a lasting enablement passes as the drill's own. It searches three folders, not systemd's whole unit path: `/usr/local/lib/systemd/system` is left out, and on Fedora IoT `/usr/local` is `/var/usrlocal`, kept across updates. `find` does not enter a linked `.wants` folder; systemd does. systemd reports any link under `/run` as `enabled-runtime` before a link in `/usr/local/lib` or `/usr/lib` (`install.c`, `find_symlinks_in_scope`), so with the drill's argument such a node reads `enabled-runtime`, the search finds the generator's link only, and the check passed. Shown on a scratch tree with the real command run through `bash -c`; not on a node.
  - Confirmed: the red commit is tests and this record only, and failed as recorded; no test changed after it; every test change has its reason and none is loosened; the command's quoting reaches root's bash intact; a quoted or shortened `systemd.wants=` fails safe. From systemd v256's source, the debug generator writes only into `/run/systemd/generator.early`, as `<default target>.wants/sshd.service`. **Not yet proven:** the image's systemd version and the link's path on a node.
  - Nits: (1) any generator link is accepted, not only the debug generator's; (2) and (3) surviving mutants: the `unit == "sshd.service"` and `state == "enabled-runtime"` conditions can each be dropped with every test passing; (4) a link of another name whose target is sshd (an alias) is not searched; (5) before this change, a drop-in `Wants=sshd.service` and systemd's ssh generator's own units are not read.
  - CI on `d260504`: `Full gate (Ubuntu)` [run 45525628608](https://github.com/rikuripi/rikurinode/actions/runs/45525628608) Pass; the drill, [run 45525627662](https://github.com/rikuripi/rikurinode/actions/runs/45525627662), still running when this was written.
- **Repair 1** (one of two), for I-1 and nits 1 to 3:
  - `SSHD_LINKS` reads the folders from `systemd-analyze unit-paths`, systemd's own list, and searches each with `find -L`, so linked folders are entered; a `find` or `systemd-analyze` that fails fails the search.
  - Only one link explains `enabled-runtime`: `DRILL_LINK`, `/run/systemd/generator.early/default.target.wants/sshd.service`, the debug generator's own. Any other link fails, in a generator folder or not. A wrong guess fails safe: the drill shows the path.
  - Nits 4 and 5: backlog, not done here.

### The drill on `d260504`, before repair 1: Pass, and the link's path observed

- The image workflow, [run 45525627662](https://github.com/rikuripi/rikurinode/actions/runs/45525627662): every job Pass, no drill check failed. From the job's log:
  `PASS no shell login by default: sshd.service: enabled-runtime, by the drill's kernel argument; sshd.socket: disabled; debug-shell.service: disabled; enablement links: /run/systemd/generator.early/default.target.wants/sshd.service; …`
- **Observed:** the debug generator's link is the one path repair 1 accepts, and the only sshd link the search found. This is the first-pass search; I-1 still stands for the folders it missed.

### Repair 1: red

- `image/tests/test_vm_drill.py` only. **Reasons for the test changes:**
  - `test_the_commands`: `SSHD_LINKS` exactly in its new form; `DRILL_LINK` in place of `GENERATOR_DIRS`, which goes.
  - `test_the_drill_s_own_start_at_run_time_passes`: only the debug generator's link passes now, so the case is that link alone. Narrowed, not loosened: the two other generator folders it passed before must now fail (below).
  - New `test_only_the_debug_generator_s_own_link_is_the_drill_s`: a link in `generator` or `generator.late`, under another target or in `.requires`, or in `/usr/local/lib/systemd/system`, alone or beside the drill's link, fails.
  - New `test_the_drill_s_link_explains_sshd_service_at_run_time_only` (nits 2 and 3): with the drill's link, sshd.service `enabled`, `static` or `linked` fails, and so does the socket or the debug shell at `enabled-runtime`.
- Expected in CI: the full gate fails on `test_the_commands` (the command and `DRILL_LINK`) and on the generator and generator.late cases of the new test, which today's rule passes.

### Repair 1's red run, `77a3dba`: Fail as expected

- #174 merged before `77a3dba` was pushed, so no run started; draft PR #177 carries the branch from there.
- `CI`, [run 45667459234](https://github.com/rikuripi/rikurinode/actions/runs/45667459234): `Full gate (Ubuntu)` failed with `FAILED (failures=9)`: `test_the_commands` (the old command), and 8 cases of `test_only_the_debug_generator_s_own_link_is_the_drill_s`: a link in `generator`, `generator.late`, under `multi-user.target` or in `.requires`, each alone and beside the drill's link, which the first rule passes. The record above expected only the `generator` and `generator.late` cases: it undercounted; the two others are the same defect (any generator link accepted, nit 1). No other test failed; the `/usr/local` cases and the new mutant-killing test already passed, as the first rule fails them.

### Repair 1: the fix

- `image/drill/vm_drill.py`: `SSHD_LINKS` reads `systemd-analyze unit-paths` and searches each folder with `find -L`, the search failing if either fails; `DRILL_LINK` replaces `GENERATOR_DIRS`, and the rule accepts that one path only. The comments and docstrings follow.
- No test changes after the red.
