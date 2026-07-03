# Repo-Struktur

Baut NixOS-Installer-ISOs für den Cluster in einem Podman-Container.

## Dateibaum

```
build.sh                        Einstiegspunkt: baut den Container und startet den Build (`--check` / `--rebuild`)
Containerfile                   Podman-Container-Definition mit Nix-Installation und Build-Umgebung
flake.nix                       Nix-Flake: definiert `installerIso` als Build-Ausgabe
flake.lock                      Eingaben-Lock (nicht manuell bearbeiten)
configuration.nix               NixOS-Konfiguration für das Installer-ISO (Benutzer, SSH, Pakete)
iso-build.code-workspace        VS-Code-Workspace-Konfiguration für dieses Repo
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
