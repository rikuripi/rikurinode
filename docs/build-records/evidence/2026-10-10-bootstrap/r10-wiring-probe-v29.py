"""Verifier round 9: does check_guard_wiring.py refuse each weakening? Each
variant is the committed .claude/settings.json with one change, checked as the
project file (full) and, where it is a local-file change, as settings.local.json
beside the committed project file (the gate's default run)."""
import copy, json, os, subprocess, sys, tempfile
REPO = sys.argv[1]
CHECK = os.path.join(REPO, "scripts/quality/check_guard_wiring.py")
base = json.load(open(os.path.join(REPO, ".claude/settings.json")))
def setin(d, path, value):
    for k in path[:-1]:
        d = d.setdefault(k, {})
    d[path[-1]] = value
V = [  # (name, path, value) — each is a weakening per Claude Code 2.1.295's settings schema
 ("network.allowedDomains += *", ("sandbox", "network", "allowedDomains"), ["github.com", "api.github.com", "*.githubusercontent.com", "*"]),
 ("network.allowedDomains += example.com", ("sandbox", "network", "allowedDomains"), ["github.com", "example.com"]),
 ("network.httpProxyPort (own proxy, no filtering)", ("sandbox", "network", "httpProxyPort"), 3128),
 ("network.socksProxyPort (own proxy)", ("sandbox", "network", "socksProxyPort"), 1080),
 ("filesystem.allowRead re-opens .env", ("sandbox", "filesystem", "allowRead"), ["/home/junc/rikuri/rikurinode/.env"]),
 ("filesystem.allowRead re-opens data/", ("sandbox", "filesystem", "allowRead"), ["/home/junc/rikuri/rikurinode/data"]),
 ("permissions.allow Edit(...) (merged into allowWrite)", ("permissions", "allow"), ["Edit(//home/junc/rikuri/**)"]),
 ("permissions.allow WebFetch(domain:*) (merged into allowedDomains)", ("permissions", "allow"), ["WebFetch(domain:*)"]),
 ("ignoreViolations {*: [/]}", ("sandbox", "ignoreViolations"), {"*": ["/"]}),
 ("denyWrite emptied (control)", ("sandbox", "filesystem", "denyWrite"), []),
 ("allowWrite (control)", ("sandbox", "filesystem", "allowWrite"), ["/home/junc"]),
 ("allowUnixSockets (control)", ("sandbox", "network", "allowUnixSockets"), ["/var/run/docker.sock"]),
 ("enabled as string 'true'", ("sandbox", "enabled"), "true"),
 ("excludedCommands git push * plus bash *", ("sandbox", "excludedCommands"), ["git push *", "bash *"]),
 ("excludedCommands git * ", ("sandbox", "excludedCommands"), ["git *"]),
 ("network section as a string", ("sandbox", "network"), "x"),
 ("hooks PreToolUse second entry with guard but matcher empty-string + disable via env", ("env",), {"CLAUDE_CODE_DISABLE_SANDBOX": "1"}),
]
def run(project, local=None):
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".claude"))
        json.dump(project, open(os.path.join(d, ".claude/settings.json"), "w"))
        if local is not None:
            json.dump(local, open(os.path.join(d, ".claude/settings.local.json"), "w"))
        p = subprocess.run([sys.executable, "-B", CHECK], cwd=d, capture_output=True, text=True)
        return p.returncode, (p.stderr.strip().splitlines() or [""])[-1][:150]
print("baseline committed settings:", run(base))
for name, path, value in V:
    full = copy.deepcopy(base); setin(full, path, value)
    rc_full, msg_full = run(full)
    local = {}; setin(local, path, value)
    rc_loc, msg_loc = run(base, local)
    print("%-62s project-file: %s %-8s local-file: %s %-8s | %s | %s" % (name, rc_full, "REFUSED" if rc_full else "PASSES", rc_loc,
          "REFUSED" if rc_loc else "PASSES", msg_full, msg_loc))