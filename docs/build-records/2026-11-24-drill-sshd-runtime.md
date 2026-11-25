# Build Record — the drill's check tells its own start of sshd from an enablement (stage 1, plan §8)

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/no-shell-login` (PR #174, draft), at `89e70fe`: the check exists only there; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
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
