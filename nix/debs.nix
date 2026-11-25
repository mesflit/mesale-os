# Every directory in packages/ becomes a .deb; the result is an apt repository.
{
  lib,
  runCommand,
  callPackage,
  fetchFromGitHub,
  dpkg,
  apt,
  shellcheck,
  artwork,
  buildId,
}:
let
  inherit (callPackage ./release.nix { }) version codename;

  # Kernel module for Acer Nitro/Predator, built on the user's machine by DKMS.
  linuwu-sense = fetchFromGitHub {
    owner = "0x7375646F";
    repo = "Linuwu-Sense";
    rev = "4483b6c38b9bb963ac9ada9ca476578e0c63cc08";
    hash = "sha256-DFPzdypTqUD4TkqEBH/+QPIyCIMojd5euMVaLVWE2Cc=";
  };
in
runCommand "mesale-repo"
  {
    nativeBuildInputs = [
      dpkg
      apt
      shellcheck
    ];
  }
  ''
    cp -r --no-preserve=all ${../packages} pkg

    # Generated and third-party files
    cp -r --no-preserve=all ${artwork}/. pkg/mesale-base/
    install -Dm644 ${../vendor/flathub.flatpakrepo} pkg/mesale-base/etc/flatpak/remotes.d/flathub.flatpakrepo
    install -Dm644 ${../vendor/nvidia-cuda.asc} pkg/mesale-base/usr/share/mesale/nvidia-cuda.asc
    # Updates need the archive key (nix run .#create-signing-key)
    if [ -e ${../vendor}/mesale-archive.asc ]; then
      install -Dm644 ${../vendor}/mesale-archive.asc pkg/mesale-base/usr/share/keyrings/mesale-archive.asc
    else
      rm pkg/mesale-base/etc/apt/sources.list.d/mesale.sources
    fi
    install -m644 ${linuwu-sense}/src/linuwu_sense.c ${linuwu-sense}/LICENSE pkg/mesale-nitro/usr/src/linuwu-sense-1.0/

    grep -rlE '@(BUILD|VERSION|CODENAME)@' pkg | xargs sed -i \
      "s/@BUILD@/${version}.${buildId}/g; s/@VERSION@/${version}/g; s/@CODENAME@/${codename}/g"

    mkdir $out
    for p in pkg/*; do
      find $p -path '*/bin/*' -type f -exec chmod 755 {} +
      find $p/DEBIAN -type f ! -name control -exec chmod 755 {} +
      if [ -d $p/usr/lib/mesale ]; then find $p/usr/lib/mesale -maxdepth 1 -type f -exec chmod 755 {} +; fi
      if [ -d $p/etc/sudoers.d ]; then chmod 440 $p/etc/sudoers.d/*; fi
      if [ -d $p/etc ]; then (cd $p && find etc -type f | sed 's|^|/|') >$p/DEBIAN/conffiles; fi
      for s in $p/usr/bin/* $p/usr/lib/mesale/* $p/DEBIAN/p*; do
        if [ -f $s ] && head -1 $s | grep -q 'sh$'; then shellcheck -S error -e SC1091 $s; fi
      done
      dpkg-deb --root-owner-group -Zxz -z1 -b $p $out/''${p##*/}_all.deb
    done

    cd $out
    apt-ftparchive packages . >Packages
    gzip -nk Packages
    apt-ftparchive release -o APT::FTPArchive::Release::Origin=Mesale \
      -o APT::FTPArchive::Release::Label=Mesale -o APT::FTPArchive::Release::Suite=stable . >Release
  ''
