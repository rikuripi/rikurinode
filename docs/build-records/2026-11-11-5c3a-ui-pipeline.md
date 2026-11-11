# Build Record — 5c.3a: the UI's pipeline, and the certificate screen

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/5c3a-ui-pipeline`, from `main` at `a25544d`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | PR #81, merged by the owner as `17cd28a` (head `03ff963`), 2026-11-11T20:53:50Z: the contract `aab8a32`; the look `ed8864d`–`3517ed6`; the packages `701abc1`, `0006361`; red `6b211b9`; tests after red `6b9536f`; the fix `e7f5b48`; docs `a94bfc8`, `fb701f1`; repair 1 red `4beca2d`, fix `46deff2`, docs `8e63b48`; repair 2 `03ff963`. This close-out: the record only. |
| **Status** | DONE (2026-11-11) |
| **Change type** | feature |

## Why

Stage 1's first UI slice is a setup page that "secures the connection (D10)": "the first setup screen, reached over plain HTTP, offers the certificate with a short per-device guide (Windows, macOS, iPhone, Android, Linux), then switches to HTTPS". The API behind it exists: `/ca.crt` over HTTP (5c.1), and the names and certificate a browser accepts (5c.2). No HTML page exists yet. D15 and D23 fix the UI's shape: TypeScript with Svelte and plain Vite, static files built in CI and embedded in the control plane's binary, types from ts-rs, render tests, a pinned and inspected supply chain, and "a design system is the first UI slice's first step".

The owner (2026-11-11), after "Next" for 5c.3:
- slicing: "Toolchain + cert screen (Recommended)". 5c.3a is the UI's whole pipeline, shipping one real screen, the certificate screen. 5c.3b is the claim, password and sign-in screens over HTTPS;
- languages: "English, ready for more (Recommended)": English text only, with the key check built and run;
- the look: "Mockup to approve first (Recommended)": a private mockup of the certificate screen in two or three styles at phone and desktop widths. The owner picks one, and it becomes the design tokens.

## Task Contract

1. **Outcome:** a novice who types `rikurisetup.local` (or the node's address) into a browser gets a friendly page. It hands them the node's certificate with steps for their device, shows them how to check its fingerprint against the node's screen, and then takes them to the secure page, which confirms the connection is secure.
2. **Scope:**
   - **Step 1, the look:** a private mockup (an Artifact, not in the repository) of the certificate screen in two or three styles, at phone and desktop widths. The owner's pick becomes the design tokens (colours, type, spacing, radii), committed as CSS variables in light and dark themes.
   - **`ui/`, new:**
     - a Svelte and plain Vite app in TypeScript, with `package.json` and its committed `package-lock.json`, every version exact;
     - installs with `npm ci --ignore-scripts`;
     - Node pinned, and present only in CI and the image build.
     - Every package in the lockfile gets AGENTS.md §2's inspection, recorded here: source, provenance, licence, maintenance, dependency tree, side effects. The tree is measured, as D23 asks.
   - **The certificate screen:**
     - served over plain HTTP at `/`;
     - `/ca.crt` offered, with a short guide for each of Windows, macOS, iPhone/iPad, Android and Linux;
     - no trust decision rests on this page, since anyone on the network can alter a plain-HTTP page; it explains, offers the download, and sends the reader on;
     - then a link to the same host over HTTPS.
     - Over HTTPS, `/` shows that the connection is secure and the node's setup state, read from `GET /api/setup` through the typed contract. Claiming is 5c.3b.
     - **The fingerprint check is made against the browser, never against a page** (a design note from step 1, 2026-11-11). The secure page tells the reader to open the browser's own certificate viewer (the padlock, then the certificate, then its SHA-256) and compare it with the node's claim screen (Ctrl+Alt+F2). Neither page shows the fingerprint to compare. Someone in the middle who served their own certificate could serve a page showing the node's real fingerprint, which is public. Only the browser knows which certificate it is talking to.
   - **`control-plane/`:**
     - the built UI embedded in the binary, served from a fixed table of files: no path from a request reaches the disk;
     - security headers: a CSP with `script-src 'self'`, no inline script and no outside origin, plus `nosniff`, `frame-ancestors 'none'` and a referrer policy;
     - the plain router serves only the certificate screen's files and `/ca.crt`, and still redirects everything else. Still no API route over HTTP;
     - `SetupReport` gets the ts-rs derive, under `cfg_attr(test, …)` as a dev-dependency, so the shipped binary's tree does not change; `cargo test` writes the TypeScript, and CI fails on a difference;
     - the embedding mechanism is chosen after inspection, preferring none (a `build.rs` table with `include_bytes!`) over a new crate.
   - **CI and the image:**
     - the full gate gains the UI's steps: install from the lockfile, its audit (one that cannot pass silently), its type check, its build, its unit and render tests;
     - the Containerfile gains a UI build stage pinned by digest, before the Rust stage;
     - the workflows' path filters gain `ui/**`;
     - `/.containerignore` lets `ui/` in, without `node_modules` or the build output.
   - **Tests:**
     - the files table and its headers;
     - the plain router: the screen's files served, everything else redirected, no API route;
     - the render tests: phone, tablet and desktop widths, every theme variable defined, every text key present in every shipped language (English);
     - `check_image_root.py` if the image gains files;
     - the VM drill: from the runner, `http://…/` serves the certificate screen with the CSP, and `https://…/` serves the secure page with only the node's CA trusted.
   - **The knowledge layer:** the install runbook's last steps (open the page, install the certificate, compare the fingerprint), and README's status.
   - Risk tier: **high-risk**. A page served to the LAN that tells a novice to trust a certificate, and a new supply chain into the binary.
   - **Not included:**
     - the claim, password and sign-in screens (5c.3b);
     - naming, the UUID and the SetupHub (5c.4);
     - languages other than English;
     - a router library, server-sent events and charts (no screen needs them yet);
     - the backlog nits of 5c.2 and PLAT-01.
3. **Done when:**
   - the owner has picked the look, and the tokens follow it;
   - unit and render tests, red first: Rust tests are red in CI (the Mac runs no tests), the UI's and Python's in rikuri-drill through `safe-run.sh` where the toolchain allows, otherwise in CI, and recorded as such;
   - every package's inspection is recorded, and the audit passes;
   - CI's VM drill passes the new checks and every check it had;
   - `Full gate (Ubuntu)`, the tools' py3.9 and py3.12 jobs, Rust mutants on the changed lines, and the OS image workflow pass on the PR;
   - one `verifier` pass has no Important finding;
   - Not provable in CI, so Not yet proven unless the owner runs it: the steps on a real phone and laptop against the N150.
4. **Authority:**
   - the owner's words above; this branch; a draft PR; no merge;
   - the npm registry, Docker Hub and the packages' source repositories, read only, for pins and inspection;
   - `scripts/cargo.sh` for `check`, `clippy` and `fmt` on the Mac, never a test;
   - rikuri-drill over its pinned SSH key for the Python tests. It has no network, so the UI's install and its tests may be CI's only;
   - Node is not installed on the Mac or on rikuri-drill without asking the owner;
   - an independent check is required.
5. **Limits:** one task; two repair cycles; two review rounds; CI at most 8 runs on the PR (a new toolchain's first runs).

## Evidence log
- **Step 1, the mockup** (2026-11-11): a private canvas, https://claude.ai/artifact/MJbUCTx3K3i7KGra4Wft4s. Three styles: A Meadow (soft green, Nunito), B Sunrise (warm cream and coral, Fredoka and Inter), C Dusk (dark indigo and lavender, Quicksand and Inter). Each shows the certificate screen at phone width and the secure page at desktop width. Awaiting the owner's pick.
- **The owner's pick** (2026-11-11): "B, Sunrise. Can you make use the Bitcoin sign (for the Sun log) and its usual orange color with a brighter yellow?" The logo is now a sun: a Bitcoin-orange disc (`#F7931A`) with a white ₿ tilted as in Bitcoin's logo, and bright yellow rays (`#FFC93C`). It is shown on the canvas's Sunrise screens. In the product it will be an SVG path, not a font glyph, so it draws the same with no web font. Bitcoin orange with white text has too little contrast for a button (about 2.3:1), so the buttons stay coral `#C2492B` (5.6:1); orange and yellow are for the logo and highlights. The Sunrise fonts are Fredoka and Inter, served from the binary (no outside origin, by the CSP); their licences are checked with the packages.
- **The owner, on the sun** (2026-11-11): "I like it. Let's adjust the Sun as rising over the horizon with round yellow glow." The logo is now the orange ₿ disc risen over a dark horizon line, with a shorter, fainter line below it for the ground. Behind it are two round glow rings of `#FFC93C`, one at 60% and one at 30%, all cut off at the horizon. The canvas's version 9 shows it.
- **The owner, on the glow and the colours** (2026-11-11): "Make thicker yellow glow. Make the pill shaped button the same bitcoin orange. The shaded accent should be the same yellow." In version 10 of the canvas:
  - the glow rings are wider and stronger (85% and 45%), with a smaller disc;
  - the pill buttons and the chosen device are Bitcoin orange `#F7931A`, with dark text `#3A2418` (about 6.7:1; white text would be about 2.3:1);
  - the step chip and the numbered badges are the yellow `#FFC93C`;
  - the large shaded panels ("Installed it?" and "Your node") are a light tint of that yellow, `#FFE7A3`, so body text on them keeps its contrast;
  - coral now remains only in link text.
- **The owner** (2026-11-11): "Ok, a bit too dark, lighter orange and yellow." In version 11 of the canvas:
  - the buttons and the chosen device are a lighter orange, `#FFAD4D`, with dark text (about 8:1);
  - the yellow accents and the glow are a lighter yellow, `#FFDD70`;
  - the large panels are a paler tint of it, `#FFF0C2`;
  - the logo's disc stays Bitcoin orange `#F7931A`, so that the white ₿ stays legible on it.
- **Step 2, the supply chain (AGENTS.md §2's inspection, 2026-11-11).** The packages were read from the npm registry, Docker Hub, Microsoft's container registry, crates.io and GitHub. No package was downloaded or run on the Mac. `npm install --package-lock-only --ignore-scripts --before=2026-10-28` (Node 22.20.0, already on the Mac) resolved the tree into `ui/package-lock.json` as of two weeks ago and wrote no `node_modules`; `--before` holds every transitive version to the same two-week cooldown as the direct ones.
  - **Direct packages, every version exact** (`ui/package.json`). There is no `.npmrc`, because the repository's hygiene check treats it as a secret file (npm keeps tokens there), so every install passes its flags explicitly: `npm ci --ignore-scripts --engine-strict --no-audit --no-fund`:

    | Package | Version | Published | Licence | npm provenance | Ships to the node? |
    |---|---|---|---|---|---|
    | `svelte` | 5.57.3 | 2026-10-26 | MIT | yes | its runtime, compiled into the output |
    | `vite` | 8.3.5 | 2026-10-21 | MIT | yes | no (build) |
    | `@sveltejs/vite-plugin-svelte` | 7.3.1 | 2026-09-23 | MIT | yes | no (build) |
    | `svelte-check` | 4.7.7 | 2026-10-16 | MIT | yes | no (type check) |
    | `typescript` | 6.0.3 | 2026-04-16 | Apache-2.0 | no | no (type check) |
    | `@playwright/test` | 1.64.1 | 2026-10-14 | Apache-2.0 | yes | no (render tests) |
    | `@fontsource/fredoka` | 5.3.0 | 2026-07-19 | OFL-1.1 | yes | its font files, with the OFL's text |
    | `@fontsource/inter` | 5.3.0 | 2026-07-19 | OFL-1.1 | yes | its font files, with the OFL's text |

    TypeScript is 6, not 7: `svelte-check` 4.7.7's peer range is `^5.0.0 || ^6.0.0`.
  - **The whole lockfile:** 76 entries. Every one is `resolved` from `registry.npmjs.org` and has a `sha512` integrity. Licences: MIT, ISC, BSD-3-Clause, Apache-2.0, OFL-1.1 and MPL-2.0. The MPL-2.0 ones are `lightningcss` and its platform builds, a build-time CSS tool whose code never ships. One package has an install script: `fsevents` 2.3.3, macOS-only and optional; scripts are off. 27 entries are optional per-platform native builds of `rolldown` 1.2.15 (MIT, provenance) and `lightningcss` 1.33.0 (MPL-2.0, no provenance). Only `linux-x64-gnu` and `linux-arm64-gnu` are installed in CI and the image build. These native binaries are the largest trust in this tree: they run at build time with the build's rights, and they can change the output. That is why the build runs only in CI and the image's build stage, with no secret, and why the binary's embedded files are the build's output.
  - **Node:** `docker.io/library/node:22.23.4-trixie-slim@sha256:be1e2a3dc2c4fd68cdfadad2a696a280e0d2749098bee509230174d72fb768c6`, the image's UI build stage. Node 22.23.4 was released 2026-10-21 (nodejs/node's release). It is trixie like the Rust stage.
  - **Render tests' browsers:** `@playwright/test` would download browsers from Microsoft's CDN at install time, an unpinned fetch. Instead, the tests run in `mcr.microsoft.com/playwright:v1.64.1-noble@sha256:2f05f8a734509a7b3f26a912639488ee08f58a7b292d14d62271bcff9038768f`, whose browsers are already inside: the same release as the package, pinned by digest.
  - **ts-rs** 12.0.1 (2026-01-31, MIT, Aleph-Alpha/ts-rs, MSRV 1.78) with `ts-rs-macros` 12.0.1. With its default feature `serde-compat` only, it needs `thiserror`, `syn`, `quote` and `proc-macro2`, already in the lockfile, so it adds two crates. It is a dev-dependency, and the derive sits under `cfg_attr(test, …)`, so the shipped binary's tree does not change; the evidence is `cargo tree -e normal` before and after.
  - **What ships, and its licences:** the Svelte runtime (MIT) and the two font families (OFL-1.1). Their notices are served with the UI. Nothing else in the tree reaches the node.
  - **Two Nodes, each pinned by its image's digest:** the Playwright image carries Node 26 (its history: `NODE_VERSION=26`). The UI is built in `node:22.23.4`, in the gate as in the image's build stage, so the tested build and the shipped one come from the same toolchain. The render tests run Playwright's image against that build. `engines` says only the minimum both meet (`>=22.12.0`, Vite 8's); the versions themselves are pinned by the digests.
- **Red, observed** (2026-11-11, commit `6b211b9`):
  - rikuri-drill, an archive of `6b211b9` through `safe-run.sh`: `image/tests` `Ran 504 tests` `FAILED (failures=2, errors=27)`, every one a new SetupPages test or the Verdict's list; `.claude/hooks` `Ran 91` `OK`; `scripts/quality/tests` `Ran 183` `FAILED (failures=6, errors=12, skipped=1)`: the new and changed workflow tests, plus the 7 errors an archive with no `.git` always has.
  - The Mac, `scripts/cargo.sh check --locked --tests -p rikuri-control`: the lib's tests do not compile (5 errors: no `RIKURI_UI_DIR`, no `ts_rs`, no `export_to_string`). The integration tests compile; their red at run time is CI's only (the Mac runs no tests): Not yet proven until CI's first run.
  - The UI's tests: red by reading only, since the toolchain runs only in CI's pinned images.
- **Test changes after red, and why:**
  - `control-plane/crates/rikuri-control/tests/plain_listener.rs` (in the red commit itself, a change to an existing test): its IPv6 subcase asked for `/` and expected a redirect. In the clear, `/` is now the certificate screen by this change's design, so the subcase asks for `/setup`, which still redirects. What it proves is the same: the redirect keeps an IPv6 host's brackets.
  - `control-plane/crates/rikuri-control/tests/ui_pages.rs`: `cargo fmt` rewrapped long lines after red. Layout only: `git diff -w --word-diff` shows only line breaks.
  - `image/tests/test_installer.py`, `test_the_nodes_own_pinned_base`: it counted two stages in `image/Containerfile`. The UI's build stage, which this contract adds, makes three. It now names all three (the Node image, the Rust image, then the base, still pinned by digest). The red commit missed it; the green run found it.
- **The fix's dependency evidence:**
  - `cargo tree -e normal -p rikuri-control`: identical before (from an archive of `6b211b9`) and after, apart from the path on its first line. The shipped binary's tree is unchanged.
  - `Cargo.lock` gains four crates, not the two expected above: `ts-rs` and `ts-rs-macros` 12.0.1, plus `termcolor` 1.4.1, which ts-rs-macros uses only to colour its warnings under `serde-compat`, and `winapi-util` 0.1.11, termcolor's Windows-only dependency, never compiled on Linux or macOS. Both are BurntSushi's (`Unlicense OR MIT`; MIT is allowed by `deny.toml`), with no build script. `serde-compat` stays on, because without it ts-rs ignores `rename_all = "lowercase"` and the generated claim states would be wrong.
- **What the fix does:**
  - `build.rs` walks `ui/dist` (or `$RIKURI_UI_DIR/dist`) into a sorted table of `include_bytes!` entries. It refuses links, names that are not UTF-8, unknown file types, and a build without `index.html`, `cert.html`, `favicon.svg` and `licenses.txt`. `src/ui.rs` serves from that table only.
  - `no_store` now leaves a `Cache-Control` the response set itself; only the pages' files set one, so every API answer is as before.
  - The UI routes sit outside `origin_check`: they are read-only, so a POST is the method router's 405.
  - The gate's step 8 builds and tests the UI.
  - The UI's install is followed by `npm audit --audit-level=low` in the same container, the only one with network. Any advisory fails it, and so does an audit npm cannot read. This is the contract's "audit that cannot pass silently". The weekly OSV audit does not yet read `ui/package-lock.json`: noted for the backlog, not done here.
  - The contract's "unit tests" for the UI are `text-keys.spec.ts` and the render tests' cases for the setup report's parser (a bad shape, an unknown claim, a 500, an abort). There is no separate unit runner.
- **A safety default (confirmed by the owner, 2026-11-11: "Keep the RIKURI_UI_LOCAL default"):** `scripts/quality/ui.sh` starts containers, and on the machine that runs the live node, Docker is the live node's. Outside GitHub Actions it refuses unless `RIKURI_UI_LOCAL=1` is set, so a local gate run there stops at step 8, and CI is the reference. Reversible: one line in `ui.sh`.
- **Green, Python** (rikuri-drill, an archive of the working tree, through `safe-run.sh`): `.claude/hooks` `Ran 91` `OK`; `image/tests` `Ran 504` `OK`; `scripts/quality/tests` `Ran 183` `FAILED (errors=7, skipped=1)`, exactly the 7 no-`.git` archive errors of the red run and of every earlier archive run.
- **The Mac** (with a stand-in `ui/dist`, ignored by git, never committed): `scripts/cargo.sh clippy --locked --workspace --all-targets -- -D warnings` clean, and `fmt --all --check` clean. shellcheck is on neither the Mac nor rikuri-drill: CI's gate runs it. Not yet proven until then.
- **CI run 1** (PR #81, head `a94bfc8`): `Full gate (Ubuntu)` failed (run 43085490570), and so did `Rust mutants (changed lines)` (run 43085490386). Both failed in `scripts/quality/ui.sh build` on `npm audit --audit-level=low`, verbatim: `deepmerge mergeObject() allows prototype poisoning of returned objects - https://github.com/advisories/GHSA-gcqx-w48m-w2h4`, `No fix available`, `Depends on vulnerable versions of deepmerge` (via `@sveltejs/vite-plugin-svelte`), `2 low severity vulnerabilities`. These passed: Build and check the OS image, the guard and quality-tool tests (py3.9 and py3.12), and the advisory audit. The Rust tests and mutants never ran.
- **Verifier, round 1: FAIL**, with three Important findings:
  - **I1:** the gate is red on that advisory.
  - **I2:** the fingerprint check compared the wrong certificate. The claim screen shows the CA's fingerprint (`console.rs`), while the padlock opens the node's server certificate, which the CA signs (`tls.rs`), so the two never match. On iPhone and iPad, Safari has no certificate viewer, so the check could not be done there at all.
  - **I3:** no render test drew the pages under the node's CSP, because `vite preview` sends none.
  - Nits: the drill's new tests sat after the file's `__main__` guard; AGENTS.md did not list the UI step; the image's UI stage runs no audit; plain `/` was a cached 308 in earlier images, and `cert.lead` overclaimed; nothing fetched `/favicon.svg`.
- **The owner, on I1** (2026-11-11): "Recorded exception (Recommended)": `ui.sh` reads the audit as JSON and fails on any advisory except GHSA-gcqx-w48m-w2h4, recorded with its reason and a review date. It also fails if that advisory disappears or the date passes.
- **Repair 1** (red `4beca2d`, then the fix):
  - **I1:**
    - `scripts/quality/npm_audit.py` reads `npm audit --json` against `ui/audit-exceptions.json`. That file holds one exception: GHSA-gcqx-w48m-w2h4, in `deepmerge`, reviewed by 2027-02-11.
    - The reason: it is low and has no fixed version. It comes in only through `@sveltejs/vite-plugin-svelte`, which every Svelte build needs. It runs at build time only and never ships to the node. It merges the plugin's own configuration, never network input.
    - The checker fails on any other advisory, on an exception that no longer matches or is past its date, on an incomplete exception, and on a report it cannot read (empty, not JSON, npm's own error, another version, or totals that disagree). A pass prints each exception it allowed.
    - `--audit-level` is gone.
    - A new exception is an owner decision. `TheRepositorysExceptions` pins the set, and each exception must name this record, which must name its advisory.
  - **I2:**
    - The secure page now sends the reader to **Rikuri Node CA** in the certificate chain (Details or Certificate Hierarchy, the top certificate) and its SHA-256.
    - It adds a route for iPhone and iPad (Settings › General › VPN & Device Management › Rikuri Node CA › More Details) and one for Android (Settings › Trusted credentials › User › Rikuri Node CA).
    - `secure.why` now says "your device" rather than "your browser". The runbook's step 11 says the same, and why the padlock's first certificate differs.
    - Both phone routes are written from the systems' documented menus and are Not yet proven on a real device, like the rest of the real-device steps.
  - **I3:**
    - `vite preview` sends the node's CSP from `ui/src/csp.ts`. `test_workflows` keeps that file equal to `src/ui.rs`'s constant.
    - The render tests check the header on both pages, and that no `securitypolicyviolation` event and no console error occurs.
  - **The nits:**
    - The drill's 5c.3a test classes were moved above the `__main__` guard. A move only: still 504 tests.
    - AGENTS.md > Verification by maturity names the UI step.
    - A runbook note covers the earlier cached redirect, and `cert.lead` now says the privacy holds after the check.
    - `the_icon_is_served_on_both_listeners` added.
    - Not changed: the image's UI stage still runs no audit or type check. The gate runs both on the same lockfile before any merge, and the image builds only from `main` or a PR that passed the gate. Noted for the backlog: the weekly OSV audit should read `ui/package-lock.json`.
- **Test code changed during repair 1:** only new tests, plus the move above.
- **Verifier, round 2** (the corrections only, `a94bfc8..8e63b48`): I1, I2, I3 and nits 1, 2, 4 and 5 are resolved in code and text, with no new Important finding. The verdict was Not yet proven, because CI run 2 was still pending and the verifier's own `safe-run.sh` refused to run on the Mac. Its backlog nits:
  - an exception matches on the advisory id and the package only, so a raised severity would still be allowed until `review_by`;
  - the phone routes are untried on a real device.
- **CI run 2** (head `8e63b48`): the audit step passed as designed, verbatim `npm_audit: allowed GHSA-gcqx-w48m-w2h4 in deepmerge until 2027-02-11: …` and `npm_audit: npm audit: 1 advisories, all recorded exceptions`. Then `Full gate (Ubuntu)` (run 43090342002) and `Rust mutants (changed lines)` (run 43090341715) both failed at `npm run check`, verbatim `Error: Cannot find module or type declarations for side-effect import of '../fonts.css'.` and the same for `'../theme.css'`, in `src/cert/main.ts` and `src/secure/main.ts`: `svelte-check found 4 errors and 0 warnings in 2 files`. This is the red of repair 2. A separate failing test is impractical, because the type check is itself the test.
- **Repair 2** (the last the contract allows):
  - The cause: `tsconfig.json`'s `types: []` keeps out Vite's client types, which declare `*.css` modules, and TypeScript 6 checks side-effect imports by default.
  - The fix: `src/env.d.ts` references `vite/client`. Read from the published `vite@8.3.5/client.d.ts`: `declare module '*.css' {}`.
  - Also checked before this last repair: the font files `fonts.css` names (`fredoka-latin-600-normal.woff2`, `inter-latin-400-normal.woff2`, `inter-latin-600-normal.woff2`) are in the published `@fontsource` 5.3.0 packages.
  - No test code changed.
- **CI run 3** (head `03ff963`):
  - **Pass:**
    - `Full gate (Ubuntu)`, all 11 steps, including the UI's build and render tests and the Rust tests (run 43090784124);
    - `Rust mutants (changed lines)` (43090784655);
    - the guard and quality-tool tests, py3.9 and py3.12;
    - the advisory audit;
    - building and checking the OS image;
    - the USB installer drill.
  - **Fail:** `Boot the image in a VM and run the rollback drill` (run 43090784113, job 130768257277).
    - Every control plane check passed, verbatim. Among them are this change's three: `PASS the certificate screen over HTTP: GET http://127.0.0.1:8080/: certificate page: 200, policy, nosniff, scripts from /assets/ only`, `PASS the secure page over HTTPS with only the node's CA: GET https://localhost:8443/setup: secure page: 200, policy, nosniff, scripts from /assets/ only`, and `PASS the secure page never over HTTP: GET http://127.0.0.1:8080/setup: 308 to https://127.0.0.1/setup`.
    - Then `variants built in the VM: broken, a, b`, and `FAIL drill: timed out after 600s waiting for the broken update to roll back`. That is case 1, a deliberately broken update that greenboot must roll back. Nothing in this change touches the update, greenboot or the variants.
  - Not yet known: whether case 1's timeout also explains the two failed push-to-`main` image runs (43060782808 and 42932353260). GitHub's API answered 502 when read.
- **Status: NEEDS_OWNER_DECISION.** Both repair cycles and both review rounds are used. Whether to re-run the failed drill job (no code change, CI run 4 of 8) or to open its own task for case 1 is the owner's call.
- **The owner, on case 1** (2026-11-11): "Re-run the drill job (Recommended)". Only job 130768257277 of run 43090784113 was re-run, with no code change (CI run 4 of 8). If case 1 passes, 5c.3a closes as DONE and the timeout is recorded as a one-off. If it fails again, 5c.3a stops as BLOCKED, and case 1 becomes its own task.
- **The drill's re-run, and the merge** (2026-11-11): the owner reported "Drill re-run passed". The app's status for PR #81 then showed 5 checks passing and none failing. Reading the re-run attempt's jobs from GitHub's API returned HTTP 502, then a 404 for attempt 2, so this record has the owner's observation and the app's count, not the drill's own lines from the re-run. The owner merged PR #81 at head `03ff963` as `17cd28a`. Case 1's timeout in run 3 is recorded as a one-off: it passed on re-run with no code change. Whether the two earlier failed push-to-`main` image runs had the same cause stays unread (the same 502s).
- **Close-out:**
  - **Done when, Pass:**
    - the look, picked by the owner, with tokens that follow it;
    - red before green: Python on rikuri-drill, the Rust lib on the Mac, the rest in CI's runs 1 and 2;
    - every package's inspection recorded, and the audit passing with the owner's recorded exception;
    - the full gate, py3.9 and py3.12, Rust mutants and the image workflow on the PR, the rollback drill on its re-run;
    - the VM drill's new checks and every earlier one;
    - the verifier: round 1 FAIL, round 2 no Important finding, Not yet proven only on CI, which then passed.
  - **Not yet proven:** the steps on a real phone and laptop against the N150, both phone routes included.
  - **Used:** both repair cycles and both review rounds; CI runs 1 to 3 on the PR, plus the drill's re-run, so 4 of 8; and this close-out's own run.
  - **Backlog, not started:**
    - the weekly OSV audit should read `ui/package-lock.json`;
    - an exception should pin the advisory's severity;
    - the image's UI stage could run the audit and type check;
    - case 1's timeout, if it recurs;
    - 5c.3b, the claim, password and sign-in pages.
