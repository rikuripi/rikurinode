# Build Record — the platform and architecture plan

| | |
|---|---|
| **Date** | 2026-10-11 |
| **Author / session** | Claude Code (Opus 5.5); owner Henry |
| **Branch** | docs/platform-plan (2026-10-11, on the pre-GitHub root); re-landed onto `main` 5630ea0 as docs/plan-and-lessons (2026-10-12; its merge Not yet proven) |
| **Commits** | 1ec05a7 on the old root; on `main`: its cherry-pick and the D5 commit of the pull request that adds this line |
| **Status** | COMPLETE — verifier round 9 PASS; D2, D3 and D5 decided (D5 on 2026-10-12, ADR 0003), D1 and D4 open; re-landed onto `main` 5630ea0 (branch docs/plan-and-lessons) with the full gate green; the branch's one final check FAIL on wording only, corrected without another round (the owner's stop rule); CI and the owner's merge Not yet proven when this line was written |
| **Change type** | documentation (plan) |

## 0. Intent
- [x] Problem: the node is rebuilt on Fedora IoT, an Intel N150 full node and
      a Raspberry Pi 5 pruned node (owner, 2026-10-10), and nothing yet says
      how: which images, how updates and rollback work, what protects funds,
      in which order the node is built, and what the owner must decide.
- [x] Outcome: `docs/architecture/platform-plan.md`, a plan a new session
      could build from, with every behaviour-changing choice exposed as an
      owner decision with its cost.
- [x] Owner approved: "Go ahead with step 1-4" (2026-10-11); step 3 is this
      plan.

## 0b. Spec
- [x] Requirements: the owner's priorities (security and reliability, then
      ease of use and maintenance, no command line for a novice, backend
      before frontend, evidence over claims); the previous repository's
      lessons register (gaps G1–G11 and the platform themes); facts about
      outside software checked on the day and sourced.
- [x] Design: one document — the facts, the two machines, three safety
      layers, the software, the LND test plan, owner decisions, stages,
      sources. Rejected: one ADR per decision now (the decisions are not made
      yet; each becomes an ADR when the owner chooses — D2 and D3 did in
      round 4: `docs/adr/0001-podman-quadlet.md`,
      `docs/adr/0002-rust-control-plane.md`).
- [x] Policy applied: "a choice not exposed is not a choice" — four
      decisions (the Pi 5, the container runtime, the backend language, the
      first mainnet amount; a fifth, rootless or rootful, added in round 4)
      were put open, each with options, costs and a
      recommendation; the owner's earlier "Docker first, then Podman" is one
      of the options, not silently replaced.
- [x] Flagged concern: the Pi 5 cannot run Fedora IoT today — routed to the
      owner as decision D1.

## 1. Plan
- [x] Files: `docs/architecture/platform-plan.md`, this record, `README.md`
      (a pointer); from round 4, `docs/adr/0001-podman-quadlet.md` and
      `docs/adr/0002-rust-control-plane.md`.
- [x] I will know this works when: every fact in §2 of the plan has a source
      read today; every link resolves to the page cited; the decisions (four,
      five from round 4) have options, costs and a recommendation; the stages
      name a drill each; `git diff --check` and the full gate pass.

