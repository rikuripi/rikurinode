#!/usr/bin/env python3
"""The node's signature policy, proven on the built OS image: stage 1 change 2a.

    signature_policy.py --image <local image> --cosign <cosign> --registry <registry> --workdir <dir>

Runs on CI's Linux runner, with sudo and podman (.github/workflows/image.yml,
job build), after the image is built and checked. A registry (distribution's
release binary) serves on 127.0.0.1; throwaway keys sign tiny test images in
it with cosign, in the older format the node can read. Then the image's own
skopeo, under the image's own /etc/containers/policy.json and registries.d
file, reads each case as ghcr.io/rikuripi/rikurinode, and each must be
accepted or refused for its own reason (CASES); a refusal for any other
reason is a miss. Into the image's container go only: the two throwaway
public keys over the owner's (the policy's key paths, unchanged), a
registries.conf.d file that reads the policy's scope from the local registry
(a prefix rewrite, never a mirror, which could fall back to ghcr.io), and the
shipped registries.d file with the local registry's name: containers/image
looks that setting up by the address it reads from, not by the policy's
name (probes 3 and 4). That the shipped file works under ghcr.io itself is
2b's, against the published image.
Record: docs/build-records/2026-10-25-signature-policy.md
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from typing import NamedTuple

REG = "127.0.0.1:5000"
IMAGE_REPO = "ghcr.io/rikuripi/rikurinode"
LOCAL_REPO = REG + "/rikuripi/rikurinode"
KEYS = {"main": "/usr/share/rikuri/signing/rikuri-main.pub",
        "spare": "/usr/share/rikuri/signing/rikuri-spare.pub"}
REGISTRIES_D_FILE = "/etc/containers/registries.d/rikuri.yaml"
CI_REGISTRIES_D = "/etc/containers/registries.d/ci-local-registry.yaml"
CI_REGISTRIES_CONF = "/etc/containers/registries.conf.d/99-ci-local-registry.conf"
REJECTED = "Source image rejected: "
# containers/image's reasons (evidence 04-probe.out).
NO_SIGNATURE = "A signature was required, but no signature exists"
BAD_SIGNATURE = "cryptographic signature verification failed"
WRONG_IDENTITY = "Signature for identity"
WRONG_DIGEST = "Signature for digest"


class Case(NamedTuple):
    name: str
    tag: str | None        # the test image built for it, pushed to `push` (None: no image of its own)
    key: str | None        # the throwaway key that signs it
    identity: str | None   # the identity the signature claims
    expect: str | None     # None: accepted; else the refusal's reason
    ref: str               # what the image's skopeo reads; "@<tag>" is that image's digest
    signature_from: str | None = None   # the case whose signature replaces its own
    push: str | None = None             # default LOCAL_REPO:<tag>


CASES = (
    Case("signed by the main key", "main", "main", IMAGE_REPO + ":main", None, IMAGE_REPO + ":main"),
    Case("signed by the spare key", "spare", "spare", IMAGE_REPO + ":spare", None, IMAGE_REPO + ":spare"),
    Case("signed by the main key, read by digest", None, None, None, None, IMAGE_REPO + "@main"),
    Case("unsigned", "unsigned", None, None, NO_SIGNATURE, IMAGE_REPO + ":unsigned"),
    Case("signed by a key the node does not trust", "untrusted", "untrusted", IMAGE_REPO + ":untrusted",
         BAD_SIGNATURE, IMAGE_REPO + ":untrusted"),
    Case("signed by the main key as another repository", "identity", "main", "ghcr.io/someone/else:identity",
         WRONG_IDENTITY, IMAGE_REPO + ":identity"),
    Case("carrying another image's valid signature", "tampered", "main", IMAGE_REPO + ":tampered",
         WRONG_DIGEST, IMAGE_REPO + ":tampered", signature_from="main"),
    Case("another repository, unsigned (outside the policy's scope)", "other", None, None, None,
         REG + "/other/thing:1", push=REG + "/other/thing:1"),
)


def miss(returncode: int, output: str, expect):
    """None when the outcome is the case's; else what happened instead."""
    last = (output.strip().splitlines() or [""])[-1]
    if expect is None:
        return None if returncode == 0 else "refused: " + last
    if returncode == 0:
        return "accepted; expected a refusal (%s)" % expect
    if REJECTED in output and expect in output.split(REJECTED, 1)[1]:
        return None
    return "refused for another reason: " + last


