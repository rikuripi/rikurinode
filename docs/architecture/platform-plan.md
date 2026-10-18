# Platform and architecture plan

**Status: proposed, 2026-10-11; D5 to D9 decided 2026-10-12.** Of its nine
owner decisions (§7), seven are taken — D2, Podman with Quadlet; D3, Rust; D5,
rootless with an ID range per container; D6 and D7, the OS image public on
GitHub's registry and signed by a key in CI with an offline spare; D8, CI
minutes; D9, Fedora's DNS boot check off (ADRs 0001 to 0004) — and two are
open (D1, the Pi 5; D4, the first mainnet amount); nothing that depends on an
open one is built. Facts about outside software were checked on
2026-10-11 and carry their source (§9); re-check them before acting on them.

## In one page

- **Two nodes.** An Intel N150 mini PC (x86_64, 12 GB RAM, 2 TB disk) runs a
  full node. A Raspberry Pi 5 (8 GB) is meant to run a pruned node.
- **The operating system is an image.** Each node runs Fedora IoT, delivered
  as a bootable container image (bootc) that this project builds, signs and
  tests. An update replaces the whole system image; if the new image fails
  its health checks, the node goes back to the previous image by itself.
- **The node software runs in containers.** Bitcoin Core, LND and Tor run in
  containers that systemd starts, stops and watches — Podman with Quadlet
  units (decision D2), rootless, each container in its own ID range
  (decision D5) — each pinned
  to an exact, verified build.
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
| Fedora 45 | Final release targeted for 2026-10-20 (fallbacks 10-27, 11-03). | Build on Fedora 45 once released. Fedora releases are short-lived, so the image moves to each new release after a soak, by owner approval. |
| Fedora IoT bootc | Fedora IoT can be built and updated as a bootable container image; base images are published on registry.fedoraproject.org and quay.io. | The node's OS is a Containerfile in this repository, built in CI. |
| Image tooling | `bootc-image-builder`'s sources moved into `image-builder` (its migration notice, 2026-06-18); a Fedora IoT 44 bootc image build failed at its bootloader step in January 2026 (rawhide composes). | Pin the build tools by digest; build install media in CI; an install test on real hardware for every Fedora release. |
| greenboot | An open bug report (2026-10-09; one user's, no maintainer reply yet): on a device installed from the stock Fedora IoT 44 image, the first update that fails its health checks never rolls back — greenboot 0.16.2 arms the rollback with a variable that 0.16.4 no longer reads. | Never trust rollback until it is drilled on the device: the install procedure ends with a deliberately broken update that must roll back by itself (§4.1). |
| Raspberry Pi 5 | Peter Robinson published Fedora 44 images for the Pi 5 in March 2026 (Minimal, Workstation, KDE), on his blog, for testing. With them: boot from microSD only, no USB or NVMe boot; no thermal (fan) control, audio or NVMe; no IoT or bootc image. An investigation closed 2026-10-10 found no published `fedora-bootc` image booting on a Pi; `bootupd` does not manage the Pi's firmware or U-Boot. | §3.2: owner decision D1; re-check at Fedora 45. |
| Bitcoin Core | 31.1 (2026-07-08) is the newest final release; 32.0 is in release-candidate testing (target date 2026-10-10, not yet on the release page on 10-11). The project maintains the newest three major versions. | Start on 31.x; move to 32.x after its first point release and our own soak. |
| LND | v0.21.4-beta (2026-10-01) is the newest; v0.20.5-beta was released the same day. | Start on 0.21.x; every RPC the backend uses is tested against the pinned version, and the backend refuses an LND version it was not tested with. |
| Tor | Relays and clients of 0.4.8 and older lost support on 2026-09-01, so 0.4.9 is the supported series. Arti, the Rust Tor, released 2.7.0 on 2026-10-01. | Use C Tor 0.4.9.x, which LND drives through Tor's control port; whether Arti can serve LND is checked before any switch. |
| Podman | Podman's auto-update can roll a container back to its previous image when the restarted unit fails; a Quadlet unit with `Notify=healthy` is ready only once its health check passes. Fedora 45 ships Podman 6. | Container updates get the same "prove it or go back" rule as the OS whatever the runtime (§4.2); with Podman, its auto-update provides it. |
| NVIDIA OpenShell | Open source (Apache 2.0): runs each agent in its own sandbox without privileges, limits its files and network, filters its system calls, and brokers its requests to a supervisor. | The candidate boundary for the assistant (stage 8), alongside the AISecurity policy. |

Re-checked for stage 1 on 2026-10-12, with sources:
`docs/build-records/evidence/2026-10-12-stage1-os-image/research.md`. Changes
since: the greenboot report is still open with no reply, and a hang before
userspace is never counted toward a rollback; Fedora 45 had 8 accepted
blockers; the base image is pinned on registry.fedoraproject.org, because
quay.io drops old digests within a day; keyless image signatures cannot be
enforced on the node yet (D7).

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
| **A. Wait (recommended)** | Build and prove everything on the N150. Re-check the Pi 5 at each Fedora release (45 on 2026-10-20, 46 in spring 2027) against the checklist below; the image is built for aarch64 in CI too, so it is ready when the hardware is. | No pruned node until Fedora supports the Pi 5; no extra work now. |
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
  required check fails three boots in a row, the node boots the previous
  image and says so on its status page and in an alert.
- `/etc` keeps the owner's changes (merged on update) and `/var` keeps all
  data: neither is rolled back.
- **The rollback drill** ends every installation and runs again after each
  Fedora release change: a deliberately broken update is staged and must roll
  back by itself, with the node's data intact and the event reported. It is
  how the greenboot report of §2 would be caught.

### 4.2 Layer 2 — the node software

- Each component is a container image built by this project from the
  upstream release binaries after verifying their signatures and checksums
  (Bitcoin Core's signed checksums, LND's signed manifest), pinned by
  digest. No third-party prebuilt images. The runtime is Podman (D2).
- One bring-up path: systemd starts the units in dependency order (OWN-01).
- **A component's version is machine state** (the open design rule in
  AGENTS.md): the image ships a minimum version; an owner-approved upgrade in
  the app raises it and records it in `/var`; an image update never lowers a
  version the node already runs — the newer wins (the owner's choice for the
  previous repository, 2026-10-10).
