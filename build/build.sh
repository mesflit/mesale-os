#!/usr/bin/env bash
# Build the Mesale OS ISO. Run it through Nix: nix run .#build [-- all|iso|clean]
# Works as root (CI) or rootless (user namespace).
#
#   all     full build (default): out/mesale-os-*.iso
#   iso     refresh the Mesale packages in the existing root, then make the ISO
#   clean   delete the work directory
#
# Nix provides the tools and these inputs:
#   MESALE_REPO       apt repository with the Mesale packages (nix build .#debs)
#   MESALE_ARTWORK    generated images (nix build .#artwork)
#   DEBIAN_KEYRING    Debian archive keys
set -euo pipefail
PROJECT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
cd "$PROJECT"

# Re-run inside private mount and PID namespaces, so no mount can leak out.
if [ "${1:-}" != --inside ]; then
  : "${MESALE_REPO:?run through nix run .#build}"
  export WORK="${MESALE_BUILD:-$HOME/.cache/mesale-os}" STAGE="${1:-all}"
  case "$STAGE" in all | iso | clean) ;; *) sed -n '2,8p' "$0"; exit 1 ;; esac
  mkdir -p "$WORK" out
  ns=(unshare --mount --pid --fork --mount-proc --kill-child)
  [ "$(id -u)" -eq 0 ] || ns+=(--map-auto --map-root-user)
  exec "${ns[@]}" bash "$PROJECT/build/build.sh" --inside
fi

export container=lxc # tells debootstrap to bind-mount devices instead of mknod
. config/mesale.conf
. config/packages.sh
for part in common base rootfs iso; do . "build/lib/$part.sh"; done

if [ "$STAGE" = clean ]; then rm -rf "$WORK"; exit 0; fi
build_base
build_rootfs
build_iso
