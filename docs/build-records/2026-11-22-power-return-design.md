# Build Record — design note: the SetupHub's power-return step (stage 1, plan §4.1)

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Author / session** | Claude (Opus 5.5, desktop Code session) for Henry Chen |
| **Branch** | `docs/power-return-design`, from `main` at `9345ee7`; a draft PR; worktree `/Users/hchome/rikurinode/.claude/worktrees/linux-security-research-eb820b` |
| **Commits** | `2587ff1` (contract), then the note on this branch |
| **Status** | DONE (the step's state is the owner's choice, below) |
| **Change type** | design note (documentation only) |

## Intent: the owner's words

- **"Next"** (2026-11-22), after the stage 1 analysis (in the session). Its Next: a design note for the power-return step: what the SetupHub says, what Linux can read on the N150 and the Pi, and which state it shows, with the owner's choice between "can't be checked here" and "done when the owner confirms".
- The plan, §4.1: every node "must start by itself when power returns (stage 1): the setup page explains the N150 firmware's power-on-after-power-loss setting once, and checks it where the firmware lets Linux read it."

## Task Contract

1. **Outcome:** the owner can choose how the power-return step works from one note that says what each choice shows and what Linux can and cannot read.
2. **Scope:** routine (documentation).
   - This record, holding the design note.
   - **Not included:** any code, page, string or test; the step itself (a task of its own, after the owner's choice); an experiment on the N150.
3. **Done when:** the note states what Linux can read on the N150 and the Pi with its sources, the options for the step's state with their costs, and a recommendation; link checks and `git diff --check` pass; CI's `Full gate (Ubuntu)` passes on the draft PR.
4. **Authority:** this file. Web searches (reading only; nothing downloaded). Commit and push this branch; a draft PR to `main`; the owner merges. No verifier pass: documentation only (AGENTS.md §5).
5. **Limits:** one task; two repair cycles and two review rounds. No budget is configured; time is reported.

## The design note

### What the step is for

- After a power cut, a node must start again by itself: the owner should never have to press its button. On the N150 that is a firmware setting, usually called "power on after power loss" or "AC power recovery" (its name, menu and default vary by board). On the Pi 5 it is the board's default.
- The owner meets the setting once, at setup. After that, the drill's boot-cause record (D22) already says when a boot followed a power cut.

### What Linux can read

| Machine | Source | What it says | Usable? |
|---|---|---|---|
| N150 | The chipset's `AFTERG3_EN` bit in its power-management configuration register (Intel's PCH datasheets; [Intel 700-series PCH](https://edc.intel.com/content/www/jp/ja/design/products-and-solutions/processors-and-chipsets/700-series-chipset-family-platform-controller-hub-datasheet-volume-1-of/pch-and-system-power-states)) | Whether the chipset boots when power returns | **No.** The bit's place differs by chipset (coreboot names it differently per platform, e.g. [Cannon Lake's `pmc.c`](https://git.ch1p.io/coreboot.git/tree/src/soc/intel/cannonlake/pmc.c)), the N150's offset is not confirmed, reading it needs raw access to chipset memory as root, and a board's embedded controller can decide power-on itself. A root tool that reads chipset memory is a risk this node should not carry for one setting. |
| N150 | The firmware's own setup variables (UEFI) | The setting, in a layout private to each firmware vendor | **No.** No public layout; a different board means a different offset. |
| N150 | SMBIOS type 1, "Wake-up Type" (DMTF [DSP0134](https://www.dmtf.org/sites/default/files/standards/documents/DSP0134_3.6.0.pdf), §7.2.2; value `08h` is "AC Power Restored", per [U-Boot's table](https://lists.denx.de/pipermail/u-boot/2024-February/545667.html) and [smbios-lib](https://docs.rs/smbios-lib/0.8.1/smbioslib/enum.SystemWakeUpType.html)) | What woke **this** boot, not the setting | **Maybe, as evidence after the fact.** Firmware commonly reports "Power Switch" (as in [a sample `dmidecode` output](https://openbenchmarking.org/system/1808056-AR-DELLXPS1381/Dell%20XPS%2013%209370/dmidecode)); what the owner's N150 reports is **not yet proven**. Read as root from `/sys/firmware/dmi/tables/DMI`. |
| N150 | The boot-cause history (`image/rootfs/usr/libexec/rikuri/boot-cause`, the last 100 boots in `/var/lib/rikuri/boot-cause/history.jsonl`) | Whether a boot followed a power cut (`power-cut`) | **Yes, but it cannot tell** a node that came back by itself from an owner who pressed the button. |
| Pi 5 | The bootloader's EEPROM settings: it starts when power is connected unless `WAIT_FOR_POWER_BUTTON=1` (with `POWER_OFF_ON_HALT=1`) is set ([Raspberry Pi: getting started](https://www.raspberrypi.com/documentation/computers/getting-started.html); [Pi 5 hardware](https://www.raspberrypi.com/documentation/hardware/raspberrypi5/)) | The setting itself | **Not yet proven on Fedora.** Raspberry Pi's tool reads it through its own firmware interface; whether Fedora IoT on the Pi exposes it is not checked. The Pi waits on D1 in any case. |

- **So:** on the N150, Linux cannot read the setting itself. It can, at most, see that a boot followed a power cut, and perhaps what the firmware says woke it.

### The options for the step's state

The SetupHub's rule (`control-plane/crates/rikuri-control/src/hub.rs`): each step is "read from the node's state at the time of the request, never from a flag of our own", and "Could not be read" is never shown as done.

| Option | What the step shows | Keeps the hub's rule? | Cost |
|---|---|---|---|
| **A. Explained, never done** | The explanation and how to find the setting, with "Can't be checked on this machine": a state of its own, so it is not mistaken for a failed read | Yes | One new state and its text. The owner may never see the step close. |
| **B. Done when the owner confirms** | The explanation and a button "I've set it"; then Done | **No:** done from a stored flag, not from the node's state | The first stored wizard state (hub.rs: it "comes with the first step that takes input"), so a store, its tests, and its resume. A confirmation does not show the setting is right. |
| **C. Done when seen** | The explanation, and "Unplug the node, wait ten seconds, plug it back in; don't press its button". Done once the boot-cause history holds a `power-cut` boot after setup began (and, if the N150's firmware proves to report it, SMBIOS "AC Power Restored") | Yes: from the node's own record | A deliberate power cut at setup. Safe in stage 1 (no wallet; the drill cuts power the same way), but not once LND runs. It cannot tell a button press from a power-on by itself, unless SMBIOS says so. |

### Recommendation

- **A now; C later, only if an N150 check shows its firmware reports "AC Power Restored".** A is small, keeps the hub's rule and tells the owner the truth. C is the only option that observes the behaviour, but without the wake-up type it proves less than it seems; a short owner-run check on the N150 settles that. Whoever runs it reads SMBIOS once after an unplug, but the node has no shell sign-in, so it needs a design of its own.
- **B is not recommended:** it is the hub's first flag of its own, and it records a belief rather than the node's state.
- **The choice is yours.** The step's task starts only after it.

## Evidence log

- Sources read: the plan §4.1; `hub.rs`, `restart.rs`, `boot-cause`, `ui/src/i18n/en.json` and the install record `2026-11-03-install-n150.md` on `main` at `9345ee7`. Four web searches (results pages only; no page fetched, nothing downloaded). The links above are what those searches returned. Two were not opened: the DSP0134 PDF (its table of contents only) and Intel's register tables. The coreboot claim comes from the search's summary of that file, not from reading it.
- **Not yet proven:** the N150's SMBIOS wake-up type after a power cut; its firmware's default for the setting; Fedora's view of the Pi 5's EEPROM settings.
- Checks: `git diff --check` clean. No relative links in this record: repository paths are in backticks; its links are the outside sources above, taken from the search results.

## Result

- **Done:** the note states what Linux can and cannot read on the N150 and the Pi, three options for the step's state, and a recommendation (A now, C after an N150 check).
- **The owner's decision:** A, B or C. The step itself is a task of its own, not started.
