#!/usr/bin/env python3
"""The source of this repository's guard policy: funds_patterns, secret_globs,
protected_globs and _doc in .claude/hooks/guard-config.json are written from
the definitions below; the worked examples stay in the JSON (they are data).

Edit a rule here, run `guard_policy.py` to rewrite the policy, add worked
examples for the change, and run the guard tests. The full gate runs
`guard_policy.py --check`: the committed policy must equal what this file
writes, so the two cannot drift.

The guard is a tripwire on command text, not a sandbox (AGENTS.md >
Deterministic gates). The rules below always ask, in every profile, because
the machine that develops this repository runs a live mainnet node; GitHub's
rules keep Rikuri-PI's profile behaviour.
Record: docs/build-records/2026-10-10-bootstrap.md
"""
from __future__ import annotations

import json
import os
import sys

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".claude", "hooks", "guard-config.json")

# --- shared fragments ---------------------------------------------------------
# The previous checkout runs the live node: /home/junc/rikuri/rikurinode, in
# every spelling the verifiers found (~, ~junc, $HOME, ${HOME}, /home/*, a quote
# after $HOME, //, /./, a trailing glob, /home//junc), and $HOME as a parameter
# expansion (${HOME:?}, ${HOME%/}, ${HOME:-…}: verifier round 9).
HOME = r"(?:~\w*|\$HOME|\$\{HOME(?:[^}\w][^}]*)?\}|/+(?:\./+)*home/+(?:\./+)*(?:junc|\*))[\"']?"
SEP = r"/+(?:\./)*"
# A folder named as a whole word: optionally with a trailing /, a /* or /**,
# or a brace list ({,.off}, /{a,b}), then the word's end.
WHOLE = r"/?(?:\*\*?|\{[^}\s]*\})?(?=[\s\"';|&)<>]|$)"
OLD = HOME + SEP + r"rikuri" + SEP + r"rikurinod(?:e(?![\w.-])|\*)"
PARENT = HOME + SEP + r"rikuri" + WHOLE
W = r"(?:^|[^\w./-])"                       # a word's start
SUDO = r"(?:sudo\s+(?:-\S+\s+)*)?"           # an optional sudo with its options
CMD = W + SUDO + r"(?:[\w.~/-]*/)?"           # a command, maybe called by its path (/bin/rm)
START = r"(?<![^\s\"'=(])"                    # a path's start: after a space, a quote, = or (
# The folders before a folder's name: git's pathspec magic (:/, :(top)), then
# ./ (repeated), or an absolute path, or one under ~ or ~+, a variable (also as
# a parameter expansion, ${PWD:?}, ${PWD%/}), a $(…) or a backtick. A relative
# path (build/scripts, ../x) is another folder: not matched. (The expansions
# and the backtick asked in round 6 and were lost in round 7: verifier round 9.)
PFX = (r"(?::/|:\([^)\s]*\))?(?:(?:\./+)+|(?:/|~[\w+]*/|(?:\$\w+|\$\{\w+(?:[^}\w][^}]*)?\})[\"']?/"
       r"|\$\([^)]*\)[\"']?/|`[^`]*`[\"']?/)"
       r"(?:[^\s\"';|&<>()]*/)?)?")
# The folders before a file's name: any (the hook's file names are specific
# enough that build/scripts/quality/hooks may ask too).
FPFX = r"(?:[^\s\"';|&<>()]*/)?"
# A redirection: 2>, >>, &>, &>>, >&2, 2>&1, <, each with its target (a >| too:
# its | is taken as the target's first character). guard.py splits a command at
# every | outside quotes, so a bare >| reaches the rules cut in two (the >\s*$
# rule asks); inside a quoted code string it arrives whole.
REDIR = r"(?:[0-9]*|&)[<>]{1,2}&?\s*\S+"
# Options with which a read runs another program or writes a file: git grep's
# -O<program> (in a cluster too, -nOvim) and --open-files-in-pager (any
# abbreviation: --op…), rg's --pre, ag's --pager, git's --output (--ou…),
# --ext-diff and --textconv (verifier round 9).
RUNS = r"\s(?:-[A-Za-z]*O|--(?:op|pre\b|pager\b|ou|ext(?:-d\w*|-)?(?![\w-])|textc))"
# A segment that runs more than its first command: a lone & (guard.py splits at
# ; && || | and newlines, not at &), a $(…), a process substitution — <(…),
# >(…) or zsh's =(…), which guard.py does not read (verifier round 9: `grep x
# <(lncli sendcoins …)`) — or an option in RUNS. (guard.py reads a backtick's
# command itself, and a $(…)'s.)
MORE = r"(?=.*(?:(?<![&>])&(?![&>])|\$\(|[<>=]\(|" + RUNS + r"))"
# A leading lookahead that exempts segments which only read or describe:
# searches, logs, commit and tag messages, PR and issue text, echo, printf —
# unless the segment runs more than that (verifier round 8: `echo & lncli …`).
READS = (r"(?:git\s+(?:-C\s+\S+\s+)?(?:grep|log|show|diff)|git\s+(?:commit|tag)\b"
         r"|gh\s+(?:pr|issue)\s+(?:create|edit|comment)|grep|egrep|fgrep|rg|ag|less|head|tail|echo|printf)\b")
NR = r"^(?:(?!\s*" + READS + r")|" + MORE + ")"
# A command started from code: system(), subprocess.run(), exec…() with a string.
CALL = r"(?:system|popen|run|call|Popen|check_output|check_call|exec[lv]p?e?|spawn\w*)\s*\(\s*\[?\s*\\?[\"']"
GITREADS = (r"(?:log|show|diff|grep|status|blame|ls-files|ls-tree|cat-file|rev-parse|describe|shortlog|reflog"
            r"|help|version)")
LIVE = " — this machine runs the LIVE mainnet node. The owner decides"
# LND, Loop, Pool and Taproot Assets REST paths that change state.
LND_WRITES = (r"/v[12]/(?:transactions|channels|payments|router|wallet|invoices?|chanpolicy|peers|newaddress|psbt"
              r"|funding|switch|macaroon|signer|unlockwallet|initwallet|changepassword|stop)\b")