- A component update is proven or undone: the new container must pass its
  health check, or the previous image is restored.
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
| Container runtime | Podman with Quadlet, Fedora 45's (D2) | both |
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
| D5 | Rootless or rootful containers | **Rootless, one user** (Podman's default) — Podman and the containers run as an unprivileged user, so an escape gets that user, not root; but by default each container's root is that same user, which owns every container's data: an escape from the Tor container reaches LND's wallet files and Bitcoin Core's data. **Rootless, a range per container** (`userns=auto` from the user's subordinate IDs) — an escape gets an unprivileged ID that owns no other container's data; costs: the user's range must be large enough to divide, and an unsized `--userns=keep-id` cannot sit beside it. Costs of both rootless options: the services are user services, kept running after logout by systemd's lingering, and cannot wait for system units (Quadlet's example: `network-online.target`); container storage lives in the user's home unless moved; networking goes through `pasta` — containers reach each other only with extra configuration, and on rootless bridge networks port forwarding uses `rootlessport` by default, which loses the client's address; ports below 1024 need a kernel setting (the node's own ports — 8333, 9735, 10009, 9050 — are above it, a web page on 80 or 443 is not); memory, CPU and process limits work through the delegation systemd gives every user service (since systemd 252; Fedora 45 ships 262), which PLAT-04's budgets need, while I/O limits and CPU pinning need one more setting. **Rootful, a range per container** (`userns=auto` from the `containers` ranges) — the same separation between containers; cost: Podman itself runs as root, so a runtime bug reaches the whole host; benefit: ordinary system services, ordered like any other. In both range options the runtime's own account can reach every container's data — rootless Podman's user can read, change or remove anything its subordinate IDs own (`podman unshare`) — so a bug in Podman, or anything that drives it, reaches LND's wallet either way; the control plane's access to the runtime must stay narrow in every option (EXEC-08: no unrestricted container-runtime access, no root socket, control through a narrow, audited interface). **All three** need ID ranges in `/etc/subuid` and `/etc/subgid` and data volumes owned to match the IDs each container runs as. (The rootless tutorial's answer for a non-root image user, `--userns=keep-id`, runs that container as the shared user, so it gives up the separation the range options are for.) The lessons register lists rootless runtime access for the backend (EXEC-08) as a thing to re-check. | Rootless with a range per container: the same separation between containers as rootful, and a runtime bug stops at an unprivileged account (which still reaches every container's data) instead of the host — paid for with the user-service costs above. The owner's message of 2026-10-11 assumed rootless ("systemd and rootless Podman"), before these options were set out. **Decided: rootless, a range per container** (owner, 2026-10-12; ADR 0003) |
| D6 | Where the OS image is published | **A public package on GitHub's registry** — nodes update with no credentials; anyone can download the image, which holds no secret by rule; making it public cannot be undone. **A private package** — a token stored on every node: one stolen node leaks an account-wide token, and an expired one stops updates silently. **quay.io, public** — the same as the first, a second account to manage. | **Decided: public on GitHub's registry** (owner, 2026-10-12; ADR 0004) |
| D7 | Who holds the image signing key | **A key in CI, usable only by `main`'s publish job, plus a spare kept offline** by the owner, its public half in every image — costs: a repository admin could misuse the CI key. **An offline key the owner uses for each release** — CI can never sign; costs: the owner at a command line for every release. Keyless signing is not an option yet: the node cannot enforce it (stage 1 research). | **Decided: CI key, `main` only, with an offline spare** (owner, 2026-10-12; ADR 0004) |
| D8 | CI minutes for the OS image | **Private repository**: 2,000 free minutes a month on 2-CPU runners; the image builds on pull requests that touch it, and the VM rollback drill (an estimated 40–70 minutes) runs on image changes and once a week. **A public repository**: larger runners and unlimited minutes; costs: every build record, with details of the owner's machine and live node, becomes public. | **Decided: private; drill on image changes and weekly** (owner, 2026-10-12) |
| D9 | Fedora IoT's DNS boot check | **Off**: an internet or ISP outage at an update's reboot must not roll a good update back; the node's own required checks (§4.1) replace it. **Kept**: fewer changes to Fedora's setup; costs: a network outage at reboot rolls the node back. | **Decided: off** (owner, 2026-10-12; `image/rootfs/etc/greenboot/greenboot.conf`) |

Later, with their stage: how LND's wallet is unlocked after a reboot (a
password stored on the node, or the owner unlocking it in the app — gap G9;
stage 4, where the wallet is created), whether settings changes reach a node
only through tested updates (AGENTS.md's proposed rule; stage 6, which ships
updates — though stages 1 and 2 already write settings; §4.2 covers versions
only), and whether the two nodes exchange anything (gap G10; when a second
node joins, D1).

