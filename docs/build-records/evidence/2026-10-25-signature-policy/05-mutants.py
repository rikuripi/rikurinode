"""Hand mutants of check_signature_policy: each weakens one rule; the suite must fail on each.
Run from image/: python3 -I <this> (writes each mutant over check_image_root.py, runs the
tests, restores the file)."""
import os
import subprocess
import sys

MUTANTS = {
    "m1 a key twice is not refused": ("object_pairs_hook=_unique_keys", "object_pairs_hook=dict"),
    "m2 only the image's scope is compared": ("    if policy != POLICY_EXPECTED:",
        '    if policy.get("transports", {}).get("docker") != POLICY_EXPECTED["transports"]["docker"]:'),
    "m3 registries.d: printable ASCII not required": ("        if not PRINTABLE_LINE.match(line):\n            problems.append(\"line %d: outside printable ASCII (a tab included)\"",
        "        if False:\n            problems.append(\"line %d: outside printable ASCII (a tab included)\""),
    # m4 (the policy's printable-ASCII rule) survived the first run: the rule was redundant and is gone.
    "m5 another registries.d file may name the image": ('if b"rikuripi" in f.read():', "if False:"),
    "m6 a link in registries.d is free": ("        if stat.S_ISLNK(st.st_mode):\n            found.append(\"%s: a link; containers/image",
        "        if False:\n            found.append(\"%s: a link; containers/image"),
    "m7 the keys' SHA-256 are not compared": ("hashlib.sha256(data).hexdigest() != want", "False"),
    "m8 root may be any link": ("if target not in ROOT_HOME_LINKS:", "if False:"),
    "m9 root's containers config is free": ("        if problem:\n            found.append(\"%s: %s\" % (rel, problem))\n    return found",
        "        if False:\n            found.append(\"%s: %s\" % (rel, problem))\n    return found"),
    "m10 not wired into check_root": ("+ check_signature_policy(root) +", "+"),
    "m11 the registries.d file is not compared": ("if not problems and kept != REGISTRIES_D_LINES:", "if False:"),
}

src = open("check_image_root.py").read()
bad = 0
try:
    for name, (old, new) in MUTANTS.items():
        assert src.count(old) == 1, name
        open("check_image_root.py", "w").write(src.replace(old, new))
        r = subprocess.run([sys.executable, "-I", "tests/test_check_image_root.py"], capture_output=True, text=True)
        last = [l for l in r.stderr.splitlines() if l.startswith(("FAILED", "OK"))]
        killed = r.returncode != 0
        bad += not killed
        print("%-48s %s  %s" % (name, "KILLED" if killed else "SURVIVED", last[-1] if last else "?"))
finally:
    open("check_image_root.py", "w").write(src)
r = subprocess.run([sys.executable, "-I", "tests/test_check_image_root.py"], capture_output=True, text=True)
print("restored:", [l for l in r.stderr.splitlines() if l.startswith(("FAILED", "OK"))][-1])
sys.exit(1 if bad else 0)
