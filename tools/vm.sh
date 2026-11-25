#!/usr/bin/env bash
# Try Mesale OS in a virtual machine. The ISO comes from GitHub Actions.
#
#   nix run              download the latest ISO if needed and boot it (UEFI)
#   nix run . -- bios    boot it with legacy BIOS
#   nix run . -- disk    boot the installed virtual disk
#   nix run . -- reset   delete the virtual disk
set -euo pipefail
WORK="${MESALE_VM:-$HOME/.cache/mesale-os/vm}"
MODE=${1:-iso}
[ $# -gt 0 ] && shift
mkdir -p "$WORK" out

fetch_iso() {
  local old
  old=$(cat out/*.iso.sha256 2>/dev/null || true)
  gh release download dev -p '*.iso.sha256' -D out --clobber || return 0
  if [ "$(cat out/*.iso.sha256)" = "$old" ] && compgen -G 'out/*.iso' >/dev/null; then return 0; fi
  rm -f out/*.iso
  gh release download dev -p '*.iso' -D out
  if ! (cd out && sha256sum -c ./*.iso.sha256); then
    rm -f out/*.iso out/*.iso.sha256
    echo "Checksum mismatch, download removed." >&2
    exit 1
  fi
}

case "$MODE" in
  reset) rm -f "$WORK/disk.qcow2" "$WORK/vars.fd"; exit 0 ;;
  iso | bios) fetch_iso ;;
  disk) ;;
  *) sed -n '2,7p' "$0"; exit 1 ;;
esac

[ -e "$WORK/disk.qcow2" ] || qemu-img create -q -f qcow2 "$WORK/disk.qcow2" 40G
if [ ! -e "$WORK/vars.fd" ]; then cp "$OVMF_FD/OVMF_VARS.fd" "$WORK/vars.fd"; chmod +w "$WORK/vars.fd"; fi

args=()
[ "$MODE" = disk ] || args+=(-cdrom "$(ls -t out/*.iso | head -1)" -boot d)
[ "$MODE" = bios ] || args+=(
  -drive "if=pflash,format=raw,readonly=on,file=$OVMF_FD/OVMF_CODE.fd"
  -drive "if=pflash,format=raw,file=$WORK/vars.fd")

exec qemu-system-x86_64 -enable-kvm -cpu host -smp 6 -m "${RAM:-4096}" -machine q35 -vga none \
  -drive "file=$WORK/disk.qcow2,if=virtio" -device virtio-vga,xres=1600,yres=900 \
  -nic user,model=virtio -device usb-ehci -device usb-tablet "${args[@]}" "$@"
