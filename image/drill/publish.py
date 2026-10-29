#!/usr/bin/env python3
"""The steps of publishing the node's OS image: stage 1 change 2b.

    publish.py tag      --fedora 44 --date 20261028 --run 3 --attempt 1
    publish.py same     --digest <d> --image-id <id> --authfile <f>
    publish.py refused  --digest <d> --authfile <f>
    publish.py sign     --cosign <cosign> --tag <t> --digest <d>
    publish.py accepted --digest <d> --tag <t> [--authfile <f>]

Run by .github/workflows/publish.yml, on main, when the owner starts it. The
build job builds, checks and drills one image and pushes it under a fixed tag
that never moves (so a re-run is refused: it would build another image under
the same tag). The sign job pulls it by digest and checks it is the image
built (its ID, the config digest: probe 5); the image's own skopeo, under
its own policy and registries.d file and nothing mounted over them, refuses
it unsigned; cosign signs the digest, in the older format the node reads,
with the key from the Environment in that one step's environment only; then
the same skopeo accepts it by digest and by tag. The anonymous job reads it
as a node does, with no login. A login, while the package is private, is a
read-only copy of the job's own; it changes no check of the policy.
Record: docs/build-records/2026-10-28-publish-signed-image.md
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I leaves this folder out
import signature_policy as sp  # noqa: E402

IMAGE_REPO = sp.IMAGE_REPO
AUTH_IN = "/run/rikuri-publish/auth.json"   # the login inside the container: no place config is read from
RUNBOOK = "docs/runbooks/publish-os-image.md"
SIGN_ENV = ("PATH", "HOME", "DOCKER_CONFIG", "COSIGN_PASSWORD", "COSIGN_PRIVATE_KEY")
SIGN_ENV_REQUIRED = ("DOCKER_CONFIG", "COSIGN_PASSWORD", "COSIGN_PRIVATE_KEY")


def tag(fedora: str, date: str, run: str) -> str:
    """The fixed tag: <Fedora release>.<UTC date>.<run number>."""
    if not (re.fullmatch(r"[1-9][0-9]*", fedora) and re.fullmatch(r"[0-9]{8}", date)
            and re.fullmatch(r"[1-9][0-9]*", run)):
        raise ValueError("not a release, a date and a run number: %r %r %r" % (fedora, date, run))
    return "%s.%s.%s" % (fedora, date, run)


def fixed_tag(t: str) -> str:
    """A tag made by tag(), or ValueError."""
    parts = t.split(".")
    if len(parts) != 3:
        raise ValueError("not a fixed tag: %r" % t)
    return tag(*parts)


def rerun_refusal(attempt: str):
    """None on a run's first attempt; else why it stops."""
    if attempt == "1":
        return None
    return ("publish: this is attempt %r of the run; a re-run of the build would put another image under "
            "the same fixed tag. Start a new publish instead (%s)." % (attempt, RUNBOOK))


def digest_ref(digest: str) -> str:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("not a sha256 digest: %r" % digest)
    return IMAGE_REPO + "@" + digest


def same_image(pulled: str, built: str):
    """None when the image pulled has the built image's ID; else what differs."""
    def bare(i):
        i = i.strip()
        return i[len("sha256:"):] if i.startswith("sha256:") else i
    if re.fullmatch(r"[0-9a-f]{64}", bare(pulled)) and bare(pulled) == bare(built):
        return None
    return "publish: the image pulled (%r) is not the image built (%r)" % (pulled.strip(), built.strip())


def pull_argv(digest: str, authfile) -> list:
    return ["sudo", "podman", "pull", "-q"] + (["--authfile", authfile] if authfile else []) + [digest_ref(digest)]


def read_argv(digest: str, ref: str, authfile) -> list:
    """The published image's own skopeo reads `ref` under its own policy; only a login is mounted."""
    mounted = [(authfile, AUTH_IN)] if authfile else []
    auth = ["--src-authfile", AUTH_IN] if authfile else []
    return sp.podman_run(digest_ref(digest), mounted, "skopeo", "copy", "-q", *auth, "docker://" + ref, "dir:/tmp/out")