def dest(target: str) -> str:
    """`target` as a command's last path word: bare or quoted (a quoted path may
    hold spaces), then only redirections, options (with or without a value), `&`,
    a comment, or the command's end — or a closing quote, where it ends a code
    string (`bash -c "cp x <target>"`)."""
    tail = (r"(?=(?:\s*" + REDIR + r"|\s+-\S+(?:\s+[^-\s&|;<>#]\S*)?|\s*&(?![&>]))*"
            r"(?:\s*(?:$|&&|\|\|?|;|\)|#)|[\"']))")
    return (r"\s(?:[\"']?" + target + r"[^\s'\"]*[\"']?|\"" + target + r"[^\"]*\"|'" + target + r"[^']*')"
            + tail)


def writes(target: str, parent: str = "", attached: str = "", attached_parent: str = "") -> list:
    """The command forms that write, edit, move or delete `target` (a regex
    fragment), listed one by one: these and no others. `parent`, if given,
    counts for the commands that delete, move or extract into a whole folder
    (copying into it is how files are ported). `attached` and
    `attached_parent` are the same paths without their start condition, for
    an option that takes its value attached (`-C<dir>`, `-o<dir>`); they
    default to `target` and `parent`. Shared by the previous checkout and the
    pre-commit hook, so the two are covered alike. (A redirect into the target
    is added by the caller, outside the read exemption.)"""
    attached, attached_parent = attached or target, attached_parent or parent
    either = "(?:" + target + ("|" + parent if parent else "") + ")"
    into = "(?:" + attached + ("|" + attached_parent if attached_parent else "") + ")"
    return [
        # the target, or its folder, named anywhere after a command that deletes or moves
        CMD + r"(?:rm|rmdir|mv|rename|shred|chmod|chown|chgrp)\b.*" + either,
        # the target named anywhere after a command that writes
        CMD + r"(?:tee|touch|truncate|ln|dd|unlink|mkdir|patch|cpio|split|csplit|ex|vi|vim|nvim|nano|ed|emacs"
        r"|pico|micro|gvim|vimdiff|view|emacsclient|joe|code|mcedit|hx|kate|gedit|subl|jed)\b.*"
        + target,
        # moved into an archive (zip -m deletes the originals)
        CMD + r"zip\b(?=.*\s-[A-Za-z]*m)" + r".*" + either,
        # edited in place
        r"\bsed\b(?=.*\s(?:-[A-Za-z]*i[A-Za-z]*\b|--in-place)).*\s[\"']?" + target,
        r"\bperl\b(?=.*\s-[A-Za-z]*i).*\s[\"']?" + target,
        r"\b[gm]?awk\b.*(?:-i\s*[\"']?inplace|--include[= ]\s*[\"']?inplace)\b.*" + target,
        # old-style tar (x… without a dash, e.g. tar xfC a.tar <dir>): the folder anywhere after it
        CMD + r"(?:g|bsd)?tar\s+[A-Za-z]*x[A-Za-z]*\s.*" + either,
        # extracted into (-C, -d, -D, --directory, 7z's -o; in a cluster of options
        # such as -xvC or -qod; the value attached or not)
        CMD + r"(?:g|bsd)?(?:tar|unzip|7z[ar]?|7zz|cpio)\b.*(?:-[A-Za-z]*[CdD]\s*|--directory[= ]\s*|-[A-Za-z]*o)"
        r"[\"']?" + into,
        # the destination: the last path word of cp, install, rsync and scp, or their -t
        CMD + r"(?:cp|install|rsync|scp)\b.*" + dest(target),
        CMD + r"(?:cp|install)\b.*(?:\s-[A-Za-z]*t\s*|--target-directory[= ])[\"']?" + attached,
        CMD + r"rsync\b(?=.*--(?:delete\S*|remove-source-files)).*" + either,
        # written by an output option
        r"\b(?:curl|wget)\b.*(?:\s-[A-Za-z]*[oOP]\s*|--output(?:-document|-dir)?[= ]\s*|--directory-prefix[= ]\s*)"
        r"[\"']?" + into,
        r"\bsort\b.*(?:\s-[A-Za-z]*o\s*|--output[= ]\s*)[\"']?" + attached,
        # deleted or changed by find
        r"\bfind\b.*" + either + r".*\s-(?:delete|exec|execdir|ok|okdir)\b"]


def rx(*alternatives: str) -> str:
    """Any of the alternatives, anywhere in a segment that is not a read."""
    return NR + r".*?(?:" + "|".join(alternatives) + ")"


RULES = []


def rule(regex: str, reason: str, always_ask: bool = True) -> None:
    RULES.append({"regex": regex, "reason": reason, "always_ask": always_ask})


# --- the previous checkout ------------------------------------------------------
rule(rx(W + r"(?:pushd|cd)(?:\s+-\S*)*(?:\s|\\n?)+[\"']?" + OLD),
     "enters the previous rikurinode checkout, where the LIVE node runs — this repository only reads it by "
     "absolute path or git -C … log/show/diff/grep. The owner decides")
rule(rx(r"(?:^\s*[\"']?|[;&|`]\s*[\"']?|\(\s*|" + CALL + r")" + SUDO
        + r"(?:(?:nohup|exec|source|\.|env(?:\s+\w+=\S*)*)\s+)*" + OLD + r"/",
        W + SUDO + r"(?:\S*/)?(?:bash|sh|zsh|dash|python3?|perl|ruby|node|nohup|source|env|xargs|watch|timeout)"
        r"(?:\s+-\S+)*\s+[\"']?" + OLD,
        W + SUDO + r"(?:\S*/)?(?:docker|docker-compose|podman|nerdctl|make|npm|npx|pnpm|yarn|cargo|just|uv|uvx"
        r"|poetry|go|deno|bun|systemctl)\b.*" + OLD),
     "runs a program in or from the previous rikurinode checkout, where the LIVE node runs. The owner decides")
rule(rx(r"\bgit\s+(?=[^|;&]*?(?:-C\s+|--git-dir[= ]|--work-tree[= ])[\"']?" + OLD + r")"
        r"(?:(?:-C|-c|--git-dir|--work-tree|--namespace)\s+[^-\s]\S*\s+|-[\w-]+(?:=\S+)?\s+)+(?!" + GITREADS + r"\b)\w",
        r"\bgit\s+(?=[^|;&]*?-C\s+[\"']?" + OLD + r")(?=[^|;&]*\s-c\s)",
        r"\bgit\s+(?:-\S+\s+)*-C\s+[\"']?" + OLD + r"\S*\s+\\",
        r"\bGIT_(?:DIR|WORK_TREE)=[\"']?" + OLD,
        r"\bgit\b.*\b(?:clone|init|worktree\s+add)\b.*\s[\"']?" + OLD),
     "git command that changes the previous rikurinode checkout (only log/show/diff/grep and other reads are free; "
     "a -c option can run a program)")
