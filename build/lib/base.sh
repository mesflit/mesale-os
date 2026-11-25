# Stage 1: minimal Debian, kept as a tarball.
build_base() {
  [ -e "$BASE" ] && return
  say "Debian $SUITE base"
  local tmp=$WORK/base.tmp
  rm -rf "$tmp"
  debootstrap --arch=amd64 --variant=minbase --keyring="$DEBIAN_KEYRING" \
    --include=ca-certificates "$SUITE" "$tmp" "$MIRROR"
  umount -R -l "$tmp/proc" "$tmp/sys" 2>/dev/null || true
  rm -rf "$tmp"/var/cache/apt/archives/*.deb
  tar -C "$tmp" --one-file-system --exclude='./dev/*' --exclude='./proc/*' --exclude='./sys/*' -cpf "$BASE.part" .
  mv "$BASE.part" "$BASE"
  umount -R -l "$tmp"/dev/* 2>/dev/null || true
  rm -rf "$tmp" 2>/dev/null || true
}
