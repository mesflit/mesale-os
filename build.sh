#!/usr/bin/env bash
# Mesale OS ISO derleyicisi — root/docker GEREKMEZ (kullanıcı isim alanı).
#
#   nix run .              her şeyi derle → out/mesale-os-*.iso
#   nix run . -- paketler  sadece .deb paketleri (içi/dışı hızlı deneme)
#   nix run . -- iso       sistemi yeniden kurmadan config + ISO
#   nix run . -- temizle   ~/.cache/mesale-os klasörünü sil
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

if [ "${1:-}" != --ic ]; then
  export MESALE_BUILD="${MESALE_BUILD:-$HOME/.cache/mesale-os}"
  mkdir -p "$MESALE_BUILD" out
  export MESALE_STAGE="${1:-hepsi}"
  N=(unshare --mount --pid --fork --mount-proc --kill-child)
  # root değilsek (yerel): userns, subuid aralığı konteyner kullanıcılarına eşlenir. CI'da zaten rootuz.
  [ "$(id -u)" -eq 0 ] || N+=(--map-auto --map-root-user)
  exec "${N[@]}" bash "$PWD/build.sh" --ic
fi

export container=lxc LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive
. ./mesale.conf
B=$MESALE_BUILD   # ağır dosyalar depo dışında (varsayılan ~/.cache/mesale-os)
say() { printf '\033[1;35m==>\033[0m \033[1m%s\033[0m\n' "$*"; }

[ "$MESALE_STAGE" = temizle ] && { rm -rf "$B"; say "$B silindi"; exit 0; }

# chroot içine sanal dosya sistemleri (sadece bu mount ns'te; çıkışta kaybolur)
baglat() {
  local r=$1
  mount -t proc proc "$r/proc"
  mount --rbind /sys "$r/sys"
  mount -t tmpfs -o mode=755 tmpfs "$r/dev"
  local d
  for d in null zero full random urandom tty; do
    : >"$r/dev/$d"; mount --bind "/dev/$d" "$r/dev/$d"
  done
  mkdir -p "$r/dev/pts" "$r/dev/shm"
  mount -t devpts -o newinstance,ptmxmode=0666,mode=620 devpts "$r/dev/pts"
  ln -s pts/ptmx "$r/dev/ptmx"
  ln -s /proc/self/fd "$r/dev/fd"
  ln -s /proc/self/fd/0 "$r/dev/stdin"
  ln -s /proc/self/fd/1 "$r/dev/stdout"
  ln -s /proc/self/fd/2 "$r/dev/stderr"
  mount -t tmpfs -o mode=755 tmpfs "$r/run"
  mount -t tmpfs tmpfs "$r/tmp"
  rm -f "$r/etc/resolv.conf"
  cat /etc/resolv.conf >"$r/etc/resolv.conf"
}
coz() { local r=$1 m; for m in tmp run dev sys proc; do umount -R -l "$r/$m" 2>/dev/null || true; done; }
icinde() { # icinde <kök> komut...
  local r=$1; shift
  env -i HOME=/root TERM="${TERM:-dumb}" LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "$(command -v chroot)" "$r" "$@"
}

