{ self, ... }:

# Erwarteter CI-Zustand: Alle Flake-Checks sind erfolgreich. Erzwingt dieselbe
# Nix-Formatierung und Lint-Sauberkeit wie die Cluster-Repos, damit der ISO-
# Builder nicht stilistisch driftet.

{
  perSystem =
    { pkgs, ... }:
    let
      src = self;

      runSourceCheck =
        name: packages: command:
        pkgs.runCommand name
          {
            nativeBuildInputs = packages;
          }
          ''
            cp -R ${src} source
            chmod -R u+w source
            cd source
            ${command}
            touch "$out"
          '';
    in
    {
      checks = {
        nixfmt-rfc-style = runSourceCheck "nixfmt-rfc-style-check" [ pkgs.nixfmt ] ''
          find . -path ./.git -prune -o -name '*.nix' -print0 | xargs -0 nixfmt --check
        '';

        deadnix = runSourceCheck "deadnix-check" [ pkgs.deadnix ] ''
          deadnix --fail .
        '';

        statix = runSourceCheck "statix-check" [ pkgs.statix ] ''
          statix check .
        '';
      };
    };
}