def registry_env(environ) -> dict:
    """The environment without REGISTRY_*: the registry reads each as a config
    override (CI run 40776852353, evidence 08)."""
    return {k: v for k, v in environ.items() if not k.startswith("REGISTRY_")}


def registry_failure(returncode, log: str) -> str:
    """Why the proof stops when the registry did not answer: its exit and its log."""
    state = "exit %d" % returncode if returncode is not None else "still running, not answering"
    return "signature_policy: the registry did not start (%s); its log:\n%s" % (state, log.strip() or "(empty)")


def ci_registries_d(shipped: str, repo: str = LOCAL_REPO) -> str:
    """The shipped registries.d file, with the local registry's name (or `repo`) for the image's."""
    if shipped.count(IMAGE_REPO + ":") != 1:
        raise ValueError("the shipped registries.d file does not name %s once" % IMAGE_REPO)
    return shipped.replace(IMAGE_REPO + ":", repo + ":")


def registry_config(workdir: str) -> str:
    return ("version: 0.1\nstorage:\n  filesystem:\n    rootdirectory: %s/reg\nhttp:\n  addr: %s\n"
            "log:\n  level: error\n" % (workdir, REG))


def start_registry(binary: str, workdir: str) -> subprocess.Popen:
    """distribution's registry on REG, storing under workdir/reg: the process once it
    answers; else it is stopped and RuntimeError says why. Also the drill's (2c)."""
    os.makedirs(os.path.join(workdir, "reg"))
    with open(os.path.join(workdir, "reg.yml"), "w") as f:
        f.write(registry_config(workdir))
    log = os.path.join(workdir, "registry.log")
    registry = subprocess.Popen([binary, "serve", os.path.join(workdir, "reg.yml")], env=registry_env(os.environ),
                                stdout=open(log, "w"), stderr=subprocess.STDOUT)
    for _ in range(100):
        try:
            urllib.request.urlopen("http://%s/v2/" % REG, timeout=2).close()
            return registry
        except OSError:
            time.sleep(0.2)
    state = registry.poll()
    registry.terminate()
    registry.wait(timeout=30)
    with open(log) as f:
        raise RuntimeError(registry_failure(state, f.read()))


def registries_conf() -> str:
    return ('[[registry]]\nprefix = "%s"\nlocation = "%s"\ninsecure = true\n\n'
            '[[registry]]\nlocation = "%s"\ninsecure = true\n' % (IMAGE_REPO, LOCAL_REPO, REG))


def mounts(workdir: str) -> list:
    return [(os.path.join(workdir, k + ".pub"), path) for k, path in KEYS.items()] + [
        (os.path.join(workdir, "registries.conf"), CI_REGISTRIES_CONF),
        (os.path.join(workdir, "ci-local-registry.yaml"), CI_REGISTRIES_D)]


def podman_run(image: str, mounted: list, *argv: str) -> list:
    cmd = ["sudo", "podman", "run", "--rm", "--network=host"]
    for src, dst in mounted:
        cmd += ["-v", "%s:%s:ro,z" % (src, dst)]  # z: SELinux relabels it (the VM run); ignored without SELinux
    return cmd + [image] + list(argv)


def copy_argv(image: str, mounted: list, ref: str, out: str) -> list:
    return podman_run(image, mounted, "skopeo", "copy", "-q", "docker://" + ref, "dir:" + out)


def sign_argv(cosign: str, key: str, identity: str, digest_ref: str, http: bool = True) -> list:
    """cosign's older format, by digest, no transparency log; http only for the proof's local registry."""
    return [cosign, "sign", "-y", "--key=" + key, "--new-bundle-format=false", "--tlog-upload=false",
            "--use-signing-config=false"] + (["--allow-http-registry"] if http else []) + [
            "--sign-container-identity=" + identity, digest_ref]


