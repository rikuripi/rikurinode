import re, sys
rank = {"allow": 0, "ask": 1, "deny": 2}
for path in sys.argv[1:]:
    t = open(path).read()
    looser, tighter, n = [], [], 0
    for blk in t.split("### ")[1:]:
        lab = blk.split("\n")[0]
        m = dict(re.findall(r"(p9-dev|old-dev|p9-stab|old-stab)=(\w+)", blk))
        want = re.search(r"want=(.*)", blk).group(1)
        n += 1
        for p in ("dev", "stab"):
            a, b = m["p9-" + p], m["old-" + p]
            if rank.get(a, -1) < rank.get(b, -1):
                looser.append((lab, p, a, b, want))
            elif rank.get(a, -1) > rank.get(b, -1):
                tighter.append((lab, p, a, b))
    print("== %s: %d cases; looser than 2075218: %d; tighter: %d" % (path.split("/")[-1], n, len(looser), len(tighter)))
    for x in looser:
        print("   looser  %s [%s] new=%s old=%s want=%s" % x)
    for x in tighter:
        print("   tighter %s [%s] new=%s old=%s" % x)