# anything under the parent folder, the previous checkout included (not rikuripi, this repository's parent)
PARENT_TREE = HOME + SEP + r"rikuri(?![\w.-])"
# A copy's destination may name a host (scp/rsync host:path); this machine may be the host.
HOST = r"(?:[\w.@-]+:[\"']?)?"
rule(rx(*writes(OLD, PARENT),
        # anything in the parent folder as a copy's destination (round 10: `cp -r /tmp/rikurinode
        # /home/junc/rikuri/` overwrote the checkout's files in the verifier's scratch copy)
        CMD + r"(?:cp|install|rsync|scp)\b.*" + dest(HOST + PARENT_TREE),
        CMD + r"(?:cp|install)\b.*(?:\s-[A-Za-z]*t\s*|--target-directory[= ])[\"']?" + PARENT_TREE,
        r"\bsort\b.*(?:\s-[A-Za-z]*o\s*|--ou\w*[= ]\s*)[\"']?" + PARENT_TREE)
     + r"|(?:>\||>>?)\s*[\"']?" + PARENT_TREE,
     "writes, edits, moves or deletes files in the previous rikurinode checkout or its parent folder, where the LIVE "
     "node runs. The owner decides")
# Closed-world (round 9): any command that names the previous checkout asks,
# unless it is one of these reads, alone in its segment — or a copy out of it
# (cp, install, rsync, scp: judged by the rule above). An option that links,
# runs a program or writes a file ends the exemption: here, or in RUNS (MORE).
OLD_READS = (r"(?:(?:cat|less|more|head|tail|wc|ls|stat|file|diff|cmp|sha\d*sum|md5sum|b2sum|du|readlink|realpath"
             r"|basename|dirname|grep|egrep|fgrep|jq|test|strings|echo|printf|rg|ag)\b|\["
             # sort without -T or --compress-program (round 10; -o into the parent folder: the rule above)
             r"|sort\b(?![^|;&]*\s(?:-[A-Za-z]*T|--(?:com|te)\w*))"
             r"|tree\b(?![^|;&]*\s(?:-[A-Za-z]*o|--o\w*))"
             r"|find\b(?![^|;&]*\s-(?:delete|exec|execdir|ok|okdir|fprint\w*|fls)\b)"
             # sed -n '<lines>p' and then only file names, to the end (round 10: -e 'w …', -i)
             r"|sed\s+-n\s+(?:-E\s+)?(?:'[\d,$]+p'|\"[\d,$]+p\"|[\d,$]+p)(?:\s+[^\s;|&<>`$()'\"-][^\s;|&<>`$()'\"]*)+"
             r"\s*(?:[0-9]*>{1,2}\s*[^\s;|&<>()]+\s*)?$"
             # git reads there (no -c, which can run a program)
             r"|git\s+-C\s+[\"']?\S+\s+(?:--no-pager\s+|--no-optional-locks\s+)*(?:log|show|diff|grep|status|blame"
             r"|ls-files|ls-tree|cat-file|rev-parse|describe|shortlog)\b"
             # text that names it: a commit or tag message (not from a file), a search here, a PR or issue
             # (not a body read from a file: it would be posted)
             r"|git\s+(?:commit|tag)\b(?![^|;&]*\s(?:-[A-Za-z]*[Ft]|--(?:fi|te)\w*))|git\s+grep\b"
             r"|gh\s+(?:pr|issue)\s+(?:create|edit|comment)\b(?![^|;&]*\s(?:-[A-Za-z]*F|--body-file))"
             # copies out of it, judged by the rule above: never as a link, never running a program
             # (cp -l/-s/--link/--symbolic-link in any cluster or abbreviation; install -s/--strip-program;
             # rsync -e/--rsh/--rsync-path, its files written elsewhere, --link-dest; scp -S/-o/-F/-J)
             r"|(?:cp|install)\b(?![^|;&]*\s(?:-[A-Za-z]*[ls]|--(?:l|sy|st)\w*))"
             r"|rsync\b(?![^|;&]*\s(?:-[A-Za-z]*[eT]|--(?:rs|link-d|log-f|te|backup-d|partial-d|write-b|only-w"
             r"|copy-d|compare-d)\w*))"
             r"|scp\b(?![^|;&]*\s-[A-Za-z]*[SoFJ]))")
rule(r"^(?:(?!\s*(?:sudo\s+)?" + OLD_READS + r")|" + MORE + r")(?=.*" + PARENT_TREE + r")",
     "names the previous rikurinode checkout, or anything in its parent folder, where the LIVE node runs, in a command "
     "that is not one of the reads "
     "this repository allows there (cat, less, head, tail, grep, ls, diff, find without -delete or -exec, sed -n, "
     "git -C … log/show/diff, …) or a copy out of it. The owner decides")

# --- containers, services and the host --------------------------------------------
rule(rx(r"\b(?:docker|podman|nerdctl)\b[\"']?(?:\s+compose|-compose)?(?:\s+-[\w-]+(?:=\S+|\s+[^-\s]\S*)?)*\s+"
        r"(?:up|down|stop|restart|kill|rm|rmi|create|start|pause|unpause|run|exec|attach|cp|update|rename|commit"
        r"|export|import|scale|watch|system\s+prune|volume\s+(?:rm|prune|create)"
        r"|network\s+(?:rm|prune|create|connect|disconnect)|image\s+(?:rm|prune)"
        r"|container\s+(?:start|stop|restart|kill|rm|prune|create|run|exec|attach|cp|pause|unpause|update|rename"
        r"|commit|export)|pod\s+(?:start|stop|restart|kill|rm|create|pause|unpause)|(?:kube|play)\s+(?:play|down|kube)"
        r"|swarm\s+(?:init|join|leave)|service\s+(?:create|rm|update|scale)|stack\s+(?:rm|deploy)"
        r"|plugin\s+(?:disable|enable|rm|install|upgrade)|checkpoint\s+(?:create|rm))\b",
        r"\b(?:docker|podman)(?:-compose|\s+compose)\b.*\b(?:up|down|stop|restart|kill|rm|start|create|run|exec|scale"
        r"|watch|pause)\b"),
     "starts, stops, removes, copies or enters a container" + LIVE
     + " (its containers: bitcoin, lnd, tor, …); this repository never runs containers here")
