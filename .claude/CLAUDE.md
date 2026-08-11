# Repository-Regeln

Dieses Repo baut nur das NixOS-Installer-ISO für die Bare-Metal-Hosts des
lokalen Clusters. Der öffentliche Cluster läuft auf Hetzner-vServern und wird
anders installiert (siehe `public-cluster-nix/docs/operations.md`).

- Bauen nur über `./build.sh` im Podman-Container; die Workstation hat keine
  Nix-Toolchain.
- `artifacts/` nie committen (gitignored, enthält eine 1,5-GB-ISO).
- SSH-Key-Rotation = `iso-authorized-keys` editieren + neu bauen.
- Prüfungen über `./build.sh --check` (Flake-Evaluierung + `nix flake check`
  im Container, ohne ISO zu bauen).
