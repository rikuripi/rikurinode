# ADR 0001 — The node's containers run under Podman with Quadlet

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-11 |
| **Decision** | D2 of `docs/architecture/platform-plan.md` |
| **Beside it** | D5, decided 2026-10-12: rootless, an ID range per container (ADR 0003) |

## Context

Fedora IoT ships Podman. The owner's earlier idea for Fedora CoreOS was
Docker first and Podman later.

## Decision

Bitcoin Core, LND and Tor run as Podman containers that systemd starts,
stops and watches through Quadlet units, from the first build.

## Consequences

- Each container is a systemd service: limits, restarts and ordering are
  systemd's; with `Notify=healthy`, a unit is ready only when its health
  check passes.
- Podman's auto-update can roll a container back to its previous image when
  the restarted unit fails; this project still drills rollback rather than
  assuming it.
- The previous node's Docker scripts and know-how do not carry over as they
  are; its lessons do (the lessons register).

## Rejected

Docker first, Podman later: Docker would be added to the image, and moving
to Podman later would be the same work done twice.
