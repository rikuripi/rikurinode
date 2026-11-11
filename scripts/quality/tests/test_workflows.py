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
docs/build-records/2026-10-29-install-media.md,
docs/build-records/2026-11-06-ci-cargo-mutants.md
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
MUTANTS = os.path.join(ROOT, ".github", "workflows", "mutants.yml")
TOOLCHAIN = os.path.join(ROOT, "rust-toolchain.toml")


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
        # 5c.1: the image holds the control plane, so a change to it builds and drills the image;
        # 5c.3a: and the control plane embeds the UI, so a change to ui/ does too.
        self.assertIn("^(image/|control-plane/|ui/|\\.github/workflows/image\\.yml$)", lines)
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
        self.assertIn("--build-arg TARGET=ghcr.io/rikuripi/rikurinode:install-test-1", lines)
        self.assertIn("--target ghcr.io/rikuripi/rikurinode:install-test-1 ", lines)
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


class ControlPlaneInTheImage(unittest.TestCase):
    """The OS image's build compiles the control plane in its first stage, so its
    context is the repository's root (`podman build -f image/Containerfile .`),
    and /.containerignore lets in only image/rootfs and control-plane/. No build
    names a context (`--build-context`): a `COPY --from=` that names no stage
    would pull an image of that name if a build left the context out. A change
    to the control plane runs the image workflow
    (docs/build-records/2026-11-06-5c1-control-plane-on-node.md; owner,
    2026-11-06: "Repo-root context (Recommended)")."""

    @staticmethod
    def builds(text):
        """Each `podman build` command, continuation lines joined."""
        joined = re.sub(r"\\\n\s*", " ", text)
        return [line.strip() for line in joined.splitlines() if "podman build" in line]

    def test_every_os_image_build_is_the_root_context_with_the_image_containerfile(self):
        for path in (IMAGE, PUBLISH):
            builds = self.builds(read(path))
            os_image = [b for b in builds if "image/installer" not in b]
            self.assertTrue(os_image, path)
            for build in os_image:
                with self.subTest(path=os.path.basename(path), build=build):
                    self.assertTrue(build.endswith(" -f image/Containerfile ."), build)
            for build in builds:
                with self.subTest(path=os.path.basename(path), build=build):
                    self.assertNotIn("--build-context", build)
                    self.assertFalse(re.search(r"\simage$", build), "the old context, image/ alone")

    def test_a_push_that_changes_the_control_plane_runs_the_image_workflow(self):
        on = block(read(IMAGE), "on")
        push = on[on.index("push:") + 1:]
        paths = next(line for line in push if line.startswith("paths:"))
        self.assertIn('"control-plane/**"', paths)

    def test_a_push_that_changes_the_ui_runs_the_image_workflow(self):
        # 5c.3a: the UI is embedded in the control plane's binary.
        on = block(read(IMAGE), "on")
        push = on[on.index("push:") + 1:]
        paths = next(line for line in push if line.startswith("paths:"))
        self.assertIn('"ui/**"', paths)

    def test_the_context_lets_in_only_what_the_image_copies(self):
        with open(os.path.join(ROOT, ".containerignore"), encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip() and not l.startswith("#")]
        # 5c.3a: the UI's sources go in for its build stage; what a local install,
        # a build or the render tests leave in ui/ never does.
        self.assertEqual(lines, ["*", "!image/rootfs", "!control-plane", "control-plane/target",
                                 "!ui", "ui/node_modules", "ui/dist", "ui/test-results", "ui/playwright-report"])

    def test_the_build_stage_is_the_pinned_rust_image(self):
        with open(os.path.join(ROOT, "image", "Containerfile"), encoding="utf-8") as f:
            text = f.read()
        froms = [l.split() for l in text.splitlines() if l.startswith("FROM ")]
        # 5c.3a: the UI's stage comes first; the control plane embeds what it built.
        self.assertEqual(froms[0][1], UI_NODE_IMAGE)
        self.assertEqual(froms[0][2:], ["AS", "ui"])
        self.assertEqual(froms[1][1], "docker.io/library/rust:1.98.1-slim-trixie@sha256:"
                         "4cd829461bd5c4d511c32e269da9cb8929223b666519d8004e35fc8d1d771ab7")
        self.assertEqual(froms[1][2:], ["AS", "control-plane"])
        self.assertEqual(len(froms), 3, "the UI, the control plane, and the OS")
        with open(os.path.join(ROOT, "rust-toolchain.toml"), encoding="utf-8") as f:
            self.assertIn('channel = "1.98.1"', f.read(), "the build stage's Rust is the repository's")
        self.assertIn("--locked", text)
        copies = [l for l in text.splitlines() if l.startswith("COPY ")]
        self.assertEqual(copies, ["COPY ui/ /ui/",
                                  "COPY control-plane/ /src/",
                                  "COPY --from=ui /ui/dist/ /ui/dist/",
                                  "COPY --from=control-plane /src/target/release/rikuri-control-plane "
                                  "/usr/bin/rikuri-control-plane",
                                  "COPY image/rootfs/ /"])
        runs = [l for l in text.splitlines() if l.startswith("RUN ")]
        self.assertEqual(runs[0], "RUN " + UI_BUILD, "the UI's stage installs as locked, scripts off")
        self.assertIn("RIKURI_UI_DIR=/ui", text)


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
        # Publish run 41705388378: image-builder cannot copy an image into the stick under a digest name.
        # The signed digest gets a local name, checked to be that digest, and the stick takes the name.
        # Whole lines, as root (the store image-builder reads), and no step may fail softly.
        rows = [x.strip() for x in lines.splitlines()]
        self.assertIn('sudo podman tag "$PUBLISHED@$DIGEST" "$PUBLISHED:$TAG"', rows)
        self.assertIn('[ "$(sudo podman image inspect --format \'{{.Digest}}\' "$PUBLISHED:$TAG")" = "$DIGEST" ] '
                      '|| { echo "the local name is not $DIGEST" >&2; exit 1; }', rows)
        self.assertNotIn("continue-on-error", lines)
        self.assertIn('--bootc-installer-payload-ref "$PUBLISHED:$TAG"', lines)
        self.assertNotRegex(lines, r"--bootc-installer-payload-ref \S*@")
        self.assertIn("bootc-generic-iso", lines)
        self.assertIn("sha256sum", lines)
        self.assertIn("actions/upload-artifact@", lines)
        order = [lines.index(s) for s in ("podman pull", "podman tag", "podman image inspect", "image/installer",
                                          '"$IMAGE_BUILDER" build', "sha256sum", "upload-artifact")]
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
        self.assertIn('step "11/11', text)
        self.assertIn("python3 scripts/quality/advisory_audit_age.py", text)
        self.assertIn("all 11 steps passed", text)
        self.assertLess(text.index("advisory_audit_age.py"), text.index("all 11 steps passed"))