## 2. Build
- [x] Written from searches and pages read on 2026-10-11 (sources in the
      plan's §9). Facts that changed the plan: no Fedora IoT or bootc image
      for the Pi 5, microSD-only boot and no fan control there; an open
      greenboot bug report that stops the first rollback after installing
      Fedora IoT 44 from its stock image; `bootc-image-builder`'s sources
      moved into `image-builder`; LND 0.21.4-beta; Bitcoin Core 31.1 with
      32.0 still in release candidates; Tor 0.4.8 out of support since
      2026-09-01. (First written "archived": wrong — see Verify.)

## 3. Debug
- N/A — no defect.

## 4. Verify
- [x] All 20 links (21 after round 2, 28 after round 5) answered HTTP 200
      (`curl -L`, 2026-10-11); the Fedora docs page is a bot check, so it is
      cited but not relied on.
- [x] **Verifier, round 1: FAIL.** Supported by their sources: Fedora 45's
      dates, the IoT bootc base images, the IoT 44 build failure, the
      greenboot report, the Pi 5 limits as of the March images, Bitcoin
      Core's releases and policy, LND's releases, Tor 0.4.8's end, Podman's
      rollback and Podman 6, OpenShell's design. Failed: "bootc-image-builder
      was archived" (it is not: its README says the sources moved to
      image-builder); "Arti is at 2.5" (2.7.0 came out 2026-10-01); "official
      Pi 5 images" (they are the ARM lead's test images, hosted on his blog);
      the Pi 5 limits stated as of today when the sources are from March;
      the greenboot report stated as a confirmed bug; facts with no source
      (IoT as a Fedora 45 edition, a 13-month support period, the date of
      Tor 0.4.9.5, `Notify=healthy`, "GTC 2026", "Arti offers no control
      port"); D4 with no options, costs or recommendation; D2 and D3 without
      a cost per option; and **the plan stating Podman as the design while D2
      was open** (its one-page summary, §2, §4.2, §5).
- [x] Round 2: each corrected — the moved sources; Arti 2.7.0 with its
      source; the Pi 5 images described as they are, dated to March, with a
      re-check at Fedora 45; the greenboot item as one user's open report;
      unsourced facts removed (support period, Tor's date, "GTC 2026",
      Arti's control port — now "checked before any switch") or sourced
      (`Notify=healthy`: the Quadlet reference; Podman 6: the Fedora 45 Beta
      article); D2, D3 and D4 each with options, a cost per option and a
      recommendation; the runtime named as D2's choice everywhere, Podman
      only as its recommendation; stage 1's aarch64 build only if D1 keeps
      the Pi.
- [x] **Verifier, round 2: PASS.** Every round-1 finding resolved; every §2
      fact supported by its §9 source; 21 of 21 links answer (the Fedora docs
      page is a bot check, as the plan says). Its minor notes, applied after
      the verdict as wording only: §4.1 called the greenboot report a bug;
      "Fedora's ARM lead" is not in the sources (now the author's name, whose
      blog hosts the images); §2 made the "prove it or go back" rule depend on
      Podman while §4.2 applies it to any runtime; this record said 20 links
      (21 since round 2). Not sourced in §9, outside §2: that LND drives Tor
      through its control port, and D3's facts about `lndclient` (the
      verifier confirmed on GitHub that lndclient, Loop, Pool and Faraday are
      Go repositories of Lightning Labs).
- [x] At round 2, owner decisions D1–D4 open, each with options, costs and
      a recommendation.
- [x] **Round 3: two owner decisions** (2026-10-11, AskUserQuestion). D2:
      Podman with Quadlet from the start, as recommended. D3: the owner first
      took the recommendation, Go, then reconsidered and confirmed **Rust**
      the same day. The recommendation was wrong on facts this plan had not
      checked: the previous node's control plane is Rust (103 `.rs` files
      under `control-plane/` — read with `git -C … ls-tree`), not only
      TypeScript as D3's TypeScript option implied; and LDK appears in the
      previous repository's plans (`docs/plans/BLUEPRINT.md`,
      `docs/plans/UniversalAgenticPayment.md`). §7 now records both decisions
      with the corrected reasoning; "In one page" and §5 say what they mean: a
      Rust control plane that decides, systemd and rootless Podman that
      enforce, and an assistant that only suggests, through a fixed menu of
      actions. ("Rootless" was withdrawn in round 4: it is decision D5.)
