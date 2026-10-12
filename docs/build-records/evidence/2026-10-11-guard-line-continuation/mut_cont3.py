"""Mutants of the continuation fix, round 2, against the files as they will be
committed. Run from the repository root inside safe-run.sh. Python runs with
-B (no bytecode cache: a same-size mutant's stale .pyc can outlive its
restore). Every file is restored and checked by sha256."""
import hashlib
import subprocess
import sys

GUARD_TESTS = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
REGEN = [sys.executable, "-B", "scripts/quality/guard_policy.py"]
G, P, C = ".claude/hooks/guard.py", "scripts/quality/guard_policy.py", ".claude/hooks/guard-config.json"
MUTANTS = [
    # split_segments
    ("M1 no join", G, '            if cmd[i + 1] == "\\n":  # a line continuation: the shell joins the two lines\n'
                      '                i += 2\n                continue\n', ""),
    ("M2 join inside single quotes", G, 'if c == "\\\\" and quote != "\'" and not comment', 'if c == "\\\\" and not comment'),
    ("M3 join inside a comment", G, 'if c == "\\\\" and quote != "\'" and not comment', 'if c == "\\\\" and quote != "\'"'),
    ("M4 no comments", G, "                comment = True\n", "                pass\n"),
    ("M5 quotes open in comments", G, 'elif c in "\'\\"" and not comment:', 'elif c in "\'\\"":'),
    ("M6 \\\" ends a double quote", G, 'if quote is None or cmd[i + 1] in "\\"\\\\$`":', "if quote is None:"),
    ("M7 a comment never ends", G, '            if c == "\\n":\n                comment = False\n', ""),
    ("M8 # anywhere starts a comment", G, 'if c == "#" and word_start:', 'if c == "#":'),
    ("S1 no \\\\ escape in double quotes", G, 'cmd[i + 1] in "\\"\\\\$`"', 'cmd[i + 1] in "\\"$`"'),
    ("S2 TAB is not a word break", G, 'WORD_BREAK = " \\t\\n;&|()<>"', 'WORD_BREAK = " \\n;&|()<>"'),
    ("S3 a comment ends at any separator", G, '            if c == "\\n":\n                comment = False\n',
     "            comment = False\n"),
    ("W1 an escaped char starts a word", G, '                cur.append(cmd[i:i + 2])  # an escaped char (`\\;`, `\\"`) '
     'is not a separator or a quote\n                word_start = False\n',
     '                cur.append(cmd[i:i + 2])  # an escaped char (`\\;`, `\\"`) is not a separator or a quote\n'
     '                word_start = cmd[i + 1] in WORD_BREAK\n'),
    ("W2 $(...) not tracked", G, 'if c == "(" and cur and cur[-1] == "$":', 'if False:'),
    ("T1 no length bound", G, "if isinstance(cmd, str) and len(cmd) > MAX_COMMAND_CHARS:", "if False:"),
    # this repository's policy
    ("P1 rules read only the first line", P, 'return NR + r"[\\s\\S]*?(?:"', 'return NR + r".*?(?:"'),
    ("P2 the read exemption on every line", P, 'NR = (r"(?m)\\A(?!', 'NR = (r"(?m)^(?!'),
    ("P3 no multi-line mode", P, 'NR = (r"(?m)\\A(?!', 'NR = (r"\\A(?!'),
    ("P4 code rule: a backslash at a segment's end", P, '.*?\\\\(?:[ \\t]*\\n|\\\\|n(?![A-Za-z]))',
     '.*?\\\\(?:\\s*$|\\\\|n(?![A-Za-z]))'),
    ("P5 lncli money: first line only", P, 'rule(NR + r"[\\s\\S]*?\\blncli\\b(?!', 'rule(NR + r".*?\\blncli\\b(?!'),
    ("P6 a help word anywhere exempts", P, '[\\s\\S]*?\\bbitcoin-cli\\b(?!(?:\\s+-\\S+)*\\s+help\\b)',
     '(?![\\s\\S]*help)[\\s\\S]*?\\bbitcoin-cli\\b(?!(?:\\s+-\\S+)*\\s+help\\b)'),
    ("P7 a \\n escape is not a line start", P, 'LINE = r"(?:^|\\\\n)"', 'LINE = r"(?:^)"'),
    ("P8 no command after a \\n escape", P, ',\n        r"\\\\n[ \\t]*" + SUDO + CODE_CMDS),', '),'),
    ("P9 echo is not a read", P, "|grep|egrep|fgrep|rg|ag|less|head|tail|echo|printf)\\b)",
     "|grep|egrep|fgrep|rg|ag|less|head|tail|printf)\\b)"),
]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


files = (G, P, C)
orig = {p: open(p, "rb").read() for p in files}
before = {p: sha(p) for p in files}
rows = []
try:
    for name, path, a, b in MUTANTS:
        src = orig[path].decode()
        assert src.count(a) == 1, (name, src.count(a))
        with open(path, "w") as f:
            f.write(src.replace(a, b))
        if path == P:
            subprocess.run(REGEN, check=True)
        r = subprocess.run(GUARD_TESTS, capture_output=True, text=True)
        fails = sorted({l.split("(")[0].split(":", 1)[1].strip() for l in r.stderr.splitlines()
                        if l.startswith(("FAIL:", "ERROR:"))})
        rows.append("%-46s %s %s" % (name, "RED  " if r.returncode else "GREEN", ", ".join(fails)[:150]))
        for p in files:
            with open(p, "wb") as f:
                f.write(orig[p])
finally:
    for p in files:
        with open(p, "wb") as f:
            f.write(orig[p])
    assert {p: sha(p) for p in files} == before
print("\n".join(rows))
print("restored, sha256 checked:", ", ".join("%s %s" % (p, before[p][:12]) for p in files))