# 5c.3a: the UI's toolchain, pinned by digest, present only in CI and the image's build
# (docs/build-records/2026-11-11-5c3a-ui-pipeline.md).
UI = os.path.join(ROOT, "scripts", "quality", "ui.sh")
UI_NODE_IMAGE = ("docker.io/library/node:22.23.4-trixie-slim@sha256:"
                 "be1e2a3dc2c4fd68cdfadad2a696a280e0d2749098bee509230174d72fb768c6")
UI_TEST_IMAGE = ("mcr.microsoft.com/playwright:v1.64.1-noble@sha256:"
                 "2f05f8a734509a7b3f26a912639488ee08f58a7b292d14d62271bcff9038768f")
UI_INSTALL = "npm ci --ignore-scripts --engine-strict --no-audit --no-fund"
UI_BUILD = UI_INSTALL + " && npm run build"


class UiGate(unittest.TestCase):
    def setUp(self):
        self.ui = read(UI)
        self.gate = read(GATE)

    def runs(self):
        """Each `docker run` in ui.sh, continuation lines joined."""
        joined = re.sub(r"\\\n\s*", " ", self.ui)
        return [line.strip() for line in joined.splitlines() if "docker run" in line]

    def test_the_gate_builds_and_tests_the_ui_before_the_rust_steps(self):
        self.assertIn("scripts/quality/ui.sh build", self.gate)
        self.assertIn("scripts/quality/ui.sh test", self.gate)
        self.assertLess(self.gate.index("scripts/quality/ui.sh build"), self.gate.index('"${CARGO[@]}" fetch'))
        self.assertIn("command -v docker", self.gate)

    def test_the_toolchains_are_the_pinned_images_and_nothing_else(self):
        self.assertIn('NODE_IMAGE="%s"' % UI_NODE_IMAGE, self.ui)
        self.assertIn('TEST_IMAGE="%s"' % UI_TEST_IMAGE, self.ui)
        images = set(re.findall(r'"\$(NODE_IMAGE|TEST_IMAGE)"', " ".join(self.runs())))
        self.assertEqual(images, {"NODE_IMAGE", "TEST_IMAGE"})
        for run in self.runs():
            with self.subTest(run=run):
                self.assertRegex(run, r'"\$(NODE_IMAGE|TEST_IMAGE)"')
                self.assertIn("--rm", run)
                self.assertIn('--user "$(id -u):$(id -g)"', run)
                self.assertNotIn("--privileged", run)
                self.assertNotIn("docker.sock", run)
                self.assertNotIn("-e GITHUB_TOKEN", run)

    def test_only_the_install_reaches_the_network(self):
        runs = self.runs()
        installs = [r for r in runs if UI_INSTALL in r]
        self.assertEqual(len(installs), 1, runs)
        self.assertNotIn("--network none", installs[0])
        for run in runs:
            if run is installs[0]:
                continue
            with self.subTest(run=run):
                self.assertIn("--network none", run)
        self.assertNotIn("npm install", self.ui)
        self.assertNotIn("playwright install", self.ui)

    def test_type_check_build_and_render_tests(self):
        joined = " ".join(self.runs())
        self.assertIn("npm run check", joined)
        self.assertIn("npm run build", joined)
        self.assertIn("npm run test:render", joined)
        test = [r for r in self.runs() if "test:render" in r]
        self.assertEqual(len(test), 1)
        self.assertIn('"$TEST_IMAGE"', test[0])

    def test_the_render_tests_cannot_be_trimmed(self):
        config = read(os.path.join(ROOT, "ui", "playwright.config.ts"))
        self.assertIn("forbidOnly: true", config)
        self.assertIn("retries: 0", config)
        for spec in ("render.spec.ts", "text-keys.spec.ts"):
            with self.subTest(spec=spec):
                text = read(os.path.join(ROOT, "ui", "tests", spec))
                self.assertNotRegex(text, r"\.(only|skip|fixme)\(")



