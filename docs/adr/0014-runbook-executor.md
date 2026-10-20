# ADR 0014 — The runbook executor: typed Rust runbooks over a closed action enum, run through APIs and never a shell

| | |
|---|---|
| **Status** | Proposed — drafted 2026-10-20 from the owner's direction in chat ("Yes, let's promote Nix-built images and Rusts runbook executor to ADRs."); Accepted when the owner confirms this wording in its Build Record |
| **Decision** | D21, to be added to `docs/architecture/platform-plan.md` §7 |
| **Supersedes** | Nothing. It makes ADR 0005's "the control plane decides" concrete and follows §3.4 of `docs/architecture/assistant-plan.md` ("a runbook is a Rust value") |
| **Beside it** | ADR 0002 (the control plane is Rust), ADR 0005 (systemd enforces, the control plane decides), ADR 0006 (release sets), ADR 0007 (the root helper's fixed list), ADR 0011 (Diagnostics), ADR 0012 (the advisor's suggestions) |

## Context

The previous node's self-repair is the evidence. Of 89 runbooks, 14 were
broken: invented routes, calls sent to the wrong port, unsupplied variables,
units that did not exist (HEAL-04). A start runbook ran 841 times because its
limit lived inside one call (HEAL-03). A proposal restarted a healthy service
while a side door restarted the broken one with no tier check (HEAL-01). An
executor reported success the effect did not bear out (HEAL-02). Values from
requests reached shells (EXEC-01).

The decisions already taken point one way. ADR 0005: the control plane acts
through systemd and Podman, never a shell, and is the assistant's only door.
ADR 0007: it holds no Podman socket, and one root helper has a fixed list.
The assistant plan's §3.4: runbooks are Rust values, so `cargo test` and
clippy check them against the real unit names in the image.

In the design discussion I suggested runbooks as YAML data files shipped in
the signed release. Reading §3.4 shows the repository has decided otherwise,
and this ADR follows the repository and records why.

## Decision

- **A runbook is a Rust value in the control-plane crate:** the issue types it
  answers, a precheck probe, one `Action`, a validate probe, an undo, an
  attempt budget and cooldown, a tier, and its text for the owner in plain
  words. Runbooks are compiled into the image, so a release carries its
  runbooks and a rollback returns the previous ones with the previous
  software. No runbook is loaded at run time; an unknown or unsigned one
  cannot exist.
- **`Action` is a closed enum** and a `match` over it has no catch-all arm
  (ADR 0002). Proposed variants for version one: `RestartUnit`, `StartUnit`,
  `StopUnit`, `SetMemory`, `TorNewCircuits`, `Wait`, `Escalate` and
  `StageRelease`. The unit is itself an enum generated from the Quadlet files
  shipped in the image, so an unknown unit cannot be named (HEAL-04). Each
  variant is exactly one call:

  | Variant | Through |
  |---|---|
  | `RestartUnit`, `StartUnit`, `StopUnit`, `SetMemory` | systemd, by the policy rule limited to the node's units (ADR 0007) |
  | `TorNewCircuits` | Tor's control port |
  | `StageRelease` | the root helper's `bootc upgrade` (stage only; applying is tier 3) |
  | `Wait`, `Escalate` | in process; `Escalate` emits an owner alert as an event for the notifier (ADR 0010) |

- **No shell and no process spawning.** `std::process::Command` and its async
  equivalents are banned by clippy's `disallowed-methods`, and no value from
  outside reaches an argument list (EXEC-01). The control plane's
  `clippy.toml` has no such ban today; adding it is a control change, its own
  task.
- **The executor is honest** (HEAL-02). A precheck that does not match fails
  the runbook. Each call is bounded by a timeout. The validate probe must
  pass. The effect is verified, not inferred from success: the unit's job
  result and start time, and that the image a container runs is the one in the
  release set. A failure runs the undo. A fix counts only when the detector
  that raised the issue no longer sees it.
- **Attempts are budgeted and recorded before they run** (HEAL-03, HEAL-06,
  HEAL-08, HEAL-10). The attempt is written with outcome unknown before the
  action, so one that kills its own process still counts. The budget is
  persisted, per hypothesis, over a rolling window. There is one open incident
  per service and issue type, one run per runbook and target, and repairs
  run to completion in their own task. A wedged or looping service is
  diagnosed, with its state captured, before anything restarts it. When the
  budget is spent the owner is told once, deduplicated.
