# Build Record — the drill proves no shell login is enabled by default (stage 1, plan §8)

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/no-shell-login`, from `main` at `5ad035d`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | test tooling: a stage requirement given a check |

## Intent: the owner's words

- **"Next"** (2026-11-24), after `docs/build-records/2026-11-24-power-return-n150.md` ended DONE. Its Next: prove stage 1's "no shell login enabled by default"; today it appears met, but no test holds it.
- The plan, §8, stage 1's security slice: "no shell login by default".

## The gap

- Nothing checks it. The drill gives root its own key (`--root-ssh-authorized-keys`) and starts sshd with a kernel argument (`systemd.wants=sshd.service`), both on its own disk only (`image/drill/vm_drill.py`, `install_argv`). Without them a node has no key and no sshd, as far as anyone has looked; the install on the N150 showed a login prompt and no account (`docs/build-records/2026-11-03-install-n150.md`).
- systemd applies the distribution's presets at a first boot. Fedora's presets enable sshd on many editions. So the image's files alone cannot show what a node runs after its first boot; the running node can.

## Design

- **Where:** the VM drill, at its first boot, by a new step `Drill.shell_login` run from `main` after `boot_automount`. This first boot differs from a real install only by the drill's key and kernel arguments, and each part of the check allows for exactly those.
- **What it reads**, as root over the drill's SSH, each command with `check=False` (a command that fails is a Fail of this check, never a drill error):
  - `systemctl show -p Id -p LoadState -p UnitFileState sshd.service sshd.socket`: each is disabled, masked, or not installed. The kernel argument starts sshd for the drill without enabling it, so it does not change this state.
  - `getent passwd`, its first three fields: every account's password field is `x` or locked (`!`, `*`); root is listed; no account has a UID from 1000 to 59999 (a human account).
  - `getent shadow`, as each account's name, its password field's first character and its length (never the field itself): every field is locked, `!` or `*` first; none empty (an empty field logs in with no password); root is listed.
  - Every file named `authorized_keys*` under `/etc`, `/root`, `/home`, `/var/roothome` and `/var/home`: every key in them is the drill's own (`key.pub`), and at least one is found, so the search is seen to reach root's.
  - `grep -rl … autologin` in the systemd unit and drop-in files under `/etc/systemd` and `/usr/lib/systemd`: none (a console that logs in by itself is a shell with no password).
- **A pure function** `shell_login_closed(sshd, accounts, passwords, keys, autologin, drill_key) -> (ok, detail)` judges the five readings; unit tests hold it and the step, as for `boot_automount`.
- **If the first run finds a login enabled,** this task stops there: the check stays red, and the fix is the owner's decision and a task of its own.
- **Not covered:** sshd's own configuration (`AuthorizedKeysFile`, `AuthorizedKeysCommand`): with sshd not enabled it serves no one; a real install, without the drill's disk (the USB install test reads the disk only offline).

## Task Contract

1. **Outcome:** stage 1's "no shell login by default" is a check that fails the drill if a node, after its first boot, could be logged into by anyone.
2. **Scope:** routine (test tooling; the node's code is untouched).
   - `image/drill/vm_drill.py`: the commands, `shell_login_closed`, `Drill.shell_login`, its place in `main`, and the check's name in `EXPECTED`.
   - `image/tests/test_vm_drill.py`: tests for the function and the step; the check's name in `Verdict`'s list; its place in `main`.
   - This record.
   - **Not included:** any change to the image; a fix if the check fails; sshd's configuration.
3. **Done when:** the full gate passes in CI with the new tests; the image workflow's drill passes, with "no shell login by default" Pass and its detail read from the log; one `verifier` pass (code; AGENTS.md §5).
4. **Authority:** the files above. On the Mac: `ast` parse checks and `git diff --check`; the tests run in CI only. Commit and push this branch; a draft PR to `main`; the owner merges.
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; VM time is reported.