def run(argv: list, **kw) -> subprocess.CompletedProcess:
    print("+ " + " ".join(argv), flush=True)
    return subprocess.run(argv, capture_output=True, text=True, **kw)


def must(argv: list, **kw) -> str:
    r = run(argv, **kw)
    if r.returncode:
        sys.exit("signature_policy: failed (%d): %s\n%s" % (r.returncode, " ".join(argv), r.stdout + r.stderr))
    return r.stdout


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--image", required=True)
    ap.add_argument("--cosign", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--workdir", required=True)
    args = ap.parse_args(argv)
    w = os.path.abspath(args.workdir)
    try:
        registry = start_registry(args.registry, w)
    except RuntimeError as e:
        sys.exit(str(e))
    pushed = []
    try:
        env = dict(os.environ, COSIGN_PASSWORD="")
        for k in sorted({c.key for c in CASES if c.key} | set(KEYS)):
            must([args.cosign, "generate-key-pair", "--output-key-prefix", os.path.join(w, k)], env=env)
        shipped = must(podman_run(args.image, [], "cat", REGISTRIES_D_FILE))
        with open(os.path.join(w, "ci-local-registry.yaml"), "w") as f:
            f.write(ci_registries_d(shipped))
        with open(os.path.join(w, "registries.conf"), "w") as f:
            f.write(registries_conf())

        digest = {}
        for c in CASES:
            if not c.tag:
                continue
            d = os.path.join(w, "img-" + c.tag)
            os.makedirs(d)
            with open(os.path.join(d, "f"), "w") as f:
                f.write(c.tag + "\n")  # its own content, so its own digest
            with open(os.path.join(d, "Containerfile"), "w") as f:
                f.write("FROM scratch\nCOPY f /f\n")
            push = c.push or LOCAL_REPO + ":" + c.tag
            must(["sudo", "podman", "build", "-q", "--network=none", "-t", push, d])
            pushed.append(push)
            must(["sudo", "podman", "push", "-q", "--tls-verify=false", "--digestfile", d + ".digest", push])
            with open(d + ".digest") as f:
                digest[c.tag] = f.read().strip()
        for c in CASES:
            if c.key:
                must(sign_argv(args.cosign, os.path.join(w, c.key + ".key"), c.identity,
                               LOCAL_REPO + "@" + digest[c.tag]), env=env)
        for c in CASES:
            if c.signature_from:
                src, dst = (digest[t].replace(":", "-") + ".sig" for t in (c.signature_from, c.tag))
                must(podman_run(args.image, [], "skopeo", "copy", "-q", "--preserve-digests",
                                "--src-tls-verify=false", "--dest-tls-verify=false",
                                "docker://%s:%s" % (LOCAL_REPO, src), "docker://%s:%s" % (LOCAL_REPO, dst)))

        rows, misses = [], 0
        for n, c in enumerate(CASES, 1):
            ref = c.ref
            if "@" in ref:
                repo, tag = ref.split("@")
                ref = repo + "@" + digest[tag]
            r = run(copy_argv(args.image, mounts(w), ref, "/tmp/out"))
            out = r.stdout + r.stderr
            m = miss(r.returncode, out, c.expect)
            misses += m is not None
            seen = "accepted" if r.returncode == 0 else "refused: " + (out.split(REJECTED, 1)[1].strip()
                                                                       if REJECTED in out else out.strip()[-200:])
            rows.append("| %d | %s | %s | %s | %s |" % (n, c.name, "accepted" if c.expect is None else
                                                          "refused: " + c.expect, seen.replace("|", "/"),
                                                          "PASS" if m is None else "MISS: " + m.replace("|", "/")))
        report = ["### Signature policy (the image's own skopeo and policy; throwaway keys)", "",
                  "| # | case | expected | seen | result |", "|---|---|---|---|---|"] + rows + [
                  "", "%d of %d cases as expected" % (len(CASES) - misses, len(CASES))]
        print("\n".join(report))
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a") as f:
                f.write("\n".join(report) + "\n")
        return 1 if misses else 0
    finally:
        registry.terminate()
        registry.wait(timeout=30)
        for p in pushed:
            run(["sudo", "podman", "rmi", "-f", p])


if __name__ == "__main__":
    sys.exit(main())
