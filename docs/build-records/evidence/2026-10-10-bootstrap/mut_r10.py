"""Bootstrap round 10 mutants: each must turn a test red (the guard's tests, or
the quality tools' — claims, baseline, speed, policy, wiring). Run from the
root of a scratch copy of the tree (never the worktree) inside safe-run.sh,
with Python -B. Every file is restored and checked by sha256. A wiring mutant
runs only the quality tests (the guard's tests do not read the wiring check).
The first run (65 mutants, mut-r10-first-run.out) left three green: X11 and X18
got tests (mut-r10-rerun.out); R33 (`listdescriptors` with any words after it
counted a read) is equivalent and removed — the older rule for private keys
still asks for `listdescriptors true` and `private=true`."""
import hashlib
import subprocess
import sys

GUARD = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
QUALITY = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "scripts/quality/tests", "-p", "test_*.py"]
REGEN = [sys.executable, "-B", "scripts/quality/guard_policy.py"]
GP, WI, CFG = "scripts/quality/guard_policy.py", "scripts/quality/check_guard_wiring.py", ".claude/hooks/guard-config.json"
M = [
    # process substitution and the options that run a program end a read
    ("R1 no process substitution in MORE", GP, r'''|\$\(|[<>=]\(|" + RUNS''', r'''|\$\(|" + RUNS'''),
    ("R2 no RUNS in MORE", GP, r'''|[<>=]\(|" + RUNS + r"))"''', r'''|[<>=]\())"'''),
    ("R3 -O only alone", GP, r'''RUNS = r"\s(?:-[A-Za-z]*O|''', r'''RUNS = r"\s(?:-O\b|'''),
    ("R4 no --op", GP, r'''--(?:op|pre\b''', r'''--(?:pre\b'''),
    ("R5 no --pre", GP, r'''|pre\b|pager\b|''', r'''|pager\b|'''),
    ("R6 no --pager", GP, r'''|pager\b|ou|''', r'''|ou|'''),
    # paths
    ("R7 no ${HOME…} expansions", GP, r'''\$\{HOME(?:[^}\w][^}]*)?\}''', r'''\$\{HOME\}'''),
    ("R8 no ${PWD…} expansions", GP, r'''(?:\$\w+|\$\{\w+(?:[^}\w][^}]*)?\})[\"']?/''', r'''\$\{?\w+\}?[\"']?/'''),
    ("R9 no backtick folder", GP, r'''|\$\([^)]*\)[\"']?/|`[^`]*`[\"']?/)"''', r'''|\$\([^)]*\)[\"']?/)"'''),
    # writes into the parent folder
    ("R10 no parent-tree copy destination", GP, '        CMD + r"(?:cp|install|rsync|scp)\\b.*" + dest(HOST + PARENT_TREE),\n', ''),
    ("R11 no parent-tree -t", GP, '        CMD + r"(?:cp|install)\\b.*(?:\\s-[A-Za-z]*t\\s*|--target-directory[= ])[\\"\']?" + PARENT_TREE,\n', ''),
    ("R12 no parent-tree sort -o", GP, ',\n        r"\\bsort\\b.*(?:\\s-[A-Za-z]*o\\s*|--ou\\w*[= ]\\s*)[\\"\']?" + PARENT_TREE)', ')'),
    ("R13 redirect only into OLD/PARENT", GP, r'''+ r"|(?:>\||>>?)\s*[\"']?" + PARENT_TREE,''', r'''+ r"|(?:>\||>>?)\s*[\"']?(?:" + OLD + "|" + PARENT + ")",'''),
    ("R14 host without a quote", GP, r'''HOST = r"(?:[\w.@-]+:[\"']?)?"''', r'''HOST = r"(?:[\w.@-]+:)?"'''),
    ("R15 no host", GP, r'''HOST = r"(?:[\w.@-]+:[\"']?)?"''', r'''HOST = r""'''),
    # the previous checkout's reads
    ("R16 sort -T a read", GP, r'''r"|sort\b(?![^|;&]*\s(?:-[A-Za-z]*T|--(?:com|te)\w*))"''', r'''r"|sort\b"'''),
    ("R17 tree -o only alone", GP, r'''r"|tree\b(?![^|;&]*\s(?:-[A-Za-z]*o|--o\w*))"''', r'''r"|tree\b(?![^|;&]*\s-o\b)"'''),
    ("R18 sed: round 9's form", GP, r'''r"|sed\s+-n\s+(?:-E\s+)?(?:'[\d,$]+p'|\"[\d,$]+p\"|[\d,$]+p)(?:\s+[^\s;|&<>`$()'\"-][^\s;|&<>`$()'\"]*)+"''' + '\n' + r'''             r"\s*(?:[0-9]*>{1,2}\s*[^\s;|&<>()]+\s*)?$"''', r'''r"|sed\s+-n\s+(?:-E\s+)?[\"']?[\d,$]+p[\"']?(?=\s)"'''),
    ("R19 sed operands may be options", GP, r'''(?:\s+[^\s;|&<>`$()'\"-][^\s''', r'''(?:\s+[^\s;|&<>`$()'\"][^\s'''),
    ("R20 git commit -F a read", GP, r'''r"|git\s+(?:commit|tag)\b(?![^|;&]*\s(?:-[A-Za-z]*[Ft]|--(?:fi|te)\w*))|git\s+grep\b"''', r'''r"|git\s+(?:commit|tag|grep)\b"'''),
    ("R21 gh --body-file a read", GP, r'''r"|gh\s+(?:pr|issue)\s+(?:create|edit|comment)\b(?![^|;&]*\s(?:-[A-Za-z]*F|--body-file))"''', r'''r"|gh\s+(?:pr|issue)\s+(?:create|edit|comment)\b"'''),
    ("R22 cp link: round 9's form", GP, r'''r"|(?:cp|install)\b(?![^|;&]*\s(?:-[A-Za-z]*[ls]|--(?:l|sy|st)\w*))"''', r'''r"|(?:cp|install)\b(?![^|;&]*\s(?:-[A-Za-z]*[ls]|--link|--symbolic-link)\b)"'''),
    ("R23 rsync -e a read", GP, r'''r"|rsync\b(?![^|;&]*\s(?:-[A-Za-z]*[eT]|--(?:rs|link-d|log-f|te|backup-d|partial-d|write-b|only-w"''' + '\n' + r'''             r"|copy-d|compare-d)\w*))"''', r'''r"|rsync\b(?![^|;&]*--link-dest)"'''),
    ("R24 scp -S a read", GP, r'''r"|scp\b(?![^|;&]*\s-[A-Za-z]*[SoFJ]))")''', r'''r"|scp\b)")'''),
    ("R43 ag not a read there", GP, r'''|echo|printf|rg|ag)\b|\["''', r'''|echo|printf|rg)\b|\["'''),
    ("R44 [ not a read there", GP, r'''|echo|printf|rg|ag)\b|\["''', r'''|echo|printf|rg|ag)\b"'''),
    ("R45 sudo read not a read", GP, r'''rule(r"^(?:(?!\s*(?:sudo\s+)?" + OLD_READS''', r'''rule(r"^(?:(?!\s*" + OLD_READS'''),
    ("R46 sed -n -E not a read", GP, r'''sed\s+-n\s+(?:-E\s+)?(?:'[''', r'''sed\s+-n\s+(?:'['''),
    # node and container tools
    ("R25 no node rule", GP, r'''r"))(?=.*" + NODE_TOOLS + ")",''', r'''r"))(?=.*NEVERMATCH)",'''),
    ("R26 a path-called tool is not named", GP, r'''NODE_TOOLS = (r"(?<![\w.-])''', r'''NODE_TOOLS = (r"(?<![\w./-])'''),
    ("R27 a docker/ folder names the tool", GP, r'''|chantools)(?![\w./-])")''', r'''|chantools)(?![\w.-])")'''),
    ("R28 a read's words may run code", GP, r'''ARG = r"(?:[\w./:=,@%+~-]+|'[^'$`\\]*'|\"[^\"$`\\]*\")"''', r'''ARG = r"(?:[\w./:=,@%+~$()`-]+|'[^']*'|\"[^\"]*\")"'''),
    ("R29 lncli debuglevel a read", GP, r'''r"|listchannels|closedchannels''', r'''r"|debuglevel|listchannels|closedchannels'''),
    ("R30 inspect any field", GP, r'''TEMPLATE = r"(?:[^'\"{}$`\\]|\{\{\s*(?:json\s+)?\." + INSPECT_FIELDS + r"(?:\.\w+)*\s*\}\})*"''', r'''TEMPLATE = r"[^'\"$`\\]*"'''),
    ("R31 inspect without a format", GP, r'''inspect(?=[^|;&]*\s(?:-f|--format)[=\s])''', r'''inspect'''),
    ("R32 compose config a read", GP, r'''|config\s+--(?:services|images|volumes)\s*$)")''', r'''|config" + TAIL + r")")'''),
    ("R34 litcli sessions list a read", GP, r'''r"|litcli(?:\s+(?:getinfo|status)''', r'''r"|litcli(?:\s+(?:getinfo|status|sessions\s+list)'''),
    ("R35 env, sudo, timeout only name it", GP, r'''NAMES_ONLY = (r"(?:which|type|''', r'''NAMES_ONLY = (r"(?:env|sudo|timeout\s+\d+|which|type|'''),
    ("R36 journalctl --vacuum only names it", GP, r'''|journalctl(?![^|;&]*\s--(?:vac|rot|flu|rel|set|syn|upd|cur)))"''', r'''|journalctl)"'''),
    ("R37 a read after sudo", GP, r'''rule(NR + r"(?!\s*(?:" + NODE_READ''', r'''rule(NR + r"(?!\s*(?:sudo\s+)?(?:" + NODE_READ'''),
    ("R47 bitcoin-cli -stdin a global", GP, r'''|named|rpcclienttimeout=\d+))*''', r'''|named|stdin\w*|rpcclienttimeout=\d+))*'''),
    ("R48 lncli --no-macaroons a global", GP, r'''|--tlscertpath[= ][\w./~-]+))*''', r'''|--tlscertpath[= ][\w./~-]+|--no-macaroons))*'''),
    # continued lines
    ("R38 a read with a redirection continued", GP, r'''|" + MORE + r"|(?=[\s\S]*>))[\s\S]*?''', r'''|" + MORE + r")[\s\S]*?'''),
    ("R39 continued only at the end", GP, r'''[\s\S]*?(?:\\(?:\n|$)|\\\\\\n)",''', r'''[\s\S]*?(?:\\$|\\\\\\n)",'''),
    ("R40 no escaped continuation", GP, r'''[\s\S]*?(?:\\(?:\n|$)|\\\\\\n)",''', r'''[\s\S]*?(?:\\(?:\n|$))",'''),
    ("R41 continued reads ask too", GP, r'''rule(r"^(?:(?!\s*" + READS + r")|" + MORE + r"|(?=[\s\S]*>))''', r'''rule(r"^(?:|" + MORE + r"|(?=[\s\S]*>))'''),
    ("R49 no continued rule", GP, r'''[\s\S]*?(?:\\(?:\n|$)|\\\\\\n)",''', r'''NEVERMATCH",'''),
    # the wiring check
    ("X1 another sandbox key allowed", WI, '''out.append("%s.%s is not part of this repository's sandbox" % (where, key))''', 'pass'),
    ("X2 an added list item allowed", WI, 'if have - need:', 'if False:'),
    ("X3 1 counts as true", WI, 'if json.dumps(want) != json.dumps(got):', 'if want != got:'),
    ("X4 the local file may set the sandbox", WI, '''return ["%s: the local settings may not set the sandbox (only .claude/settings.json does)" % path]''', 'return []'),
    ("X5 Read(…) does not widen", WI, '"WebFetch", "Read"}', '"WebFetch"}'),
    ("X6 WebFetch does not widen", WI, '"NotebookEdit", "WebFetch", "Read"}', '"NotebookEdit", "Read"}'),
    ("X7 no env check", WI, '''return ["%s: env.%s names the sandbox or hooks" % (path, k) for k in sorted(env) if ENV_WORDS.search(k)]''', 'return []'),
    ("X8 env: SANDBOX only, case-sensitive", WI, 're.compile(r"SANDBOX|HOOK", re.IGNORECASE)', 're.compile(r"SANDBOX")'),
    ("X9 PermissionRequest hooks allowed", WI, 'if hooks.get("PermissionRequest"):', 'if False:'),
    ("X10 other PreToolUse hooks allowed", WI, 'if others:', 'if False:'),
    ("X11 the local file may add PreToolUse", WI, 'if not full and entries:', 'if False:'),
    ("X12 unknown permission keys allowed", WI, 'for key in sorted(set(perms) - PERMISSION_KEYS - {"additionalDirectories"}):', 'for key in []:'),
    ("X13 rule lists unchecked", WI, 'if not isinstance(rules, list) or not all(isinstance(r, str) for r in rules):', 'if False:'),
    ("X15 hooks of any type", WI, 'if not isinstance(hooks, dict):', 'if False:'),
    ("X16 a section of any type", WI, 'return ["%s must be an object" % where]', 'return []'),
    ("X17 additionalDirectories allowed", WI, 'if "additionalDirectories" in perms:', 'if False:'),
    ("X18 a guard that fails open counts", WI, 'open_on_failure = True  # counts for nothing', 'pass  # counts for nothing'),
]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


