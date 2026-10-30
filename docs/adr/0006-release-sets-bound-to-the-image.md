# ADR 0006 — Releases are tested sets, bound to the OS image

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-17 (the principle: "2 & 3. A"; the mechanism with package R of D13, the same day; record `docs/build-records/2026-10-17-plan-review.md`); clarified, not changed, 2026-10-22 (owner, "Add dated clarification to ADR 0006."; the section "Clarification (2026-10-22)" below; record `docs/build-records/2026-10-22-adr-0006-clarification.md`); clarified 2026-10-29 (owner, "USB installer with the image inside (Recommended)"; the section "Clarification (2026-10-29)" below; record `docs/build-records/2026-10-29-install-media.md`) |
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

## Clarification (2026-10-22): how many failed boots, and what the rollback depends on

Recorded on the owner's word ("Add dated clarification to ADR 0006. We'll
probably use the information when our build gets there."). It changes
nothing above; it keeps what was observed with the decision.

- **Four boots, not three.** "Three failed boots return the previous image"
  reads greenboot's setting (`GREENBOOT_MAX_BOOT_ATTEMPTS=3`). greenboot
  0.16.4 sets its counter to three on the *first* failure, then counts down
  over three more boots, so a failing release runs **four** boots before the
  rollback (about a minute in the VMs tried; not yet measured on the N150 or
  the Pi; the node's services are down for that time). Observed in the Parallels experiment and in every CI drill
  run (`docs/build-records/2026-10-21-greenboot-drill-parallels.md`,
  `docs/build-records/2026-10-22-ci-vm-drill.md`); plan §4.1 already says four.
- **"Proven or undone" depends on two changes to stock greenboot**, both in the
  image since #28 and #29:
  - greenboot sets its rollback trigger only at shutdown; on a disk without a
    separate `/boot` partition (what `bootc install to-disk` makes) it never
    did, and a failing release stayed in place ("manual intervention
    required", greenboot-rs #218). A drop-in now orders the trigger against
    `final.target` (`docs/build-records/2026-10-22-greenboot-218.md`).
  - greenboot sets that trigger *before* the release is applied; when applying
    then fails, or the power is cut between the two, it rolled a healthy node
    back to the set before (greenboot-rs #219). A check before greenboot's own
    clears the trigger when the release was never applied, remounting a
    read-only `/boot` for that write
    (`docs/build-records/2026-10-22-d22-unapplied-update.md`; plan §4.1, D22).
- **Held by CI.** The `drill` job of `.github/workflows/image.yml` proves both,
  on every image change and weekly: a failing release returns the previous set
  with `/var` intact; a release that failed to apply, or was cut off by a
  power loss, leaves the node on its current set. A greenboot or Fedora update
  that brings either bug back fails that job.
- **For the builder of release sets:** a release's containers return with
  the previous image only through these paths; a release whose containers
  fail after the image's own checks pass is the control plane's to roll back
  (the "Proven or undone" bullet above), not greenboot's.

## Clarification (2026-10-29): the install media

Recorded on the owner's choice of 2026-10-29 ("USB installer with the image
inside (Recommended)"). It settles the "Install media" point above, which left
two ways open; nothing else changes.

- **The install path is a live environment.** It is a USB stick, made by
  image-builder (`bootc-generic-iso`) from the node's own pinned base, that
  runs `bootc install to-disk` from the node image it carries, read-only and
  offline. It is not Anaconda, and not a first-boot pull.
- **Carrying bound images is still to come.** None exist yet. The live
  environment is the way that can carry them; how the stick holds them, and
  the install puts them in the node's store, is decided with the first bound
  image.
- **Proven in CI** by the `install` job of `.github/workflows/image.yml`: the
  stick refuses two disks, erases nothing on any answer but `ERASE`, and the
  installed disk boots alone with greenboot passing (probe 6 and its
  follow-up, in the record).

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
