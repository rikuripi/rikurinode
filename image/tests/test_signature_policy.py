"""Tests for image/drill/signature_policy.py, CI's proof of the node's signature policy.

Only its pure parts run here: the pass rule (a refusal counts only with the
expected reason), the cases, the files it adds to the image's container (the
shipped policy and registries.d file are never replaced), and the command
lines for cosign and the image's skopeo. The proof itself runs only in CI
(.github/workflows/image.yml, job build); its evidence is the job's runs.
Record: docs/build-records/2026-10-25-signature-policy.md
"""
from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "drill"))
sys.path.insert(0, os.path.join(HERE, os.pardir))
import check_image_root as cir  # noqa: E402
import signature_policy as sp  # noqa: E402

SHIPPED_REGISTRIES_D = os.path.join(HERE, os.pardir, "rootfs", cir.REGISTRIES_D_FILE)
REJECTED = 'time="..." level=fatal msg="Source image rejected: '


class PassRule(unittest.TestCase):
    def test_an_expected_acceptance(self):
        self.assertIsNone(sp.miss(0, "", None))

    def test_an_expected_refusal_with_its_reason(self):
        self.assertIsNone(sp.miss(1, REJECTED + sp.NO_SIGNATURE + '"', sp.NO_SIGNATURE))

    def test_a_refusal_where_acceptance_was_expected(self):
        self.assertIn("refused", sp.miss(1, REJECTED + sp.NO_SIGNATURE + '"', None))

    def test_an_acceptance_where_refusal_was_expected(self):
        self.assertIn("accepted", sp.miss(0, "", sp.NO_SIGNATURE))

    def test_a_refusal_for_another_reason_does_not_count(self):
        # The registry down, a missing image, a wrong key file: not the policy's refusal.
        for out in ('level=fatal msg="initializing source docker://ghcr.io/rikuripi/rikurinode:x: '
                    'pinging container registry 127.0.0.1:5000: connection refused"',
                    REJECTED + 'A signature was required, but no signature exists"'.replace("required", "wanted"),
                    REJECTED + sp.BAD_SIGNATURE + '"'):
            with self.subTest(out=out):
                self.assertIn("another reason", sp.miss(1, out, sp.NO_SIGNATURE))

    def test_the_reason_must_come_from_the_policy(self):
        # The reason's text alone, without containers/image's "Source image rejected", is not enough.
        self.assertIn("another reason", sp.miss(1, sp.NO_SIGNATURE, sp.NO_SIGNATURE))
        # Nor the reason before it: only what containers/image says it rejected for counts
        # (verifier pass 1, nit 2).
        self.assertIn("another reason", sp.miss(1, sp.NO_SIGNATURE + "\n" + REJECTED + sp.BAD_SIGNATURE, sp.NO_SIGNATURE))


class Cases(unittest.TestCase):
    def test_both_keys_are_accepted_and_each_refusal_is_covered(self):
        by_name = {c.name: c for c in sp.CASES}
        self.assertEqual(len(by_name), len(sp.CASES))
        accepted = [c for c in sp.CASES if c.expect is None]
        self.assertEqual(sorted(c.key for c in accepted if c.ref.startswith(sp.IMAGE_REPO + ":")),
                         ["main", "spare"])
        self.assertEqual({c.expect for c in sp.CASES if c.expect},
                         {sp.NO_SIGNATURE, sp.BAD_SIGNATURE, sp.WRONG_IDENTITY, sp.WRONG_DIGEST})

    def test_every_refused_case_is_read_through_the_policys_scope(self):
        for c in sp.CASES:
            if c.expect:
                with self.subTest(case=c.name):
                    self.assertTrue(c.ref.startswith(sp.IMAGE_REPO + ":"), c.ref)

    def test_another_repository_and_a_digest_are_covered(self):
        refs = [c.ref for c in sp.CASES if c.expect is None]
        self.assertTrue(any(not r.startswith(sp.IMAGE_REPO) for r in refs))
        self.assertTrue(any(r.startswith(sp.IMAGE_REPO + "@") for r in refs))

    def test_the_tampered_case_carries_another_images_signature(self):
        tampered = [c for c in sp.CASES if c.expect == sp.WRONG_DIGEST]
        self.assertEqual(len(tampered), 1)
        self.assertTrue(tampered[0].signature_from and tampered[0].signature_from != tampered[0].tag)

    def test_the_identity_case_claims_another_repository(self):
        (c,) = [c for c in sp.CASES if c.expect == sp.WRONG_IDENTITY]
        self.assertEqual(c.key, "main")
        self.assertFalse(c.identity.startswith(sp.IMAGE_REPO + ":"))


