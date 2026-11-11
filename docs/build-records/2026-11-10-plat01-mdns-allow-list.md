# Build Record — PLAT-01: mDNS only on the node's physical interfaces

| | |
|---|---|
| **Date** | 2026-11-10 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `stage1/plat01-mdns-allow-list`, from `main` at `88b1645`; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | (fill at close-out) |
| **Status** | IN PROGRESS |
| **Change type** | feature |

## Why

5c.2 (`docs/build-records/2026-11-10-5c2-names-and-mdns.md`, "PLAT-01") turned on systemd-resolved's mDNS for every link, the podman bridge included. The lessons register's PLAT-01 asks for more: "mDNS publishes only on an allow-list of physical interfaces derived at runtime, refuses to write an empty list, and restores its config if the name resolves to anything but the LAN address". Its tripwire: "Allow-list tests (mutation: a block-list fails)". The old node's port, `scripts/rikuri-mdns-interfaces-fix.sh` (hchengit/rikurinode, read on GitHub 2026-11-10, nothing run), did this for avahi: a physical interface is one with `/sys/class/net/<if>/device`; no physical interface is a refusal; and if the name does not resolve to the LAN address, the old config comes back. The owner (2026-11-10): "Next, for PLAT-01: can add list as follow-up task".

## Task Contract

