"""Bootstrap round 8 mutants: each must turn a test red. Run from the
repository root inside safe-run.sh, with Python -B (no bytecode cache). Every
file is restored and checked by sha256. A mutant that stays green is listed
as such: either an example is missing or the mutant is equivalent. Three
equivalents found on the first run were removed from the policy and from this
list (record, round 8): `>` and `|` in a path's start, `>|` in REDIR, and the
old checkout's `>|` redirect."""
import hashlib
import re
import subprocess
import sys

GUARD = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
CLAIMS = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "scripts/quality/tests", "-p", "test_guard_claims.py"]
REGEN = [sys.executable, "-B", "scripts/quality/guard_policy.py"]
GP, CFG = "scripts/quality/guard_policy.py", ".claude/hooks/guard-config.json"
MUTANTS = [
    ("R2 no absolute prefix", 'PFX = r"(?:\\./|(?:/|~\\w*/|', 'PFX = r"(?:\\./|(?:~\\w*/|'),
    ("R3 no ~ prefix", '(?:/|~\\w*/|\\$\\{?\\w+\\}?', '(?:/|\\$\\{?\\w+\\}?'),
    ("R4 no $VAR prefix", '~\\w*/|\\$\\{?\\w+\\}?[\\"\']?/|\\$\\(pwd\\)/)', '~\\w*/|\\$\\(pwd\\)/)'),
    ("R5 no ./ prefix", 'PFX = r"(?:\\./|(?:', 'PFX = r"(?:(?:'),
    ("R6 any relative prefix", 'PFX = r"(?:\\./|(?:/|~\\w*/|\\$\\{?\\w+\\}?[\\"\']?/|\\$\\(pwd\\)/)(?:[^\\s\\"\';|&<>()]*/)?)?"',
     'PFX = r"(?:[^\\s\\"\';|&<>()]*/)?"'),
    ("R7 a folder without braces", 'WHOLE = r"/?(?:\\*\\*?|\\{[^}\\s]*\\})?', 'WHOLE = r"/?(?:\\*\\*?)?'),
    ("R8 a folder without /**", 'WHOLE = r"/?(?:\\*\\*?|', 'WHOLE = r"/?(?:\\*|'),
    ("R9 redirections without &>", 'REDIR = r"(?:[0-9]*|&)[<>]', 'REDIR = r"[0-9]*[<>]'),
    ("R42 >| into the hook ignored", '     r"|(?:>\\||>>?)\\s*[\\"\']?" + PFX + HOOK_NAMES,', '     r"|>>?\\s*[\\"\']?" + PFX + HOOK_NAMES,'),
    ("R10 options without a value", '|\\s+-\\S+(?:\\s+[^-\\s&|;<>#]\\S*)?|', '|\\s+-\\S+|'),
    ("R11 no comment after the destination", '(?:\\s*(?:$|&&|\\|\\|?|;|\\)|#)|', '(?:\\s*(?:$|&&|\\|\\|?|;|\\))|'),
    ("R12 no quoted destination with spaces",
     '[^\\s\'\\"]*[\\"\']?|\\"" + target + r"[^\\"]*\\"|\'" + target + r"[^\']*\')"', '[^\\s\'\\"]*[\\"\']?)"'),
    ("R13 a closing quote ends no destination", '|;|\\)|#)|[\\"\']))")', '|;|\\)|#)))")'),
    ("R14 no command called by path", 'CMD = W + SUDO + r"(?:[\\w.~/-]*/)?"', 'CMD = W + SUDO'),
    ("R15 install not a copy", '        CMD + r"(?:cp|install|rsync|scp)\\b.*" + dest(target),',
     '        CMD + r"(?:cp|rsync|scp)\\b.*" + dest(target),'),
    ("R16 no curl/wget output", '        r"\\b(?:curl|wget)\\b.*(?:\\s-[A-Za-z]*[oO]', '        r"\\bxcurl\\b.*(?:\\s-[A-Za-z]*[oO]'),
    ("R17 no sort -o", '        r"\\bsort\\b.*(?:\\s-[A-Za-z]*o', '        r"\\bxsort\\b.*(?:\\s-[A-Za-z]*o'),
    ("R18 awk only", 'r"\\b[gm]?awk\\b', 'r"\\bawk\\b'),
    ("R19 no rename", '(?:rm|rmdir|mv|rename|shred', '(?:rm|rmdir|mv|shred'),
    ("R20 no split", '|patch|cpio|split|csplit|ex', '|patch|cpio|ex'),
    ("R21 no gtar/bsdtar", 'CMD + r"(?:g|bsd)?(?:tar', 'CMD + r"(?:tar'),
    ("R22 extraction options need a space", '(?:-[CdD]\\s*|--directory', '(?:-[CdD]\\s+|--directory'),
    ("R23 no 7z -o", '|--directory[= ]\\s*|-o)', '|--directory[= ]\\s*)'),
    ("R24 chmod/chown not on a folder", '|rename|shred|chmod|chown|chgrp)\\b.*" + either', '|rename|shred)\\b.*" + either'),
    ("R25 rsync --delete only on the files", 'rsync\\b(?=.*--(?:delete\\S*|remove-source-files)).*" + either',
     'rsync\\b(?=.*--(?:delete\\S*|remove-source-files)).*" + target'),
    ("R26 the old parent as before", 'PARENT = HOME + SEP + r"rikuri" + WHOLE', 'PARENT = HOME + SEP + r"rikuri/?(?=[\\"\'\\s;|&)]|$)"'),
    ("R27 core.sparseCheckout ignored", '     r"|\\bconfig\\b.*\\s[\\"\']?(?i:core\\.sparseCheckout(?:Cone)?)\\b"\n', ''),
    ("R28 read-tree ignored", '     r"|\\bgit\\b.*\\bread-tree\\b"\n', ''),
    ("R29 switch --orphan ignored", '     r"|\\bgit\\b.*\\bswitch\\b.*\\s--orphan\\b"\n', ''),
    ("R30 update-index ignored", '(?=.*--(?:skip-worktree|assume-unchanged)\\b).*" + HOOK_FILES', '(?=.*--xx\\b).*" + HOOK_FILES'),
    ("R31 copies into .git ignored", 'COPY_IN = [COPY + r".*" + dest(START + PFX + r"\\.git(?![\\w.-])"),',
     'COPY_IN = [COPY + r".*" + dest(START + PFX + r"\\.gitx(?![\\w.-])"),'),
    ("R32 a folder named hooks ignored", '[^\\s\\"\']*\\bhooks/?[\\"\']?(?=\\s)', '[^\\s\\"\']*\\bhooksx/?[\\"\']?(?=\\s)'),
    ("R33 a folder named quality ignored", '[^\\s\\"\']*\\bquality/?[\\"\']?(?=\\s)', '[^\\s\\"\']*\\bqualityx/?[\\"\']?(?=\\s)'),
    ("R34 the stable-only copy rule gone", 'rule(rx(COPY + r".*" + dest(QUALITY), ', 'rule(rx(r"\\bxx\\b", '),
    ("R35 the >| rule gone", 'rule(r">\\s*$",', 'rule(r"\\bxx\\b",'),
    ("R36 hook names without a right boundary", '"(?:config|hooks))(?![\\w.-])"', '"(?:config|hooks))"'),
    ("R37 mkdir deletes a folder", '|rename|shred|chmod|chown|chgrp)\\b.*" + either', '|rename|shred|chmod|chown|chgrp|mkdir)\\b.*" + either'),
    ("R38 find only -delete", 'r".*\\s-(?:delete|exec|execdir|ok|okdir)\\b"]', 'r".*\\s-(?:delete)\\b"]'),
    ("R39 hook names without //", 'r"(?:scripts" + SEP + r"quality" + SEP + r"hooks|', 'r"(?:scripts/quality/hooks|'),
    ("R40 sparse-checkout list asks", 'sparse-checkout\\b(?!\\s+list\\b)"', 'sparse-checkout\\b"'),
]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


files = (GP, CFG)
orig = {p: open(p, "rb").read() for p in files}
before = {p: sha(p) for p in files}
rows = []
try:
    for name, a, b in MUTANTS:
        src = orig[GP].decode()
        assert src.count(a) == 1, (name, src.count(a))
        mutated = src.replace(a, b)
        compile(mutated, GP, "exec")
        with open(GP, "w") as f:
            f.write(mutated)
        subprocess.run(REGEN, check=True)
        r = subprocess.run(GUARD, capture_output=True, text=True)
        c = subprocess.run(CLAIMS, capture_output=True, text=True)
        n = sum(l.startswith("FAIL:") or l.startswith("ERROR:") for l in r.stderr.splitlines())
        m = re.search(r"(\d+) of \d+ claims do not hold", c.stderr)
        rows.append("%-42s examples %s (%d failing subtests); claims %s (%s)" % (
            name, "RED  " if r.returncode else "GREEN", n, "RED  " if c.returncode else "GREEN",
            m.group(1) + " wrong" if m else "0 wrong"))
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
