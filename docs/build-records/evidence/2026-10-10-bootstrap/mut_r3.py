import hashlib, subprocess, os
os.chdir('/home/junc/rikuripi/rikurinode')
W='scripts/quality/check_guard_wiring.py'; R='scripts/quality/safe-run.sh'; H='scripts/quality/repo_hygiene.py'
T=lambda name: ['python3','-m','unittest','discover','-s','scripts/quality/tests','-p',name]
M=[('W1 disableAllHooks ignored', W, '    if settings.get("disableAllHooks"):\n', '    if False:\n', T('test_guard_wiring.py')),
   ('W2 a command that mentions the guard counts', W, '            if GUARD in commands:\n', '            if any("guard.py" in (c or "") for c in commands):\n', T('test_guard_wiring.py')),
   ('W3 the matcher ignored', W, '                covered |= TOOLS if matcher in ("", "*") else set(matcher.split("|"))\n', '                covered |= TOOLS\n', T('test_guard_wiring.py')),
   ('W4 every event counts, PostToolUse too', W, '        for entry in (settings.get("hooks") or {}).get("PreToolUse") or []:\n', '        for entry in [e for v in (settings.get("hooks") or {}).values() for e in v]:\n', T('test_guard_wiring.py')),
   ('W5 unreadable settings pass', W, '        return ["%s: cannot read the settings (%s)" % (path, e)]\n', '        return []\n', T('test_guard_wiring.py')),
   ('R1 network shared', R, 'NS=(unshare --user --map-root-user --mount --net --pid --fork --mount-proc)', 'NS=(unshare --user --map-root-user --mount --pid --fork --mount-proc)', T('test_safe_run.py')),
   ('R2 /run not hidden', R, "inner='mount -t tmpfs -o mode=755 none /run || { echo \"safe-run: cannot hide /run\" >&2; exit 2; }", "inner='true", T('test_safe_run.py')),
   ('R3 processes shared', R, 'NS=(unshare --user --map-root-user --mount --net --pid --fork --mount-proc)', 'NS=(unshare --user --map-root-user --mount --net)', T('test_safe_run.py')),
   ('R4 no namespace: runs anyway', R, 'elif [ "${SAFE_RUN_ALLOW_NO_NAMESPACE:-}" = 1 ]; then', 'elif true; then', T('test_safe_run.py')),
   ('R5 pkill not stood in', R, '         pkill killall; do', '         killall; do', T('test_safe_run.py')),
   ('R6 stand-ins after PATH', R, '  PATH="$bin:$PATH" DOCKER_HOST="unix:///nonexistent/rikuri-safe-run.sock" SAFE_RUN_MODE="namespace" \\', '  PATH="$PATH:$bin" DOCKER_HOST="unix:///nonexistent/rikuri-safe-run.sock" SAFE_RUN_MODE="namespace" \\', T('test_safe_run.py')),
   ('H1 any digit is a version', H, '    if not re.search(r"\\d+\\.\\d+", tag):  # at least major.minor: "3", "20-alpine", "lts" float\n', '    if not re.search(r"\\d", tag):\n', T('test_repo_hygiene.py')),
   ('H2 COPY --from not checked', H, '            c = re.match(r"^\\s*COPY\\s+.*--from=(\\S+)", line, re.I)\n', '            c = None\n', T('test_repo_hygiene.py')),
   ('H3 fixtures exempt a root runtime folder', H, '        if by_name or set(anywhere) & set(dirs) or (dirs and dirs[0] in at_root):\n', '        if by_name or ((set(anywhere) & set(dirs) or (dirs and dirs[0] in at_root)) and not in_fixtures):\n', T('test_repo_hygiene.py')),
   ('H4 target anywhere', H, '    (BUILD, ["*.pyc"], ["node_modules", "dist", "__pycache__", ".venv"], ["target"]),\n', '    (BUILD, ["*.pyc"], ["node_modules", "dist", "__pycache__", ".venv", "target"], []),\n', T('test_repo_hygiene.py'))]
import sys
if len(sys.argv)>1: M=[m for m in M if m[0].split()[0] in sys.argv[1:]]
red=0
for name,p,o,n,cmd in M:
    orig=open(p).read(); h=hashlib.sha256(orig.encode()).hexdigest()
    assert orig.count(o)==1,(name,orig.count(o))
    open(p,'w').write(orig.replace(o,n))
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        ok=r.returncode!=0; red+=ok
        print('RED ' if ok else 'SURVIVED', name, '|', (r.stderr.strip().splitlines() or ['?'])[-1], flush=True)
    finally:
        open(p,'w').write(orig); assert hashlib.sha256(open(p,'rb').read()).hexdigest()==h, name
print('red: %d of %d; every file restored (sha256 checked)' % (red, len(M)))
