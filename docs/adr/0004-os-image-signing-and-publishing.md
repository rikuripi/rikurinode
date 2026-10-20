# ADR 0004 — OS images are key-signed in CI and published publicly

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-12 (the recommendations) |
| **Decision** | D6 and D7 of `docs/architecture/platform-plan.md` |
| **Sources** | `docs/build-records/evidence/2026-10-12-stage1-os-image/research.md` |

## Context

Each node updates by pulling its next OS image and must refuse any image the
project did not sign (plan §4.1). The repository is private. Facts that
decide it (research, 2026-10-12): the node's image library cannot yet enforce
keyless signatures made in GitHub Actions; cosign 3.x signs by default in a
format that library cannot see, while `cosign verify` still passes; a private
registry needs a GitHub token stored on every node.

## Decision

- **D6:** the OS image is published as a **public** package on GitHub's
  container registry (ghcr.io); the repository stays private.
- **D7:** images are signed with a **cosign key** held in a GitHub
  Environment that only `main`'s publish job can use. A **spare key** is made
  by the owner and kept offline; its public half ships in every image beside
  the main one, so a lost or leaked main key can be replaced without
  reinstalling any node. The node's policy accepts only these keys for this
  image.

## Consequences

- Nodes need no credentials to update, and checking a signature needs no
  network beyond the registry (so it should work over Tor; not yet tried).
- Anyone can download the image: by rule it holds no secret
  (`image/check_image_root.py` refuses, in etc, root, var, usr/local, opt,
  tmp and boot, these forms only: a PEM private key or PGP key block, an
  SSH host key under etc/ssh, a Tor onion service or ed25519 secret key, an
  age secret key, a WireGuard private key; files over 1 MiB and links are
  not read, and Fedora's own files under /usr are not scanned; the gate's
  secret scan covers the files added to it). Making the GHCR package
  public cannot be undone.
- Signing uses cosign's older format (`--new-bundle-format=false`) until the
  image library reads the new one, and CI verifies each signature with the
  node's own policy (skopeo or podman), not with `cosign verify`.
- Pull requests never reach the key: only a job on `main`, in the protected
  Environment, signs. A repository admin could still misuse it.
- A signature names the repository, not the version: the node's version rule
  (plan §4.2, never downgrade) must refuse an older signed image.
- Owner steps, once: create the Environment and its secrets; make the spare
  key offline.

## Rejected

- Keyless signing (GitHub's identity, no stored key): the node cannot enforce
  it today (containers-libs issue 34, pull request 625 unmerged).
- A private registry with a token on every node: one stolen node leaks an
  account-wide token, and an expired token stops updates silently.
- The owner signing each release offline: CI could never sign, but every
  release would need the owner at a command line.
- quay.io: the same as public GHCR, with a second account to manage.
