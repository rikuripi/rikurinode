# Build Record — Stage 1 gains the boot-cause record, its rollback rule and UPS support (D22)

| | |
|---|---|
| **Date** | 2026-10-21 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `docs/d22-boot-cause-and-ups` (renamed from `claude/linux-security-research-eb820b` on the owner's word), in the worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` (made by the app for this session) |
| **Commits** | one commit on `docs/d22-boot-cause-and-ups` holding the change and this record (its hash is in the pull request); committed without the pre-commit hook, see Skipped items |
| **Status** | Edits verified (verifier FAIL, repaired, follow-up PASS); COMPLETE; committed and opened as a pull request on the owner's word (2026-10-21, "Commit + PR, new branch") |
| **Change type** | ops (plan amendment; documentation only) |

## Task Contract

1. **Outcome:** stage 1 of the plan says the node records why it restarted, never rolls back a good update for a power cut, and responds to a UPS when one is connected, so these are built and drilled together with the rollback they protect.
2. **Scope:** `docs/architecture/platform-plan.md` (the status paragraph; §2's greenboot fact; §4.1; a row D22 in §7; stage 1's row in §8; §9's sources) and stage 1's row in `docs/security/THREAT_MODEL.md` §5. Tier: **high-risk** (the rollback path, which protects the node and its data); documentation only. **Not included:** any code, the image, greenboot units, the choice of UPS software (a candidate is named, to be inspected first), the Pi (D1 stays open), other stages.
3. **Done when:** D22 is recorded as decided by the owner with its options and costs; §4.1 and stage 1's row carry the boot-cause record, the rollback rule and UPS support with their drill and security slice; the threat model's stage 1 row agrees; §2 and §9 carry the greenboot reports read today with their sources; no other decided text changes; `git diff --check` clean; `repo_hygiene.py` exits 0; links resolve; one `verifier` pass has no Important finding.
4. **Authority:** edit the two documents and this record; read the repository and public web pages. No commit, push or PR until the owner says so; nothing running touched. Independent check required (high-risk).
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured; report what was used.

## 0. Intent

- [x] **Problem, in the owner's words:** "Ok, can we just include boot-cause rule and UPS support as stage one? If they are all about reboot and rollback." (2026-10-21), after "I suppose if someone provides an UPS, the node should respond to it. If we can leave traces of power outage and crash caused by it or some update that would provide rollback reasoning."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** stage 1's scope, drill and security slice; nothing running.
- [x] **Open questions:** how greenboot is told the cause (its own counter, a drop-in, or the node's required check) is left to the stage 1 change that builds it, because of greenboot's open reports (§2); the UPS software is a candidate until inspected.
- [x] **Owner approved the intent:** the message above.

## 0b. Spec

- [x] **Requirements:** a power cut or a UPS shutdown before or while an update is applied never rolls the running image back; a fault of the new image still rolls it back; unclear evidence counts against the update; without a UPS nothing changes; the UPS service listens on loopback at most, never on the LAN; the owner sees the cause in plain words.
- [x] **Design:** bullets in §4.1 for the record, the rule and the UPS; one decision row; stage 1's row and the threat model's row extended. Rejected: a separate stage or ADR (the owner chose stage 1; the plan's decision table is enough for a scope choice); letting the cause record replace greenboot's counter (more code on the rollback path, where the previous node failed).
- [x] **Policy applied:** "nothing important fails silently" (the heartbeat and the stated cause); "roll back software, never data"; a behaviour-changing default is an explicit owner choice (D22); third-party code inspected before adoption (AGENTS.md §2).
- [x] **Flagged concerns:** a frozen node that its owner unplugs looks like a power cut; the rule counts a repeated power loss on an unproven image against it (recorded in §4.1).

## 1. Plan

- [x] **One sentence:** add D22 and write its content into §4.1, stage 1 and the threat model's stage 1 row.
- [x] **Blast radius:** two documentation files; nothing irreversible.
- [x] **Current behaviour characterized:** read this session: the status paragraph, §2, §4.1, §7, §8's stage 1 row, §9 and the threat model's §5.
- [x] **Files and order:** this record, the plan, the threat model, checks, verifier.
- [x] **Risks:** a stale count in the status paragraph; a rule that hides a real failure.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] Edits made, additions only except the status paragraph's counts and dates and §2's greenboot row, which gained a dated sentence.
- [x] **Security question answered:** the record and the UPS sit on the rollback path and add a root service with a new USB input; stage 1's slice names its tests (the UPS service unreachable from the LAN; a flapping or false UPS obeyed a bounded number of times; the drill's power cuts and failed apply). None exists, so nothing is proven.

## 3. Debug

- N/A

## 4. Verify

- [x] Checks: see the Evidence log.
- [x] Independent verification: first `verifier` pass **FAIL** on two Important findings: (1) §2 claimed D22 covers greenboot #219, but the rule covered only power cuts, not a finalize failure from a full `/boot` or an ostree error, so a healthy node could still be rolled back; (2) "a wrong rollback can be undone" conflicted with ADR 0006's "Migrations end automatic rollback". Both corrected in repair cycle 1 (of two): the rule now covers an update never applied for any cause, and yields to ADR 0006 after a migration; five nits corrected with them (#218 scoped to hosts without a separate `/boot` mount; #221 counted as a pull request; the UPS-ordered shutdown, low-battery restart and a flapping UPS covered; power-on after power loss for every node; an unsourced "packaged by Fedora" and an unused §9 line removed). Follow-up pass **PASS** (corrections only), no new Important finding.

## 5. Close Out

- [ ] Full gate: documentation only, so CI runs it on the pull request, if the owner asks for one.
- [x] Review and commit: verifier FAIL, repaired, follow-up PASS; committed on `docs/d22-boot-cause-and-ups` and opened as a pull request on the owner's word (see Status).

## Skipped items — visible, never silent

- Full gate: documentation only; CI runs it on a pull request, if the owner asks for one.
- Follow-up nit 1 (units held back for charge could fail a required check and count against a good image) resolved by the owner's ruling, 2026-10-21, option B of three (A: do not count those boots; B: no update applied while on battery; C: leave it to the build task): "B: no update on battery". Written into §4.1's UPS bullet and the D22 row as the owner's text; added after the two review rounds, so it has no verifier pass (AGENTS.md §5 allows no third round); CI's full gate covers the documentation checks.
- Pre-commit hook: not run. Installing it (`git config core.hooksPath scripts/quality/hooks`) was refused by the sandbox (`could not lock config file .../.git/config: Operation not permitted`), and gitleaks is not installed on this Mac. Its other two checks were run by hand on the staged change: `git diff --cached --check` clean, `repo_hygiene.py` exit 0 with this record indexed. The secret scan runs in CI's full gate on the pull request. Installing the hook in this clone is the owner's step.
- Backlog nit from the follow-up pass, not pursued: (2) once a flapping UPS is no longer obeyed, a real low battery ends in a power cut, which the help text should say.

## Evidence log

Checks, 2026-10-21, on the uncommitted edit (documentation only):

- `git diff --check`: clean, after the first edit and after repair 1.
- `python3 scripts/quality/repo_hygiene.py .`: exit 0 both times (it reads `git ls-files`, so this untracked record is checked when committed).
- The nine new URLs in §9: each HTTP 200 (curl -L); #221 confirmed a pull request through the API.
- Not run: the guard tests (no `.claude/` change; the verifier's attempt through `safe-run.sh` refused: "namespace isolation unavailable here", this host is macOS); the full gate (CI runs it on a pull request).
- Correction during the edit: "the UPS service opens no network port" became "loopback at most, never on the LAN", because the candidate's monitor normally reaches its own server over local TCP.
- Budget used: one session; one verifier pass and one follow-up.

Sources read 2026-10-21 (public, read-only):

- `fedora-iot/fedora-iot-bootc` at `bff02ddc` (2026-10-21): `fedora-iot-45.yaml` builds from `fedora-devel`, with the same `iot-packages.yaml` as 44.
- greenboot-rs issues #212, #217 to #221 and releases (v0.16.4, 2026-08-18, the newest).
- `usr/lib/systemd/system/greenboot-set-rollback-trigger.service` at `v0.16.4` and `main`: `DefaultDependencies=no`, `ExecStop=` only, no `Conflicts=`; ostree's `src/boot/ostree-finalize-staged.service` on `main` has `Conflicts=final.target` and `Before=final.target`. Read only, not run.
- Not read: the shared base layer (gitlab.com) and Fedora's package sources (src.fedoraproject.org); the sandbox refused both.