class Mutants(unittest.TestCase):
    """cargo-mutants over the control plane's changed lines, a missed mutant
    failing the run (docs/build-records/2026-11-06-ci-cargo-mutants.md)."""
    URL = ("https://github.com/sourcefrog/cargo-mutants/releases/download/v27.1.0/"
           "cargo-mutants-x86_64-unknown-linux-gnu.tar.gz")
    SHA = "dfe6dc37d0342c891d2829b5a695aa57c2d0edecef7e7d0399a30cc6e206411e"

    def setUp(self):
        self.text = read(MUTANTS)
        self.lines = [line.strip() for line in self.text.splitlines()]

    def test_control_plane_pull_requests_and_by_hand_from_a_base(self):
        on = block(self.text, "on")
        self.assertIn("pull_request:", on)
        self.assertIn("branches: [main]", on)
        for path in ("control-plane/**", "rust-toolchain.toml", ".github/workflows/mutants.yml"):
            self.assertIn("- " + path, on)
        self.assertIn("workflow_dispatch:", on)
        self.assertIn("base:", on)
        self.assertIn("required: true", on)
        self.assertNotIn("push:", on)
        self.assertNotIn("pull_request_target:", on)

    def test_read_only_token_no_credential_full_history(self):
        self.assertEqual(block(self.text, "permissions"), ["contents: read"])
        self.assertIn("runs-on: ubuntu-24.04", self.lines)
        self.assertIn("persist-credentials: false", self.lines)
        self.assertIn("fetch-depth: 0", [re.sub(r"\s+#.*$", "", line) for line in self.lines])
        self.assertTrue(any(re.match(r"^timeout-minutes: \d+$", line) for line in self.lines))
        self.assertNotIn("secrets.", self.text)
        self.assertNotIn("continue-on-error", self.text)

    def test_the_binary_is_the_pinned_release_checked_by_its_digest(self):
        self.assertIn(self.URL + " \\", self.lines)
        self.assertIn('echo "%s  $RUNNER_TEMP/cargo-mutants.tgz" | sha256sum -c -' % self.SHA, self.lines)
        self.assertLess(self.text.index("sha256sum -c -"), self.text.index("tar -xzf"))
        self.assertEqual(self.text.count("cargo-mutants/releases/download/"), 1)

    def test_the_installed_binary_is_asked_as_cargo_would_ask_it(self):
        # cargo-mutants parses its arguments as `cargo mutants ...` (src/main.rs at
        # v27.1.0), so run directly it needs `mutants` first; bare, it refuses
        # every flag (Rust mutants, run 1 of this PR: job 128288915034).
        self.assertIn("cargo-mutants mutants --version", self.lines)
        self.assertFalse([line for line in self.lines if re.match(r"^cargo-mutants --", line)])

    def test_the_ui_is_built_before_the_crates_are_fetched(self):
        # 5c.3a: the control plane embeds the UI's build, and the copy of
        # control-plane/ that cargo-mutants builds finds it by RIKURI_UI_DIR.
        self.assertIn("RIKURI_UI_DIR: ${{ github.workspace }}/ui", self.lines)
        self.assertIn("scripts/quality/ui.sh build", self.lines)
        self.assertLess(self.text.index("scripts/quality/ui.sh build"),
                        self.text.index("scripts/cargo.sh fetch --locked"))

    def test_the_toolchain_is_rust_toolchain_tomls(self):
        channel = re.search(r'^channel = "([^"]+)"$', read(TOOLCHAIN), re.M).group(1)
        self.assertIn('RUSTUP_TOOLCHAIN: "%s"' % channel, self.lines)

    def test_the_base_reaches_the_shell_only_as_a_checked_commit(self):
        for line in self.lines:
            if "inputs.base" in line or "base.sha" in line:
                self.assertTrue(line.startswith("BASE: ${{"), "only an env line may carry the base: " + line)
        self.assertIn('[[ "$BASE" =~ ^[0-9a-f]{7,40}$ ]] || { echo "base must be a commit id: $BASE"; exit 1; }',
                      self.lines)
        self.assertNotIn("grep -Eqx", self.text)
        self.assertIn('git diff --relative=control-plane "$BASE...HEAD" > "$RUNNER_TEMP/changes.diff"', self.lines)

    def test_mutants_run_offline_locked_inside_the_test_safety_layer(self):
        fetch = "scripts/cargo.sh fetch --locked --manifest-path control-plane/Cargo.toml"
        run = ('scripts/quality/safe-run.sh scripts/cargo.sh mutants --dir control-plane '
               '--in-diff "$RUNNER_TEMP/changes.diff" --output "$RUNNER_TEMP" --cargo-arg=--locked'
               ' --test-workspace=true --timeout 600 --no-shuffle || rc=$?')
        self.assertIn(fetch, self.lines)
        self.assertIn(run, self.lines)
        self.assertLess(self.text.index(fetch), self.text.index(run))
        self.assertIn('CARGO_NET_OFFLINE: "true"', self.lines)
        self.assertIn('SAFE_RUN_ALLOW_NO_NAMESPACE: "1"', self.lines)
        mutants = [line for line in self.lines if " mutants " in line and "cargo.sh" in line]
        self.assertEqual(mutants, [run], "one mutants run, with no exclusion on its command line")

    def test_only_success_and_timeouts_pass(self):
        self.assertIn("rc=0", self.lines)
        self.assertIn('case "$rc" in', self.lines)
        self.assertIn("0|3) ;;", self.lines)
        self.assertIn('*) echo "cargo-mutants exited $rc: missed mutants (2) or an error"; exit "$rc" ;;',
                      self.lines)
        self.assertNotIn("|| true", self.text)

    def steps(self):
        """Each step under `steps:`, as its stripped lines without comments or blanks."""
        out = []
        for line in self.text.splitlines():
            if re.match(r"^      - ", line):
                out.append([])
            if out and line.strip() and not line.strip().startswith("#"):
                out[-1].append(re.sub(r"\s+#.*$", "", line.strip()))
        return out

    def test_the_mutation_step_is_exactly_this(self):
        # Line checks alone let `2) ;;`, an `exit 0` or `if: false` through (verifier, round 1).
        mutate = [st for st in self.steps() if st[0] == "- name: Mutate the changed lines (inside safe-run.sh, offline)"]
        self.assertEqual(mutate, [[
            "- name: Mutate the changed lines (inside safe-run.sh, offline)",
            "env:",
            'SAFE_RUN_ALLOW_NO_NAMESPACE: "1"',
            'CARGO_NET_OFFLINE: "true"',
            "run: |",
            "rc=0",
            'scripts/quality/safe-run.sh scripts/cargo.sh mutants --dir control-plane --in-diff '
            '"$RUNNER_TEMP/changes.diff" --output "$RUNNER_TEMP" --cargo-arg=--locked '
            '--test-workspace=true --timeout 600 --no-shuffle || rc=$?',
            'case "$rc" in',
            "0|3) ;;",
            '*) echo "cargo-mutants exited $rc: missed mutants (2) or an error"; exit "$rc" ;;',
            "esac"]])

    def test_only_the_two_reports_have_a_condition(self):
        conditions = [line for line in self.lines if line.startswith("if:")]
        self.assertEqual(conditions, ["if: always()", "if: always()"])
        reporting = [st[0] for st in self.steps() if "if: always()" in st]
        self.assertEqual(reporting, ["- name: What was missed, or timed out", "- name: Keep mutants.out"])

    def test_the_trigger_paths_are_exactly_these(self):
        on = block(self.text, "on")
        self.assertEqual([line for line in on if line.startswith("- ")],
                         ["- control-plane/**", "- rust-toolchain.toml", "- .github/workflows/mutants.yml"])

    def test_what_was_missed_is_shown_and_kept(self):
        self.assertIn("if: always()", self.lines)
        self.assertIn('cat "$RUNNER_TEMP/mutants.out/missed.txt" >> "$GITHUB_STEP_SUMMARY"', self.lines)
        self.assertIn('cat "$RUNNER_TEMP/mutants.out/timeout.txt" >> "$GITHUB_STEP_SUMMARY"', self.lines)
        self.assertIn("uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2",
                      self.lines)
        self.assertIn("path: ${{ runner.temp }}/mutants.out", self.lines)


