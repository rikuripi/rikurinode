# Build Record — the drill proves no shell login is enabled by default (stage 1, plan §8)

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/no-shell-login`, from `main` at `5ad035d`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (filled at close-out) |
| **Status** | BLOCKED (two repair cycles used; the check reads the drill's own start of sshd as enabled) |
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
  - `systemctl show -p Id -p LoadState -p UnitFileState sshd.service sshd.socket debug-shell.service`: each is disabled, masked, or not installed (the debug shell since repair 1). The kernel argument starts sshd for the drill without enabling it, so it does not change this state.
  - `getent passwd`, as each account's name, its password field's first character and length, and its UID: every field is `x` alone or locked (`!`, `*`); root is listed; no account has a UID from 1000 to 60513 (login's 1000–60000 and systemd-homed's 60001–60513: a human account; repair 1, nit 2). Both `getent` commands run with `pipefail` (nit 4).
  - `getent shadow`, as each account's name, its password field's first character and its length (never the field itself): every field is locked, `!` or `*` first; none empty (an empty field logs in with no password); root is listed.
  - Every file named `authorized_keys*` under `/etc`, `/root`, `/home`, `/var/roothome` and `/var/home`: every key in them is the drill's own (`key.pub`), and at least one is found, so the search is seen to reach root's.
  - `grep -rlE` for an `ExecStart=` that starts agetty with `--autologin` or `-a` in any form, in the systemd unit and drop-in files under `/etc/systemd`, `/usr/lib/systemd` and `/run/systemd`: none (a console that logs in by itself is a shell with no password; the pattern and `/run/systemd` as of repair 1).
  - `/proc/cmdline` and the login credentials (repair 1): see "Added in repair 1" below.
- **A pure function** `shell_login_closed(sshd, accounts, passwords, keys, autologin, cmdline, credentials, drill_key) -> (ok, detail)` judges the seven readings (five before repair 1) and the drill's key; unit tests hold it and the step, as for `boot_automount`.
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
- **The verifier**, follow-up pass on `c287a6b..18cdf5d` (the corrections only): **Pass**, no Important finding open. I-1 closed: each bypass it named now fails. No new false pass or false fail found on a good Fedora IoT node. Nothing loosened. 37 hand mutants killed; the survivors are equivalent or end the drill in an error, never a pass.
  - Its nits: (A) systemd reads `-` and `_` alike in a kernel argument's name, so `systemd.debug-shell` would give the debug shell and pass; (B) Design bullets still described the readings before repair 1; (C) the surviving mutants, for the backlog.
- **Repair 2** (the second and last), nits A and B: `_karg_name` reads each `-` in an argument's name as `_` before comparing (`systemd.debug-shell`, `rd.systemd.debug-shell=tty1` and `systemd.set-credential=…` now fail; a `-` in a value, such as `rootflags=data-journal`, is left alone); the Design's bullets updated. **Reasons for its test changes:** three hyphenated arguments added to `test_a_kernel_argument_for_a_shell_fails`, and a value with `-` that must pass; nothing changed or loosened. Not reviewed again: a third review round is not allowed (AGENTS.md §5), and the change is the verifier's own suggested fix; CI holds it.

## The drill on `18cdf5d`: the check finds sshd enabled

- `CI`, [run 45495424736](https://github.com/rikuripi/rikurinode/actions/runs/45495424736): `Full gate (Ubuntu)` Pass.
- The image workflow, [run 45495422770](https://github.com/rikuripi/rikurinode/actions/runs/45495422770): build, image check and USB install Pass. The drill: 50 checks Pass, one **Fail**, the new one, from the job's log:
  `FAIL no shell login by default: sshd.service: enabled; sshd.socket: disabled; debug-shell.service: disabled; accounts with a password: none; human accounts: none; authorized keys: 1, the drill's only: True (/var/roothome/.ssh/authorized_keys); autologin: none; kernel arguments for a shell: none; login credentials: none`
