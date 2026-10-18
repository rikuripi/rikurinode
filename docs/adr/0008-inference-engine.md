# ADR 0008 — The inference engine is llama.cpp's own server image, pinned by digest

| | |
|---|---|
| **Status** | Accepted — owner, 2026-10-18 ("1. use llama.cpp"; record `docs/build-records/2026-10-18-assistant-plan.md`) |
| **Decision** | F1 of `docs/architecture/assistant-plan.md`; D16 of `docs/architecture/platform-plan.md` |
| **Supersedes** | Nothing in this repository. The previous node's fork, Lean_llama.cpp, was that repository's choice, never this one's |
| **Beside it** | ADR 0002 (the Rust control plane, the engine's only client), ADR 0006 (release sets bound to the image: the engine's image is one of the set), ADR 0007 (rootful, a range per container: the engine's container gets its own) |

## Context

The previous node served its models with Lean_llama.cpp, a fork of
ik_llama.cpp (itself a performance fork of llama.cpp) that adds TurboQuant
KV-cache types TQ2, TQ3 and TQ4. Read on 2026-10-18 at the fork's HEAD
`1b37afab` (2026-07-21): its upstream snapshot is from 2026-07-17; its own
work since is 22 commits, about 13,800 added lines in 89 files, mostly ggml
kernels and flash-attention paths; no remote for ik_llama.cpp is configured,
so its drift from upstream is not measured. Its own executive summary of
July 2026 recommends TQ4 and then concludes: "KV quantization is no longer
the binding constraint on edge inference. Weight quantization is the next
lever."

The node agreed in practice. Its model registry ran Gemma-4-E2B with a plain
q8_0 cache ("E2B does NOT use TQ"); its router benchmark of 2026-04-19 notes
"KV quant doesn't help (it's a memory/precision lever, not a speed lever)"
and could not run Gemma-4-E4B because the fork's build did not know the
architecture; its bake-off of 2026-07-21 found the fork's flash-attention
setting architecture-dependent — the wrong setting garbles output — and
called that "deployment-critical".

The node's workload is a 2B to 4B model at 2k to 8k context, batch one, on
a CPU. At 2k context E2B's KV cache is 10 MiB against 3 GB of weights. The
binding constraints are weight memory, CPU speed on four efficiency cores,
and hallucination; none of them is a KV-cache problem.

Upstream, TurboQuant is not in mainline llama.cpp: of two status pages read
today, the older (verified in April) had the pull request still open and the
newer reports it closed unmerged as of July 2026; only community forks carry
it. Two October 2026 papers on query-adaptive and
budget-allocated KV quantization (ReadKV, MultiAlloc) are GPU research
prototypes; neither ships in an engine the node could pin. llama.cpp
publishes official container images at `ghcr.io/ggml-org/llama.cpp` —
`server` (llama-server only), `light` and `full`, CPU builds for
linux/amd64 and linux/arm64 — and its release page showed v0.7.0 on
2026-10-15.

The design rules bind: every image pinned by digest inside one tested set
(ADR 0006); runtime truth; nothing fails silently.

## Decision

- **The engine is llama.cpp's official `server` image, CPU build, from
  `ghcr.io/ggml-org/llama.cpp`, pinned by digest inside the release set**
  like bitcoind, LND and Tor (ADR 0006), in its own user-ID range (ADR
  0007), on the private network with a fixed address (D14), reachable by the
  control plane only. It has no network of its own and never faces the
  owner's browser or the internet.
- **The model is a separate artefact.** The release set names a GGUF file
  by SHA-256. It is fetched to a temporary name, verified, moved atomically,
  verified again on load; a failed verification is a health finding and the
  assistant reports itself unavailable (AI-05). Which model runs is decided
  in stage 8 from the measurement on the N150 (assistant plan, F4 and §3.9).
- **The boundary is the engine's OpenAI-compatible HTTP interface with
  grammar-constrained JSON output.** The control plane depends on that
  interface and nothing else: no fork's flags, types or cache formats.
  Swapping the engine or the model is a release, gated like any other.
- **Lean_llama.cpp, LeanKV and LeanInfer leave the node's path.** They stay
  research-tier repositories under the owner's standing rules. Nothing in
  this repository builds, depends on or cites them except as history.
- **An engine image enters a release only with the evaluation gate's result
  for that engine-and-model pair** (assistant plan, contract C), and a
  smoke subset runs on the node after every model load, so a garbling class
  of failure like the fork's flash-attention trap is caught before an owner
  sees it.

## Consequences

- Given up: TQ4's roughly 3.6× K-cache compression and ik_llama.cpp's faster
  CPU kernels. Kept against it: at the node's context the cache is tens of
  MiB, and speed is measured in stage 8 with ik_llama.cpp as the fallback
  (below).
- Gone: rebasing a 13,800-line fork on a moving upstream, model-architecture
  lag, the flash-attention trap, and a build pipeline of our own for the
  engine.
- Gained: upstream releases with container images for both architectures
  the node targets, and the same pin-by-digest path as every other
  container.
- The engine's memory and CPU join PLAT-04's per-service budgets; the model's
  weights are the dominant line (assistant plan, §3.9).
- Supply chain: the image is a third party's binary. It enters the set by
  digest after the gate, runs without network, holds no secret, and the
  control plane treats its output as data (AGENTS.md > Security baseline).

## Rejected

- **Keep Lean_llama.cpp.** A rebase every few weeks, model-architecture lag
  (the E4B case), the flash-attention trap, and the node's funds safety
  resting on a fork with one part-time maintainer.
- **ik_llama.cpp.** Faster CPU kernels; one maintainer; no release images
  found to pin on 2026-10-18. It is the fallback to measure in stage 8 only
  if llama.cpp misses the speed budget on the N150; if chosen then, it is
  built in CI from a pinned commit and enters the set as an image of our own.
- **A community TurboQuant fork of llama.cpp.** The same maintenance
  exposure as our own fork, with less knowledge of it.
- **Fedora's packaged llama.cpp inside the OS image.** Ties the engine's
  version to the image build and Fedora's packaging cadence; whether Fedora
  45 ships it was not checked. Revisit only if the container path proves
  heavy.

## Sources (read 2026-10-18)

- The fork, `/home/junc/Lean_llama.cpp` at `1b37afab`: `README.md`;
  `docs/leankv-EXECUTIVE-SUMMARY-2026-07.md`; `docs/RESULTS.md`; `git log`
  and `git remote -v`.
- The previous repository, `/home/junc/rikuri/rikurinode` at `3bbbe392`:
  `config/model-registry.json`; `docs/specs/ROUTER-MODEL-BENCHMARK-2026-04-19.md`;
  `docs/node-deeptier-bakeoff-2026-07.md`.
- [llama.cpp container images](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md):
  `ghcr.io/ggml-org/llama.cpp`, variants `full`, `light`, `server`, CPU
  builds for linux/amd64 and linux/arm64.
- [llama.cpp latest release](https://github.com/ggml-org/llama.cpp/releases/latest):
  v0.7.0, 2026-10-15.
- TurboQuant's upstream status: [turbo-quant.com](https://turbo-quant.com/turboquant-llama-cpp);
  [vucense.com](https://vucense.com/dev-corner/turboquant-llama-cpp-install-benchmark-2026/).
- [ReadKV, arXiv 2610.11245](https://arxiv.org/abs/2610.11245);
  [MultiAlloc, arXiv 2610.18642](https://arxiv.org/abs/2610.18642).