- **Tiers (proposed; the repository has only HEAL-01's "tiered proposal"):**

  | Tier | Who decides | Examples |
  |---|---|---|
  | 0 Observe | Automatic | probes, the audit log |
  | 1 Safe, automatic | Automatic, within budget | restart electrs, mempool or a lobby helper; fresh Tor circuits |
  | 2 Gated, automatic | Automatic after its prechecks and a captured diagnosis; the owner is told after | restart bitcoind, LND or Tor; change memory limits |
  | 3 Ask first | The owner, by step-up, in the one approval store (HEAL-07) | apply a release, reboot, any reindex, any migration that ends rollback |
  | 4 Never automatic | A human, outside the executor | moving funds, changing the cold-wallet address, deleting or restoring channel data, downgrading LND, disabling SELinux, the firewall or signature checks |

  Tier 4 effects are not variants of `Action`. They cannot be expressed, so no
  runbook, proposal or model output can name them.
- **The healing loop holds only read-only credentials:** bitcoind's RPC
  whitelist and LND's read-only macaroon, never an admin macaroon (SEC-01).
- **The assistant may only propose a typed intent** that maps to an existing
  runbook or action template. The control plane re-checks the preconditions,
  the budget and the tier on every proposal, and the assistant cannot create
  or change a runbook (AI-02).
- **Starting catalogue (the first rows, each with its hard stop):**

  | Failure | Automatic repair | Hard stop |
  |---|---|---|
  | electrs out of memory | Restart; raise its memory ceiling during the initial index build | Repeated kills: escalate with a plain RAM message; never touch bitcoind or LND to make room |
  | Tor disconnected | Check the clock; fresh circuits; restart Tor | Still down: tell the owner to check the internet connection |
  | bitcoind stalled | Check Tor; capture a diagnosis; one graceful restart | Never reindex automatically |
  | LND unreachable | Wait for bitcoind to be synced; capture a diagnosis; restart once | Never delete channel data, never downgrade |
  | Disk filling | Stop optional services (mempool, the feeds) | Never delete data; escalate |
  | A running image is not the release set's | Re-verify the digest once | A repeat is possible tampering: stop and escalate |

- **Proofs.** A table test per runbook against the real unit names from the
  image's Quadlet files, so a unit that disappears breaks the build (HEAL-04);
  every runbook run against its induced fault on the regtest stack before a set
  ships; tests of the budget and the escalation; `cargo mutants` on the
  refusal paths (threat model T6); a test that fails if `Command` appears in
  the crate once the ban exists.

## Consequences

- Changing a runbook is a Build Procedure task with tests and a release, not a
  hot fix on a node. That is slower and is the point: no one edits repair
  logic where it cannot be tested.
- Adding a unit regenerates the unit enum; forgetting is a compile error.
- The owner cannot tune a runbook on a node. Diagnostics (ADR 0011) shows what
  a runbook did and why; the owner's levers are the budgets and the tier
  settings the control plane exposes as settings.
- Tier 2's automatic restart of bitcoind and LND rests on ADR 0005's rule that
  a diagnosis is captured first; the stage 2 and 4 drills are where that is
  proven.
- Edits that follow, each its own change: a D21 row in the platform plan §7;
  the clippy ban; the threat model's T26 (added with this ADR); the
  catalogue's growth from the lessons register's HEAL entries as stages land.

## Rejected

- Runbooks as YAML or TOML data, my own earlier suggestion: parsing gives up
  the compiler's check that every case is handled (ADR 0002), needs its own
  schema validator and a separate check of unit names (HEAL-04), and buys no
  flexibility because the files would ship inside the signed image anyway.
- Shell-script runbooks, as the previous node's 89 were.
- A generic "run this command" action with an allowlist: the lessons of
  EXEC-04 and AI-02, that a filter over command text is a tripwire and not a
  boundary.
- A supervisor loop in the control plane that restarts on its own clock: ADR
  0005 rejected it (OWN-07).
- Runbooks written or changed by the assistant at run time.

## Sources (read 2026-10-20)

- `docs/requirements/lessons-register.md`: HEAL-01 to HEAL-10, EXEC-01,
  EXEC-04, SEC-01, AI-02, OWN-07.
- ADR 0002, 0005, 0007; `docs/architecture/assistant-plan.md` §3.4 and
  contract A; `docs/security/THREAT_MODEL.md` T6; `control-plane/clippy.toml`.
