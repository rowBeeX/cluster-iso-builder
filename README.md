# Cluster NixOS ISO Builder

Builds the x86_64 NixOS 26.05 installer used to provision the local and public
development clusters. The build is isolated in a digest-pinned Podman image;
the exact nixpkgs revision is pinned by `flake.lock`.

This repo sits *upstream* of everything else in the monorepo. It defines no
runtime services, no networking, no DNS and holds no secrets; it only emits the
installer ISO that boots bare-metal hosts before any NixOS config, k3s, Cilium,
Envoy Gateway or ArgoCD exists on them.

## How the ISO is used downstream

The ISO is a live NixOS installer that bootstraps a target host:

1. Boot the ISO on the target hardware (a local-cluster or public-cluster node).
2. SSH into the live installer as `root`. Authentication is key-only: the single
   baked operator ed25519 key is the only accepted credential; password and
   keyboard-interactive auth are refused (`configuration.nix`).
3. Partition and format the disks and run `nixos-install` (`nixos-install-tools`)
   via `install_dev_host.py` from `cluster-testing`, pointing at the host's flake
   in the matching `*-nix` repo (`local-cluster-nix` / `public-cluster-nix`).
   Partitioning is done imperatively with `gptfdisk`/`parted` + `mkfs`; the disk
   UUIDs are fixed and mirror each host's `hosts/dev/*/storage-map.nix`.
4. Reboot into the installed system. From there the node runs its NixOS config
   (k3s, Cilium CNI + L2 announcement, the Envoy Gateway edge, ArgoCD, etc.);
   none of that lives in this repo.

The tools baked into the installer exist to support exactly this bootstrap:
`gptfdisk`/`parted` (partitioning), `sops`/`age` (decrypting host secrets during
install), `nixos-install-tools`, the `zfs`/`btrfs-progs`/`lvm2`/`mdadm`/
`nfs-utils` storage stacks, and `python3`/`rsync`/`git` for the install
automation. The ISO carries no secrets itself; `sops`/`age` are for the
post-boot step.

```mermaid
flowchart LR
  dev["operator: build.sh --check / build.sh"] --> img["podman image (Containerfile, digest-pinned nixos/nix)"]
  img --> build["container-build.sh: nix build .#installerIso (flake.lock)"]
  build --> art["artifacts/: ISO + .iso.sha256 + meta/output-iso.json"]
  art --> boot["boot ISO on target host, SSH in with operator key"]
  boot --> install["install_dev_host.py: partition + nixos-install from the host's *-nix flake"]
  install --> node["running cluster node (k3s, Cilium, Envoy Gateway, ArgoCD)"]
```

## Build

```bash
./build.sh --check
./build.sh
```

`build.sh` is the entry point; it builds the Podman image if needed and runs
`scripts/container-build.sh` inside it. That script performs the actual `nix build`
and writes the ISO, checksum and metadata to `artifacts/`.

The `artifacts/` directory and all common image formats are ignored by Git.
A reference ISO is not required; Nix builds the installer directly from the
locked inputs.

Use `REBUILD_IMAGE=1 ./build.sh` or `./build.sh --rebuild` after changing the
`Containerfile`.

## Installer contents

The image enables key-only SSH for the configured operator key and includes
the tools needed by the cluster installation automation: Python, rsync,
SOPS/age, gptfdisk/parted, ZFS, Btrfs, LVM, mdraid, NFS and common diagnostics.

## Updating inputs

Update deliberately inside the build container, review the lock-file diff,
then run a complete build:

```bash
# Reuse the image build.sh already built. The tag defaults to build.sh's own
# default (or your $NIX_IMAGE override); it is never hard-coded here.
image="${NIX_IMAGE:-$(sed -n 's/.*NIX_IMAGE:-\(.*\)}"/\1/p' build.sh)}"
podman run --rm -v "$PWD:/workspace:Z" -w /workspace \
  --entrypoint bash "$image" -lc 'nix flake update'
./build.sh
```

## SSH-Key & ISO-Signatur

- **Autorisierter Installer-SSH-Key (#30):** in `iso-authorized-keys` (eine Zeile
  je Key). Rotation = Datei bearbeiten + neu bauen. Es ist ein öffentlicher Key
  (kein Secret); wer ihn privat halten will, gitignored die Datei und befüllt sie
  pro Build (die Flake sieht dann nur getrackte Dateien — Datei tracken oder mit
  `--impure` bauen).
- **ISO-Signatur (#32):** optional mit minisign. Der Secret-Key liegt NICHT im
  Repo; beim Build übergeben:

  ```bash
  MINISIGN_SECRET_KEY_FILE=~/.minisign/iso.key ./build.sh   # erzeugt <iso>.minisig
  # Verifizieren: minisign -Vm <iso> -P <public-key>
  ```

  Ohne Key wird nur die SHA256-Prüfsumme erzeugt (mit Hinweis).
- **Nix-Sandbox (#31):** im rootless-Podman-Container deaktiviert (kein
  privilegierter mount/user-namespace); Begründung im `Containerfile`.

Do not commit ISOs, disk images, checksums generated for them, build metadata,
or local credentials.
