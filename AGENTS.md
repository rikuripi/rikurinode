# Rikuri Node — Agent Standard Work

> **Two checkouts, two letters apart.** This repository is
> `/home/junc/rikuripi/rikurinode` (github.com/rikuripi/rikurinode). The
> previous rikurinode at `/home/junc/rikuri/rikurinode`
> (github.com/hchengit/rikurinode) runs the **live mainnet node** on this
> machine. Read it by absolute path only (`cat`, `sed -n`,
> `git -C … log|show|diff|grep`). Never enter it, run anything in it, or change
> it: the guard asks the owner first. "rikurinode" in
> `.agents/workflows/BUILD-PROCEDURE.md` means that previous repository.

Rikuri Node is a self-hosted Bitcoin and Lightning node for people who are not
system administrators: a full node (x86, Intel N150) and a pruned node
(Raspberry Pi 5, 8 GB), both on Fedora IoT, updated and rolled back as whole
images. **Status: bootstrap. There is no node code yet.**

## Priorities (owner, 2026-10-10)

1. Security and reliability.
2. Ease of use and of maintenance: a novice should never need a command line.

Evidence decides. Code works when tests, independent verification and observed
results say so, never because it looks right. Keep code tight and fit for an
expert audit. The previous repository is a source of lessons and proven parts,
ported with their tests, not copied wholesale.

## Standard work

- `.agents/workflows/BUILD-PROCEDURE.md` is binding: the Five Laws, the
  per-change loop, the scrap taxonomy, the incident procedure, the release
  gate. One Build Record per change, from
  `.agents/workflows/BUILD-CHECKLIST-TEMPLATE.md`, at
  `docs/build-records/YYYY-MM-DD-<slug>.md`, begun during planning.
- Read `git status` first. Stage only your own change; never commit another
  session's work.
- Changes land on `main` by pull request; the `Full gate (Ubuntu)` check must
  pass. Verify with the `verifier` subagent; review per [REVIEW.md](REVIEW.md).
- Every behaviour-changing default is put to the owner as an explicit, costed,
  reversible choice. Ask the owner about conflicts, design decisions and
  security; otherwise proceed.

## Deterministic gates

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
  command that does not list the host is refused, with no prompt), and cannot read
  the previous checkout's `.env` and `data/` or `/run/rikuri`, or the owner's
  credential files (`~/.ssh`, `~/.config/gh`, `~/.git-credentials`,
  `~/.docker`, Claude Code's `~/.claude/.credentials.json`; owner, D25,
  2026-10-12: a crate's build script runs inside the sandbox, and reads are
  otherwise open). A plain `cargo` fails when it must download (the sandbox
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
  in this folder itself; crates.io's two hosts and the D25 read denies
  (proven only outside the sandbox: a crate fetched through a proxy that
  allowed only the sandbox's hosts; the first sandboxed fetch and a refused
  read of a credential file are B0's first steps). Inside the sandbox, paths it protects that do not
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
- Fixing a defect: write the failing test, see it fail, then
  `python3 .claude/hooks/guard.py fix-lock on <build-record>`; tests are
  read-only until the lock is released as its own step.
- `scripts/quality/full-gate.sh` is the one gate, run locally and by CI.
  Install the pre-commit hook once per clone:
  `git config core.hooksPath scripts/quality/hooks`. With the sandbox's
  drill and a protected `main`, CI's full gate on every pull request is the
  last boundary.

## Never in git

Checked by `scripts/quality/repo_hygiene.py` in the gate and the pre-commit
hook: logs; runtime state (`data/`, `backups/`, databases); secrets and
credentials (`.env`, macaroons, `wallet.db`, `channel.backup`, cookies, keys);
build output; models; archives; files over 1 MiB; container images without a
version tag (`latest`, `stable`, `lts` and other tags without a number
float; an image needs at least a major.minor version or a digest, and a
distribution release such as `fedora:41` a digest). The secret list is the
guard's own, so the two never drift; node configs are tracked only as
`*.conf.template`, because a live `bitcoin.conf` or `lnd.conf` holds
credentials (the previous repository leaked a Tor password from one). A node's own state, including the versions it upgraded to,
lives on the node. An update never changes or downgrades it.

## Design rules (lessons of the previous repository)

- Roll back software, never data. Never restore an old LND channel database:
  an outdated channel state can lose that channel's funds. Funds safety is the
  seed and the static channel backup kept off the node, plus a restore drill a
  novice can follow.
- Nothing important fails silently; watch for the absence of success
  (last-success times, heartbeats). A fallback is visible, never a quiet save.
- Runtime truth over declared truth: versions and status come from the running
  process, not from a tag, a cache or a config file.
- Every dependency and image pinned; lockfiles committed.
- Proposed, to be decided in the architecture plan: settings changes arrive
  only through tested updates; an in-app upgrade changes a version, nothing
  else.

## Security baseline

From the owner's AI-security briefing (2026-10-10) and Rikuri-PI's adopted
direction (AISecurity policy, OpenShell enforcement):

Requirements for the code to come; none of it exists yet:

- The assistant plans; it never holds authority. Hard limits are enforced
  outside the model. Outbound network must be denied by default, with an
  explicit allow-list (no URL shorteners, no open resolvers), and tool scope
  fixed per task.
- Stop when blocked: a denied tool call must end the attempt and be reported;
  a retry through another tool must be logged and alerted.
- Keys, seeds, macaroons and L402 credentials never enter an agent's context.
  Signing and payments stay in deterministic code behind a secrets store.
  Payments above an owner-set amount need the owner's approval. No single
  component holds untrusted input, outside communication and payment
  authority together.

## Testing on this machine

This machine runs the live node. No test may reach its Docker, systemd, network
services or processes. CI is the reference run. Run every local test through
`scripts/quality/safe-run.sh <command>`: private namespaces (an empty `/run`,
so no runtime or systemd socket; no network but an empty loopback; a private
process list), refusing stand-ins first on `PATH`, `DOCKER_HOST` at a missing
socket, and the node's container start times compared before and after (a
change fails the run; inside Claude Code's sandbox it sees no container and
says it compared nothing). Without namespace support it refuses, unless
`SAFE_RUN_ALLOW_NO_NAMESPACE=1` (CI only: no live node there). What it does
not cover: Unix sockets bound outside `/run` (a desktop's, an editor's, under
`/tmp` or the home folder) stay reachable, and files stay writable — the layer
keeps tests away from the node, it is not a general sandbox. The new stack never runs here:
integration and Lightning tests run on regtest and signet in isolated
environments, then on the N150 and the Pi.

## Knowledge layer

The help pages the assistant answers from, and the runbooks, change in the
same change as the behaviour they describe. A user-visible change without them
is not done.

## Verification by maturity

Now (bootstrap): the full gate runs the guard tests, the quality tools' own
tests, the hygiene check, shell lint, a whitespace check and the secret scan
of history. The
language's build, lint, type and test steps, the smoke script and the debt
ratchet join with the first code. Pass, Fail and Not yet proven stay distinct;
nothing is called green until it has been observed.
