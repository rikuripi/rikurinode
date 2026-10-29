"""Hand mutants of publish.py and publish.yml: each weakens one rule; its tests must fail on each.
Run from the repository's root: python3 -I <this> (writes each mutant over its file, runs that file's
tests, restores the file)."""
import subprocess
import sys

PY, YML = "image/drill/publish.py", ".github/workflows/publish.yml"
PY_TESTS = ["image/tests/test_publish.py"]
YML_TESTS = ["scripts/quality/tests/test_workflows.py"]   # run directly: -m unittest with a path fails to import it
MUTANTS = [
    ("m1 a run number of any form", PY, 're.fullmatch(r"[1-9][0-9]*", run)', 're.fullmatch(r".*", run)'),
    ("m2 a re-run goes ahead", PY, '    if attempt == "1":\n        return None', '    if True:\n        return None'),
    ("m3 any digest", PY, '    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):', '    if False:'),
    ("m4 any image counts as the one built", PY, '        return None\n    return "publish: the image pulled',
     '        return None\n    return None\n    return "publish: the image pulled'),
    ("m5 the login mounted where config is read", PY, 'AUTH_IN = "/run/rikuri-publish/auth.json"',
     'AUTH_IN = "/root/.config/containers/auth.json"'),
    ("m6 cosign may fall back to http", PY, 'digest_ref(digest), http=False)', 'digest_ref(digest), http=True)'),
    ("m7 cosign gets the job's whole environment", PY, 'return {k: environ[k] for k in SIGN_ENV if k in environ}',
     'return dict(environ)'),
    ("m8 an empty password signs", PY, 'SIGN_ENV_REQUIRED = ("DOCKER_CONFIG", "COSIGN_PASSWORD", "COSIGN_PRIVATE_KEY")',
     'SIGN_ENV_REQUIRED = ("DOCKER_CONFIG", "COSIGN_PRIVATE_KEY")'),
    ("m9 started by a push too", YML, "on:\n  workflow_dispatch:\n", "on:\n  workflow_dispatch:\n  push:\n    branches: [main]\n"),
    ("m10 the anonymous job on any branch", YML,
     "    needs: [build, sign]\n    if: github.ref == 'refs/heads/main'\n", "    needs: [build, sign]\n"),
    ("m11 the build job in the Environment", YML, "    timeout-minutes: 150\n",
     "    timeout-minutes: 150\n    environment: image-publish\n"),
    ("m12 the key for the whole sign job", YML, "      IMAGE_ID: ${{ needs.build.outputs.image_id }}\n",
     "      IMAGE_ID: ${{ needs.build.outputs.image_id }}\n      COSIGN_PASSWORD: ${{ secrets.COSIGN_PASSWORD }}\n"),
    ("m13 a re-run not refused", YML, ' --attempt "$GITHUB_RUN_ATTEMPT"', ' --attempt 1'),
    ("m14 no drill before the push", YML,
     '          python3 -I image/drill/vm_drill.py --image "$IMAGE" --workdir /mnt/drill --artifacts "$RUNNER_TEMP/drill-evidence"\n',
     '          true\n'),
    ("m15 the anonymous read logs in", YML, '          python3 -I image/drill/publish.py accepted --digest "$DIGEST" --tag "$TAG"\n',
     '          python3 -I image/drill/publish.py accepted --digest "$DIGEST" --tag "$TAG" --authfile a.json\n'),
    ("m16 the build job may write anything", YML, "    timeout-minutes: 150\n    permissions:\n      contents: read\n",
     "    timeout-minutes: 150\n    permissions:\n      contents: write\n"),
    ("m17 refused checked after signing", YML,
     "      - name: The image's own policy refuses it unsigned\n        run: python3 -I image/drill/publish.py refused --digest \"$DIGEST\" --authfile \"$RUNNER_TEMP/auth.json\"\n",
     ""),
    # Repair 1: the verifier's mutants of main() (pass 1, I1 to I8), and the built ID at the push (M3).
    ("m18 I1 another image counts as built", PY, "        if m:\n            sys.exit(m)", "        if False:\n            sys.exit(m)"),
    ("m19 I2 a failed inspect counts", PY, 'if r.returncode == 0 else "publish: inspect failed: " + r.stderr',
     'if True else None'),
    ("m20 I3 a miss exits 0", PY, "    return 0 if m is None else 1", "    return 0"),
    ("m21 I4 refused expects acceptance", PY, "args.authfile, sp.NO_SIGNATURE)", "args.authfile, None)"),
    ("m22 I5 the tag not read", PY, "            | read_as_node(args.digest, IMAGE_REPO", "            | 0 * read_as_node(args.digest, IMAGE_REPO"),
    ("m23 I6 cosign's failure ignored", PY, "        if r.returncode:\n            sys.exit(\"publish: cosign failed",
     "        if False:\n            sys.exit(\"publish: cosign failed"),
    ("m24 I7 cosign gets the job's environment", PY, "env=sign_env(os.environ),", "env=dict(os.environ),"),
    ("m25 I8 a failed pull ignored", PY, "    r = run(pull_argv(args.digest, getattr(args, \"authfile\", None)))\n    if r.returncode:",
     "    r = run(pull_argv(args.digest, getattr(args, \"authfile\", None)))\n    if False:"),
    ("m26 M3 the built ID not compared", YML, '          [ "$id" = "$(cat "$RUNNER_TEMP/built-id")" ] || {', '          true || {'),
]

src = {f: open(f).read() for f in (PY, YML)}
bad = 0
try:
    for name, path, old, new in MUTANTS:
        assert src[path].count(old) == 1, name
        open(path, "w").write(src[path].replace(old, new))
        r = subprocess.run([sys.executable, "-I"] + (PY_TESTS if path == PY else YML_TESTS), capture_output=True, text=True)
        open(path, "w").write(src[path])
        last = [l for l in r.stderr.splitlines() if l.startswith(("FAILED", "OK"))]
        # A kill counts only when the tests ran: a suite that cannot import is not a test failing.
        broken = any(s in r.stderr for s in ("ModuleNotFoundError", "ImportError", "_FailedTest", "SyntaxError"))
        killed = r.returncode != 0 and bool(last) and not broken
        bad += not killed
        print("%-48s %s  %s" % (name, "KILLED" if killed else "SURVIVED", last[-1] if last else "?"))
finally:
    for f, s in src.items():
        open(f, "w").write(s)
for tests in (PY_TESTS, YML_TESTS):
    r = subprocess.run([sys.executable, "-I"] + tests, capture_output=True, text=True)
    print("restored:", [l for l in r.stderr.splitlines() if l.startswith(("FAILED", "OK"))][-1])
sys.exit(1 if bad else 0)
