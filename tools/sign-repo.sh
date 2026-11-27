#!/usr/bin/env bash
# Usage: APT_SIGNING_KEY=<armored private key> sign-repo.sh DIR
set -euo pipefail
[ $# -eq 1 ] || { sed -n 2p "$0"; exit 1; }
: "${APT_SIGNING_KEY:?}"
GNUPGHOME=$(mktemp -d)
export GNUPGHOME
trap 'rm -rf "$GNUPGHOME"' EXIT

mkdir -p "$1"
cp -L --no-preserve=mode "$MESALE_REPO"/* "$1/"

# Every build stamps every package with a new version. Where a package is the same
# as the published one apart from that version, keep the published one, so installed
# systems only download what really changed. MESALE_PUBLISHED is the live repository URL.
unpack() { # deb dir: contents, file modes and control fields without the version
  dpkg-deb -R "$1" "$2"
  sed -i '/^Version: /d' "$2/DEBIAN/control"
  (cd "$2" && find . -printf '%p %m %y\n' | LC_ALL=C sort) >"$2.modes"
}
if [ -n "${MESALE_PUBLISHED:-}" ]; then
  work=$(mktemp -d)
  kept=0
  for deb in "$1"/*.deb; do
    name=${deb##*/}
    rm -rf "${work:?}"/*
    curl -fsSL --retry 3 -o "$work/old.deb" "$MESALE_PUBLISHED/$name" || continue
    unpack "$deb" "$work/new"
    unpack "$work/old.deb" "$work/old"
    if diff -rq "$work/new" "$work/old" >/dev/null && cmp -s "$work/new.modes" "$work/old.modes"; then
      cp "$work/old.deb" "$deb"
      kept=$((kept + 1))
    else
      echo "Changed: ${name%_all.deb}"
    fi
  done
  rm -rf "$work"
  echo "Unchanged packages kept at their published version: $kept"
  (
    cd "$1"
    rm -f Packages Packages.gz Release
    apt-ftparchive packages . >Packages
    gzip -nk Packages
    apt-ftparchive release -o APT::FTPArchive::Release::Origin=Mesale \
      -o APT::FTPArchive::Release::Label=Mesale -o APT::FTPArchive::Release::Suite=stable . >Release
  )
fi

gpg --batch --quiet --import <<<"$APT_SIGNING_KEY"
gpg --batch --yes --clearsign -o "$1/InRelease" "$1/Release"
gpg --batch --yes --armor --detach-sign -o "$1/Release.gpg" "$1/Release"

# A page for people who open the address in a browser
{
  cat <<'EOF'
<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mesale OS packages</title><link rel="icon" href="../img/mesale-logo.svg"><link rel="stylesheet" href="../style.css">
<main class="wrap"><section><h1>Packages</h1>
<p>Installed systems update from here by themselves. The index is signed with the Mesale OS archive key.</p><ul>
EOF
  for deb in "$1"/*.deb; do
    name=${deb##*/}
    version=$(awk -v p="${name%_all.deb}" '/^Package: /{found = $2 == p} found && /^Version: /{print $2; exit}' "$1/Packages")
    printf '<li><a href="%s">%s</a> %s</li>\n' "$name" "${name%_all.deb}" "$version"
  done
  echo '</ul><p><a href="../">Mesale OS</a></p></section></main></html>'
} >"$1/index.html"
