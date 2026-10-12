import hashlib, subprocess, sys
G, C = "scripts/quality/guard_policy.py", ".claude/hooks/guard-config.json"
og, oc = open(G, "rb").read(), open(C, "rb").read()
hg, hc = hashlib.sha256(og).hexdigest(), hashlib.sha256(oc).hexdigest()
src = og.decode()
MUTANTS = {
 "P1 rules read only the first line": ('return NR + r"[\\s\\S]*?(?:"', 'return NR + r".*?(?:"'),
 "P2 the read exemption on every line": ('NR = (r"(?m)\\A(?!', 'NR = (r"(?m)^(?!'),
 "P3 no multi-line mode": ('NR = (r"(?m)\\A(?!', 'NR = (r"\\A(?!'),
 "P4 code-escape rule: backslash at a segment's end": ('.*?\\\\(?:[ \\t]*\\n|\\\\|n(?![A-Za-z]))', '.*?\\\\(?:\\s*$|\\\\|n(?![A-Za-z]))'),
 "P5 lncli money: first line only": ('rule(NR + r"[\\s\\S]*?\\blncli\\b(?!', 'rule(NR + r".*?\\blncli\\b(?!'),
 "P7 a \\n escape in code is not a line start": ('LINE = r"(?:^|\\\\n)"', 'LINE = r"(?:^)"'),
 "P6 bitcoin-cli money: help anywhere exempts": ('[\\s\\S]*?\\bbitcoin-cli\\b(?!(?:\\s+-\\S+)*\\s+help\\b)', '(?![\\s\\S]*help)[\\s\\S]*?\\bbitcoin-cli\\b(?!(?:\\s+-\\S+)*\\s+help\\b)'),
}
out = []
try:
    for name, (a, b) in MUTANTS.items():
        assert src.count(a) == 1, (name, src.count(a))
        open(G, "w").write(src.replace(a, b))
        subprocess.run([sys.executable, G], check=True)
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"],
                           capture_output=True, text=True)
        last = [l for l in r.stderr.splitlines() if l.startswith(("FAILED", "OK"))]
        out.append("%-50s %s %s" % (name, "RED  " if r.returncode else "GREEN", last[-1] if last else r.stderr[-300:]))
finally:
    open(G, "wb").write(og); open(C, "wb").write(oc)
    assert hashlib.sha256(open(G, "rb").read()).hexdigest() == hg and hashlib.sha256(open(C, "rb").read()).hexdigest() == hc
print("\n".join(out)); print("restored", hg[:12], hc[:12])
