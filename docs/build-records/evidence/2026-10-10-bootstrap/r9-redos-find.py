import json, subprocess, sys
cfg = json.load(open(sys.argv[1]))
SLOW = ["git" + " -a" * 60, "git" + " -c x" * 40, "docker" + " --a x" * 60, "cp" + " x" * 300, "rm " + "a/" * 600,
        "lncli" + " --x=y" * 80, "echo " + "'" * 400, "x" * 4000, "git commit" + " -m x" * 60,
        "rsync" + " -a" * 100 + " x /home/junc/rikuri/rikurinode/", "tar" + " -xvf" * 80, " " * 3000 + "rm"]
SLOW += [w + run * 60 for w in ("docker", "podman", "systemctl", "http", "git -C /home/junc/rikuri/rikurinode", "curl",
                                "wget", "lncli", "bitcoin-cli", "gh api", "tar", "cp", "rsync", "sed", "find", "apt",
                                "dnf", "pkill", "kill", "xargs", "sudo", "git", "git config", "tapcli", "loginctl")
         for run in (" --a", " --a x", " -a x", " --a=x", " -c -a", " -C -a")]
code = "import re,sys,time; r=sys.argv[1]; s=sys.argv[2]; t=time.perf_counter(); re.search(r,s); print(round(time.perf_counter()-t,3))"
for i, r in enumerate(cfg["funds_patterns"]):
    for j, s in enumerate(SLOW):
        try:
            out = subprocess.run([sys.executable, "-c", code, r["regex"], s], capture_output=True, text=True, timeout=4)
            dt = float(out.stdout.strip() or "0")
            if dt > 0.25:
                print("SLOW rule %d input %d: %.2fs  %s" % (i, j, dt, r["reason"][:70]))
        except subprocess.TimeoutExpired:
            print("HANG rule %d input %d (>4s): %s | input %r" % (i, j, r["reason"][:70], s[:40]))