- **What it means:** after its first boot the node has **sshd enabled** and listening on port 22 (the drill's "only SSH, 80 and 443 listen outside" saw `[22, 80, 443]`). It starts without the drill's kernel argument. Every other part is closed: no account has a password, no human account, no key but the drill's, no autologin, no debug shell. So on a real node nobody can log in through it today, but the plan's "no shell login by default" and ADR 0011 ("Expert shell: SSH, key-only, off by default") are not met: a login service runs on the LAN with no use.
- **Not yet known:** whether the image ships sshd enabled or Fedora's presets enable it at the first boot; whether the node's firewall lets port 22 in from the LAN (the drill reaches it through QEMU's port forward).
- **As the Design says, this task stops here:** the check stays as it is, red, and the fix is a task of its own, the owner's to start.

## The owner's decision, and the drill on `main` with sshd off

- **"A, then Next"** (2026-11-24): option A, switch sshd off in the image, a task of its own: `docs/build-records/2026-11-24-sshd-off-by-default.md`, DONE. PR #175 merged by the owner at `47683cb` (`56e1c64`); its close-out, PR #176, at `3312b6d` (`cd69ea2`), `Full gate (Ubuntu)` [run 45510698073](https://github.com/rikuripi/rikurinode/actions/runs/45510698073) Pass.
- **"Next"** (2026-11-24): this branch updated with `main` by a merge (`8f367e1`), not a rebase, so no force-push. The branch's own changes are unchanged: this record, `image/drill/vm_drill.py`, `image/tests/test_vm_drill.py`. No test changed.
- Expected: the drill's "no shell login by default" passes, its detail reading `sshd.service: disabled`. The drill still starts sshd through its kernel argument, so "only SSH, 80 and 443 listen outside" is unchanged.

## The drill on `eeb38a5`: sshd no longer enabled, but enabled at run time by the drill itself

- `CI`, [run 45519944000](https://github.com/rikuripi/rikurinode/actions/runs/45519944000): `Full gate (Ubuntu)` Pass.
- The image workflow, [run 45519943959](https://github.com/rikuripi/rikurinode/actions/runs/45519943959): build, image check and USB install Pass. The drill: one **Fail**, the new check, from the job's log:
  `FAIL no shell login by default: sshd.service: enabled-runtime; sshd.socket: disabled; debug-shell.service: disabled; accounts with a password: none; human accounts: none; authorized keys: 1, the drill's only: True (/var/roothome/.ssh/authorized_keys); autologin: none; kernel arguments for a shell: none; login credentials: none`
- **What changed:** on `18cdf5d` sshd was `enabled`; now it is `enabled-runtime`. The image's fix (#175) holds: nothing on the node's disk enables sshd any more.
- **Why it still fails, reasoned and not observed:** `enabled-runtime` means an enablement link under `/run`, which lasts one boot. The drill's own kernel argument `systemd.wants=sshd.service` makes systemd's debug generator write such a link in its generator folder under `/run` at every boot. Before the fix the persistent `enabled` hid this. The check accepts only `disabled`, `masked` or not installed (`shell_login_closed`), and its tests hold `enabled-runtime` as a Fail (`ShellLoginReads`, "enabled at run time"). Where the link lies was not read: the drill keeps `systemctl show` only.
- **So the Fail is the check's, not the node's,** as far as the reading shows. It is a defect in this task's own check, and a fix would be a third repair cycle, which AGENTS.md §5 does not allow. This task stops: **BLOCKED**.
- **Proposed next task** (the owner's to authorize; it renews the repair count): the check accepts `enabled-runtime` for `sshd.service` only when the kernel command line holds the drill's `systemd.wants=sshd.service` **and** every enablement link for sshd lies in systemd's generator folders under `/run` (read with a `find` of the `*.wants`, `*.requires` and `*.upholds` folders under `/etc/systemd`, `/run/systemd` and `/usr/lib/systemd`). Any link in `/etc`, `/usr/lib` or `/run/systemd/system`, or any other state, still fails. Red first: the test that holds `enabled-runtime` as a Fail is changed with that reason, and a new reading added; one verifier pass.
