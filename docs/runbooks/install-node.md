# Runbook — install the node on the N150 from the USB stick

Who: the owner. Where: a Mac (or any computer) to make the stick, then the
N150 with a screen and a keyboard; no command line on the N150. How long: about
half an hour. What it does: writes the install stick of one published release
onto a USB stick, then, on the N150, erases its one internal disk and installs
the node from the stick, with no network. The installed node updates from
`ghcr.io/rikuripi/rikurinode` under that release's fixed name.
**Everything on the N150's internal disk is lost.**

Stage 1 changes 5b, 5c.1, 5c.2 and 5c.3a. The node's screen keeps a login
prompt nobody can use; a second screen, the claim screen, shows the node's
address, its certificate fingerprint and a claim code; and a browser on the
same network opens the node's first setup pages: one that installs the node's
certificate, then a private page where you check that fingerprint. Claiming
the node with the code comes with a later update (5c.3b): that is the expected
result. Workflow:
`.github/workflows/publish.yml`, job **Build the USB installer from the signed
digest, with no credential**; records:
`docs/build-records/2026-10-29-install-media.md`,
`docs/build-records/2026-11-06-5c1-control-plane-on-node.md`,
`docs/build-records/2026-11-10-5c2-names-and-mdns.md`,
`docs/build-records/2026-11-11-5c3a-ui-pipeline.md`.

## What you need

- A USB stick of 8 GB or more. Writing the install stick erases it.
- The N150 with a screen and a keyboard. Unplug USB drives and memory cards
  other than the stick. The installer never offers a USB or removable disk.
  A memory card in a built-in card reader can look like an internal disk to
  it, and would then be listed by number: take any card out first.
  If the N150 has more than one internal disk (for example a built-in 64 GB
  eMMC and an SSD), it lists them and you pick one.
- No network cable is needed on the N150.

## 1. Get the install stick's file

Each publish (`docs/runbooks/publish-os-image.md`) keeps it for 90 days.

1. On GitHub, open the repository's **Actions** tab, then **Publish the OS image**, then the run to install.
2. Its summary shows **Install media: rikuri-node-&lt;name&gt;.iso** and its SHA-256. Under **Artifacts**, download **install-media**. It is a zip file of about 1 GB, holding the `.iso` and its `.sha256`.
3. Unzip it, then check the file. In Terminal.app, with the name the run shows:

   ```bash
   cd ~/Downloads/install-media && shasum -a 256 -c rikuri-node-<name>.iso.sha256
   ```

   It must say `rikuri-node-<name>.iso: OK`. Any other answer: delete the folder and download it again. Never write a file that did not say OK.

## 2. Write the USB stick

