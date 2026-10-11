"""Bootstrap round 9 mutants: each must turn a test red (the guard's tests, or
the quality tools' — claims, baseline, speed, wiring). Run from the repository
root inside safe-run.sh, with Python -B. Every file is restored and checked by
sha256. Round 9's first run found two equivalents, removed from the policy
and from this list: a backtick in MORE (guard.py reads backtick commands
itself) and the git rule's reflog/--output alternative (the closed-world rule
asks for them)."""
import hashlib
import re
import subprocess
import sys

GUARD = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
QUALITY = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "scripts/quality/tests", "-p", "test_*.py"]
REGEN = [sys.executable, "-B", "scripts/quality/guard_policy.py"]
GP, WI, CFG = "scripts/quality/guard_policy.py", "scripts/quality/check_guard_wiring.py", ".claude/hooks/guard-config.json"
M = [
    ("Q1 a lone & no longer voids a read", GP, r'(?:(?<![&>])&(?![&>])|\$\()', r'(?:\$\()'),
    ("Q2 $( no longer voids a read", GP, r'(?:(?<![&>])&(?![&>])|\$\()', r'(?:(?<![&>])&(?![&>]))'),
    ("Q4 no closed-world rule", GP, r'+ r")(?=.*" + PARENT_TREE + r")",', r'+ r")(?=.*NEVERMATCH)",'),
    ("Q5 closed world without the parent tree", GP, r'PARENT_TREE = HOME + SEP + r"rikuri(?![\w.-])"', r'PARENT_TREE = OLD'),
    ("Q6 a link copy counts as a read", GP, r'r"|(?:cp|install)\b(?![^|;&]*\s(?:-[A-Za-z]*[ls]|--link|--symbolic-link)\b)"', r'r"|(?:cp|install)\b"'),
    ("Q7 rsync --link-dest counts as a read", GP, r'r"|rsync\b(?![^|;&]*--link-dest)|scp\b)")', r'r"|rsync\b|scp\b)")'),
    ("Q8 find -fprint counts as a read", GP, r'r"|find\b(?![^|;&]*\s-(?:delete|exec|execdir|ok|okdir|fprint\w*|fls)\b)"', r'r"|find\b(?![^|;&]*\s-(?:delete|exec|execdir|ok|okdir)\b)"'),
    ("Q9 tree -o counts as a read", GP, r'r"|tree\b(?![^|;&]*\s-o)|rg\b(?![^|;&]*\s--pre)"', r'r"|tree\b|rg\b(?![^|;&]*\s--pre)"'),
    ("Q10 rg --pre counts as a read", GP, r'r"|tree\b(?![^|;&]*\s-o)|rg\b(?![^|;&]*\s--pre)"', r'r"|tree\b(?![^|;&]*\s-o)|rg\b"'),
    ("Q11 git -O counts as a read", GP, r'\b(?![^|;&]*\s(?:--output|-O|--open-files-in-pager)\b)"', r'\b(?![^|;&]*\s(?:--output)\b)"'),
    ("Q12 sed -n is not a read", GP, r'''r"|sed\s+-n\s+(?:-E\s+)?[\"']?[\d,$]+p[\"']?(?=\s)"''', r'r"|sed\s+-n\s+NEVER"'),
    ("Q13 commit and grep text not exempt", GP, r'r"|git\s+(?:commit|tag|grep)\b|gh', r'r"|gh'),
    ("Q14 hook files without a folder prefix", GP, r'HOOK_FILES = r"(?<![\w.-])" + FPFX + HOOK_NAMES', r'HOOK_FILES = r"(?<![\w.-])" + HOOK_NAMES'),
    ("Q15 no pathspec magic", GP, r'PFX = (r"(?::/|:\([^)\s]*\))?(?:', r'PFX = (r"(?:'),
    ("Q16 a single ./", GP, r'(?:(?:\./+)+|(?:/|~', r'(?:\./|(?:/|~'),
    ("Q17 no ~+", GP, r'(?:/|~[\w+]*/|', r'(?:/|~\w*/|'),
    ("Q18 no $(…)/", GP, r'''|\$\([^)]*\)[\"']?/)"''', r')"'),
    ("Q19 no option clusters in extraction", GP, r'(?:-[A-Za-z]*[CdD]\s*|--directory[= ]\s*|-[A-Za-z]*o)', r'(?:-[CdD]\s*|--directory[= ]\s*|-o)'),
    ("Q20 gawk only as -i inplace", GP, r'''(?:-i\s*[\"']?inplace|--include[= ]\s*[\"']?inplace)''', r'(?:-i\s*inplace)'),
    ("Q21 no curl/wget output folders", GP, r'(?:\s-[A-Za-z]*[oOP]\s*|--output(?:-document|-dir)?[= ]\s*|--directory-prefix[= ]\s*)', r'(?:\s-[A-Za-z]*[oO]\s*|--output(?:-document)?[= ]\s*)'),
    ("Q22 no more editors", GP, r'r"|pico|micro|gvim|vimdiff|view|emacsclient|joe|code|mcedit|hx|kate|gedit|subl|jed)\b.*"', r'r")\b.*"'),
    ("Q23 no -t into .git", GP, '           COPY + r".*" + TDIR + PFX + r"\\.git(?![\\w.-])",\n', ''),
    ("Q24 ln not a copy", GP, r'COPY = CMD + r"(?:cp|install|rsync|scp|ln)\b"', r'COPY = CMD + r"(?:cp|install|rsync|scp)\b"'),
    ("Q25 no sparse checkout through -c", GP, r'"|" + INDIRECT + "|" + SPARSE + "))"', r'"|" + INDIRECT + "))"'),
    ("Q26 no worktreeConfig", GP, r'''+ r"|\bconfig\b.*\s[\"']?(?i:extensions\.worktreeConfig)\b"''', r'+ r""'),
    ("Q27 no config.worktree", GP, r'(?:config(?:\.worktree)?|hooks)', r'(?:config|hooks)'),
    ("Q28 no xargs rule", GP, r'r"|\bxargs\b(?:', r'r"|\bxargsNEVER\b(?:'),
    ("Q29 no zip -m", GP, r'CMD + r"zip\b(?=', r'CMD + r"zipNEVER\b(?='),
    ("Q30 no old-style tar", GP, r'CMD + r"(?:g|bsd)?tar\s+[A-Za-z]*x[A-Za-z]*\s.*" + either,', r'CMD + r"NEVERtar\s+[A-Za-z]*x[A-Za-z]*\s.*" + either,'),
    ("Q31 /home only", GP, r'/+(?:\./+)*home/+(?:\./+)*(?:junc|\*)', r'/home/(?:junc|\*)'),
    ("Q33 the old continued-line list", GP, r'|rpm-ostree|dnf|yum|zypper|pacman|curl|wget|https?|grpcurl|', r'|curl|'),
    ("Q34 ReDoS: docker options back", GP, r'(?:\s+-[\w-]+(?:=\S+|\s+[^-\s]\S*)?)*', r'(?:\s+-{1,2}[\w-]+(?:[= ]\S+)?)*'),
    ("Q35 ReDoS: xargs values back", GP, r'(?:\s+-\S+(?:\s+[^-\s]\S*)?)*?', r'(?:\s+-\S+(?:\s+\S+)?)*?'),
    ("Q36 ReDoS: commit options back", GP, r'(?:\s+(?:-\S+|[^-\s]\S*))*?\s+commit', r'(?:\s+-\S+(?:\s+\S+)?)*?\s+commit'),
    ("Q37 ReDoS: git -c values back", GP, r'(?:-C|-c|--git-dir|--work-tree|--namespace)\s+[^-\s]\S*\s+', r'(?:-C|-c|--git-dir|--work-tree|--namespace)\s+\S+\s+'),
    ("W1 old checkout's secrets not required unreadable", WI, 'for want, key in ((DENY_WRITE, "denyWrite"), (DENY_READ, "denyRead")):', 'for want, key in ((DENY_WRITE, "denyWrite"),):'),
    ("W2 the unsandboxed retry allowed", WI, 'wanted = {"enabled": True, "failIfUnavailable": True, "allowUnsandboxedCommands": False}', 'wanted = {"enabled": True, "failIfUnavailable": True}'),
    ("W3 nothing counts as widening", WI, 'WIDENING = [("filesystem", "allowWrite"),', 'WIDENING = 0 * [("filesystem", "allowWrite"),'),
    ("W4 any excluded command", WI, 'extra = set(box.get("excludedCommands") or []) - (EXCLUDED_OK if full else set())', 'extra = set()'),
    ("W5 additional directories allowed", WI, 'if (settings.get("permissions") or {}).get("additionalDirectories"):', 'if False:'),
    ("W6 local settings' sandbox unread", WI, 'found += sandbox_problems(path, settings, require_guard)', 'found += sandbox_problems(path, settings, require_guard) if require_guard else []'),
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
