# ADR 0006 — Releases are tested sets, bound to the OS image

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-17 (the principle: "2 & 3. A"; the mechanism with package R of D13, the same day; record `docs/build-records/2026-10-17-plan-review.md`) |
| **Decision** | D12 of `docs/architecture/platform-plan.md`; its §4.2 |
| **Supersedes** | The rule of 2026-10-10, carried into the plan on 2026-10-11, that a component's version is machine state and the newer wins |
| **Beside it** | ADR 0005 (supervision), ADR 0007 (rootful Podman, which this mechanism needs) |

## Context

The previous node upgraded each service on its own. Combinations were never
tested together, an adjustment one service needed for another's new version
was made live, Electrs 0.12 was reported "upgrade complete" two seconds
after start while it crash-looped (UPG lessons), and after its last OS
update the node could not recover consistently. The owner, 2026-10-17: "The
trick is to make failed upgrade of rikurinode and all its associated
services repairable either with rollback or restarts. … if upgrade to latest
fails, then use the one previous stable container."

## Decision

- **A release is one tested set:** the OS image with the control plane in
  it, the container images by digest, their settings templates and any
  migration, proven together in CI (regtest) and on the N150 before a node
  sees it. A node moves between releases, never one service at a time; an
  in-app upgrade offers the next release, says what changes in it, and does
  nothing else.
- **The container images are bound to the OS image.** Their Quadlet files
  are linked under `/usr/lib/bootc/bound-images.d`, so bootc pulls them when
  an update is staged, keeps the ones that belong to the rollback
  deployment, and removes images no file references. One update, one
  rollback, and the node boots without the network.
- **Proven or undone.** After the reboot, greenboot's required checks (plan
  §4.1) judge the set; three failed boots return the previous image and,
  with it, the previous containers. Once booted, the control plane watches
  each service for its start period plus interval times retries plus a
  margin; a failing service is restarted within bounds with a diagnosis
  captured first; still failing, the release is rolled back (`bootc
  rollback`, through the root helper of ADR 0007) and the owner is told what
  failed. The node stays on the last good set.
- **Migrations end automatic rollback.** A release that migrates a database
  (Bitcoin Core, LND) says so before the owner agrees, takes a backup with
  the service stopped, and from that point the previous release is never
  started automatically (the plan's rule, kept).
- **Every change is a release, and every release reboots** (LND and
  bitcoind stopped cleanly first, with their 90 s). The owner accepted this
  cost with package R.
- **Install media.** Anaconda does not support bound images, so the install
  path provides them another way, decided in stage 1: a `bootc install` from
  a live environment that carries the images, or a first-boot pull during
  setup. The setup page (D10) does not depend on the containers.

## Consequences

- Podman's auto-update is not used (`AutoUpdate=` unset); ADR 0001's
  consequence "Podman's auto-update can roll a container back" no longer
  applies. bootc's update is the one path.
- The units read their images from bootc's store, configured for the node's
  units and not globally (the bootc page's advice: a global additional store
  lets floating images break when shared layers go).
- The running release is reported from runtime truth: the digests the units
  run, not the manifest in the image.
- "Version is machine state" is gone with its reason: there are no
  per-service in-app upgrades for an image update to undo. `/var` (data) and
  `/etc` (the owner's settings) survive every update and rollback; data is
  never rolled back (plan §4.3).
- The release pipeline is stage 6's work; stage 2's first unit already
  follows the binding layout.

## Rejected

- Per-service upgrades: the previous node's model and its failures.
- Release sets applied by the control plane (package U of D13): more
  control-plane code on the rollback path, which is where the previous node
  failed, and two rollback mechanisms that must agree.
- Podman auto-update on moving tags: floating tags are forbidden by the
  hygiene rule, and auto-update judges only the first start, not a failure
  minutes later.

## Sources (read 2026-10-17)

- [bootc, logically bound images](https://bootc.dev/bootc/bootc-logically-bound-images.7.html):
  "the bound images defined in the new bootc image will be automatically
  pulled into the bootc image storage"; "The logically bound images
  corresponding to rollback deployments will also be retained"; "Rootless
  containers from these system stores are not supported"; Anaconda does not
  currently support logically bound images; the store is
  `/usr/lib/bootc/storage`.
- [podman-systemd.unit](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html):
  `AutoUpdate=registry|local`.
- The previous repository's lessons register, UPG-01 to UPG-12 and OWN-01.