## 8. Stages

Each stage is a set of changes with build records; a stage closes when its
drill has been seen to pass.

| Stage | Delivers | Its drill |
|---|---|---|
| 1 Platform | The bootc image (x86_64; aarch64 too if D1 keeps the Pi), signed, built in CI; install media; first-boot setup without a command line; greenboot checks | The rollback drill (§4.1) on the N150 |
| 2 Bitcoin Core | Verified build, container, health judge, sync progress, full/pruned settings per tier | Kill and restart during sync; disk full; power loss |
| 3 Tor | Onion service for Bitcoin Core and LND; control-port authentication without a password file | Tor restart; onion reachability check |
| 4 LND | Container; wallet creation in the app; SCB export | §6 step 1 in CI |
| 5 Backup and restore | Encrypted SCB to a UUID-identified destination; restore through the UI | Restore on clean hardware, test network |
| 6 Updates | OS and component updates, the version rules of §4.2, migrations | A broken image; a broken component; an LND upgrade with a migration |
| 7 Backend API and channel management | The control plane; channels, fees, rebalancing, node search, analytics | §6 steps 2 and 3 |
| 8 Frontend, then the assistant | The UI; the planning-only assistant in a sandbox (OpenShell, AISecurity policy) | The sandbox boundary tests (gap G5) |
| 9 Treasury and agent payments | The control plane as the treasury: owner-signed, revocable mandates for agents; the payment pipeline with reservations and the approval queue; invoices for sellers; the hash-chained ledger; reconciliation and the divergence alarm; the caps as settings ([agent payments and marketplace plan §5](agent-payments-and-marketplace-plan.md#5-stages-9-and-10)) | On a test network: a mandate pays within its allowance, waits above it, and is refused when revoked, forged, expired or replayed; a ledger-versus-LND disagreement suspends mandates and alerts; a reservation survives an update and rollback; the sandbox boundary test with an agent inside |
| 10 Marketplace | A separable marketplace service, a client of the treasury: signed listings and reviews, reputation, discovery, auctions with hold-invoice collateral, selling through the treasury's invoices, help pages (same plan, §5) | Two nodes on a test network, one not a Rikuri node: publish, discover, buy, review; forged and replayed items refused; a wash-trading ring scored below the trusted tier; an auction settled; no path to LND but the treasury |

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
