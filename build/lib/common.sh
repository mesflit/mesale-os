# Shared helpers. Work directory layout:
#   base.tar  minimal Debian    root/  the system image    iso/  ISO tree
BASE=$WORK/base.tar
ROOT=$WORK/root

say() { printf '\033[1;34m==>\033[0m \033[1m%s\033[0m\n' "$*"; }

# Mount the virtual file systems a chroot needs. They vanish with the namespace.
mount_chroot() {
  local r=$1 dev
  mount -t proc proc "$r/proc"
  mount --rbind /sys "$r/sys"
  # mode=755: a sticky world-writable /dev trips fs.protected_regular
  mount -t tmpfs -o mode=755 tmpfs "$r/dev"
  for dev in null zero full random urandom tty; do
    : >"$r/dev/$dev"
    mount --bind "/dev/$dev" "$r/dev/$dev"
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

umount_chroot() {
  local m
  for m in tmp run dev sys proc; do umount -R -l "$1/$m" 2>/dev/null || true; done
}

# in_chroot <root> <command...>
in_chroot() {
  local r=$1
  shift
  env -i HOME=/root TERM="${TERM:-dumb}" LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    "$(command -v chroot)" "$r" "$@"
}
