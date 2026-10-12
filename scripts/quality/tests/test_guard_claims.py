"""AGENTS.md > Deterministic gates, as tests: every command form it lists,
against every path spelling it names, asks in both profiles; copying into
scripts/quality asks in stable only; the lookalikes it leaves free stay free.
A form added to AGENTS.md is added here, and the other way round.
Record: docs/build-records/2026-10-10-bootstrap.md (rounds 8 and 10)
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, ".claude", "hooks"))
import guard  # noqa: E402

CFG = guard.load_config()

# --- the path spellings AGENTS.md names ---------------------------------------------
OLD_FILES = ["/home/junc/rikuri/rikurinode/f", "~/rikuri/rikurinode/f", "~junc/rikuri/rikurinode/f",
             "$HOME/rikuri/rikurinode/f", "${HOME}/rikuri/rikurinode/f", "/home/*/rikuri/rikurinode/f",
             '"${HOME:?}/rikuri/rikurinode/f"', "${HOME%/}/rikuri/rikurinode/f"]
OLD_DIRS = ["/home/junc/rikuri/rikurinode", "~/rikuri/rikurinode", "$HOME/rikuri/rikurinode",
            '"${HOME:?}/rikuri/rikurinode"', "${HOME:-/home/junc}/rikuri/rikurinode"]
OLD_PARENTS = ["/home/junc/rikuri", "~/rikuri", "/home/junc/rikuri/", "/home/junc/rikuri/*",
               "/home/junc/rikuri/**", "/home/junc/rikuri{,.bak}"]
HOOK_FILES = ["scripts/quality/hooks/pre-commit", "./scripts/quality/hooks/pre-commit", ".git/config",
              ".git/hooks/pre-commit", "/home/junc/rikuripi/rikurinode/scripts/quality/hooks/pre-commit",
              "~/rikuripi/rikurinode/.git/config", "$PWD/.git/hooks/pre-commit", "scripts/quality/hooks/*"]
HOOK_DIRS = ["scripts/quality/hooks", ".git/hooks", "/home/junc/rikuripi/rikurinode/.git/hooks"]
FOLDERS = ["scripts", "scripts/quality", ".git", "scripts/", "scripts/*", "scripts/**", "scripts{,.off}",
           "/home/junc/rikuripi/rikurinode/scripts", "~/rikuripi/rikurinode/.git", "$PWD/scripts/quality",
           "././scripts", ".//scripts/quality", "~+/scripts", "~+/.git", '"$(git rev-parse --show-toplevel)/scripts"',
           ":/scripts", "':(top)scripts/quality'", '"${PWD:?}/scripts"', '"${PWD%/}/.git"', "${PWD:?}/scripts/quality",
           "`pwd`/scripts"]

# --- the forms AGENTS.md lists ----------------------------------------------------------
FILE_FORMS = ["rm -f {t}", "rmdir {t}", "mv {t} /tmp/x", "rename s/a/b/ {t}", "shred -u {t}", "chmod -x {t}",
              "chown nobody {t}", "chgrp nobody {t}", "echo x | tee {t}", "touch {t}", "truncate -s0 {t}",
              "ln -sf /tmp/x {t}", "dd if=/tmp/x of={t}", "unlink {t}", "mkdir -p {t}", "patch {t} x.diff",
              "split -b 1k x {t}", "csplit -f {t} x 1", "vi {t}", "vim {t}", "nvim {t}", "nano {t}", "ed {t}",
              "emacs {t}", "ex {t}", "pico {t}", "micro {t}", "gvim {t}", "vimdiff {t} x", "view {t}",
              "emacsclient {t}", "joe {t}", "code {t}", "mcedit {t}", "hx {t}", "kate {t}", "gedit {t}", "subl {t}",
              "jed {t}", "sed -i s/a/b/ {t}", "perl -pi -e s/a/b/ {t}", "awk -i inplace 1 {t}",
              "gawk -i inplace 1 {t}", "cp x {t}", "cp x {t} 2>/dev/null", "cp x {t} &>/dev/null", "cp x {t} -f",
              "cp x {t} --backup=numbered", "cp x {t} -S .bak", "cp x {t} &", "cp x {t} # note",
              "install -m 644 x {t}", "rsync -a x {t}", "scp h:x {t}", "curl -o {t} https://e.x/y",
              "curl --output {t} https://e.x/y", "curl -sSLo {t} https://e.x/y", "wget -O {t} https://e.x/y",
              "wget --output-document={t} https://e.x/y", "sort -o {t} x", "sort --output={t} x", "echo x > {t}",
              "echo x >> {t}", "echo x >| {t}", "sudo rm -f {t}", "/bin/rm -f {t}", "sudo -u root cp x {t}"]
DIR_FORMS = ["tar -xf a.tar -C {t}", "tar -xf a.tar -C{t}", "tar -xf a.tar --directory={t}",
             "tar -xf a.tar --directory {t}", "gtar -xf a.tar -C {t}", "bsdtar -xf a.tar -C {t}",
             "unzip a.zip -d {t}", "unzip a.zip -d{t}", "7z x a.7z -o{t}", "cpio -idm -D {t} < a.cpio",
             "cp -t {t} x", "cp --target-directory={t} x", "install -t {t} x",
             "rsync -a --delete /tmp/e/ {t}/", "rsync -a --remove-source-files {t}/ /tmp/s/",
             "find {t} -delete", "find {t} -exec rm {{}} +", "find {t} -execdir rm {{}} +", "find {t} -ok rm {{}} ;"]
FOLDER_FORMS = ["rm -rf {t}", "rmdir {t}", "mv {t} /tmp/x", "chmod -R 000 {t}", "chown -R nobody {t}",
                "shred -u {t}", "tar -xf a.tar -C {t}", "unzip a.zip -d{t}", "7z x a.7z -o{t}",
                "rsync -a --delete /tmp/e/ {t}", "find {t} -delete", "find {t} -exec rm {{}} +"]
GIT_PATH_FORMS = ["git rm -r {t}", "git mv {t} /tmp/x", "git checkout HEAD~1 -- {t}", "git restore {t}",
                  "git stash push {t}", "git reset -- {t}"]
GIT_FILE_ONLY = ["git update-index --skip-worktree {t}", "git update-index --assume-unchanged {t}"]
COPY_IN = ["cp x .git/", "cp x .git", "rsync -a /tmp/x/ .git/", "install x .git/", "cp -r /tmp/hooks scripts/quality/",
           "cp -r /tmp/hooks scripts/quality", "rsync -a /tmp/hooks scripts/quality/", "cp -r /tmp/quality scripts/",
           "cp -r ./quality scripts", "cp -r /tmp/x/hooks/ scripts/quality/"]
GIT = ["git -c core.hooksPath=/dev/null commit -m x", "git --config-env=core.hooksPath=X commit -m x",
       "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/x git commit -m x",
       "git commit -n -m x", "git commit --no-verify -m x", "git config include.path /tmp/x",
       "git config alias.ci 'commit -n'", "git config --unset core.hooksPath", "git config --remove-section core",
       "git config --edit", "git sparse-checkout set docs", "git config core.sparseCheckout true",
       "git read-tree -mu HEAD", "git switch --orphan x", "git config core.hooksPath /tmp/h"]
STABLE_ONLY = ["cp x.py scripts/quality/", "cp x.py scripts/quality/ 2>/dev/null", "cp -t scripts/quality x.py"]
# the previous checkout, closed-world: a command that names it and is not a listed read
OLD_NOT_READS = ["cp -l /home/junc/rikuri/rikurinode/x ./x", "cp --link /home/junc/rikuri/rikurinode/x ./x",
                 "cp -s /home/junc/rikuri/rikurinode/x ./x", "install -l /home/junc/rikuri/rikurinode/x ./x",
                 "rsync -a --link-dest=/home/junc/rikuri/rikurinode/ src/ dst/",
                 "find /home/junc/rikuri/rikurinode -fprint /tmp/x", "find /home/junc/rikuri/rikurinode -fls /tmp/x",
                 "tree -o /tmp/x /home/junc/rikuri/rikurinode",  # (find … -ok: DIR_FORMS has it)
                 "rg --pre cat x /home/junc/rikuri/rikurinode/README.md", "git -C /home/junc/rikuri/rikurinode grep -O vim x",
                 "git -C /home/junc/rikuri/rikurinode grep --open-files-in-pager=vim x",
                 "git -C /home/junc/rikuri/rikurinode diff --output=x.diff",
                 "git -C /home/junc/rikuri/rikurinode reflog expire --expire=now --all",
                 "timeout 5 /home/junc/rikuri/rikurinode/scripts/x.sh", "env -i PATH=/bin /home/junc/rikuri/rikurinode/x",
                 "nice -n 5 cat /home/junc/rikuri/rikurinode/x", "python3 /home/junc/rikuri/rikurinode/x.py",
                 "cd /home/junc/rikuri", "touch /home/junc/rikuri/x", "cat /home/junc/rikuri/rikurinode/x & rm -rf y",
                 "cat $(ls /home/junc/rikuri/rikurinode)"]
# a read exempt from the money and node rules only when it runs alone
READ_PLUS = ["echo & lncli sendcoins --addr x --amt 1", "grep x f & sudo reboot", "echo & docker stop lnd",
             "echo $(lncli sendcoins --addr x --amt 1)", "echo `lncli sendcoins --addr x --amt 1`",
             "git log -1 & bitcoin-cli stop"]
# round 10: a read plus process substitution (<(…), >(…), zsh's =(…)) is not a read alone
READ_PLUS += ["grep x <(lncli sendcoins --addr x --amt 1)", "echo <(lncli sendcoins --addr x --amt 1)",
              "head -1 <(bitcoin-cli stop)", "tail -n1 <(docker stop lnd)", "grep x <(sudo reboot)",
              "echo >(lncli closeallchannels)", "echo =(lncli sendcoins --addr x --amt 1)",
              "less <(rm -rf /home/junc/rikuri/rikurinode)", "git log -1 <(lncli sendcoins --addr x --amt 1)",
              "printf x <(sudo apt-get install -y foo)", "grep -c x <(pkill lnd)"]
# a read whose option runs a program or writes a file is not a read
READ_PLUS += ["git grep -O'lncli sendcoins --addr x --amt 1' x", "git grep --open-files-in-pager='lncli stop' x",
              "git grep --op='lncli stop' x", "git grep -nO'lncli stop' x", "rg --pre 'lncli sendcoins' x",
              "ag --pager 'lncli sendcoins' x"]
# the previous checkout's listed reads: options that link, run a program or write
OLD_NOT_READS += [c % "/home/junc/rikuri/rikurinode" for c in [
    "cp -lv %s/x ./x", "cp -sf %s/x ./x", "cp -la %s/x ./x", "cp -al %s/x ./x", "cp -sl %s/x ./x", "cp --lin %s/x ./x",
    "cp --sym %s/x ./x", "cp -rl %s ./old", "install -lv %s/x ./x", "tree -aCo %s/x /tmp", "tree -o%s/x /tmp",
    "git -C %s grep -Ovim x", "git -C %s grep -nOvim x", "git -C %s grep --open-files=vim x",
    "git grep --no-index -O%s/x.sh x /tmp/f", "git -C %s diff --ext-diff", "git -C %s log -p --textconv",
    "sed -n 1p -e 'w %s/f' /tmp/x", "sed -n 1p -e '1e %s/x.sh' /tmp/x", "sed -n '1p;e %s/x.sh' /tmp/f",
    "sed -n '1p;w /tmp/x' %s/f", "sed -n 1p -i %s/f", "sort --compress-program=%s/x.sh -S 1K /tmp/f",
    "sort -T %s /tmp/f", "rsync -e %s/x.sh /tmp/a h:/tmp/b", "rsync --rsh=%s/x.sh /tmp/a h:/tmp/b",
    "rsync --rsync-path=%s/x.sh /tmp/a h:/tmp/b", "rsync --log-file=%s/x /tmp/a /tmp/b",
    "scp -S %s/x.sh /tmp/a h:/tmp/b", "scp -o ProxyCommand=%s/x.sh /tmp/a h:/tmp/b",
    "install --strip --strip-program=%s/x.sh /tmp/a /tmp/b", "git commit -F %s/notes",
    "gh pr create --title x --body-file %s/notes", "gh issue create --title x -F %s/data/bitcoin/debug.log",
    "cat $( echo %s/x )", "cp x %s/f >> /tmp/log",
    # round 11 (round 10's verifier: listed in AGENTS.md, held by no test)
    "git commit --file=%s/notes", "git commit --file %s/notes", "git commit -t %s/template",
    "git tag -a v1 -F %s/notes", "cp --symbolic-link %s/x ./x", "rsync -T %s/tmp /tmp/a /tmp/b",
    "rsync --temp-dir=%s/tmp /tmp/a /tmp/b", "rsync -b --backup-dir=%s/old /tmp/a /tmp/b",
    "rsync --partial-dir=%s/p /tmp/a /tmp/b", "rsync --write-batch=%s/b /tmp/a /tmp/b",
    "rsync --copy-dest=%s /tmp/a /tmp/b", "rsync --compare-dest=%s /tmp/a /tmp/b",
    "scp -F %s/ssh_config /tmp/a h:/tmp/b", "scp -J jump %s/x /tmp/b"]]
# round 10: the parent folder of the previous checkout, closed-world for writes
PARENT_FILES = ["/home/junc/rikuri/x", "~/rikuri/x", '"${HOME:?}/rikuri/x"', "/home/junc/rikuri/rikurinode-old/x",
                "/home/junc/rikuri/x/../rikurinode/f", "/home/junc/rikuri/", "~/rikuri"]
PARENT_WRITES = ["echo x > {t}", "echo x >> {t}", "printf x > {t}", "cat /tmp/f >> {t}", "ls /tmp > {t}",
                 "cp /tmp/x {t}", "cp -r /tmp/rikurinode {t}", "rsync -a /tmp/x {t}", "scp /tmp/x localhost:{t}",
                 "rsync -a /tmp/x localhost:{t}", "install -m 644 /tmp/x {t}", "sort -o {t} /tmp/f",
                 "sed -n 1p -i {t}", "cp -t {t} /tmp/x"]
# round 10: a command that names a node or container tool asks unless it is one of the listed reads
NODE_ASKS = ["lncli updatechanpolicy --base_fee_msat 1000 --fee_rate 0.0001 --time_lock_delta 40",
             "lncli debuglevel --level debug", "lncli wallet labeltx x y", "lncli newaddress p2tr", "lncli signmessage x",
             "lncli getdebuginfo", "lncli --no-macaroons getinfo", "bitcoin-cli settxfee 0.0001",
             "bitcoin-cli createwallet x", "bitcoin-cli -stdinrpcpass getblockcount",
             "bitcoin-cli -rpcpassword=x getblockcount", "bitcoin-cli logging", "bitcoin-cli listdescriptors true",
             "tapcli addrs new --asset_id x --amt 1", "litcli sessions add --label x --type admin",
             "litcli sessions list", "chantools sweepremoteclosed", "cat <(lncli getinfo)",
             "/usr/local/bin/lncli getinfo", "LNCLI=1 lncli getinfo", "sudo lncli getinfo", "env lncli getinfo",
             "timeout 5 lncli getinfo", "nohup lncli getinfo", "ssh n150 lncli getinfo",
             "python3 -c 'import subprocess; subprocess.run([\"lncli\", \"getinfo\"])'",
             "lncli getinfo && lncli debuglevel --level debug", "lncli getinfo $(echo x)", "lncli getinfo `echo x`",
             "docker inspect lnd", "docker inspect -f '{{.Config.Env}}' lnd", "docker inspect -f '{{json .}}' lnd",
             "docker compose config", "docker exec lnd lncli getinfo", "docker cp lnd:/root/.lnd/x /tmp/",
             "docker pull x", "docker save lnd -o /tmp/x.tar", "docker stats", "podman generate systemd lnd",
             "podman secret inspect x", "nerdctl ps; nerdctl stop lnd", "docker-compose config",
             "/usr/bin/docker ps -q | xargs docker inspect", "docker container inspect lnd", "podman inspect lnd",
             "docker build -t x .", "journalctl --vacuum-time=1s -u docker",
             # round 11: nerdctl and podman-compose by the node rule alone (the older container rule
             # does not list these subcommands)
             "nerdctl pull x", "nerdctl save x -o /tmp/x.tar", "podman-compose config", "podman-compose pull"]
NODE_READS = ["lncli getinfo", "lncli --network=mainnet getinfo", "lncli -n mainnet listchannels",
              "lncli listchannels --active_only", "lncli fwdinghistory --start_time -1w", "lncli walletbalance",
              "lncli channelbalance", "lncli pendingchannels", "lncli closedchannels", "lncli listpeers",
              "lncli feereport", "lncli listpayments --max_payments 10", "lncli listinvoices", "lncli describegraph",
              "lncli getnetworkinfo", "lncli wallet accounts list", "lncli sendcoins --help", "lncli help sendcoins",
              "lncli --version", "lncli getinfo > /tmp/info.json", "lncli getinfo 2>/dev/null",
              "lncli getinfo 2>&1", "lncli getinfo | jq .identity_pubkey", "bitcoin-cli getblockchaininfo",
              "bitcoin-cli -rpcwallet=x getbalances", "bitcoin-cli help sendtoaddress", "bitcoin-cli -getinfo",
              "bitcoin-cli getblock 0000abc 2", "bitcoin-cli getmempoolinfo", "bitcoin-cli getpeerinfo",
              "bitcoin-cli estimatesmartfee 6", "tapcli assets list", "tapcli assets transfers", "tapcli getinfo",
              "litcli getinfo", "which lncli", "command -v bitcoin-cli", "type docker", "ls -l /usr/local/bin/lncli",
              "echo lncli", "grep -rn 'lncli sendcoins' docs/", "git commit -m 'lncli: read only'", "docker ps",
              "docker ps -a --format '{{.Names}} {{.Status}}'", "docker logs --tail 50 lnd",
              "docker logs --since 1h lnd 2>&1", "docker inspect -f '{{.State.StartedAt}}' lnd bitcoin tor",
              "docker images", "docker version", "docker info", "docker stats --no-stream", "docker network ls",
              "docker volume ls", "docker compose ps", "docker compose logs lnd", "podman ps", "podman pod ps",
              "podman logs lnd", "podman inspect --format '{{.State.Status}}' lnd", "docker --version",
              "docker --help", "cat deploy/docker-compose.yml", "ls deploy/docker", "cat deploy/docker/compose.yml", "systemctl status docker",
              "journalctl -u docker --since today", "docker events --since 1h --until 1m",
              "docker image inspect lightninglabs/lnd:v0.18.3-beta", "docker inspect lnd --format '{{json .Mounts}}'",
              "docker compose -f compose.yml logs -f --tail 50 lnd", "docker compose config --services",
              "bitcoin-cli listdescriptors", "tapcli assets mint batches",
              "nerdctl ps", "nerdctl images", "podman-compose ps", "podman-compose logs lnd"]
# round 10: a command continued onto the next line asks, unless it is a read that writes nowhere
CONTINUED = ([f.format(t="\\\n" + "scripts/quality/hooks/pre-commit") for f in FILE_FORMS]
             + ["rm -rf \\\nscripts", "shred -u \\\n/home/junc/rikuri/rikurinode/f",
                # inside quotes a backslash-newline stays in one segment (a code string)
                "python3 -c 'import os; os.system(\"shred -u \\\nscripts/quality/hooks/pre-commit\")'"])
CONTINUED_FREE = ["echo a \\\nb", "git commit -m x \\\n-m y", "grep -n x \\\ndocs/"]
# the continuation fix: the shared guard reads a command whose last character is
# a backslash as the command it runs — here a force push, which it denies
CONTINUED_DENY = ["sh -c 'git push --force origin x' \\"]
# the lookalikes and reads AGENTS.md leaves free
FREE = ["cp /home/junc/rikuri/rikurinode/README.md docs/", "cat /home/junc/rikuri/rikurinode/README.md",
        "git -C /home/junc/rikuri/rikurinode log -1", "install -m 755 /home/junc/rikuri/rikurinode/x.sh scripts/",
        "rm -rf build/scripts", "rm -rf docs/.git", "rm -f .git/hooks.bak", "mkdir scripts", "touch docs/scripts",
        "cp x.sh scripts/", "tar -tf a.tar", "git sparse-checkout list", "git switch main", "cp .gitignore /tmp/x",
        "git config core.hooksPath scripts/quality/hooks", "curl -o /tmp/f https://e.x/y", "unzip -o a.zip -d /tmp/x",
        "sed -n '1,20p' /home/junc/rikuri/rikurinode/README.md", "sudo cat /home/junc/rikuri/rikurinode/README.md",
        "[ -f /home/junc/rikuri/rikurinode/README.md ]", "sed -n -E '1,5p' /home/junc/rikuri/rikurinode/README.md",
        "ag x /home/junc/rikuri/rikurinode/README.md", "rg x /home/junc/rikuri/rikurinode/README.md",
        "git -C /home/junc/rikuri/rikurinode grep -n lncli", "cat /home/junc/rikuri/rikurinode/README.md > /tmp/r.md",
        "rsync -a /home/junc/rikuri/rikurinode/scripts/ /tmp/old-scripts/", "ls /home/junc/rikuri.bak",
        "diff <(sort a.txt) <(sort b.txt)", "grep -c x <(git log --oneline)", "git log --oneline -3",
        "git log --pretty=format:%h -3", "grep --extended-regexp 'a|b' docs/x.md"]


def cases():
    out = []
    for f in FILE_FORMS:
        out += [(f.format(t=t), "ask", "ask") for t in OLD_FILES + HOOK_FILES]
    for f in DIR_FORMS:
        out += [(f.format(t=t), "ask", "ask") for t in OLD_DIRS + HOOK_DIRS]
    for f in FOLDER_FORMS:
        out += [(f.format(t=t), "ask", "ask") for t in FOLDERS + OLD_PARENTS]
    for f in GIT_PATH_FORMS:
        out += [(f.format(t=t), "ask", "ask") for t in HOOK_FILES + FOLDERS if "{" not in t]
    for f in GIT_FILE_ONLY:
        out += [(f.format(t=t), "ask", "ask") for t in HOOK_FILES]
    out += [(c, "ask", "ask") for c in COPY_IN + GIT + OLD_NOT_READS + READ_PLUS + NODE_ASKS + CONTINUED]
    out += [(f.format(t=t), "ask", "ask") for f in PARENT_WRITES for t in PARENT_FILES]
    out += [(c, "ask", "allow") for c in STABLE_ONLY]
    out += [(c, "allow", "allow") for c in FREE + NODE_READS + CONTINUED_FREE]
    out += [(c, "deny", "deny") for c in CONTINUED_DENY]
    return out


def verdict(cmd, profile):
    event = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": guard.ROOT}
    return guard.decide(event, dict(CFG, profile=profile), guard.ROOT, lock_present=False,
                        branch_fn=lambda _cwd: "feature/x")[0]


# Inputs that make a regular expression backtrack: long runs of options, words,
# path segments, quotes and spaces (verifier round 8: `git -a -a …`, 117
# characters, took 21 s through the hook).
SLOW = ["git" + " -a" * 60, "git" + " -c x" * 40, "docker" + " --a x" * 60, "cp" + " x" * 300, "rm " + "a/" * 600,
        "lncli" + " --x=y" * 80, "echo " + "'" * 400, "x" * 4000, "git commit" + " -m x" * 60,
        "rsync" + " -a" * 100 + " x /home/junc/rikuri/rikurinode/", "tar" + " -xvf" * 80, " " * 3000 + "rm"]
# and a run of options, with and without values, after every command a rule guards
SLOW += [w + run * 60 for w in ("docker", "podman", "systemctl", "http", "git -C /home/junc/rikuri/rikurinode", "curl",
                                "wget", "lncli", "bitcoin-cli", "gh api", "tar", "cp", "rsync", "sed", "find", "apt",
                                "dnf", "pkill", "kill", "xargs", "sudo", "git", "git config", "tapcli", "loginctl")
         for run in (" --a", " --a x", " -a x", " --a=x", " -c -a", " -C -a")]


class Speed(unittest.TestCase):
    def test_every_rule_is_fast(self):
        # Python's re cannot be interrupted, so a rule that backtracks
        # exponentially would hang the test: the searches run in a child
        # process, which fails the test if it does not finish in time.
        import json
        import subprocess
        code = ("import json, re, sys, time\n"
                "rules, inputs = json.load(sys.stdin)\n"
                "slow = []\n"
                "for r in rules:\n"
                "    rx = re.compile(r['regex'])\n"
                "    for s in inputs:\n"
                "        t0 = time.perf_counter(); rx.search(s); dt = time.perf_counter() - t0\n"
                "        if dt > 0.25: slow.append('%.2fs: %s on %s' % (dt, r['reason'][:50], s[:30]))\n"
                "print(json.dumps(slow))\n")
        try:
            out = subprocess.run([sys.executable, "-c", code], input=json.dumps([CFG["funds_patterns"], SLOW]),
                                 capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            self.fail("a rule backtracks: the searches did not finish in 60 s")
        self.assertEqual(json.loads(out.stdout), [], out.stderr)


class Claims(unittest.TestCase):
    def test_every_listed_form(self):
        wrong = ["%s: want stable=%s development=%s, got %s/%s" % (c, s, d, gs, gd)
                 for c, s, d in cases()
                 for gs, gd in [(verdict(c, "stable"), verdict(c, "development"))] if (gs, gd) != (s, d)]
        self.assertGreater(len(cases()), 1000)
        self.assertEqual(wrong, [], "%d of %d claims do not hold:\n" % (len(wrong), len(cases())) + "\n".join(wrong))


if __name__ == "__main__":
    unittest.main()