1. **Outcome:** the node's mDNS name is answered only on interfaces with hardware behind them, whatever bridges and veths containers create or recreate, so a LAN client can never be handed a container bridge's address.
2. **Scope:**
   - **An experiment first** (disposable, in rikuri-drill, one question, 1 hour). On Fedora IoT, with resolved's global `MulticastDNS=yes`:
     - does `resolvectl mdns <link> no` stop resolved answering and announcing on that link, while the NIC still answers this Mac?
     - what does a bridge or veth that is created or recreated get?
     - does a resolved restart reset the per-link settings?
     - does a unit started by udev for a new link find the link already known to resolved?
     Keep, simplify or drop. The evidence is kept here and the VM's settings are restored.
   - `image/`, per the experiment:
     - a small root program, `rikuri-mdns-links`, in Python like the image's greenboot check. It derives the allow-list at each run: links with `/sys/class/net/<if>/device`, loopback never. It turns mDNS off on every other link resolved knows. It refuses, and fails loudly, when the list is empty. It then reads resolved's state back and fails if any link outside the list answers;
     - the units that run it whenever resolved starts and whenever a network link appears;
     - `check_image_root.py` for each new file, as closed worlds with their overrides.
   - `image/drill/vm_drill.py`: with a container running (a bridge and a veth present), resolved's mDNS is `yes` on the NIC only, and the program's last run succeeded.
   - The lessons register's PLAT-01 "Port" line records the port; the 5c.2 record's open decision is answered by a dated note.
   - Risk tier: **high-risk** (a root program on the node's network configuration; the LAN's view of the node's name).
   - **Not included:**
     - IPv6 or Wi-Fi specifics beyond what the allow-list's rule covers;
     - the control plane;
     - 5c.3 and later;
     - publishing mDNS services;
     - round 1's and round 2's other backlog nits from 5c.2.
3. **Done when:**
   - unit tests, red first: the allow-list from fixture sysfs trees (a NIC, a bridge, a veth, loopback, a Wi-Fi device, a renamed bridge); the empty-list refusal; the read-back check. Mutation: a block-list fails them;
   - the image checks' tests, and the drill's new checks' tests;
   - the experiment's answer is recorded, and the design follows it;
   - CI's VM drill passes the new checks, and every check it had;
   - `Full gate (Ubuntu)`, the tools' py3.9 and py3.12 jobs, and the OS image workflow pass on the PR;
   - one `verifier` pass has no Important finding;
   - Not provable in CI, and recorded as Not yet proven unless the owner runs it: what a LAN client receives on the N150 (QEMU's user network carries no multicast).
4. **Authority:**
   - the owner's words above; this branch; a draft PR; no merge;
   - rikuri-drill over its pinned SSH key, with `sudo` there (the owner's decision of 2026-10-21), for the tests and the experiment, whose changes are undone;
   - an mDNS query from this Mac to rikuri-drill (`dns-sd`, read-only);
   - reading the previous repository on GitHub (read-only).
5. **Limits:** one task; two repair cycles; two review rounds; CI at most 6 runs on the PR.

## Evidence log
- **The experiment** (2026-11-10, rikuri-drill: Fedora IoT 44 aarch64, systemd-resolved 259.10, Parallels' shared network; evidence in `docs/build-records/evidence/2026-11-10-plat01-mdns-allow-list/`; trailing blanks stripped). With a resolved drop-in `MulticastDNS=yes` and a container on podman's bridge:
  - `01-experiment.out`, B: `resolvectl mdns podman0 no` and `veth0 no` take effect at once (`Link 5 (podman0): no`, `Link 6 (veth0): no`).
  - C: the container stopped and run again: netavark removes and recreates `podman0`, and the new links (new link numbers 7 and 8) come back `yes`. A setting must be made again for each new link.
  - D: a resolved restart **keeps** the per-link settings.
  - E: a unit started by a udev rule's `SYSTEMD_WANTS` for each new link found it known to resolved at its first try (`podman0 1`, `veth0 1`) and turned it off.
  - `02-queries.out`: an mDNS question for `rikuri-drill.local` asked from inside the container, on the bridge. With `podman0` off (F, H): `answers: 0`. With it on, the control (G): `answer from 10.88.0.1: A ['10.88.0.1']`, twice. The first run's in-container questions (A, B and E in `01`) asked nothing, because `podman exec` without `-i` gave python an empty script; F to H are their rerun.
  - `03-mac-query.out`: from this Mac, with the bridge off, `rikuri-drill.local` still answered `10.37.129.3`, the NIC's address.
  - `04-undo.out`, `05-after.out`: the drop-in, the units, the rule and the container removed; `05` identical to `00-before.out` (`diff` empty, once the empty `/run/udev/rules.d` the experiment made was removed too).
  - **Answer: keep.** resolved's per-link setting does what PLAT-01 asks, and udev's per-link start reaches each new link in time. A run at resolved's start covers the links of the boot, and any that came before resolved.
- **Red** (`d83db2e`, rikuri-drill, `safe-run.sh`): `image/tests` `Ran 473 tests`, `FAILED (failures=2, errors=24)`. Every one is in the new tests: `test_mdns_links` cannot load a program not yet there; the `MdnsLinks` checker tests; the drill's `MdnsLinksReads` and `MdnsLinksSteps`; and Verdict's list. `.claude/hooks` `OK`; `scripts/quality/tests` only the 7 known errors.
- **A test change after red, with its reason** (in `04e4c7d`): in `MdnsLinks.test_overrides_are_findings`, the path `run/systemd/system/rikuri-mdns-links@.service.d/x.conf` became `usr/local/lib/systemd/system/…`, and `usr/local/lib/udev/rules.d/90-rikuri-mdns-links.rules` was added. `/run` is a tmpfs an image cannot ship, and the checker's unit model (`SUBID_UNIT_DIRS`, probed in systemd 259 for the subid unit) leaves it out on purpose. The test now asks for a folder the image can ship; one more override path is checked. Nothing loosened.
- **Green** (`04e4c7d`, rikuri-drill, `safe-run.sh`): `image/tests` `Ran 496 tests` `OK`; `.claude/hooks` `Ran 91 tests` `OK`; `scripts/quality/tests` only the 7 known errors.
- **The register's tripwire: a block-list fails.** Three weakenings of the program, each applied to a copy in rikuri-drill, running `test_mdns_links`:
  - M1, the allow-list replaced by a block-list of names (`veth`, `podman`, `docker`, `br-`): `FAILED (failures=5)`;
  - M2, the empty-list refusal removed: `FAILED (failures=2)`;
  - M3, the read-back removed: `FAILED (failures=4)`.
- **What the port leaves out, against the register's rule:**
  - "restores its config": there is no config file to restore. A link outside the list still answering fails the unit, so it shows in `systemctl --failed` and the journal, and the next start of resolved or of the link tries again.
  - "if the name resolves to anything but the LAN address": the node cannot see a LAN client's answer. The read-back checks resolved's per-link state instead, and the N150 report is the real view. Recorded in the register's Port line.

## Verifier, round 1 (2026-11-10): FAIL, one Important

- **I-1:** both units' `RestrictAddressFamilies=AF_UNIX` blocks the netlink socket that `resolvectl` (systemd 259) opens to find a link by name and to list links, so on the node every call would fail and the bridges keep answering. The verifier found it by reading systemd's source. **Seen in rikuri-drill** with the shipped `rikuri-mdns-links.service`, run as `exp-plat01b.service` from `/run/systemd/system`: its `ExecStart` pointed at a copy of the program under `/run`, its `[Install]` removed, and started by hand, not by resolved or udev. The template was not run; its `[Service]` differs only by the `%i` argument, and the real triggers are the drill's to prove (`06-shipped-units.out`):
  - **as shipped:** `could not turn mDNS off on podman0 after 5 tries: Failed to resolve interface "podman0": Address family not supported by protocol`, then `Failed to connect to netlink`; `Result=exit-code`, and `podman0` and `veth0` stayed `yes`;
  - **`AF_UNIX AF_NETLINK`:** `mDNS off on podman0`, `mDNS off on veth0`, `Result=success`, both `no`;
  - **`AF_UNIX AF_NETLINK` with `CapabilityBoundingSet=` empty:** the same. That confirms the verifier's N1: resolved lets root set a link's mDNS with no capability.
  - Undone; `08-after.out` is identical to `00-before.out`.

  The record's evidence before this had run the program only through a stand-in and an unhardened unit: the gap the verifier named.
- **Repair 1** (of two): red `9a2e1f8` (the checker's tests expect `AF_UNIX AF_NETLINK` and no capability; `image/tests` `FAILED (failures=9)`, all in `MdnsLinks`), fix `968db6e` (both units and the checker; `image/tests` `Ran 496 tests` `OK`, hooks `OK`, scripts only the 7 known errors). The test change after the first red is that red itself: the expected values, and four closed-world cases (a capability, every capability kept, the network, no netlink) for the two old ones. Nothing loosened.
- **Nits, backlog:**
  - N2, N3, N5: races. A link recreated, or a virtual link renamed, while its instance runs can stay answering until resolved next starts; a link made between a full run's listing and its read-back fails that run falsely.
  - N4: failures show only as failed units and in the journal; there is no greenboot wanted check or heartbeat.
  - N6: likely mutation survivors (the `code == 0` guard; `NAME`'s 15-character boundary).
  - N7: a later rule clearing `SYSTEMD_WANTS` is not detected.
  - N8: the rule's overrides list `run/udev/rules.d`, which the units' model leaves out as unshippable. Harmless.
  - N9: the drill reads resolved's per-link state, not a question asked on the bridge.

  N1's comments are fixed with I-1.

## Verifier, round 2 (2026-11-10): PASS, corrections only

I-1 is closed by `968db6e`, backed by evidence 06; no Important finding is open. Nits:
- R2-N1, the exact description of evidence 06: fixed above;
- R2-N2, backlog: `unit_problems` prints a missing `CapabilityBoundingSet=` as `CapabilityBoundingSet=...`.
