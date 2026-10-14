# Guard and sandbox: the reference

The detail behind [AGENTS.md](../AGENTS.md) > Deterministic gates, which
keeps the short form. Moved there from AGENTS.md word for word on
2026-10-13 (the owner's amendment; Build Record
[2026-10-13-bounded-agent-standard](build-records/2026-10-13-bounded-agent-standard.md)).
`scripts/quality/tests/test_guard_claims.py` holds the forms and path
spellings listed here: a form added here is added there, and the other
way round. "Above" and "below" refer to this page.

## Claude Code's OS sandbox

- **The boundary: Claude Code's OS sandbox** (owner, 2026-10-11). Every
  shell command in a session opened here runs inside bubblewrap: it can
  write only inside this repository and the temporary folder, cannot reach
  a Unix socket (the Docker socket drives the live node) or a local port,
  reaches GitHub's domains and crates.io's index and download hosts
  (`index.crates.io`, `static.crates.io`; owner, D24, 2026-10-12: run cargo
  as `scripts/cargo.sh`, which keeps its cache in the checkout) without a
  prompt and any other host only after
  a prompt (`strictAllowlist`, which would refuse them, is ignored in
  project settings, per Claude Code's settings schema; in `auto` mode a
  command that does not list the host is refused, with no prompt), and is set
  to deny reads of the previous checkout's `.env` and `data/`, `/run/rikuri`,
  and fourteen private paths of the owner's that exist on this machine
  (owner, D25, 2026-10-12: a crate's build script runs inside the sandbox,
  and reads are otherwise open): `~/.ssh`, `~/.config/gh`,
  `~/.git-credentials`, `~/.docker`, `~/.claude/.credentials.json`,
  `~/.gnupg`, `~/.bitcoin`, `~/.local/share/keyrings`, the Chrome, Chromium
  and Brave profiles under `~/.config`, `~/.config/Code`, `~/.config/Claude`
  and `~/.local/share/Trash`. Any other file in the home folder stays
  readable; a private path made later needs adding. A plain `cargo` fails when it must download (the sandbox
  refuses its write to `~/.cargo`), but builds quietly from crates already
  in that shared cache; use `scripts/cargo.sh`. The sandbox
  itself protects `.git/hooks`, `.git/config` and the paths it names under
  `.claude` (not `.claude/state`, as round 9's verifier read Claude Code's
  binary); the settings add `scripts/quality/hooks`. If the sandbox cannot
  start, Claude
  Code refuses to run commands (`failIfUnavailable`), and a command never
  retries outside it (`allowUnsandboxedCommands: false`). Only `git push`, `git fetch` and
  `git pull` leave it (SSH cannot use its proxy); they still pass the guard
  and the permission prompt. `scripts/quality/check_guard_wiring.py` (run by
  the gate) is closed-world: it fails unless `.claude/settings.json`'s
  `sandbox` block is exactly this one and `.claude/settings.local.json` sets
  none, and in either file it allows only the top-level keys it lists
  (`$schema`, `hooks`, `permissions`, `sandbox`, `env`, `disableAllHooks`:
  others may run a command, such as `apiKeyHelper` or `statusLine`, load a
  plugin that brings hooks, or start MCP servers), only the guard's own
  `PreToolUse` hook (with exactly its committed keys — `if`, `once` or
  `async` would change when it runs or whether its failure blocks — and a
  timeout, a whole number of seconds from 1 to 10; no other hook event, and
  none in the local file),
  no allow rule for `Edit`, `Write`, `MultiEdit`, `NotebookEdit`,
  `WebFetch` or `Read` (the settings schema merges `Edit` allow rules into
  the sandbox's writable paths and `WebFetch` ones into its domains; the
  other four are refused as a precaution), no `additionalDirectories`, no
  permissions key it does not know, a
  permission mode from its list (`default`, its alias `manual`,
  `acceptEdits`, `plan`; the other modes the settings schema names,
  `bypassPermissions`, `dontAsk` and `auto`, are refused),
  and only the environment variables it lists (`RUST_LOG`, `NO_COLOR` and a
  few more: `PATH`, `LD_PRELOAD` or `BASH_ENV` would change what a command
  runs). Not checked: the owner's own user settings (`~/.claude/`); MCP
  servers a project `.mcp.json` declares — their tools are outside the
  guard's matcher; and agents, skills or commands under `.claude/`, which
  may declare MCP servers or run shell commands (only `.claude/agents/
  verifier.md` is tracked, and it declares neither). The settings need
  Claude Code 2.1.295 or later (`onFailure`: the version Claude Code's
  hooks reference gave when round 4 of the bootstrap read it; round 4's
  verifier found the setting in the installed 2.1.295 settings schema,
  absent from 2.1.289, 2.1.292 and the 2.1.221 binary). **The drill**
  (2026-10-12, `r18-sandbox-drill.out`), in a session opened in a worktree
  of this repository, in `auto` mode: the sandbox started and refused a
  write in the home folder, in `scripts/quality/hooks` and in `.git/hooks`,
  a Unix socket (the guard asked first; the owner approved), a connection
  to 127.0.0.1 (inside its own network namespace, where only its proxy
  listens) and an unlisted site; it allowed a write inside the repository
  and GitHub; it showed the previous checkout's `data/` and `/run/rikuri`
  as empty folders. Round 9's drill (2026-10-11) failed closed on Ubuntu's
  AppArmor rule for bubblewrap (`bwrap-userns-restrict`); the owner
  relaxed it that day (`r12-bwrap-check.out`), and it is still relaxed.
  **Not yet proven:** which change let the sandbox start (that, the Claude
  Code version, or the folder); the prompt for an unlisted host in the
  other modes; a local port named through the sandbox's proxy; the
  hook-folder forms under "What gets through the guard"; a session opened
  in this folder itself; thirteen of the fourteen D25 read denies (a deny
  acts only inside the sandbox; one is shown, below). **Shown inside the
  sandbox** by B0.1's session (2026-10-12, in a worktree, `auto` mode;
  `docs/build-records/evidence/2026-10-12-b0-1-control-plane-workspace/d24-fetch.out`,
  `d25-stat.out`): `scripts/cargo.sh fetch` of a pinned crate from
  crates.io's two hosts into the checkout's `.cargo-home/`, nothing in
  `git status`; and `~/.git-credentials` as the sandbox's stand-in (`stat
  -c %F` prints "character special file"; its type only, never its
  contents). Inside the sandbox, paths it protects that do not
  exist here (`.bashrc`, `.mcp.json`, `.claude/skills`, …) are `/dev/null`
  placeholders: they show as untracked, and `git add --all` fails on them
  (stage by name); the one for `.claude/settings.local.json` cannot be
  read, and the wiring check reads `/dev/null` itself there (a character
  device numbered 1:3, not a link to it) as no local settings, and says so;
  anything else there must be a regular file, read in place: a link
  (dangling or not), a folder, a FIFO, a device or a socket fails the gate
  (owner, 2026-10-12; `docs/build-records/2026-10-12-wiring-sandbox-placeholder.md`); and
  `safe-run.sh` sees no node containers there,
  so its start-time check compares nothing.

## The guard

- `.claude/hooks/guard.py` (with `guard_base.py` and `test_guard.py`,
  identical in every Full-tier repository) runs before each `Bash`,
  `Read`, `Edit`, `Write`, `MultiEdit`, `NotebookEdit` and `Grep` call
  (its matcher in `.claude/settings.json`); this repository's policy is
  `.claude/hooks/guard-config.json`, profile `development`, written by
  `scripts/quality/guard_policy.py` (change a rule there and add a worked
  example; the gate refuses a policy edited by hand). It is an early
  warning that reads command text, not a boundary. It denies reading
  secrets, force pushes, and test edits under the fix-lock. It always asks
  before: money moves and key-exposing commands; container, runtime,
  service, power and package changes on this machine (it runs the live
  node); kills of node daemons; commands that name one of the node's key
  files; and the forms below. **Node and container tools, closed-world**
  (owner, 2026-10-11): any command that names `lncli`, `bitcoin-cli`,
  `tapcli`, `litcli`, `chantools`, `docker`, `podman`, `nerdctl`,
  `docker-compose` or `podman-compose` as a word — anywhere, called by a
  path, after `sudo`, `env`, `timeout` or `ssh`, inside quotes or code —
  asks, unless the command, alone in its segment and whole, is one of the
  reads listed in `guard_policy.py` (such as `lncli getinfo`,
  `listchannels`, `walletbalance`; `bitcoin-cli getblockchaininfo`,
  `getbalances`; `tapcli assets list`; `docker ps`, `logs`, `images`,
  `inspect` only with a `--format` of fields that hold no secret; their
  `--help` and `--version`), with plain words after it and only
  redirections, or only names it (`which`, `type`, `command -v`, `ls`, a
  checksum, a service's `systemctl status` or `journalctl`). A read command
  (`grep`, `echo`, `git log`, …) is exempt from these rules only when it
  runs alone: a lone `&`, a `$(…)`, a process substitution (`<(…)`, `>(…)`,
  zsh's `=(…)`), or an option with which it runs a program or writes a file
  (git grep's `-O` or `--open-files-in-pager`, rg's `--pre`, ag's
  `--pager`, git's `--output`, `--ext-diff`, `--textconv`) ends the
  exemption. A backtick does not end it; the guard judges a backtick's
  command, and a `$(…)`'s, itself. Its other asks are
  protected-path writes: they ask in `stable` and are logged in
  `development`. The guard blocks the tool call when it times out or fails
  (`"onFailure": "block"`, Claude Code 2.1.295 or later; checked by the
  gate). A deny is not an obstacle to route around: stop and ask.

## The previous checkout

- **The previous checkout, closed-world: always asks** before any command that
  names it (`/home/junc/rikuri/rikurinode`) or anything else in its parent
  folder (`/home/junc/rikuri`) — spelled from `/home/junc` (also `//`, `/./`),
  `/home/*`, `~`, `~junc`, `$HOME`, `${HOME}` or a parameter expansion such
  as `${HOME:?}`, `${HOME%/}` — unless the command, alone in its segment, is
  one of these reads: `cat`, `less`, `more`, `head`, `tail`, `wc`, `ls`,
  `stat`, `file`, `diff`, `cmp`, the checksum tools, `du`, `readlink`,
  `realpath`, `basename`, `dirname`, `grep`, `rg`, `ag`, `jq`, `test`, `[`,
  `strings`, `echo`, `printf`, `sort` (not `-T` or `--compress-program`),
  `tree` (not `-o`, in any cluster), `find` (not `-delete`, `-exec`, `-ok` or
  `-fprint`), `sed -n '<lines>p'` followed only by file names, `git -C <it>
  log|show|diff|grep|status|blame|ls-files|…`, a commit or tag message (not
  read from a file: `-F`, `--file`, `-t`), a search here, a PR or issue text
  (not `--body-file` or `-F`: the file would be posted); or a copy out of it
  with `cp` or `install` (never a link or a strip program: `-l`, `-s`,
  `--link`, `--symbolic-link`, `--strip-program`, in any cluster or
  abbreviation), `rsync` (not `-e`, `--rsh`, `--rsync-path`, `-T`,
  `--log-file`, `--temp-dir`, `--backup-dir`, `--partial-dir`,
  `--write-batch`, `--link-dest`, `--copy-dest`, `--compare-dest`) or `scp`
  (not `-S`, `-o`, `-F`, `-J`). The read options that end every read's
  exemption (above) end these too. **Writes into the parent folder always
  ask**: anything under `/home/junc/rikuri` as a copy's destination (also as
  `host:<path>`) or `-t`, `sort -o`, or a redirection's target. File-tool
  edits there are refused by the deny rule in `.claude/settings.json`, not by
  the guard.

