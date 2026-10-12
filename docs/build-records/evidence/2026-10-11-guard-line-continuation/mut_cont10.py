"""Round 4 mutants of the continuation fix: each must turn a test red. Run from
the root of a scratch copy of the tree (never the worktree) inside safe-run.sh
with Python -B; every file is restored and checked by sha256. V2, V10, V16,
V18, V20 and V21 are the round-3 verifier's surviving mutants (its
mut_mine.py), replayed on round 4's code. The first run had D3 (a backtick
inside double quotes not tracked) green: it changed a verdict only for
commands with an unclosed backtick, which bash does not run; the code was
removed as equivalent. Two more stayed green in that run (mut-cont10-first-run.out),
both kept as code and recorded: V16 is equivalent now (`_end_segment` also drops
a comment's last backslash), and J4 can only make an override rarer (stricter)."""
import hashlib
import subprocess
import sys

GUARD = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
G = ".claude/hooks/guard.py"
M = [
    # comments only outside a substitution
    ("D1 a comment inside a substitution", G, 'if c == "#" and word_start and not subst and not tick:',
     'if c == "#" and word_start:'),
    ("D2 a backtick not tracked", G, '                elif c == "`":\n                    tick, word_start = not tick, False\n', ''),
    ("D4 no note of a comment in a substitution", G, 'notes.append("comment-in-substitution")', 'pass'),
    ("D5 the note only at a substitution's start", G, '(not cur or cur[-1] in WORD_BREAK + "(`")', '(not cur)'),
    ("D6 a note does not ask", G, '    if notes:\n        hits.append(', '    if False:\n        hits.append('),
    # the end of a segment
    ("E1 an escaped blank stripped", G, '        elif len(t) < len(text.lstrip()):', '        elif False:'),
    ("E2 a comment's backslash kept", G, '        if in_comment:\n            t = t[:-1].rstrip()',
     '        if False:\n            t = t[:-1].rstrip()'),
    ("E3 any run of backslashes", G, 'if (len(t) - len(t.rstrip("\\\\"))) % 2:', 'if (len(t) - len(t.rstrip("\\\\"))):'),
    # substitutions and heredocs
    ("S1 an unclosed substitution loses its last character", G,
     '_balanced(seg, m.end() - 1, open_end=True, shell=shell)', '_balanced(seg, m.end() - 1, shell=shell)'),
    ("H1 the command without its heredoc bodies not judged", G,
     'for seg in split_segments("\\n".join(shell)) + [', 'for seg in ['),
    ("H2 a heredoc body's lines not judged on their own", G,
     ' + [s for _tag, body, _at in bodies for line in body.split("\\n")\n                                                       for s in split_segments(line)]:',
     ':'),
    # the previous guard judges the joined command (owner: "Judge as one line")
    ("J1 a continuation not recorded", G,
     '                if joins is not None:\n                    joins.append(i)\n                i += 2', '                i += 2'),
    ("J2 a final backslash not recorded", G,
     '            if joins is not None:\n                joins.append(i)\n            i += 1', '            i += 1'),
    ("J3 the previous guard given the command as written", G,
     '        base_event = dict(event, tool_input=dict(event["tool_input"], command=_joined(cmd)))', '        pass'),
    ("J4 the overrides read the command as written", G, '_overridable(r, base_event,', '_overridable(r, event,'),
    # a lone & ends a command (round 4's fuzzer)
    ("A1 a lone & not a separator", G, 'or (c == "&" and cur[-1:] not in (["<"], [">"])',
     'or (False and cur[-1:] not in (["<"], [">"])'),
    ("A2 |& keeps its &", G, ' or cmd.startswith("|&", i):\n                i += 1', ':\n                i += 1'),
    ("A3 >& and <& split", G, 'cur[-1:] not in (["<"], [">"])', 'True'),
    ("A4 &> split", G, '                                                         and cmd[i + 1:i + 2] != ">"):',
     '                                                         ):'),
    # the previous guard's line-by-line deny (round 4's fuzzer)
    ("L1 a line-by-line deny dropped", G, '            if lines[0] == "deny":\n                base = lines',
     '            if False:\n                base = lines'),
    ("L2 line-by-line asks kept", G, '            if lines[0] == "deny":', '            if RANK[lines[0]] > RANK[base[0]]:'),
    # a substitution read with the shell's escapes, and as before
    ("B1 no shell escapes in _balanced", G, 'if shell and c == "\\\\" and quote != "\'":', 'if False:'),
    ("B2 escapes inside single quotes", G, 'if shell and c == "\\\\" and quote != "\'":', 'if shell and c == "\\\\":'),
    ("B3 only the shell's reading", G, "        for shell in (True, False):", "        for shell in (True,):"),
    ("B4 only the plain reading", G, "        for shell in (True, False):", "        for shell in (False,):"),
    # the timer
    ("T1 a deny found in time lost", G, 'return new if new[0] == "deny" else TOO_SLOW', 'return TOO_SLOW'),
    ("V2 disarm leaves the timer running", G,
     "        signal.setitimer(signal.ITIMER_REAL, 0)\n        signal.signal(signal.SIGALRM, old)",
     "        signal.signal(signal.SIGALRM, old)"),
    ("V10 the new checks' timer at the overall budget", G, "        new = _timed(_DEADLINE_ALL - time.time(), lambda",
     "        new = _timed(OVERALL_TIME_BUDGET, lambda"),
    # word starts (round 3's survivors)
    ("V16 the trailing-backslash rule also in a comment", G,
     'if c == "\\\\" and quote != "\'" and not comment and i + 1 == len(cmd):',
     'if c == "\\\\" and quote != "\'" and i + 1 == len(cmd):'),
    ("V18 no word start after a separator", G, "            cur, word_start = [], True", "            cur, word_start = [], False"),
    ("V20 ( not a word break", G, 'WORD_BREAK = " \\t\\n;&|()<>"', 'WORD_BREAK = " \\t\\n;&|)<>"'),
    ("V21 ) not a word break", G, 'WORD_BREAK = " \\t\\n;&|()<>"', 'WORD_BREAK = " \\t\\n;&|(<>"'),
]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


files = (G,)
orig = {p: open(p, "rb").read() for p in files}
before = {p: sha(p) for p in files}
for name, path, a, b in M:
    assert orig[path].decode().count(a) == 1, (name, orig[path].decode().count(a))
if "--check" in sys.argv:
    print(len(M), "mutants apply")
    sys.exit(0)
ONLY = [a for a in sys.argv[1:] if not a.startswith("--")]
try:
    for name, path, a, b in M:
        if ONLY and name.split()[0] not in ONLY:
            continue
        src = orig[path].decode().replace(a, b)
        compile(src, path, "exec")
        open(path, "w").write(src)
        r = subprocess.run(GUARD, capture_output=True, text=True, timeout=900)
        fails = sorted({l.split("(")[0].split(":", 1)[1].strip() for l in r.stderr.splitlines()
                        if l.startswith(("FAIL:", "ERROR:"))})
        print("%-52s %s %s" % (name, "RED  " if r.returncode else "GREEN", ", ".join(fails)), flush=True)
        for p in files:
            open(p, "wb").write(orig[p])
finally:
    for p in files:
        open(p, "wb").write(orig[p])
    assert {p: sha(p) for p in files} == before
print("restored, sha256 checked:", ", ".join("%s %s" % (p, before[p][:12]) for p in files))
