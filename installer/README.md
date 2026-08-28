# Installer-Skripte

Python-Skripte, die **auf dem gebooteten Installer-ISO** laufen (nicht auf dem
Operator-Rechner) und einen Bare-Metal-Host des lokalen Clusters installieren:

- `install_host.py` — partitioniert, formatiert, richtet Subvolumes/ZFS-Pool
  ein und ruft `nixos-install` auf.
- `install_disk_guard.py` — fail-closed-Prüfung, dass die Zielmaschine wirklich
  der erwartete Host ist, bevor irgendetwas geschrieben wird.
- `log.py` — farbiges Logging, von beidem benutzt.

Sie werden von der Ziel-Hardware aus per SSH bedient, nicht vom Build-Container
dieses Repos — Details zum ISO-Build stehen in der `README.md` eine Ebene
darüber.

## Voraussetzungen auf dem Installer

Der gebootete Installer trägt zwei Bäume nebeneinander unter `/root`:

```
/root/local-cluster-nix/            # Host-Flake, MIT .git (siehe unten)
/root/cluster-iso-builder/          # dieses Repo, für installer/
/root/age-key.txt                   # Age-Key des Zielhosts
```

`install_host.py` leitet den Pfad zu `local-cluster-nix` selbst her
(`nix_repo_root()`): zwei Verzeichnisebenen über sich selbst, also
`/root` bei diesem Layout — überschreibbar mit `$LOCAL_CLUSTER_NIX_ROOT`, falls
ein Baum woanders liegt. Getrennt davon steuert `--repo-root`/`$REPO_ROOT`, wo
`nixos-install --flake` das Systemflake findet; beide Wege zeigen im
Normalfall auf denselben Pfad, sind aber zwei unabhängige Stellschrauben.

Kopieren, je Installer-IP:

```bash
rsync -a --timeout=120 --exclude local-secrets \
  local-cluster-nix/ root@<installer-ip>:/root/local-cluster-nix/
rsync -a --timeout=120 --exclude artifacts --exclude __pycache__ \
  cluster-iso-builder/ root@<installer-ip>:/root/cluster-iso-builder/
scp local-cluster-nix/local-secrets/age/<host>.txt root@<installer-ip>:/root/age-key.txt
```

`local-cluster-nix` geht **mit** `.git`: nicht weil die Flake-Evaluierung ein
Git-Verzeichnis bräuchte (ein Pfad ohne `.git` ist ein gültiges Path-Flake, und
`install_host.py` legt bei fehlendem `.git` selbst einen Wegwerf-Commit an),
sondern damit der installierte Stand nachvollziehbar bleibt. Der Preis: mit
vorhandenem `.git` behandelt Nix den Pfad als Git-Flake und sieht
**unversionierte neue Dateien nicht** — vor dem rsync entweder alles committen
oder mit `git status --porcelain` sicherstellen, dass keine `??`-Zeile übrig
ist.

## Ablauf

Erst schreibfrei nachweisen, dass der Guard die richtige Maschine sieht —
prüft MAC, Disk-Anzahl, exakte Disk-Größen, Block-Device-Typ sowie
Mount-/Read-only-/Holder-Zustand, schreibt aber nichts:

```bash
python /root/cluster-iso-builder/installer/install_host.py \
  <host> --preflight-only --confirm-wipe <host>
```

Erst danach der echte, destruktive Lauf (formatiert alle Disks aus
`HOST_CONFIGS[<host>]`, mountet das Layout, `nixos-install --flake
local-cluster-nix#<host>`):

```bash
python /root/cluster-iso-builder/installer/install_host.py \
  <host> --confirm-wipe <host>
```

`<host>` ist einer von `beelink-server` (Manager) oder `fujitsu-server`
(Worker); `--confirm-wipe` muss exakt denselben Namen tragen — eine reine
Tippfehlersperre, kein zweiter Identitätsnachweis.

## Warnung: der Guard prüft Identität, nicht Inhalt

`install_disk_guard.py` stellt sicher, dass die richtige **Maschine** vor
einem steht — nicht, dass ihre Platten entbehrlich sind. `install_host.py`
löscht **jede** Disk aus `HOST_CONFIGS[<host>].disks`, auch eine, die nur als
Datengrab angehängt war. Vor dem echten Lauf selbst nachsehen, was auf den
Zielplatten liegt (`mount -o ro /dev/sdX /mnt/inspect && du -sh
/mnt/inspect/*`) — der Guard hätte keinen Einwand, wenn dort etwas
Wertvolles läge, solange MAC und Disk-Topologie zum konfigurierten Host passen.

## Vor dem ersten echten Lauf eines neuen Hosts

Die Hardware-Identität in `HOST_CONFIGS` (`install_host.py`) — NIC-MAC,
Disk-Pfade und exakte Disk-Größen in Byte — muss an der realen Maschine erhoben
sein:

```bash
ip -o link show                        # MAC der LAN-NIC
lsblk -dn -b -o PATH,TYPE,SIZE         # Disk-Pfade und Größen in Bytes
```

Die Disk-UUIDs werden nicht hier gepflegt, sondern von `install_host.py`
direkt aus `hosts/<host>/storage-map.nix` in `local-cluster-nix` gelesen —
eine einzige Quelle der Wahrheit für Installer und NixOS-Konfiguration.
