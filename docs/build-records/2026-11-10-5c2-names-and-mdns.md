# Build Record — 5c.2: the node answers as `rikurisetup.local`, and its certificate carries its address

| | |
|---|---|
| **Date** | 2026-11-10 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/5c2-names-and-mdns`, from `main` at `51a6fcc`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature |

## Why

Stage 1, change 5c, slice 2 of 4 (owner, 2026-11-06: "4 slices, 5c.1 first (Recommended)"). 5c.1 (`docs/build-records/2026-11-06-5c1-control-plane-on-node.md`) left out "`rikurisetup.local` and the node's LAN name or IP in its certificate (5c.2) … a browser by IP is 5c.2". Today the service sets no `RIKURI_NAMES`, so the server certificate names only `localhost` and the loopback addresses, and nothing on the node answers mDNS (Fedora IoT ships systemd-resolved with mDNS off, and no avahi: `rpm -q avahi nss-mdns`, `resolvectl status` in rikuri-drill, 2026-11-10). The owner's choices (2026-11-10): "systemd-resolved (Recommended)" for mDNS; "Names + current IP (Recommended)" for the certificate. The owner: "Yes, go back to stage 1 and B0 plan".

## Task Contract

1. **Outcome:** a browser on the node's LAN reaches the node at `http://rikurisetup.local` or at its IP address, fetches its CA, and then gets HTTPS that the CA verifies by either way in, with no name warning; when DHCP gives the node another address, the certificate follows without a restart.
2. **Scope:**
   - **An experiment first** (disposable, in rikuri-drill, one question, 1 hour): on Fedora IoT 44, does `MulticastDNS=yes` in resolved plus NetworkManager's per-connection mDNS default make resolved answer the hostname over mDNS on the NIC NetworkManager manages, and not on a podman bridge? Keep, simplify or drop; its evidence kept here, the VM's settings restored.
   - `image/`:
     - a resolved drop-in turning mDNS on (its own file; the LLMNR drop-in stays exactly as it is). Per the experiment (below), resolved answers on each link with that link's own addresses, so a LAN client never receives a container bridge's address (the lessons register's PLAT-01: a `.local` name once resolved to a Compose bridge); no per-link setting is needed;
     - the node's hostname `rikurisetup` until naming (5c.4) renames it, set so an update keeps a name the node has since been given;
     - the firewalld policy `rikuri-node` gains `mdns` (UDP 5353);
     - the service's `RIKURI_NAMES=rikurisetup.local`;
     - `check_image_root.py` for each.
   - `control-plane/`:
     - the server certificate also names the node's current LAN address (the source address of the route to TEST-NET-1, as the claim screen finds it);
     - the daemon looks again at start and every 60 s; on a change it reissues the server certificate from the node's CA and serves it to new connections without a restart (a rustls certificate resolver over a lock; no new crate). The CA is never reissued. The issue is logged with the names, never a key.
   - `image/drill/vm_drill.py`: from outside the VM, HTTPS verified against the node's CA as `rikurisetup.local` and as the guest's address (with the probe's host route, as 5c.1's address check has it); in the VM: the hostname, resolved's mDNS on the NIC and off on loopback, UDP 5353 bound, the policy's three services.
   - Knowledge layer: the install runbook's claim-screen step (the way in by name and by address), README's status.
   - Risk tier: **high-risk** (a new listener on the LAN, mDNS; the certificate a browser trusts).
   - **Not included:** the setup page (5c.3); naming, the UUID and the SetupHub (5c.4); IPv6 addresses in the certificate; publishing mDNS services (DNS-SD); the root helper (D13); UPS (D22).
3. **Done when:**
   - unit tests, red first, for the certificate's names with and without an address, the reissue on a change and none without one, the resolver serving the new certificate to a new connection, the image's new files, and the drill's new checks;
   - the experiment's answer is recorded, and the design follows it;
   - CI's VM drill on the image built from this change passes the new checks, and every check it had;
   - `Full gate (Ubuntu)`, the tools' py3.9 and py3.12 jobs, **Rust mutants** on the changed lines, and the OS image workflow pass on the PR;
   - one `verifier` pass has no Important finding.
   - Not provable in CI, and recorded as Not yet proven unless the owner runs it: a phone or laptop on the N150's LAN opening `http://rikurisetup.local` (QEMU's user network carries no multicast).
4. **Authority:** the owner's words above; this branch; a draft PR; no merge. rikuri-drill over its pinned SSH key, with `sudo` there (the owner's decision of 2026-10-21), for the tests and the experiment, whose changes are undone; an mDNS query from this Mac to rikuri-drill (`dns-sd`, read-only, on the Parallels network).
5. **Limits:** one task; two repair cycles; two review rounds; CI at most 6 runs on the PR.

## Evidence log

