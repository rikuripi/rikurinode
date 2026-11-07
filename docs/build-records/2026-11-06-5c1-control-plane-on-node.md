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
   - `.github/workflows/image.yml` and `publish.yml`: the OS image is built with the repository's root as its context (`podman build -f image/Containerfile .`), so the build sees `control-plane/`; `/.containerignore` lets in only `image/rootfs` and `control-plane/` (without `target/`). The image workflow also runs when `control-plane/**` changes. (First planned as a named `--build-context`; changed by the owner's choice below.)
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
- **Red, Python** (rikuri-drill, `safe-run.sh`, the tree of `1458ce2` from `git archive`):
  - `image/tests` `Ran 421 tests` `FAILED (failures=2, errors=38)`. The errors are the missing pieces: `test_greenboot_control_plane` cannot import its script; `check_image_root` has no control plane files or checks; `vm_drill` has no `exposed_ports`, `service_ok`, `screen_ok`, `policy_active`, `required_passed`, `parse_http`, `pem_fingerprint`, `setup_ok` or `control_plane`. The failures: `test_every_case_is_expected` and `test_network_is_restricted_to_ssh_and_the_drills_registry` (one forward, not three).
  - `.claude/hooks` `Ran 91 tests` `OK` (unchanged by this task).
  - `scripts/quality/tests` `Ran 159 tests` `FAILED (failures=7, errors=7, skipped=1)`: the 7 errors are the known ones from a tree with no `.git` (`repo_hygiene.WholeRepository` ×6, `advisory_audit_age.Remotes` ×1); the failures are `ControlPlaneInTheImage` (×6 with subtests: no control plane in the builds, no push path, no Rust stage) and `Image.test_only_a_pull_request_can_skip`.
- **Red commit amended before any push:** `193e7c7` became `1458ce2` when rustfmt laid out its new Rust tests (line wrapping only), so that no test changes after red for layout.
- **Fix** (its own commit):
  - `control-plane`:
    - `StateDir::lock`, std's `File::lock`.
    - `claim::LOCK`: `arm` (after the slow hash), the wrong-try write-back and `finish` take it.
    - `claim::count_wrong` re-reads under the lock and writes only if the claim's hash is still the one judged.
    - `console`: `initial` never arms; `press_enter` arms on an unclaimed node; `ca_fingerprint`; `lan_address` (the TEST-NET-1 trick); `render`.
    - `main.rs`: the `claim-screen` subcommand (it clears, draws, reads a line, and arms on Enter; it ends at end of input, and its unit restarts it).
    - **The daemon no longer writes the first start's code in the journal:** it logs `claim code armed and not shown` and points to the claim screen. The journal is kept on disk, and the contract says no code is kept in clear.
  - `image/Containerfile`: the first stage, from the Rust image by digest, copies `control-plane/` and runs `cargo build --release --locked -p rikuri-control-plane`; the program goes to `/usr/bin`, and `rootfs/` is copied as `image/rootfs/`. `/.containerignore` is the context's allowlist.
  - `image/rootfs/`:
    - the sysusers entry;
    - the two units (closed worlds) and their `multi-user.target.wants` links;
    - the three `tty2` masks;
    - the firewalld policy;
    - greenboot's required check (it waits up to 120 s, every 5 s).
  - `image/check_image_root.py`:
    - `check_control_plane`, in `check_root`;
    - the subid unit's closed-world reader generalised as `unit_problems` and `unit_overrides`; the subid unit's own rules are unchanged.
  - `image/drill/vm_drill.py`:
    - the two forwards;
    - `Drill.control_plane()` after the first boot, which makes nine checks, each in `EXPECTED`;
    - the evidence goes to `02-control-plane.out`.
  - `.github/workflows/image.yml` (three builds, the changes job's pattern, the push paths) and `publish.yml` (its build): `-f image/Containerfile .`.
  - Knowledge layer: `docs/runbooks/install-node.md` (the intro; step 8; a new step 9, the claim screen; the Report line), README's status.
- **Test changes after the red commit, and why:**
  - `test_vm_drill.py`, `ControlPlaneSteps.test_each_failure_fails_its_own_case`: the 404 on `/ca.crt` moved to `test_no_certificate_means_no_https_case_can_pass`. The red test asked that a 404 fail the CA case alone, but with no CA there is nothing to trust, so the HTTPS case must fail too, as the other red test already said: the two contradicted each other. The 404 now must fail both.
  - `test_vm_drill.py`: a ninth case, "no claim code in the journal" (`code_kept_out`), with its stand-in journal, its failures (no line, a code in clear, a `claim_code` field) and `ClaimCodeInTheJournal`. Added with the daemon's change above, which has no unit seam (`main`'s log line); the drill reads the real service's journal. Additions only.
