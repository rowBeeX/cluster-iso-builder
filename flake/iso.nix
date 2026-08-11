{ inputs, ... }:
{
  # Die reproduzierbare Installer-ISO als Flake-Paket. Analog zu den Cluster-
  # Repos (flake/hosts.nix) wird die NixOS-Konfiguration hier zusammengesetzt;
  # configuration.nix bleibt die einzige Modulquelle der Installer-Umgebung.
  perSystem =
    { system, ... }:
    let
      installerIso =
        (inputs.nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [ ../configuration.nix ];
        }).config.system.build.isoImage;
    in
    {
      packages.installerIso = installerIso;
    };
}
