# Review instructions

How any review of a change to this repository is run: `/code-review`, the
`verifier` subagent's report, a human reviewer, a PR bot. Referenced from
AGENTS.md > Standard work. AGENTS.md > "Design rules" and "Security baseline"
are the judgement this review applies.

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
  Plan? Plus the rules only this repository has:
  - **Claims match evidence**: a record, document or README that says
    something works or passed without linked evidence is **Important**. Pass,
    Fail and Not yet proven stay distinct.
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
gate; claim something passed without evidence; or diverge from the approved
plan. Everything else is **Nit**. A change to a protected path (listed in
`.claude/hooks/guard-config.json`) always gets a written risk note in the
Build Record, finding or not.

## Cap the nits

At most five nits per review; summarise the rest as a count.

## Do not report

Build output and generated files, and what CI enforces once it has been
observed green (the full gate in `.github/workflows/ci.yml`).

## Separation of duties

The session that wrote a change does not approve it. Review findings are
evidence in the Build Record; the owner decides.
