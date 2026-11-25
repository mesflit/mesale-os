#!/usr/bin/env bash
# Mesale OS'u sanal makinede dene (yerelde derleme YOK, ISO GitHub Actions'tan gelir).
#   nix run .#vm            son ISO'yu indir (gerekirse) ve aç
#   nix run .#vm -- disk    kurulu sanal diski aç
#   nix run .#vm -- bios    eski BIOS ile aç
#   nix run .#vm -- sifirla sanal diski sil
set -euo pipefail
W="${MESALE_VM:-$HOME/.cache/mesale-os/vm}"; mkdir -p "$W" out
mod=${1:-iso}; [ $# -gt 0 ] && shift
[ "$mod" = sifirla ] && { rm -f "$W"/disk.qcow2 "$W"/vars.fd; echo "Sanal disk silindi."; exit 0; }
if [ "$mod" != disk ]; then
  # sha256 değiştiyse yeni ISO'yu indir
  eski=$(cat out/*.sha256 2>/dev/null || true)
  if gh release download dev -p '*.sha256' -D out --clobber && [ "$(cat out/*.sha256)" != "$eski" -o ! -e out/mesale-os-*.iso ]; then
    rm -f out/*.iso; gh release download dev -p '*.iso' -D out
    (cd out && sha256sum -c ./*.sha256) || { rm -f out/*.iso out/*.sha256; echo "ISO bozuk indi." >&2; exit 1; }
  fi
fi
[ -e "$W/disk.qcow2" ] || qemu-img create -q -f qcow2 "$W/disk.qcow2" 40G
[ -e "$W/vars.fd" ] || { cp "$OVMF_FD/OVMF_VARS.fd" "$W/vars.fd"; chmod +w "$W/vars.fd"; }
M=(); [ "$mod" = disk ] || M=(-cdrom "$(ls -t out/*.iso | head -1)" -boot d)
[ "$mod" = bios ] || M+=(-drive if=pflash,format=raw,readonly=on,file="$OVMF_FD/OVMF_CODE.fd" -drive if=pflash,format=raw,file="$W/vars.fd")
exec qemu-system-x86_64 -enable-kvm -cpu host -smp 6 -m "${RAM:-4096}" -machine q35 -vga none \
  -drive file="$W/disk.qcow2",if=virtio -device virtio-vga,xres=1600,yres=900 -nic user,model=virtio -device usb-ehci -device usb-tablet \
  "${M[@]}" "$@"
