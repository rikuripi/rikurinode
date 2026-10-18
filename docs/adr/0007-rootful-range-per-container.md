# ADR 0007 — Rootful Podman, each container in its own user-ID range

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-17 ("D13 Package R as you recommended"; record `docs/build-records/2026-10-17-plan-review.md`) |
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
