"""Round 10: inputs built against the new rules' shapes (a node tool's words and
options, inspect templates, compose options, host prefixes, continued lines,
process substitution), run against every rule in a child with a timeout."""
import json, subprocess, sys
cfg = json.load(open(sys.argv[1]))
N = int(sys.argv[2]) if len(sys.argv) > 2 else 1
NEW = ["lncli getinfo" + " x" * 1500 + " $", "lncli" + " -n x" * 500 + " getinfo!", "lncli" + " --network=x" * 600 + " ;x",
       "docker inspect" + " -f" * 800 + " '", "docker inspect -f '" + "{{.State}}" * 400 + "' x!",
       "docker inspect --format " + "'{{.State}} '" * 300 + " x $", "docker compose" + " -f x" * 600 + " ps!",
       "docker compose" + " --file=x" * 600 + " config", "bitcoin-cli" + " -named" * 700 + " getblock!",
       "bitcoin-cli" + " -rpcwallet=x" * 600 + " getbalances $(", "which" + " lncli" * 1200 + " $(", "ls " + "a/" * 2500 + "lncli(",
       "echo " + "\\" * 4000 + "x", "x " + "\\\\\\n" * 1200 + "y", "cp x " + "a:" * 1500 + "/home/junc/rikuri/x",
       "scp x " + "h:'" * 1200, "sed -n 1p" + " f" * 1500 + " -i", "sed -n '1p'" + " /home/junc/rikuri/x" * 300 + " >",
       "git commit" + " -F" * 800 + " /home/junc/rikuri/x", "rsync" + " -e" * 800 + " /home/junc/rikuri/x",
       "cat " + "<(" * 1500, "cat " + "=(" * 1500 + "lncli", "journalctl" + " --x" * 1200 + " docker&",
       "lncli getinfo" + " 'a'" * 1200 + " $", " " * 6000 + "lncli", "lncli " * 1200, "docker ps --format '" + "{" * 4000 + "'",
       "systemctl status" + " docker" * 1200 + " $(", "tapcli" + " -n x" * 600 + " assets list!", "litcli" + " getinfo" * 1000,
       "${HOME" + ":" * 3000 + "}/rikuri", "rm -rf ${PWD" + "%" * 3000 + "}/scripts", "rm -rf `" + "x" * 3000 + "`/scripts",
       "grep x " + "<(" * 800 + "lncli sendcoins", "echo a >" + " \\\n" * 1500, "git grep" + " -n" * 1200 + "O",
       "cp" + " -a" * 1500 + " /home/junc/rikuri/rikurinode/x ./x", "docker" + " logs x" * 800 + " 2>&1 $"]
code = ("import re,sys,time; r=sys.argv[1]; s=sys.argv[2]; n=int(sys.argv[3]); s=s*n if n>1 else s; "
        "t=time.perf_counter(); re.search(r,s); print(round(time.perf_counter()-t,3))")
worst = (0, "", "")
for i, r in enumerate(cfg["funds_patterns"]):
    for j, s in enumerate(NEW):
        try:
            out = subprocess.run([sys.executable, "-c", code, r["regex"], s, str(N)], capture_output=True, text=True,
                                 timeout=4)
            dt = float(out.stdout.strip() or "0")
            if dt > worst[0]:
                worst = (dt, r["reason"][:60], s[:30])
            if dt > 0.25:
                print("SLOW rule %d input %d: %.2fs  %s | %r" % (i, j, dt, r["reason"][:70], s[:40]))
        except subprocess.TimeoutExpired:
            print("HANG rule %d input %d (>4s): %s | input %r" % (i, j, r["reason"][:70], s[:40]))
print("%d rules x %d inputs; worst %.3fs (%s | %r)" % (len(cfg["funds_patterns"]), len(NEW), *worst))
