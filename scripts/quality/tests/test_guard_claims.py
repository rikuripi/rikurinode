"""AGENTS.md > Deterministic gates, as tests: every command form it lists,
against every path spelling it names, asks in both profiles; copying into
scripts/quality asks in stable only; the lookalikes it leaves free stay free.
A form added to AGENTS.md is added here, and the other way round.
Record: docs/build-records/2026-10-10-bootstrap.md (round 8)
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
             "$HOME/rikuri/rikurinode/f", "${HOME}/rikuri/rikurinode/f", "/home/*/rikuri/rikurinode/f"]
OLD_DIRS = ["/home/junc/rikuri/rikurinode", "~/rikuri/rikurinode", "$HOME/rikuri/rikurinode"]
OLD_PARENTS = ["/home/junc/rikuri", "~/rikuri", "/home/junc/rikuri/", "/home/junc/rikuri/*",
               "/home/junc/rikuri/**", "/home/junc/rikuri{,.bak}"]
HOOK_FILES = ["scripts/quality/hooks/pre-commit", "./scripts/quality/hooks/pre-commit", ".git/config",
              ".git/hooks/pre-commit", "/home/junc/rikuripi/rikurinode/scripts/quality/hooks/pre-commit",
              "~/rikuripi/rikurinode/.git/config", "$PWD/.git/hooks/pre-commit", "scripts/quality/hooks/*"]
HOOK_DIRS = ["scripts/quality/hooks", ".git/hooks", "/home/junc/rikuripi/rikurinode/.git/hooks"]
FOLDERS = ["scripts", "scripts/quality", ".git", "scripts/", "scripts/*", "scripts/**", "scripts{,.off}",
           "/home/junc/rikuripi/rikurinode/scripts", "~/rikuripi/rikurinode/.git", "$PWD/scripts/quality",
           "././scripts", ".//scripts/quality", "~+/scripts", "~+/.git", '"$(git rev-parse --show-toplevel)/scripts"',
           ":/scripts", "':(top)scripts/quality'"]

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
                 "find /home/junc/rikuri/rikurinode -ok rm {} ;", "tree -o /tmp/x /home/junc/rikuri/rikurinode",
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
# the lookalikes and reads AGENTS.md leaves free
FREE = ["cp /home/junc/rikuri/rikurinode/README.md docs/", "cat /home/junc/rikuri/rikurinode/README.md",
        "git -C /home/junc/rikuri/rikurinode log -1", "install -m 755 /home/junc/rikuri/rikurinode/x.sh scripts/",
        "rm -rf build/scripts", "rm -rf docs/.git", "rm -f .git/hooks.bak", "mkdir scripts", "touch docs/scripts",
        "cp x.sh scripts/", "tar -tf a.tar", "git sparse-checkout list", "git switch main", "cp .gitignore /tmp/x",
        "git config core.hooksPath scripts/quality/hooks", "curl -o /tmp/f https://e.x/y", "unzip -o a.zip -d /tmp/x"]


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
    out += [(c, "ask", "ask") for c in COPY_IN + GIT + OLD_NOT_READS + READ_PLUS]
    out += [(c, "ask", "allow") for c in STABLE_ONLY]
    out += [(c, "allow", "allow") for c in FREE]
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
