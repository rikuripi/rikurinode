"""Bootstrap rounds 4 to 6 mutants: each must turn a test red. Run from the
repository root inside safe-run.sh. Python runs with -B (no bytecode cache:
round 3's verifier saw a same-size mutant's stale .pyc outlive its restore).
Every file is restored and checked by sha256."""
import hashlib
import subprocess
import sys

QUALITY = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "scripts/quality/tests", "-p", "test_*.py"]
GUARD = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".claude/hooks", "-p", "test_*.py"]
REGEN = [sys.executable, "-B", "scripts/quality/guard_policy.py"]
SR, WI, GP, CFG = ("scripts/quality/safe-run.sh", "scripts/quality/check_guard_wiring.py",
                   "scripts/quality/guard_policy.py", ".claude/hooks/guard-config.json")
MUTANTS = [
    ("S2 no start-time comparison", SR, 'elif [ "$before" != "$after" ]; then', "elif false; then", QUALITY),
    ("S4 no private PID namespace", SR, "--net --pid --fork --mount-proc", "--net --fork", QUALITY),
    ("S5 /run not hidden", SR, "mount -t tmpfs -o mode=755 none /run || ", "true || ", QUALITY),
    ("S6 no pkill stand-in", SR, "         pkill killall; do", "         killall; do", QUALITY),
    ("W3 local settings never read", WI, 'if os.path.exists(".claude/settings.local.json"):', "if False:", QUALITY),
    ("W5 a guard that fails open counts", WI, 'if any(h.get("onFailure") != "block" for h in guards):', "if False:",
     QUALITY),
    ("G1 hooksPath case-sensitive", GP, 'HOOKSPATH = r"[\\"\']?(?i:core\\.hooksPath)\\b"',
     'HOOKSPATH = r"[\\"\']?core\\.hooksPath\\b"', GUARD),
    ("G2 no --no-verify prefixes", GP, 'NO_VERIFY = r"--no-veri(?:fy?)?\\b"', 'NO_VERIFY = r"--no-verify\\b"', GUARD),
    ("G3 GIT_CONFIG_* ignored", GP, 'r"|\\bGIT_CONFIG_(?:COUNT|KEY_\\d+|PARAMETERS)\\b"', 'r""', GUARD),
    ("G4 --config-env ignored", GP, '(?:-c\\s*|--config-env[=\\s]\\s*)', '(?:-c\\s*)', GUARD),
    ("G10 any value starting with the install path", GP,
     'INSTALL = r"[\\"\']?(?:\\./|\\$PWD/|\\$\\{PWD\\}/)?scripts/quality/hooks/?[\\"\']?(?:\\s|$)"',
     'INSTALL = r"scripts/quality/hooks"', GUARD),
    ("G10b install only as written", GP, '(?:\\./|\\$PWD/|\\$\\{PWD\\}/)?scripts/quality/hooks/?', 'scripts/quality/hooks/?', GUARD),
    ("G12 -c include/alias ignored", GP, '(?:" + HOOKSPATH + "|" + INDIRECT + "))"', '" + HOOKSPATH + ")"', GUARD),
    ("G13 config include/alias ignored", GP, '+ r"|\\bconfig\\b.*\\s" + INDIRECT + r"\\S*(?:\\s+|=)\\S"\n', '+ r""\n', GUARD),
    ("G14 core section removal ignored", GP, 'r"|\\bconfig\\b.*\\b(?:remove|rename)-section\\s+[\\"\']?(?i:core)\\b"\n', '\n', GUARD),
    ("G15 config --edit ignored", GP, 'r"|\\bgit\\b.*\\bconfig\\b.*\\s(?:-e|--edit|edit)\\b"\n', '\n', GUARD),
    ("V8 config -e ignored (--edit kept)", GP, '(?:-e|--edit|edit)\\b"', '(?:--edit|edit)\\b"', GUARD),
    ("V10 the core section case-sensitive", GP, '[\\"\']?(?i:core)\\b"', '[\\"\']?core\\b"', GUARD),
    ("V7 git apply/reset of the hook ignored", GP, '(?:rm|mv|checkout|restore|apply|reset|stash)', '(?:rm|mv|checkout|restore|stash)', GUARD),
    ("G16 git writes of the hook ignored", GP,
     '+ r"|\\bgit\\b.*\\b(?:rm|mv|checkout|restore|apply|reset|stash)\\b.*(?:" + HOOK_FILES + "|" + HOOK_PARENTS + ")"\n', '+ r""\n', GUARD),
    ("R1 parent folders ignored", GP, '"|".join(writes(HOOK_FILES, HOOK_PARENTS))', '"|".join(writes(HOOK_FILES))', GUARD),
    ("R2 parents count for copies too", GP, 'either = "(?:" + target + ("|" + parent if parent else "") + ")"',
     'either = "(?:" + target + ("|" + parent if parent else "") + ")"; target = either', GUARD),
    ("R3 find -delete only on the target", GP, 'r"\\bfind\\b.*" + either', 'r"\\bfind\\b.*" + target', GUARD),
    ("R4 awk -i inplace ignored", GP, '            r"\\bawk\\b.*-i\\s*inplace\\b.*" + target,\n', '', GUARD),
    ("R5 patch ignored", GP, '|unlink|mkdir|patch"', '|unlink|mkdir"', GUARD),
    ("G18 perl -i ignored", GP, '            r"\\bperl\\b(?=.*\\s-[A-Za-z]*i).*\\s[\\"\']?" + target,\n', '', GUARD),
]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


files = {SR, WI, GP, CFG}
orig = {p: open(p, "rb").read() for p in files}
before = {p: sha(p) for p in files}
rows = []
try:
    for name, path, a, b, tests in MUTANTS:
        src = orig[path].decode()
        assert src.count(a) == 1, (name, src.count(a))
        with open(path, "w") as f:
            f.write(src.replace(a, b))
        if path == GP:
            subprocess.run(REGEN, check=True)
        r = subprocess.run(tests, capture_output=True, text=True)
        fails = sorted({l.split("(")[0].split(":", 1)[1].strip() for l in r.stderr.splitlines()
                        if l.startswith(("FAIL:", "ERROR:"))})
        rows.append("%-34s %s %s" % (name, "RED  " if r.returncode else "GREEN", ", ".join(fails)))
        for p in files:
            with open(p, "wb") as f:
                f.write(orig[p])
finally:
    for p in files:
        with open(p, "wb") as f:
            f.write(orig[p])
    assert {p: sha(p) for p in files} == before
print("\n".join(rows))
print("restored, sha256 checked:", ", ".join("%s %s" % (p, before[p][:12]) for p in sorted(files)))
