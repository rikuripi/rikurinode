# Build Record — 5c.1: the control plane runs on the node, with a claim screen at the console

| | |
|---|---|
| **Date** | 2026-11-06 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/5c1-control-plane-on-node`, from `main` at `f5584b6`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature |

## Task Contract

1. **Outcome:** an installed node runs the control plane by itself. A browser on the LAN can fetch the node's CA certificate and reach the API over HTTPS through the node's firewall. At the node, Alt+F2 shows a claim screen with the claim code, the node's addresses and the CA fingerprint, and Enter arms a new code. Nothing else is opened.
2. **Scope:** stage 1, change 5c, the first of four slices (owner, 2026-11-06: "4 slices, 5c.1 first (Recommended)"). The owner's design choices (2026-11-06):
   - the screen keeps Fedora's login prompt on `tty1`, and the claim screen is on `tty2`, reached with Alt+F2 ("Login on 1, claim on 2 (Recommended)");
   - a key press at the node arms a new claim code ("Key press at the node (Recommended)"), so physical presence stays the proof and no code is kept in clear;
   - the program is built in the image's own build ("Built in the image's build (Recommended)"), in a first stage from the official Rust image pinned by digest at the repository's Rust 1.98.1 (`rust:1.98.1-slim-trixie@sha256:4cd829461bd5c4d511c32e269da9cb8929223b666519d8004e35fc8d1d771ab7`, read from Docker Hub on 2026-11-06).

   Files:
   - `image/Containerfile`: the build stage; the program into `/usr/bin`.
   - `image/rootfs/`:
     - the system user (sysusers);
     - the hardened service unit (its own user, `CAP_NET_BIND_SERVICE` only, `StateDirectory=rikuri/control-plane`, listening on 443 and 80);
     - a firewalld service opening 80 and 443 in the default zone;
     - the claim screen unit on `tty2`, with `getty@`, `autovt@` and `kmsconvt@tty2` masked, because a login there would hang it up (the kmscon lesson);
     - a greenboot check that the API answers on loopback.
   - `control-plane/`: one subcommand, `claim-screen`. It shows the node's addresses and the CA fingerprint; on Enter at the node, it arms a new code on an unclaimed node and shows it. Once claimed, it says so and offers nothing.
   - `.github/workflows/image.yml` and `publish.yml`: the build gets the control plane's sources (`--build-context`), and the image workflow also runs when `control-plane/**` changes.
   - `image/drill/vm_drill.py`: the drill forwards the VM's 80 and 443 to the runner. From outside the VM it fetches `/ca.crt` over HTTP and reads the API over HTTPS with only that CA trusted. It checks the service user, the open ports and the greenboot check.
   - `image/check_image_root.py`: the shipped units and files, as for the others.
   - Tests for each of these, and the knowledge layer: the install runbook's last step (Alt+F2, the claim screen), README's status.
   - Risk tier: **high-risk** (a trust boundary opened to the LAN; the claim, which makes the owner).
   - **Details settled while writing the tests** (each is in the tests; none widens the outcome):
     - **The claim lock.** The claim screen is a second writer of `claim.json`. `claim::attempt` reads the file, spends the argon2 time judging, then writes `wrong_tries` back. A code armed at the screen in that window would be overwritten by the old hash, so the code on the screen would never work, and both writers share `claim.json.tmp`. `arm`, the wrong-try write-back and `finish` take one lock (`claim.lock`, `StateDir::lock`, `File::lock` of std), and the write-back re-reads under it and writes only if the claim is still the one judged (`claim::count_wrong`).
     - **Ctrl+Alt+F2, not Alt+F2.** Fedora 45's kmscon draws `tty1` itself and reads the keyboard through libinput, so the kernel never sees Alt+Fn there; kmscon switches consoles on Ctrl+Alt+Fn (xkb's `XF86Switch_VT_n`). Ctrl+Alt+F2 reaches the claim screen, and Ctrl+Alt+F1 (or Alt+F1) returns from it. The owner's choice (login on 1, claim on 2) is unchanged; only the keys named change. This is reasoning, **not yet seen** on the N150.
     - **The firewall:** one firewalld policy, `/usr/lib/firewalld/policies/rikuri-node.xml`: from any zone to the node itself, `http` and `https`, target `CONTINUE`. It replaces no zone file of Fedora's, whatever the default zone is. Fedora IoT ships firewalld (`docs/build-records/evidence/2026-10-12-stage1-os-image/research.md`).
     - **greenboot's check is a required one** (`required.d/50-rikuri-control-plane`): an image can repair a control plane that an update broke, which is the reason the containers range is only wanted (no image can repair `/etc`). It waits up to 120 s for the API, verified against the node's CA as `localhost`.
     - **Masks in `/usr/lib`:** `getty@tty2`, `autovt@tty2` and `kmsconvt@tty2` link to `/dev/null` in `/usr/lib/systemd/system`, so an image update keeps them, unlike a mask in a node's `/etc`.
     - **Addresses:** the screen shows the address the node would use to reach another network: a UDP socket connected to `192.0.2.1` (TEST-NET-1; connecting a UDP socket sends nothing), so no new dependency. With no route it says to connect the cable. The claim screen's unit denies all IP traffic (`IPAddressDeny=any`).
   - **Not included:**
     - `rikurisetup.local` and the node's LAN name or IP in its certificate (5c.2). In this slice the drill reaches the API as `localhost` through the forward; a browser by IP is 5c.2;
     - any HTML page (5c.3);
     - naming, the UUID and the SetupHub (5c.4);
     - the root helper (D13); UPS (D22).
3. **Done when:**
   - unit tests, red first, for the subcommand, the units, the image check and the drill's new checks;
   - CI's VM drill, on the image built from this change: the service runs as its own user, not root. From the runner, through the forwarded ports, `/ca.crt` is fetched over HTTP, and `GET /api/setup` over HTTPS succeeds with only that CA trusted, while a client without it fails the handshake. The greenboot check passes. No other new port is open;
   - the install test still passes, and the claim screen's unit is seen running on `tty2` in the drill;
   - `Full gate (Ubuntu)` and the OS image workflow pass on the PR;
   - one `verifier` pass, with `cargo mutants` over the changed Rust lines, has no Important finding.
   - Not in this task: the claim screen seen on the N150's Alt+F2 (the owner's, after a publish).
4. **Authority:** the owner's words above; this branch; registry reads of Docker Hub for the digest; `scripts/cargo.sh` for cargo; tests only in rikuri-drill through `safe-run.sh`; a draft PR; no merge. An independent check is required.
   - **The Rust parts are tested only in CI** (owner, 2026-11-06: "CI only, budget 6 (Recommended)"). Tests may not run on the Mac; rikuri-drill has no network, so it has no Rust toolchain and no crates; the sandbox does not reach Rust's toolchain downloads. CI's full gate runs `cargo test` inside `safe-run.sh`, plus clippy and cargo-deny. Every Rust result is recorded as Not yet proven locally. On the Mac, `scripts/cargo.sh` is used only to compile and lint (`check`, `clippy`), never to run a test.
5. **Limits:** one task; two repair cycles; two review rounds; development CI at most 6 runs (raised from 4 by the owner's choice above).

## Evidence log

- **Test changes in the red commit to tests that existed before, and why** (none loosens a check):
  - `image/tests/test_vm_drill.py`, `test_network_is_restricted_to_ssh_and_the_drills_registry`: the VM's forwards become three. The new two are the control plane's ports, on the CI machine's loopback (`8080` to `80`, `8443` to `443`), each required by name; `restrict=on` and the one forward out are unchanged.
  - `scripts/quality/tests/test_workflows.py`, `test_only_a_pull_request_can_skip`: the changes job's pattern must also match `control-plane/`, since the image now holds the control plane.
  - `image/tests/test_check_image_root.py`, `Root`: the fixture root also holds the control plane's shipped files, once they exist (the same form as the files before them).
- **Red, Rust** (the Mac, `scripts/cargo.sh check --locked --tests -p rikuri-control`, compile only, no test run): `could not compile rikuri-control (lib test) due to 65 previous errors`, each one a missing item: `count_wrong`, `LOCK`, `StateDir::lock`, and the console's `Shown`, `Fingerprint`, `initial`, `press_enter`, `ca_fingerprint`, `shown_address`, `render`. Running these tests is CI's (Not yet proven locally).
