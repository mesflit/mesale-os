#!/usr/bin/env bash
# One-time setup by the maintainer: nix run .#create-signing-key
# Creates the archive key outside the repository, stores the private half in the
# APT_SIGNING_KEY secret of the GitHub repository and the public half in vendor/.
set -euo pipefail
umask 077
export GNUPGHOME="${MESALE_SIGNING:-$HOME/.local/share/mesale-signing}"
mkdir -p "$GNUPGHOME"
if [ -n "$(gpg -K 2>/dev/null)" ]; then
  echo "Using the existing key in $GNUPGHOME"
else
  gpg --batch --passphrase '' --quick-gen-key "Mesale OS archive signing key" rsa4096 sign never
fi
gpg --armor --export-secret-keys | gh secret set APT_SIGNING_KEY
(umask 022 && gpg --armor --export >vendor/mesale-archive.asc)
echo "Done. Back up $GNUPGHOME, then commit and push vendor/mesale-archive.asc."
