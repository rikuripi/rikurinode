"""Tests that hold the CI workflows together with the audit and the gate.

Every action is pinned to a commit with its version named (the audit refuses
otherwise, SEC-06); the cargo-deny install lines are the same in ci.yml and
advisory-audit.yml, so the two cannot drift apart; the audit runs on a
schedule and on demand with a read-only token and runs both readers; ci.yml's
token has exactly the two read permissions the gate needs; the gate runs the
stale-audit warning as its last step (TEST-05); the publish workflow is
started by hand on main only, and only its signing step sees the key; the
install media is built and installed in the image workflow, and built from
the signed digest, with no login, in the publish workflow. Reads the
repository's own files; no network.
Records: docs/build-records/2026-10-21-weekly-advisory-audit.md,
docs/build-records/2026-10-28-publish-signed-image.md,
docs/build-records/2026-10-29-install-media.md
Run: python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'
"""
import glob
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import osv_audit as oa  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
WORKFLOWS = sorted(glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml")))
CI = os.path.join(ROOT, ".github", "workflows", "ci.yml")
AUDIT = os.path.join(ROOT, ".github", "workflows", "advisory-audit.yml")
GATE = os.path.join(ROOT, "scripts", "quality", "full-gate.sh")
IMAGE = os.path.join(ROOT, ".github", "workflows", "image.yml")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def block(text, key):
    """The lines indented under a top-level `key:`, stripped, without comments or blanks."""
    lines, inside = [], False
    for line in text.splitlines():
        if re.match(r"^[A-Za-z_]+:", line):
            inside = line.startswith(key + ":")
            continue
        if inside and line.strip() and not line.strip().startswith("#"):
            lines.append(re.sub(r"\s+#.*$", "", line.strip()))
    return lines


def cargo_deny_lines(text):
    """The install lines that name the cargo-deny archive and its checksum (not the other tools')."""
    return [line.strip() for line in text.splitlines()
            if "cargo-deny" in line and (line.strip().startswith("https://") or re.match(r'^\s*echo "[0-9a-f]{64}\s', line))]


class Pins(unittest.TestCase):
    def test_every_action_is_pinned_with_its_version_named(self):
        found = oa.pinned_actions(WORKFLOWS)
        self.assertGreaterEqual(len(found), 3, found)
        for name, version, where in found:
            self.assertRegex(name, r"^[\w.-]+/[\w.-]+$", where)
            self.assertRegex(version, r"^\d+(\.\d+)*$", where)
        self.assertIn("actions/checkout", [name for name, _, _ in found])


class Audit(unittest.TestCase):
    def test_cargo_deny_install_lines_are_identical_to_ci(self):
        in_ci, in_audit = cargo_deny_lines(read(CI)), cargo_deny_lines(read(AUDIT))
        self.assertTrue(in_ci, "ci.yml installs cargo-deny by a checksummed archive")
        self.assertTrue(any(re.match(r'^echo "[0-9a-f]{64}\s', line) for line in in_ci), in_ci)
        self.assertEqual(in_ci, in_audit)

    def test_scheduled_on_demand_and_on_its_own_inputs(self):
        on = block(read(AUDIT), "on")
        self.assertIn("schedule:", on)
        self.assertTrue(any(re.match(r"^- cron: '\d+ \d+ \* \* \d'$", line) for line in on), on)
        self.assertIn("workflow_dispatch:", on)
        self.assertIn("pull_request:", on)
        for path in (".github/workflows/advisory-audit.yml", "control-plane/Cargo.lock", "control-plane/deny.toml",
                     "scripts/quality/osv_audit.py"):
            self.assertIn("- " + path, on)

    def test_read_only_token_and_pinned_runner(self):
        text = read(AUDIT)
        self.assertEqual(block(text, "permissions"), ["contents: read"])
        self.assertIn("runs-on: ubuntu-24.04", text)
        self.assertIn("persist-credentials: false", text)

    def test_runs_both_readers(self):
        text = read(AUDIT)
        self.assertIn("deny --manifest-path control-plane/Cargo.toml --locked check advisories", text)
        self.assertIn("python3 scripts/quality/osv_audit.py", text)


class Ci(unittest.TestCase):
    def test_token_permissions_are_exactly_the_two_reads(self):
        self.assertEqual(sorted(block(read(CI), "permissions")), ["actions: read", "contents: read"])

    def test_the_gate_step_gets_the_token(self):
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", read(CI))


def job(text, name):
    """The lines of one job under `jobs:` (two-space indent), its header included."""
    lines, out, inside = text.splitlines(), [], False
    for line in lines:
        if re.match(r"^  [A-Za-z0-9_-]+:\s*$", line):
            inside = line.strip() == name + ":"
        elif line and not line.startswith(" "):
            inside = False
        if inside:
            out.append(line)
    return out


class Image(unittest.TestCase):
    """The image workflow starts on every pull request, so its jobs can be
    required checks, and its build and drill run only when the image or the
    workflow changed (docs/build-records/2026-10-22-image-workflow-every-pr.md)."""

    def test_every_pull_request_starts_the_workflow(self):
        on = block(read(IMAGE), "on")   # stripped lines; a trigger's name ends with ":"
        trigger = []
        for line in on[on.index("pull_request:") + 1:]:
            if line.endswith(":"):
                break
            trigger.append(line)
        self.assertFalse(any(line.startswith("paths") for line in trigger), trigger)

    def test_build_drill_and_install_wait_for_the_changes_job(self):
        text = read(IMAGE)
        self.assertTrue(job(text, "changes"), "a changes job")
        for name in ("build", "drill", "install"):
            lines = " ".join(job(text, name))
            self.assertRegex(lines, r"needs: \[?[^\]]*\bchanges\b", name)
            self.assertIn("if: needs.changes.outputs.image == 'true'", lines, name)

    def test_only_a_pull_request_can_skip(self):
        lines = "\n".join(job(read(IMAGE), "changes"))
        self.assertIn('if [ "$EVENT" != "pull_request" ]', lines)
        self.assertIn("image=true", lines)
        self.assertIn("image=false", lines)
        self.assertIn("^(image/|\\.github/workflows/image\\.yml$)", lines)
        # A pipe into grep -q can fail under GitHub's `bash -e -o pipefail` and
        # skip the drill wrongly; the match reads a here-string instead.
        self.assertNotRegex(lines, r"\|\s*grep -q")

    def test_the_drill_gets_the_pinned_registry(self):
        # 2c: cases 4 and 5 need a registry on the runner (docs/build-records/2026-10-29-node-refuses-unsigned.md).
        lines = "\n".join(job(read(IMAGE), "drill"))
        self.assertIn("registry_${DISTRIBUTION_VERSION}_linux_amd64.tar.gz", lines)
        self.assertIn("sha256sum --strict -c -", lines)
        self.assertIn('--registry "$RUNNER_TEMP/sig-tools/registry"', lines)
        self.assertLess(lines.index("sha256sum --strict"), lines.index("vm_drill.py"))

    def test_both_drills_install_the_forwards_nc(self):
        # Repair 1 (CI run 40932208792): QEMU starts nc for each connection to the drill's registry.
        for path, name in ((IMAGE, "drill"), (PUBLISH, "build")):
            lines = "\n".join(job(read(path), name))
            self.assertRegex(lines, r"apt-get install -y -q --no-install-recommends qemu-system-x86 ovmf netcat-openbsd\n",
                             path)
            self.assertRegex(lines, r"dpkg-query -W .* qemu-system-x86 ovmf netcat-openbsd\b", path)   # its version recorded


    def test_the_install_job_builds_the_serial_stick_and_installs_it(self):
        # 5a: the stick CI types into; the published one uses the screen (publish.yml, job iso).
        lines = "\n".join(job(read(IMAGE), "install"))
        self.assertIn("--build-arg CONSOLE=ttyS0", lines)
        self.assertIn("--build-arg TARGET=ghcr.io/rikuripi/rikurinode:install-test", lines)
        self.assertIn('"$IMAGE_BUILDER" build', lines)
        self.assertIn("bootc-generic-iso", lines)
        self.assertIn("--bootc-installer-payload-ref", lines)
        self.assertIn("image/drill/install_test.py", lines)
        self.assertRegex(lines, r"apt-get install -y -q --no-install-recommends qemu-system-x86 ovmf ostree\n")
        order = [lines.index(s) for s in ("podman build", "image/installer", '"$IMAGE_BUILDER" build',
                                          "install_test.py")]
        self.assertEqual(order, sorted(order))


PUBLISH = os.path.join(ROOT, ".github", "workflows", "publish.yml")


def steps(lines):
    """One job's steps (`      - ` at six spaces), each as its lines joined."""
    out = []
    for line in lines:
        if line.startswith("      - "):
            out.append(line)
        elif out and line.startswith("        "):
            out[-1] += "\n" + line
    return out


def env_pins(text):
    return [line.strip() for line in text.splitlines() if re.match(r"^  (COSIGN|DISTRIBUTION)_(VERSION|SHA256):", line)]


def builder_pin(text):
    return [line.strip() for line in text.splitlines() if line.startswith("  IMAGE_BUILDER:")]


class Publish(unittest.TestCase):
    """Only the owner starts a publish, only on main; only the sign job, in the
    Environment, sees the key, and only in its signing step; a re-run is refused
    because it would move a fixed tag
    (docs/build-records/2026-10-28-publish-signed-image.md)."""

    JOBS = ("build", "sign", "anonymous", "iso")

    def setUp(self):
        self.text = read(PUBLISH)

    def test_started_only_by_hand(self):
        self.assertEqual(block(self.text, "on"), ["workflow_dispatch:"])

    def test_every_job_runs_only_on_main(self):
        jobs = [m.group(1) for m in re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\s*$", self.text.split("\njobs:", 1)[1])]
        self.assertEqual(jobs, list(self.JOBS))
        for name in self.JOBS:
            self.assertIn("    if: github.ref == 'refs/heads/main'", job(self.text, name), name)

    def test_permissions_per_job(self):
        self.assertRegex(self.text, r"(?m)^permissions: \{\}$")
        want = {"build": ["contents: read", "packages: write"], "sign": ["contents: read", "packages: write"],
                "anonymous": ["contents: read"], "iso": ["contents: read"]}
        for name, perms in want.items():
            lines = job(self.text, name)
            i = lines.index("    permissions:")
            got = []
            for line in lines[i + 1:]:
                if not line.startswith("      ") or line.startswith("      - "):
                    break
                got.append(line.strip())
            self.assertEqual(sorted(got), perms, name)

    def test_only_the_sign_job_is_in_the_environment(self):
        for name in self.JOBS:
            envs = [line.strip() for line in job(self.text, name) if line.strip().startswith("environment")]
            self.assertEqual(envs, ["environment: image-publish"] if name == "sign" else [], name)

    def test_secrets_only_in_the_signing_step(self):
        with_secrets = [s for s in steps(job(self.text, "sign")) if "secrets." in s]
        self.assertEqual(len(with_secrets), 1, with_secrets)
        names = sorted(re.findall(r"\$\{\{\s*secrets\.([A-Z_]+)\s*\}\}", with_secrets[0]))
        self.assertEqual(names, ["COSIGN_PASSWORD", "COSIGN_PRIVATE_KEY"])
        self.assertIn("publish.py sign ", with_secrets[0])
        for name in ("build", "anonymous", "iso"):
            self.assertNotIn("secrets.", "\n".join(job(self.text, name)), name)
        outside = self.text.replace(with_secrets[0], "")
        self.assertNotIn("secrets.", outside)

    def test_the_build_job_refuses_a_rerun_and_proves_before_it_pushes(self):
        lines = "\n".join(job(self.text, "build"))
        self.assertIn('--attempt "$GITHUB_RUN_ATTEMPT"', lines)
        order = [lines.index(s) for s in ("publish.py tag", "check_image_root.py", "signature_policy.py",
                                          "vm_drill.py", "podman push")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("anonymous", " ".join(re.findall(r"needs:.*", lines)))
        # The ID is recorded right after the build and compared at the push (verifier pass 1, M3).
        record = lines.index('> "$RUNNER_TEMP/built-id"')
        compare = lines.index('[ "$id" = "$(cat "$RUNNER_TEMP/built-id")" ] || {')
        self.assertLess(lines.index("podman build"), record)
        self.assertLess(record, lines.index("check_image_root.py"))
        self.assertLess(lines.index("podman push"), compare)
        # 2c: the drill's cases 4 and 5 use the registry the proof fetched.
        drill = [s for s in steps(job(self.text, "build")) if "vm_drill.py" in s]
        self.assertEqual(len(drill), 1)
        self.assertIn('--registry "$RUNNER_TEMP/sig-tools/registry"', drill[0])

    def test_the_sign_job_refuses_signs_then_accepts(self):
        lines = "\n".join(job(self.text, "sign"))
        self.assertIn("needs: build", lines)
        order = [lines.index(s) for s in ("publish.py same", "publish.py refused", "publish.py sign ",
                                          "publish.py accepted")]
        self.assertEqual(order, sorted(order))

    def test_the_anonymous_job_has_no_login(self):
        lines = "\n".join(job(self.text, "anonymous"))
        self.assertIn("needs: [build, sign]", lines)
        self.assertIn("publish.py accepted", lines)
        self.assertNotIn("login", lines)
        self.assertNotIn("authfile", lines)
        self.assertNotIn("token", lines.lower())

    def test_the_iso_job_builds_the_stick_from_the_signed_digest_with_no_login(self):
        # 5a: after the anonymous job proved the signed digest readable with no credential.
        lines = "\n".join(job(self.text, "iso"))
        self.assertIn("needs: [build, sign, anonymous]", lines)
        for word in ("login", "authfile"):
            self.assertNotIn(word, lines)
        self.assertNotIn("token", lines.lower())
        self.assertIn('podman pull "$PUBLISHED@$DIGEST"', lines)
        self.assertIn("--build-arg CONSOLE=tty1", lines)
        self.assertIn('--build-arg TARGET="$PUBLISHED:$TAG"', lines)
        self.assertIn('--bootc-installer-payload-ref "$PUBLISHED@$DIGEST"', lines)
        self.assertIn("bootc-generic-iso", lines)
        self.assertIn("sha256sum", lines)
        self.assertIn("actions/upload-artifact@", lines)
        order = [lines.index(s) for s in ("podman pull", "image/installer", '"$IMAGE_BUILDER" build', "sha256sum",
                                          "upload-artifact")]
        self.assertEqual(order, sorted(order))

    def test_the_image_builder_pin_is_the_image_workflows(self):
        pin = builder_pin(self.text)
        self.assertEqual(len(pin), 1)
        self.assertRegex(pin[0], r"^IMAGE_BUILDER: ghcr\.io/osbuild/image-builder-cli:v87\.0\.0@sha256:[0-9a-f]{64}$")
        self.assertEqual(pin, builder_pin(read(IMAGE)))

    def test_every_checkout_keeps_no_credential(self):
        uses = self.text.count("uses: actions/checkout@")
        self.assertEqual(uses, len(self.JOBS))
        self.assertEqual(self.text.count("persist-credentials: false"), uses)

    def test_the_tool_pins_are_the_image_workflows(self):
        self.assertEqual(len(env_pins(self.text)), 4)
        self.assertEqual(env_pins(self.text), env_pins(read(IMAGE)))


class Gate(unittest.TestCase):
    def test_runs_the_stale_audit_warning_last(self):
        text = read(GATE)
        self.assertIn('step "10/10', text)
        self.assertIn("python3 scripts/quality/advisory_audit_age.py", text)
        self.assertIn("all 10 steps passed", text)
        self.assertLess(text.index("advisory_audit_age.py"), text.index("all 10 steps passed"))


if __name__ == "__main__":
    unittest.main()
