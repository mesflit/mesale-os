# Stage 3: squashfs and a hybrid ISO (BIOS, UEFI, Secure Boot).
# The initrd already sits next to the squashfs; the installer generates a new one.
make_squashfs() {
  say "squashfs"
  mksquashfs "$ROOT" "$1/live/filesystem.squashfs" -comp zstd \
    -Xcompression-level "${ZSTD:-15}" -b 1M -noappend -no-progress -mem 2G \
    -wildcards -e 'boot/initrd.img-*'
}

# Signed shim and GRUB come from the Debian image itself. gcdx64 finds the ISO by /.disk/info.
make_boot_tree() {
  local tree=$1 lib=$ROOT/usr/lib
  mkdir -p "$tree"/boot/grub/{fonts,x86_64-efi,i386-pc} "$tree/EFI/BOOT"
  cp "$ROOT/usr/share/grub/unicode.pf2" "$tree/boot/grub/fonts/"
  cp "$lib"/grub/x86_64-efi/*.{mod,lst} "$tree/boot/grub/x86_64-efi/"
  cp "$lib"/grub/i386-pc/*.{mod,lst} "$tree/boot/grub/i386-pc/"
  cp "$lib/shim/shimx64.efi.signed" "$tree/EFI/BOOT/BOOTX64.EFI"
  cp "$lib/shim/mmx64.efi.signed" "$tree/EFI/BOOT/mmx64.efi"
  cp "$lib/grub/x86_64-efi-signed/gcdx64.efi.signed" "$tree/EFI/BOOT/grubx64.efi"

  local efi=$tree/boot/grub/efi.img
  truncate -s 8M "$efi"
  mkfs.vfat -n MESALE_EFI "$efi" >/dev/null
  mmd -i "$efi" ::/EFI ::/EFI/BOOT
  mcopy -i "$efi" "$tree"/EFI/BOOT/* ::/EFI/BOOT/
}

# BIOS core image, built by the image's own GRUB so modules and core match.
make_bios_core() {
  in_chroot "$ROOT" grub-mkimage -O i386-pc-eltorito -p /boot/grub -o /tmp/bios.img \
    biosdisk iso9660 search normal configfile part_gpt part_msdos linux png gfxterm all_video
  cp "$ROOT/tmp/bios.img" "$WORK/bios.img"
}

make_iso() {
  local tree=$1 iso=$2
  say "ISO"
  xorriso -as mkisofs -quiet -iso-level 3 -full-iso9660-filenames \
    -joliet -joliet-long -rational-rock -volid MESALE_OS \
    --grub2-mbr "$ROOT/usr/lib/grub/i386-pc/boot_hybrid.img" -partition_offset 16 \
    -eltorito-boot boot/grub/bios.img -no-emul-boot -boot-load-size 4 -boot-info-table \
    --grub2-boot-info --eltorito-catalog boot/grub/boot.cat \
    -eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot \
    -append_partition 2 0xef "$tree/boot/grub/efi.img" -appended_part_as_gpt \
    -o "$iso" "$tree"
}

build_iso() {
  local tree=$WORK/iso iso="mesale-os-$VERSION-amd64.iso"
  rm -rf "$tree"
  mkdir -p "$tree"/{live,boot/grub,.disk}
  cp "$ROOT"/boot/vmlinuz-* "$tree/live/vmlinuz"
  cp "$ROOT"/boot/initrd.img-* "$tree/live/initrd.img"
  echo "Mesale OS $VERSION" >"$tree/.disk/info"
  cp config/grub.cfg "$tree/boot/grub/grub.cfg"
  cp "$MESALE_ARTWORK/usr/share/mesale/grub.png" "$tree/boot/grub/mesale.png"
  make_squashfs "$tree"
  make_boot_tree "$tree"
  cp "$WORK/bios.img" "$tree/boot/grub/bios.img"
  make_iso "$tree" "out/$iso"
  (cd out && sha256sum "$iso" | tee "$iso.sha256")
  ls -lh "out/$iso"
}
