# Repo-Struktur

Baut NixOS-Installer-ISOs für den Cluster in einem Podman-Container.

## Ordner

| Pfad | Inhalt |
|------|--------|
| `artifacts/` | Build-Artefakte: ISO-Datei und Metadaten (gitignored) |
| `artifacts/output/` | Fertige ISO-Datei und SHA256-Prüfsumme |
| `artifacts/meta/` | JSON-Metadatei mit Pfad, Größe, SHA256 und Nixpkgs-Revision |
| `scripts/` | Container-interne Build-Skripte |
| `docs/` | Dokumentation zur Repo-Struktur |
| `.github/` | GitHub-Webhook-Konfiguration |

## Wichtige Dateien

| Datei | Inhalt |
|-------|--------|
| `build.sh` | Einstiegspunkt: baut den Container und startet den Build (`--check` / `--rebuild`) |
| `Containerfile` | Podman-Container-Definition mit Nix-Installation |
| `flake.nix` | Nix-Flake: definiert `installerIso` als Build-Ausgabe |
| `configuration.nix` | NixOS-Konfiguration für das Installer-ISO |
| `scripts/container-build.sh` | Wird im Container ausgeführt: Flake-Check oder ISO-Build |

## Verwendung

```bash
# ISO bauen
./build.sh

# Nur Syntax- und Flake-Prüfung ohne Build
./build.sh --check

# Container-Image neu erstellen (z.B. nach Containerfile-Änderungen)
./build.sh --rebuild
```
