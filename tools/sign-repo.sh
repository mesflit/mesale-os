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
