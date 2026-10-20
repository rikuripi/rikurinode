# ADR 0013 — Container images built by Nix from nothing: one experiment, then keep, simplify or drop

| | |
|---|---|
| **Status** | Proposed — drafted 2026-10-20 from the owner's direction in chat ("Yes, let's promote Nix-built images and Rusts runbook executor to ADRs."). It proposes an experiment; it becomes a decision only if the experiment passes its criteria and the owner accepts the result |
| **Decision** | D20, to be added to `docs/architecture/platform-plan.md` §7 |
| **Supersedes** | Nothing. If the experiment keeps, §4.2 of the plan ("built by this project from the upstream release binaries") is amended by dated clarification |
| **Beside it** | ADR 0004 (image signing and publishing), ADR 0005 (probes and `Notify=healthy`), ADR 0006 (release sets bound to the image), ADR 0007 (rootful Podman), ADR 0009 (the threat model) |

## Context

Plan §4.2 says each component is a container image built by this project
from the upstream release binaries, after verifying their signatures and
checksums, pinned by digest, with no third-party prebuilt images. ADR 0005
orders units by `Notify=healthy`, so the probes must ship in the images this
project builds (the previous node's checks used tools its images lacked,
PLAT-06). The threat model's T6 says no shell anywhere, and T8 covers the
supply chain.

The idea the owner liked in the design discussion: an image with no shell and
no package manager, holding only the program and what it needs, so that a
breached container has nothing to run. Nix's `dockerTools.buildLayeredImage`
builds an image from nothing and includes the runtime closure of the program
it is given, so the contents follow from the program's closure, which
`nix path-info -r` lists; the experiment checks the image against that list. A Containerfile that copies a binary onto `scratch` can
also be shell-less, but it has no automatic list of what the program pulls in.

Prior art: nix-bitcoin, a collection of Nix packages and NixOS modules for
Bitcoin nodes. Its last release, 0.0.139, was published in August 2026 as
its final one; according to CriptoNoticias, its farewell invited forks, and
others relaunched it as
Bitcoinix on 14 October 2026, which describes itself as experimental. That
last release fixed LND's admin macaroon being passed in curl's argument list,
readable from `/proc` (the class of SEC-01). It is a source of ideas, not a
dependency: AGENTS.md §2 asks about provenance and maintenance before adoption,
and the project has already stopped once.

## Decision

- **Run one experiment first,** on bitcoind only. The stated question: can a
  Nix-built, from-scratch image of Bitcoin Core replace the stage 2
  Containerfile build, and be audited, run, health-checked, bound and verified
  more simply or more safely? It runs in a disposable environment with no
  secrets and the network denied except named destinations, never against the
  live node, within a time budget the owner sets in its Build Record
  (AGENTS.md §2 and §6).
- **Nix is a build tool and never runs on the node.** The OS stays Fedora IoT
  on bootc; the images are published to the same registry by digest, signed as
  ADR 0004 says, and bound to the OS image (ADR 0006). Nixpkgs is pinned by
  commit in a committed lock file.
- **The experiment is kept only if all of these hold, with receipts:**
  1. *Contents.* `nix path-info -r` of the image lists no shell, package
     manager, coreutils, curl or wget; the list goes in the Build Record.
  2. *Runs as designed.* Under the stage 2 Quadlet unit with `ReadOnly`, all
     capabilities dropped, `NoNewPrivileges` and `UserNS=auto`, on regtest;
     the stage 2 drills (a kill and restart during sync, a power loss) pass.
  3. *Health without a shell.* The image carries an exec-form probe, one
     static binary this project builds, and `Notify=healthy` works with it.
     Whether Quadlet's `HealthCmd=` accepts an exec form with no shell is to be
     verified; if not, the experiment fails or another way is decided then.
  4. *Bound.* A file in `/usr/lib/bootc/bound-images.d` names the image by
     digest and `bootc upgrade` pulls it (ADR 0006).
  5. *Provenance.* Plan §4.2 is met one of two ways. *Wrap:* the upstream
     release binary, its signature and checksum verified when the pin is
     chosen. If it cannot run in a from-scratch image without patching its
     interpreter and library paths, the bytes the signature covered change; both
     hashes and the change are recorded and the owner decides if that is
     acceptable. *Build:* Bitcoin Core from pinned source in nixpkgs, with the
     release tag's signature verified on the source; §4.2 is then amended,
     because the image no longer holds the upstream binary.
  6. *Repeatable.* Two builds from the same pinned inputs on two machines give
     the same image digest, or the differences are explained. Repeatability is
     measured, not assumed.
  7. *Cost.* Image size, memory and build time are recorded and no worse than
     the Containerfile build by an amount the owner accepts.
  8. *Adoption inspection.* The source, provenance, licence, maintenance and
     dependency tree of Nix and nixpkgs are inspected and recorded
     (AGENTS.md §2).
- **If all hold:** keep it for the other images (LND, Tor, electrs, later
  mempool), amend §4.2, and make the CI change its own control-change task.
  **If some fail:** simplify (a Containerfile from `scratch` with the binary,
  the probe and the same contents audit) or drop. No partial adoption: one
  build system for the images.

## Consequences

- A second toolchain, and a language, for a solo maintainer. The cost is
  accepted only if the experiment shows the audit and the repeatability are
  worth it.
- No shell means no `exec` into a container. Debugging uses the Diagnostics
  page (ADR 0011) and the journal; a debug image is built on purpose and never
  shipped.
- The aarch64 build for the Pi needs a builder, by cross-build or a native
  runner; neither is verified, and it matters only if D1 keeps the Pi.
- Edits that follow, each its own change: a D20 row in the platform plan §7; a
  §4.2 amendment if the experiment keeps; the threat model's T25 (added with
  this ADR); a contents check for service images beside the OS image's.

## Rejected

- Shell-bearing base images (Fedora or UBI): they keep a shell and a package
  manager in every container.
- A Containerfile from `scratch` as the first choice: it is the fallback, and
  it has no automatic closure listing.
- NixOS as the host: the operating system stays Fedora IoT on bootc; this ADR
  is about the contents of container images only.
- Depending on nix-bitcoin or Bitcoinix modules: a volunteer project that
  has already stopped once.
- Health checks only from outside the container: ADR 0005's ordering by
  `Notify=healthy` would no longer work.

## Sources (read 2026-10-20)

- `docs/architecture/platform-plan.md` §4.2; ADR 0004, 0005, 0006, 0007;
  `docs/security/THREAT_MODEL.md` T6, T8; `AGENTS.md` §2 and §6; the lessons
  register's PLAT-06 and SEC-01.
- [nixpkgs, "Create a many-layered Docker Image" (#47411)](https://github.com/NixOS/nixpkgs/pull/47411):
  `buildLayeredImage` includes the runtime closure of the config.
- [nix-bitcoin 0.0.139](https://github.com/fort-nix/nix-bitcoin/releases/tag/v0.0.139):
  the final release and the macaroon fix.
- [CriptoNoticias, Bitcoinix relaunch](https://www.criptonoticias.com/tecnologia/nix-cliente-nodos-bitcoin-bitcoinix/):
  the relaunch of 14 October 2026 and its "experimental" description.
- Not read for this draft, to be read by the experiment: Podman's
  `podman-systemd.unit` page on `HealthCmd=` and bootc's logically bound
  images page (ADR 0006's sources), Nix's own reproducibility documentation.
