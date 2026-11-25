{
  description = "Mesale OS: Debian base, newest kernel, drivers and GNOME";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      inherit (pkgs) lib;

      artwork = pkgs.callPackage ./nix/artwork.nix { };
      debs = pkgs.callPackage ./nix/debs.nix {
        inherit artwork;
        buildId = self.lastModifiedDate or "19700101000000";
      };
      video = pkgs.callPackage ./nix/video.nix { inherit artwork; };
      website = pkgs.callPackage ./nix/website.nix { inherit artwork video; };
      scripts = pkgs.callPackage ./nix/scripts.nix { inherit artwork debs; };

      app = pkg: { type = "app"; program = lib.getExe pkg; meta.description = pkg.name; };
    in
    {
      packages.${system} = {
        inherit artwork debs video website;
        inherit (scripts) build vm sign-repo create-signing-key;
        default = scripts.vm;
      };
      apps.${system} = {
        default = app scripts.vm;
        vm = app scripts.vm;
        build = app scripts.build;
        sign-repo = app scripts.sign-repo;
        create-signing-key = app scripts.create-signing-key;
      };
      checks.${system} = removeAttrs (pkgs.callPackage ./nix/checks.nix {
        inherit artwork debs;
      }) [ "override" "overrideDerivation" ];
      formatter.${system} = pkgs.nixfmt-rfc-style;
    };
}
