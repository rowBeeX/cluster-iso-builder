# Repository-Regeln

Dieses Repo baut nur das NixOS-Installer-ISO für die Bare-Metal-Hosts des
lokalen Clusters. Der öffentliche Cluster läuft auf Hetzner-vServern und wird
anders installiert (siehe `<Monorepo>/cluster-docs/betrieb/installation-public.md`).

- Bauen nur über `./build.sh` im Podman-Container; die Workstation hat keine
  Nix-Toolchain.
- `artifacts/` nie committen (gitignored, enthält eine 1,5-GB-ISO).
- SSH-Key-Rotation = `iso-authorized-keys` editieren + neu bauen.
- Prüfungen über `./build.sh --check` (Flake-Evaluierung + `nix flake check`
  im Container, ohne ISO zu bauen).

Dieses Repo hat **keine** Skills, und das bleibt so: seine gesamte Bedienung
sind die vier Zeilen oben. Ein Skill hätte nichts hinzuzufügen, was hier nicht
schon steht.

Wozu das ISO gehört, steht in `../../cluster-docs/08-notfall.md`: es ist der erste
Schritt beim Wiederaufbau eines lokalen Hosts (ISO → `install_host.py` →
SOPS-Age-Identität → `nixos-rebuild`). `../../cluster-docs/10-repo-wegweiser.md` sagt, was
statt dessen woanders liegt.
