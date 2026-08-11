# Repo-Struktur

Baut NixOS-Installer-ISOs für den Cluster in einem Podman-Container.

## Einordnung

Dieses Repo steht *vor* allen anderen Repos des Monorepos: es erzeugt nur das
Installer-ISO, mit dem die Bare-Metal-Hosts des lokalen Clusters provisioniert
werden. Der öffentliche Cluster läuft auf Hetzner-Cloud-vServern und wird
anders installiert, ohne Custom-ISO (siehe
`public-cluster-nix/docs/operations.md`). Die Einordnung im Monorepo, den
Downstream-Ablauf und die eingebackenen Werkzeuge beschreibt README.md; diese
Datei dokumentiert den Dateibaum.

## Dateibaum

```
build.sh                        Einstiegspunkt: baut den Container und startet den Build (`--check` / `--rebuild`)
Containerfile                   Podman-Container-Definition mit Nix-Installation und Build-Umgebung
flake.nix                       Nix-Flake-Einstiegspunkt: lädt flake-parts + import-tree über flake/
flake.lock                      Eingaben-Lock (nicht manuell bearbeiten)
configuration.nix               NixOS-Konfiguration für das Installer-ISO (Benutzer, SSH, Pakete)
iso-authorized-keys             Autorisierte Installer-SSH-Keys (ein Key je Zeile)
README.md                       Kurzübersicht: Zweck, Verwendung, Voraussetzungen

flake/
  systems.nix                   Zielsysteme für perSystem (x86_64-linux)
  formatting.nix                `formatter`-Ausgabe (nixfmt-tree)
  checks.nix                    Flake-Checks: nixfmt/deadnix/statix über den Source-Baum
  iso.nix                       Baut `installerIso` aus configuration.nix als Flake-Paket

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
