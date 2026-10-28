"""Tests for image/drill/publish.py, the steps of .github/workflows/publish.yml.

Only its pure parts run here: the fixed tag and the refusal of a re-run, the
digest's form, the image pulled being the one built, the command lines for
podman, the image's skopeo and cosign, and the signing step's environment
(the key and its password, and nothing else of the job's). The publish itself
runs only on main, started by the owner; its evidence is that run.
Record: docs/build-records/2026-10-28-publish-signed-image.md
"""
from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "drill"))
import publish as pb  # noqa: E402
import signature_policy as sp  # noqa: E402

DIGEST = "sha256:" + "ab" * 32
REF = sp.IMAGE_REPO + "@" + DIGEST


class Tag(unittest.TestCase):
    def test_fedora_release_date_and_run(self):
        self.assertEqual(pb.tag("44", "20261028", "3"), "44.20261028.3")

    def test_anything_else_is_refused(self):
        for args in (("44a", "20261028", "3"), ("44", "2026-10-28", "3"), ("44", "20261028", "0"),
                     ("44", "20261028", ""), ("44", "20261028", "3; true"), ("", "20261028", "3"),
                     ("44", "202610281", "3")):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    pb.tag(*args)

    def test_a_rerun_is_refused_because_it_would_move_the_tag(self):
        self.assertIsNone(pb.rerun_refusal("1"))
        for attempt in ("2", "10", "", "x"):
            with self.subTest(attempt=attempt):
                self.assertIn("new publish", pb.rerun_refusal(attempt))


class Digest(unittest.TestCase):
    def test_a_digest_names_the_image(self):
        self.assertEqual(pb.digest_ref(DIGEST), REF)

    def test_anything_but_a_sha256_digest_is_refused(self):
        for d in ("sha256:" + "ab" * 31, "sha512:" + "ab" * 64, "sha256:" + "AB" * 32, "44.20261028.3",
                  DIGEST + "\n", ""):
            with self.subTest(d=d):
                with self.assertRaises(ValueError):
                    pb.digest_ref(d)

    def test_the_image_pulled_is_the_one_built(self):
        self.assertIsNone(pb.same_image("sha256:" + "cd" * 32, "cd" * 32))
        self.assertIsNone(pb.same_image("cd" * 32, "sha256:" + "cd" * 32 + "\n"))
        self.assertIn("not the image built", pb.same_image("cd" * 32, "ce" * 32))
        self.assertIn("not the image built", pb.same_image("", ""))


class Argv(unittest.TestCase):
    def test_pull_by_digest(self):
        self.assertEqual(pb.pull_argv(DIGEST, None), ["sudo", "podman", "pull", "-q", REF])
        self.assertEqual(pb.pull_argv(DIGEST, "/r/auth.json"),
                         ["sudo", "podman", "pull", "-q", "--authfile", "/r/auth.json", REF])

    def test_the_published_image_reads_with_its_own_skopeo_and_policy(self):
        for ref in (REF, sp.IMAGE_REPO + ":44.20261028.3"):
            for auth in (None, "/r/auth.json"):
                with self.subTest(ref=ref, auth=auth):
                    argv = pb.read_argv(DIGEST, ref, auth)
                    self.assertEqual(argv[:4], ["sudo", "podman", "run", "--rm"])
                    i = argv.index(REF)   # the container is always the image by digest
                    self.assertEqual(argv[i + 1:i + 4], ["skopeo", "copy", "-q"])
                    self.assertEqual(argv[-2:], ["docker://" + ref, "dir:/tmp/out"])
                    for flag in ("--policy", "--insecure-policy", "--registries.d", "--registries-conf"):
                        self.assertFalse(any(a.startswith(flag) for a in argv), flag)
                    mounted = [argv[n + 1] for n, a in enumerate(argv[:i]) if a == "-v"]
                    if auth is None:
                        self.assertEqual(mounted, [])
                        self.assertNotIn("--src-authfile", argv)
                    else:
                        # The login only, read-only, outside every place containers/image takes config from.
                        self.assertEqual(mounted, [auth + ":" + pb.AUTH_IN + ":ro,z"])
                        self.assertEqual(argv[argv.index("--src-authfile") + 1], pb.AUTH_IN)
                        self.assertFalse(pb.AUTH_IN.startswith(("/etc/", "/root/", "/usr/")), pb.AUTH_IN)

    def test_cosign_signs_the_digest_with_the_key_from_the_environment(self):
        argv = pb.sign_argv("/t/cosign", "44.20261028.3", DIGEST)
        self.assertEqual(argv[:3], ["/t/cosign", "sign", "-y"])
        for flag in ("--key=env://COSIGN_PRIVATE_KEY", "--new-bundle-format=false", "--tlog-upload=false",
                     "--use-signing-config=false", "--sign-container-identity=" + sp.IMAGE_REPO + ":44.20261028.3"):
            self.assertIn(flag, argv)
        self.assertNotIn("--allow-http-registry", argv)   # ghcr.io only over HTTPS
        self.assertEqual(argv[-1], REF)

    def test_the_proofs_signing_still_allows_its_local_registry(self):
        self.assertIn("--allow-http-registry", sp.sign_argv("/t/c", "/w/k.key", "i", "r"))


class SignEnv(unittest.TestCase):
    JOB = {"PATH": "/usr/bin", "HOME": "/home/runner", "DOCKER_CONFIG": "/r/cosign-auth",
           "COSIGN_PRIVATE_KEY": "-----BEGIN ENCRYPTED SIGSTORE PRIVATE KEY-----", "COSIGN_PASSWORD": "pw",
           "GITHUB_TOKEN": "t", "ACTIONS_RUNTIME_TOKEN": "t", "ACTIONS_ID_TOKEN_REQUEST_URL": "u", "TAG": "x"}

    def test_cosign_gets_the_key_its_password_and_its_login_only(self):
        self.assertEqual(sorted(pb.sign_env(self.JOB)),
                         ["COSIGN_PASSWORD", "COSIGN_PRIVATE_KEY", "DOCKER_CONFIG", "HOME", "PATH"])

    def test_a_missing_or_empty_key_or_password_stops_it(self):
        for name in ("COSIGN_PRIVATE_KEY", "COSIGN_PASSWORD", "DOCKER_CONFIG"):
            for value in (None, ""):
                with self.subTest(name=name, value=value):
                    env = dict(self.JOB)
                    if value is None:
                        del env[name]
                    else:
                        env[name] = value
                    with self.assertRaises(ValueError) as e:
                        pb.sign_env(env)
                    self.assertNotIn(self.JOB["COSIGN_PRIVATE_KEY"], str(e.exception))
                    self.assertNotIn("pw", str(e.exception).replace("PASSWORD", ""))


class Anonymous(unittest.TestCase):
    def test_a_refused_anonymous_pull_names_the_owners_step(self):
        msg = pb.anonymous_failure(125, "Error: initializing source docker://ghcr.io/rikuripi/rikurinode@...: "
                                        "reading manifest: unauthorized\n")
        self.assertIn("public", msg)
        self.assertIn("docs/runbooks/publish-os-image.md", msg)
        self.assertIn("unauthorized", msg)


if __name__ == "__main__":
    unittest.main()
