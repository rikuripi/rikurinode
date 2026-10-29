#!/usr/bin/env python3
"""2c's hand mutants: each weakens one new rule; the tests must fail (not error on import).

Run in a copy of the repository (rikuri-drill): python3 -I 02-mutants.py <copy>
"""
import os
import subprocess
import sys

ROOT = sys.argv[1]
DRILL, SP = "image/drill/vm_drill.py", "image/drill/signature_policy.py"
IMG, PUB = ".github/workflows/image.yml", ".github/workflows/publish.yml"
TESTS = ["image/tests/test_vm_drill.py", "image/tests/test_signature_policy.py",
         "scripts/quality/tests/test_workflows.py"]
MUTANTS = [
    ("m1 no forward to the registry", DRILL, ",guestfwd=tcp:%s-tcp:%s\"\n            % (port, MIRROR_IN_VM, sp.REG)",
     "\" % port"),
    ("m2 the forward to any host", DRILL, "guestfwd=tcp:%s-tcp:%s", "guestfwd=tcp:%s-tcp:0.0.0.0:%s"),
    ("m3 a mirror, not a rewrite", DRILL, '\\nlocation = "%s"\\ninsecure', '\\nlocation = "%s"\\nmirror = 1\\ninsecure'),
    ("m4 the published image by tag", DRILL, '"docker://%s@%s" % (sp.IMAGE_REPO, SIGNED_DIGEST)',
     '"docker://%s:44.20261029.1" % sp.IMAGE_REPO'),
    ("m5 digests not kept", DRILL, '"--preserve-digests", "--dest-tls-verify=false", src', '"--dest-tls-verify=false", src'),
    ("m6 a copy with a login", DRILL, '"--remove-signatures",', '"--remove-signatures", "--authfile=/run/a.json",'),
    ("m7 any refusal counts", DRILL, "sp.miss(returncode, output, sp.NO_SIGNATURE) is None", "returncode != 0"),
    ("m8 a staged update after a refusal passes", DRILL,
     "and booted(status) is not None\n            and staged(status) is None)", "and booted(status) is not None)"),
    ("m9 an unreadable status passes the refusal", DRILL,
     " and booted(status) is not None\n", "\n"),
    ("m10 any digest staged", DRILL, "staged(status) == (SIGNED_REF, SIGNED_DIGEST)", "staged(status)[0] == SIGNED_REF"),
    ("m11 the spec not compared", DRILL, " and spec_image(status) == SIGNED_REF", ""),
    ("m12 a failed switch passes case 5", DRILL, "return returncode == 0 and staged", "return staged"),
    ("m13 case 4 judged without its rule", DRILL, 'refused", unsigned_refused(rc, out, status)', 'refused", True'),
    ("m14 case 5 judged without its rule", DRILL, 'staged", signed_staged(rc, status)', 'staged", rc == 0'),
    ("m15 case 5 not required", DRILL, ', "case 5, a signed update staged"})', "})"),
    ("m16 another pinned digest", DRILL, "c984d651db4f15be5dac56fcd974d230bc248536fade4ceee29323abadfdecfd",
     "c984d651db4f15be5dac56fcd974d230bc248536fade4ceee29323abadfdecfe"),
    ("m17 the shipped file unrenamed", DRILL, "sp.REGISTRIES_D_FILE) or \"\", MIRROR_REPO)", "sp.REGISTRIES_D_FILE) or \"\")"),
    ("m18 the rename ignores its address", SP, 'return shipped.replace(IMAGE_REPO + ":", repo + ":")',
     'return shipped.replace(IMAGE_REPO + ":", LOCAL_REPO + ":")'),
    ("m19 the registry on every address", SP, '"log:\\n  level: error\\n" % (workdir, REG))',
     '"log:\\n  level: error\\n" % (workdir, ":5000"))'),
    ("m20 the drill's registry unchecked", IMG, "printf '%s  registry.tar.gz\\n' \"$DISTRIBUTION_SHA256\" | sha256sum --strict -c -\n",
     ""),
    ("m21 image.yml's drill without the registry", IMG,
     ' \\\n            --registry "$RUNNER_TEMP/sig-tools/registry"', ""),
    ("m22 publish.yml's drill without the registry", PUB,
     ' \\\n            --registry "$RUNNER_TEMP/sig-tools/registry"', ""),
]


def run_tests():
    out, ran = "", True
    for t in TESTS:
        r = subprocess.run([sys.executable, "-I", t], cwd=ROOT, capture_output=True, text=True)
        out += r.stderr
        if "Ran " not in r.stderr:
            ran = False
        if r.returncode:
            return "FAILED" if ran else "ERROR", out
    return "OK", out


killed = 0
for name, path, old, new in MUTANTS:
    p = os.path.join(ROOT, path)
    with open(p) as f:
        text = f.read()
    if text.count(old) != 1:
        print("%-46s NOT APPLIED (%d matches)" % (name, text.count(old)))
        continue
    with open(p, "w") as f:
        f.write(text.replace(old, new))
    try:
        result, _ = run_tests()
    finally:
        with open(p, "w") as f:
            f.write(text)
    verdict = "KILLED" if result == "FAILED" else "SURVIVED" if result == "OK" else "IMPORT ERROR (not a kill)"
    killed += verdict == "KILLED"
    print("%-46s %s" % (name, verdict))
print("restored tree:", run_tests()[0])
print("%d of %d KILLED" % (killed, len(MUTANTS)))
