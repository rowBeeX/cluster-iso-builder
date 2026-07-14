{
  lib,
  modulesPath,
  pkgs,
  ...
}:

{
  imports = [
    "${modulesPath}/installer/cd-dvd/installation-cd-minimal.nix"
  ];

  # Dateisysteme
  # Attributset-Form statt Listenform, damit einzelne Einträge selektiv überschrieben werden können
  boot.supportedFilesystems = {
    btrfs = true;
    zfs = true;
  };
  boot.zfs.forceImportRoot = false;

  # ZFS benötigt eine Host-ID (muss nicht persistent sein, da nur Live-ISO)
  networking.hostId = "deadbeef";

  # ISO-Metadaten
  networking.hostName = "nixos-installer";

  # mkForce überschreibt die Defaults aus installation-cd-minimal
  image.baseName = lib.mkForce "cluster-nixos-installer-26.05";
  image.fileName = lib.mkForce "cluster-nixos-installer-26.05.iso";
  isoImage.volumeID = lib.mkForce "CLUSTER2605";

  # Bessere Kompression (zstd ist schneller dekomprimierbar als xz, nur ~5 % größer)
  isoImage.squashfsCompression = "zstd -Xcompression-level 15";

  # Locale & Konsole
  i18n.defaultLocale = "de_DE.UTF-8";
  console = {
    font = "Lat2-Terminus16";
    keyMap = "de";
  };
  time.timeZone = "Europe/Berlin";

  # Nix-Einstellungen im Installer
  nix.settings = {
    # Parallelität anpassen (während des Bootstraps auf der Zielmaschine)
    max-jobs = "auto";
    cores = 0;
  };

  # SSH (nur Key-Auth, kein Passwort)
  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      PermitRootLogin             = "prohibit-password";
    };
  };

  # Benutzer
  users.users.root = {
    # Autorisierte Installer-SSH-Keys aus einer dedizierten Datei (#30), damit
    # der Operator-Key nicht im Modulcode verstreut liegt und Rotation ein
    # Ein-Datei-Edit ist. Für eine private Ablage: `iso-authorized-keys`
    # gitignoren und pro Build befüllen (z. B. aus ~/.ssh/id_ed25519.pub).
    # Es ist ein öffentlicher Key (kein Secret), aber ein Operator-Artefakt.
    openssh.authorizedKeys.keys =
      lib.filter (k: k != "" && !lib.hasPrefix "#" k) (
        lib.splitString "\n" (builtins.readFile ./iso-authorized-keys)
      );
  };

  # Pakete im Installer-Image
  environment.systemPackages = with pkgs; [
    age
    btrfs-progs
    btop
    curl
    cryptsetup
    git
    gptfdisk
    htop
    jq
    lshw
    lvm2
    mdadm
    neovim
    nfs-utils
    nixos-install-tools
    parted
    pciutils
    python3
    rsync
    sops
    usbutils
    wget
    zfs
  ];
}
