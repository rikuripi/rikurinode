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
