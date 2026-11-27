# Package sets for the system image. Recommends are off, so everything needed is listed.

CORE="systemd-sysv dbus dbus-user-session libpam-systemd locales tzdata console-setup
  keyboard-configuration kbd sudo less nano bash-completion polkitd rtkit
  pciutils curl plymouth mokutil"

NETWORK="iproute2 iputils-ping wpasupplicant wireless-regdb network-manager
  systemd-resolved systemd-timesyncd libnss-resolve libnss-myhostname"

# Compilers and headers stay off the ISO: the driver features pull them in through DKMS.
KERNEL="linux-image-amd64 initramfs-tools zstd"

FIRMWARE="firmware-linux-free firmware-misc-nonfree firmware-amd-graphics
  firmware-intel-graphics firmware-iwlwifi firmware-realtek firmware-mediatek
  firmware-atheros firmware-brcm80211 firmware-sof-signed firmware-intel-sound
  firmware-cirrus amd64-microcode intel-microcode"

BOOT="grub-efi-amd64 grub-efi-amd64-signed shim-signed grub-pc-bin efibootmgr os-prober"

GRAPHICS="mesa-vulkan-drivers mesa-va-drivers libgl1-mesa-dri libegl-mesa0 libglx-mesa0"

VM_GUEST="spice-vdagent qemu-guest-agent open-vm-tools-desktop"

# Installed together with GNOME from testing. Built from stable, these would pull
# a second ICU and a second Evolution Data Server next to the ones GNOME uses.
DESKTOP_EXTRA="xdg-desktop-portal-gtk libpam-gnome-keyring xfsprogs"

# Newest GNOME, from Debian testing. Its dependencies follow automatically.
GNOME="gnome-shell gnome-session gdm3 gnome-control-center gnome-settings-daemon
  mutter-common xwayland nautilus ptyxis gnome-text-editor loupe papers
  gnome-software gnome-software-plugin-flatpak gnome-software-plugin-deb xdg-desktop-portal-gnome
  gnome-shell-extension-dash-to-panel gnome-shell-extension-blur-my-shell
  gnome-shell-extension-tiling-assistant gnome-shell-extension-appindicator
  adwaita-icon-theme gir1.2-adw-1 gstreamer1.0-plugins-good python3-gi e2fsprogs
  systemd-sysv libpam-systemd systemd-resolved systemd-oomd systemd-timesyncd
  libnss-resolve libnss-myhostname udev"

# Preinstalled applications, kept to the essentials. Each one can be unchecked in the
# installer; everything else (browser, calendar, codecs, ...) is an optional feature.
APPS="gnome-text-editor loupe papers
  gnome-software gnome-software-plugin-flatpak gnome-software-plugin-deb"

# Dependencies of the features that must install without a network. The installer
# removes the ones no chosen feature needs (see offline-packages in build/lib/rootfs.sh).
OFFLINE_FEATURES="systemd-zram-generator irqbalance systemd-oomd ufw apparmor"