class ContainerFiles(unittest.TestCase):
    def test_the_ci_registries_d_file_is_the_shipped_one_renamed(self):
        with open(SHIPPED_REGISTRIES_D, encoding="ascii") as f:
            shipped = f.read()
        ci = sp.ci_registries_d(shipped)
        self.assertEqual(ci, shipped.replace(sp.IMAGE_REPO + ":", sp.LOCAL_REPO + ":"))
        self.assertNotEqual(ci, shipped)

    def test_the_registries_d_file_can_name_another_address(self):
        # 2c: the drill VM reads the image's name from the CI machine through 10.0.2.100.
        with open(SHIPPED_REGISTRIES_D, encoding="ascii") as f:
            shipped = f.read()
        repo = "10.0.2.100:5000/rikuripi/rikurinode"
        self.assertEqual(sp.ci_registries_d(shipped, repo), shipped.replace(sp.IMAGE_REPO + ":", repo + ":"))

    def test_a_shipped_file_without_the_name_is_refused(self):
        with self.assertRaises(ValueError):
            sp.ci_registries_d("docker:\n  ghcr.io/else:\n    use-sigstore-attachments: true\n")

    def test_the_registries_conf_reads_only_the_scope_from_the_local_registry(self):
        conf = sp.registries_conf()
        self.assertIn('prefix = "%s"' % sp.IMAGE_REPO, conf)
        self.assertIn('location = "%s"' % sp.LOCAL_REPO, conf)
        self.assertNotIn("mirror", conf)  # a mirror would fall back to ghcr.io itself

    def test_the_shipped_policy_and_registries_d_file_are_never_replaced(self):
        mounts = sp.mounts("/w")
        targets = [dst for _, dst in mounts]
        self.assertEqual(sorted(targets), sorted(
            ["/" + k for k in cir.SIGNING_KEYS]
            + ["/etc/containers/registries.conf.d/99-ci-local-registry.conf",
               "/etc/containers/registries.d/ci-local-registry.yaml"]))
        self.assertNotIn("/" + cir.POLICY, targets)
        self.assertNotIn("/" + cir.REGISTRIES_D_FILE, targets)
        for src, _ in mounts:
            self.assertTrue(src.startswith("/w/"), src)


class Argv(unittest.TestCase):
    def test_the_image_reads_with_its_own_skopeo_and_policy(self):
        argv = sp.copy_argv("localhost/rikuri-os:ci", sp.mounts("/w"), sp.IMAGE_REPO + ":main", "/tmp/out")
        self.assertEqual(argv[:4], ["sudo", "podman", "run", "--rm"])
        self.assertIn("--network=host", argv)
        i = argv.index("localhost/rikuri-os:ci")
        self.assertEqual(argv[i + 1:], ["skopeo", "copy", "-q", "docker://" + sp.IMAGE_REPO + ":main", "dir:/tmp/out"])
        self.assertNotIn("--policy", argv)
        self.assertNotIn("--insecure-policy", argv)
        for n, a in enumerate(argv[:i]):
            if a == "-v":
                self.assertIn("ro", argv[n + 1].rsplit(":", 1)[1].split(","), argv[n + 1])

    def test_cosign_signs_in_the_older_format_by_digest_without_a_log(self):
        argv = sp.sign_argv("/t/cosign", "/w/main.key", sp.IMAGE_REPO + ":main", sp.LOCAL_REPO + "@sha256:" + "a" * 64)
        self.assertEqual(argv[:3], ["/t/cosign", "sign", "-y"])
        for flag in ("--key=/w/main.key", "--new-bundle-format=false", "--tlog-upload=false",
                     "--use-signing-config=false", "--allow-http-registry",
                     "--sign-container-identity=" + sp.IMAGE_REPO + ":main"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[-1], sp.LOCAL_REPO + "@sha256:" + "a" * 64)


class Registry(unittest.TestCase):
    """CI run 40776852353: the workflow's REGISTRY_VERSION reached the registry,
    which reads every REGISTRY_* variable as a config override, and it did not
    start; nothing said why (evidence 08)."""

    def test_the_registry_starts_without_any_registry_variable(self):
        env = sp.registry_env({"PATH": "/usr/bin", "REGISTRY_VERSION": "3.1.2",
                               "REGISTRY_SHA256": "ab", "REGISTRY_HTTP_ADDR": ":80", "HOME": "/h"})
        self.assertEqual(env, {"PATH": "/usr/bin", "HOME": "/h"})

    def test_the_registry_serves_on_loopback_from_the_workdir(self):
        self.assertEqual(sp.registry_config("/w"), "version: 0.1\nstorage:\n  filesystem:\n    rootdirectory: /w/reg\n"
                                                   "http:\n  addr: 127.0.0.1:5000\nlog:\n  level: error\n")

    def test_a_failed_start_says_why(self):
        msg = sp.registry_failure(1, "configuration error: parsing environment variable REGISTRY_VERSION\n")
        self.assertIn("exit 1", msg)
        self.assertIn("parsing environment variable REGISTRY_VERSION", msg)
        self.assertIn("still running", sp.registry_failure(None, ""))

    def test_the_workflow_names_no_registry_variable(self):
        with open(os.path.join(HERE, os.pardir, os.pardir, ".github", "workflows", "image.yml")) as f:
            self.assertNotRegex(f.read(), r"(?m)^\s+REGISTRY_[A-Z0-9_]*:")


if __name__ == "__main__":
    unittest.main()
