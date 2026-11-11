# Build Record — 5c.3a: the UI's pipeline, and the certificate screen

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/5c3a-ui-pipeline`, from `main` at `a25544d`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
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
