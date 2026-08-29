"""Fail-Closed-Prüfung von Host-Identität und Disk-Topologie für destruktive Installer."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _output(*args: str) -> str:
    return subprocess.run(
        args, check=True, text=True, capture_output=True
    ).stdout.strip()


def _live_medium_disks() -> set[str]:
    """Disks, von denen der Installer selbst läuft.

    Der Boot-Stick gehört nicht zur Disk-Topologie des Hosts: er wechselt, und
    ein anderer Stick hätte eine andere Größe. Deshalb wird er hier ermittelt
    und aus dem Vergleich genommen — die Zielplatten bleiben lückenlos geprüft.
    """
    disks: set[str] = set()
    for mountpoint in ("/iso", "/nix/.ro-store"):
        try:
            source = _output("findmnt", "-no", "SOURCE", mountpoint)
        except subprocess.CalledProcessError:
            continue
        if not source.startswith("/dev/"):
            continue
        try:
            # PKNAME ist bei einer Partition die Elternplatte und bei einer
            # ganzen Platte leer; dann zählt der Pfad selbst.
            parent = _output("lsblk", "-ndo", "PKNAME", source)
        except subprocess.CalledProcessError:
            continue
        disks.add(f"/dev/{parent}" if parent else source)
    return disks


def verify_install_target(
    *,
    host: str,
    confirmation: str,
    expected_mac: str,
    expected_disks: dict[str, int],
) -> None:
    """Lehnt ein Installationsziel ab, außer Host-Identität und jede Disk passen exakt."""
    if confirmation != host:
        raise SystemExit(f"Wipe-Bestätigung stimmt nicht überein: erwartet {host!r}")

    actual_macs = {
        address.read_text().strip().lower()
        for address in Path("/sys/class/net").glob("*/address")
    }
    if expected_mac.lower() not in actual_macs:
        raise SystemExit(f"Host-Identität stimmt nicht überein: erwartete NIC {expected_mac}")

    live_disks = _live_medium_disks()
    disk_rows = _output("lsblk", "-dn", "-b", "-o", "PATH,TYPE,SIZE").splitlines()
    actual_disks = {
        fields[0]: int(fields[2])
        for row in disk_rows
        if len(fields := row.split()) == 3
        and fields[1] == "disk"
        and fields[0] not in live_disks
    }
    # `lsblk` liefert immer /dev/sdX, die erwartete Topologie darf dagegen
    # by-id-Pfade führen. Verglichen wird über den aufgelösten Gerätepfad,
    # gemeldet aber die ursprüngliche Schreibweise aus der Konfiguration.
    resolved_expected = {
        os.path.realpath(device): size for device, size in expected_disks.items()
    }
    if actual_disks != resolved_expected:
        raise SystemExit(
            f"Disk-Topologie stimmt nicht überein: erwartet {expected_disks} "
            f"(aufgelöst {resolved_expected}), erhalten {actual_disks} "
            f"(Installer-Medium ausgenommen: {sorted(live_disks) or 'keins erkannt'})"
        )

    for device, expected_size in expected_disks.items():
        # Über den aufgelösten Pfad prüfen: bei einem by-id-Symlink hiesse der
        # Knoten sonst `ata-ORICO-...`, und die Holder-Pruefung unten faende
        # /sys/class/block/<name> nicht — sie würde kommentarlos durchwinken.
        path = Path(os.path.realpath(device))
        if not path.is_block_device():
            raise SystemExit(f"Ziel ist kein Block-Device: {device}")

        size = int(_output("blockdev", "--getsize64", device))
        if size != expected_size:
            raise SystemExit(
                f"Disk-Größe für {device} stimmt nicht überein: erwartet {expected_size}, erhalten {size}"
            )
        if _output("blockdev", "--getro", device) != "0":
            raise SystemExit(f"Ziel-Disk ist schreibgeschützt: {device}")

        mounted = [
            mountpoint
            for mountpoint in _output(
                "lsblk", "-nr", "-o", "MOUNTPOINT", device
            ).splitlines()
            if mountpoint
        ]
        if mounted:
            raise SystemExit(f"Ziel-Disk hat gemountete Dateisysteme: {device}")

        holders = Path(f"/sys/class/block/{path.name}/holders")
        if holders.is_dir() and any(holders.iterdir()):
            raise SystemExit(f"Ziel-Disk hat aktive Holder: {device}")

    summary = ", ".join(f"{device}={size}" for device, size in expected_disks.items())
    print(f"INSTALLATIONSZIEL BESTAETIGT host={host} mac={expected_mac} disks={summary}")
