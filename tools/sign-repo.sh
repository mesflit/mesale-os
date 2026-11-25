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
