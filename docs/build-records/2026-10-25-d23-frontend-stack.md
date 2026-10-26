# Build Record — The frontend's stack: framework, charts, live data, types, embedding (D23)

| | |
|---|---|
| **Date** | 2026-10-25 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `claude/rebuild-architecture-plan-25caf5`, in the worktree `/Users/hchome/rikurinode/.claude/worktrees/rebuild-architecture-plan-25caf5` (made by the app for this session) |
| **Commits** | one commit on `claude/rebuild-architecture-plan-25caf5` holding the change and this record (its hash is in the pull request) |
| **Status** | Edits verified (verifier FAIL, repaired, follow-up PASS); committed and opened as a pull request on the owner's word (2026-10-25, "Documentation only; open a PR."); CI `Full gate (Ubuntu)` to be read on the pull request |
| **Change type** | ops (plan amendment; documentation only) |

## Task Contract

1. **Outcome:** the plan records the frontend's stack as the owner chose it, so the first UI slice starts from settled choices instead of reopening them.
2. **Scope:** `docs/architecture/platform-plan.md`: the status paragraph's counts, a row D23 in §7, and §9's sources. Tier: **high-risk**, because D23 sets how the live stream authenticates and how the content security policy is built (a trust boundary, BUILD-PROCEDURE "Risk tiers"); documentation only. **Not included:** any code; adopting a crate or npm package (each still gets AGENTS.md §2's inspection when the UI slice adds it); the design system; the threat model (its stage 8 row already requires the CSP and session flags; D23 makes them concrete without changing them); stage 8's scope; D15's text.
3. **Done when:** D23 is recorded as decided by the owner with its options and costs; the status paragraph counts it; §9 carries today's sources; no other decided text changes; `git diff --check` clean; `repo_hygiene.py` exits 0; the new links resolve; one `verifier` pass has no Important finding; the pull request's `Full gate (Ubuntu)` is green.
4. **Authority:** edit the plan and this record; read the repository and public web pages; commit on this branch, push it and open one pull request (owner, 2026-10-25, "Documentation only; open a PR."). No merge. Nothing running touched. Independent check required (high-risk).
5. **Limits:** one task; two repair cycles; two review rounds. Budget: none configured; report what was used.

## 0. Intent

- [x] **Problem, in the owner's words:** "Svelte is fine with plain Vite. Keep Lightweight Charts as is. Ok with Server-sent events with those 4 rules. [...] Embedding: whichever is more secure or reliable. If don't need python. that's fine with me." (2026-10-25); then, on the type generator, "Yes. Write a Task Contract and record D22 in the platform plan: Svelte with plain Vite, Lightweight Charts, SSE with the four rules, ts-rs for the types, the UI embedded in the binary, no Python. Documentation only; open a PR."
- [x] **Outcome:** as the Task Contract.
- [x] **Who/what it affects:** the plan's decision table; the first UI slice and stage 8 when they are built; nothing running.
- [x] **Open questions:** the number. The owner said D22, but D22 is taken (the boot-cause record and UPS, 2026-10-21), so this is recorded as D23; the content is the owner's. Which embedding crate: left to the UI slice's inspection; D23 sets only the rule it must meet.
- [x] **Owner approved the intent:** the messages above.

## 0b. Spec

- [x] **Requirements:** each of the six choices recorded with its alternatives and their costs; the four SSE rules stated as rules; the owner's words quoted; nothing that D15 decided restated as new or changed.
- [x] **Design:** one row D23 in §7, beside D15, that names D15 as what it refines; sources under a dated heading in §9. Rejected: an ADR (a choice of libraries inside D15's shape is "a small implementation choice" by AGENTS.md §8, and D22 set the precedent of a row and a record); editing D15's row (decided text stays as decided).
- [x] **Policy applied:** pinning (every package pinned when adopted); third-party code inspected before adoption (AGENTS.md §2); "nothing important fails silently" and "runtime truth over declared truth" (the stale-stream rule; the UI and backend as one file); EVID-05 (no third party learns from the browser that the node exists).
- [x] **Flagged concerns:** an EventSource cannot send an `Authorization` header, and the common workaround is a token in the URL; D23 forbids that and names the session cookie instead. The control plane serves HTTP/1.1 only (`axum` and `hyper` features `http1`, `control-plane/Cargo.toml`), so the six-connection limit applies.

## 1. Plan

- [x] **One sentence:** add D23 to §7, count it in the status paragraph and list its sources in §9.
- [x] **Blast radius:** one documentation file; nothing irreversible.
- [x] **Current behaviour characterized:** read this session: the status paragraph, D15, D18, D22, the text after §7's table, §9's last headings, ADR 0005, ADR 0010, `control-plane/Cargo.toml`; no mention of Python in the plan, the assistant plan or the ADRs (`grep -i python`, no match).
- [x] **Files and order:** this record, the plan, checks, verifier, commit, pull request.
- [x] **Risks:** a stale count in the status paragraph; a claim about outside software without a source; D23 reading as if it changed D15.
- [x] **Verification defined up front:** the Task Contract's "Done when".

## 2. Build

- [x] Edits made: the status paragraph's counts, lists and dates; a row D23; §9's 2026-10-25 block. No other row changed.
- [x] **Security question answered:** D23 sets design rules for authentication of the live stream (the session cookie, same origin, never a token in the URL) and the CSP (scripts allowed by hash from the embedded build). Nothing is built, so nothing is proven; stage 8's tests (the CSP and session flags) carry them.

## 3. Debug

- N/A

## 4. Verify

- [x] Checks: see the Evidence log.
- [x] Independent verification: first `verifier` pass **FAIL** on one Important finding: the row said ts-rs adds "nothing to the binary", but its README adds it under `[dependencies]` with an unconditional derive, so no source supported the claim. Six nits with it: the licence needs the NOTICE attribution as well as the link; one stream per tab still meets the six-connection limit, which counts across all tabs; specta's release candidates began 2023-07-17, not 2024; unsourced comparisons (Svelte's size, React's runtime, utoipa's npm generator, a CSP by script hash, which external lazy-loaded chunks make awkward) and "no Python" read as covering the repository's own tools; EVID-04, not EVID-05, for the node's own status; "every release is a new binary" was not what D12 says. All corrected in repair cycle 1 (of two): ts-rs is now a rule the UI slice proves (dev-dependency, `cfg_attr(test, ...)`, the dependency tree shown); one stream per browser shared by its tabs, with its cost; `script-src` with no inline script and no outside origin. Follow-up pass **PASS** (corrections only), no new Important finding.

## 5. Close Out

- [ ] Full gate: CI `Full gate (Ubuntu)` on the pull request (read at close-out).
- [x] Review and commit: verifier FAIL, repaired, follow-up PASS; committed and opened as a pull request on the owner's word.

## Skipped items — visible, never silent

- Follow-up nit (two parentheticals back to back in the "No Python" sentence) merged into one after the second review round, wording only; it has no verifier pass (AGENTS.md §5 allows no third round); CI's full gate covers the documentation checks.
- Full gate: not run locally (documentation only, AGENTS.md §5); CI runs it on the pull request.
- Guard tests: not required (`.claude/` unchanged); `safe-run.sh` refuses on this Mac ("namespace isolation unavailable here").
- Pre-commit hook: as in `2026-10-21-boot-cause-and-ups.md`, not installed in this clone; its whitespace and hygiene checks were run by hand on the staged change (Evidence log); the secret scan runs in CI.

## Evidence log

Sources read 2026-10-25 (public, read-only):

- ts-rs: [README](https://github.com/Aleph-Alpha/ts-rs) (`#[ts(export)]` "generates a test which writes the bindings"; `serde-compat` "enabled by default"; MIT); [crates.io](https://crates.io/crates/ts-rs) (12.0.1, 2026-01-31, the newest).
- specta: [crates.io](https://crates.io/crates/specta) (newest stable 1.0.5; 2.0.0 in release candidates since at least 2024-08-04, rc.27 on 2026-10-21).
- Lightweight Charts: [README, License](https://github.com/tradingview/lightweight-charts) (Apache-2.0; "requires specifying TradingView as the product creator"; the `attributionLogo` option satisfies the link requirement).
- Svelte: [Getting started](https://svelte.dev/docs/svelte/getting-started) ("use Svelte directly with Vite via vite-plugin-svelte"; a separate router is likely needed).
- EventSource: [MDN](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) (without HTTP/2, six connections "per browser + domain"; the constructor's only option is credentials mode); [WHATWG HTML, server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html) (`Last-Event-ID` sent on reconnection when the last event ID is not empty).

Checks, 2026-10-25, on the uncommitted edit (documentation only):

- `git diff --check`: clean, after the first edit, after repair 1 and after the wording nit.
- `python3 scripts/quality/repo_hygiene.py .`: exit 0 each time.
- The seven new URLs in §9: HTTP 200 (curl -L); the two crates.io pages answer 404 to a plain request and 200 with `Accept: text/html`, and their API answers 200.
- Privacy slip: two requests to the crates.io API carried the owner's email address in the User-Agent header, unasked; reported to the owner the same turn; no later request carries it.
- Budget used: one session; one verifier pass and one follow-up; one repair cycle.
