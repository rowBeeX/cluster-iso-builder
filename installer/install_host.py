#!/usr/bin/env python3
"""NixOS-Host des lokalen Clusters vom Installer-ISO aus installieren.

Dieses Skript läuft auf dem Installer (NixOS-ISO), nicht auf dem Operator-Rechner.
Partitioniert, formatiert, richtet Subvolumes/Pools ein und führt nixos-install aus.

Voraussetzungen:
  - Repo (mit .git) liegt unter /root/local-cluster-nix oder $REPO_ROOT
  - Age-Key liegt unter /root/age-key.txt oder $AGE_KEY
  - Optional: PREBUILT_SYSTEM zeigt auf eine vorab gebaute NixOS-Closure

Verwendung (vom /root des gebooteten Installers aus, siehe installer/README.md):
    python cluster-iso-builder/installer/install_host.py \
        <host> --preflight-only --confirm-wipe <host>
    python cluster-iso-builder/installer/install_host.py \
        <host> --confirm-wipe <host>

Unterstützte Hosts: beelink-server (Manager), fujitsu-server (Worker)

WICHTIG — vor dem ersten echten Lauf eines Hosts auszufüllen:
Die Hardware-Identität (NIC-MAC, Disk-Pfade und exakte Disk-Größen) steht unten
in HOST_CONFIGS; für beide Hosts sind die Werte an der realen Maschine erhoben.
Der Guard (install_disk_guard.py) ist fail-closed: solange die Werte nicht
der realen Maschine entsprechen, bricht das Skript ab, bevor irgendetwas
geschrieben wird. Werte auf der Zielmaschine ermitteln:

    ip -o link show                       # MAC der LAN-NIC
    lsblk -dn -b -o PATH,TYPE,SIZE        # Disk-Pfade und Größen in Bytes

Die Disk-UUIDs werden NICHT hier gepflegt, sondern direkt aus
``hosts/<host>/storage-map.nix`` gelesen — eine einzige Quelle der Wahrheit.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from install_disk_guard import verify_install_target
from log import Logger


def nix_repo_root() -> Path:
    """Wo `local-cluster-nix` auf dem Installer liegt.

    Der Installer trägt beide Bäume nebeneinander unter /root. Die Umgebungs-
    variable erlaubt eine abweichende Ablage, ohne das Skript anzufassen.
    """
    env = os.environ.get("LOCAL_CLUSTER_NIX_ROOT")
    return Path(env) if env else Path(__file__).resolve().parents[2] / "local-cluster-nix"

# Platzhalter, die der Guard garantiert ablehnt. Beim Provisionieren durch die
# realen Werte der Maschine ersetzen (siehe Modul-Docstring).
_PLACEHOLDER_MAC = "00:00:00:00:00:00"


@dataclass(frozen=True)
class HostConfig:
    name: str
    role: str  # "manager" | "worker"
    root_disk: str
    swap_size: str
    mac: str
    disks: dict[str, int]
    # Manager: SSD mit ZFS-SLOG/L2ARC + Btrfs-Pool. Worker: Btrfs-Bulk-Disk.
    pool_disk: str = ""
    # Nur Manager: RAIDZ1-Mitglieder des ZFS-Datapools.
    raidz_disks: tuple[str, ...] = field(default_factory=tuple)


HOST_CONFIGS: dict[str, HostConfig] = {
    "beelink-server": HostConfig(
        name="beelink-server",
        role="manager",
        # Am laufenden Installer erhoben (lsblk -b -d, ip link, lsblk -o TRAN).
        root_disk="/dev/nvme0n1",  # 512 GB NVMe
        pool_disk="/dev/sda",  # 512 GB SATA-SSD (INTENSO), btrfs-Pool + SLOG/L2ARC
        # Die vier ZFS-Platten hängen an einem USB-DAS (TerraMas TDAS). USB-
        # Enumeration ist nicht stabil: sdb..sde können nach einem Reboot die
        # Buchstaben tauschen, und alle vier sind exakt gleich groß, sodass ein
        # Tausch am Größenvergleich nicht auffiele. Deshalb by-id statt /dev/sdX
        # — die Seriennummer im Pfad bindet jedes vdev an genau eine Platte.
        raidz_disks=(
            "/dev/disk/by-id/ata-WDC_WD40EZRZ-22GXCB0_WD-WCC7K2FUKKZK",
            "/dev/disk/by-id/ata-WDC_WD40EZRZ-22GXCB0_WD-WCC7K4JFNND7",
            "/dev/disk/by-id/ata-ST4000VX016-3CV104_WW66JJX9",
            "/dev/disk/by-id/ata-WDC_WD40EZRZ-00GXCB0_WD-WCC7K5DZULUY",
        ),
        swap_size="+8G",
        mac="b0:41:6f:17:5d:20",  # enp1s0
        disks={
            "/dev/nvme0n1": 512110190592,
            "/dev/sda": 512110190592,
            "/dev/sdb": 4000787030016,
            "/dev/sdc": 4000787030016,
            "/dev/sdd": 4000787030016,
            "/dev/sde": 4000787030016,
        },
    ),
    "fujitsu-server": HostConfig(
        name="fujitsu-server",
        role="worker",
        # by-id statt /dev/sdX: die Buchstaben haben zwischen zwei Bootvorgängen
        # getauscht (erst SATA=sda/USB=sdb, dann USB=sda/SATA=sdb). Mit festen
        # Buchstaben hätte der zweite Lauf das System auf die 16-TB-USB-Platte
        # installiert und die SSD zum Bulk-Pool gemacht — genau verkehrt. Die
        # Seriennummer im Pfad bindet jedes Ziel an genau ein Gerät; dieselbe
        # Begründung gilt für die ZFS-Platten des Managers.
        root_disk="/dev/disk/by-id/ata-ORICO-ZH10_2407VE1R910C0039",  # 128 GB SATA-SSD
        pool_disk="/dev/disk/by-id/usb-Seagate_Expansion_HDD_00000000NT17XGTC-0:0",  # 16 TB
        swap_size="+8G",
        mac="90:1b:0e:89:2e:5b",  # enp1s0 (r8169)
        disks={
            "/dev/disk/by-id/ata-ORICO-ZH10_2407VE1R910C0039": 128035676160,
            "/dev/disk/by-id/usb-Seagate_Expansion_HDD_00000000NT17XGTC-0:0": 16000900660736,
        },
    ),
}

_PERSIST_DIRS = (
    "etc/k3s",
    "etc/rancher/k3s",
    "etc/rancher/node",
    "etc/ssh",
    "var/lib/crowdsec",
    "var/lib/kubelet",
    "var/lib/netbird-wt0",
    "var/lib/nixos",
    "var/lib/systemd/timers",
    "var/log",
)

_UUID_KEYS = ("bootUuid", "swapUuid", "rootUuid", "btrfsPoolUuid")


def storage_map(host: str) -> dict[str, str]:
    """Liest die Disk-UUIDs aus hosts/<host>/storage-map.nix.

    Einzige Quelle der Wahrheit: dieselbe Datei, aus der die NixOS-Konfiguration
    ihre fileSystems-Einträge ableitet. Damit kann Installer und Konfiguration
    nicht auseinanderlaufen.
    """
    path = nix_repo_root() / "hosts" / host / "storage-map.nix"
    text = path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for key in _UUID_KEYS:
        match = re.search(rf'^\s*{key}\s*=\s*"([^"]+)";', text, re.MULTILINE)
        if match:
            values[key] = match.group(1)
    missing = [key for key in ("bootUuid", "swapUuid", "rootUuid") if key not in values]
    if missing:
        raise SystemExit(f"{path}: fehlende UUIDs {missing}")
    return values


def require_real_hardware(cfg: HostConfig) -> None:
    """Bricht ab, solange die Hardware-Identität Platzhalter enthält."""
    problems = []
    if cfg.mac == _PLACEHOLDER_MAC:
        problems.append("mac ist noch der Platzhalter")
    if not cfg.disks:
        problems.append("disks ist leer")
    if problems:
        raise SystemExit(
            f"HOST_CONFIGS[{cfg.name!r}] ist noch nicht provisioniert: "
            + ", ".join(problems)
            + ". Werte mit `ip -o link show` und `lsblk -dn -b -o PATH,TYPE,SIZE` "
            "auf der Zielmaschine ermitteln und hier eintragen."
        )


def run(cmd: list[str], *, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, **kwargs)


def run_quietly(cmd: list[str]) -> None:
    run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def part(disk: str, index: int) -> str:
    """Partitionspfad.

    Drei Schreibweisen: udev haengt an by-id/by-path `-partN` an, NVMe und mmc
    brauchen ein `p` vor der Nummer, alles andere haengt die Nummer direkt an.
    Die by-id-Form fiel bisher nicht auf, weil nur die ZFS-Platten des Managers
    by-id adressiert werden und `make_zfs_pool` sie ungeteilt an `zpool` gibt.
    """
    if disk.startswith("/dev/disk/by-"):
        return f"{disk}-part{index}"
    return f"{disk}p{index}" if re.search(r"\d$", disk) else f"{disk}{index}"


def wipe_disk(dev: str) -> None:
    # TRIM zuerst. Die SSD in fujitsu-server liefert `Medium Error` fuer jede
    # Flash-Seite ohne gueltig geschriebenen Inhalt — nach einer abgebrochenen
    # Installation blieb das Mapping inkonsistent, und ausgerechnet die letzten
    # Sektoren waren betroffen. Dort liegt die GPT-Sicherungstabelle: sgdisk
    # scheiterte an ihr und verwarf daraufhin auch die primaere Tabelle, sodass
    # gar keine Partitionen entstanden. Ein blkdiscard raeumt das in Sekunden
    # ab (gemessen: 2,3 s fuer 128 GB, danach 0 Fehler im Vollesen).
    # check=False, weil rotierende Platten kein TRIM koennen — dort ist der
    # Aufruf folgenlos.
    run(["blkdiscard", dev], check=False)
    run(["wipefs", "-a", dev], check=False)
    run(["sgdisk", "--zap-all", dev], check=False)
    run(["partprobe", dev], check=False)
    run(["udevadm", "settle"])


def forget_btrfs(dev: str) -> None:
    run_quietly(["btrfs", "device", "scan", "--forget", dev])


def cleanup_mounts() -> None:
    run_quietly(["swapoff", "-a"])
    run_quietly(["umount", "-R", "/mnt"])
    run_quietly(["zpool", "export", "datapool"])


def make_root_disk(cfg: HostConfig, uuids: dict[str, str]) -> None:
    cleanup_mounts()
    disk = cfg.root_disk
    wipe_disk(disk)

    run(["sgdisk", "-n1:0:+512M", "-t1:ef00", "-c1:ESP", disk])
    run(["sgdisk", f"-n2:0:{cfg.swap_size}", "-t2:8200", "-c2:swap", disk])
    run(["sgdisk", "-n3:0:0", "-t3:8300", "-c3:root", disk])
    run(["partprobe", disk])
    run(["udevadm", "settle"])

    for index in (1, 2, 3):
        run(["wipefs", "-a", part(disk, index)], check=False)
    forget_btrfs(part(disk, 3))
    run(["udevadm", "settle"])

    boot_uuid_raw = uuids["bootUuid"].replace("-", "")
    run(["mkfs.fat", "-F32", "-n", "ESP", "-i", boot_uuid_raw, part(disk, 1)])
    run(["mkswap", "-U", uuids["swapUuid"], "-L", "swap", part(disk, 2)])
    run(["mkfs.btrfs", "-f", "-K", "-U", uuids["rootUuid"], "-L", "root", part(disk, 3)])

    run(["mount", part(disk, 3), "/mnt"])
    # K3s-Datastore und Runtime liegen auf der Root-Disk im @kubernetes-Subvolume,
    # nicht auf den separaten Btrfs-/ZFS-Pools.
    for sv in ("@nixos", "@persist", "@home", "@snapshots", "@kubernetes"):
        run(["btrfs", "subvolume", "create", f"/mnt/{sv}"])
    run(["umount", "/mnt"])


def make_btrfs_pool(
    dev: str, uuid: str, *, data_subvolume: str = "kubernetes", label: str = "datapool"
) -> None:
    if not uuid:
        return
    wipe_disk(dev)
    run(["sgdisk", "-n1:0:0", "-t1:8300", "-c1:btrfs-pool", dev])
    run(["partprobe", dev])
    run(["udevadm", "settle"])

    run(["wipefs", "-a", part(dev, 1)], check=False)
    forget_btrfs(part(dev, 1))
    run(["udevadm", "settle"])

    run(["mkfs.btrfs", "-f", "-K", "-U", uuid, "-L", label, part(dev, 1)])
    run(["mount", part(dev, 1), "/mnt"])
    run(["btrfs", "subvolume", "create", f"/mnt/@{data_subvolume}"])
    run(["btrfs", "subvolume", "create", "/mnt/@snapshots"])
    run(["umount", "/mnt"])


def make_manager_ssd_disk(dev: str, pool_uuid: str) -> None:
    wipe_disk(dev)
    run(["sgdisk", "-n1:0:+16G", "-t1:BF01", "-c1:zfs-slog", dev])
    run(["sgdisk", "-n2:0:+64G", "-t2:BF01", "-c2:zfs-cache", dev])
    run(["sgdisk", "-n3:0:0", "-t3:8300", "-c3:btrfs-pool", dev])
    run(["partprobe", dev])
    run(["udevadm", "settle"])

    for index in (1, 2, 3):
        run(["wipefs", "-a", part(dev, index)], check=False)
        forget_btrfs(part(dev, index))
        run_quietly(["zpool", "labelclear", "-f", part(dev, index)])
    run(["udevadm", "settle"])

    run(["mkfs.btrfs", "-f", "-K", "-U", pool_uuid, "-L", "datapool", part(dev, 3)])
    run(["mount", part(dev, 3), "/mnt"])
    run(["btrfs", "subvolume", "create", "/mnt/@kubernetes"])
    run(["btrfs", "subvolume", "create", "/mnt/@snapshots"])
    run(["umount", "/mnt"])


def make_zfs_pool(cfg: HostConfig) -> None:
    key_path = Path("/tmp/datapool.key")
    key_path.write_bytes(os.urandom(32))
    key_path.chmod(0o400)

    run_quietly(["zpool", "destroy", "-f", "datapool"])
    for dev in cfg.raidz_disks:
        run_quietly(["zpool", "labelclear", "-f", dev])
        wipe_disk(dev)
    slog = part(cfg.pool_disk, 1)
    cache = part(cfg.pool_disk, 2)
    run_quietly(["zpool", "labelclear", "-f", slog])
    run_quietly(["zpool", "labelclear", "-f", cache])

    run(
        [
            "zpool",
            "create",
            "-f",
            "-o",
            "ashift=12",
            "-O",
            "compression=lz4",
            "-O",
            "atime=off",
            "-O",
            "xattr=sa",
            "-O",
            "dedup=off",
            "-O",
            "mountpoint=none",
            "-O",
            "encryption=aes-256-gcm",
            "-O",
            "keyformat=raw",
            "-O",
            "keylocation=file:///tmp/datapool.key",
            "datapool",
            "raidz1",
            *cfg.raidz_disks,
            "cache",
            cache,
            "log",
            slog,
        ]
    )
    run(["zfs", "create", "datapool/kubernetes"])
    run(["zpool", "export", "datapool"])


def mount_install_layout(cfg: HostConfig) -> None:
    disk = cfg.root_disk
    root_part = part(disk, 3)
    run(["mount", "-t", "tmpfs", "-o", "size=4G,mode=755", "none", "/mnt"])
    for d in ("/mnt/nix", "/mnt/persist", "/mnt/home", "/mnt/.snapshots", "/mnt/boot"):
        Path(d).mkdir(parents=True, exist_ok=True)
    for subvol, target in (
        ("@nixos", "/mnt/nix"),
        ("@persist", "/mnt/persist"),
        ("@home", "/mnt/home"),
        ("@snapshots", "/mnt/.snapshots"),
    ):
        run(["mount", "-o", f"subvol={subvol},noatime,discard=async", root_part, target])
    run(["mount", "-o", "fmask=0077,dmask=0077", part(disk, 1), "/mnt/boot"])
    run(["swapon", part(disk, 2)])

    for directory in _PERSIST_DIRS:
        Path("/mnt/persist", directory).mkdir(parents=True, exist_ok=True)


def _meminfo_kib(key: str) -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(f"{key}:"):
            return int(line.split()[1])
    return 0


def grow_installer_store() -> None:
    """Den beschreibbaren Store des Installers vergrößern, sobald Swap läuft.

    Das Live-ISO legt /nix/.rw-store als tmpfs mit dem Default von 50 % des RAM
    an. Auf fujitsu-server (7,4 GiB) sind das 3,8 GB — gegen eine System-Closure
    von 2,9 GiB. Das reicht rechnerisch, aber ohne nennenswerte Reserve, und ein
    ENOSPC schlägt erst mitten in `nixos-install` zu: die Disks sind dann bereits
    formatiert und der Host bleibt unbootbar zurück.

    Die Obergrenze eines tmpfs ist nur eine Grenze, keine Belegung. Nach
    `swapon` (mount_install_layout) stehen RAM + Swap zur Verfügung, Seiten
    dürfen also auslagern. Deshalb hier auf RAM + Swap abzüglich 2 GiB Reserve
    anheben — auf einer großen Maschine schrumpft das nichts, weil nur
    vergrößert wird.
    """
    store = Path("/nix/.rw-store")
    if not store.is_mount():
        return
    budget_kib = _meminfo_kib("MemTotal") + _meminfo_kib("SwapTotal") - 2 * 1024 * 1024
    if budget_kib <= 0:
        return
    current_kib = os.statvfs(store).f_blocks * os.statvfs(store).f_frsize // 1024
    if budget_kib <= current_kib:
        return
    run(
        ["mount", "-o", f"remount,size={budget_kib}k", str(store)],
        check=False,
    )


_BOOT_ENTRY_LABEL = "Linux Boot Manager"


def prefer_installed_boot_entry() -> None:
    """Den frisch angelegten EFI-Eintrag an den Anfang der BootOrder stellen.

    Ohne das bootet die Maschine am neuen System vorbei. Auf fujitsu-server stand
    nach der ersten Installation `BootOrder: 000A,000B,000C,0008,0000,0009,0001`
    — der USB-Installerstick zuerst, "Linux Boot Manager" (0001) zuletzt, und
    dazwischen ein BBS-Legacy-Eintrag auf dieselbe SSD, die nach dem
    GPT-Neuaufbau keinen MBR-Bootcode mehr hat. Der Host war danach auf keiner
    Adresse mehr erreichbar; ein Thin Client hat weder IPMI noch serielle
    Konsole, also half nur ein Gang zum Geraet.

    Fehler sind hier nicht fatal: das System ist installiert, es bootet nur
    womoeglich nicht von selbst. Deshalb warnen statt abbrechen.
    """
    try:
        listing = subprocess.run(
            ["efibootmgr"], check=True, text=True, capture_output=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"WARNUNG: efibootmgr nicht auswertbar ({exc}); BootOrder unveraendert")
        return

    # efibootmgr trennt Label und Geraetepfad mit einem Tabulator — ohne den
    # optionalen Rest im Muster trifft die Zeile nie.
    entries = re.findall(
        rf"^Boot([0-9A-Fa-f]{{4}})\*?\s+{re.escape(_BOOT_ENTRY_LABEL)}(?:\t(.*))?$",
        listing,
        re.MULTILINE,
    )
    order_match = re.search(r"^BootOrder:\s*(\S+)", listing, re.MULTILINE)
    if not entries or not order_match:
        print(f"WARNUNG: kein Eintrag {_BOOT_ENTRY_LABEL!r} oder keine BootOrder gefunden; "
              "nach dem Reboot im Bootmenue haendisch waehlen")
        return

    # Eine Neuinstallation laesst den Eintrag der vorherigen stehen: er zeigt
    # dann auf eine ESP-Partitions-GUID, die es nicht mehr gibt, und erscheint
    # als `VenHw(...)` ohne Geraetepfad. Der brauchbare Eintrag traegt `HD(`.
    # Ohne diese Unterscheidung waehlt man die Leiche und bootet wieder nirgends.
    usable = [num for num, tail in entries if "HD(" in (tail or "")]
    if not usable:
        print(f"WARNUNG: nur Eintraege ohne Geraetepfad gefunden "
              f"({', '.join(n for n, _ in entries)}); BootOrder unveraendert")
        return
    target = usable[-1]
    rest = [e for e in order_match.group(1).split(",") if e.upper() != target.upper()]
    new_order = ",".join([target, *rest])
    result = subprocess.run(
        ["efibootmgr", "-o", new_order], check=False, text=True, capture_output=True
    )
    if result.returncode != 0:
        print(f"WARNUNG: BootOrder konnte nicht gesetzt werden: {result.stderr.strip()}")
        return
    print(f"BootOrder gesetzt: {new_order} ({_BOOT_ENTRY_LABEL} zuerst)")


def install_system(host: str, repo_root: Path, age_key: Path) -> None:
    secrets_dir = Path("/mnt/persist/secrets/sops")
    secrets_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    subprocess.run(
        ["install", "-m", "0600", str(age_key), str(secrets_dir / "age-key.txt")],
        check=True,
    )

    # Korrektes Eigentum sicherstellen
    subprocess.run(["chown", "-R", "root:root", str(repo_root)], check=True)

    # Minimales .git anlegen, falls es fehlt (Installer-tmpfs zu klein für .git)
    if not (repo_root / ".git").exists():
        for cmd in [
            ["git", "-C", str(repo_root), "init", "-q"],
            ["git", "-C", str(repo_root), "config", "user.email", "install@local"],
            ["git", "-C", str(repo_root), "config", "user.name", "Installer"],
            ["git", "-C", str(repo_root), "add", "-A"],
            [
                "git",
                "-C",
                str(repo_root),
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "install",
            ],
        ]:
            subprocess.run(cmd, check=True)

    subprocess.run(
        ["git", "config", "--global", "--add", "safe.directory", str(repo_root)],
        check=True,
    )

    prebuilt = os.environ.get("PREBUILT_SYSTEM", "")
    if prebuilt:
        subprocess.run(
            [
                "nixos-install",
                "--root",
                "/mnt",
                "--system",
                prebuilt,
                "--no-root-passwd",
                "--no-channel-copy",
            ],
            check=True,
            env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        )
    else:
        subprocess.run(
            [
                "nixos-install",
                "--root",
                "/mnt",
                "--flake",
                f"{repo_root}#{host}",
                "--no-root-passwd",
                "--no-channel-copy",
                "--no-update-lock-file",
            ],
            check=True,
            env={**os.environ, "LANG": "C", "LC_ALL": "C"},
        )

    admin_home = Path("/mnt/home/administrator")
    admin_home.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "rsync",
            "-a",
            "--delete",
            "--exclude",
            "local-secrets",
            "--exclude",
            ".vectimus",
            f"{repo_root}/",
            str(admin_home / "local-cluster-nix") + "/",
        ],
        check=True,
    )
    subprocess.run(["chown", "-R", "1000:100", str(admin_home)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("host", choices=list(HOST_CONFIGS.keys()))
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(os.environ.get("REPO_ROOT", "/root/local-cluster-nix")),
    )
    parser.add_argument(
        "--age-key",
        type=Path,
        default=Path(os.environ.get("AGE_KEY", "/root/age-key.txt")),
    )
    parser.add_argument(
        "--confirm-wipe", required=True, help="Muss exakt dem Zielhost entsprechen"
    )
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    cfg = HOST_CONFIGS[args.host]
    uuids = storage_map(args.host)
    log = Logger()

    log.section(f"Installiere {args.host}")

    require_real_hardware(cfg)
    verify_install_target(
        host=args.host,
        confirmation=args.confirm_wipe,
        expected_mac=cfg.mac,
        expected_disks=cfg.disks,
    )
    if args.preflight_only:
        return
    cleanup_mounts()

    log.step("Root-Disk formatieren")
    make_root_disk(cfg, uuids)

    pool_uuid = uuids.get("btrfsPoolUuid", "")
    if cfg.role == "manager":
        log.step("Manager-SSD formatieren")
        make_manager_ssd_disk(cfg.pool_disk, pool_uuid)
        log.step("ZFS-Datapool anlegen")
        make_zfs_pool(cfg)
    else:
        log.step("Btrfs-Pool formatieren")
        make_btrfs_pool(cfg.pool_disk, pool_uuid)

    log.step("Install-Layout mounten")
    mount_install_layout(cfg)

    # Erst hier, nicht früher: die Vergrößerung lebt vom Swap, den
    # mount_install_layout gerade eingeschaltet hat.
    log.step("Installer-Store vergrößern")
    grow_installer_store()

    if cfg.role == "manager":
        log.step("ZFS-Verschlüsselungsschlüssel nach /persist verschieben")
        Path("/mnt/persist/secrets/zfs").mkdir(parents=True, mode=0o700, exist_ok=True)
        subprocess.run(
            [
                "install",
                "-m",
                "0400",
                "/tmp/datapool.key",
                "/mnt/persist/secrets/zfs/datapool.key",
            ],
            check=True,
        )
        subprocess.run(
            ["zpool", "import", "-d", "/dev/disk/by-id", "datapool"], check=True
        )
        subprocess.run(
            [
                "zfs",
                "set",
                "keylocation=file:///persist/secrets/zfs/datapool.key",
                "datapool",
            ],
            check=True,
        )
        subprocess.run(["zpool", "export", "datapool"], check=True)

    log.step("System installieren")
    install_system(args.host, args.repo_root, args.age_key)

    log.step("BootOrder auf das installierte System stellen")
    prefer_installed_boot_entry()

    log.step("Mounts bereinigen")
    cleanup_mounts()

    log.section(f"Installation von {args.host} abgeschlossen")


if __name__ == "__main__":
    main()