rule(rx(W + SUDO + r"(?:ctr|runc|crun|nsenter|containerd-shim\S*)\b", r"(?:docker|podman|containerd)\.sock\b"),
     "drives the container runtime directly (its socket, ctr, runc, nsenter)" + LIVE)
rule(rx(r"\bsystemctl\b(?:\s+-[\w-]+(?:=\S+)?)*\s+(?:start|stop|restart|reload|try-restart|reload-or-restart|kill"
        r"|enable|disable|mask|unmask|isolate|reboot|poweroff|halt|kexec|suspend|hibernate|rescue|emergency"
        r"|daemon-reload|set-property|edit|revert|link|preset)\b",
        r"\bloginctl\s+(?:reboot|poweroff|halt|suspend|hibernate|terminate-\w+|kill-\w+)\b",
        r"(?:^|[;&|(`\"']\s*)" + SUDO + r"(?:reboot|shutdown|poweroff|halt)\b",
        r"(?:^|[;&|(`\"']\s*)" + SUDO + r"(?:init|telinit)\s+[0-6sSqQ]\b"),
     "changes a service or the machine's power state (systemctl, loginctl, reboot, init)" + LIVE)
rule(rx(W + SUDO + r"(?:apt|apt-get|aptitude|dpkg|snap|rpm-ostree|dnf|yum|zypper|pacman)\s+(?:-\S+\s+)*"
        r"(?:install|upgrade|dist-upgrade|full-upgrade|remove|purge|autoremove|reinstall|refresh|rebase|rollback"
        r"|deploy|-i|-r|-P)\b"),
     "changes the host's system packages — on this machine the LIVE node's host (a Linux update deadlocked the node, "
     "2026-10-09). The owner decides")
rule(rx(W + SUDO + r"(?:pkill|killall)\b.*\b(?:lnd|lncli|bitcoind|tapd|dockerd|containerd|tor|electrs)\b",
        r"\bkill\b.*(?:\$\(|`)\s*(?:pidof|pgrep)\b",
        r"\bxargs\b(?:\s+-\S+)*\s+(?:sudo\s+)?kill\b",
        r"\bkill\b(?:\s+-\S+)*\s+1(?=[\s\"']|$)"),
     "kills node daemons, the container runtime, or processes found by name or PID 1" + LIVE)

# --- money and keys -------------------------------------------------------------------
LNCLI_MONEY = ["sendcoins", "sendmany", "sendpayment", "payinvoice", "sendtoroute", "openchannel", "batchopenchannel",
               "closechannel", "closeallchannels", "abandonchannel", "unlock", "changepassword", "create",
               "updatechanpolicy", "fundpsbt", "finalizepsbt", "publishtx", "bumpfee", "bumpclosefee",
               "bumpforceclosefee", "leaseoutput", "releaseoutput", "restorechanbackup", "deletepayments",
               "createwatchonly", "exportchanbackup", "bakemacaroon", "deletemacaroonid", "settleinvoice",
               "cancelinvoice"]
rule(NR + r"(?!.*\s(?:--help|-h)\b)(?!.*\blncli\s+help\b).*?\blncli\b.*\b(" + "|".join(LNCLI_MONEY) + r")\b",
     "lncli command that moves funds, changes channels or credentials, or stops LND — owner approves")
rule(rx(r"\blncli\b.*\b(?:psbt\s+(?:fund|finalize|publish)|updatechanstatus|accounts\s+import|importpubkey)\b"),
     "lncli command that funds, signs or broadcasts a transaction, or changes a channel — owner approves")
BTC_MONEY = [r"send\w*", r"walletpassphrase\w*", "dumpprivkey", "dumpwallet", "importprivkey", "importdescriptors",
             "importwallet", "sethdseed", "encryptwallet", "createwallet", "unloadwallet", "backupwallet",
             "restorewallet", "bumpfee", "psbtbumpfee", "abandontransaction", "lockunspent", "walletprocesspsbt",
             "pruneblockchain", "invalidateblock", "setnetworkactive", "rescanblockchain", "setban", "disconnectnode",
             "reconsiderblock", "preciousblock", "importmulti", "importaddress", "importpubkey", "migratewallet"]
rule(NR + r"(?!.*\bbitcoin-cli\s+(?:-\S+\s+)*help\b).*?\bbitcoin-cli\b.*\b(" + "|".join(BTC_MONEY) + r")\b",
     "bitcoin-cli command that spends, exposes keys, or changes the node's chain or network state — owner approves")
rule(rx(r"\bbitcoin-cli\b.*\b(?:listdescriptors\b.*\b(?:true|private=true)\b|gethdkeys\b.*\bprivate=true\b)",
        r"\bbitcoin-cli\b(?:\s+-\S+)*\s+-stdin\b"),
     "prints private keys, or reads its arguments where the guard cannot see them (-stdin) — owner approves")
rule(rx(r"\blncli\b.*\bstop\b"), "stops LND" + LIVE)
rule(rx(r"\bbitcoin-cli\b.*\bstop\b"), "stops bitcoind" + LIVE)
rule(rx(r"\btapcli\b.*\b(?:send|mint(?!\s+batches)|burn|finalize)\b"), "tapcli asset send/mint/burn — owner approves")
rule(r"\brm\b.*(\.lnd\b|lnd[-_]?data|\.bitcoin\b|bitcoin[-_]?data|\.tapd\b|tapd[-_]?data|channel\.backup|wallet\.db"
     r"|chainstate)", "deletes wallet / channel / chain data — owner approves")
rule(rx(r"\bcurl\b(?=.*(?:\s-X\s*|\s--request[= ]?\s*)(?:POST|PUT|DELETE|PATCH)\b|.*\s(?:-d|--data(?:-raw|-binary"
        r"|-urlencode)?|--json|-F|--form)\b).*" + LND_WRITES,
        r"\bwget\b(?=.*--(?:post|put|delete)-|.*--method[= ]?(?:POST|PUT|DELETE)).*" + LND_WRITES,
        r"\bhttp(?:ie|s)?\b(?:\s+-[\w-]+(?:=\S+)?)*\s+(?:POST|PUT|DELETE|PATCH)\b.*" + LND_WRITES,
        r"\brequests\.(?:post|put|delete|patch)\s*\(.*" + LND_WRITES,
        r"\bgrpcurl\b.*\b(?:lnrpc|routerrpc|walletrpc|signrpc|invoicesrpc|chainrpc|looprpc|poolrpc|taprpc)\b"),
     "a write to LND's (or Loop's, Pool's, Taproot Assets') API — payments, channels, on-chain sends, keys — "
     "owner approves")