Use Fedora Media Writer (Fedora's own tool, free, from `fedoraproject.org/workstation/download`). It writes only to removable drives, so it cannot erase the Mac's disk by mistake.

1. Plug in the USB stick, and open Fedora Media Writer.
2. Choose **Select .iso file**, then the `rikuri-node-<name>.iso` you checked.
3. Choose the USB stick, then **Write**. Enter the Mac's password if it asks. Wait until it says it is finished.
4. Eject the stick.

## 3. Install on the N150

1. With the N150 off, plug in the stick, the screen and the keyboard.
2. Power it on and press the boot-menu key straight away, several times. On N150 mini PCs it is usually **F7**, **F11** or **F12** (sometimes **Esc**). Choose the USB stick; if it is listed twice, choose the one that starts with **UEFI**.
   - If the machine says the stick is not trusted, or shows a **Secure Boot** error: stop, note the exact words or take a photo, and report it. Do not change the firmware's settings: that is a decision still to make.
3. A menu shows **Install Rikuri Node** for one second, then text scrolls. After about a minute the installer starts.
   - **If the N150 has more than one internal disk,** it lists them first, numbered:

     ```
     Rikuri Node installer
     This machine has more than one internal disk. Pick the one for the node; everything on it will be lost:
       1) <model>, 63 GB, serial <serial> (/dev/mmcblk0)
       2) <model>, 2000 GB, serial <serial> (/dev/nvme0n1)
     Type the number of the disk to erase and press Enter. Anything else stops:
     ```

     Type the number of the disk for the node (the large SSD, by its size) and press Enter. Anything else erases nothing and stops. The installer then names that one disk and asks for `ERASE`, as below.
   - With one internal disk, it shows that disk straight away:

   ```
   Rikuri Node installer
   This disk will be erased, and everything on it lost:
     <model>, <size> GB, serial <serial> (/dev/<name>)
   Type ERASE and press Enter to erase it and install Rikuri Node. Anything else stops:
   ```

4. Check that the model and size are the disk you mean. If they are not, or you are unsure, press Enter: nothing is erased, and the next line asks you to press Enter again to power off.
5. Type `ERASE` in capitals and press Enter. It says **Installing** and takes a few minutes. Do not power off.
6. When it says **Rikuri Node is installed. This machine powers off in 15 seconds.**, wait: the N150 powers off by itself, and the screen goes dark.
7. Take the USB stick out, then press the N150's power button.
   - If you power it on with the stick still in, many machines start from it again and the installer appears again, as if nothing happened. The node is installed: press Enter at the installer's question (nothing is erased), then Enter again to power off; take the stick out, and power on.
   - If the firmware says it has no boot device, set its boot order to the internal disk you picked (on the N150 it was listed by its maker, ORICO), and change nothing else there.
8. The N150 now starts from its own disk. After a minute or so the screen shows **Fedora Linux 45 (IoT Edition)** and a login prompt. No one signs in there: the node is set up from a browser, from step 10 on.
9. Hold **Ctrl** and **Alt** and press **F2**. The claim screen appears:
   - **Address**: the node's address on your network, such as `http://192.168.1.20`. If it says **none yet**, connect the N150 to your router with a network cable; press Enter to look again.
   - The node also answers by name: on a phone or computer on the same network, `http://rikurisetup.local` reaches it as well as the address does. Some networks and some phones do not find `.local` names; the address always works. If the router later gives the node another address, the screen shows it when you press Enter, and the node follows it by itself within a minute.
   - **Certificate fingerprint**: two lines of letters and numbers. In step 11 your browser shows the node's fingerprint; it must be the same.
   - **Press Enter to show a claim code.** Enter shows a code such as `K7QM-4XD9-TR`. Whoever types it on the setup page first becomes the node's owner, so show it only to yourself. It lasts 24 hours and works once; Enter again replaces it, and the old one stops working. Once the node is claimed, Enter shows no code.
   - Ctrl+Alt+F1 returns to the login prompt. Leave the N150 on for the next steps.
10. On a phone or computer on the same network, open the address the claim screen shows (or `http://rikurisetup.local`). The page **Let's make this connection private** opens. Pick your device if it did not guess it, tap **Download the certificate**, and follow the three steps the page lists for that device; they install **Rikuri Node CA** on that device only. Then tap **Continue securely**.
    - If the browser warns that the connection is not private, the certificate is not installed yet, or not trusted: go back and finish the three steps. Do not click past the warning.
    - If the browser skips this page and goes straight to that warning, it remembers the node's address from an earlier test, when the node sent every page on to `https://`. Clear that browser's history and site data for the address (or use a private window), and open it again.
11. The page **The connection is private** opens, with a padlock beside the address. Check the fingerprint of **Rikuri Node CA**, the certificate you installed, as your device shows it, never as a page shows it. The claim screen (Ctrl+Alt+F2 at the node) shows that certificate's fingerprint; the padlock first opens the node's own certificate, which Rikuri Node CA signs and whose fingerprint is different, so go one step up:
    - **On a computer:** click the padlock, open the certificate, go to its chain (**Details** or **Certificate Hierarchy**), pick the top one, **Rikuri Node CA**, and find its **SHA-256** fingerprint.
    - **On iPhone or iPad** (Safari shows no certificate): Settings › General › VPN & Device Management › **Rikuri Node CA** › More Details, and its **SHA-256**.
    - **On Android:** Settings, search for **Trusted credentials**, its **User** tab, **Rikuri Node CA**, and its **SHA-256**.
    - Compare it with the claim screen's. They must match exactly.
    - If they do not match, stop: unplug the node's network cable and report it. Something on your network may be pretending to be the node.
    - The page's **Your node** box says **Waiting to be claimed** and lists the node's names.
12. Only when the fingerprints match, tap **Claim this node**. The page **Claim your node** opens.
    - **Claim code**: at the node, Ctrl+Alt+F2 and Enter, and type the code it shows. Capitals or not, with or without the dashes, all work.
    - **New password**, then **The same password again**: at least 12 characters (the line under the field ticks when it has enough). A few unrelated words, like `harbor violet tractor maple`, are long and easy to remember. **Show passwords** shows what you typed.
    - Write the password down or keep it in a password manager. Nothing can reset it yet: if it is lost, the node cannot be claimed again until a later update brings a reset at the node.
    - Tap **Claim this node**. **This node is yours** opens. Under **What setup still needs** it shows the node's **Node ID** (letters, numbers and dashes, the node's own for its whole life) and each step of setup:
      - **A private connection** and **An owner and a password**: **Done**;
      - **A name for the node**: **Next**. Naming the node comes with the next update;
      - **Bitcoin**, **Lightning** and **Backups**: **Comes with a later update**.
      - A step that says **Couldn’t be read** is not done: report it. Below the list, the page says until when this device stays signed in.
    - If it says the code is not the one on the node's screen, check it against the screen (a code lasts 24 hours; Enter at the node shows a new one) and type it again. After several wrong tries it asks you to wait a number of seconds; the button returns when they are over.
    - If it says the node already has an owner, someone has claimed it. If that was not you, stop: unplug the node's network cable and report it.
