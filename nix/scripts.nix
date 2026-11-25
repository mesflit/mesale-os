# Commands that run from a checkout: the ISO build and the VM.
# The ISO build needs the network (apt), so it is a command and not a derivation.
{
  lib,
  writeShellApplication,
  debootstrap,
  dpkg,
  perl,
  wget,
  gnutar,
  zstd,
  xz,
  gzip,
  util-linux,
  coreutils,
  gnused,
  gnugrep,
  gawk,
  findutils,
  xorriso,
  squashfsTools,
  mtools,
  dosfstools,
  qemu_kvm,
  gh,
  git,
  cacert,
  debian-archive-keyring,
  OVMF,
  artwork,
  debs,
}:
let
  command =
    name: file: runtimeInputs: env:
    writeShellApplication {
      inherit name runtimeInputs;
      bashOptions = [ ];
      checkPhase = "";
      text = ''
        unset LD_LIBRARY_PATH LD_PRELOAD
        export PATH="/run/wrappers/bin:$PATH" # setuid newuidmap/newgidmap on NixOS
        ${lib.concatStrings (lib.mapAttrsToList (k: v: "export ${k}=${v}\n") env)}
        exec bash ./${file} "$@"
      '';
    };
in
{
  build =
    command "mesale-build" "build/build.sh"
      [
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
        xorriso
        squashfsTools
        mtools
        dosfstools
      ]
      {
        MESALE_REPO = "${debs}";
        MESALE_ARTWORK = "${artwork}";
        DEBIAN_KEYRING = "${debian-archive-keyring}/share/keyrings/debian-archive-keyring.gpg";
        SSL_CERT_FILE = "${cacert}/etc/ssl/certs/ca-bundle.crt";
      };

  vm = command "mesale-vm" "tools/vm.sh" [
    qemu_kvm
    coreutils
    gh
    git
  ] { OVMF_FD = "${OVMF.fd}/FV"; };
}