rule(rx(r"(?<![\w.-])(?:wallet\.dat|wallet\.db|macaroons\.db|channels?\.backup|[\w-]+\.macaroon|hs_ed25519_secret_key"
        r"|control_auth_cookie|aezeed[\w.-]*\.txt|wallet_password[\w.-]*|seed\.txt)"
        r"(?:\.(?:bak|old|orig|gz|b64|hex|\d)[\w.-]*)?(?![\w.-])"),
     "names one of the node's key files (wallet, macaroons, channel backup, onion key, seed) — its contents must not "
     "leave the node; the owner decides")
rule(rx(r"--(?:macaroonpath|macaroon-path|macaroon)\b"),
     "hands a macaroon (an LND credential) to a command — owner approves")
rule(rx(r"\b(?:loop\s+(?:out|in)|pool\s+(?:orders\s+submit|accounts\s+(?:new|deposit|withdraw|close|renew)))\b"),
     "Lightning Loop or Pool operation that moves funds — owner approves")
rule(rx(r"\bxargs\b.*\b(?:lncli|bitcoin-cli|tapcli|loop|pool)\b"),
     "feeds commands to a node CLI that the guard cannot see one by one — owner approves")
rule(rx(r"\b(?:tar|zip|7z|rsync|scp|cp)\b.*(?:\.lnd|\.bitcoin|\.tapd|lnd[-_]?data|bitcoin[-_]?data|tapd[-_]?data"
        r"|/var/lib/rikuri)(?:/|\b)"),
     "copies or archives the node's wallet, key or channel folders — owner approves")

# --- node and container tools, closed-world (owner, 2026-10-11) ---------------------------
# The rules above list what moves money; each review found a form they missed
# (round 9: `grep x <(lncli sendcoins …)`). So a command that names a node or
# container tool asks unless it is, alone in its segment and whole, one of the
# reads below: named as a word anywhere — called by a path, after sudo, env,
# timeout or ssh, inside quotes or code, in a process substitution — but not
# inside a longer name (lncli.md, docker-compose.yml, ~/.docker, docker/).
NODE_TOOLS = (r"(?<![\w.-])(?:docker-compose|podman-compose|docker|podman|nerdctl|lncli|bitcoin-cli|tapcli|litcli"
              r"|chantools)(?![\w./-])")
ARG = r"(?:[\w./:=,@%+~-]+|'[^'$`\\]*'|\"[^\"$`\\]*\")"   # a plain word, or quoted text with no $, ` or \
TAIL = (r"(?:\s+" + ARG + r")*(?:\s+(?:[0-9]*|&)>{1,2}(?:&\d|\s*[\w./~-]+))*\s*$")  # its words, then redirections
HELP = r"(?:\s+[a-z]+)*\s+(?:--help|-h)\s*$|\s+(?:help(?:\s+[a-z]+)*|--version|-v|version)\s*$"
LNCLI_READS = (r"getinfo|getrecoveryinfo|getnetworkinfo|getnodeinfo|getchaninfo|getnodemetrics|describegraph"
               r"|listchannels|closedchannels|pendingchannels|listpeers|listinvoices|lookupinvoice|listpayments"
               r"|walletbalance|channelbalance|feereport|fwdinghistory|queryroutes|decodepayreq|listunspent"
               r"|listchaintxns|estimatefee|verifymessage|state|wallet\s+(?:accounts\s+list|listsweeps|pendingsweeps"
               r"|estimatefeerate|addresses\s+list)|chain\s+(?:getblock|getblockheader|getblockhash|getbestblock)")
BTC_READS = (r"getblockchaininfo|getblockcount|getbestblockhash|getblock|getblockhash|getblockheader|getblockstats"
             r"|getchaintips|getchaintxstats|getdifficulty|getmempoolinfo|getrawmempool|getmempoolentry"
             r"|getmempoolancestors|getmempooldescendants|getnetworkinfo|getpeerinfo|getconnectioncount|getnettotals"
             r"|getnodeaddresses|getaddednodeinfo|getindexinfo|getrawtransaction|decoderawtransaction|decodescript"
             r"|decodepsbt|analyzepsbt|estimatesmartfee|testmempoolaccept|getwalletinfo|getbalance|getbalances"
             r"|getunconfirmedbalance|listwallets|listwalletdir|listunspent|listtransactions|listsinceblock"
             r"|gettransaction|getaddressinfo|validateaddress|getdescriptorinfo|deriveaddresses|uptime|getmininginfo"
             r"|getnetworkhashps|gettxout|gettxoutproof|verifytxoutproof|gettxoutsetinfo|getdeploymentinfo"
             r"|getrpcinfo|getmemoryinfo|getzmqnotifications|listlabels|getaddressesbylabel|listreceivedbyaddress"
             r"|listreceivedbylabel|listaddressgroupings|getreceivedbyaddress|getreceivedbylabel|verifymessage")
# Reads only: the docker family's listings and logs, and inspect only with a
# --format naming fields that hold no secret (a container's environment can).
INSPECT_FIELDS = (r"(?:State|Name|Id|Created|RestartCount|Image|Platform|Driver|NetworkSettings|HostConfig|Mounts"
                  r"|Config\.(?:Image|Labels|Hostname))")
TEMPLATE = r"(?:[^'\"{}$`\\]|\{\{\s*(?:json\s+)?\." + INSPECT_FIELDS + r"(?:\.\w+)*\s*\}\})*"
COMPOSE = (r"(?:\s+(?:-f|--file|-p|--project-name|--project-directory)(?:=|\s+)[\w./-]+)*\s+"
           r"(?:(?:ps|logs|ls|images|top|version)" + TAIL + r"|config\s+--(?:services|images|volumes)\s*$)")
DOCKER_READS = (r"(?:ps|images|version|info|logs|top|port|history|diff|events|stats\s+--no-stream"
                r"|(?:container|image|network|volume|pod)\s+(?:ls|list|ps)|container\s+(?:logs|top|port|diff)"
                r"|image\s+(?:history|inspect)|manifest\s+inspect|(?:network|volume)\s+inspect|system\s+df"
                r"|context\s+(?:ls|show)|pod\s+ps)" + TAIL
                + r"|compose" + COMPOSE
                # a container's inspect: only with a --format of the fields above, before or after its names
                + r"|(?:container\s+)?inspect(?=[^|;&]*\s(?:-f|--format)[=\s])(?:\s+(?:[\w.-]+|(?:-f|--format)"
                r"(?:=|\s+)(?:'" + TEMPLATE + r"'|\"" + TEMPLATE + r"\")))+\s*$")
