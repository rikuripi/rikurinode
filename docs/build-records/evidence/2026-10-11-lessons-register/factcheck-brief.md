# Fact-check brief — lessons register

You are fact-checking part of `lessons-register.md` (in this scratchpad folder:
`/tmp/claude-1000/-home-junc-Rikuri-PI/a9a3c3c8-1aaa-42d0-ba54-21f1946de07e/scratchpad/`).
The register distils 475 lessons harvested from the 114 build records of the
previous repository into 107 requirements for a rebuilt Bitcoin/Lightning node.
It will be committed to a public-quality repository and audited, so every
factual claim must be supported by its source.

## Sources (read-only)
- The build records: `/home/junc/rikuri/rikurinode/docs/build-records/<record>.md`.
- The harvest: `lessons-all.json` (a JSON list; index 0 = first lesson). Fields:
  record, component, class, what_happened, root_cause, lesson, tripwire,
  evidence, owner_decision, applies_to_new_node, port_candidate, superseded_by.
- `reqs.txt`: each requirement's text with a `LESSONS:` line listing the lesson
  indices (0-based) merged into it.

## Hard rules
- `/home/junc/rikuri/rikurinode` is the checkout where a LIVE mainnet node runs.
  READ ONLY, by absolute path: `grep`, `sed -n`, the Read tool, `git -C … show/log/ls-tree`.
  Never `cd` into it, never run a script, test, docker, systemctl, lncli, bitcoin-cli
  or anything else there. Never write anything there.
- Never read secret files (`.env`, `*.macaroon`, `wallet.db`, `channel.backup`,
  cookies, keys, `bitcoin.conf`, `lnd.conf`, `tapd.conf`).
- Do not edit `lessons-register.md`. Write your findings ONLY to the file named
  in your task.
- Be economical: do not read whole records. For each claim, `grep -n` the cited
  record for its key words or numbers and read the few lines around the hits.

## What to check, for each requirement in your slice
1. **Why**: split it into its factual claims (each event, number, quoted text,
   component, date, outcome). For each claim, find it in the cited record (the
   record in parentheses after it). Verdict per claim: SUPPORTED, WRONG (quote
   what the record actually says, and give the corrected wording), or NOT FOUND
   (you searched and could not find it — say what you searched for). Numbers must
   match exactly ("12 of 16" vs the record's "12 of 14" is WRONG).
2. **Rule** and **Tripwire**: they may generalise, but must not claim the old
   repository did or proved something it did not. Flag any sentence that states
   an old-repository fact (e.g. "the old node had X", "was tested by Y") that the
   lessons for this requirement (`LESSONS:` indices in `reqs.txt`) do not support.
3. **Owner** lines: the quote must match the lesson's `owner_decision` field and,
   for words in double quotes, the record. Flag paraphrase presented as a quote.
4. **Port** lines: the path exists (`git -C /home/junc/rikuri/rikurinode ls-tree -r --name-only HEAD`)
   and the stated test exists; the one-line "what it proves"/verdict is consistent
   with the lesson's `port_candidate` field.
5. **Status words**: "superseded", "still open", "never", "only", "every", "0 channels"
   and similar absolutes need explicit support.

## Output
Write a Markdown file with one section per requirement you checked:

    ## EVID-01
    - SUPPORTED: <claim> — <record>:<line>
    - WRONG: <claim> — record says: "<exact words>" (<record>:<line>) — correct to: "<new wording>"
    - NOT FOUND: <claim> — searched <record> for <terms>
    - OVERCLAIM (Rule/Tripwire): <sentence> — <why>

Then a final summary line: `TOTAL: <n> claims checked, <w> wrong, <nf> not found, <o> overclaims`.
List only WRONG / NOT FOUND / OVERCLAIM lines in full; for SUPPORTED claims, one
line each is enough. Your final reply: the summary line and every WRONG,
NOT FOUND and OVERCLAIM item (they are what matters), nothing else.