class MutantsExclusions(unittest.TestCase):
    """control-plane/.cargo/mutants.toml skips exactly the four mutants no
    `cargo test` can kill, each anchored to one mutant's name and naming the
    VM drill check that kills it instead (docs/build-records/2026-11-10-mutants-survivors.md)."""

    CONFIG = os.path.join(ROOT, "control-plane", ".cargo", "mutants.toml")
    # Each survivor of run 42905996478, as cargo-mutants 27.1.0 names it for its
    # filters: Options::allows_mutant matches Mutant::name(true), the
    # tree-relative path with line and column, ": ", then the mutation.
    SURVIVORS = {
        "crates/rikuri-control/src/console.rs:80:5: replace lan_address -> Option<IpAddr> with None":
            "the claim screen shows the node's address",
        "apps/rikuri-control-plane/src/main.rs:31:5: replace main -> ExitCode with Default::default()":
            "the control plane runs as its own user",
        "apps/rikuri-control-plane/src/main.rs:83:5: replace run -> Result<(), Box<dyn Error>> with Ok(())":
            "the control plane runs as its own user",
        "apps/rikuri-control-plane/src/main.rs:181:5: replace claim_screen -> ExitCode with Default::default()":
            "the claim screen shows the node's address",
    }
    # The same mutants after the code above them moves: still excluded.
    MOVED = ("crates/rikuri-control/src/console.rs:97:5: replace lan_address -> Option<IpAddr> with None",
             "apps/rikuri-control-plane/src/main.rs:40:9: replace main -> ExitCode with Default::default()",
             "apps/rikuri-control-plane/src/main.rs:120:5: replace run -> Result<(), Box<dyn Error>> with Ok(())",
             "apps/rikuri-control-plane/src/main.rs:1:1: replace claim_screen -> ExitCode with Default::default()")
    # Other mutants, of these functions and of their neighbours, that must still be tested.
    NEAR = ("crates/rikuri-control/src/console.rs:70:5: replace shown_address -> Option<IpAddr> with None",
            "crates/rikuri-control/src/console.rs:80:5: replace lan_address -> Option<IpAddr> with Some(Default::default())",
            "apps/rikuri-control-plane/src/main.rs:31:5: replace main -> ExitCode with ExitCode::FAILURE",
            "apps/rikuri-control-plane/src/main.rs:83:5: replace run -> Result<(), Box<dyn Error>> with Ok(Default::default())",
            "apps/rikuri-control-plane/src/main.rs:83:5: replace run -> Result<(), Box<dyn Error>> with Err(Default::default())",
            "apps/rikuri-control-plane/src/main.rs:181:5: replace claim_screen -> ExitCode with ExitCode::FAILURE",
            "apps/rikuri-control-plane/src/main.rs:52:5: replace daemon -> ExitCode with Default::default()",
            "apps/rikuri-control-plane/src/main.rs:136:5: replace rearm_claim -> ExitCode with Default::default()",
            "apps/rikuri-control-plane/src/main.rs:34:9: delete match arm (Some(\"claim-screen\"), None) in main",
            "apps/rikuri-control-plane/src/main.rs: replace main -> ExitCode with Default::default()",
            "apps/rikuri-control-plane/src/main.rs:31: replace main -> ExitCode with Default::default()",
            "apps/rikuri-control-plane/src/mainXrs:31:5: replace main -> ExitCode with Default::default()",
            "apps/rikuri-control-plane/src/mainXrs:83:5: replace run -> Result<(), Box<dyn Error>> with Ok(())",
            "apps/rikuri-control-plane/src/mainXrs:181:5: replace claim_screen -> ExitCode with Default::default()",
            # A changed signature is a new mutant, to be tested or excluded anew.
            "apps/rikuri-control-plane/src/main.rs:83:5: replace run -> Result<(), std::io::Error> with Ok(())",
            "apps/rikuri-control-plane/src/main.rs:181:5: replace claim_screen -> u8 with Default::default()",
            "crates/rikuri-control/src/console.rs:80:5: replace lan_address -> Option<Ipv4Addr> with None",
            "crates/rikuri-control/src/consoleXrs:80:5: replace lan_address -> Option<IpAddr> with None",
            "x/apps/rikuri-control-plane/src/main.rs:31:5: replace main -> ExitCode with Default::default()",
            "apps/rikuri-control-plane/src/main.rs:31:5: replace main -> ExitCode with Default::default() ")

    @classmethod
    def without_line_or_column(cls):
        """Each survivor's name with no line and column, and with a line only:
        names cargo-mutants never filters on, so a regex that takes them has
        loosened its `:line:column:`."""
        out = []
        for name in cls.SURVIVORS:
            m = re.fullmatch(r"(.*?\.rs):(\d+):\d+(: .*)", name)
            out += [m.group(1) + m.group(3), m.group(1) + ":" + m.group(2) + m.group(3)]
        return out

    def lines(self):
        with open(self.CONFIG, encoding="utf-8") as f:
            return f.read().splitlines()

    def regexes(self):
        """The file's every line that is not a comment or blank: `exclude_re = [`,
        one TOML literal string per line, `]`. Read by hand, so no other key,
        table or string form can get in, on every Python the tools support."""
        body = [line.strip() for line in self.lines() if line.strip() and not line.strip().startswith("#")]
        self.assertEqual((body[0], body[-1]), ("exclude_re = [", "]"))
        out = []
        for line in body[1:-1]:
            m = re.fullmatch(r"'([^']*)',", line)
            self.assertIsNotNone(m, "not one literal string: %r" % line)
            out.append(m.group(1))
        return out

    def test_the_loosened_names_are_eight(self):
        self.assertEqual(len(set(self.without_line_or_column())), 2 * len(self.SURVIVORS))

    def test_only_name_regexes_and_nothing_wider(self):
        regexes = self.regexes()
        try:
            import tomllib
        except ImportError:   # Python < 3.11: the hand reading above is the check
            return
        with open(self.CONFIG, "rb") as f:
            self.assertEqual(tomllib.load(f), {"exclude_re": regexes})

    def test_each_regex_matches_its_one_survivor_and_nothing_else(self):
        regexes = self.regexes()
        self.assertEqual(len(regexes), len(self.SURVIVORS))
        for rx in regexes:
            with self.subTest(rx=rx):
                self.assertTrue(rx.startswith("^") and rx.endswith("$"), "anchored at both ends")
                self.assertEqual(len([n for n in self.SURVIVORS if re.search(rx, n)]), 1)
                self.assertEqual(len([n for n in self.MOVED if re.search(rx, n)]), 1)
                for name in self.NEAR + tuple(self.without_line_or_column()):
                    self.assertIsNone(re.search(rx, name), name)
        for name in tuple(self.SURVIVORS) + self.MOVED:
            with self.subTest(name=name):
                self.assertTrue(any(re.search(rx, name) for rx in regexes), "not excluded")

    def test_each_exclusion_says_why_and_names_the_drill_check_that_kills_it(self):
        sys.path.insert(0, os.path.join(ROOT, "image", "drill"))
        import vm_drill
        lines = self.lines()
        for rx in self.regexes():
            with self.subTest(rx=rx):
                at = next(i for i, line in enumerate(lines) if line.strip() == "'%s'," % rx)
                above = []
                for line in reversed(lines[:at]):
                    if not line.strip().startswith("#"):
                        break
                    above.insert(0, line.strip().lstrip("#").strip())
                why = " ".join(above)
                self.assertIn("Why:", why)
                check = self.SURVIVORS[next(n for n in self.SURVIVORS if re.search(rx, n))]
                self.assertIn(check, vm_drill.EXPECTED)
                self.assertIn('Killed by the drill\'s "%s"' % check, why)


if __name__ == "__main__":
    unittest.main()
