{
  description = "Reproducible NixOS installer ISO for Sedware clusters";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      installerIso = (
        nixpkgs.lib.nixosSystem {
          inherit system;
          modules = [ ./configuration.nix ];
        }
      ).config.system.build.isoImage;
    in
    {
      packages.${system} = {
        default = installerIso;
        installerIso = installerIso;
      };

      formatter.${system} = nixpkgs.legacyPackages.${system}.nixfmt-tree;

    };
}
