#!/usr/bin/env bash
# One-time setup by the maintainer: nix run .#create-signing-key
# Creates the archive key, stores the private half only in the APT_SIGNING_KEY secret
# of the GitHub repository, and writes the public half to vendor/. Keeps no local copy.
set -euo pipefail
PUBLIC=vendor/mesale-archive.asc
if [ -e "$PUBLIC" ]; then
  echo "$PUBLIC already exists. Installed systems trust that key; replacing it would stop their updates." >&2
  exit 1
fi
GNUPGHOME=$(mktemp -d)
export GNUPGHOME
trap 'gpgconf --kill all; rm -rf "$GNUPGHOME"' EXIT
gpg --batch --quiet --passphrase '' --quick-gen-key "Mesale OS archive signing key" rsa4096 sign never
gpg --armor --export-secret-keys | gh secret set APT_SIGNING_KEY
gpg --armor --export >"$PUBLIC"
echo "Done. Commit and push $PUBLIC."