def sign_argv(cosign: str, release_tag: str, digest: str) -> list:
    return sp.sign_argv(cosign, "env://COSIGN_PRIVATE_KEY", IMAGE_REPO + ":" + fixed_tag(release_tag),
                        digest_ref(digest), http=False)


def sign_env(environ) -> dict:
    """cosign's environment: the key, its password, its login, PATH and HOME; nothing else of the job's."""
    for name in SIGN_ENV_REQUIRED:
        if not environ.get(name):
            raise ValueError("publish: %s is missing or empty in the signing step" % name)
    return {k: environ[k] for k in SIGN_ENV if k in environ}


def anonymous_failure(returncode: int, output: str) -> str:
    return ("publish: a node could not pull the image without credentials (exit %d): the package is not public "
            "yet. Making it public is the owner's step (%s), then re-run this job.\n%s"
            % (returncode, RUNBOOK, output.strip()[-400:]))


def run(argv: list, **kw) -> subprocess.CompletedProcess:
    print("+ " + " ".join(argv), flush=True)
    return subprocess.run(argv, capture_output=True, text=True, **kw)


def summary(line: str) -> None:
    print(line)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(line + "\n")


def read_as_node(digest: str, ref: str, authfile, expect) -> int:
    r = run(read_argv(digest, ref, authfile))
    out = r.stdout + r.stderr
    m = sp.miss(r.returncode, out, expect)
    summary("- %s: %s" % (ref, "PASS, " + ("accepted" if expect is None else "refused: " + expect)
                          if m is None else "MISS: " + m))
    return 0 if m is None else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("tag")
    for a in ("--fedora", "--date", "--run", "--attempt"):
        p.add_argument(a, required=True)
    p = sub.add_parser("same")
    for a in ("--digest", "--image-id", "--authfile"):
        p.add_argument(a, required=True)
    p = sub.add_parser("refused")
    for a in ("--digest", "--authfile"):
        p.add_argument(a, required=True)
    p = sub.add_parser("sign")
    for a in ("--cosign", "--tag", "--digest"):
        p.add_argument(a, required=True)
    p = sub.add_parser("accepted")
    for a in ("--digest", "--tag"):
        p.add_argument(a, required=True)
    p.add_argument("--authfile")
    args = ap.parse_args(argv)

    if args.cmd == "tag":
        refusal = rerun_refusal(args.attempt)
        if refusal:
            sys.exit(refusal)
        print(tag(args.fedora, args.date, args.run))
        return 0
    if args.cmd == "sign":
        r = subprocess.run(sign_argv(args.cosign, fixed_tag(args.tag), args.digest), env=sign_env(os.environ),
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit("publish: cosign failed (exit %d):\n%s" % (r.returncode, (r.stdout + r.stderr).strip()))
        summary("- signed %s as %s:%s" % (digest_ref(args.digest), IMAGE_REPO, args.tag))
        return 0

    r = run(pull_argv(args.digest, getattr(args, "authfile", None)))
    if r.returncode:
        if args.cmd == "accepted" and not args.authfile:
            sys.exit(anonymous_failure(r.returncode, r.stdout + r.stderr))
        sys.exit("publish: the pull failed (exit %d):\n%s" % (r.returncode, (r.stdout + r.stderr).strip()))
    if args.cmd == "same":
        r = run(["sudo", "podman", "image", "inspect", "--format", "{{.Id}}", digest_ref(args.digest)])
        m = same_image(r.stdout, args.image_id) if r.returncode == 0 else "publish: inspect failed: " + r.stderr
        if m:
            sys.exit(m)
        summary("- %s is the image built (ID %s)" % (digest_ref(args.digest), args.image_id.strip()))
        return 0
    if args.cmd == "refused":
        return read_as_node(args.digest, digest_ref(args.digest), args.authfile, sp.NO_SIGNATURE)
    return (read_as_node(args.digest, digest_ref(args.digest), args.authfile, None)
            | read_as_node(args.digest, IMAGE_REPO + ":" + fixed_tag(args.tag), args.authfile, None))


if __name__ == "__main__":
    sys.exit(main())
