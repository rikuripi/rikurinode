# Platform and architecture plan

**Status: proposed, 2026-10-11; D5 to D9 decided 2026-10-12; D10 to D15
decided 2026-10-17, D13 superseding D5; D16, the assistant, and D17,
security built in, decided 2026-10-18; D18, the lobby zone, D19, remote
and expert access, an amendment to F3 (D16) in ADR 0012, D20, Nix-built
images as one experiment, and D21, the runbook executor, proposed and
decided 2026-10-20; D22, the boot-cause record and UPS support in stage 1,
decided 2026-10-21; D23, the frontend's stack, decided 2026-10-25.** D13
and D14 were clarified, not changed, on
2026-10-21 (ADR 0007, "Clarification (2026-10-21)";
`docs/build-records/2026-10-21-adr-0007-clarification-rootless-and-pods.md`).
Of its twenty-three owner decisions
(§7), twenty-one are taken — D2, Podman with Quadlet; D3, Rust; D5, rootless
with an ID range per container, superseded by D13, rootful with an ID range
per container; D6 and D7, the OS image public on GitHub's registry and signed
by a key in CI with an offline spare; D8, CI minutes; D9, Fedora's DNS boot
check off; D10, the setup page's connection; D11, accounts; D12, releases as
tested sets bound to the OS image; D14, a private network with fixed
addresses; D15, the frontend's shape; D16, the assistant's engine,
learning, cloud, models and voice; D17, security built in: the threat
model, a security slice per stage, the advisory intake loop and AISecurity
as a pinned dependency; D18 to D21, the lobby zone, remote and expert
access, Nix-built images as one experiment and the runbook executor; D22,
the boot-cause record and UPS support in stage 1; D23, the frontend's
stack: Svelte with Vite, Lightweight Charts, server-sent events, ts-rs and
the UI embedded in the control plane's binary
(ADRs 0001 to 0014,
`docs/build-records/2026-10-21-boot-cause-and-ups.md` for D22,
`docs/build-records/2026-10-25-d23-frontend-stack.md` for D23,
`docs/build-records/2026-10-17-plan-review.md`,
`docs/build-records/2026-10-18-assistant-plan.md` and
`docs/build-records/2026-10-18-security-plan.md` and
`docs/build-records/2026-10-20-accept-adrs-0010-0014.md`; D8 and D9 are
recorded in §7 only) — and two are open (D1, the
Pi 5; D4, the first mainnet amount); nothing that depends on an open one is
built. Facts about outside software were checked on 2026-10-11,
2026-10-17, 2026-10-18, 2026-10-20, 2026-10-21 and 2026-10-25 and carry their source (§9); re-check them before acting on them.

## In one page

- **Two nodes.** An Intel N150 mini PC (x86_64, 12 GB RAM, 2 TB disk) runs a
  full node. A Raspberry Pi 5 (8 GB) is meant to run a pruned node.
- **The operating system is an image.** Each node runs Fedora IoT, delivered
  as a bootable container image (bootc) that this project builds, signs and
  tests. An update replaces the whole system image; if the new image fails
  its health checks, the node goes back to the previous image by itself.
- **The node software runs in containers.** Bitcoin Core, LND and Tor run in
  containers that systemd starts, stops and watches — Podman with Quadlet
  units (decision D2), rootful, each container in its own user-ID range
  (decision D13, which superseded D5 on 2026-10-17) — each pinned to an
  exact, verified build and bound to the OS image (D12).
- **The node moves between release sets.** A release is one tested set: the
  OS image with the control plane, the container images by digest, their
  settings and migrations, proven together before a node sees it; a failed
  set is undone by going back to the previous one (D12). No service is
  upgraded on its own.
- **The control plane decides; systemd enforces; the assistant only
  suggests.** systemd and Podman enforce limits, restarts and ordering. The
  control plane, written in Rust (decision D3), decides what "healthy" means
  (a running bitcoind can still be syncing; LND's wallet can be locked),
  which phase a service is in, which fix applies, and how an upgrade is
  checked, done and rolled back. It is also the assistant's only door: a
  short, fixed menu of actions, each run through systemd and Podman, never a
  shell.
- **Data is never rolled back.** The blockchain, LND's channel database and
  the node's settings live outside the image and survive every update and
  rollback. Funds are protected by the wallet seed and the static channel
  backup kept off the node, and by a restore drill — not by going back in
  time.
- **The Pi 5 could not run Fedora IoT in the latest images found** (March
  2026, §3.2): no Fedora IoT or bootc image for it, boot from an SD card
  only, no fan or thermal control. The N150 comes first.
- **Security fits each stage.** The [threat model](../security/THREAT_MODEL.md) names the
  assets, what is trusted and what is not, and maps every threat to a
  control, a stage and a test; each stage row in §8 carries its security
  slice; advisories are checked weekly and a critical one cuts a release set
  within seven days, once the CI task lands; AISecurity's detectors are a pinned dependency that
  signals while systemd, Podman and the control plane enforce (D17,
  ADR 0009).
- **Everything that talks to outsiders sits in a lobby zone (D18).**
  Market feeds, chat alerts, backup upload and the AI relay run as helper
  containers off the core network, reach the internet only through one
  allowlisting proxy, and hand data to the control plane by a typed ingest
  route; no commands cross (ADR 0010).
- **No terminal in the web UI (D19).** A Diagnostics page of typed
  read-only actions for everyone; SSH for experts is key-only, off by
  default, enabled behind step-up for a window that ends on its own, and
  reachable only over Tailscale or a Tor onion service (ADR 0011).
- **Order of work:** the image and its rollback drill → Bitcoin Core → Tor →
  LND on a private test network → backup and a restore drill → updates and
  their rollback drill → the backend API → Lightning channel management,
  test-first, on test networks and then a capped mainnet amount → the
  frontend → the sandboxed assistant → the treasury and agent payments → the
  marketplace (stages 9 and 10, planned 2026-10-17 in the
  [agent payments and marketplace plan](agent-payments-and-marketplace-plan.md)).

## 1. What this plan answers

The owner's priorities, in order: security and reliability; then ease of use
and of maintenance; a novice should never need a command line. The backend is
made solid before the frontend. Whether code works is judged by tests,
verification and results.

The previous repository's lessons register (107 requirements; it lands in
this repository as its own change) sets the rules this plan must meet. The
ones that shape the platform most: one bring-up path and one owner per action
(OWN), upgrades proven before they are reported and reverted exactly (UPG),
backups trusted only once restored (FUND), and Fedora, Pi and container
specifics re-verified rather than assumed (PLAT).

## 2. Facts this plan rests on (checked 2026-10-11)

