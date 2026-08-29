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

  # Attributset-Form statt Listenform, damit einzelne Einträge selektiv überschrieben werden können
  boot.supportedFilesystems = {
    btrfs = true;
    zfs = true;
  };
  boot.zfs.forceImportRoot = false;

  # ZFS benötigt eine Host-ID (muss nicht persistent sein, da nur Live-ISO)
  networking.hostId = "deadbeef";

  networking.hostName = "nixos-installer";

  # mkForce überschreibt die Defaults aus installation-cd-minimal
  image.baseName = lib.mkForce "cluster-nixos-installer-26.05";
  image.fileName = lib.mkForce "cluster-nixos-installer-26.05.iso";
  isoImage.volumeID = lib.mkForce "CLUSTER2605";

  # Bessere Kompression (zstd ist schneller dekomprimierbar als xz, nur ~5 % größer)
  isoImage.squashfsCompression = "zstd -Xcompression-level 15";

  i18n.defaultLocale = "de_DE.UTF-8";
  console = {
    font = "Lat2-Terminus16";
    keyMap = "de";
  };
  time.timeZone = "Europe/Berlin";

  nix.settings = {
    # Parallelität anpassen (während des Bootstraps auf der Zielmaschine)
    max-jobs = "auto";
    cores = 0;
  };

  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      PermitRootLogin = "prohibit-password";
    };
  };

  users.users.root = {
    # Aus dedizierter Datei statt im Modulcode, damit Rotation ein Ein-Datei-
    # Edit bleibt. Für private Ablage: `iso-authorized-keys` gitignoren und
    # pro Build befüllen.
    openssh.authorizedKeys.keys = lib.filter (k: k != "" && !lib.hasPrefix "#" k) (
      lib.splitString "\n" (builtins.readFile ./iso-authorized-keys)
    );
  };

  environment.systemPackages = with pkgs; [
    age
    btrfs-progs
    btop
    curl
    git
    gptfdisk
    htop
    jq
    lshw
    neovim
    nixos-install-tools
    pciutils
    python3
    rsync
    sops
    usbutils
    wget
    zfs
  ];
}
