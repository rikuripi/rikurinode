# ADR 0011 — Remote and expert access: a diagnostics page for everyone, key-only SSH for experts, no terminal in the web UI

| | |
|---|---|
| **Status** | Proposed — drafted 2026-10-20 from the owner's direction in chat ("Ok, so we'll stay rootful, and make all the adjustments you just listed with report-card schema and F3 changes to the Rikuri Node Plan."); Accepted when the owner confirms this wording in its Build Record. Its default window was confirmed by the owner on 2026-10-20 ("1. SSH window OK with 1 hour default, 24 hours at most. Manual approval for each external AI send until finish of shadow period, OK."); the ADR as a whole stays Proposed |
| **Decision** | D19, to be added to `docs/architecture/platform-plan.md` §7 |
| **Supersedes** | Nothing. It settles the "later choice" that D11 and `docs/security/THREAT_MODEL.md` §8 ("Shell access") left open |
| **Beside it** | ADR 0007 (the root helper's fixed list, rootful Podman), ADR 0009 (the threat model), ADR 0010 (the lobby zone) |

## Context

D11 decided web sign-in only: `root` locked, no SSH, SSH "enabled later under
technical settings with a key". The threat model's §8 says no SSH or console
login by default, and leaves open whether the owner may enable SSH behind the
app's step-up. The owner, 2026-10-20: "I use Tailscale, Telegram, Discord,
cloud backup options (not used yet), tor and ssh (like Umbrel). There is a
Terminal access with limited command (not sure if an expert would want full
access to Terminal: is it safe?)"

The previous node answers the question twice. Its Terminal page was removed
on 2026-08-23: it showed a password-and-2FA lock that unlocked itself while
its backend had been deleted (EXEC-04). A shell injection from the LAN was
root-equivalent because the dashboard's user was in the container runtime's
group (EXEC-08). And after eight verifier rounds the command guard still
listed forms it cannot see, so it calls itself a tripwire and not a sandbox
(AI-02). A filter over command text is not a security boundary.

## Decision

- **No terminal in the web UI,** filtered or not. A browser session that can
  run commands is a root-equivalent path behind one web sign-in.
- **A Diagnostics page for everyone.** A closed menu of typed, read-only
  actions run by the control plane, each with an output schema and a size cap:
  unit status; the recent journal of one named node unit, with secrets
  redacted at write time (SEC-01); bitcoind and LND state through the
  read-only credentials; Tor circuit status; disk, memory and temperature; the
  release set and its bound images; the latest audit events. It is a menu and
  not a shell, and it is the first thing the assistant's explanations point to.
- **Expert shell: SSH, key-only, off by default.** The owner switches it on
  in the app behind step-up, for a window that ends on its own. Defaults,
  confirmed by the owner on 2026-10-20 and both settings the owner can
  change: one hour, at most 24 hours. No
  password login, ever (D11: a web form never sets a Linux credential).
- **Only over a remote path, only while the window is open.** The SSH port
  is reachable through Tailscale or a Tor onion service, never from the open
  LAN. The host firewall opens it on those interfaces for the window and
  closes it after. How each path reaches the host is decided in the Build
  Record of the stage that builds it.
- **The account is unprivileged with real OS limits.** A dedicated account
  with no sudo, in no group that reaches the container runtime, the
  secrets store or the journal as a whole, and unable to reach the root
  helper, which answers only the control plane's user (ADR 0007). SELinux
  confines it where the policy allows (to be verified in the Build Record).
  Safety comes from the operating system, not from filtering commands
  (AI-02).
- **Every session is visible.** Start and end are audit events and owner
  alerts. The status page shows "modified by owner" when the system has
  drifted from the booted image; how drift is detected is decided in the
  Build Record, and the detection is best-effort. Self-healing and the tested
  rollback are weaker on a modified node, and the page says so.
- **Remote web UI paths are optional and off by default:** a Tor onion
  service with client authorization, and Tailscale. Each adds its name to
  `RIKURI_NAMES`. A network identity never replaces sign-in and step-up
  (EXEC-07). Tailscale's HTTPS certificates publish machine names in a public
  certificate ledger, so they stay off; D10's per-node certificate authority
  remains the way the setup page is trusted.
- **No agent uses the expert shell.** The assistant never receives SSH
  access, keys or a terminal.

## Consequences

- Experts lose a web terminal and get a real shell with real limits. Some
  will want more; the answer is a break-glass procedure the owner writes, not
  a wider default.
- A key to manage and a window that expires add friction for the owner.
- Which remote path ships first (Tor, Tailscale or both) is left open; each
  is its own change with its own drill.
- Edits that follow, each its own change: a D19 row in the platform plan §7;
  threat model §8 (the "Shell access" bullet, decided once this ADR is accepted) and a row for a
  remote path as an attack surface.

## Rejected

- A web terminal with a command allowlist: the lessons above.
- A full web terminal behind a password and 2FA: one web session becomes a
  root-equivalent path, and EXEC-04 records a lock that was not enforced.
- SSH always on, from the LAN: a funds device with a standing shell for every
  compromised device on the network.
- Password SSH: D11.

## Sources (read 2026-10-20)

- `docs/requirements/lessons-register.md`: EXEC-04, EXEC-07, EXEC-08,
  AI-02, SEC-01.
- `docs/architecture/platform-plan.md` §7 D10 and D11;
  `docs/security/THREAT_MODEL.md` §8.
- [Tailscale, "Enabling HTTPS"](https://tailscale.com/docs/how-to/set-up-https-certificates):
  machine names and the tailnet DNS name are published in the Certificate
  Transparency ledger.
