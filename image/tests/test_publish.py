"""Tests for image/drill/publish.py, the steps of .github/workflows/publish.yml.

Only its pure parts run here: the fixed tag and the refusal of a re-run, the
digest's form, the image pulled being the one built, the command lines for
podman, the image's skopeo and cosign, and the signing step's environment
(the key and its password, and nothing else of the job's). main() runs with
podman and cosign faked (class Main; verifier pass 1, I1 to I8): each
subcommand's exit, and what reaches cosign. The publish itself runs only on
main, started by the owner; its evidence is that run.
Record: docs/build-records/2026-10-28-publish-signed-image.md
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest import mock

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


REJECTED_NO_SIG = 'level=fatal msg="Source image rejected: ' + sp.NO_SIGNATURE + '"'
TAG = "44.20261028.3"


class Fake:
    """subprocess.run, faked: each call's argv is recorded and answered by the first rule that matches."""

    def __init__(self, *rules):
        self.rules, self.calls = rules, []

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        for match, rc, out in self.rules:
            if match(argv):
                return subprocess.CompletedProcess(argv, rc, out, "" if rc == 0 else out)
        return subprocess.CompletedProcess(argv, 0, "", "")

    def reads(self):
        return [a[-2] for a, _ in self.calls if "skopeo" in a]


def is_pull(a):
    return a[:3] == ["sudo", "podman", "pull"]


def is_inspect(a):
    return a[:4] == ["sudo", "podman", "image", "inspect"]


def reads(ref):
    return lambda a: "skopeo" in a and a[-2] == "docker://" + ref


def is_cosign(a):
    return a[1:2] == ["sign"]


class Main(unittest.TestCase):
    def main(self, fake, *argv, environ=None):
        env = {"PATH": "/usr/bin"} if environ is None else environ
        with mock.patch.object(pb.subprocess, "run", fake), mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("sys.stdout"):
            try:
                return pb.main(list(argv))
            except SystemExit as e:
                return e.code if e.code is not None else 0

    def test_same_passes_only_for_the_image_built(self):
        args = ("same", "--digest", DIGEST, "--image-id", "cd" * 32, "--authfile", "/r/a.json")
        self.assertEqual(self.main(Fake((is_inspect, 0, "sha256:" + "cd" * 32 + "\n")), *args), 0)
        other = self.main(Fake((is_inspect, 0, "ce" * 32 + "\n")), *args)          # I1
        self.assertIn("not the image built", other)
        failed = self.main(Fake((is_inspect, 125, "no such image")), *args)        # I2
        self.assertIn("inspect failed", failed)
        pull = self.main(Fake((is_pull, 125, "unauthorized"), (is_inspect, 0, "cd" * 32)), *args)   # I8
        self.assertIn("pull failed", pull)

    def test_refused_fails_the_step_when_the_policy_accepts_it(self):
        args = ("refused", "--digest", DIGEST, "--authfile", "/r/a.json")
        fake = Fake((reads(REF), 1, REJECTED_NO_SIG))
        self.assertEqual(self.main(fake, *args), 0)
        self.assertEqual(fake.reads(), ["docker://" + REF])
        self.assertEqual(self.main(Fake((reads(REF), 0, "")), *args), 1)           # I3, I4
        other = 'level=fatal msg="Source image rejected: ' + sp.BAD_SIGNATURE + '"'
        self.assertEqual(self.main(Fake((reads(REF), 1, other)), *args), 1)       # refused, but not as unsigned

    def test_accepted_reads_by_digest_and_by_tag_and_each_counts(self):
        args = ("accepted", "--digest", DIGEST, "--tag", TAG, "--authfile", "/r/a.json")
        by_tag = sp.IMAGE_REPO + ":" + TAG
        fake = Fake()
        self.assertEqual(self.main(fake, *args), 0)
        self.assertEqual(fake.reads(), ["docker://" + REF, "docker://" + by_tag])   # I5
        self.assertEqual(self.main(Fake((reads(by_tag), 1, REJECTED_NO_SIG)), *args), 1)   # I3, I5
        self.assertEqual(self.main(Fake((reads(REF), 1, REJECTED_NO_SIG)), *args), 1)

    def test_an_anonymous_pull_that_fails_names_the_owners_step(self):
        msg = self.main(Fake((is_pull, 125, "unauthorized")), "accepted", "--digest", DIGEST, "--tag", TAG)
        self.assertIn("not public", msg)
        fake = Fake((is_pull, 125, "unauthorized"))
        self.main(fake, "accepted", "--digest", DIGEST, "--tag", TAG)
        self.assertEqual(fake.reads(), [])

    def test_sign_gives_cosign_only_its_environment_and_fails_with_it(self):
        job = dict(SignEnv.JOB)
        args = ("sign", "--cosign", "/t/cosign", "--tag", TAG, "--digest", DIGEST)
        fake = Fake()
        self.assertEqual(self.main(fake, *args, environ=job), 0)
        (argv, kw), = fake.calls
        self.assertEqual(argv, pb.sign_argv("/t/cosign", TAG, DIGEST))
        self.assertEqual(kw["env"], pb.sign_env(job))                               # I7
        self.assertNotIn("GITHUB_TOKEN", kw["env"])
        failed = self.main(Fake((is_cosign, 1, "error: signing")), *args, environ=job)   # I6
        self.assertIn("cosign failed", failed)
        self.assertNotIn(job["COSIGN_PRIVATE_KEY"], failed)
        missing = dict(job, COSIGN_PASSWORD="")
        fake = Fake()
        with self.assertRaises(ValueError):
            with mock.patch.object(pb.subprocess, "run", fake), mock.patch.dict(os.environ, missing, clear=True):
                pb.main(list(args))
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
