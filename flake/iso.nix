{ inputs, ... }:
{
  # Analog zu den Cluster-Repos (flake/hosts.nix); configuration.nix bleibt
  # die einzige Modulquelle der Installer-Umgebung.
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
