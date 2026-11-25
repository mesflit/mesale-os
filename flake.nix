{
  description = "Mesale OS — Debian stable tabanlı, en yeni kernel/sürücülü, cam görünümlü GNOME dağıtımı";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      # Derleyicinin çekirdeği: Debian tabanını kurmaya yeten araçlar.
      # Gerisi (xorriso, grub, squashfs...) Debian kutusunun İÇİNDEN gelir.
      buildTools = with pkgs; [
        debootstrap
        dpkg
        perl
        wget
        gnutar
        zstd
        xz
        gzip
        util-linux
        coreutils
        gnused
        gnugrep
        gawk
        findutils
        curl
      ];

      script =
        name: file: deps:
        pkgs.writeShellApplication {
          inherit name;
          runtimeInputs = deps;
          checkPhase = "";
          bashOptions = [ ];
          text = ''
            unset LD_LIBRARY_PATH LD_PRELOAD
            export PATH="/run/wrappers/bin:$PATH" # newuidmap/newgidmap (setuid)
            export DEBIAN_KEYRING=${pkgs.debian-archive-keyring}/share/keyrings/debian-archive-keyring.gpg
            export OVMF_FD=${pkgs.OVMF.fd}/FV
            exec bash ./${file} "$@"
          '';
        };
      build = script "mesale-build" "build.sh" buildTools;
      vm = script "mesale-vm" "vm.sh" [ pkgs.qemu_kvm pkgs.coreutils pkgs.gh pkgs.git ];
    in
    {
      packages.${system} = { inherit build vm; };
      apps.${system} = {
        default = { type = "app"; program = "${vm}/bin/mesale-vm"; };
        build = { type = "app"; program = "${build}/bin/mesale-build"; };
        vm = { type = "app"; program = "${vm}/bin/mesale-vm"; };
      };
    };
}
