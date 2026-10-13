# ADR 0003 — Rootless containers, each in its own ID range

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-12 (the plan's recommendation) |
| **Decision** | D5 of `docs/architecture/platform-plan.md` |
| **Beside it** | ADR 0001: Podman with Quadlet |

## Context

Bitcoin Core, LND and Tor run as Podman containers (ADR 0001). Podman can
run them as root or as an unprivileged user, and can give every container
the same user or its own range of user IDs. The plan's §7 sets out three
options and their costs.

## Decision

Podman runs rootless, as an unprivileged user, and each container gets its
own range of user IDs from that user's subordinate IDs (`userns=auto`).

## Consequences

- A break-out of one container gets an unprivileged ID that owns no other
  container's data: an escape from Tor does not reach LND's wallet files.
- A bug in Podman stops at the unprivileged account, not the host. That
  account can still reach every container's data (`podman unshare`), so the
  control plane's access to Podman stays narrow (lessons register EXEC-08).
- The containers are user services: kept running after logout by systemd's
  lingering, and they cannot wait on system units (the plan's example,
  `network-online.target`, has a Quadlet workaround).
- Container storage lives in the user's home unless moved. Networking goes
  through `pasta`: containers reach each other only with extra
  configuration, and on rootless bridge networks port forwarding uses
  `rootlessport` by default, which loses the client's address.
- Ports below 1024 need a kernel setting: the node's own ports (8333, 9735,
  10009, 9050) are above it, a web page on 80 or 443 is not.
- Memory, CPU and process limits work through systemd's delegation to user
  services (PLAT-04's budgets need them); I/O limits and CPU pinning need
  one more setting.
- The user's subordinate ID range must be large enough to divide, and an
  unsized `--userns=keep-id` cannot sit beside it.
- Open, for the first container (stage 2): how each data volume's owner
  stays matched to its container's IDs when `userns=auto` picks the range.
  Found by the plan's verifier (round 9) as a question for the owner; put
  to the owner with its options and costs at stage 2, and held by a test
  before any data is written.

## Rejected

- Rootless, one user (Podman's default): every container's root is the same
  user, which owns every container's data.
- Rootful, a range per container: the same separation between containers,
  but Podman runs as root, so a runtime bug reaches the whole host.
- Rootful, one user: a container's root is the host's root.