- [x] **Verifier, round 3: FAIL.** The gate, the links and these facts held:
      103 `.rs` files (at the previous checkout's HEAD, 3bbbe392), LDK in
      both plan files, TypeScript as the dashboard's backend, `lndclient`'s
      go.mod requiring LND. Failed: (1) "LND over gRPC with `tonic`" — the
      cited `control-plane/Cargo.toml` names the community crate
      `lnd_grpc_rust` as the LND client (`tonic` builds the control plane's
      own server), so the Rust cost this round had removed, community-kept
      LND clients, is real; its `docs/plans/BLUEPRINT.md` records that crate
      has no BOLT12 `offersrpc`; (2) "rootless" Podman credited to D2, though
      D2 never offered it and its costs were never shown (a default chosen
      for the owner); (3) "secrets … never stored" against G9's option of a
      stored wallet password; (4) this record still said D1–D4 open, and no
      ADR followed the decisions. Smaller: "(decision D3)" on the split of
      roles; "port candidates keep their language" (12 of 90 are the control
      plane's, 60 the TypeScript backend's); "fail to compile" without the
      catch-all exception; "secret types refuse to print" as if built in;
      "a third language" unnamed; jargon; D2's "earlier idea for Fedora
      CoreOS" dropped; the `lndclient` facts unsourced. It also reported a
      slip of its own: one `curl` to crates.io sent the owner's email
      address in its User-Agent header.
- [x] Round 4. D3 rewritten from its sources: `lnd_grpc_rust` and its
      missing `offersrpc` as the cost of Rust, the LND client generated by
      this project from the pinned LND version's protocol files, 12 and 60 of
      the 90 port candidates, LDK's `lightning` crate already in use, the
      catch-all exception, `secrecy` named as a library, the three languages
      named. "Rootless" taken out of D2 and put to the owner as D5 (rootless
      or rootful, with costs; the owner's message of 2026-10-11 assumed
      rootless, so it is the recommendation, to be confirmed). The secrets
      sentence now says what passes through and leaves the stored-password
      question to G9. D2's Fedora CoreOS note restored. ADRs 0001 and 0002
      written. Sources added for `lndclient`'s go.mod and the previous
      repository's files.
- [x] **Verifier, round 4: FAIL.** Held: the gate, all links, the counts
      (103 files; 12 and 60 of 90), the owner's quote and the decisions'
      times, the secrets sentence against G9, the ADRs' existence, ADR 0001.
      Failed: (1) the new cost example — LND itself has no `offersrpc` (its
      `lnrpc/` at v0.21.4-beta has no BOLT12 sub-server), so the gap was not
      the community crate's; the real lag, which the verifier measured, is
      that `lnd_grpc_rust` 2.16.0 lacks calls LND 0.21.4 has (29 lines of
      `walletkit.proto`, 2 of `router.proto`); (2) D5's cgroup cost —
      systemd has delegated `pids memory cpu` to user services by default
      since version 252, and Fedora 45 ships 262 — and D5's facts had no
      sources; (3) ADR 0002 kept the "thin interfaces" sentence that round 4
      had dropped from the plan. Not recorded in round 4: that drop, Go's
      lost "no exhaustiveness check" cost, and §8's "in Rust" and §4.2's
      "Podman (D2)". Smaller: "some 200 dependencies" (188); rootful's
      benefit listed as a cost and its own setup missing; `pasta` and ports
      80/443 unmentioned; the link count and §1's "four decisions" stale; a
      long line.
- [x] Round 5. D3's cost example is now the measured lag, with the crate's
      option of building from a chosen LND checkout; the thin interfaces are
      back in D3 (the owner's proposal) and in ADR 0002; Go's exhaustiveness
      cost restored; "some 190 dependencies"; Rikuri-PI's crates "can be
      shared". D5 rewritten from its sources: lingering, storage, `pasta`,
      ports (the node's above 1024, a web page's not), limits through
      systemd's default delegation (I/O excepted); rootful's cost (the
      subuid/subgid ranges and volume ownership) and benefit separated.
      Sources added: LND's protocol files at v0.21.4-beta, `lnd_grpc_rust`,
      Podman's troubleshooting and rootless tutorial, systemd's
      `user@.service`, Fedora 45's systemd package. All 28 links answered
      HTTP 200 (12:02); the gate was run, but its result was not written
      here (round 5's verifier).
- [x] **Verifier, round 5: FAIL.** Held: the gate (its own run), 28 links,
      every `lnd_grpc_rust` and `lndclient` claim (2.16.0 lacks
      `XCreateAccount` and `SubmitPackage`, which LND 0.21.4's
      `walletkit.proto` has at lines 152 and 287; `LND_REPO_DIR`; 188
      requirements), the systemd and Fedora facts, both ADRs. Failed: D5
      showed the `/etc/subuid`/`/etc/subgid` ranges and data-volume
      ownership as rootful's costs only, though the rootless tutorial the
      plan cites requires both for rootless too (lines 32 and 201) — a lean
      toward the recommended option of an open decision. Not yet proven:
      "the owner's proposal" for the thin interfaces (they come from the
      analysis the owner pasted, not the owner's own words). Smaller: no
      gate result in the record; two long lines; §9 repeating the
      `offersrpc` premise uncorrected; `lndclient` trails too (it pins an
      LND commit from before 0.21.0 and has no `XCreateAccount`); CPU
      pinning is not delegated by default; AGENTS.md's "settings changes only
      through tested updates" is not listed among the plan's decisions.
- [x] Round 6. D5: a **Both** clause carries the ID ranges and the volume
      ownership (`--userns=keep-id` for rootless with a non-root image user);
      rootful keeps its one cost (Podman as root) and its benefit; CPU
      pinning joins I/O as needing a setting; §9's notes on the two Podman
      pages say what each supports. D3: the thin interfaces attributed to the
      analysis the owner shared (also in ADR 0002); `lndclient`'s own lag
      stated. §9's `offersrpc` note says LND itself has none. The settings
      rule is listed with the later decisions. Long lines rewrapped. Gate:
      all 7 steps passed at 12:36 (91 guard tests, 52 quality-tool tests).
- [x] **Verifier, round 6: FAIL.** Held: the gate, 28 links, round 5's
      ID-range finding, every D5 source. Failed: (1) D5 still leaned toward
      rootless by omission — by default every rootless container runs as
      the same user, which owns every container's data, so an escape from
      the Tor container reaches LND's wallet files and Bitcoin Core's data;
      rootful `userns=auto` gives each container its own range, and rootless
      can use `userns=auto` too, which D5 never offered; (2) "`lndclient`
      pins an LND commit from before 0.21.0" — false: the commit (40c64f9,
      2026-06-30) is after 0.21.1; I took it from round 5's verifier report
      without checking it; (3) my rewrap merged "## 2. Build" into the
      Plan's last line. Smaller: "they also say" (only BLUEPRINT.md says
      it); the thin interfaces' source named systemd and LND only, not
      Podman or tests; the settings rule named no stage; two more rootless
      costs in Podman's own pages (`pasta` between containers,
      `rootlessport` and client addresses) and one in Quadlet's (user units
      cannot wait for system units).