13. Tap **Sign out**: the page **Sign in to your node** opens. Type the password and tap **Sign in**: **This node is yours** opens again, with the same **Node ID**. Sign out again, then power the N150 off with a short press of its power button.

Report: whether it started from the stick, what the disk line said, whether
it powered off by itself and started to the login prompt, and what the claim
screen showed after Ctrl+Alt+F2 (an address, the fingerprint, and a code after
Enter), whether a phone or computer on the same network reached
`http://rikurisetup.local` ("cannot find" or "server not found" means it did
not), which device you installed the certificate on and whether its steps
worked as the page said, whether the browser's fingerprint matched the
claim screen's, and whether claiming, signing out and signing in worked as
steps 12 and 13 say, and what **What setup still needs** listed. Photos of the screens are enough; never photograph or
send the password. A photo of a code is harmless once the node is claimed, as
that code no longer works.

## When it stops

Every stop in the table erases nothing; press Enter to power off.

| The installer says | Meaning, and what to do |
|---|---|
| No internal disk was found to install on. | It found no disk it may use. Report the model of the N150. |
| The installer cannot tell which disk is this USB stick … | It will not risk erasing the stick, or a disk it cannot tell apart from it. Write the stick again, or try another stick. |
| This USB stick is damaged or incomplete. | Write the stick again from the checked file. |
| Nothing was erased. | Something other than a listed number, or other than `ERASE` in capitals (`Erase` stops too), was typed. Start again to install. |

**The installer stopped on an unexpected error.** It shows the error under that
line. If it had not yet said **Installing**, nothing was erased; if it had, the
disk may be partly erased, as below. Take a photo
of the whole screen and report it, then follow the last line: press Enter, or
hold the power button until the N150 is off.

One stop can follow an erase: **The install failed. The disk may be partly
erased; nothing else was changed.** Power off, start again from the stick, and
report what the screen showed above that line.
