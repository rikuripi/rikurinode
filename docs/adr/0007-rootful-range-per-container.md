# ADR 0007 — Rootful Podman, each container in its own user-ID range

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-17 ("D13 Package R as you recommended"; record `docs/build-records/2026-10-17-plan-review.md`); clarified, not changed, 2026-10-21 (owner, "Yes, please record."; the section "Clarification (2026-10-21)" below; record `docs/build-records/2026-10-21-adr-0007-clarification-rootless-and-pods.md`) |
| **Decision** | D13 and D14 of `docs/architecture/platform-plan.md` |
| **Supersedes** | ADR 0003 (rootless, a range per container; 2026-10-12), kept as written with a dated note |
| **Beside it** | ADR 0001 (Podman with Quadlet), ADR 0005 (supervision), ADR 0006 (release sets bound to the image) |

## Context

ADR 0003 chose rootless Podman so that a runtime bug would stop at an
unprivileged account. Two facts read on 2026-10-17 changed the balance:
bootc's logically bound images, the mechanism behind "one update, one
rollback" (ADR 0006), are not available to rootless containers; and a pod's
user namespace is set for all its containers, so the owner's pick of one pod
would have given bitcoind, Tor and LND one shared ID range instead of ADR
0003's range per container. Rootless also brought lingering, units that
cannot wait for system units, a userspace port forwarder that loses inbound
peers' addresses, container storage in a home folder, a kernel setting for
port 443 and no way to lower a service's OOM score (ADR 0003's own list).

## Decision

- **Podman runs as root, and every container gets its own user-ID range**
  (`UserNS=auto`, from the `containers` ranges in `/etc/subuid` and
  `/etc/subgid`). A break-out of one container lands in an unprivileged ID
  that owns no other container's data: an escape from Tor does not reach
  LND's wallet files.
- **System Quadlet units,** shipped in the image and overridden by drop-ins
  in `/etc`, ordered after the data disk and `network-online.target` like
  any system service. greenboot's checks can read them directly and still
  ask the control plane for the judgement (plan §4.1).
- **One private bridge network with a fixed address per container** (D14).
  RPC, REST and ZMQ bind to those addresses only; Tor's address never
  changes, so the previous node's stale-proxy restarts cannot recur. The
  published ports (8333, 9735, the web page's 443) are forwarded by the
  kernel's address translation, not a userspace proxy, so peers' addresses
  are kept; the stage 2 drill confirms it.
- **The control plane is a system service under its own unprivileged user,**
  hardened by systemd. It manages the node's units through systemd, with a
  policy rule limited to the node's units (to verify in B0.2: the rule can
  be scoped by unit name; otherwise the helper below does it). The
  privileged actions go through **one root helper service with a fixed
  list:** `bootc upgrade` and `bootc rollback`, the hostname, the backup
  drive's mount and unmount, reboot and shutdown. Each argument is
  validated, every call logged (EXEC-08). The control plane never holds
  Podman's API socket.
- Container storage and data volumes live under `/var`, each volume owned
  to match its container's range. How that match is kept when `UserNS=auto`
  picks the range is ADR 0003's open question, carried over to stage 2 and
  held by a test before any data is written (Podman's `U` volume option is
  the candidate).

## Consequences

- Given up: a Podman bug in its own setup code, which runs as root, could
  reach the host. Kept against it: Podman pinned by the image, the container
  processes run as unprivileged mapped IDs, SELinux stays enforcing, and no
  component gets the runtime's socket.
- Gone with rootless: lingering, the user bus, the wait on
  `podman-user-wait-network-online.service`, storage in a home folder, the
  port-443 kernel setting, `rootlessport`.
- Available again: `OOMScoreAdjust=` and `MemoryLow=` for bitcoind and LND
  (ADR 0005).
- The control plane's identity question of the review (a user service
  beside the containers, or root) is answered: a system service as its own
  user, with the root helper's fixed list as the only privilege.
- The lessons register's EXEC-08 ("re-check rootless runtime access for the
  backend") is answered by the helper's fixed list and the absence of a
  socket, not by rootless.

## Rejected

- Package U, rootless as decided: the control plane would implement release
  sets itself, on the rollback path where the previous node failed; a pod
  on pasta shares one range, a bridge network loses peers' addresses; boot
  ordering through lingering.
- Rootful, one user: a container's root is the host's root.
- Rootless, one user: every container's root is the same user, which owns
  every container's data.

## Clarification (2026-10-21): rootless versus rootful for this node, and pods

The owner asked (2026-10-21): "Regarding Podman. I guess it runs without
daemon and can run rootless for security. Our plan call for running
containers rootful. I need to know the difference and whether it's safer to
run rootless given the nature of bitcoin node and its disparate services.
And what is Podman Pod, does it have any relevance on the node?" The answer
was given in chat and is recorded here on the owner's word ("Yes, please
record."; `docs/build-records/2026-10-21-adr-0007-clarification-rootless-and-pods.md`).
It changes nothing above; it keeps the reasoning with the decision.

**Daemonless either way.** Podman has no daemon in either mode, so "no
daemon" is not what rootless buys. The previous node's weak point was
Docker's root socket, and this decision refuses a runtime socket in either
mode (EXEC-08): the control plane drives the node through systemd and the
root helper's fixed list, never through Podman's API.

