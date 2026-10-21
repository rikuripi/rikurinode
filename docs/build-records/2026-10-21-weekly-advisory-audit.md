# Build Record — The weekly advisory audit in CI (S2): cargo-deny and OSV on a schedule, and the gate's stale-run warning

| | |
|---|---|
| **Date** | 2026-10-21 |
| **Author / session** | Claude (Fable 5.1, desktop app; handed off from the session that pulled `main`) for Henry Chen |
| **Branch** | `ci/weekly-advisory-audit`, from `main` at `c070a98`, in the main checkout `/home/junc/rikuripi/rikurinode` |
| **Commits** | the change and this record in one commit; the close-out commit that follows names its hash and the push |
| **Status** | COMPLETE locally; CI on the pull request not yet proven. First `verifier` pass FAIL (OA7, AGE4, the T8 claim), repair cycle 1, follow-up pass PASS (2026-10-21) |
| **Change type** | ops (a control: CI and the full gate) |

## Task Contract

1. **Outcome:** an advisory against one of the control plane's locked crates or one of CI's pinned actions is found within a week of its publication, on its own clock, and a weekly audit that fails, stops running or goes stale is seen: GitHub emails the owner on a failed run, and the full gate warns when the last successful run is older than eight days or cannot be read.
2. **Scope:** `.github/workflows/advisory-audit.yml` (new: the scheduled audit), `scripts/quality/osv_audit.py` (new: the OSV query over `control-plane/Cargo.lock` and the workflows' pinned actions), `scripts/quality/advisory_audit_age.py` (new: the gate's warning), their tests `scripts/quality/tests/test_osv_audit.py`, `test_advisory_audit_age.py` and `test_workflows.py` (new), `scripts/quality/full-gate.sh` (step 10), `.github/workflows/ci.yml` (`actions: read` and the token for step 10), and the documents the behaviour changes: `docs/security/THREAT_MODEL.md` (T8, T9, §6, §9), `.agents/workflows/BUILD-PROCEDURE.md` (the weekly loop), `AGENTS.md` ("Verification by maturity", one clause), `docs/requirements/lessons-register.md` (two status lines, SEC-06 and TEST-05), and this record. Tier: **high-risk** (a control; BUILD-PROCEDURE.md, "Risk tiers": when unsure, choose high-risk). **Not included:** the image scan (S3: its scanner is adopted only after the inspection AGENTS.md §2 requires), any dependency bump (`cargo deny` is green on `main` since pull request #18), the release cadence (process, decided 2026-10-18), README, the guard and its policy.
3. **Done when:** `python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'` passes with the new tests; each new check is seen to fail on a scratch mutation (a floating `uses:` tag, a fake finding, a nine-day-old run) and the runs are recorded below; the real OSV query over this lockfile and these workflows returns clean (rc 0) for every registry crate and every pinned action; the age check run here without a token prints its warning and exits 0; `shellcheck --severity=style`, `repo_hygiene.py` and `git diff --check` pass; `scripts/quality/full-gate.sh` is green on this machine; one `verifier` pass has no Important finding; CI's `Full gate (Ubuntu)`, the guard job and the new `Advisory audit (weekly)` job are green on the pull request (not yet proven until the owner opens it).
4. **Authority:** the owner, 2026-10-21, chose "S2 weekly advisory audit in CI (Recommended)" from the three candidate changes put to them, which authorizes building this control change on this branch (the decision itself: "do as you recommended", 2026-10-18, S2 in `docs/build-records/2026-10-18-security-plan.md`; the threat model §6 named its CI parts the next task). Edit the files in Scope on this branch. Network: `api.osv.dev` for the one real run (a one-command sandbox allowance) and `api.github.com`. **No commit, push or pull request until the owner says so** (the owner's standing rule): given on 2026-10-21, "Yes, if the follow-up passes", and the follow-up passed the same day. One `verifier` pass, and a follow-up pass on its corrections only. No merge.
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured; consumption reported at close-out.

## 0. Intent

- [x] **Problem, in the owner's words:** "S2 weekly advisory audit in CI (Recommended)" (2026-10-21, chosen from three candidates); the decision behind it, "do as you recommended" (2026-10-18): a weekly scheduled advisory audit whose failure emails the owner. The lessons: the previous node's audit read RustSec only while GitHub listed advisories it lacked, and printed "clean" with cargo missing (SEC-06); its weekly audit lived on a non-default branch and never ran once, and CI was red for seven weeks with nothing saying so (TEST-05). Today every check in this repository runs on a pull request or a push, and nothing is scheduled (threat model T8).
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** this repository's CI and the full gate; the owner's inbox on a failed weekly run. Nothing runs on a node.
- [x] **Open questions:** three reversible defaults are chosen here and put to the owner at close-out, each with its cost: (a) the schedule, Tuesdays 08:00 UTC (the hour AISecurity's weekly audit uses); cost: about five minutes of CI a week and an email only on failure; the hour is UTC, and any other hour or day is a one-line change. (b) `actions: read` on CI's token, passed to the full gate's step so step 10 can list the audit's runs; cost: that read-only, job-lifetime token sits in the environment of every gate step in CI, including cargo's build scripts and the tests inside `safe-run.sh`, not only step 10 (the verifier's nit 4); the alternative is a separate CI step that holds the token and runs the age check outside the one gate, in which case the gate's own step 10 warns "no token" in CI too. (c) a `pull_request` trigger on the audit workflow, limited to its own inputs (the workflow file, the lockfile, `deny.toml`, the script); cost: one more job of about five minutes on such pull requests; benefit: a lockfile change is audited by OSV before it merges, and the workflow is proven on this pull request. **Answered by the owner on 2026-10-21** (question card): (a) "Tuesdays 08:00 UTC (Recommended)"; (b) "Yes, on the gate step (Recommended)"; (c) "Yes (Recommended)".
- [x] **Owner approved the intent:** the choice above.

## 0b. Spec

- [x] **Requirements:** R1 the audit runs on a schedule from `main` and on demand. R2 it reads a merged source: RustSec through the pinned cargo-deny, and OSV (which merges RustSec and GitHub's advisories) for every locked crates.io crate, and OSV's "GitHub Actions" ecosystem for every action CI pins (SEC-06). R3 it distinguishes clean (0), findings (1) and could-not-audit (2), and never passes an error off as clean (SEC-06). R4 one allow-list, by any alias, with a reason: cargo-deny's own `ignore` list in `control-plane/deny.toml`, read by both checks; entries that match nothing are printed (SEC-06). R5 a failed run reaches the owner: GitHub emails the failure of a scheduled workflow. R6 the full gate warns, and never fails, when the audit's last successful run on `main` is older than eight days, failed, or cannot be read (TEST-05, threat model §6). R7 every action is pinned by commit with its version named in a comment, or the audit refuses (could-not-audit), because OSV's ranges name versions, not commits. R8 tools pinned and checksum-verified as in `ci.yml`; Python 3.9 or newer, standard library only, as the quality tools claim.
- [x] **Design:** one workflow, `advisory-audit.yml`, on a weekly cron, `workflow_dispatch`, and `pull_request` for its own inputs, running the pinned cargo-deny's `check advisories` and then `osv_audit.py`. `osv_audit.py` reads the lockfile's registry packages and the workflows' `uses:` pins, asks OSV's batch endpoint for the crates (OSV evaluates crate versions itself) and OSV's single-query endpoint for each action by package, then evaluates the "GitHub Actions" ranges locally, because OSV returns nothing for a version query in that ecosystem (probe of 2026-10-21, Evidence log); it fetches each finding's record for its aliases and summary, applies `deny.toml`'s `ignore` list by id or alias, and exits 0, 1 or 2. `advisory_audit_age.py` asks GitHub's API for the workflow's completed runs on `main`, keeps the scheduled and dispatched ones, and prints one `full-gate: warning:` line when there is no token, an HTTP error, no run, a failed latest run, or a latest success older than eight days; the gate runs it as step 10. A test holds the workflows together: every `uses:` pinned to a 40-hex commit with a version comment; the cargo-deny install lines identical in `ci.yml` and the audit; the audit's triggers and permissions; CI's permissions exactly `contents: read` and `actions: read`. **Rejected:** `osv-scanner` (a third-party binary that needs the inspection AGENTS.md §2 requires; forty lines of standard-library HTTP do the same for two ecosystems); `cargo audit` (RustSec only, what cargo-deny already reads); Dependabot alerts or pull requests (a bot's clock; D17 rejects bots, and alerts are a repository setting outside the tree that the gate cannot see); failing the gate on a stale audit (it would block every pull request for a cause outside it; the plan says warns); querying actions by commit (OSV answers nothing for a commit query, probe of 2026-10-21); a shared install script factored out of `ci.yml` (the identical-lines test holds the two copies together with no change to the gate's own install steps).
- [x] **Policy applied:** "Nothing important fails silently: watch for the absence of success" (the gate's warning on a missing run); SEC-06 and TEST-05 verbatim; "a control change is its own task" (AGENTS.md §2); every behaviour-changing default an explicit, costed, reversible owner choice (§0, the three defaults); untrusted content as data (OSV's and GitHub's answers are parsed, never executed); no third-party code adopted.
- [x] **Flagged concerns, routed:** (1) **Who gets the email.** GitHub notifies a scheduled workflow's failure to the user who last modified the cron line in the workflow file. The commits here are authored as `Henry Chen <henrycofc@outlook.com>` (`git config user.email`); if that address is not one GitHub knows for the owner's account, the alarm goes nowhere. Owner to confirm at close-out. (2) **A silent stop.** GitHub disables a repository's schedules after sixty days without activity; the gate's warning (R6) is what sees it. (3) **The private repository.** Listing workflow runs needs a token: CI's `GITHUB_TOKEN` with `actions: read` (owner default b). A local run in the sandbox has no token and warns "no token" every time; the warning says so plainly rather than claiming a check it did not make. (4) **OSV's limits.** One batch call of about 130 queries and a few single queries a week, well within OSV's published limits.

## 1. Plan

- [x] **One sentence:** a weekly workflow runs cargo-deny's advisories and an OSV query over the locked crates and the pinned actions, with exit codes that cannot pass off an error as clean, and the full gate warns when that workflow's last success on `main` is stale.
- [x] **Blast radius:** CI workflows, the gate script, two new quality scripts and three test files, and the documents named in Scope. No runtime behaviour; no node; no secret.
- [x] **Current behaviour characterized:** `grep -n schedule .github/workflows/*.yml` finds nothing; cargo-deny runs only in `ci.yml` on pull requests and pushes to `main` (full gate step 9); threat model T8 says "nothing scheduled" and T9 "Not in place"; the unauthenticated API returns 404 for the repository, so it is private; OSV probes of 2026-10-21 in the Evidence log fix the API's shapes; the lockfile has 131 packages, 129 from the registry and 2 workspace crates; the workflows pin two actions (`actions/checkout` v7.0.1, `actions/setup-python` v5.6.0).
- [x] **Files and order:** this record; `osv_audit.py` and its tests; `advisory_audit_age.py` and its tests; `test_workflows.py`; `advisory-audit.yml`; `ci.yml`; `full-gate.sh`; the four documents.
- [x] **Risks:** the "GitHub Actions" ranges evaluated locally (a version-format mismatch would hide a finding: the range tests cover both boundaries and the `v` prefix, and an unparsable version is could-not-audit, never clean); the local age warning becoming noise (it is one line, and it names the cause); a Python 3.9 incompatibility seen only in CI's matrix.
- [x] **Verification defined up front:** I will know this works when the tests pass here (3.14) and in CI (3.9 and 3.12), each scratch mutation fails, the real OSV run is clean on this lockfile and these workflows, the age check warns here without a token, the full gate is green here, and the audit workflow is green on the pull request.

## 2. Build

- [x] **New code meets the bar:** two scripts (about 300 and 150 lines), standard library only, Python 3.9 or newer; every input and every answer checked for shape, and a wrong one is could-not-audit or a warning, never clean; bounded requests (OSV's batch limit of 1000, one query per distinct action, GitHub's ten latest completed runs), a timeout and a User-Agent on every request. Each module's docstring names the lesson, the usage and this record.
- [x] **Clean as you go:** nothing replaced; the gate's nine steps renumbered to ten; no old version to remove.
- [x] **Security question answered:** the change touches no authentication, money, execution or private data. CI's token gains `actions: read`, read-only; the two scripts read two public APIs and treat the answers as data (parsed, compared, printed; nothing executed or written). Gate: the quality tools' tests (full gate step 3) and `test_workflows.py`, which pins CI's permissions to exactly `contents: read` and `actions: read` and the audit's to `contents: read`.

## 3. Debug

- N/A: no defect fixed.

## 4. Verify

- [x] **Unit tests:** three new files, 50 tests (`test_osv_audit.py` 28, `test_advisory_audit_age.py` 14, `test_workflows.py` 8), each failure path a case: the three exit codes, an answer of the wrong shape, a floating or unversioned pin, both range boundaries and the `v` prefix, the alias match and the unmatched entry, the no-token, bad-status, unreachable, no-run, failed-run and stale-run warnings at seven, eight and nine days, and the workflows' pins, permissions and triggers. The quality tools' suite: 132 tests, OK (Evidence log).
- [x] **Watched it work:** the real OSV query over this lockfile and these workflows, 129 crates and 2 actions (5 pins), clean, rc 0; the age check here without a token (the warning, rc 0) and with a bad token (HTTP 401 named, rc 0). Not yet watched: the audit workflow in CI and the age check with CI's token, both on the pull request once the owner opens it; until the first scheduled run on `main` after the merge, CI's gate will warn "no completed scheduled or dispatched run", which is the expected first state.
- [x] **Recovery/fallback path live:** could-not-audit (rc 2) on a scratch copy with a floating tag and on one with the version comment removed; the two warnings above.
- [x] **Regression guard proven to FAIL:** eight hand mutants of the two scripts, one line each, every one killed by the tests (Evidence log), and the two red runs. The old tree has no audit and no warning, so there is no older code to run the guards against.
- [x] **Independent verification:** first `verifier` pass (2026-10-21) **FAIL**, three Important findings: (1) OA7, a mutant matching every `ignore` entry to every finding survived, because no test had a finding beside an unrelated entry; (2) AGE4, a mutant warning only on a `failure` conclusion survived, because no test used `cancelled`, `timed_out`, `skipped` or a null conclusion; (3) the threat model's T8 cell claimed the audit "seen green on its pull request" before any pull request existed. Its other 18 mutants were killed; its real-entry-point runs (a real finding, an alias match, an unrelated entry, the two refusals, the age warnings) agreed with this record. Five nits and two more. **Repair cycle 1:** a test for each survivor (`test_an_unrelated_entry_does_not_suppress_a_finding`, `test_any_conclusion_but_success_warns`), both mutants re-run and killed; T8 and §9 reworded as owed. Nits fixed in place: both fetchers turn `http.client.HTTPException` into could-not-audit or a warning (tests through a mocked `urlopen` and a fake fetcher); a missing workflows folder is could-not-audit, not "0 actions" (test); the origin test reads whatever origin the clone has, so a fork passes; the age message prints days with two decimals ("8.01 days old, older than the 8-day limit"); an advisory id of an unexpected form is refused before it is put in a URL (test). Recorded, not changed: the token's reach in CI (owner default b, its cost now in §0); the nine-day-old run through GitHub stays Not yet proven until a token exists (its judgement is tested with a fixture and held by mutants AGE1, AGE3 and M5). **Follow-up pass:** **PASS** (2026-10-21): the three corrections checked, the first pass's twenty mutants rerun and all killed (OA7 and AGE4 by their new tests), the gate rerun by the verifier rc 0 with 138 quality-tool tests; CI stays Not yet proven until the pull request.
- [x] **Diff matches the plan:** the 13 files Scope names, nothing else. One refinement beyond the plan's wording: one OSV query per distinct action, with every pinned version of it placed in that action's ranges (the plan said one query per action line), and a test for it.

## 5. Close Out

- [x] **Full gate green, locally:** `scripts/quality/full-gate.sh` on the staged change, 2026-10-21, rc 0, `full-gate: all 10 steps passed` (Evidence log): the guard's 91 tests, the quality tools' 132 (50 new) and the image check's 54 all OK; hygiene, ShellCheck, whitespace and the secret scan clean; Rust with the pinned 1.98.1 (step 1 refuses any other): fetch as locked, fmt, clippy with warnings as errors, `cargo test` inside `safe-run.sh` (104 unit, `plain_listener` 3, `sign_in` 9, `status_route` 3; the layer saw no live container to compare); `cargo deny`: advisories, bans, licenses and sources ok; step 10 printed its no-token warning and the gate went on; rerun after repair cycle 1, rc 0 again (138 quality-tool tests). **CI: not yet proven** (`Full gate (Ubuntu)`, the guard job on Python 3.9 and 3.12, and the new `Advisory audit (weekly)` job all wait for the pull request).
- [x] **Scrap Sweep:** the scratch copies for the two red runs and the eight mutants removed; the gate's output kept in the session's scratchpad, outside the repository; nothing else to remove.
- [x] **Reviewed per `REVIEW.md`:** the `verifier`'s first pass FAIL, the repair above, the follow-up pass PASS. No Important finding open; the nits fixed in place or recorded in §4.
- [x] **Lesson loop:** N/A (no rule broken, no repeated mistake).
- [x] **Knowledge layer:** the threat model (T8, T9, §6, §9), the build procedure's weekly loop, AGENTS.md's gate list and the register's two status lines, in this change.
- [x] **Commit message explains why; record committed with the change:** yes, one commit with the change and this record, then the close-out commit; on the owner's word of 2026-10-21, "Yes, if the follow-up passes".

## Skipped items — visible, never silent

- **Full gate in CI**, the guard job on Python 3.9 and 3.12, and the `Advisory audit (weekly)` job on the pull request: not yet proven; they run once the owner opens the pull request. Owner: Henry.
- **The age check with a real token**: not run here (the sandbox has none); CI's gate on the pull request is its first real run, and until the first scheduled run on `main` it will warn "no completed scheduled or dispatched run", the expected first state. The nine-day-old run named in "Done when" was therefore shown through the test fixture and the mutants, not through GitHub (the verifier's nit 5).

## Evidence log

All runs 2026-10-21 on the owner's machine, in Claude Code's sandbox, Python 3.14.4.

```
# OSV API probes (sandbox allowance for api.osv.dev, one command each)
POST /v1/query {"package":{"name":"rustls-webpki","ecosystem":"crates.io"},"version":"0.103.15"}
  -> 1 vuln: RUSTSEC-2026-0382, aliases CVE-2026-111943, GO-2026-6809, RUSTSEC-2026-0381, RUSTSEC-2026-0383
POST /v1/querybatch {"queries":[{actions/checkout 7.0.1, "GitHub Actions"},{tokio 1.53.2, crates.io}]}
  -> {"results":[{},{}]}
POST /v1/query {"package":{"name":"tj-actions/changed-files","ecosystem":"GitHub Actions"},"version":"45.0.0"}   -> {}
POST /v1/query {... "version":"v45.0.0"}                                                                      -> {}
POST /v1/query {"package":{"name":"tj-actions/changed-files","ecosystem":"GitHub Actions"}}
  -> 2 vulns: GHSA-mcph-m25j-8j63 (events introduced "0", fixed "41"),
              GHSA-mrrh-fwg8-r2c3 (events introduced "0", fixed "46.0.1")
POST /v1/query {"commit":"3d3c42e5aac5ba805825da76410c181273ba90b1"}                                          -> {}
GET https://api.github.com/repos/rikuripi/rikurinode (no token)                                              -> 404 (private)

# the change
$ python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'          -> Ran 132 tests, OK
  test_osv_audit.py 28 OK; test_advisory_audit_age.py 14 OK; test_workflows.py 8 OK
$ shellcheck --severity=style scripts/quality/*.sh scripts/quality/hooks/* scripts/cargo.sh      -> rc 0
$ python3 scripts/quality/repo_hygiene.py .   (the 13 files staged by path)                        -> rc 0
$ git diff --check "$(git hash-object -t tree /dev/null)" HEAD && git diff HEAD --check           -> rc 0
$ python3 scripts/quality/osv_audit.py        (api.osv.dev allowed for this one command)
osv-audit: asked OSV about 129 crates and 2 actions (5 pins): 0 findings, 0 ignored, 0 not asked -> clean   -> rc 0
$ env -u GITHUB_TOKEN -u GH_TOKEN python3 scripts/quality/advisory_audit_age.py
full-gate: warning: advisory audit: no token (GITHUB_TOKEN or GH_TOKEN), so the last run was not checked    -> rc 0
$ GITHUB_TOKEN=not-a-token python3 scripts/quality/advisory_audit_age.py
full-gate: warning: advisory audit: HTTP 401 from GitHub listing the runs of advisory-audit.yml (...)         -> rc 0

# red runs: scratch copies of the lockfile, deny.toml and the workflows (discarded)
image.yml with `uses: actions/checkout@v7 # v7`:
osv-audit: could not audit: .../image.yml:38: `uses: actions/checkout@v7` is not pinned to a 40-hex commit  -> rc 2
ci.yml with its `# v7.0.1` comment removed:
osv-audit: could not audit: .../ci.yml:35: `uses: actions/checkout@3d3c42e5...` names no version in its comment (# vX.Y.Z) -> rc 2

# hand mutants: a copy of scripts/quality with one line changed, its tests run against it (discarded)
M1 osv_audit   fixed boundary inclusive (`<` -> `<=`)        killed: 3 failures of 28
M2 osv_audit   could-not-audit returns 0                      killed: 7 failures of 28
M3 osv_audit   ignore matches by id only, not by alias        killed: 1 failure of 28
M4 osv_audit   a floating tag accepted                        killed: 1 error of 28
M5 age         the eight-day limit doubled                    killed: 2 failures of 14
M6 age         a failed latest run passes                     killed: 2 failures of 14
M7 age         pull_request runs counted                      killed: 3 failures of 14
M8 age         the no-token line says ok                      killed: 2 failures of 14

# the full gate on the staged change (scripts/quality/full-gate.sh, in the sandbox)
== 1/10 pinned tools                                                   (cargo 1.98.1, cargo-deny 0.20.2, gitleaks 8.30.1, shellcheck 0.11.0)
== 2/10 AI-session guard ...                                           Ran 91 tests, OK
== 3/10 the quality tools' own tests ... and the OS image check's      Ran 132 tests, OK; Ran 54 tests, OK
== 4/10 .. 7/10 hygiene, shell lint, whitespace, secret scan           clean
== 8/10 Rust ...                                                       104 + 3 + 9 + 3 passed, 0 failed (two empty doc-test targets)
                                                                       safe-run: no live node containers found here; the start-time check had nothing to compare
== 9/10 Rust dependencies                                              advisories ok, bans ok, licenses ok, sources ok
== 10/10 the weekly advisory audit's last run on main                  full-gate: warning: advisory audit: no token (GITHUB_TOKEN or GH_TOKEN), so the last run was not checked
full-gate: all 10 steps passed                                         -> rc 0

# repair cycle 1 (the verifier's first pass: OA7 and AGE4 survived; T8 claimed a pull-request result)
$ python3 -m unittest discover -s scripts/quality/tests -p 'test_*.py'          -> Ran 138 tests, OK
  test_osv_audit.py 33 OK; test_advisory_audit_age.py 15 OK; test_workflows.py 8 OK
OA7  every ignore entry matches every finding (scratch copy)                     killed: 1 failure of 33
AGE4 only a "failure" conclusion warns (scratch copy)                            killed: 1 failure of 15
# the fake finding through the real entry point: a scratch copy with rustls-webpki set back to 0.103.15 (api.osv.dev allowed)
osv-audit: FINDING: crate rustls-webpki 0.103.15: RUSTSEC-2026-0382 (CVE-2026-111943, GO-2026-6809, RUSTSEC-2026-0381, RUSTSEC-2026-0383): Certificate verification may accept distrusted intermediates
osv-audit: asked OSV about 129 crates and 2 actions (5 pins): 1 findings, 0 ignored, 0 not asked -> FINDINGS   -> rc 1
# the same copy with `ignore = [ { id = "CVE-2026-111943", reason = "scratch: the red run" } ]` in deny.toml (the alias, not the RUSTSEC id)
osv-audit: ignored by deny.toml (CVE-2026-111943): crate rustls-webpki 0.103.15: RUSTSEC-2026-0382 (...)
osv-audit: asked OSV about 129 crates and 2 actions (5 pins): 0 findings, 1 ignored, 0 not asked -> clean      -> rc 0
# the full gate, rerun on the repaired change
Ran 91 tests, OK (guard); Ran 138 tests, OK (quality tools); Ran 54 tests, OK (image check); Rust suites and cargo deny as before
full-gate: all 10 steps passed                                         -> rc 0
```
