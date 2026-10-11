"""Bootstrap rounds 4 to 7 mutants: each must turn a test red. Run from the
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
    ("E1 a destination's tail ignored", GP, '-\\S+|&))*"', '-\\S+|&)){0}"', GUARD),
    ("E2 a trailing & ends the destination", GP, '|-\\S+|&))*"', '|-\\S+))*"', GUARD),
    ("E3 a closing quote ends no destination", GP, '(?:\\s*(?:$|&&|\\|\\||;|\\|)|[\\"\'])', '(?:\\s*(?:$|&&|\\|\\||;|\\|))', GUARD),
    ("H1 hook files without a word start", GP, 'HOOK_FILES = r"(?<![\\w.-])', 'HOOK_FILES = r"', GUARD),
    ("H2 hook folders by prefix", GP, '/?\\*?(?=[\\s\\"\';|&)]|$)"', '"', GUARD),
    ("H3 rmdir of a hook folder ignored", GP, '(?:rm|rmdir|mv)\\b.*" + HOOK_PARENTS', '(?:rm|mv)\\b.*" + HOOK_PARENTS', GUARD),
    ("H4 extracting into a hook folder ignored", GP, '(?:tar|unzip|7z|cpio)\\b.*(?:-C\\s*|-d\\s*|-D\\s*|--directory[= ]|-o)[\\"\']?" + HOOK_PARENTS',
     '(?:tar)\\b.*(?:-C\\s*)[\\"\']?" + HOOK_PARENTS', GUARD),
    ("H5 find -delete under a hook folder ignored", GP, '+ r"|\\bfind\\b.*" + HOOK_PARENTS + r".*\\s-(?:delete|exec|execdir|ok|okdir)\\b"\n', '+ r""\n', GUARD),
    ("H6 git stash of the hook ignored", GP, '(?:rm|mv|checkout|restore|apply|reset|stash)', '(?:rm|mv|checkout|restore|apply|reset)', GUARD),
    ("H7 sparse checkout ignored", GP, 'r"|\\bgit\\b.*\\bsparse-checkout\\b(?!\\s+list\\b)"\n', '\n', GUARD),
    ("O1 cpio ignored", GP, '|unlink|mkdir|patch"\n            r"|cpio|ex', '|unlink|mkdir|patch"\n            r"|ex', GUARD),
    ("O2 7z ignored", GP, '(?:tar|unzip|7z)\\b.*(?:-C', '(?:tar|unzip)\\b.*(?:-C', GUARD),
    ("O3 tar --directory ignored", GP, '(?:-C\\s*|-d\\s*|--directory[= ]|-o)', '(?:-C\\s*|-d\\s*|-o)', GUARD),
    ("O4 editors ignored", GP, '|cpio|ex|vi|vim|nvim|nano|ed|emacs)', '|cpio|ex)', GUARD),
    ("O5 shred and unlink ignored", GP, 'ln|install|dd|shred|unlink|mkdir', 'ln|install|dd|mkdir', GUARD),
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