**What rootless buys, and what it does not.** Rootless runs Podman itself
as an ordinary account. A bug in Podman, or in the runtime it calls, lands
an attacker as that account, not as root. The catch is what the account
owns: every container's files, LND's wallet included, belong to its
subordinate IDs, and it reaches all of them with one command (`podman
unshare`, ADR 0003's own consequence). So an escape through a runtime bug
reaches the wallet in both modes. Rootless also pays the costs listed in
Context: lingering, units that cannot wait for system units, a userspace
port forwarder that loses inbound peers' addresses, and no bound images.

**What rootful with a range per container gives.** Podman's setup code
runs as root for a moment; then each container runs in its own disjoint ID
range (`UserNS=auto`). Root inside the Tor container is an unprivileged
host ID that owns Tor's volume and nothing else, and a break-out lands in
that ID. A bug in Podman's or the runtime's setup path reaches the host as
root: the one place rootful is worse, as Consequences says.

**For this node's disparate services,** the separation that matters is
between containers. Tor, bitcoind's peer-to-peer side and the lobby zone's
helpers (ADR 0010) parse hostile input and must never reach LND's data. A
range per container gives that in both modes; rootful gives it with system
units, and keeps inbound peers' real addresses, which bitcoind's bans and
peer selection act on.

Residual risk, both ways:

| Event | Rootless, a range per container (ADR 0003) | Rootful, a range per container (this ADR) |
|---|---|---|
| A bug in Podman's or the runtime's setup path | The Podman account, which owns every container's data: the wallet is reachable, the host is not | Root: the wallet and the host. The signed immutable image and the one-shot rollback bound what an attacker can keep |
| A kernel exploit from inside a container | An unprivileged mapped ID, under SELinux enforcing | The same |
| What holds the line in both | Podman and the runtime patched on the release cadence (threat model §6); SELinux enforcing; volumes owned per range; the lobby zone off the core network; no runtime socket | The same |

**Why the decision stands.** For funds, the two modes end in the same
place. What decides is ADR 0006: a release is one tested set bound to the
OS image, with the previous set kept for a boot-time rollback that needs no
network, and bootc's bound images are rootful-only (Sources, 2026-10-17).
The previous node failed through inconsistent recovery (D12's record of
the owner's words), not through a container escape, so the plan spends its
risk on a provable rollback. Reopening this needs bound images available
rootless and a rootless bridge that keeps inbound peers' addresses, and
then a dated ADR.

**Pods.** A pod is Podman's unit of several containers that share kernel
namespaces, coordinated by a small infra container. By default they share
the network, IPC and UTS namespaces: one address, localhost between them,
ports published only by the pod, one `/etc/hosts` and `/etc/resolv.conf`.
PID and cgroup sharing are optional. The user namespace is set for all the
containers in a pod, so a pod has one ID range. D14 weighed one pod for
bitcoind, Tor and LND against a private bridge network with fixed
addresses, and chose the network, for three reasons:

- One pod is one ID range: Tor's root would map to the same host IDs as
  LND's, undoing the separation above.
- One network namespace puts nothing between the services' ports: Tor's
  control port, bitcoind's RPC and LND's gRPC would reach each other with
  no firewall in between.
- One pod is one unit to stop and start, where the stage 2 drill wants a
  bitcoind restart with no dependant restarted.

A pod's one benefit, RPC and ZMQ that never leave localhost, is matched by
binding each service to its fixed private address and allowing only the
pairs that need each other. So no pod exists on the node: each service is a
Quadlet container unit on D14's Quadlet network, and Quadlet's `Pod=` key
(ADR 0005's sources) stays unused. A pod would earn its place only for a
sidecar that must share a container's localhost; the design has none, and
D20's exec-form health probe needs no sidecar.

Sources (read 2026-10-21):

- [podman-pod-create](https://github.com/containers/podman/blob/main/docs/source/markdown/podman-pod-create.1.md.in):
  "unit of multiple containers"; `--share` "Defaults match Kubernetes
  default (ipc, net, uts)", choices "cgroup, ipc, net, pid, uts"; `--infra`
  "a lightweight container used to coordinate the shared kernel namespace
  of a pod. Default: true"; `--publish` "You must not publish ports of
  containers in the pod individually, but only by the pod itself";
  `/etc/hosts` and `/etc/resolv.conf` "shared between all containers in the
  pod". For `--userns` "for all the containers in a pod", pasta and
  `rootlessport`, the sources of 2026-10-17 below.
- ADR 0003 and the plan's D5 row (sources of 2026-10-11) for `podman
  unshare` and the rootless costs; ADR 0006 and the bootc source below for
  bound images being rootful-only.

## Sources (read 2026-10-17)

- [bootc, logically bound images](https://bootc.dev/bootc/bootc-logically-bound-images.7.html):
  "Rootless containers from these system stores are not supported".
- [podman-pod-create](https://docs.podman.io/en/latest/markdown/podman-pod-create.1.html):
  `--userns` "Set the user namespace mode for all the containers in a pod";
  pasta "Port forwarding preserves the original source IP address";
  `rootlessport` "is a userspace proxy that does not preserve client source
  IPs".
- [podman-systemd.unit](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html):
  `UserNS=`, `IP=`, user units and `network-online.target`.
- ADR 0003 and the plan's D5 row, with their sources of 2026-10-11, for the
  rootless costs.