- **The first fix commit was refused by the pre-commit hook** (`repo_hygiene.py`): `image/Containerfile: line 20: COPY --from image not pinned (no version tag)`. The check reads `COPY --from=control-plane-src`, a named build context, as an image; no Containerfile line can declare a context. Nothing was bypassed. The staged fix was kept as a patch in the session's scratchpad (SHA-256 `e045f2af…264e`), the tree was cleared back to `1458ce2`, and the patch re-applied cleanly afterwards.
  - The owner first chose a separate control fix (2026-11-06: "Control fix first (Recommended)"). While designing it, I found a second fault in a named context: a build that leaves out `--build-context` would pull an image named `control-plane-src` from Docker Hub, unpinned, under a name anyone can register. The owner then chose (2026-11-06: "Repo-root context (Recommended)"): build with the repository's root as the context, with an allowlist, so no build names a context, the check stands unchanged, and nothing can fall back to a pull. The empty branch made for the control fix (`stage1/hygiene-build-context`, no commits) was deleted.
  - For the backlog: `repo_hygiene.py` never reads `RUN --mount=... from=<image>`, so an unpinned image there would pass.
- **More test changes after the red commit, and why** (the build layout above):
  - `scripts/quality/tests/test_workflows.py`, `ControlPlaneInTheImage`: rewritten for the root context. Every OS image build ends `-f image/Containerfile .`; no build names `--build-context` or keeps the old `image` context; `.containerignore` is exactly its four lines; and the Containerfile's `COPY` lines are exactly the three expected. Its push-paths test and its pin of the Rust image are unchanged. Nothing is weaker: each requirement is now on the layout that ships.
  - `image/tests/test_installer.py`, `test_the_nodes_own_pinned_base`: the node's Containerfile now has two stages, so the installer's base is compared with the node's last one, the node's base. The test also now requires exactly two stages, the first the Rust image. Before, it compared the two single FROM lists.
- **A third set of test changes after the red commit, and why** (found by the green run and the mutants):
  - `image/tests/test_vm_drill.py`, `Verdict.test_every_check_names_a_step`: an existing test that pins the whole `EXPECTED` set. The fix adds the nine control plane cases to it, so the pinned set now names them too, one by one. It stays an exact-set check, so nothing is looser. Green failed on it before (`Ran 433 tests` `FAILED (failures=1)`).
  - `image/tests/test_greenboot_control_plane.py`, `test_anything_else_fails_with_what_was_seen`: three answers added, each a valid setup report under a status that is not 200 (421, 302, 404). The hand mutant that accepts any status below 500 survived every test, because the one refusal there carried no report and failed on that. Additions only.
- **Green** (rikuri-drill, `safe-run.sh`, `1172b3d` with the two test changes above): `image/tests` `Ran 433 tests` `OK`; `.claude/hooks` `Ran 91 tests` `OK`; `scripts/quality/tests` `Ran 160 tests`, with only the 7 known `git` errors (Not yet proven locally; CI's gate).
- **Hand mutants: 19 of 19 red** (18 at first, then the survivor above after the added answers):
  - greenboot's check: any status below 500 passing; `claimed` not checked as a boolean; the first answer passing whatever it is; giving up at once; never giving up;
  - `check_image_root.py`: the ELF check off; the service's capability bound, or the screen's `IPAddressDeny`, unchecked; a tty2 mask that may link anywhere; the screen not required enabled; the firewall overrides unchecked; greenboot's check not required;
  - `vm_drill.py`: more ports than 22, 80 and 443 allowed; the service's user unchecked; the policy's services unchecked; greenboot's success unread; a code in clear in the journal allowed; a claimed node passing; a case left out of `EXPECTED`.
- **Not yet proven:** every Rust test (CI's); the OS image build with the repository's root as its context and the `.containerignore` allowlist; the VM drill's nine checks on a booted image (CI's OS image workflow); Ctrl+Alt+F2 and the claim screen on the N150 (the owner's, after a publish).