NODE_READ = (r"(?:lncli(?:\s+(?:-n\s+\w+|--network[= ]\w+|--rpcserver[= ][\w.:-]+|--chain[= ]\w+"
             r"|--lnddir[= ][\w./~-]+|--tlscertpath[= ][\w./~-]+))*(?:\s+(?:" + LNCLI_READS + r")" + TAIL + "|" + HELP
             + r")|bitcoin-cli(?:\s+-(?:rpcwallet=[\w.-]+|chain=\w+|testnet|regtest|signet|rpcport=\d+"
             r"|rpcconnect=[\w.:-]+|datadir=[\w./~-]+|named|rpcclienttimeout=\d+))*(?:\s+(?:" + BTC_READS + r")" + TAIL
             + r"|\s+listdescriptors(?:\s+false)?\s*$"   # its public descriptors; `true` prints the private keys
             r"|\s+-(?:getinfo|netinfo(?:=\d)?|version|help|\?)\s*$|\s+help(?:\s+\w+)?\s*$)"
             r"|tapcli(?:\s+(?:-n\s+\w+|--network[= ]\w+|--rpcserver[= ][\w.:-]+))*(?:\s+(?:getinfo"
             r"|assets\s+(?:list|balance|transfers|utxos|groups|meta|mint\s+batches)|addrs\s+(?:query|receives|decode)"
             r"|universe\s+(?:roots|stats|leaves|keys|info|federation\s+list))" + TAIL + "|" + HELP + r")"
             r"|litcli(?:\s+(?:getinfo|status)" + TAIL + "|" + HELP + r")"
             r"|chantools(?:" + HELP + r")"
             r"|(?:docker|podman|nerdctl)(?:\s+(?:" + DOCKER_READS + r")|" + HELP + r")"
             r"|(?:docker|podman)-compose(?:" + COMPOSE + "|" + HELP + r"))")
# a command that only names it: which, type, command -v, a listing, a checksum,
# a service's status or journal (not journalctl's --vacuum, --rotate, --flush, …)
NAMES_ONLY = (r"(?:which|type|whereis|command\s+-[vV]|ls|stat|file|readlink|realpath|basename|dirname|sha\d*sum"
              r"|md5sum|b2sum|du|wc|test|\[|systemctl\s+(?:--user\s+)?(?:status|is-active|is-enabled|is-failed|show|cat"
              r"|list-units|list-unit-files)|journalctl(?![^|;&]*\s--(?:vac|rot|flu|rel|set|syn|upd|cur)))"
              r"(?:\s+[\w./~=\]-]+)*\s*$")
rule(NR + r"(?!\s*(?:" + NODE_READ + "|" + NAMES_ONLY + r"))(?=.*" + NODE_TOOLS + ")",
     "names a node or container tool (lncli, bitcoin-cli, tapcli, litcli, chantools, docker, podman, nerdctl, "
     "docker-compose, podman-compose) in a command that is not one of the reads this repository allows" + LIVE)

# --- a command the guard cannot see whole ---------------------------------------------
# every command family a rule here guards (verifier round 8 found nerdctl, the
# package managers, grpcurl, wget and http missing)
CONTINUED = (r"(?:lncli|bitcoin-cli|tapcli|loop|pool|docker|docker-compose|podman|nerdctl|ctr|runc|crun|nsenter"
             r"|systemctl|loginctl|reboot|shutdown|poweroff|halt|init|telinit|apt|apt-get|aptitude|dpkg|snap"
             r"|rpm-ostree|dnf|yum|zypper|pacman|curl|wget|https?|grpcurl|kill|pkill|killall|rm|rmdir|mv|cp|install"
             r"|rsync|scp|ln|tar|gtar|bsdtar|unzip|7z\w*|cpio|sed|perl|g?awk|find|chmod|chown|git|gh|cd|pushd|xargs"
             r"|sudo|sh|bash|zsh|eval|python3?)")
rule(rx(W + SUDO + r"(?:\S*/)?" + CONTINUED + r"\b.*?\\(?:\\|n(?![A-Za-z]))"),
     "a command continued onto the next line inside a code string (a doubled backslash or \\n): the shared guard.py "
     "judges each line on its own, so it cannot see this command whole (verifier, 2026-10-10). Join it onto one line")
# Any command continued onto the next line (backslash-newline) asks, whatever
# it is (verifier round 9: `shred -u \⏎scripts/quality/hooks/pre-commit`, and
# tee, truncate, dd, unlink, vim, …) — except a read that writes nowhere: a
# read with a redirection asks too (`echo x > \⏎<the hook>` writes the hook).
# A backslash-newline inside quotes (a code string) is not split by guard.py:
# it asks wherever it is in the segment, also written as Python writes it in
# a string (`'rm \\\nx'`: an escaped backslash, then \n).
rule(r"^(?:(?!\s*" + READS + r")|" + MORE + r"|(?=[\s\S]*>))[\s\S]*?(?:\\(?:\n|$)|\\\\\\n)",
     "a command continued onto the next line (backslash-newline): the shared guard.py judges each line on its own, "
     "so it cannot see this command whole (verifier, 2026-10-10; the fix to guard.py is in review). Join it onto one "
     "line")

rule(r">\s*$",
     "a `>|` redirection (it overwrites even under noclobber): the shared guard.py splits a command at every `|`, "
     "so it cannot see where this one writes. Write `>` instead, or the owner approves")

# --- the pre-commit gate -----------------------------------------------------------------
# What always asks, each form listed here and in docs/guard-and-sandbox.md,
# and nothing else:
# git's options, configuration commands and environment that bypass the local
# hook or move core.hooksPath; a sparse checkout (the command, or
# core.sparseCheckout, or read-tree); hiding the hook's files from git
# (update-index --skip-worktree/--assume-unchanged) and an orphan switch; the
# hook's own files written, moved or deleted in the forms of writes(), the
# path relative, ./, absolute or under ~ or $PWD, with anything after it
# (/pre-commit, /*, *); and the folders that hold them (scripts,
# scripts/quality, .git) deleted, moved, extracted into or emptied by rsync,
# as whole words or with /*, /** or a brace list. Copying into those folders
# (how old scripts are ported) and edits with the file tools are
# protected-path writes for scripts/quality and the hook paths only, read by
# guard.py (PROTECTED_GLOBS): they ask in stable and are logged in
# development. A tripwire on command text cannot list every way (verifier
# rounds 3 to 7): the forms it misses are listed in docs/guard-and-sandbox.md.
# The hook is an early warning; the boundary is CI's full gate on every pull request to a
# protected main.
HOOK_NAMES = (r"(?:scripts" + SEP + r"quality" + SEP + r"hooks|\.git" + SEP + r"(?:config(?:\.worktree)?|hooks))"
              r"(?![\w.-])")
