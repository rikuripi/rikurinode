# Review instructions

How any review of a change to this repository is run: `/code-review`, the
`verifier` subagent's report, a human reviewer, a PR bot. This is the review
pass [AGENTS.md](AGENTS.md) §5 requires: one pass after tests, then at most
one follow-up on corrected findings; a review that would need a third round
ends in `NEEDS_OWNER_DECISION` instead. AGENTS.md > "Design rules" and
"Security baseline" are the judgement this review applies. The change's risk
tier (routine or high-risk), named in its Task Contract, sets how deep the
review goes
([BUILD-PROCEDURE.md, "Risk tiers"](.agents/workflows/BUILD-PROCEDURE.md#risk-tiers)).

## Passes (run all three; tag every finding with its pass)

- **Bugs**: logic errors, edge cases, regressions, races, error paths that
  swallow a failure, non-deterministic tests (wall clock, ordering, shared
  temporary paths). A fallback that reports success when the primary path
  failed.
- **Security & funds**: for every change ask **"how could untrusted input — a
  peer, an invoice, a web request, a retrieved help page, model or tool output
  — use this to move funds, reach a key, or gain authority?"** Review the
  boundary, not just the diffed lines: a key, seed, macaroon or credential
  reaching a log, a response, or an agent's context; a payment or channel
  action without the owner's approval path; a value from a request reaching a
  shell; network access beyond the allow-list; a restore that could bring
  back an old channel state.
- **Compliance**: does the diff match the Build Record's Intent, Spec and
  Plan, and its Task Contract's Scope (AGENTS.md §3)? Work outside the Task
  Contract is a finding. Plus the rules only this repository has:
  - **Claims match evidence**: a record, document or README that claims a
    gate or stage result, a security or funds property, data integrity, or
    completion without linked evidence is **Important**; other imprecise
    wording is a nit. Pass, Fail and Not yet proven stay distinct.
  - **Never in git** (AGENTS.md): no log, runtime state, secret, model or
    unpinned image; the hygiene check enforces it.
  - The old version is removed in the same change: no dead code, no orphan
    files.
  - Help pages and runbooks updated with any user-visible behaviour change.
  - A behaviour-changing default not put to the owner as an explicit, costed,
    reversible choice is **Important**.

## What "Important" means here

Reserve **Important** for findings that can lose or lock funds; expose a key,
seed, macaroon or credential; let untrusted input gain authority or reach a
shell; let an update downgrade a node or roll back data; disable or weaken a
gate; make one of the claims above without evidence; or diverge from the
approved plan. Two test gaps are Important too: a test the change's own
"Done when" depends on is missing, or, in high-risk code, a mutant of the
changed lines survives in a refusal, validation, recovery, funds or integrity
check. Everything else is **Nit**. A change to a protected path (listed in
`.claude/hooks/guard-config.json`) always gets a written risk note in the
Build Record, finding or not.

A review fails only on an Important finding. Nits never fail it and never
start another round: they are fixed in place or listed in the Build Record.

## Cap the nits

At most five nits per review; summarise the rest as a count. Surviving
mutants rated nits are listed in full in the evidence and count as one nit;
each surviving mutant rated Important is its own finding.

## The follow-up pass

It checks the corrections to the first pass's findings and reruns that
pass's mutation scope; it does not search for new findings. A new nit it
happens to see is listed for the backlog. A new Important finding it happens
to see is reported, and the task ends in `NEEDS_OWNER_DECISION`: the owner
decides whether it is fixed now, as its own task, or recorded as debt.

## Do not report

Build output and generated files, dated Build Records unless the change
contradicts them, and what CI enforces once it has been observed green (the
guard tests in `.github/workflows/claude-guard.yml` and the full gate in
`ci.yml`).

## Separation of duties

The session that wrote a change does not approve it. Review findings are
evidence in the Build Record; the owner decides. A review does not start
work: findings outside the task go to the backlog or the owner (AGENTS.md
§3), and the independent reviewer never fixes.