## The pre-commit hook

- **The pre-commit hook: always asks** before git's options, configuration
  commands and environment that bypass it or move `core.hooksPath` (`-c`,
  `--config-env`, `GIT_CONFIG_COUNT`/`KEY_n`/`PARAMETERS`, `commit -n` or
  `--no-verify`, `include.path`, aliases, unsetting it, removing the `core`
  section, `config --edit`, `extensions.worktreeConfig`); a sparse checkout
  (`git sparse-checkout` other than `list`, `core.sparseCheckout` set or
  passed with `-c`, `read-tree`); `git switch --orphan`; `update-index
  --skip-worktree` or `--assume-unchanged`; paths fed by `xargs` to a
  command that deletes, moves or rewrites; and these on the hook's files
  (`scripts/quality/hooks`, `.git/hooks`, `.git/config`,
  `.git/config.worktree`, under any folder, through git's `:/` or `:(top)`
  magic, `~`, `~+`, a variable — also a parameter expansion such as
  `${PWD:?}` or `${PWD%/}` — a `$(…)` or a backtick):
  - `rm`, `rmdir`, `mv`, `rename`, `shred`, `chmod`, `chown`, `chgrp` — also
    on the folders that hold them (`scripts`, `scripts/quality`, `.git`,
    as whole words, with `/*`, `/**` or a brace list);
  - `tee`, `touch`, `truncate`, `ln`, `dd`, `unlink`, `mkdir`, `patch`,
    `cpio`, `split`, `csplit`, an editor (`vi`, `vim`, `nvim`, `nano`,
    `emacs`, `pico`, `micro`, `code`, `hx` and others listed in
    `writes()`); `sed -i`, `perl -i`, `gawk -i inplace` or
    `--include=inplace`; `zip -m`;
  - extraction with `tar`, `gtar`, `bsdtar`, `unzip`, `7z` or `cpio` (`-C`,
    `-d`, `-D`, `--directory`, `-o`, attached, in a cluster such as `-xvC`,
    or old-style `tar x…`) — also into the folders;
  - `cp`, `install`, `rsync`, `scp` or `ln` as the destination or `-t`;
    `rsync --delete` or `--remove-source-files`; `curl -o`/`--output-dir`,
    `wget -O`/`-P`, `sort -o`; `find` with `-delete` or `-exec`; a
    redirection (`>`, `>>`, `>|`);
  - git's `rm`, `mv`, `checkout`, `restore`, `apply`, `reset` and `stash`;
  - copying anything into `.git`, a folder named `hooks` into
    `scripts/quality`, or one named `quality` into `scripts`.

  Copying into `scripts/quality` and editing the hook's paths with the file
  tools ask in `stable` and are logged in `development`.