- [x] Round 7. D5 has three options: rootless with one user (Podman's
      default, and what an escape then reaches), rootless with a range per
      container, rootful with a range per container; each with its costs
      and benefit, the rootless costs shared, the ID ranges and volume
      ownership common to all three, every fact sourced (the userns option
      and rootless limitations pages added). Recommended: rootless with a
      range per container — still to be confirmed by the owner. D3: the
      false `go.mod` claim removed (only "no `XCreateAccount`" stays); the
      thin interfaces credited for systemd and LND, Podman added here. §9:
      only BLUEPRINT.md says it. The settings rule: stage 6. The record's
      heading restored. All 30 links answered HTTP 200 (12:48); gate: all 7
      steps passed at 12:49.
- [x] **Verifier, round 7: FAIL.** Held: the gate, 30 links, the
      headings, D5's three options and nearly all its facts, the `lndclient`
      sentence, §9's BLUEPRINT note. Failed: ADR 0002 still credited the
      thin interfaces, Podman included, to the analysis the owner shared
      (fixed in the plan only, and the analysis's purpose was a swappable
      language, not tests); "Quadlet's page above" (it is below); "cannot
      be ordered after system services (such as the image's own health
      checks)" — Quadlet's example is `network-online.target`, and greenboot
      checks run after the containers, not before. The recommendation's
      reason held only in part: rootful's range gives the same separation,
      so the only stated reason for rootless was the owner's earlier message.
      Smaller: `rootlessport` loses client addresses only by default; "every
      container runs as that same user" overstates (container root does);
      the `keep-id` note dropped without a word; the status, the summary,
      ADR 0001 and the commit message still framed D5 as rootless or not;
      the settings rule's stage 6 unexplained, G9 and G10 without a stage.
- [x] Round 8. ADR 0002 and D3 now say the analysis proposed the interfaces
      for systemd and LND to keep the language swappable, and that this
      plan adds Podman and uses them to fake backends in tests. D5: the
      Quadlet example and its link fixed; "by default" for `rootlessport`;
      container root is the shared user; `keep-id`, sized, restored. The
      recommendation now gives its reason — the same separation as rootful,
      and Podman never holds root, paid for with the user-service costs —
      and says the owner's message came before the options were set out.
      The status, the summary, ADR 0001 and the commit message name both
      halves of D5. G9 is stage 4, the settings rule stage 6 (with the note
      that stages 1 and 2 already write settings), G10 when a second node
      joins. Gate: all 7 steps passed at 13:05.
- [x] **Verifier, round 8: FAIL.** Every round-7 failure answered; gate,
      30 links, headings, the attributions (checked against the transcript)
      held. Failed: (A) the `keep-id` note I restored runs a container as
      the shared user (userns page lines 29 and 63), which undoes the
      separation the recommended option rests on, unstated; (B) "Podman
      itself never holds root" left out its counterpart — rootless Podman's
      user can read, change or remove what its subordinate IDs own
      (`podman unshare`), so in either range option a runtime bug reaches
      every container's data, LND's wallet included. Not answered from
      round 7: EXEC-08's rule bears on all three options. Smaller: the
      summary and the commit message gave D5's two halves as the answer,
      not the questions; "by default" sat on the wrong word.
