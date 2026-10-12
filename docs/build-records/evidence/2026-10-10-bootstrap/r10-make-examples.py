"""Round 10's worked examples: (command, stable, development). Written before the rules."""
import json, sys
O = "/home/junc/rikuri/rikurinode"
P = "/home/junc/rikuri"
NL = "\n"
A, F = "ask", "allow"
E = []
def ex(cmd, stable, dev=None):
    E.append({"tool": "Bash", "input": {"command": cmd}, "expect": stable, "expect_dev": dev or stable})
# 1. process substitution ends the read exemption (round 9's p1-p17)
for c in ["grep x <(lncli sendcoins --addr x --amt 1)", "echo <(lncli sendcoins --addr x --amt 1)",
          "head -1 <(bitcoin-cli stop)", "tail -n1 <(docker stop lnd)", "grep x <(sudo reboot)",
          "echo >(lncli closeallchannels)", "echo =(lncli sendcoins --addr x --amt 1)",
          "less <(rm -rf " + O + ")", "grep x <(systemctl stop docker)", "printf x <(sudo apt-get install -y foo)",
          "grep -c x <(pkill lnd)", "cat <(lncli sendcoins --addr x --amt 1)",
          "git log -1 <(lncli sendcoins --addr x --amt 1)",
          "echo x <(curl -X POST -d '{}' https://localhost:8080/v1/channels)", "grep x <(cp x " + O + "/f)",
          "echo `lncli sendcoins --addr x --amt 1`", "echo $(lncli sendcoins --addr x --amt 1)"]:
    ex(c, A)
ex("diff <(sort a.txt) <(sort b.txt)", F)                       # nothing guarded inside: free
ex("grep -c x <(git log --oneline)", F)
# 2. a node tool, closed-world: asks unless the whole command is a known read
for c in ["lncli updatechanpolicy --base_fee_msat 1000 --fee_rate 0.0001 --time_lock_delta 40",
          "bitcoin-cli settxfee 0.0001", "bitcoin-cli createwallet x", "bitcoin-cli -stdinrpcpass getblockcount",
          "tapcli addrs new --asset_id x --amt 1", "litcli sessions add --label x --type admin",
          "cat <(lncli getinfo)", "/usr/local/bin/lncli sendcoins --addr x --amt 1",
          "lncli --no-macaroons sendcoins getinfo", "lncli getinfo; lncli wallet bumpfee --conf_target 2 x:0",
          "python3 -c 'import subprocess; subprocess.run([\"lncli\", \"getinfo\"])'",
          "lncli getinfo && lncli debuglevel --level debug", "bitcoin-cli -named sendtoaddress address=x amount=1",
          "lncli -n mainnet --rpcserver localhost:10009 sendcoins x 1", "LNCLI=1 lncli getinfo"]:
    ex(c, A)
for c in ["lncli getinfo", "lncli --network=mainnet getinfo", "lncli -n mainnet listchannels",
          "lncli listchannels --active_only", "lncli fwdinghistory --start_time -1w", "lncli walletbalance",
          "lncli pendingchannels", "lncli feereport", "lncli sendcoins --help", "lncli help sendcoins", "lncli --version",
          "lncli getinfo > /tmp/info.json", "lncli getinfo 2>/dev/null", "lncli getinfo | jq .identity_pubkey",
          "bitcoin-cli getblockchaininfo", "bitcoin-cli -rpcwallet=x getbalances", "bitcoin-cli help sendtoaddress",
          "bitcoin-cli -getinfo", "bitcoin-cli getblock 0000abc 2",
          "tapcli assets list", "tapcli assets transfers", "litcli getinfo", "which lncli",
          "echo lncli", "grep -rn 'lncli sendcoins' docs/", "git commit -m 'lncli: read only'"]:
    ex(c, F)
# 3. $HOME as a parameter expansion (round 9's v1-v5)
for c in ['rm -rf "${HOME:?}/rikuri/rikurinode"', "rm -rf ${HOME%/}/rikuri/rikurinode",
          'cd "${HOME:?}/rikuri/rikurinode"', 'cp x "${HOME:?}/rikuri/rikurinode/f"',
          "${HOME:?}/rikuri/rikurinode/scripts/x.sh", "rm -rf ${HOME:-/home/junc}/rikuri/rikurinode"]:
    ex(c, A)
