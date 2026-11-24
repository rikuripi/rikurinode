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
  - `getent passwd`, as each account's name, its password field's first character and length, and its UID: every field is `x` alone or locked (`!`, `*`); root is listed; no account has a UID from 1000 to 60513 (login's 1000–60000 and systemd-homed's 60001–60513: a human account; repair 1, nit 2). Both `getent` commands run with `pipefail` (nit 4).
  - `getent shadow`, as each account's name, its password field's first character and its length (never the field itself): every field is locked, `!` or `*` first; none empty (an empty field logs in with no password); root is listed.
  - Every file named `authorized_keys*` under `/etc`, `/root`, `/home`, `/var/roothome` and `/var/home`: every key in them is the drill's own (`key.pub`), and at least one is found, so the search is seen to reach root's.
  - `grep -rl … autologin` in the systemd unit and drop-in files under `/etc/systemd` and `/usr/lib/systemd`: none (a console that logs in by itself is a shell with no password).
- **A pure function** `shell_login_closed(sshd, accounts, passwords, keys, autologin, drill_key) -> (ok, detail)` judges the five readings; unit tests hold it and the step, as for `boot_automount`.
- **If the first run finds a login enabled,** this task stops there: the check stays red, and the fix is the owner's decision and a task of its own.
- **Added in repair 1** (verifier I-1): `debug-shell.service` must be disabled, masked or not installed (it gives a root shell on tty9); `/proc/cmdline` must hold no argument but the drill's own that gives a shell or a credential (`init=`, `rd.break`, `systemd.debug_shell`, `rd.systemd.debug_shell`, `systemd.set_credential`, `systemd.wants=`, `systemd.unit=`, `SYSTEMD_SULOGIN_FORCE`); no credential named `agetty.*` or `login.*` in the credential stores or among those systemd imported at this boot (`/run/credentials/@system`, which holds those from the command line and SMBIOS); agetty's `-a` in any form (`-a root`, `-aroot`), and `/run/systemd` searched too.
- **Not covered:**
  - sshd's own configuration (`AuthorizedKeysFile`, `AuthorizedKeysCommand`), and keys outside the folders searched (system homes under `/var/lib`);
  - sshd **started** but not enabled: a `Wants=` from another unit or drop-in, or `systemd.wants=sshd.service` in the image's own kernel arguments (`/usr/lib/bootc/kargs.d`), which on the drill's disk looks the same as the drill's own (verifier nit 1);
  - drop-ins under `/usr/local/lib/systemd`, and unit files reached only through a symbolic link;
  - a real install, without the drill's disk (the USB install test reads the disk only offline).

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

## Evidence log

### The change

- `image/drill/vm_drill.py`, as designed: the commands `SHOW_SSHD`, `ACCOUNTS`, `PASSWORDS`, `KEY_FILES`, `AUTOLOGIN`; `shell_login_closed`; `Drill.shell_login` (its readings kept in `01e-shell-login.out`); `main` runs it after `boot_automount`; `EXPECTED` names "no shell login by default".
- **Narrowed while writing, before any run:** the autologin search looks only for an `ExecStart=` that starts agetty with `--autologin` or `-a`. A plain search for "autologin" might match a unit's comment or a credential's name; a plain `-a` matches other programs' flags. Each key file's contents are followed by a newline, so a file without a last newline cannot join the next file's name.
- **Reasons for the test changes** (`image/tests/test_vm_drill.py`; new coverage, no defect fixed, so no red commit):
  - `Verdict.test_every_check_names_a_step`: the new check's name added to the list; nothing else changed.
  - New `ShellLoginReads`: the commands exactly, with the password field never printed; a closed node passes with its detail; sshd masked or not installed passes; sshd enabled (service or socket), enabled at run time, static, with no state or not reported fails; an account with a hash, an empty field, a human UID (1000 and 59999), an unreadable line, or root missing fails; UIDs outside the human range pass; no key, a file with no key, another key, or a line that is not a key fails; the drill's key with options and comments passes; autologin found, grep failed or no answer fails; each reading not made fails with "not read".
  - New `ShellLoginSteps`: the step asks the five commands with `check=False`, keeps what it read, fails when sshd is enabled, when a command failed (kept as "(no answer)") or when the drill's key cannot be read; `main` runs it between `boot_automount` and `control_plane`.
- On the Mac: `ast` parse checks of both files and `git diff --check`.

## Verification

- **The verifier**, pass 1 on `5ad035d..c287a6b` (routine): **Fail**, one Important finding.
  - **I-1:** the console rule missed three ways a console gives a shell with no password: an `agetty.autologin` credential (systemd's getty units import `agetty.*`; util-linux's agetty reads it, and `login -f` skips even a locked password), an enabled `debug-shell.service`, and agetty's attached `-aroot`. The Outcome and the step's docstring claimed more than the check held.
  - Confirmed: the five commands quote correctly for root's shell; every failed command ends in a Fail; shadow's password field never printed; the test changes additive.
  - Nits: (1) sshd started but not enabled is not seen; (2) mutants survive: a key compared by type alone (no test had a second ed25519 key), and the UID range's upper bound; (3) passwd's own field was kept in the artifact; (4) no `pipefail`.
  - CI on `c287a6b`: `Full gate (Ubuntu)` [run 45493995072](https://github.com/rikuripi/rikurinode/actions/runs/45493995072) Pass.
- **Repair 1** (one of two): option (b) of the verifier's two, which keeps the Outcome as the contract set it, instead of narrowing it. In the Design above: the debug shell, the kernel arguments, the credentials, `-a` in every form and `/run/systemd`; passwd read as first character and length (nit 3); `pipefail` (nit 4); the human range to 60513 (nit 2). Nit 1 is listed under "Not covered".
- **Reasons for the test changes in repair 1:**
  - The fixtures follow the new readings: `SSHD_OFF` gains the debug shell's block; `ACCOUNTS_OK` is in the new form (name, first character, length, UID); `CMDLINE_OK` and `CREDENTIALS_OK` added. `test_the_commands` and the passing detail follow the new commands and detail. No expectation is loosened: each earlier failing case still fails, rewritten in the new form.
  - New cases: the debug shell enabled or not reported; a passwd `x` that is not the whole field; UIDs 60000 and 60513 fail and 60514 passes; a second ed25519 key fails (nit 2); each kernel argument for a shell fails and only the drill's own pass; `agetty.autologin` and `login.noauth` credentials fail, another credential passes, and a search that did not finish fails; the autologin pattern matches `--autologin`, `-a root` and `-aroot`, and not Fedora's agetty lines or another program's `-a`.
  - `ShellLoginSteps`: seven commands, not five.