- **The experiment** (2026-11-10, rikuri-drill: Fedora IoT 44 aarch64, systemd-resolved 259.10, Parallels' shared network; evidence in `docs/build-records/evidence/2026-11-10-5c2-names-and-mdns/`). Question: does resolved's mDNS answer on the NIC and not hand a LAN client a container bridge's address?
  - `00-before.out`: mDNS `Global: no`, `enp0s5: no`; NetworkManager's `connection.mdns` `-1` (default); Fedora's `public` zone already allows `mdns`; UDP 5355 (LLMNR) bound, 5353 not.
  - `01-case-a-global-only.out`: with a container on podman's bridge and only `MulticastDNS=yes` in a resolved drop-in, mDNS is `yes` on **every** link, `enp0s5`, `podman0` and `veth0`; UDP 5353 bound. From this Mac, `dns-sd -G v4 rikuri-drill.local` answered `10.37.129.3`, the NIC's address only.
  - `02-case-b-nm-default.out`: adding NetworkManager's `connection.mdns=2` changes nothing; the bridge follows the global setting.
  - `03-mac-query-v4v6.out`: `dns-sd -G v4v6` from the Mac: `10.37.129.3`, the NIC's ULA and its link-local address; never `podman0`'s `10.88.0.1` or its link-local.
  - `04-after.out`: the drop-ins removed and the container stopped; identical to `00-before.out` (`diff` empty). The kept copies have trailing blanks stripped (the pre-commit whitespace check); nothing else changed.
  - **Answer: keep, simplified.** One resolved drop-in. resolved answers per link with that link's addresses, so the LAN sees only the LAN's; the responder on a bridge answers only the containers there, with the bridge's address, which they already have as their gateway. NetworkManager's setting is dropped from the design: it does nothing here.
- **Red** (`851444f`, rikuri-drill, `safe-run.sh`): the tests, the control plane with two stubs (`san_names` ignores the LAN address; `refresh` serves the old certificate again), and none of the image's files, checks or drill code. `image/tests`: `Ran 454 tests`, `FAILED (failures=8, errors=22)`, every one a new or changed 5c.2 test: the mDNS file, the hostname, the policy's `mdns`, the unit's `RIKURI_NAMES`, `mdns_on`, `mdns_listens`, the three-service policy, and every `ControlPlaneSteps` test (the stand-in VM answers `NIC`, which the drill did not have yet). `.claude/hooks`: `Ran 91 tests` `OK`. `scripts/quality/tests`: `Ran 176 tests`, only the 7 known errors (the archive copy has no git checkout). The Rust red is CI's (the Mac runs no Rust tests): the first run on the PR.
- **Green, first try** (`28b7242`): `image/tests` `FAILED (failures=3)`. Two consequences of the change that the red commit missed: the fixture's `/etc` now holds five files, not four (`etc/hostname`; `test_main_exit_codes`, `test_scan_report_names_every_tree`), and `Verdict.test_every_check_names_a_step` lists every drill check by name (five new ones, and the firewall check renamed "the firewall opens 80, 443 and mDNS").
- **Test changes after red, with their reason** (`bc7391a`): the two counts `4` → `5`, and the five names added to Verdict's list with the one renamed. Nothing loosened: a count is still exact, and the list is still the whole of `EXPECTED`. Also in the red commit, two cases moved out of `test_each_failure_fails_its_own_case` into `test_a_wrong_or_missing_route_source_fails_the_screen_and_the_address`: a wrong or missing route source now fails the address check too, by design (the address HTTPS is tried as is the route's source), so they fail two cases, and the new test asserts exactly those two.
- **Green** (`bc7391a`, rikuri-drill, `safe-run.sh`): `image/tests` `Ran 454 tests` `OK`; `.claude/hooks` `Ran 91 tests` `OK`; `scripts/quality/tests` `Ran 176 tests`, only the 7 known errors. On the Mac: `cargo clippy --all-targets --locked -- -D warnings` and `cargo fmt --check` clean (rustc 1.98.1).
- **The drill's address check waits for the daemon.** QEMU's restricted network has no default route, so at boot `console::lan_address` finds none and the certificate names no address. With the probe's host route in place the daemon finds `10.0.2.15` at its next look (60 s); the drill tries HTTPS as that address up to 30 times, 5 s apart, before it removes the route. That proves the reissue without a restart on the image itself, not only in the Rust test.

## PLAT-01: the lesson's outcome, by another mechanism

The lessons register's PLAT-01 rule says "mDNS publishes only on an allow-list of physical interfaces derived at runtime", with allow-list tests as its tripwire. That was the cure for avahi, which announced every address on every interface, so the LAN received a Docker bridge's. This change has no allow-list: resolved's mDNS is on for every link, the podman bridge included. The experiment (`01` and `03` above) shows why the lesson's failure cannot happen with resolved: it answers on each link with that link's own addresses, so from the LAN `rikurisetup.local` resolved only to the NIC's IPv4, ULA and link-local addresses, never `podman0`'s. What the design gives up against the rule: resolved also answers on the bridge, to the containers, with the bridge's address (their gateway already), and listens there. The register's rule text is unchanged: whether it is clarified to "the LAN receives only the LAN's addresses" or an allow-list is added is the owner's decision (asked at close-out).
