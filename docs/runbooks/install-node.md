# Runbook — install the node on the N150 from the USB stick

Who: the owner. Where: a Mac (or any computer) to make the stick, then the
N150 with a screen and a keyboard; no command line on the N150. How long: about
half an hour. What it does: writes the install stick of one published release
onto a USB stick, then, on the N150, erases its one internal disk and installs
the node from the stick, with no network. The installed node updates from
`ghcr.io/rikuripi/rikurinode` under that release's fixed name.
**Everything on the N150's internal disk is lost.**

Stage 1 change 5b. The installer's setup page does not exist yet (5c), so after
the install the node shows only a login prompt nobody can use: that is the
expected result. Workflow: `.github/workflows/publish.yml`, job **Build the USB
installer from the signed digest, with no credential**; record:
`docs/build-records/2026-10-29-install-media.md`.

## What you need

- A USB stick of 8 GB or more. Writing the install stick erases it.
- The N150 with a screen and a keyboard. Unplug every other disk from it: USB
  drives, memory cards. The installer refuses a machine with more than one
  internal disk, and never installs on a USB disk.
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
3. A menu shows **Install Rikuri Node** for one second, then text scrolls. After about a minute the installer shows:

   ```
   Rikuri Node installer
   This disk will be erased, and everything on it lost:
     <model>, <size> GB, serial <serial> (/dev/<name>)
   Type ERASE and press Enter to erase it and install Rikuri Node. Anything else stops:
   ```

4. Check that the model and size are the N150's internal disk. If they are not, or you are unsure, press Enter: nothing is erased, and the next line asks you to press Enter again to power off.
5. Type `ERASE` in capitals and press Enter. It says **Installing** and takes a few minutes. Do not power off.
6. When it says **Rikuri Node is installed. Remove the USB stick now.**, take the stick out. The N150 restarts by itself 15 seconds later.
7. The N150 now starts from its own disk. After a minute or so the screen shows **Fedora Linux 44 (IoT Edition)** and a login prompt. That is the end of the install: no one can sign in yet (the setup page comes with 5c). Power the N150 off with a short press of its power button.

Report: whether it started from the stick, what the disk line said, and whether
it restarted to the login prompt by itself. Photos of the screen are enough.

## When it stops

Every stop below erases nothing; press Enter to power off.

| The installer says | Meaning, and what to do |
|---|---|
| This machine has more than one internal disk … Found: | It lists them. Unplug every disk but the N150's own, and start again. |
| No internal disk was found to install on. | It found no disk it may use. Report the model of the N150. |
| The installer cannot tell which disk is this USB stick … | It will not risk erasing the stick, or a disk it cannot tell apart from it. Write the stick again, or try another stick. |
| This USB stick is damaged or incomplete. | Write the stick again from the checked file. |
| Nothing was erased. | Something other than `ERASE` was typed. Start again to install. |

One stop can follow an erase: **The install failed. The disk may be partly
erased; nothing else was changed.** Power off, start again from the stick, and
report what the screen showed above that line.
