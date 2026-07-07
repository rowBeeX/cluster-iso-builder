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

  # ---------------------------------------------------------------------------
  # Dateisysteme
  # ---------------------------------------------------------------------------
  # Attributset-Form statt Listenform, damit einzelne Einträge selektiv überschrieben werden können
  boot.supportedFilesystems = {
    btrfs = true;
    zfs = true;
  };
  boot.zfs.forceImportRoot = false;

  # ZFS benötigt eine Host-ID (muss nicht persistent sein, da nur Live-ISO)
  networking.hostId = "deadbeef";

  # ---------------------------------------------------------------------------
  # ISO-Metadaten
  # ---------------------------------------------------------------------------
  networking.hostName = "nixos-installer";

  # mkForce überschreibt die Defaults aus installation-cd-minimal
  image.baseName = lib.mkForce "cluster-nixos-installer-26.05";
  image.fileName = lib.mkForce "cluster-nixos-installer-26.05.iso";
  isoImage.volumeID = lib.mkForce "CLUSTER2605";

  # Bessere Kompression (zstd ist schneller dekomprimierbar als xz, nur ~5 % größer)
  isoImage.squashfsCompression = "zstd -Xcompression-level 15";

  # ---------------------------------------------------------------------------
  # Locale & Konsole
  # ---------------------------------------------------------------------------
  i18n.defaultLocale = "de_DE.UTF-8";
  console = {
    font = "Lat2-Terminus16";
    keyMap = "de";
  };
  time.timeZone = "Europe/Berlin";

  # ---------------------------------------------------------------------------
  # Nix-Einstellungen im Installer
  # ---------------------------------------------------------------------------
  nix.settings = {
    # Öffentlicher Binary Cache für schnelle Pulls
    substituters = [
      "https://cache.nixos.org"
    ];
    trusted-public-keys = [
      "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
    ];
    # Parallelität anpassen (während des Bootstraps auf der Zielmaschine)
    max-jobs = "auto";
    cores = 0;
  };

  # ---------------------------------------------------------------------------
  # SSH (nur Key-Auth, kein Passwort)
  # ---------------------------------------------------------------------------
  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      PermitRootLogin             = "prohibit-password";
    };
  };

  # ---------------------------------------------------------------------------
  # Benutzer
  # ---------------------------------------------------------------------------
  users.users.root = {
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGiIrQddHA7yHu2dqGiJP2+fL3uVfncgyezapF99br8 tobias@tobias-computer"
    ];
  };

  # ---------------------------------------------------------------------------
  # Pakete im Installer-Image
  # ---------------------------------------------------------------------------
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
