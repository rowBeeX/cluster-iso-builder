# Repo-Struktur

Baut NixOS-Installer-ISOs für den Cluster in einem Podman-Container.

## Einordnung

Dieses Repo steht *vor* allen anderen Repos des Monorepos. Es definiert keine
Laufzeitdienste, kein Netzwerk, kein DNS und enthält keine Secrets; es erzeugt
nur das Installer-ISO, mit dem Bare-Metal-Hosts (lokaler und öffentlicher
Cluster) provisioniert werden, bevor auf ihnen NixOS-Konfiguration, k3s, Cilium,
Envoy Gateway oder ArgoCD existieren.

Ablauf downstream: Operator bootet das ISO auf der Zielhardware, meldet sich per
SSH als `root` an (ausschließlich mit dem einen eingebackenen Operator-
ed25519-Key; Passwort-Auth ist abgelehnt), partitioniert die Disks per
`install_dev_host.py` (gptfdisk/parted + mkfs) und schreibt die eigentliche
NixOS-Konfiguration mit `nixos-install` aus dem passenden `*-nix`-Repo. Die
eingebackenen Werkzeuge (gptfdisk/parted, sops/age, nixos-install-tools,
zfs/btrfs/lvm2/mdadm/nfs, python3, rsync) dienen genau diesem Bootstrap; das ISO
selbst trägt keine Secrets.

## Dateibaum

```
build.sh                        Einstiegspunkt: baut den Container und startet den Build (`--check` / `--rebuild`)
Containerfile                   Podman-Container-Definition mit Nix-Installation und Build-Umgebung
flake.nix                       Nix-Flake: definiert `installerIso` als Build-Ausgabe
flake.lock                      Eingaben-Lock (nicht manuell bearbeiten)
configuration.nix               NixOS-Konfiguration für das Installer-ISO (Benutzer, SSH, Pakete)
iso-authorized-keys             Autorisierte Installer-SSH-Keys (ein Key je Zeile)
cluster-iso-builder.code-workspace  VS-Code-Workspace-Konfiguration für dieses Repo
README.md                       Kurzübersicht: Zweck, Verwendung, Voraussetzungen

scripts/
  container-build.sh            Wird im Container ausgeführt: Flake-Check oder ISO-Build

artifacts/                      Build-Artefakte (gitignored)
  output/
    cluster-nixos-installer-*.iso      Fertige ISO-Datei
    cluster-nixos-installer-*.iso.sha256  SHA256-Prüfsumme der ISO
  meta/
    output-iso.json             JSON-Metadatei: Pfad, Größe, SHA256 und Nixpkgs-Revision

docs/
  structure.md                  Diese Datei

.gitignore                      Schließt das gesamte artifacts/-Verzeichnis, *.iso, *.iso.sha256 und Nix-Ergebnisse aus
```

## Verwendung

```bash
# ISO bauen
./build.sh

# Nur Syntax- und Flake-Prüfung ohne Build
./build.sh --check

# Container-Image neu erstellen (z.B. nach Containerfile-Änderungen)
./build.sh --rebuild
```
