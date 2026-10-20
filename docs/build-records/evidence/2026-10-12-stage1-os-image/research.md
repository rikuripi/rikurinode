# Stage 1 research — facts checked 2026-10-12

Three research agents read these sources on 2026-10-12 for stage 1's start
(the plan's §2 asks for its facts to be re-checked when a stage begins). Each
fact carries its source; "not confirmed" means no source said it. The base
image digest and the greenboot configuration were re-read by the builder
(marked **checked**).

## Fedora IoT bootc base

- Fedora 45 is not released: target 2026-10-20, fallbacks 10-27 and 11-03
  (schedule, Wayback copy 2026-10-12:
  https://web.archive.org/web/20261012214117/https://fedorapeople.org/groups/schedule/f-45/f-45-key-tasks.html);
  8 accepted Final blockers, 1 proposed
  (https://qa.fedoraproject.org/blockerbugs/milestone/45/final/buglist).
- Images: `registry.fedoraproject.org/fedora-iot` and `quay.io/fedora/fedora-iot`
  serve the same digests; tags `44`, `44-x86_64`, `45`, `45-x86_64`, `46`
  (rawhide), `latest` (= 44); rebuilt daily. **quay.io deletes old digests
  within a day; registry.fedoraproject.org keeps them** (a 2026-06-01 digest
  still pulls). See also https://github.com/phoban01/flintlock-runner/issues/85.
  [Corrected 2026-10-12, verifier round 1: "within days", not "a day" — the
  cited case is a 2026-09-22 digest gone by 09-28 (404 on quay.io, 200 on
  registry.fedoraproject.org when the verifier looked).]
- **Checked** (registry manifest request, 2026-10-12):
  `fedora-iot:44-x86_64` = `sha256:29d16f4ccc5c86c84ba21aca0b7dcabfc4ecb2a79c9e51810f7838695f6be1c3`
  (an OCI image manifest; version 44.20261012.0); `fedora-iot:44` = index
  `sha256:c1445e4a55b317cf5a3dda58f83b4a506d9f54b182a2231ebcc5a6016e75ded1`.
- The IoT image adds greenboot, its default health checks, ignition, fdo,
  clevis (TPM2), firewalld and usbguard to the generic `fedora-bootc`, which has
  no greenboot (https://github.com/fedora-iot/fedora-iot-bootc/blob/main/iot-packages.yaml).
- The `fedora-iot:43` tag stopped updating on 2026-04-24, around 44's release.

## greenboot

- Fedora's greenboot is greenboot-rs, 0.16.4 in f43, f44 and f45 (built
  2026-08-19); upstream v0.16.4 is the newest
  (https://github.com/fedora-iot/greenboot-rs/releases).
- How rollback works (v0.16.4 source): `greenboot-healthcheck.service` runs
  before `boot-complete.target`; a failed required check runs `red.d`, sets
  GRUB's `boot_counter` to `GREENBOOT_MAX_BOOT_ATTEMPTS` and reboots; when the
  counter runs out greenboot runs `bootc rollback`. **A kernel panic or a hang
  before userspace is never counted.** [Contested 2026-10-12, verifier round
  1: greenboot 0.16.4's `detect_grub_fallback` (`src/main.rs`) reports a GRUB
  fallback "e.g. due to kernel panic on the new one", so GRUB's own counter
  may cover it. Not yet proven either way; stage 1's change 4 drills it.]
- **Open bug, no maintainer reply:** https://github.com/fedora-iot/greenboot-rs/issues/217
  (2026-10-09): a device from the stock IoT 44 image (greenboot 0.16.2) arms
  rollback with a variable 0.16.4 no longer reads, so the first failed update
  never rolls back. Reproduced on rpm-ostree IoT, not bootc.
- **Checked** (v0.16.4 source, `src/main.rs` and `etc/greenboot/greenboot.conf`):
  greenboot reads `/etc/greenboot/greenboot.conf` as INI; if it cannot, or a
  key is missing, it uses its defaults with only a debug message.
  `DISABLED_HEALTHCHECKS` must read `( "name" ... )`, anything else is an
  empty list with a warning; a disabled name that matches no script only
  warns. Fedora's required DNS check is
  `/usr/lib/greenboot/check/required.d/01_repository_dns_check.sh`.

## Install media and VM testing

- bootc-image-builder moved into `image-builder` (migration notice
  2026-06-18; https://github.com/osbuild/image-builder/blob/main/doc/20-advanced/20-bootc/50-migration.md);
  `ghcr.io/osbuild/image-builder-cli` v86.0.0 (2026-10-07) runs as
  `sudo podman run --privileged`. Open: Fedora 45 anaconda-iso failure
  (https://github.com/osbuild/image-builder/issues/2704); logically bound
  images fail to install in v82 (https://github.com/osbuild/image-builder/issues/2681).
- `bcvk` v0.21.0 (2026-10-05, pre-1.0; https://github.com/bootc-dev/bcvk):
  ephemeral VMs, persistent libvirt VMs that survive reboots, and `to-disk`.
- bootc's own CI boots images under bcvk on GitHub-hosted ubuntu runners
  (https://github.com/bootc-dev/bootc/blob/main/.github/workflows/ci.yml);
  greenboot's automatic-rollback test (install, update to an image with a
  failing check, reboot, assert `FALLBACK BOOT DETECTED!`) runs on Testing
  Farm (https://github.com/fedora-iot/greenboot/blob/main/tests/greenboot-bootc-qcow2.sh),
  which a private personal repository is likely not eligible for (not
  confirmed).
- No guided first-boot setup exists: zezere was retired in Fedora 42
  (https://fedoraproject.org/wiki/Changes/Retire_Zezere); Ignition and FDO take
  configuration files.

## CI runners and minutes

- Private repositories' standard `ubuntu-24.04` runner: 2 vCPU, 8 GB, 14 GB
  SSD (public: 4 vCPU, 16 GB) (https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
  KVM on 2-vCPU Linux runners since 2024-04-02
  (https://github.blog/changelog/2024-04-02-github-actions-hardware-accelerated-android-virtualization-now-available/);
  for private repositories **not confirmed** — this change's probe step answers it.
- GitHub Free: 2,000 minutes and 500 MB storage a month; Linux 2-core
  $0.006 a minute beyond (https://docs.github.com/en/billing/concepts/product-billing/github-actions).
  GHCR storage and transfer currently free
  (https://docs.github.com/en/billing/concepts/product-billing/github-packages).
- ubuntu-24.04 ships Podman 4.9.3; bootc's CI replaces it with newer packages
  (https://github.com/bootc-dev/actions/blob/main/bootc-host-setup/ci/workarounds.sh).
- Estimate (not measured): a VM rollback drill takes 40–70 minutes on 2 vCPU.

## Signing and publishing

- bootc pulls through containers/image: `/etc/containers/policy.json`
  (`sigstoreSigned`) and `registries.d` (`use-sigstore-attachments: true`)
  decide (https://github.com/podman-container-tools/container-libs/blob/main/image/docs/containers-policy.json.5.md).
  `--enforce-container-sigpolicy` (switch, install) also refuses a default of
  `insecureAcceptAnything` (https://www.mankier.com/5/bootc-install-config);
  whether an image switched to without it is still checked is **not
  confirmed** — a device drill settles it.
- **Keyless signatures from GitHub Actions cannot be enforced on the node
  yet:** the policy's `fulcio` block needs an email subject
  (https://github.com/podman-container-tools/container-libs/issues/34, open;
  PR #625 unmerged). Bluefin left its keyless images unenforced
  (https://github.com/projectbluefin/common/issues/1133).
- **cosign 3.x's default signature format is invisible to containers/image
  while `cosign verify` passes**; sign with `--new-bundle-format=false`
  (https://github.com/projectbluefin/common/issues/977: Bluefin shipped
  effectively unsigned images 2026-06-08 to 2026-08-15;
  https://github.com/podman-container-tools/container-libs/issues/388).
- A cosign signature names the repository, not the tag: an older signed image
  could be served as the newest (policy man page). The node's own version rule
  (plan §4.2) must hold against that.
- One unknown key in `policy.json` breaks every pull on the machine
  (https://github.com/projectbluefin/common/issues/1133).
- Rotation: `keyPaths` takes several keys; Bluefin ships a backup public key
  (https://raw.githubusercontent.com/projectbluefin/common/main/system_files/shared/etc/containers/policy.json).
- A GHCR package starts private, can be made public while the repository
  stays private, and that cannot be undone
  (https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).
