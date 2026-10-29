# ADR 0004 — OS images are key-signed in CI and published publicly

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-12 (the recommendations); clarified, not changed, 2026-10-28 (owner, "You start each publish (Recommended)" and "Fixed names only (Recommended)"; the section "Clarification (2026-10-28)" below; record `docs/build-records/2026-10-28-publish-signed-image.md`); clarified again 2026-10-29 (owner, "Fixed names only (Recommended)" for what a node follows; the section "Clarification (2026-10-29)"; record `docs/build-records/2026-10-29-node-refuses-unsigned.md`) |
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

## Clarification (2026-10-28): who starts a publish, and the names it uses

- **The owner starts each publish.** "Only `main`'s publish job" is
  `.github/workflows/publish.yml`: it is started by hand (`workflow_dispatch`)
  and never on a merge, and each of its jobs refuses any branch but `main`.
  GitHub offers no required reviewer for an Environment of a private repository
  on this plan, so the Environment `image-publish` limits only the branch
  (`main`). Its administrator bypass stays on, and the owner is the only
  administrator. The key is in the sign job alone, in one step, through
  `env://`, never in a file.
- **Fixed names only.** Each publish gets a tag that never moves,
  `<Fedora release>.<UTC date>.<run number>`. A re-run of the build is
  refused, because it would put another image under the same name. The
  moving name that nodes follow is decided when a node first follows one
  (stage 1, change 2c).
- **CI checks each signature as a node would.** Before signing, the published
  image's own skopeo and policy refuse it unsigned; after signing, they
  accept it, under the real name; a job with no credential then reads it as
  a node does.
- **The package is private until the owner makes it public** after the first
  publish (D6; runbook `docs/runbooks/publish-os-image.md`).

## Clarification (2026-10-29): what a node follows, and where its check is proven

- **No moving name.** Nodes follow no moving tag. A node is switched to a
  release's fixed name (`bootc switch ghcr.io/rikuripi/rikurinode:<fixed tag>`):
  in CI by the VM drill, later by the control plane. This settles the point
  left open above ("decided when a node first follows one"): the hygiene
  rule against floating tags holds for nodes too, and whoever can move a tag
  cannot point nodes at an older signed image. How a node learns of a new
  release is the control plane's, and the never-downgrade rule (plan §4.2)
  still stands.
- **The node's own update command checks the signature.** The VM drill
  (`image/drill/vm_drill.py`, cases 4 and 5) has the booted node's `bootc
  switch`, under the image's own policy and keys, refuse an unsigned image
  named `ghcr.io/rikuripi/rikurinode` and stage the first published, signed
  image, on every image pull request and every publish. The drill's VM
  reads that name from a registry on the CI machine; nothing unsigned is put
  in the public package.
- bootc's `--enforce-container-sigpolicy` is not used: it refuses any policy
  whose default is `insecureAcceptAnything`, which the node's is. A stricter
  default would be a separate owner decision.

## Rejected

- Keyless signing (GitHub's identity, no stored key): the node cannot enforce
  it today (containers-libs issue 34, pull request 625 unmerged).
- A private registry with a token on every node: one stolen node leaks an
  account-wide token, and an expired token stops updates silently.
- The owner signing each release offline: CI could never sign, but every
  release would need the owner at a command line.
- quay.io: the same as public GHCR, with a second account to manage.