PARENT_NAMES = r"(?:scripts(?:" + SEP + r"quality)?|\.git)" + WHOLE
HOOK_FILES = r"(?<![\w.-])" + FPFX + HOOK_NAMES
HOOK_PARENTS = START + PFX + PARENT_NAMES
QUALITY = START + PFX + r"scripts" + SEP + r"quality(?![\w.-])"
COPY = CMD + r"(?:cp|install|rsync|scp|ln)\b"
TDIR = r"(?:\s-[A-Za-z]*t\s*|--target-directory[= ])[\"']?"   # cp/install/ln -t <dir>
# A copy that replaces the hook from outside: anything into .git; a folder
# named hooks into scripts/quality, or one named quality into scripts — as the
# last word or as -t.
NAMED = r"(?=.*\s[\"']?[^\s\"']*\b%s/?[\"']?(?:\s|$))"
COPY_IN = [COPY + r".*" + dest(START + PFX + r"\.git(?![\w.-])"),
           COPY + r".*" + TDIR + PFX + r"\.git(?![\w.-])",
           COPY + r".*\s[\"']?[^\s\"']*\bhooks/?[\"']?(?=\s).*" + dest(QUALITY),
           COPY + NAMED % "hooks" + r".*" + TDIR + PFX + r"scripts" + SEP + r"quality/?(?=[\s\"']|$)",
           COPY + r".*\s[\"']?[^\s\"']*\bquality/?[\"']?(?=\s).*" + dest(START + PFX + r"scripts(?![\w.-])"),
           COPY + NAMED % "quality" + r".*" + TDIR + PFX + r"scripts/?(?=[\s\"']|$)"]
INSTALL = r"[\"']?(?:\./|\$PWD/|\$\{PWD\}/)?scripts/quality/hooks/?[\"']?(?:\s|$)"  # the documented install
# git reads config keys in any case, and long options by any unique prefix
# (`--no-veri` is `--no-verify`; `--no-ve` is ambiguous with `--no-verbose`).
HOOKSPATH = r"[\"']?(?i:core\.hooksPath)\b"
SPARSE = r"[\"']?(?i:core\.sparseCheckout(?:Cone)?)\b"
NO_VERIFY = r"--no-veri(?:fy?)?\b"
# Settings git takes from elsewhere or under another name: an included file, an alias.
INDIRECT = r"[\"']?(?i:include(?:If\.\S*?)?\.path|alias\.)"
rule(r"\bgit\b(?=.*\s(?:-c\s*|--config-env[=\s]\s*)(?:" + HOOKSPATH + "|" + INDIRECT + "|" + SPARSE + "))"
     r"|\bGIT_CONFIG_(?:COUNT|KEY_\d+|PARAMETERS)\b"
     r"|\bgit\b(?:\s+(?:-\S+|[^-\s]\S*))*?\s+commit\b(?=.*\s(?:" + NO_VERIFY + r"|-[A-Za-z]*n[A-Za-z]*\b))"
     r"|\bgit\b.*\b(?:merge|rebase|cherry-pick|am|revert|push)\b.*" + NO_VERIFY
     # any option, valued or not, may come between `config` and the key
     + r"|\bconfig\b.*\s" + HOOKSPATH + r"[\"']?(?:\s+|=)(?!" + INSTALL + r")\S"
     r"|\bconfig\b.*(?:--unset(?:-all)?|\bunset)\s+(?:--\S+\s+)*" + HOOKSPATH
     + r"|\bconfig\b.*\s" + INDIRECT + r"\S*(?:\s+|=)\S"
     r"|\bconfig\b.*\b(?:remove|rename)-section\s+[\"']?(?i:core)\b"
     r"|\bgit\b.*\bconfig\b.*\s(?:-e|--edit|edit)\b"
     r"|\bgit\b.*\bsparse-checkout\b(?!\s+list\b)"
     r"|\bconfig\b.*\s" + SPARSE
     + r"|\bconfig\b.*\s[\"']?(?i:extensions\.worktreeConfig)\b"
     # paths fed to a command that deletes, moves or rewrites: the guard cannot see them
     r"|\bxargs\b(?:\s+-\S+(?:\s+[^-\s]\S*)?)*?\s+(?:sudo\s+)?(?:rm|rmdir|mv|shred|unlink|chmod|truncate|tee"
     r"|sed\s+-i|git\s+(?:rm|mv|update-index|checkout|restore))\b"
     + r"|\bgit\b.*\bread-tree\b"
     r"|\bgit\b.*\bswitch\b.*\s--orphan\b"
     r"|\bgit\b.*\bupdate-index\b(?=.*--(?:skip-worktree|assume-unchanged)\b).*" + HOOK_FILES
     + r"|" + "|".join(writes(HOOK_FILES, HOOK_PARENTS, FPFX + HOOK_NAMES, PFX + PARENT_NAMES) + COPY_IN)
     + r"|\bgit\b.*\b(?:rm|mv|checkout|restore|apply|reset|stash)\b.*(?:" + HOOK_FILES + "|" + HOOK_PARENTS + ")"
     r"|(?:>\||>>?)\s*[\"']?" + FPFX + HOOK_NAMES,
     "turns off or rewrites the pre-commit gate (the secret scan and the hygiene check) — a gate is never switched "
     "off to get through (Law 2); the owner decides")

# Copying into scripts/quality, the folder that holds the hook, is a
# protected-path write: guard.py reads a copy's last word, so this rule adds
# the forms it misses there (a redirection or option after the destination,
# -t). It asks in stable and is logged in development, like guard.py's own.
rule(rx(COPY + r".*" + dest(QUALITY), COPY + r".*(?:\s-[A-Za-z]*t\s*|--target-directory[= ])[\"']?" + PFX
        + r"scripts" + SEP + r"quality(?![\w.-])"),
     "copies into scripts/quality, the folder that holds the pre-commit hook (a protected path) — the owner decides",
     always_ask=False)

