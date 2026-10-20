# ADR 0010 — The lobby zone: helpers that talk to outsiders, behind one egress proxy and a narrow ingest

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-20 ("accept all five."; record `docs/build-records/2026-10-20-accept-adrs-0010-0014.md`); drafted the same day from the owner's direction in chat ("Ok, so we'll stay rootful, and make all the adjustments you just listed with report-card schema and F3 changes to the Rikuri Node Plan.") |
| **Decision** | D18, to be added to `docs/architecture/platform-plan.md` §7 |
| **Supersedes** | Nothing. It adds a zone beside D14's private network (ADR 0007) |
| **Beside it** | ADR 0005 (supervision), ADR 0006 (release sets), ADR 0007 (rootful Podman, a range per container, fixed addresses), ADR 0008 (the engine has no egress), ADR 0009 (the threat model), ADR 0012 (cloud model lanes) |

## Context

The owner, 2026-10-20: "There is substantial external data in Bitcoin
section (bitcoin price, charts, fear and greed, Bitcoin ETF, Strategy's debt
security tracking, etc.)--should these external data be in their own
container to minimize exposure to attack? I use Tailscale, Telegram,
Discord, cloud backup options (not used yet), tor and ssh (like Umbrel)."

The platform plan gives the node one way out, Tor, on D14's private network.
It does not say where outside-facing code lives. The previous node ran it in
the backend: price and market feeds, an issuer fallback that drove a headless
browser, Telegram alerts and a cloud summary. The lessons register records
what that cost: a price shown as live from a cache after its only source had
refused the node for about ten hours, and Fear & Greed and a chart fallback
fetched from the owner's browser (EVID-05); fallbacks nobody was alarmed
about (EVID-06); an alert logged "sent" that never reached the owner
(HEAL-09); Retry, `/execute` and a Telegram button that bypassed a guard
which lived only in the page (UPG-04); untrusted text ingested into
assistant-reachable stores (AI-02). Everything a feed parses is hostile input
from strangers, and the control plane is the node's one authority (ADR 0002).

## Decision

- **A lobby zone, separate from the core.** Four helper containers: feeds
  (market data), notifier (Telegram and Discord), backup uploader, and the AI
  relay (ADR 0012). Each is its own container in its own user-ID range
  (`UserNS=auto`) with a read-only root filesystem, no capabilities,
  `NoNewPrivileges`, and no secret except its own token. None is on the core
  network of D14.
- **The control plane is the only bridge, by two narrow routes, and no
  commands cross.** Up: a typed ingest route per helper, taking validated
  records behind a machine credential scoped to that route alone (EXEC-07).
  Down: typed events (an alert to deliver, a backup file to upload, a payload
  to relay). A helper is never told to run anything.
- **One egress proxy.** All helper traffic leaves through one proxy
  container that allows listed hostnames, enforces size, time and redirect
  limits, and logs every request. Host firewall rules for the helpers' fixed
  addresses allow nothing else. Widening the allowlist ships in a release set
  or needs the owner's step-up.
- **The core's traffic is unchanged:** Tor only (stage 3).
- **Market data follows EVID-05.** Each value carries its source, the
  source's own timestamp, its age and a stale flag. A failed, empty or
  malformed fetch is never stored as fresh. Each source has its own backoff;
  fallbacks are labelled and kept warm; figures the node can derive from its
  own chain are computed on the node; the owner's browser never calls a third
  party. No headless browser in version one: a source that needs one is its
  own later change, high-risk, in a separate throwaway container with no
  storage. Filings and other free text are untrusted: numbers pass, text does
  not enter any assistant-reachable store (AI-02).
- **The notifier notifies and nothing else.** No inbound commands. A button
  opens the app, where the server's checks and step-up apply (EXEC-04).
  Messages carry no balances, addresses, peers or payment details. An alert
  counts as delivered only when a channel confirms it (HEAL-09). Delivery goes
  through Tor by default, so the chat services do not learn the node's home
  address; clearnet through the proxy is the owner's choice, because a service
  may refuse Tor.
- **The backup uploader sends the static channel backup and nothing else,**
  with a write-only credential, to a destination identified by UUID that
  counts only once a restore from it has passed (FUND-01 to FUND-04). Never
  `channel.db`.
- **Helpers are optional parts of the node.** Ordered with `Wants=` after the
  units they serve, never `Requires=`; the highest `OOMScoreAdjust`; each
  records its last attempt, last success and last error (EVID-06). When one is
  down the node shows "stale" or "unknown", never a zero.
- **Stages, proposed:** feeds with the frontend (stage 8); the notifier at the
  first stage that raises an owner alert; the backup uploader as a destination
  type of stage 5, after its restore drill; the AI relay with the assistant
  (stage 8).

## Consequences

- More containers to pin, patch and release; each is in the release set
  (ADR 0006) like any other.
- A compromised helper yields its own token and the data it handled. It has no
  route to the core network, the secrets store, LND or bitcoind.
- The egress allowlist is a list to maintain. CDN-hosted APIs change
  addresses, so it is by hostname, and it is as strong as DNS and TLS.
- Telegram and Discord still learn that a node exists and when it alerts.
  Telegram's cloud chats are not end-to-end encrypted (only secret chats
  are), so message content is minimal by rule.
- Edits that follow, each its own change: a D18 row in the platform plan §7
  and a line in stage 8's security slice; the threat model §3 ("not trusted"
  gains the helpers and the chat services) and §4 rows for a compromised
  helper and for a chat channel used as a control path.

## Rejected

- Fetching in the control plane: the one authority would parse hostile input
  and hold outbound credentials beside the sign-in and the approval store.
- Fetching in the browser: the owner's address goes to each third party, and
  the page holds a second copy of the freshness rules (EVID-05, EXEC-04).
- One helper for everything: one compromise yields every token.
- Direct egress per helper: no single place to allow, log or stop outbound
  traffic.
- A headless browser for fallbacks: the largest attack surface in the old
  feed code, kept running to keep a fallback warm.

## Sources (read 2026-10-20)

- `docs/requirements/lessons-register.md`: EVID-05, EVID-06, HEAL-09, UPG-04,
  AI-02, EXEC-04, EXEC-07, FUND-01 to FUND-04.
- `docs/architecture/platform-plan.md`: §7 D14 and §8, stages 3, 5 and 8.
- [Telegram, "End-to-End Encryption FAQ"](https://tsf.telegram.org/manuals/e2ee-simple):
  cloud chats are not end-to-end encrypted; secret chats are device-specific. That the
  Bot API's messages are cloud chats is to be confirmed in the Build Record.
