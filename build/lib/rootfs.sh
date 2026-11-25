# Stage 2: the system image.
APT=(apt-get -qy -o Dpkg::Options::=--force-confnew -o Dpkg::Options::=--force-unsafe-io)

apt_install() { in_chroot "$ROOT" "${APT[@]}" install --no-install-recommends "$@"; }

copy_repo() {
  rm -rf "$ROOT/usr/share/mesale/repo"
  mkdir -p "$ROOT/usr/share/mesale"
  cp -r --no-preserve=all "$MESALE_REPO" "$ROOT/usr/share/mesale/repo"
}

preseed() {
  printf 'en_US.UTF-8 UTF-8\n' >"$ROOT/etc/locale.gen"
  in_chroot "$ROOT" debconf-set-selections <<'EOF'
locales locales/default_environment_locale select en_US.UTF-8
locales locales/locales_to_be_generated multiselect en_US.UTF-8 UTF-8
keyboard-configuration keyboard-configuration/layoutcode string us
tzdata tzdata/Areas select Etc
tzdata tzdata/Zones/Etc select UTC
EOF
}

# Pin every source package that came from testing, so upgrades and sibling
# packages (-dev, i386, ...) keep coming from the same place.
pin_testing() {
  cp build/forky_pins.py "$ROOT/tmp/"
  in_chroot "$ROOT" python3 /tmp/forky_pins.py >"$WORK/testing-sources.txt"
  cat >"$ROOT/etc/apt/preferences.d/mesale-gnome" <<EOF
Explanation: GNOME and what it requires, from Debian testing (generated at build time)
Package: $(cat "$WORK/testing-sources.txt") python3 python3-* libpython3-*
Pin: release n=forky
Pin-Priority: 900
EOF
}

install_system() {
  say "System"
  rm -rf "$ROOT" "$ROOT.ok"
  mkdir -p "$ROOT"
  tar -C "$ROOT" -xpf "$BASE"
  mount_chroot "$ROOT"
  rm -f "$ROOT/etc/apt/sources.list"
  printf '#!/bin/sh\nexit 101\n' >"$ROOT/usr/sbin/policy-rc.d" # no services in the chroot
  chmod 755 "$ROOT/usr/sbin/policy-rc.d"
  cp -r --no-preserve=all packages/mesale-base/etc/apt/. "$ROOT/etc/apt/"
  copy_repo
  in_chroot "$ROOT" apt-get -q update
  preseed
  apt_install $CORE $NETWORK $KERNEL $FIRMWARE $BOOT $GRAPHICS $VM_GUEST $DESKTOP_EXTRA
  say "GNOME"
  apt_install -t forky $GNOME
  pin_testing
  apt_install mesale-live $APPS
  apt_install $OFFLINE_FEATURES
  in_chroot "$ROOT" systemctl set-default graphical.target
  in_chroot "$ROOT" systemctl enable NetworkManager systemd-resolved gdm3 2>/dev/null || true
  in_chroot "$ROOT" systemctl disable NetworkManager-wait-online.service 2>/dev/null || true
  touch "$ROOT.ok"
}

refresh_system() {
  say "Refreshing Mesale packages"
  mount_chroot "$ROOT"
  copy_repo
  in_chroot "$ROOT" apt-get -q update
  apt_install --reinstall mesale-base mesale-desktop mesale-live
}

write_manifest() {
  in_chroot "$ROOT" dpkg-query -W -f '${Package} ${Version}\n' >out/packages.txt
  grep -E '^(linux-image-amd64|mesa-vulkan-drivers|firmware-amd-graphics|gnome-shell|calamares) ' \
    out/packages.txt | tee out/versions.txt
}

# Leave nothing machine-specific behind.
clean_system() {
  rm -f "$ROOT/usr/sbin/policy-rc.d"
  in_chroot "$ROOT" apt-get clean
  # Keep only the local repository index: offline features install from it.
  rm -rf "$ROOT"/var/lib/apt/lists/*
  in_chroot "$ROOT" apt-get -q update -o Dir::Etc::sourceparts=- \
    -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/mesale-local.list
  umount_chroot "$ROOT"
  rm -f "$ROOT/etc/resolv.conf" "$ROOT/etc/hostname" "$ROOT"/var/log/*.log "$ROOT"/var/log/apt/*
  rm -rf "$ROOT"/tmp/* "$ROOT"/run/* "$ROOT"/root/.cache
  ln -s ../run/systemd/resolve/stub-resolv.conf "$ROOT/etc/resolv.conf"
  : >"$ROOT/etc/machine-id"
}

build_rootfs() {
  if [ "$STAGE" = iso ] && [ -e "$ROOT.ok" ]; then refresh_system; else install_system; fi
  in_chroot "$ROOT" /usr/lib/mesale/installer-options
  in_chroot "$ROOT" update-initramfs -u -k all
  write_manifest
  make_bios_core
  clean_system
}
