# Repo-Struktur

Baut NixOS-Installer-ISOs für den Cluster in einem Podman-Container.

## Einordnung

Dieses Repo steht *vor* allen anderen Repos des Monorepos: es erzeugt nur das
Installer-ISO, mit dem Bare-Metal-Hosts (lokaler und öffentlicher Cluster)
provisioniert werden. Die Einordnung im Monorepo, den Downstream-Ablauf und die
eingebackenen Werkzeuge beschreibt README.md; diese Datei dokumentiert den
Dateibaum.

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

Bauen, Prüfen (`--check`) und Image-Neubau (`--rebuild`) laufen über `./build.sh`;
Details siehe README.md (Abschnitt „Build").