# --- GitHub (Rikuri-PI's rules) -----------------------------------------------------------
GITHUB = [
    (r"\bgh\s+pr\s+merge\b",
     "gh pr merge lands work on a protected branch on GitHub — owner approves", False),
    (r"\bgh\s+repo\s+(unarchive|rename|edit)\b",
     "changes or deletes the GitHub repository itself — owner approves", False),
    (r"\bgh\s+repo\s+(delete|archive)\b",
     "deletes or archives the GitHub repository — irreversible; owner approves", True),
    (r"(?i)\bgh\s+api\b(?!.*\sgraphql(\s|$))(?!.*(-X|--method)[\s=]*GET\b(?!.*(-X|--method)))"
     r"(?=.*((-X|--method)[\s=]*(PUT|POST|PATCH|DELETE)\b|\s(-f|--field|--raw-field|--input)))",
     "a gh api write changes GitHub state directly (branch protection, rulesets, workflows, secrets, merges, refs) "
     "— owner approves", False),
    (r"(?i)\bgh\s+api\b.*\sgraphql(\s|$).*(mutation|--input|=@|\$)",
     "a GraphQL mutation, or a GraphQL body the guard cannot read (file, --input, shell variable), may change "
     "GitHub state — owner approves", False),
    (r"\bgh\s+workflow\s+disable\b",
     "disables a CI workflow — a required gate is never switched off to get green (Law 2); owner approves", False),
    (r"\bgh\s+(secret|variable)\s+(set|delete|remove)\b",
     "changes GitHub Actions secrets or variables — owner approves", False),
    (r"\bgh\s+auth\s+(token\b|status\b.*(\s-t\b|--show-token\b))",
     "prints a GitHub credential into the transcript (gh auth token, gh auth status --show-token) — owner approves",
     True),
    (r"\bgit\s+filter-(repo|branch)\b", "rewrites repository history — owner approves", False),
]
for _regex, _reason, _always in GITHUB:
    rule(_regex, _reason, _always)

# --- files ----------------------------------------------------------------------------------
_BACKUPS = [".bak*", ".old*", ".orig", ".gz", ".b64", ".hex", ".[0-9]*"]
SECRET_GLOBS = (
    [".env", ".env.*", "*.env", "*.env.*", ".envrc", ".netrc", ".npmrc", ".pypirc",
     "*.local.env", "*.local.json", "*.local.toml", "*.local.yaml", "*.local.yml",
     "*.key", "*.pem", "*.p12", "*.pfx", "*.jks", "*.keystore", "*.kdbx", "*.keychain*",
     "*.token", "*.secret", "id_rsa*", "id_ed25519*", "id_ecdsa*", "ssh_host_*_key",
     "credentials", "credentials.json", "credentials.toml", ".credentials.json", "client_secret*.json",
     "service-account*.json", ".git-credentials", "hosts.yml", "secrets.json", "secrets.yaml", "secrets.yml",
     "keys.txt", "wg*.conf"]
    # the node's key files: wallets, macaroons, channel state and backups, Tailscale's state
    + ["wallet.db", "wallet.dat", "macaroons.db", "channel.db", "channel.backup", "channels.backup", "*.macaroon",
       "tailscaled.state"]
    # authentication cookies (bitcoind, Tor) and Tor's onion-service keys; one name per line where a
    # secret scanner would read "<key name>, <next name>" as a credential and its value
    + ["*.cookie", "*_secret_key",
       "control_auth_cookie",
       "hs_ed25519_secret_key"]
    # wallet passwords and seeds
    + ["password.txt", "*_password.txt", "*-password", "*_password", "wallet_password*",
       "wallet-password",
       "wallet-password.txt",
       "seed.txt", "*seed.txt", "aezeed*.txt", "*.seed", "mnemonic*.txt"]
    + [k + s for k in ("wallet.db", "wallet.dat", "macaroons.db", "channel.backup", "channels.backup", "*.macaroon")
       for s in _BACKUPS]
    # live node configs hold credentials; tracked configs are *.conf.template
    + ["bitcoin.conf", "lnd.conf", "tapd.conf"])
SECRET_ALLOW_GLOBS = ["*.example", "*.sample", "*.template", "*.pub", "settings.local.json"]
PROTECTED_GLOBS = ["AGENTS.md", "CLAUDE.md", "REVIEW.md", ".gitignore", ".gitleaks.toml",
                   ".claude", ".claude/settings.json", ".claude/settings.local.json", ".claude/settings*",
                   ".claude/hooks", ".claude/hooks/*", ".claude/agents", ".claude/agents/*",
                   ".claude/state", ".claude/state/*", ".agents", ".agents/workflows", ".agents/workflows/*",
                   ".github", ".github/workflows", ".github/workflows/*", "scripts/quality", "scripts/quality/*",
                   ".git/config", ".git/hooks", ".git/hooks/*", ".git/info/sparse-checkout"]
DOC = ("Policy for .claude/hooks/guard.py (AGENTS.md > Deterministic gates). Generated by "
       "scripts/quality/guard_policy.py: edit the rules there, not here; the gate checks the two agree. The worked "
       "examples below are data kept here, replayed by test_guard.py: add one whenever the policy changes. Globs "
       "without '/' match the basename; with '/' the repo-relative path ('*' crosses '/'). guard.py, guard_base.py "
       "and test_guard.py are identical across the owner's Full-tier repositories; only this file differs.")


def generated(cfg: dict) -> dict:
    out = dict(cfg)
    out.update({"_doc": DOC, "secret_globs": SECRET_GLOBS, "secret_allow_globs": SECRET_ALLOW_GLOBS,
                "protected_globs": PROTECTED_GLOBS, "funds_patterns": RULES})
    return out


def main(argv: list, config: str = CONFIG) -> int:
    with open(config) as f:
        current = json.load(f)
    wanted = generated(current)
    if "--check" in argv[1:]:
        if wanted != current:
            changed = sorted(k for k in set(wanted) | set(current) if wanted.get(k) != current.get(k))
            print("guard-config.json differs from scripts/quality/guard_policy.py in: " + ", ".join(changed)
                  + " — run scripts/quality/guard_policy.py", file=sys.stderr)
            return 1
        return 0
    with open(config, "w") as f:
        json.dump(wanted, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