# 4. the listed reads of the previous checkout: options that write or run, and writes into its folder
for c in ["cp -lv %s/x ./x", "cp -sf %s/x ./x", "cp -la %s/x ./x", "cp --lin %s/x ./x", "cp --sym %s/x ./x",
          "cp -rl %s ./old", "cp -sv %s/x ./x", "install -lv %s/x ./x", "tree -aCo %s/x /tmp", "tree -o%s/x /tmp",
          "git -C %s grep -Ovim x", "git -C %s grep -O'sh /tmp/evil.sh' x", "git -C %s grep --open-files=vim x",
          "git -C %s grep -nOvim x", "git grep --no-index -O%s/x.sh x /tmp/f", "git -C %s diff --ext-diff",
          "git -C %s log -p --textconv", "sed -n 1p -e 'w %s/f' /tmp/x", "sed -n 1p -e '1e %s/x.sh' /tmp/x",
          "sed -n '1p;w /tmp/x' %s/f", "sed -n 1p -i %s/f",
          "sort --compress-program=%s/x.sh -S 1K /tmp/f", "rsync -e %s/x.sh /tmp/a h:/tmp/b",
          "scp -S %s/x.sh /tmp/a h:/tmp/b", "install --strip --strip-program=%s/x.sh /tmp/a /tmp/b",
          "scp /tmp/x localhost:%s/f", "rsync -a /tmp/x localhost:%s/f",
          "git commit -F %s/.env", "gh pr create --title x --body-file %s/.env",
          "gh issue create --title x --body-file %s/data/bitcoin/debug.log",
          "cat $( echo %s/x )", "cp x %s/f >> /tmp/log"]:
        ex(c % O, A)
for c in ["sed -n 1p -i %s/x", "sort -o %s/x /tmp/f", "echo x > %s/x", "cat /tmp/f >> %s/rikurinode-old/x",
          "cp -r /tmp/rikurinode %s/", "rsync -a /tmp/rikurinode %s/", "cp /tmp/x %s/y", "cp x %s/x/../rikurinode/f",
          "printf x > %s/rikurinode-new", "ls " + O + " > %s/x"]:
    ex(c % P, A)
ex("cp -r /tmp/rikurinode ~/rikuri", A)
for c in ["cp %s/README.md docs/", "sed -n '1,20p' %s/README.md", "git -C %s show HEAD:README.md",
          "sudo cat %s/README.md", "[ -f %s/README.md ]", "sed -n -E '1,5p' %s/README.md", "ag x %s/README.md",
          "git -C %s grep -n lncli", "git -C %s log --oneline -3", "cat %s/README.md > /tmp/readme.md",
          "rsync -a %s/scripts/ /tmp/old-scripts/"]:
    ex(c % O, F)
ex("ls /home/junc/rikuri.bak", F)
# 5. a continued line asks (until the shared guard joins it), whatever the command
for c in ["shred -u \\" + NL + "scripts/quality/hooks/pre-commit", "echo x | tee \\" + NL + "scripts/quality/hooks/pre-commit",
          "truncate -s0 \\" + NL + "scripts/quality/hooks/pre-commit", "dd if=/dev/null \\" + NL + "of=scripts/quality/hooks/pre-commit",
          "unlink \\" + NL + "scripts/quality/hooks/pre-commit", "vim \\" + NL + "scripts/quality/hooks/pre-commit",
          "rm -rf \\" + NL + "scripts", "shred -u \\" + NL + O + "/f", "sh -c 'git push --force origin x' \\"]:
    ex(c, A)
ex("echo a \\" + NL + "b", F)
# 6. round 8's surviving mutants, pinned (they ask today)
for c in ["rm -rf (scripts)", "cp -tscripts/quality/hooks x", "rm -rf scripts//quality",
          "python3 -c 'import os; os.system(\"cp /bin/true scripts/quality/hooks/pre-commit | cat\")'",
          "( cp /bin/true .git/hooks/pre-commit )", "find scripts -okdir rm {} +", "./rm -rf scripts",
          "echo scripts/quality/hooks/pre-commit | xargs sed -i s/a/b/"]:
    ex(c, A)
json.dump(E, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
print(len(E), "examples")