| Item | Fact | Consequence |
|---|---|---|
| Fedora 45 | Final release targeted for 2026-10-20 (fallbacks 10-27, 11-03). **2026-10-19:** the Go/No-Go of 2026-10-15 was a no-go (no release candidate published), so the target is 2026-10-27, with a Go/No-Go on 10-22 and a fallback of 11-03 (reported by the owner; checked against the public record, `docs/build-records/2026-10-19-b0-2-sign-in.md` §4). | Build on Fedora 45 once released. Fedora releases are short-lived, so the image moves to each new release after a soak, by owner approval. The image stays on its Fedora IoT 44 digest until then. |
| Fedora IoT bootc | Fedora IoT can be built and updated as a bootable container image; base images are published on registry.fedoraproject.org and quay.io. | The node's OS is a Containerfile in this repository, built in CI. |
| Image tooling | `bootc-image-builder`'s sources moved into `image-builder` (its migration notice, 2026-06-18); a Fedora IoT 44 bootc image build failed at its bootloader step in January 2026 (rawhide composes). | Pin the build tools by digest; build install media in CI; an install test on real hardware for every Fedora release. |
| greenboot | An open bug report (2026-10-09; one user's, no maintainer reply yet): on a device installed from the stock Fedora IoT 44 image, the first update that fails its health checks never rolls back — greenboot 0.16.2 arms the rollback with a variable that 0.16.4 no longer reads. | Never trust rollback until it is drilled on the device: the install procedure ends with a deliberately broken update that must roll back by itself (§4.1). **2026-10-21:** three more open reports on Fedora 44 bootc with greenboot 0.16.4, the newest release (2026-08-18), none with a maintainer reply, and a proposed fix for #217 by a regular contributor (#221, a pull request). The unit that arms rollback does its work only when stopped, and on hosts without a separate `/boot` mount nothing stops it at shutdown, so rollback is never armed (#218; the unit read at `v0.16.4` and on `main` lacks the `Conflicts=` that ostree's own finalize unit carries, read, not run; commenters show a separate `/boot` mount makes it run). An update that fails to apply at shutdown rolls the healthy running image back (#219; reproduced with a full `/boot` and a forced finalize failure; a power cut is named, not reproduced). `/boot` on a software mirror reboots a failing update forever (#220). A maintainer's issue says the default health checks do not fit bootc (#212). Whether stage 1's drill fails on the stock setup depends on the N150's install layout, and the drill decides it. D22's rule covers #219's case: an update that was never applied never rolls the running image back. **2026-10-22:** the CI drill reproduced #218 on the layout `bootc install to-disk` makes (no `/boot` partition): the trigger never ran and a broken update stayed, "manual intervention required" (run 39710186883); the image now orders the trigger against `final.target` (`docs/build-records/2026-10-22-greenboot-218.md`), and #219's case is handled by the unapplied-update check (`docs/build-records/2026-10-22-d22-unapplied-update.md`). |
| Raspberry Pi 5 | Peter Robinson published Fedora 44 images for the Pi 5 in March 2026 (Minimal, Workstation, KDE), on his blog, for testing. With them: boot from microSD only, no USB or NVMe boot; no thermal (fan) control, audio or NVMe; no IoT or bootc image. An investigation closed 2026-10-10 found no published `fedora-bootc` image booting on a Pi; `bootupd` does not manage the Pi's firmware or U-Boot. | §3.2: owner decision D1; re-check at Fedora 45. |
| Bitcoin Core | 31.1 (2026-07-08) is the newest final release; 32.0 is in release-candidate testing (target date 2026-10-10, not yet on the release page on 10-11). The project maintains the newest three major versions. | Start on 31.x; move to 32.x after its first point release and our own soak. |
| LND | v0.21.4-beta (2026-10-01) is the newest; v0.20.5-beta was released the same day. | Start on 0.21.x; every RPC the backend uses is tested against the pinned version, and the backend refuses an LND version it was not tested with. |
| Tor | Relays and clients of 0.4.8 and older lost support on 2026-09-01, so 0.4.9 is the supported series. Arti, the Rust Tor, released 2.7.0 on 2026-10-01. | Use C Tor 0.4.9.x, which LND drives through Tor's control port; whether Arti can serve LND is checked before any switch. |
| Podman | Podman's auto-update can roll a container back to its previous image when the restarted unit fails; a Quadlet unit with `Notify=healthy` is ready only once its health check passes. Fedora 45 ships Podman 6. | Container updates get the same "prove it or go back" rule as the OS (§4.2); since D12 (2026-10-17) the container images are bound to the OS image and go back with it, so auto-update is not used. |
| NVIDIA OpenShell | Open source (Apache 2.0): runs each agent in its own sandbox without privileges, limits its files and network, filters its system calls, and brokers its requests to a supervisor. | The candidate boundary for the assistant (stage 8), alongside the AISecurity policy. |

Re-checked for stage 1 on 2026-10-12, with sources:
`docs/build-records/evidence/2026-10-12-stage1-os-image/research.md`. Changes
since: the greenboot report is still open with no reply; whether a kernel
panic or a hang before userspace counts toward a rollback is not yet proven
(greenboot 0.16.4's `detect_grub_fallback` reports a GRUB fallback after a
panic; stage 1's change 4 drills it); Fedora 45 had 8 accepted blockers; the
base image is pinned on registry.fedoraproject.org, because quay.io drops old
digests within days (a 2026-09-22 digest was gone by 09-28); keyless image
signatures cannot be enforced on the node yet (D7).

## 3. The two machines

### 3.1 The N150 full node

- Fedora IoT 45, x86_64, from this project's signed bootc image.
- One disk: the image's deployments and `/var` (all data) on the same 2 TB
  device. The blockchain (≈ 0.7 TB) and an Electrs index fit with room for
  growth; the disk-budget check of UPG-11 runs before any index-format
  change.
- Bitcoin Core (not pruned), Tor, LND, and on this node only, Electrs and
  the explorer — added after the core is proven.
- Memory (12 GB) is budgeted per service (PLAT-04): Bitcoin Core's cache is
  large during the initial sync and reduced afterwards, by the node, not by
  hand.

### 3.2 The Raspberry Pi 5 pruned node — owner decision D1

Fedora IoT did not run on the Pi 5 in the latest images found (§2). The
options:

| Option | What it means | Cost |
|---|---|---|
| **A. Wait (recommended)** | Build and prove everything on the N150. Re-check the Pi 5 at each Fedora release (45, targeted 2026-10-27 after the slip of 10-15; 46 in spring 2027) against the checklist below; the image is built for aarch64 in CI too, so it is ready when the hardware is. | No pruned node until Fedora supports the Pi 5; no extra work now. |
| B. Raspberry Pi OS now | Debian-based, with full Pi 5 support (NVMe boot, fan control). | No image updates or automatic rollback — the update model this plan is built on would not apply; a second platform to maintain and test. |
| C. Fedora Minimal now | The Fedora 44 Pi 5 Minimal image, updated package by package. | No image rollback, OS on an SD card, no fan control — not suitable for a 24/7 node. |
| D. A second x86 mini PC for the pruned tier | The same image and tests as the N150, set to prune. | Buys hardware (a small N100/N150 box); the Pi 5 waits as in A. |

**Checklist before the Pi 5 can run a node** (each item seen working on the
device, not read in release notes):

1. A Fedora IoT bootc image for aarch64 boots on the Pi 5 from an NVMe or USB
   SSD (an SD card does not survive years of a node's writes).
2. Fan and thermal control work, and the node reads the CPU temperature
   (PLAT-02).
3. The rollback drill of §4.1 passes on the Pi, including power loss during
   an update.
4. Bitcoin Core pruned and LND on a pruned backend complete the LND test plan
   of §6 on a test network.

### 3.3 This machine (the Ryzen)

It keeps running the previous rikurinode and the live mainnet node until the
new node has passed every stage below and the owner chooses to move funds. No
test or container of this project runs on it (AGENTS.md > Testing on this
machine): unit tests only, inside `safe-run.sh`; anything that needs containers
runs in CI or on the N150 before it holds funds.

## 4. Three safety layers

A failed update must never cost the node or its funds. Three layers, each
proven by a drill before it is trusted.

### 4.1 Layer 1 — the operating system

- The image is built in CI from a Fedora IoT bootc base pinned by digest, and
  signed. The node verifies the signature before it stages an update.
- An update is staged in the background and applied at a time the owner
  allows. The previous image stays on the disk.
- After the reboot, health checks run (greenboot). Required checks, each with
  a bounded time: the container runtime starts the node's units; Bitcoin
  Core answers RPC (an initial sync in progress is healthy, an answer that
  stops advancing is not); LND's process answers (a locked wallet is healthy);
  Tor finishes bootstrapping; the data disk is mounted by its UUID. If a
  required check fails on four boots in a row (the first failure sets
  greenboot's counter to its three attempts; observed 2026-10-21,
  `docs/build-records/2026-10-21-greenboot-drill-parallels.md`), the node
  boots the previous image and says so on its status page and in an alert.
- **How the checks see the node** (review of 2026-10-16). The required
  checks ask the control plane's health endpoint on loopback and wait within
  a bound; the control plane judges the units (system units since D13, so
  the checks can also read them directly). bitcoind answering
  "in warmup" counts as healthy, and the bound covers a chainstate replay
  after an unclean stop, so a good image is never rolled back for a slow
  bitcoind. The rollback drill includes an unclean stop.
- **Why the node restarted** (D22). A machine cannot record its own power
  cut, so the cause is worked out at the next boot from what was written
  before it. The control plane writes a heartbeat to `/var` every minute
  and, before every shutdown it orders, the reason. At each boot it records
  one cause from the evidence: a clean shutdown (the persistent journal shows
  it complete); a shutdown ordered by the UPS (its reason written first); a
  power cut (no shutdown after the last heartbeat, which dates it to within
  a minute); a kernel crash (a pstore record); a hang reset by the hardware
  watchdog; an update applied, or rolled back (bootc's and greenboot's
  records). Evidence that fits none is recorded as unknown. The owner sees
  one sentence on the status page and in an alert, for example "Power was
  lost around 14:02; the node restarted at 14:40; your funds and data were
  not affected."
- **The rollback rule** (D22). An update that was never applied, for any
  cause (a power cut or a UPS shutdown while it is applied, a full `/boot`,
  an ostree error), never rolls the running image back: the node stays on
  it, records why, and stages the update again once; a second failure is
  reported to the owner (greenboot's open report #219, §2). After the new
  image has booted and until its checks pass, a kernel crash, a watchdog
  reset or a failed check counts against it, and a shutdown the UPS ordered
  does not. A power cut in that window counts only when it happens twice in
  a row, because a frozen node that its owner unplugs looks the same as a
  power cut. An unknown cause counts against the update: staying on a broken
  image is worse than a rollback the owner can retry. After a release that
  migrated data, none of these rolls back automatically: ADR 0006's rule
  ("Migrations end automatic rollback") holds and the owner is told. The
  record informs greenboot and never replaces its boot counter; greenboot
  counts every boot that does not report success, so it must be told which
  boots not to count. How is decided by the stage 1 change that builds it,
  against the reports of §2.
- **A UPS, when one is connected** (D22). A UPS that reports over USB is
  found without setup, and the status page shows it with its charge. On
  battery the node alerts with the time left; at low battery, or after a
  bounded time on battery, it stops the node's units in order (LND before
  bitcoind, once they exist), writes the reason and shuts down. After a UPS
  shutdown the node's units start again only once the UPS reports enough
  charge for another clean shutdown, so a low battery cannot cycle the node.
  A UPS that flaps or reports falsely orders a bounded number of shutdowns
  and is then reported, not obeyed. No update is applied while the UPS
  reports battery power or a low charge; it waits for mains power (owner,
  2026-10-21), so a new image's first boot never meets services held back
  for charge. Without a UPS none of this runs. Every
  node, with or without one, must start by itself when power returns: the
  setup page explains the N150 firmware's power-on-after-power-loss setting
  once, and checks it where the firmware lets Linux read it. The UPS service
  listens on loopback at most, never on the LAN. Network UPS Tools is the
  candidate; its source and its Fedora packaging are checked before
  adoption, like any third-party code.
- `/etc` keeps the owner's changes (merged on update) and `/var` keeps all
  data: neither is rolled back.
- **The rollback drill** ends every installation and runs again after each
  Fedora release change: a deliberately broken update is staged and must roll
  back by itself, with the node's data intact and the event reported. It is
  how the greenboot report of §2 would be caught. It also cuts the power
  while an update is applied and while the new image first boots, and makes
  an update fail to apply at shutdown, and checks that a good update
  survives each (staged again, or kept), that the running image is never
  rolled back for an update that was not applied, and that each boot's
  cause is recorded correctly (D22).

### 4.2 Layer 2 — the node software

- Each component is a container image built by this project from the
  upstream release binaries after verifying their signatures and checksums
  (Bitcoin Core's signed checksums, LND's signed manifest), pinned by
  digest. No third-party prebuilt images. The runtime is Podman (D2).
- One bring-up path: systemd starts the units in dependency order (OWN-01).
- **Releases are tested sets** (owner, 2026-10-17, D12; this replaces the
  2026-10-10 rule that a component's version is machine state and the newer
  wins, which served per-service upgrades). A release is the OS image with
  the control plane, the container images by digest, their settings and any
  migration, proven together in CI and on the N150. A node moves between
  releases, never one service at a time: an adjustment one service needs for
  another's new version ships in the same release. An in-app upgrade moves
  the node to the next release and nothing else. The container images are
  bound to the OS image (ADR 0006): pulled when the update is staged and
  kept for the rollback deployment, so one update is one rollback and the
  node boots without the network.
- A release is proven or undone: the new set must pass its health checks
  within the watch window (start period, interval times retries, a margin),
  or the previous set is restored. Restarts are bounded and diagnosed before
  a rollback; what cannot be repaired is reported with the exact failure,
  and the node stays on the last good set (ADR 0005).
- **Database migrations end automatic rollback.** Bitcoin Core and LND may
  upgrade their databases on first start; an older version must not run
  against a newer database. Before such an upgrade the node takes a backup
  with the service stopped, and after it the previous version is never
  started automatically; the owner is told, in plain words, before agreeing.

### 4.3 Layer 3 — funds and data

- Roll back software, never data. An old LND channel database is never
  restored: an outdated channel state can lose that channel's funds.
- The wallet seed is shown once, for the owner to write down; the node does
  not keep it in readable form.
- The static channel backup (SCB) is written off the node on every channel
  change, encrypted, to a destination identified by UUID (FUND-01, FUND-04).
- A backup counts only once it has been restored (FUND-02): the restore
  drill — seed and SCB on clean hardware, on a test network — is part of the
  plan, and runs through the UI.
- A watchtower is registered and its health shown (LN-02).

## 5. Software

| Component | Starting version | Runs on |
|---|---|---|
| Fedora IoT (bootc) | 45, after its release | both |
| Bitcoin Core | 31.1, then 32.x after its first point release | both (pruned on the Pi tier) |
| LND | 0.21.4-beta | both |
| Tor | 0.4.9.x (C Tor) | both |
| Container runtime | Podman with Quadlet, Fedora 45's (D2); rootful, a user-ID range per container (D13) | both |
| Control plane | Rust (D3), toolchain pinned; LND over its gRPC API, never linked in as a library | both |
| Electrs and explorer | later, after the core | N150 only |

Every version above is a starting point, re-checked when the stage that uses
it begins.

## 6. LND test plan

The previous node never ran Lightning channels with real funds (lessons
register, gap G1). Channel management is built test-first, in three steps; a
step starts only when the previous one is green.

1. **Private test network (regtest), in CI.** Bitcoin Core regtest and three
   LND nodes, all in containers, driven by the backend's own code: open a
   channel; cooperative close to a cold address; force close and the sweep
   after the timelock; a fee-policy update; a circular rebalance; a payment
   that times out and is resolved through its payment hash without paying
   twice; channel analytics bound to real LND fields; restore from the seed
   and SCB.
2. **Public test network (signet or testnet4), on the N150.** Real peers and
   gossip: node search, choosing peers, routing, fee changes seen by the
   network, a restore drill on clean hardware.
3. **Mainnet, capped (decision D4).** A small amount the owner sets; every
   money-moving step approved by the owner; a withdrawal to the owner's cold
   address as the final drill.

Every LND call is checked against the pinned LND version's RPC definitions,
and the backend refuses to run against a version it was not tested with.

## 7. Owner decisions

| | Decision | Options and their costs | Recommended |
|---|---|---|---|
| D1 | The Pi 5 | A wait, B Raspberry Pi OS, C Fedora Minimal, D a second x86 box — costs in §3.2 | A (and D if a pruned node is wanted soon) |
| D2 | Container runtime | **Podman with Quadlet from the start** — part of Fedora IoT, run by systemd, update rollback built in; costs: the previous node's Docker know-how and scripts do not carry over as they are. **Docker first, Podman later** (the owner's earlier idea for Fedora CoreOS) — familiar; costs: Docker is added to the image, and the move to Podman later is work done twice. | **Decided: Podman from the start** (owner, 2026-10-11; ADR 0001) |
| D3 | Backend language | **Rust** — the previous node's control plane is Rust (103 `.rs` files under `control-plane/` at its HEAD, 3bbbe392), and 12 of the lessons register's 90 port candidates come from it; it already uses LDK's `lightning` crate, and LDK is in the previous repository's plans; Rikuri-PI's foundation crates and gates can be shared; the compiler checks that a `match` over a closed set of cases — the assistant's action menu, the phase, wizard and upgrade state machines — handles every case, unless a catch-all arm is written; libraries such as `secrecy` keep secrets out of logs and debug output. Costs: slower compiles; LND's Rust clients are maintained by the community and trail LND — the previous node used `lnd_grpc_rust`, whose latest version (2.16.0) lacks calls LND 0.21.4 has (`XCreateAccount` and `SubmitPackage` in its wallet kit) — so this project generates its LND client from the pinned LND version's protocol files (that crate can also build from a chosen LND checkout) and keeps it current itself. **Go** — LND, Loop and Pool are Go, and Lightning Labs' `lndclient` follows LND's releases, though it too can trail (it has no `XCreateAccount`, which LND 0.21.4 has); costs: a third language beside Rust (Rikuri-PI) and TypeScript (the frontend), the compiler does not check that every case is handled, and `lndclient` brings LND's own code and some 190 dependencies inside the control plane's boundary (its `go.mod`). **TypeScript** — the previous node's dashboard backend, the source of 60 of the 90 port candidates; costs: it broke on runtime upgrades through native modules (PLAT-03); it stays the frontend's language. In every option the seed words and wallet password typed during setup pass through to LND and are not kept by the control plane; whether the wallet password is stored on the node to unlock LND after a reboot is decision G9's (below). Thin interfaces over systemd, Podman and LND keep each backend replaceable in tests (the analysis the owner shared on 2026-10-11 proposed them for systemd and LND, so the language stays swappable; this plan adds Podman, and uses them to fake each backend in tests). | **Decided: Rust** (owner, 2026-10-11; ADR 0002; this plan first recommended Go, without having checked the previous control plane's language and its LDK use) |
| D4 | First mainnet amount (§6 step 3) | **A small fixed amount** for one or two channels (for example 0.01 BTC in all) — costs: that amount at risk in software proven only on test networks, plus on-chain fees to open and close. **A larger amount** for real routing (for example 0.05 BTC) — costs: more at risk before mainnet experience. **No mainnet yet**, a longer public-test-network soak — costs: channel management stays unproven under mainnet's real conditions. | A small fixed amount, decided when step 3 begins |
| D5 | Rootless or rootful containers | **Rootless, one user** (Podman's default) — Podman and the containers run as an unprivileged user, so an escape gets that user, not root; but by default each container's root is that same user, which owns every container's data: an escape from the Tor container reaches LND's wallet files and Bitcoin Core's data. **Rootless, a range per container** (`userns=auto` from the user's subordinate IDs) — an escape gets an unprivileged ID that owns no other container's data; costs: the user's range must be large enough to divide, and an unsized `--userns=keep-id` cannot sit beside it. Costs of both rootless options: the services are user services, kept running after logout by systemd's lingering, and cannot wait for system units (Quadlet's example: `network-online.target`); container storage lives in the user's home unless moved; networking goes through `pasta` — containers reach each other only with extra configuration, and on rootless bridge networks port forwarding uses `rootlessport` by default, which loses the client's address; ports below 1024 need a kernel setting (the node's own ports — 8333, 9735, 10009, 9050 — are above it, a web page on 80 or 443 is not); memory, CPU and process limits work through the delegation systemd gives every user service (since systemd 252; Fedora 45 ships 262), which PLAT-04's budgets need, while I/O limits and CPU pinning need one more setting. **Rootful, a range per container** (`userns=auto` from the `containers` ranges) — the same separation between containers; cost: Podman itself runs as root, so a runtime bug reaches the whole host; benefit: ordinary system services, ordered like any other. In both range options the runtime's own account can reach every container's data — rootless Podman's user can read, change or remove anything its subordinate IDs own (`podman unshare`) — so a bug in Podman, or anything that drives it, reaches LND's wallet either way; the control plane's access to the runtime must stay narrow in every option (EXEC-08: no unrestricted container-runtime access, no root socket, control through a narrow, audited interface). **All three** need ID ranges in `/etc/subuid` and `/etc/subgid` and data volumes owned to match the IDs each container runs as. (The rootless tutorial's answer for a non-root image user, `--userns=keep-id`, runs that container as the shared user, so it gives up the separation the range options are for.) The lessons register lists rootless runtime access for the backend (EXEC-08) as a thing to re-check. | Rootless with a range per container: the same separation between containers as rootful, and a runtime bug stops at an unprivileged account (which still reaches every container's data) instead of the host — paid for with the user-service costs above. The owner's message of 2026-10-11 assumed rootless ("systemd and rootless Podman"), before these options were set out. **Decided: rootless, a range per container** (owner, 2026-10-12; ADR 0003). **Superseded** 2026-10-17 by D13, package R: rootful, a range per container (ADR 0007) |
| D6 | Where the OS image is published | **A public package on GitHub's registry** — nodes update with no credentials; anyone can download the image, which holds no secret by rule; making it public cannot be undone. **A private package** — a token stored on every node: one stolen node leaks an account-wide token, and an expired one stops updates silently. **quay.io, public** — the same as the first, a second account to manage. | **Decided: public on GitHub's registry** (owner, 2026-10-12; ADR 0004) |
| D7 | Who holds the image signing key | **A key in CI, usable only by `main`'s publish job, plus a spare kept offline** by the owner, its public half in every image — costs: a repository admin could misuse the CI key. **An offline key the owner uses for each release** — CI can never sign; costs: the owner at a command line for every release. Keyless signing is not an option yet: the node cannot enforce it (stage 1 research). | **Decided: CI key, `main` only, with an offline spare** (owner, 2026-10-12; ADR 0004) |
| D8 | CI minutes for the OS image | **Private repository**: 2,000 free minutes a month on 2-CPU runners; the image builds on pull requests that touch it, and the VM rollback drill (an estimated 40–70 minutes) runs on image changes and once a week. **A public repository**: larger runners and unlimited minutes; costs: every build record, with details of the owner's machine and live node, becomes public. | **Decided: private; drill on image changes and weekly** (owner, 2026-10-12) |
| D9 | Fedora IoT's DNS boot check | **Off**: an internet or ISP outage at an update's reboot must not roll a good update back; the node's own required checks (§4.1) replace it. **Kept**: fewer changes to Fedora's setup; costs: a network outage at reboot rolls the node back. | **Decided: off** (owner, 2026-10-12; `image/rootfs/etc/greenboot/greenboot.conf`) |
| D10 | The setup page's connection (stage 1) | A browser trusts a certificate only when a CA it knows signed it, and no public CA signs a `.local` name. **A. A per-node certificate authority with a guided one-time install** — the node makes its own CA at first boot; the first setup screen, reached over plain HTTP, offers the certificate with a short per-device guide (Windows, macOS, iPhone, Android, Linux), then switches to HTTPS; fallback: accept the browser's warning once; costs: one extra screen and a step per device; no third party, works offline; the seed and the wallet password never cross the network in the clear. **B. Plain HTTP on the LAN** — costs: the seed and the password readable by any compromised device on the network. **C. The owner's own domain with ACME (DNS challenge)** — a certificate every browser trusts; costs: a domain, a DNS provider's API key, the internet, and the node's name in public certificate logs; a later opt-in, not the default. | **Decided: A** (owner, 2026-10-17, "1. A") |
| D11 | Accounts (stage 1) | "Root is read-only" on Fedora IoT means the root *filesystem* (`/usr` immutable; `/etc` and `/var` persist and merge across updates), not the root user; accounts work normally. **Web sign-in only (recommended)** — `root` locked with no password and no SSH; a fixed system account runs the node; the owner signs in to the web page with a password set on the setup page; SSH off, enabled later under technical settings with a key; costs: an owner who wants a shell takes one more step; a web form never sets a Linux credential. **A Linux admin account made at setup** — a shell from day one; costs: a password SSH account on a funds device, set through a web form. | **Decided: web sign-in only** (owner, 2026-10-17, "D11. as you recommend") |
| D12 | How releases are shipped (§4.2) | **Principle, decided:** a release is one tested set — the OS image with the control plane, the container images by digest, their settings and migrations — proven together in CI and on the N150; a node moves between sets, never one service at a time; a failed set is undone by going back to the previous one (owner, 2026-10-17: "if upgrade to latest fails, then use the one previous stable container. Any failure needs to be monitored and fix or rollback"; and on the previous node: "the current upgrade does separate upgrades for each services. But some upgrade require rikurinode to make adjustments … My running node can't recover consistently"). This supersedes the 2026-10-10 rule that a component's version is machine state and the newer wins. **Mechanism (decided with D13, package R):** **bound to the OS image** — bootc's logically bound images are pulled with `bootc upgrade` and "the logically bound images corresponding to rollback deployments will also be retained": one update, one rollback, boots without the network; costs: every release, even an LND patch, is an OS update with a reboot (LND stopped cleanly first); available only to rootful Podman ("rootless containers from these system stores are not supported"), and Anaconda does not support bound images, so the install media must copy them another way. **Applied by the control plane** — it pulls the next set before the switch, keeps the previous set until the next is proven, and refuses to start a set that is missing; costs: more control-plane code on the rollback path, which is where the previous node failed, and two mechanisms that must agree. | **Decided** (owner, 2026-10-17, "2 & 3. A"): tested sets, bound to the OS image (ADR 0006), with package R (D13) |
| D13 | Rootless or rootful, revisited as a package (D5, ADR 0003) | Two facts read on 2026-10-17 (§9) bind D5, D12's mechanism and D14 together: bound images are rootful-only, and a pod's user namespace is set "for all the containers in a pod", so one pod means one ID range shared by bitcoind, Tor and LND, not ADR 0003's range per container. **Package R: rootful Podman, a user-ID range per container** (`userns=auto`; D5's third option) — system Quadlet units; the container images bound to the OS image; a private bridge network with fixed addresses, so the range per container is kept and inbound peers' addresses are preserved; the control plane a system service under its own user with one small root helper for a fixed list of actions (`bootc` upgrade and rollback, hostname, the backup drive, reboot); greenboot sees the units directly; `OOMScoreAdjust` available; costs: Podman's own setup code runs as root, so a bug in it reaches the host (the container processes still run as unprivileged mapped IDs); ADR 0003 superseded by a dated ADR. **Package U: rootless, as decided** — the control plane applies release sets and keeps the images (D12's second mechanism); containers in one pod on pasta (one ID range per pod; pasta "preserves the original source IP address") or on a bridge network with a range per container (`rootlessport` "does not preserve client source IPs"; the pasta forwarder for it is experimental); the control plane a user service beside the units plus a root helper (the owner's "4. A"); greenboot asks the control plane; units kept alive by lingering; costs: more control-plane code on the rollback path, the rootless networking trade-offs, boot ordering through lingering. | **Decided: package R** (owner, 2026-10-17, "D13 Package R as you recommended"; ADR 0007 supersedes ADR 0003): the one-image, one-rollback model is only available rootful, and `userns=auto` keeps the separation between containers that ADR 0003 wanted. **Clarified 2026-10-21**, not changed (ADR 0007, "Clarification (2026-10-21)"; owner, "Yes, please record."): rootless is not safer for the wallet, because the rootless account owns every container's data; what rootful gives up is named there |
| D14 | Internal network (stage 2) | **One pod** (the owner's pick of 2026-10-17): bitcoind, Tor and LND on localhost; RPC, REST and ZMQ never leave it; the stale Tor address of the previous node cannot occur; costs: one ID range per pod (D13). **A private network with fixed addresses**: a range per container kept; the services bind to their fixed addresses and the Tor address never changes; costs: more network configuration (and, under a rootless runtime, its forwarding trade-offs). | **Decided: a private network with fixed addresses** (with package R; owner, 2026-10-17; ADR 0007). **Clarified 2026-10-21** (ADR 0007, "Clarification (2026-10-21)"): pods are not used on the node; one pod would give bitcoind, Tor and LND one ID range and one network namespace, with nothing between their ports |
| D15 | The frontend's technical shape | TypeScript stays the UI's language (D3). **Static files, built in CI and served by the Rust control plane**: no Node.js on the node, so PLAT-03's class (a runtime replaced under a native module) and PLAT-11's (a proxy site) cannot occur. **One typed contract**: the UI's API types generated from the Rust types in CI, so a renamed field fails the build; EVID-02's four-state status with an explicit `unknown` is a type the UI cannot coalesce to 0. **Render tests in CI** (TEST-10): phone, tablet and desktop widths, every theme variable defined, every text key present in every shipped language (the previous UI ships en, es, ja, zh, zh-TW). **Supply chain**: lockfile committed, installs with scripts off, a dependency audit that cannot pass silently (SEC-06), the Node toolchain pinned and present only in CI. **Sizing**: 61 of the register's 90 port candidates are TypeScript, about 12,000 lines, re-expressed in Rust with their tests; the previous backend is 172,000 lines, and "behaviour and tests, not code" is what keeps stage 7 from being that. The look: the owner wants it "a bit softer, fun" than the previous page, which was "clean, but a bit crowded and verbose"; a design system is the first UI slice's first step. | **Decided** (owner, 2026-10-17) |
| D16 | The assistant: engine, learning loops, cloud tier, models on the node, voice | Five choices, each with its alternatives and their costs in the [assistant plan](assistant-plan.md) §2: F1 llama.cpp's official server image pinned by digest, not ik_llama.cpp and not the previous node's Lean_llama.cpp fork; F2 no behaviour-changing learning loop until a labelled evaluation exists, then reflection into a reviewed backlog; F3 no cloud model by default, an owner-enabled exception for reflection and evaluation only, redacted and recorded (AI-02's dated caveat); F4 one model with a grammar for both of its jobs, a second router model only if the gate says so; F5 speech-to-text on the phone first, whisper.cpp on the node later if memory allows, approval never by voice. **Amendment decided 2026-10-20** (owner, "accept all five."; ADR 0012; the text of 2026-10-18 above stands, amended by this): F3 gains three lanes by data class: local by default for chat, actions and anything touching node data; an external public lane with no private fields; and an external review lane that carries only a typed, sanitized weekly report card for a performance review of fees, rebalancing and profitability. Each is opt-in and off by default, every send goes through the lobby zone's relay and is recorded first, external answers are only typed suggestions that Rust bounds-checks and the owner approves, and none moves funds. | **Decided** (owner, 2026-10-18; ADR 0008 for the engine; `docs/build-records/2026-10-18-assistant-plan.md`) |
| D17 | Security built in: AISecurity's place, advisory intake, image scanning, the threat model | Four choices with their alternatives and costs in the [threat model](../security/THREAT_MODEL.md) and ADR 0009: S1 AISecurity's `security-core` linked as a Git dependency pinned by commit, features limited to the detectors, signals only, enforcement by systemd, Podman and the control plane (not a daemon beside it, not vendored, not deferred); S2 a weekly scheduled advisory audit in CI whose failure emails the owner, and a release cadence: a critical advisory cuts a set within 7 days, a high one within 30, at least one set a month (not quarterly; no dependency bots); S3 a scanner for the built images adopted after the inspection `AGENTS.md` §2 requires (not Fedora's advisories alone); S4 the threat model now, before stage 2 (not at stage 7). The CI parts are the next task, a control change. S5, disk encryption at rest, is open there. | **Decided** (owner, 2026-10-18, "do as you recommended"; ADR 0009; `docs/build-records/2026-10-18-security-plan.md`) |
| D18 | Where outside-facing code lives: market feeds, chat alerts, backup upload, the AI relay (stages 5 and 8) | **A lobby zone:** four helper containers (feeds, notifier, backup uploader, AI relay), each in its own ID range and off the core network, reaching the internet only through one allowlisting egress proxy, joined to the control plane by a typed ingest route and typed events, no commands; costs: more containers to pin and patch, an allowlist to maintain, and Telegram and Discord still learn that the node exists. **Inside the control plane:** the one authority would parse hostile input and hold outbound credentials. **In the browser:** the owner's address goes to every third party (EVID-05). | **Decided** (owner, 2026-10-20, "accept all five."; ADR 0010; `docs/build-records/2026-10-20-accept-adrs-0010-0014.md`) |
| D19 | A shell, remote paths and diagnostics (the "later choice" of D11) | **No terminal in the web UI; a Diagnostics page of typed read-only actions; key-only SSH, off by default, enabled behind step-up for a window that ends on its own (one hour, at most 24: confirmed by the owner, 2026-10-20), reachable only over Tailscale or a Tor onion service; remote web UI paths optional and off by default;** costs: experts lose a web terminal, and a key and a window are to be managed. **A filtered web terminal:** a command filter is a tripwire, not a boundary (EXEC-04, AI-02). **A full web terminal behind a password and 2FA:** a root-equivalent path behind one sign-in. **SSH always on from the LAN.** | **Decided** (owner, 2026-10-20; ADR 0011; same record; the window's defaults confirmed the same day) |
| D20 | How the service images are built (stage 2; §4.2) | **One experiment on bitcoind first: an image built by Nix from nothing**, holding only the program, its runtime closure and one exec-form probe, contents listed by `nix path-info -r` and refused if they hold a shell, package manager, coreutils or curl; nixpkgs pinned by commit; Nix as a build tool only, never on the node; kept for every image only if all of ADR 0013's criteria hold (contents, the stage 2 drills, health without a shell, bound to the image, provenance under §4.2, repeatable builds, cost, the adoption inspection); costs: a second toolchain for one maintainer, no `exec` into a container, and patching an upstream binary to run from nothing changes the bytes its signature covered. **Fallback: a Containerfile from `scratch`** with the binary, the probe and the same contents check; costs: no automatic closure listing. **Shell-bearing base images:** a shell and a package manager in every container. | **Decided: the experiment** (owner, 2026-10-20; ADR 0013; same record); Nix itself only if the experiment keeps |
| D21 | How the control plane repairs (stages 2 to 7; ADR 0005) | **Typed Rust runbooks over a closed action enum, compiled into the image:** each with an issue type, a precheck, one action, a validate probe, an undo, a budget and a tier; every action one call through systemd, Tor's control port or the root helper, never a shell (`std::process::Command` banned by clippy, a control change still to make); attempts recorded before acting and budgeted (HEAL-03); tier 4 effects (moving funds, deleting or restoring channel data, downgrading LND, disabling SELinux, the firewall or signature checks) not expressible; read-only credentials only; costs: a runbook change is a release, not a fix on a node. **Runbooks as YAML or TOML data:** gives up the compiler's exhaustive check and needs its own validator (HEAL-04). **Shell scripts or a generic command action with an allowlist:** EXEC-01, EXEC-04, AI-02. | **Decided** (owner, 2026-10-20; ADR 0014; same record) |
| D22 | Why the node restarted, and a UPS (§4.1) | **Both in stage 1, beside the rollback they protect:** the boot-cause record, its rollback rule and UPS support built and drilled with stage 1's rollback; costs: a larger stage 1; more code on the rollback path; a UPS service in the image (run as root, reading a new USB device); only the UPS models at hand can be drilled. **The boot-cause record in stage 1, the UPS later:** costs: until then every power cut is an unclean stop. **Both later:** costs: stage 1's drill cannot tell a power cut from a failed update, and greenboot's open reports (§2) show where that leads. | **Decided: both in stage 1** (owner, 2026-10-21, "can we just include boot-cause rule and UPS support as stage one? If they are all about reboot and rollback."; `docs/build-records/2026-10-21-boot-cause-and-ups.md`); no update applied on battery (owner, 2026-10-21, option B of the same record) |
| D23 | The frontend's stack, inside D15's shape (stages 1 and 8) | **Framework: Svelte with plain Vite**, no SvelteKit (Svelte's own guide describes this setup); chosen for a smaller dependency tree, which the first UI slice measures; costs: fewer ready-made libraries than React, and a router to choose (the guide says one is likely needed). **React with Vite:** more ready-made libraries; costs: a larger set of packages to inspect and pin. **Charts: TradingView's Lightweight Charts**, loaded only on the pages that draw charts; Apache-2.0, which "requires specifying TradingView as the product creator": the attribution notice from its NOTICE file and a link to TradingView on a page users can reach, the link met by its `attributionLogo` option. **Live data: server-sent events**, one pipe from the control plane for sync progress, service status and the assistant's streamed replies, under four rules: (1) one stream per browser, carrying every topic and shared by its open tabs, since without HTTP/2 a browser holds at most six connections to one site across all its tabs and the control plane serves HTTP/1.1; costs: the sharing between tabs is code to write and test; (2) authenticated by the session cookie on the same origin, never by a token in the URL (an EventSource cannot send an `Authorization` header); (3) resumed after a reconnect with `Last-Event-ID`; (4) a dropped stream turns every value it fed to stale in the UI, never left showing its last value (EVID-04). **Polling:** costs: a request per gauge per interval, and staleness hidden between polls. **WebSockets:** costs: a second protocol, and authentication and reconnection written by hand. **Types: ts-rs**, a derive on the Rust types the API sends; `cargo test` writes the TypeScript files and CI fails when they differ from the committed ones, so a renamed field fails the pull request; it reads serde's attributes; MIT; no npm package; its README adds it as an ordinary dependency, so the UI slice keeps it out of the shipped binary (a dev-dependency, the derive under `cfg_attr(test, ...)`) and shows the binary's dependency tree without it, or reports that it cannot; costs: types only, so a short hand-written module maps routes to them. **specta:** the same idea; costs: its 2.0 has been in release candidates since 2023-07-17. **utoipa and OpenAPI:** a full description of routes and types; costs: a second generator to turn that description into TypeScript, and an annotation on every route, worth it only if outside programs call the API, which none does. **Serving: the built UI embedded in the control plane's binary**, served from a fixed table of files: the UI and the backend cannot be out of step, no path from a request reaches the disk, and since every script is one of the embedded files the CSP's `script-src` needs no inline script and no outside origin; the embedding crate must embed in every build, tests included, and is chosen after AGENTS.md §2's inspection; costs: a UI change needs a new binary, so it reaches a node only in a release (D12). **Files in the image beside the binary:** the same rollback (D12); costs: a directory served from disk, and a binary and a UI that a fault could pair wrongly. **No Python on the node or in the UI's build:** nothing in this plan, the assistant plan or the ADRs needs it (the engine is llama.cpp's server, ADR 0008; the action templates are stage 7's Rust; the repository's quality tools are Python and stay so); a need for it later is its own decision. | **Decided** (owner, 2026-10-25, "Svelte is fine with plain Vite. Keep Lightweight Charts as is. Ok with Server-sent events with those 4 rules." and "Embedding: whichever is more secure or reliable."; ts-rs on this plan's recommendation, "Yes. [...] ts-rs for the types [...] no Python"; `docs/build-records/2026-10-25-d23-frontend-stack.md`). Every package still gets AGENTS.md §2's inspection when the UI slice adds it |

Later, with their stage: how LND's wallet is unlocked after a reboot (a
password stored on the node, or the owner unlocking it in the app — gap G9;
stage 4, where the wallet is created), whether settings changes reach a node
only through releases (D12 decides it for versions; AGENTS.md's proposed rule
for settings is decided at stage 6, which ships updates — stages 1 and 2
already write settings), and whether the two nodes exchange anything (gap
G10; when a second node joins, D1).

## 8. Stages

Each stage is a set of changes with build records; a stage closes when its
drill has been seen to pass.

| Stage | Delivers | Its drill | Its security slice ([threat model §5](../security/THREAT_MODEL.md#5-the-security-slice-of-every-stage)) |
|---|---|---|---|
| 1 Platform | The bootc image (x86_64; aarch64 too if D1 keeps the Pi), signed, built in CI; install media; first-boot setup without a command line — the first UI slice: a setup page served by the control plane, reached as `rikurisetup.local`, that secures the connection (D10), names the node (`rikuri01.local` by default, numbered after the Rikuri nodes it finds on the network, or the owner's choice; the node's IP shown as the way in where `.local` does not resolve, as on many Android browsers), takes the owner's sign-in (D11) and gives the node its UUID, then a SetupHub that lists what remains and marks done only what the node's real state shows; input beside explanation, back and next; the wizard's state kept by the control plane, so a refresh or a crash resumes; built as D15 says; greenboot checks; the boot-cause record, its rollback rule and UPS support (D22, §4.1) | The rollback drill (§4.1) on the N150, including an unclean stop, a power cut while an update is applied and while the new image first boots, and an update that fails to apply; a UPS going on battery and to low battery shuts the node down cleanly, with the cause recorded | Image signed and verified before staging; no secret in the image; SELinux enforcing; inbound closed except the node's ports; the setup page's TLS and sign-in; no shell login by default; the UPS service on loopback at most. Tests: a tampered image refused; a wrong sign-in refused and rate-limited; the UPS service unreachable from the LAN; a flapping or false UPS obeyed a bounded number of times |
| 2 Bitcoin Core | Verified build, container, health judge, sync progress, full/pruned settings per tier; the first Quadlet unit under ADR 0005 (static `rpcauth` credentials, limits in the unit, the internal network of D14) | Kill and restart during sync; disk full; power loss; a bitcoind restart with no dependant restarted | `rpcauth` per client, `rpcwhitelist`, RPC on the private network only; verified build; data owned by its range; limits in the unit; if D20's experiment runs, the image's contents checked for no shell or package manager. Tests: a whitelist refusal; the port unreachable from the LAN; the contents check |
| 3 Tor | Onion service for Bitcoin Core and LND; control-port authentication without a password file | Tor restart; onion reachability check | Control-port authentication without a password file; onion keys in Tor's range; no exit. Tests: unauthenticated control refused; keys unreadable from other containers |
| 4 LND | Container; wallet creation in the app; SCB export | §6 step 1 in CI | Seed shown once, never stored readable; one macaroon per client with the least caveats, in the secrets store; TLS; wallet data in LND's range. Tests: a read macaroon cannot pay; the wallet path unreadable from Tor and the engine |
| 5 Backup and restore | Encrypted SCB to a UUID-identified destination; restore through the UI | Restore on clean hardware, test network | SCB encrypted before it leaves; a UUID destination; the stale-backup alarm; no path restores `channel.db`; a cloud destination (D18) counts only after a restore from it passes. Tests: the restore drill; the alarm; a `channel.db` restore refused |
| 6 Updates | OS and component updates, the version rules of §4.2, migrations | A broken image; a broken component; an LND upgrade with a migration | Signature and digest verification; downgrade refused; migrations end rollback; the advisory release cadence (threat model §6). Tests: tampered and downgraded sets refused |
| 7 Backend API and channel management | The control plane; channels, fees, rebalancing, node search, analytics | §6 steps 2 and 3 | One authority; authentication fails closed; step-up and one approval store; no shell, a closed action enum; the redaction filter (ADR 0009); security health in the status API; runbooks as typed values whose units are checked against the image's Quadlet files and whose attempts are budgeted (D21). Tests: the register's EXEC and SEC tripwires; mutants on refusal paths; a replay test; each runbook against its induced fault |
| 8 Frontend, then the assistant | The full UI, grown from the setup slice of stage 1 and the wallet and restore screens of stages 4 and 5 (D15); the planning-only assistant in a sandbox (OpenShell, AISecurity policy), built to the [assistant plan](assistant-plan.md) (D16): llama.cpp's server image pinned by digest (ADR 0008), one model chosen by the N150 measurement, the action templates stage 7 exposes, the AI event store and page, the evaluation gate; the lobby zone's feeds and AI relay and the Diagnostics page (D18 and D19) | The sandbox boundary tests (gap G5); the evaluation gate green on the release's engine and model (assistant plan, contract C); one action template driven end to end on a test network, approved by step-up | Content security policy and session flags; the engine without egress; the sandbox boundary (G5); the emergency stop; metadata and LAN ranges refused in every fetch; injection probes in the eval gate. Tests: G5's list, the stop tests, a fetch-to-metadata test. The lobby zone (D18): helpers off the core network, one egress proxy, ingest by a route-scoped credential. Tests: no route from a helper to the core; a valid credential refused on another route; a forced-stale feed shown stale; an alert counted only when delivered |
| 9 Treasury and agent payments | The control plane as the treasury: owner-signed, revocable mandates for agents; the payment pipeline with reservations and the approval queue; invoices for sellers; the hash-chained ledger; reconciliation and the divergence alarm; the caps as settings ([agent payments and marketplace plan §5](agent-payments-and-marketplace-plan.md#5-stages-9-and-10)) | On a test network: a mandate pays within its allowance, waits above it, and is refused when revoked, forged, expired or replayed; a ledger-versus-LND disagreement suspends mandates and alerts; a reservation survives an update and rollback; the sandbox boundary test with an agent inside | The security layer of the agent payments plan §4.3; detectors' signals hold payments; the "who holds what" table enforced by deployment. Tests: that plan's drill |
| 10 Marketplace | A separable marketplace service, a client of the treasury: signed listings and reviews, reputation, discovery, auctions with hold-invoice collateral, selling through the treasury's invoices, help pages (same plan, §5) | Two nodes on a test network, one not a Rikuri node: publish, discover, buy, review; forged and replayed items refused; a wash-trading ring scored below the trusted tier; an auction settled; no path to LND but the treasury | No path to LND but the treasury; signed listings; untrusted text never ingested into the assistant's stores (AI-02). Tests: that plan's drill |

What carries over from the previous repository: behaviour and test cases,
not code — the 90 port candidates of the lessons register, each rewritten in
Rust and re-checked for Fedora, the container runtime and the
Pi where its verdict says so.

Stages 9 and 10 were added on 2026-10-17 from the
[agent payments and marketplace plan](agent-payments-and-marketplace-plan.md):
the node as the treasury for the owner's agents, then a marketplace it can
host, behind the security layer that plan describes. They start only after
stage 8's drill, and their owner decisions (E1 to E10 there) are open. The
previous repository's commerce code is harvested at module level in the
lessons register's §7, with gap G12 for what it never proved.

The assistant's shape was decided on 2026-10-18 in the
[assistant plan](assistant-plan.md) (D16; ADR 0008 for the engine): the
model has two jobs, classifying into typed intents and explaining from
retrieved text; everything else is deterministic Rust. Stage 7 exposes the
action templates it drives (that plan's contract A); stage 8 builds the
rest. The previous repository's AI code is evidence and specification
there, not a port.

## 9. Sources (read 2026-10-11)

- Fedora 45 schedule: [Final Freeze, October 20 release date](https://www.linuxcompatible.org/story/fedora-45-final-freeze-october-20-release-date-set-as-trackers-clear/); [Fedora 45 Beta](https://9to5linux.com/fedora-linux-45-beta-released-with-linux-7-2-gnome-51-and-kde-plasma-6-7).
- Fedora IoT bootc: [Fedora IoT bootc image example](https://docs.fedoraproject.org/az/iot/fedora-iot-bootc-quay-example/) (behind a bot check on 2026-10-11: not read); [roadmap to bootable containers](https://github.com/fedora-iot/iot-distro/issues/53); [bootc-image-builder](https://github.com/osbuild/bootc-image-builder) (its README: the sources now live in image-builder); [Fedora IoT 44 bootc image build failure](https://github.com/virt-s1/rhel-edge/issues/11175).
- greenboot: [first update from the Fedora IoT 44 stock image can never roll back](https://github.com/fedora-iot/greenboot-rs/issues/217).
- Raspberry Pi 5: [Fedora 44 on the Raspberry Pi 5](https://nullr0ute.com/2026/03/fedora-44-on-the-raspberry-pi-5/); [Raspberry Pi 5 images for Fedora 44](https://discussion.fedoraproject.org/t/raspberry-pi-5-images-for-fedora-44/183204); [how Pi 4 and Pi 5 boot a fedora-bootc disk](https://github.com/Open-Source-Space-Foundation/proves-ci-os/issues/36).
- Bitcoin Core: [31.1 released](https://bitcoincore.org/en/2026/07/08/release-31.1/); [releases](https://bitcoincore.org/en/releases/); [lifecycle](https://bitcoincore.org/en/lifecycle/); [32.0 in final testing](https://www.kucoin.com/blog/bitcoin-core-32-0-enters-final-testing-faster-validation-smarter-fees-and-security-fixes-ahead-of-october-10).
- LND: [releases](https://github.com/lightningnetwork/lnd/releases); [its gRPC protocol files at v0.21.4-beta](https://github.com/lightningnetwork/lnd/tree/v0.21.4-beta/lnrpc); [lndclient's go.mod](https://github.com/lightninglabs/lndclient/blob/master/go.mod) (it requires `github.com/lightningnetwork/lnd`); [lnd_grpc_rust](https://github.com/niteshbalusu11/lnd-grpc-rust) (its README: building from a chosen LND checkout).
- Rootless Podman (D5): [troubleshooting](https://github.com/containers/podman/blob/main/troubleshooting.md) (lingering, ports below 1024, CPU pinning, `userns=auto`'s ranges); [rootless tutorial](https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md) (ID ranges, `pasta`, storage, `--userns=keep-id`); [the userns option](https://github.com/containers/podman/blob/main/docs/source/markdown/options/userns.container.md) (`auto` in rootful and rootless mode; `keep-id` takes the whole range); [rootless limitations](https://github.com/containers/podman/blob/main/rootless.md) (`pasta` between containers, `rootlessport` and client addresses); Quadlet's page, under Podman below (user units cannot wait for system units); [systemd's user@.service](https://github.com/systemd/systemd/blob/main/units/user%40.service.in) (`Delegate=pids memory cpu`); [Fedora 45's systemd package](https://src.fedoraproject.org/rpms/systemd/blob/f45/f/systemd.spec) (version 262).
- The previous repository, read with `git -C … show` at 3bbbe392: `control-plane/Cargo.toml` (`lnd_grpc_rust`, `lightning`), `docs/plans/BLUEPRINT.md` and `docs/plans/UniversalAgenticPayment.md` (LDK; BLUEPRINT.md also says `lnd_grpc_rust` lacks an `offersrpc`, but LND itself has none).
- Tor: [0.4.8 support ends](https://www.securitylab.ru/news/574170.php); [Arti 2.7.0 released](https://blog.torproject.org/arti_2_7_0_released/).
- Podman: [podman-auto-update](https://docs.podman.io/en/v5.8.2/markdown/podman-auto-update.1.html); [Quadlet units, `Notify=healthy`](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html).
- NVIDIA OpenShell: [product page](https://www.nvidia.com/en-us/ai/openshell/); [developer guide](https://docs.nvidia.com/openshell/home).

Read 2026-10-17, for D10 to D15 and ADR 0005
(`docs/build-records/2026-10-17-plan-review.md`):

- bootc: [logically bound images](https://bootc.dev/bootc/bootc-logically-bound-images.7.html) (pulled with `bootc upgrade`; "the logically bound images corresponding to rollback deployments will also be retained"; "rootless containers from these system stores are not supported"; Anaconda does not support them; stored under `/usr/lib/bootc/storage`).
- Podman: [podman-pod-create](https://docs.podman.io/en/latest/markdown/podman-pod-create.1.html) (`--userns` "for all the containers in a pod"; pasta "preserves the original source IP address"; `rootlessport` "does not preserve client source IPs", its pasta setting experimental); [podman-systemd.unit](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) (`Notify=healthy`, `HealthOnFailure`, `StopTimeout`, `Pod=`, `AutoUpdate`, `[Unit]` and `[Service]` passed through; user units wait on `podman-user-wait-network-online.service`).
- Bitcoin Core: [JSON-RPC interface](https://github.com/bitcoin/bitcoin/blob/master/doc/JSON-RPC-interface.md) (the cookie "is the preferred RPC authentication method"; `rpcauth` from `share/rpcauth`; whitelists "should not be considered robust security boundaries"; RPC "does not use encryption").
- LND: [`sample-lnd.conf` at v0.21.4-beta](https://github.com/lightningnetwork/lnd/blob/v0.21.4-beta/sample-lnd.conf) (`bitcoind.rpccookie`, `bitcoind.rpcpolling`); the previous repository's `docs/build-records/2026-09-26-lnd-rpccookie.md` (LND does not re-read a rotated cookie).

Read 2026-10-20, for D18, D19 and the F3 amendment
(`docs/build-records/2026-10-20-lobby-zone-access-and-ai-lanes-adrs.md`):

- Tailscale: [Enabling HTTPS](https://tailscale.com/docs/how-to/set-up-https-certificates) (machine names and the tailnet DNS name are published in the Certificate Transparency ledger; only devices that run `tailscale cert` appear).
- Telegram: [End-to-End Encryption FAQ](https://tsf.telegram.org/manuals/e2ee-simple) (cloud chats are not end-to-end encrypted; secret chats are device-specific). That Bot API messages are cloud chats is still to be confirmed.
- LND: [recovery.md](https://github.com/lightningnetwork/lnd/blob/master/docs/recovery.md) (the static channel backup is encrypted with a key derived from the seed; restoring from it closes the channels).

Read 2026-10-20, for D20 and D21
(`docs/build-records/2026-10-20-adrs-nix-images-and-runbook-executor.md`):
the sources listed in ADR 0013 (nixpkgs `buildLayeredImage`, the nix-bitcoin
0.0.139 release, the Bitcoinix relaunch) and ADR 0014 (the lessons register's
HEAL and EXEC entries).

Read 2026-10-21, for D22 and §2's greenboot row
(`docs/build-records/2026-10-21-boot-cause-and-ups.md`):

- greenboot: [rollback trigger never runs at shutdown](https://github.com/fedora-iot/greenboot-rs/issues/218); [a healthy host rolled back when finalize-staged fails](https://github.com/fedora-iot/greenboot-rs/issues/219); [boot counter on md RAID1](https://github.com/fedora-iot/greenboot-rs/issues/220); [a fix proposed for #217, a pull request](https://github.com/fedora-iot/greenboot-rs/pull/221); [default health checks and bootc](https://github.com/fedora-iot/greenboot-rs/issues/212); [releases](https://github.com/fedora-iot/greenboot-rs/releases) (v0.16.4, 2026-08-18); [the rollback trigger unit at v0.16.4](https://github.com/fedora-iot/greenboot-rs/blob/v0.16.4/usr/lib/systemd/system/greenboot-set-rollback-trigger.service); [ostree's finalize-staged unit](https://github.com/ostreedev/ostree/blob/main/src/boot/ostree-finalize-staged.service) (`Conflicts=final.target`).

Read 2026-10-25, for D23
(`docs/build-records/2026-10-25-d23-frontend-stack.md`):

- ts-rs: [README](https://github.com/Aleph-Alpha/ts-rs) (`#[ts(export)]` "generates a test which writes the bindings"; `serde-compat` "enabled by default"; MIT; its Get started adds it under `[dependencies]`); [crates.io](https://crates.io/crates/ts-rs) (12.0.1, 2026-01-31).
- specta: [crates.io](https://crates.io/crates/specta) (newest stable 1.0.5, 2023-07-17; 2.0.0-rc.1 the same day; rc.27 on 2026-10-21).
- Lightweight Charts: [README, License](https://github.com/tradingview/lightweight-charts) (Apache-2.0; "requires specifying TradingView as the product creator"; the NOTICE file's attribution notice and a link to TradingView; the `attributionLogo` option meets the link requirement).
- Svelte: [Getting started](https://svelte.dev/docs/svelte/getting-started) (Svelte "directly with Vite via vite-plugin-svelte"; a routing library likely needed).
- Server-sent events: [MDN, EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) (without HTTP/2, six connections "per browser + domain", "across all of the tabs"; the constructor's one option is credentials mode); [WHATWG HTML](https://html.spec.whatwg.org/multipage/server-sent-events.html) (`Last-Event-ID` on reconnection).
