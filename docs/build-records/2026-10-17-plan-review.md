# Build Record — Plan review of 2026-10-16: supervision, releases, the setup page and the frontend

| | |
|---|---|
| **Date** | 2026-10-17 (the review itself: 2026-10-16) |
| **Author / session** | Claude Code (Fable 5.1) for Henry Chen, in the owner's desktop session |
| **Branch** | `docs/plan-review-2026-10-16`, this checkout, from `main` `c235364` (PR #10 merged). The checkout had been left on another session's branch, `docs/agent-payments-plan` (pushed, its PR not yet open), with nothing uncommitted; that branch also touches `platform-plan.md` (14 lines) and the lessons register, so whichever PR lands second rebases. |
| **Commits** | `86eea75`, the change (the pre-commit hook ran: gitleaks "no leaks found"); a second commit records this row and the push |
| **Status** | DONE locally; committed and pushed on the owner's word ("Commit and push", 2026-10-17); CI on the pull request Not yet proven. The `NEEDS_OWNER_DECISION` on D11 and the D13 package was answered the same day ("D11. as you recommend. D13 Package R as you recommended") |
| **Change type** | ops (architecture decisions and plan amendments; documentation only) |

## Task Contract

1. **Outcome:** the owner's answers to the 2026-10-16 review become recorded decisions, the platform plan says them, and the two decisions that met a new fact are put back to the owner with their options and costs instead of being chosen for them.
2. **Scope:** this record; `docs/adr/0005-service-supervision.md`, `0006-release-sets-bound-to-the-image.md` and `0007-rootful-range-per-container.md` (new); dated supersession notes in `docs/adr/0003-rootless-range-per-container.md` (status) and `0001-podman-quadlet.md` ("Beside it"); `docs/architecture/platform-plan.md` (status line, "In one page", §2's Podman row, §4.1, §4.2, §5's runtime row, §7 rows D5 and D10 to D15, §8 stages 1, 2 and 8, "Later, with their stage", §9). Tier: **routine** (documentation and process text; [BUILD-PROCEDURE.md, "Risk tiers"](../../.agents/workflows/BUILD-PROCEDURE.md#risk-tiers)). **Not included:** code, units, images, CI, the guard, `AGENTS.md` (its "proposed" design rule points at this plan, which now decides the version half; the settings half waits for stage 6), the lessons register, the agent-payments branch.
3. **Done when:** every decision the owner gave on 2026-10-17 is in §7 of the plan with its status; the open ones say what is open and why, with the owner's options; every fact about outside software the new text rests on carries a source read today (§9); every relative link and anchor in the changed files resolves; `git diff --check` is clean; `repo_hygiene.py` passes; the owner has the open decisions in plain words.
4. **Authority:** edit the files in Scope on the task branch. No commit, push or PR until the owner says so (the owner's standing rule). No code, no agents beyond this session, no verifier (documentation only: the `AGENTS.md` §5 checks and the owner's pull-request review).
5. **Limits:** one task; two repair cycles; no review rounds beyond the owner's. Budget: none configured; consumption reported at close-out.

## 0. Intent

- [x] **Problem, in the owner's words.** 2026-10-16: "I want to make sure that this just as reliable or more reliable the RUST acting as the control plane. … do you see any problems with the current plan. We did go through the error logs and know what needs fixing? How about using TS and the rest of the Frontend work?" Then: "Ok, let me think about each issue. I'll come back tomorrow to do the one Build Record." 2026-10-17, on the four findings: (1) "we need to design and scaffold the UI as we go … a bit softer, fun design … an USB install where the first page would be a setup page that pops up via rikurisetup.local … Could we do https:// ? … name of node (default would be rikuri01.local … rikuri02.local, etc.) … like turbo tax software's split image … The SetupHub has the order of things to setup and indicates what is setup"; (2) "the result should be a clean rollback from failed upgrade of OS. The trick is to make failed upgrade of rikurinode and all its associated services repairable either with rollback or restarts. The current upgrade does separate upgrades for each services. But some upgrade require rikurinode to make adjustments … My running node can't recover consistently"; (3) "if upgrade to latest fails, then use the one previous stable container. Any failure needs to be monitored and fix or rollback"; (4) "Give me the options, your best recommendation"; (5) "What decision do I need to make?"; frontend: "UI use Static files; Yes generate ui's API types from Rust; One typed contract-yes; render tests in CI for different form factors; Ok good, fix the supply chain; sizing, not a flaw yes on TS to be re-express in Rust." Picks: "1. A; 2 & 3. A; 4. A 5. Internal network one Podman pod."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** the platform plan and its decision table; stage 1's deliverables (the setup page); stage 2's first unit; nothing running.
- [x] **Open questions:** the accounts item (D11) was not reached by the owner's picks ("2 & 3. A" answers the release-set question); the package conflict under Decisions.
- [x] **Owner approved the intent:** "Reply with your picks … and I'll start the Build Record … on its own branch" was answered with the picks (2026-10-17).

## 0b. Spec

- [x] **Requirements:** record each decision with the owner's words and date; a decided default is explicit, costed and reversible (every §7 row names its alternatives and their costs); a fact about outside software is used only with a source read today; a conflict between decisions stops only the affected part and goes back to the owner with the smallest resolving decision (`AGENTS.md` §8, "Conflicts"); ADR history is kept by dated supersession, never by rewriting.
- [x] **Design:** one ADR now for what is settled whatever the owner chooses next (ADR 0005, service supervision: systemd enforces, the control plane decides; static per-client RPC credentials; health as function; the repair ladder). The plan's decision table carries D10 to D15; D11, D13 and D14 open. Rejected: writing ADRs for D12 and D13 on the owner's first picks (the picks rest on a fact that turned out false for rootless Podman); editing `AGENTS.md` (its "Proposed, to be decided in the platform plan" line is satisfied by the plan deciding it, and an `AGENTS.md` edit would re-tier this task to high-risk for a pointer).
- [x] **Policy applied:** the first principle (choices exposed, costed, reversible) in every row; the security baseline and design rules in ADR 0005 (credentials never on a command line or in git; health means function; runtime truth; nothing fails silently).
- [x] **Flagged concerns:** the live node's current inability to recover after its Ubuntu update is an incident of the previous repository, outside this task and this checkout; said so to the owner.

## 1. Plan

- [x] **One sentence:** record the 2026-10-17 decisions in the plan and ADR 0005, and return the conflicted package to the owner.
- [x] **Blast radius:** documents only; nothing irreversible; Git history keeps the old texts.
- [x] **Current behaviour characterized:** the plan at `c235364` read in full on 2026-10-16; the previous repository read by absolute path (its `control-plane/src/{cookie,cascade,tor_cascade,electrs_phase,cgroup}.rs`, `scripts/{electrs-start,lnd-start,set-memory-high,set-oom-policy,ensure-swap,auto-scale-memory,compose-lock,rikuri-stack-compose}.sh`, its stack units, `docker-compose.yml`, the records `2026-09-26-lnd-rpccookie.md`, `2026-09-26-cascade-skip-restarted.md`, `2026-08-10-upgrade-reboot-compose-race.md`, `2026-08-16-mempool-oom-recurrence.md`); the lessons register's OWN-01/02/03/04, PLAT-03/04/05/06/07/11, LN-01/04, EXEC-08, SEC-06, TEST-10, HEAL-10 and the gaps table. Findings in the Evidence log.
- [x] **Files and order:** this record → ADR 0005 → the plan → checks → the owner's open decisions.
- [x] **Riskiest step:** stating a decision the owner did not make. Guard: every row quotes the owner's words or says "open".
- [x] **I will know this works when** the "Done when" line holds and the owner can answer the open items from the plan alone.

## 2. Build

- [x] **`docs/adr/0005-service-supervision.md`** (new): systemd enforces (one Quadlet unit per container, one target, limits in the unit, `After=` with `Notify=healthy`, the daemon as the main process, per-unit stop grace, bounded restarts); the control plane decides (phases, budgets, repairs, upgrades, the assistant's only door); static `rpcauth` credentials per client with `rpcwhitelist` as defence in depth; health checks that test function; the repair ladder; what is not ported from the previous node and which of its scenarios become tests. The form of the internal network is left to D14.
- [x] **`docs/architecture/platform-plan.md`:** status line; "In one page" gains the release-set bullet; §4.1 gains "How the checks see the node"; §4.2's "version is machine state" bullet replaced by "Releases are tested sets" and "A release is proven or undone"; §7 rows D10 (setup page's connection, decided A), D11 (accounts, open), D12 (release sets: principle decided, mechanism open with D13), D13 (rootless or rootful as a package, open, with the new facts), D14 (internal network, decided with D13), D15 (the frontend's shape, decided); "Later, with their stage" cites D12; §8 stage 1 names the setup slice, stage 2 the first unit under ADR 0005, stage 8 the full UI; §9 lists the sources read today.
- [x] **After the owner's answers of the same day** ("D11. as you recommend. D13 Package R as you recommended"): **`docs/adr/0006-release-sets-bound-to-the-image.md`** (new): a release is one tested set; the container images bound to the OS image with bootc's logically bound images; proven or undone (greenboot after the reboot, the control plane's watch window after boot, `bootc rollback` through the root helper); migrations end automatic rollback; every release reboots; the install media's path for the images decided in stage 1; auto-update unused. **`docs/adr/0007-rootful-range-per-container.md`** (new): rootful Podman with `UserNS=auto`; system Quadlet units; one private bridge network with fixed addresses (D14); the control plane a system service under its own user, privileged actions through one root helper with a fixed list; the volume-ownership question carried over to stage 2; supersedes ADR 0003. **ADR 0003**: status cell marked superseded, text kept. **ADR 0001**: "Beside it" notes D13 and that the auto-update consequence no longer applies. **The plan**: status line (thirteen decided, D1 and D4 open), "In one page" (rootful, bound to the image), §2's Podman row, §4.1, §4.2, §5's runtime row, D5's cell marked superseded, D11 to D14's status cells.
- [x] **Clean as you go:** the replaced §4.2 bullet is gone, not kept beside the new one; its owner choice of 2026-10-10 is named in the new text as superseded; ADR 0003 is superseded by a dated note, not rewritten.
- [x] **Security question:** no code; the ADR's credential rules tighten the previous node's practice (no credential on a command line, in a unit file or in git; the gate's hygiene check and the secret scan cover the repository side).

## 3. Debug

N/A: no defect fixed.

## 4. Verify

- [x] Links and anchors in the changed files resolve: 1 relative link in the three files (the record's link to "Risk tiers"), 0 broken; the other references are `§` numbers, `D` numbers and absolute URLs (Evidence log).
- [x] `git diff --check` clean; `python3 scripts/quality/repo_hygiene.py .` exit 0 (it scans tracked files; the two new files are not yet staged and hold no secret, log or state).
- [x] Independent verification: N/A, documentation only (routine tier: the `AGENTS.md` §5 checks and the owner's pull-request review).
- [x] Diff matches §1: the plan (62 insertions, 22 deletions), ADR 0005 and this record; no other file. Deviation: none. Not done on purpose: `AGENTS.md` (see Scope) and the ADRs for D12 and D13.

## 5. Close Out

- [ ] Full gate: not run locally for a documentation-only change (BUILD-PROCEDURE, Close Out); CI runs it on the PR. Not yet proven.
- [x] Scrap sweep: the link-check script lives in the session's scratchpad, not the repository; nothing created in the tree beyond the three files in Scope. (Untracked files in the checkout root that are not this task's — shell dotfiles, editor folders, `.codex/` — were left as found.)
- [ ] Reviewed per `REVIEW.md`: the owner's pull-request review.
- [x] Lesson loop: N/A.
- [x] Knowledge layer: the plan and the ADR are the knowledge layer for this change; no help page or runbook exists yet.
- [x] Commit message explains why; record committed with the change (`86eea75`, on the owner's word).

## Decisions of 2026-10-17

| | Decision | Status |
|---|---|---|
| D10 | The setup page's connection: a per-node certificate authority with a guided one-time install; plain HTTP never carries the seed or a password | **Decided: A** ("1. A") |
| D11 | Accounts: web sign-in only, `root` locked, SSH off and later key-only (recommended), or a Linux admin account made at setup | **Decided: web sign-in only** ("D11. as you recommend", later the same day; the first picks had not reached it) |
| D12 | Releases are tested sets; no service upgraded on its own; a failed set is undone by going back to the previous one | **Decided** ("2 & 3. A", and "use the one previous stable container"); mechanism: bound to the OS image (ADR 0006), which needs rootful Podman |
| D13 | Rootless or rootful, revisited as a package (see below) | **Decided: package R** ("D13 Package R as you recommended"; ADR 0007). The first picks of A for the release sets and of a pod assumed facts that do not hold under rootless Podman |
| D14 | Internal network: one pod (the owner's first pick), or a private network with fixed addresses | **Decided: a private network with fixed addresses** (with package R; ADR 0007) |
| D15 | The frontend: TypeScript, static files served by the control plane, API types generated from Rust, render tests at phone, tablet and desktop widths, supply-chain rules, TypeScript logic re-expressed in Rust | **Decided** |
| — | Control plane as a user service beside the containers plus a root helper ("4. A") | Folded into D13: it is the rootless package's shape; the rootful package makes it a system service |

### The conflict, and the two packages

Read on 2026-10-17 (sources in the plan's §9):

- bootc's logically bound images are pulled with `bootc upgrade` and "the logically bound images corresponding to rollback deployments will also be retained", which is what the owner wants from "use the one previous stable container". But "rootless containers from these system stores are not supported", and Anaconda does not support them. So the one-image, one-rollback mechanism exists only for rootful Podman.
- A pod's `--userns` is set "for all the containers in a pod". One pod means one ID range shared by bitcoind, Tor and LND, not ADR 0003's range per container. Pasta preserves inbound peers' addresses; the rootless bridge forwarder (`rootlessport`) does not, and the pasta setting for it is marked experimental.

Hence one owner decision, as a package:

- **Package R — rootful Podman with a user-ID range per container** (`userns=auto`; the plan's D5 third option). System Quadlet units; the container images bound to the OS image (one update, one rollback, boots without the network); a private bridge network with fixed addresses (a range per container kept; inbound peer addresses preserved); the control plane a system service under its own user, with one small root helper for a fixed list of actions (`bootc` upgrade and rollback, hostname, the backup drive, reboot); greenboot sees the units directly. **Cost:** Podman's own setup code runs as root, so a bug in it reaches the host; the container processes themselves run as unprivileged mapped IDs, as under rootless. ADR 0003 is superseded by a dated ADR. **Recommended:** the project's central reliability mechanism is only available this way, and the separation between containers that ADR 0003 wanted is kept.
- **Package U — rootless, as decided.** The control plane implements the release set: it pulls the next set into the user's storage before the switch, keeps the previous set until the next is proven, and refuses to start a set that is missing (never starts the money daemons at defaults, OWN-01). Containers in one pod on pasta (one ID range per pod) or on a bridge network with a range per container (inbound peer addresses lost). The control plane a user service beside the units plus a root helper; greenboot asks the control plane; units kept alive by lingering. **Cost:** more control-plane code on the rollback path, which is where the previous node failed; the rootless networking trade-offs; boot ordering through lingering.

Package R also decides D14 (a private network with fixed addresses) and D12's mechanism (bound images); package U decides them the other way.

**Resolved the same day.** The owner: "D11. as you recommend. D13 Package R as you recommended." ADRs 0006 and 0007 record it; ADR 0003 carries the dated supersession.

## Skipped items — visible, never silent

- §5's full-gate box: not run locally (documentation only); CI runs the gate on the pull request, Not yet proven until seen green.
- `AGENTS.md` §7's "Proposed, to be decided in the platform plan" line: the version half is decided by D12; the settings half waits for stage 6. A pointer edit there is high-risk tier (agent rules) and is not worth a task on its own; it goes with the next change to `AGENTS.md`.

## Evidence log

```
2026-10-16 analysis (this session), read by absolute path in /home/junc/rikuri/rikurinode:
  electrs_phase.rs: engages only when host RAM < 12288 MB (min_engage_ram_mb);
    this machine: MemTotal 27973356 kB -> marked STEADY, inert. Its actions: docker stop/start of
    mempool-api, mempool-web, mempool-db, redis, chromadb during Electrs's first sync.
  set-memory-high.sh: writes cgroup memory.high at 85 % of memory.max; rikuri-memory-high.timer
    re-applies every 5 min because the cgroup resets on restart. set-oom-policy.sh: oom_score_adj
    -800 bitcoin/electrs/lnd, +700 mempool/chromadb/redis. ensure-swap.sh: 4 GB swap cushion.
  cascade.rs: restarts electrs, lnd, mempool-api, mempool-web on a cookie change (inotify);
    2026-09-26 skip rule for a dependant already restarted. lnd-start.sh / electrs-start.sh:
    PID-1 wrappers, cookie wait, cookie watcher, Tor control-port wait.
  2026-09-26-lnd-rpccookie.md: LND 0.21.3 with bitcoind.rpccookie kept failing 401 for 2.5+ min
    after a bitcoind restart (regtest): it does not re-read a rotated cookie.
  Static credentials in the old repo: docker-compose.testnet.yml / testnet-knots.yml pass
    -rpcuser=rikuri-testnet -rpcpassword=rikuri-testnet on the command line.
  Old frontend: 200 .ts/.tsx files, 55 test files under dashboard/frontend/tests, locales en es
    ja zh zh-TW. Old backend: 709 .ts files, 172,506 lines outside tests.
  Lessons register port candidates: 90 rows; 61 TypeScript (5,260 lines "port with tests",
    6,880 "port after re-check"), 12 Rust, 11 shell; verdicts 42 port with tests,
    45 after re-check, 3 do not port.

2026-10-17 sources (WebFetch; quotations as returned):
  https://bootc.dev/bootc/bootc-logically-bound-images.7.html
    "the bound images defined in the new bootc image will be automatically pulled into the bootc
    image storage"; "The logically bound images corresponding to rollback deployments will also be
    retained"; "Rootless containers from these system stores are not supported"; Anaconda does
    not currently support logically bound images; store /usr/lib/bootc/storage.
  https://docs.podman.io/en/latest/markdown/podman-pod-create.1.html
    --userns: "Set the user namespace mode for all the containers in a pod."; default --share
    ipc,net,uts; pasta "Port forwarding preserves the original source IP address."; rootlessport
    "is a userspace proxy that does not preserve client source IPs"; rootless_port_forwarder=pasta
    "This option is experimental".
  https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html
    Notify=healthy "will postpone startup notifications until such time as the container is marked
    healthy"; HealthOnFailure "Action to take once the container transitions to an unhealthy
    state" (kill recommended, systemd restarts); StopTimeout below the unit timeout; Pod= links a
    .pod unit; AutoUpdate registry|local; [Service] and [Install] "pass directly to systemd";
    user units wait on podman-user-wait-network-online.service.
  https://github.com/bitcoin/bitcoin/blob/master/doc/JSON-RPC-interface.md
    cookie "is the preferred RPC authentication method"; rpcauth via share/rpcauth; whitelists
    "should not be considered robust security boundaries"; "it does not use encryption";
    "Do not enable RPC connections over the public Internet."
  https://raw.githubusercontent.com/lightningnetwork/lnd/v0.21.4-beta/sample-lnd.conf
    bitcoind.rpccookie "Authentication cookie file for RPC connections."; bitcoind.rpcpolling.

Checks, 2026-10-17, branch docs/plan-review-2026-10-16 at c235364 + working tree:
  python3 -I <scratchpad>/linkcheck.py docs/build-records/2026-10-17-plan-review.md \
      docs/adr/0005-service-supervision.md docs/architecture/platform-plan.md
    -> checked 1 relative links; 0 broken
  git diff --check -> clean
  python3 scripts/quality/repo_hygiene.py . -> exit 0
  git diff --stat -> docs/architecture/platform-plan.md | 84 ++++---- (62 insertions, 22 deletions)

Checks re-run after the owner's answers (ADRs 0006 and 0007, the notes in ADRs 0001 and 0003,
the plan's status cells), same branch and tree:
  linkcheck.py over the 7 changed files -> checked 1 relative links; 0 broken
  git diff --check -> clean
  python3 scripts/quality/repo_hygiene.py . -> exit 0
  grep for stale wording ("open with D13", "package U.", "**Open**") in the plan -> 0
  git diff --stat -> 3 files changed, 70 insertions(+), 30 deletions(-); new: ADR 0005 (111 lines),
    ADR 0006 (92), ADR 0007 (95), this record (160)
  Full gate: not run (documentation only); CI on the pull request: Not yet proven.
```