files = (GP, WI, CFG)
orig = {p: open(p, "rb").read() for p in files}
before = {p: sha(p) for p in files}
for name, path, a, b in M:
    assert orig[path].decode().count(a) == 1, (name, orig[path].decode().count(a))
if "--check" in sys.argv[1:]:
    print(len(M), "mutants apply")
    sys.exit(0)
only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
rows = []
try:
    for name, path, a, b in M:
        if only and name.split(" ")[0] not in only:
            continue
        src = orig[path].decode().replace(a, b)
        compile(src, path, "exec")
        with open(path, "w") as f:
            f.write(src)
        if path == GP:
            subprocess.run(REGEN, check=True)
            g = subprocess.run(GUARD, capture_output=True, text=True)
        else:
            g = subprocess.CompletedProcess([], 0, "", "")
        q = subprocess.run(QUALITY, capture_output=True, text=True, timeout=600)
        fails = sorted({l.split("(")[0].split(":", 1)[1].strip() for l in (g.stderr + q.stderr).splitlines()
                        if l.startswith(("FAIL:", "ERROR:"))})
        red = g.returncode or q.returncode
        rows.append("%-46s %s %s" % (name, "RED  " if red else "GREEN", ", ".join(fails)))
        print(rows[-1], flush=True)
        for p in files:
            with open(p, "wb") as f:
                f.write(orig[p])
finally:
    for p in files:
        with open(p, "wb") as f:
            f.write(orig[p])
    assert {p: sha(p) for p in files} == before
print("restored, sha256 checked:", ", ".join("%s %s" % (p, before[p][:12]) for p in sorted(files)))