## Held by tests

- **Held by tests:** the 934 worked examples; `test_guard_claims.py` builds
  2,168 cases from the forms, path spellings, node and container reads
  listed above; `test_guard_baseline.py` replays 1,089 cases — the
  verifiers' from rounds 6 to 8 and 100 that round 8 drafted — and fails on
  any changed verdict until the baseline is regenerated and its diff
  reviewed; a speed test runs every rule on 162 inputs built to make a
  regular expression backtrack, in a child process, and fails if one is
  slow or the child does not finish in 60 s (a rule that took 21 s on a
  117-character command was found in round 8); `test_guard_wiring.py`
  checks the closed-world settings check against each widening above.

## What gets through the guard

- **What gets through the guard.** Not covered: a path relative to a folder
  entered earlier (`cd scripts/quality/hooks && rm pre-commit`); a glob inside
  a name (`hook*`, `scrip*`, `.gi?`, `rm -rf *`) and `git rm -r .`; `find .
  -name pre-commit -delete`; copying a folder's contents into `scripts/`
  (`rsync -a /tmp/x/ scripts/`); for the hook, any writer not listed above,
  such as a program that opens files from its own code or an option that
  writes a file (`git log --output=<the hook>`), and these the round-9
  verifier found: git's case-insensitive pathspecs (`git rm -r
  ':(icase)SCRIPTS/quality/hooks'`, `GIT_ICASE_PATHSPECS=1`), `git worktree
  add --orphan`, copying a folder named `scripts` into the repository root
  (`cp -r /tmp/scripts .`), `tar -xf` into the current folder, and a path
  through `..` (`rm -rf ../rikurinode/scripts`) — for the hook's folder,
  the sandbox's write protection is meant to stop them (its drill saw it
  refuse a direct write, not these forms); a node tool named through a variable or a word the shell
  assembles (`T=lnc; ${T}li …`, `ln""cli`), or run from a script file the
  guard does not read (`bash /tmp/x.sh`); other words the shell assembles
  (`core.hoo""ksPath`, `$'…'`); a credential file with a generic name
  (`~/.docker/config.json`); git's configuration outside the repository
  (`~/.gitconfig`; `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` point at other
  files, but git keeps the repository's own `hooksPath`). Some forms ask where
  nothing is at risk (`rm -rf /tmp/x/.git`, `tar -tf a.tar -C scripts`, `mv x
  scripts/quality/`, `git restore` of the hook, a `curl -w '…\n'`, a
  `docker inspect` of an image (`docker image inspect` is free), a node
  tool's name in a heredoc's body). The shared `guard.py` judges a command continued onto a second line
  (backslash-newline) one line at a time and splits a command at every `|`,
  so this policy asks before any command continued that way — except a read
  with no redirection — also inside a quoted code string, and before a `>|`
  outside one; it also reads a heredoc's body as commands, so write
  commit messages and documents with the file tools and `git commit -F
  <file>`. The guard and the deny rule apply only to sessions opened in this
  folder.
