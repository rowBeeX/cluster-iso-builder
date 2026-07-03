# Cluster NixOS ISO Builder

Builds the x86_64 NixOS 26.05 installer used to provision the local and public
development clusters. The build is isolated in a digest-pinned Podman image;
the exact nixpkgs revision is pinned by `flake.lock`.

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
SOPS/age, disko, ZFS, Btrfs, LVM, mdraid, NFS and common diagnostics.

## Updating inputs

Update deliberately inside the build container, review the lock-file diff,
then run a complete build:

```bash
podman run --rm -v "$PWD:/workspace:Z" -w /workspace \
  --entrypoint bash \
  local/cluster-iso-builder:26.05 \
  -lc 'nix flake update'
./build.sh
```

Do not commit ISOs, disk images, checksums generated for them, build metadata,
or local credentials.
