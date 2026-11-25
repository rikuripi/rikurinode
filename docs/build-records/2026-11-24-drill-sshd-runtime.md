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
