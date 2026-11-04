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
8. The N150 now starts from its own disk. After a minute or so the screen shows **Fedora Linux 45 (IoT Edition)** and a login prompt. That is the end of the install: no one can sign in yet (the setup page comes with 5c). Power the N150 off with a short press of its power button.

Report: whether it started from the stick, what the disk line said, and whether
it powered off by itself, then started to the login prompt. Photos of the screen are enough.

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