- [x] Round 9. D5: the `keep-id` sentence now says it runs the container as
      the shared user and gives up the separation; the range options say
      the runtime's own account reaches every container's data, and that
      EXEC-08 (no unrestricted container-runtime access, no root socket,
      control through a narrow, audited interface) applies in every option;
      rootful's cost is "a runtime bug reaches the whole host"; the
      recommendation's reason is the difference that is left — a runtime
      bug stops at an unprivileged account instead of the host. The summary
      and the commit message ask both questions (rootless or rootful; one
      user or a range per container). "By default" now qualifies
      `rootlessport` on rootless bridge networks. Gate: all 7 steps passed
      at 13:33.
- [x] **Verifier, round 9: PASS.** Every round-8 finding answered and
      supported by its source; the gate, the 30 links, the headings, the
      diff, record and commit message hold. Its notes, for the owner's
      decision on D5 rather than changes here: `network-online.target` is
      the one system unit Quadlet works around for user units, so the
      example overstates that cost; rootful's `containers` range needs
      sizing too; "the user-service costs above" undersells the list it
      points at; §9's notes do not name `podman unshare` or keep-id's
      mapping; ADR 0001 states D5 as two halves, and the fourth
      combination, rootful with one user (container root is host root), is
      left out without a word; how data-volume ownership stays matched when
      `userns=auto` picks ranges is a question for the owner. Not yet
      proven: the gate on the final `main`.
- [x] **Re-landed onto `main`, and D5 decided** (2026-10-12). The branch sat
      on the pre-GitHub root (2075218), with no merge base with `main`;
      1ec05a7 cherry-picked onto `main` 5630ea0 without conflict, beside the
      lessons register's commit. The owner, asked why no node code existed
      after three days of process work, chose (AskUserQuestion): freeze
      guard work after the running review; D5 = "Rootless, range each
      (Recommended)"; the N150 is not ready, so stage 1 builds and tests the
      image in CI first (its drill on the N150, §8, still closes the
      stage). D5 written into the plan (status, summary, §7) and
      ADR 0001, and as ADR 0003, whose consequences come from §7's D5 row
      and round 9's notes; round 9's data-volume ownership question is kept
      in ADR 0003 as an owner question for stage 2's first container. The
      README links the ADRs and the register. Gate: all 7 steps passed on
      this tree with the D5 edits not yet committed (`reland-gate.out`;
      its history scan covered 34 commits, so not the D5 commit).
- [x] **Verifier, the branch's one final check** (the owner's stop rule,
      2026-10-11, recorded in the bootstrap record: one final check per
      branch; wording findings fixed without another round): FAIL on
      wording only. Passed: both cherry-picks byte-identical to the
      originals; the gate at 5c5062f, all 7 steps, its scan covering the D5
      commit (35 commits); the register checker identical to both
      receipts; every local link; no scrap. Findings, all corrected here:
      this entry claimed no check round was needed for new content; the
      Knowledge-layer box was unchecked; "on `main`" read as merged; the
      lessons record cited the gate receipt by a wrong relative path and
      undercounted round 12's findings; ADR 0003 left out four of §7's
      costs (a web page on 80 or 443, `pasta` and container-to-container
      traffic, `rootlessport` losing the client's address, I/O limits and
      CPU pinning) and turned round 9's owner question on data-volume
      ownership into a test alone. Not yet proven: the owner's three
      answers outside this session's transcript, CI on this branch, the
      merge.

## 5. Close Out
- [x] Full gate green: all 7 steps, 13:33 on round 9's tree, and on the
      re-landed tree on top of `main` 5630ea0 (2026-10-12, `reland-gate.out`;
      the verifier's run at 5c5062f)
- [x] Knowledge layer: N/A — no behaviour, help page or runbook exists yet.
- [x] Commit message explains why; record committed with the change.

## Skipped items — visible, never silent
- Fedora's own documentation pages for IoT bootc refused automated reading
  (an "Access Denied" bot check); the plan cites them but relies for its
  facts on the bug trackers, release pages and announcements it could read.
  Reactivate: stage 1 reads them in a browser before building the image.

## Evidence log
```
2026-10-11  sources read: see platform-plan.md §9
2026-10-12  re-landed onto main 5630ea0 (docs/plan-and-lessons); D5 decided (ADR 0003);
            full gate: all 7 steps passed (evidence/2026-10-11-platform-plan/reland-gate.out);
            verifier (final check): FAIL on wording only, corrected
```