########## 1. Debian tabanı ##########
if [ ! -e "$B/base.tar" ]; then
  say "Debian $SUITE tabanı"
  rm -rf "$B/base.tmp"
  debootstrap --arch=amd64 --variant=minbase --keyring="$DEBIAN_KEYRING" \
    --include=ca-certificates "$SUITE" "$B/base.tmp" "$MIRROR"
  umount -R -l "$B/base.tmp/proc" "$B/base.tmp/sys" 2>/dev/null || true
  rm -rf "$B/base.tmp"/var/cache/apt/archives/*.deb
  tar -C "$B/base.tmp" --one-file-system --exclude='./dev/*' --exclude='./proc/*' --exclude='./sys/*' -cpf "$B/base.tar.y" .
  mv "$B/base.tar.y" "$B/base.tar"
  umount -R -l "$B/base.tmp"/dev/* 2>/dev/null || true
  rm -rf "$B/base.tmp" 2>/dev/null || true
fi

########## 2. Derleme kutusu (ISO/paket araçları) ##########
if [ ! -e "$B/kutu.ok" ]; then
  say "Derleme kutusu"
  rm -rf "$B/kutu"; mkdir -p "$B/kutu"; tar -C "$B/kutu" -xpf "$B/base.tar"
  baglat "$B/kutu"
  icinde "$B/kutu" apt-get update -q
  icinde "$B/kutu" apt-get install -qy --no-install-recommends \
    xorriso squashfs-tools mtools dosfstools grub-pc-bin grub-efi-amd64-bin grub-common \
    grub-efi-amd64-signed shim-signed librsvg2-bin python3 python3-numpy python3-pil dpkg-dev apt-utils zstd \
    fonts-inter libglib2.0-bin gettext shellcheck
  coz "$B/kutu"
  touch "$B/kutu.ok"
fi

########## 3. Mesale paketleri ##########
say "Mesale paketleri"
SURUM="$VERSION.$(date -u +%Y%m%d%H%M)"
rm -rf "$B/pk" "$B/depo"; mkdir -p "$B/depo"; cp -a packages "$B/pk"
chown -R 0:0 "$B/pk"; chmod -R u=rwX,go=rX "$B/pk"
baglat "$B/kutu"
mkdir -p "$B/kutu/is"; mount --bind "$B" "$B/kutu/is"
if [ ! -e "$B/gorsel.ok" ] || [ -n "$(find gorsel -newer "$B/gorsel.ok")" ]; then
  rm -rf "$B/gorsel" "$B/gorsel-kod"; cp -a gorsel "$B/gorsel-kod"
  icinde "$B/kutu" python3 /is/gorsel-kod/uret.py /is/gorsel
  touch "$B/gorsel.ok"
fi
cp -a "$B/gorsel/." "$B/pk/mesale-base/"
for p in "$B"/pk/*; do
  ad=${p##*/}
  grep -rlE '@(SURUM|SURUMKISA|KODAD)@' "$p" --include=control --include=os-release --include=branding.desc |
    xargs -r sed -i "s/@SURUM@/$SURUM/g; s/@SURUMKISA@/$VERSION/g; s/@KODAD@/$CODENAME/g"
  find "$p" -path '*/bin/*' -type f -exec chmod 755 {} +
  find "$p/DEBIAN" -type f ! -name control -exec chmod 755 {} +
  find "$p/usr/lib/mesale" -maxdepth 1 -name '*' -exec chmod 755 {} + 2>/dev/null || true
  [ -d "$p/etc/sudoers.d" ] && chmod 440 "$p"/etc/sudoers.d/*
  if [ -d "$p/etc" ]; then (cd "$p" && find etc -type f ! -path 'etc/calamares/features.yaml' | sed 's|^|/|') >"$p/DEBIAN/conffiles"; fi
  for s in "$p"/usr/bin/* "$p"/DEBIAN/p*; do
    if [ -f "$s" ] && head -1 "$s" | grep -q 'sh$'; then
      icinde "$B/kutu" shellcheck -S error -e SC1091 "/is/pk/${s#"$B/pk/"}"; fi
  done
  icinde "$B/kutu" dpkg-deb -Zxz -z1 -b "/is/pk/$ad" "/is/depo/${ad}_all.deb" >/dev/null
done
icinde "$B/kutu" sh -c 'cd /is/depo && apt-ftparchive packages . > Packages && gzip -k Packages && apt-ftparchive release . > Release'
ls "$B/depo"
[ "$MESALE_STAGE" = paketler ] && exit 0

########## 4. Sistem kökü ##########
K=$B/kok
APT=(apt-get -qy -o Dpkg::Options::=--force-confnew -o Dpkg::Options::=--force-unsafe-io)
depoyu_koy() { rm -rf "$K/usr/share/mesale/depo"; mkdir -p "$K/usr/share/mesale"; cp -a "$B/depo" "$K/usr/share/mesale/depo"; }
if [ ! -e "$B/kok.ok" ] || [ "$MESALE_STAGE" = hepsi ]; then
  say "Sistem kökü kuruluyor"
  rm -f "$B/kok.ok"; rm -rf "$K"; mkdir -p "$K"; tar -C "$K" -xpf "$B/base.tar"
  baglat "$K"
  rm -f "$K/etc/apt/sources.list"
  printf '#!/bin/sh\nexit 101\n' >"$K/usr/sbin/policy-rc.d"; chmod 755 "$K/usr/sbin/policy-rc.d"
  cp -a "$B"/pk/mesale-base/etc/apt/. "$K/etc/apt/"
  depoyu_koy
  icinde "$K" apt-get -q update
  printf 'tr_TR.UTF-8 UTF-8\nen_US.UTF-8 UTF-8\n' >"$K/etc/locale.gen"
  printf 'locales locales/default_environment_locale select en_US.UTF-8\nlocales locales/locales_to_be_generated multiselect tr_TR.UTF-8 UTF-8, en_US.UTF-8 UTF-8\nkeyboard-configuration keyboard-configuration/layoutcode string us\ntzdata tzdata/Areas select Europe\ntzdata tzdata/Zones/Europe select London\n' | icinde "$K" debconf-set-selections
  # Yer önemli: önerilenler kapalı, gerekenler açıkça listede
  icinde "$K" "${APT[@]}" install --no-install-recommends \
    systemd-sysv dbus dbus-user-session libpam-systemd locales tzdata console-setup keyboard-configuration kbd sudo less nano bash-completion \
    iproute2 iputils-ping wpasupplicant wireless-regdb network-manager systemd-resolved systemd-timesyncd libnss-resolve libnss-myhostname \
    linux-image-amd64 linux-headers-amd64 initramfs-tools zstd dkms build-essential \
    firmware-linux-free firmware-misc-nonfree firmware-amd-graphics firmware-intel-graphics firmware-iwlwifi firmware-realtek firmware-mediatek firmware-atheros firmware-brcm80211 firmware-sof-signed firmware-intel-sound firmware-cirrus amd64-microcode intel-microcode \
    grub-efi-amd64 grub-efi-amd64-signed shim-signed grub-pc-bin efibootmgr os-prober \
    mesa-vulkan-drivers mesa-va-drivers libgl1-mesa-dri libegl-mesa0 libglx-mesa0 \
    spice-vdagent qemu-guest-agent open-vm-tools-desktop mokutil pciutils usbutils curl wget unzip fwupd plymouth polkitd rtkit man-db \
    xdg-desktop-portal-gtk gnome-bluetooth-sendto libpam-gnome-keyring gnome-menus
  say "GNOME (Debian testing'den en yeni sürüm)"
  icinde "$K" "${APT[@]}" install --no-install-recommends -t forky $GNOME
  # testing'den gelen HER kaynak paketi sabitle: güncelleme ve 32-bit/-dev eşleri aynı yerden gelsin
  cp forky-pins.py "$K/tmp/"; icinde "$K" python3 /tmp/forky-pins.py >"$B/forky.txt"
  printf 'Explanation: GNOME and what it requires, from Debian testing (generated at build time)\nPackage: %s python3 python3-* libpython3-*\nPin: release n=forky\nPin-Priority: 900\n' "$(cat "$B/forky.txt")" >"$K/etc/apt/preferences.d/mesale-gnome"
  icinde "$K" "${APT[@]}" install --no-install-recommends mesale-live $APPS
  # Ağsız kurulabilen özelliklerin bağımlılıkları hazır dursun
  icinde "$K" "${APT[@]}" install --no-install-recommends systemd-zram-generator irqbalance systemd-oomd ufw apparmor
  icinde "$K" systemctl set-default graphical.target
  icinde "$K" systemctl enable NetworkManager systemd-resolved gdm3 2>/dev/null || true
  icinde "$K" systemctl disable NetworkManager-wait-online.service 2>/dev/null || true
  touch "$B/kok.ok"
else
  say "Mesale paketleri kökte yenileniyor"
  baglat "$K"
  depoyu_koy
  icinde "$K" apt-get -q update
  icinde "$K" "${APT[@]}" install --no-install-recommends --reinstall mesale-base mesale-desktop mesale-live
fi
rm -f "$K/etc/cron.d/timeshift-hourly" "$K/usr/sbin/policy-rc.d"
rm -f "$K"/usr/bin/__pycache__ 2>/dev/null || true
icinde "$K" /usr/lib/mesale/installer-options
icinde "$K" update-initramfs -u -k all

say "Sürümler"
icinde "$K" dpkg-query -W -f '${Package} ${Version}\n' linux-image-amd64 mesa-vulkan-drivers firmware-amd-graphics gnome-shell calamares | tee "$B/surumler.txt"
icinde "$K" dpkg-query -W -f '${Package} ${Version}\n' >"out/paket-listesi.txt"

########## 5. Temizle, squashfs, ISO ##########
I=$B/iso; rm -rf "$I"; mkdir -p "$I"/{live,boot/grub,EFI/BOOT,.disk}
cp "$K"/boot/vmlinuz-* "$I/live/vmlinuz"; cp "$K"/boot/initrd.img-* "$I/live/initrd.img"
icinde "$K" apt-get clean
# apt listeleri: sadece yerel depo kalsın (ağsız özellik kurulumu için)
rm -rf "$K"/var/lib/apt/lists/*
icinde "$K" apt-get -q update -o Dir::Etc::sourceparts=- -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/mesale-local.list
coz "$K"
rm -f "$K/etc/resolv.conf" "$K/etc/hostname" "$K"/var/log/*.log "$K"/var/log/apt/*; rm -rf "$K"/tmp/* "$K"/run/* "$K"/root/.cache
ln -s ../run/systemd/resolve/stub-resolv.conf "$K/etc/resolv.conf"
: >"$K/etc/machine-id"
say "squashfs (birkaç dakika)"
mkdir -p "$B/kutu/kok"; mount --bind "$K" "$B/kutu/kok"
rm -f "$I/live/filesystem.squashfs"
icinde "$B/kutu" mksquashfs /kok /is/iso/live/filesystem.squashfs -comp zstd -Xcompression-level "${ZSTD:-15}" -b 1M -noappend -no-progress -mem 2G -e /kok/proc/* /kok/sys/* /kok/dev/*  -wildcards | tail -3
umount "$B/kutu/kok"

say "ISO"
echo "Mesale OS $VERSION" >"$I/.disk/info"
cp iso.grub.cfg "$I/boot/grub/grub.cfg"; cp "$B/gorsel/usr/share/mesale/grub.png" "$I/boot/grub/mesale.png"
ISO="mesale-os-$VERSION-amd64.iso"
icinde "$B/kutu" bash -euc "
  cd /is/iso
  mkdir -p boot/grub/fonts boot/grub/x86_64-efi boot/grub/i386-pc
  cp /usr/share/grub/unicode.pf2 boot/grub/fonts/
  cp /usr/lib/grub/x86_64-efi/*.mod /usr/lib/grub/x86_64-efi/*.lst boot/grub/x86_64-efi/
  cp /usr/lib/grub/i386-pc/*.mod /usr/lib/grub/i386-pc/*.lst boot/grub/i386-pc/
  cp /usr/lib/shim/shimx64.efi.signed EFI/BOOT/BOOTX64.EFI
  cp /usr/lib/shim/mmx64.efi.signed EFI/BOOT/mmx64.efi
  cp /usr/lib/grub/x86_64-efi-signed/gcdx64.efi.signed EFI/BOOT/grubx64.efi
  truncate -s 8M boot/grub/efi.img && mkfs.vfat -n MESALE_EFI boot/grub/efi.img >/dev/null
  mmd -i boot/grub/efi.img ::/EFI ::/EFI/BOOT
  mcopy -i boot/grub/efi.img EFI/BOOT/* ::/EFI/BOOT/
  grub-mkimage -O i386-pc-eltorito -p /boot/grub -o boot/grub/bios.img biosdisk iso9660 search normal configfile part_gpt part_msdos linux png gfxterm all_video
  xorriso -as mkisofs -quiet -iso-level 3 -full-iso9660-filenames -joliet -joliet-long -rational-rock -volid MESALE_OS \
    --grub2-mbr /usr/lib/grub/i386-pc/boot_hybrid.img -partition_offset 16 \
    -eltorito-boot boot/grub/bios.img -no-emul-boot -boot-load-size 4 -boot-info-table --grub2-boot-info --eltorito-catalog boot/grub/boot.cat \
    -eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot -append_partition 2 0xef boot/grub/efi.img -appended_part_as_gpt \
    -o /is/$ISO /is/iso"
mv "$B/$ISO" "out/$ISO"; (cd out && sha256sum "$ISO" | tee "$ISO.sha256"); ls -lh "out/$ISO"
