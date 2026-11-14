# Build Record — a suggestion that runs out of time says it could not check

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/suggest-limit-503`, from `main` at `fd157d9`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `57db7c0` (contract), `d1ed28a` (red), `cdf36e0` (fix); merged as `5fc7da6` (#104) |
| **Status** | DONE |
| **Change type** | fix |

## Intent: the owner's words

- "Next" (2026-11-14), answering the proposed task: "When a suggestion runs out its 30 seconds, should the page say 'could not check' (a 503) instead of 'no free name'? … It would change the route's behaviour, so it would be its own high-risk task."
- Found by the verifier of `docs/build-records/2026-11-14-suggest-lock-tests.md` (its nit 1).

## Why

- `hostname::suggest` ends `tokio::time::timeout(limit, first_free).await.unwrap_or(Ok(None))` (`src/hostname.rs:319-321`). When the 30 s `SUGGEST_LIMIT` runs out, the route answers 200 `{"name": null}`.
- The page reads `null` as "every name is taken" (`ui/src/secure/Name.svelte:54`) and shows `name.none_free`: "Every name from rikuri01 to rikuri99 is in use on your network." After a timeout that is untrue: the node does not know.
- This was 5c.4b-2's design ("`{"name": null}` when all are taken or the time limit runs out", `docs/build-records/2026-11-13-5c4b2-naming-page.md`, Task Contract). This task replaces that one clause, by the owner's choice above. Its other rule stays: "503 when resolved cannot be asked: never a guess." A timeout is that case.

## Task Contract

1. **Outcome:** when the suggestion runs out of time, the owner is told the node could not check ("You can still type one"), not that every name is taken.
2. **Scope:** high-risk: it changes a signed-in route's answers.
   - `control-plane/crates/rikuri-control/src/hostname.rs`: `suggest` gives `Err` when the limit runs out, so the route's existing `Err` arm answers 503 "the node could not check which names are free" and logs why. Its doc comment says so. `Ok(None)` stays only for every name taken.
   - Its unit test `the_limit_ends_the_suggestion_with_none` becomes `the_limit_ends_the_suggestion_unchecked`, expecting `Err`. It is changed, not added, because it pinned the old behaviour; that is the reason for the test change, and it is the red.
   - `README.md`, only if it describes this answer (it does not today).
   - **Not included:**
     - the page: it already shows `name.check_failed` for any answer but a suggestion;
     - the limit's value (30 s), the per-lookup 10 s timeout, the lock;
     - an HTTP-level test of the limit: it would wait 30 s; the `Err` → 503 mapping is already tested by `a_suggestion_resolved_cannot_give_is_refused`.
3. **Done when:**
   - The changed unit test is seen failing in CI on the current code (a red commit, pushed alone), then passing on the fix.
   - The full gate, the mutants run and the OS image pass in CI.
   - The verifier passes, with hand mutations: `unwrap_or(Ok(None))` restored; the timeout mapped to `Ok(Some(_))`; the limit ignored.
4. **Authority:** these files. On the Mac, `scripts/cargo.sh` fmt, clippy and check; the Rust tests run in CI. Commit, push this branch and a draft PR. The owner merges.
5. **Limits:** one task; two repair cycles; two review rounds. No budget is configured.

## Evidence log

### Red (the current code)

- `src/hostname.rs`: `the_limit_ends_the_suggestion_with_none` is renamed `the_limit_ends_the_suggestion_unchecked`; `assert_eq!(got, Ok(None))` becomes `assert!(got.is_err())`. Its other checks (fewer than 4 names asked, done within 2 s) stay.
- **Expected on the current code:** `got` is `Ok(None)`, so the assertion fails.
- On the Mac: fmt and clippy (all targets, `-D warnings`) are clean. Pushed alone, so CI shows the red before the fix.

### CI on `d1ed28a` (the red): Fail, as expected

- `Full gate (Ubuntu)`, [run 43562461921](https://github.com/rikuripi/rikurinode/actions/runs/43562461921): `test hostname::tests::the_limit_ends_the_suggestion_unchecked ... FAILED`, panicked at `src/hostname.rs:1178:9` with `Ok(None)`; `test result: FAILED. 173 passed; 1 failed`. It is the only failing test result in the log.
- Rust mutants [43562461969](https://github.com/rikuripi/rikurinode/actions/runs/43562461969) and the OS image [43562461920](https://github.com/rikuripi/rikurinode/actions/runs/43562461920) passed.

### Fix

- `src/hostname.rs`, `suggest`: `.unwrap_or(Ok(None))` becomes `.unwrap_or_else(|_| Err(format!("no answer within {limit:?}")))`. The route's `Err` arm answers 503 "the node could not check which names are free" and logs the reason. The doc comment says `Ok(None)` is only for every name taken.
- `README.md`: one sentence: without an answer within 30 s, 503, and the page asks for a name.
- No test changed after red.
- On the Mac: fmt and clippy (all targets, `-D warnings`) are clean.

### CI on `cdf36e0` (the fix): Pass

- `Full gate (Ubuntu)`, [run 43563632280](https://github.com/rikuripi/rikurinode/actions/runs/43563632280): `the_limit_ends_the_suggestion_unchecked ... ok`, `every_name_taken_is_no_suggestion ... ok`; `174 passed; 0 failed`.
- Rust mutants, [run 43563632279](https://github.com/rikuripi/rikurinode/actions/runs/43563632279): `2 mutants tested … 1 caught, 1 unviable`. Caught: `suggest` replaced with `Ok(None)`. Unviable: `Ok(Some(Default::default()))`, since `NodeName` has no `Default`.
- OS image, [run 43563632282](https://github.com/rikuripi/rikurinode/actions/runs/43563632282): passed.
- The owner merged #104 at `cdf36e0` (as `5fc7da6`) before the verifier ran.

### The verifier, at `cdf36e0`: PASS

- `Ok(None)` now comes only from every candidate taken. The timeout goes through the route's `Err` arm, and the guard is still dropped there (`a_suggestion_resolved_cannot_give_is_refused` asks twice).
- The test is unchanged between the red and the fix. It is not too loose: its fixture has no unknown answer, so the timeout is the only possible `Err`.
- The page: `readSuggestion` expects 200, so a 503 shows `name.check_failed` (`Name.svelte:53`). `ui/tests/owner.spec.ts:595` already covers a 503 with this route's words. No UI test assumed `null` on a timeout.
- **Hand mutations, reasoned:**
  | Mutant | Killed by |
  |---|---|
  | `unwrap_or(Ok(None))` restored | `the_limit_ends_the_suggestion_unchecked` (seen red) |
  | the timeout gives `Ok(Some(_))` | the same test |
  | the limit ignored | the same test (`is_err`, `asked.len() < 4`, the 2 s bound) |
  | every name taken gives `Err` | `every_name_taken_is_no_suggestion`, and the route test `every_name_taken_suggests_none` |
- **Findings:** no Important finding. Nits:
  1. this close-out (answered here);
  2. Scope said the README would change "only if it describes this answer (it does not today)". It gained a sentence anyway, under AGENTS.md's Knowledge layer rule: a user-visible change carries its description;
  3. that sentence's "it" read as the refused request; reworded here to "A suggestion without an answer within 30 s gets 503";
  4. the route logs "resolved could not say which names are free" for a timeout too; the `why` field ("no answer within 30s") tells them apart;
  5. the timeout test could also assert the "no answer within" text.
- **Not yet proven:** the live node's container start times were not compared (the Mac sees no node); nothing was run against it.

### Close-out

- **Done when:** met. The changed test was red in CI, then green; the gate, the mutants run (1 caught, 0 missed) and the OS image passed; the verifier passed.
- **Repairs:** 0. Review rounds: 1.
- **Used:** no budget is configured. Two CI pushes and one verifier pass.
- **Backlog, not started:** nits 4 and 5.
