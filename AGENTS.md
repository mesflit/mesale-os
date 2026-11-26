# Working on Mesale OS

Rules for people and coding agents.

## Principles

- Everything is in English: code, comments, file names, commits, user interface.
- Everything runs through Nix. Do not add a tool that is not in `nix/`.
- Do not build ISOs locally. Push to `main`; GitHub Actions builds and publishes the `dev` release. Test it with `nix run`.
- The user chooses. Never preselect or bundle an extra package. One feature installs one thing.
- Do not add user-facing commands when Mesale Center or `mesale-feature` can do the job.
- Keep the look its own: clouds, sky colors, real blur, one floating bottom bar. Never copy another system's names, art or layout.
- Never commit personal data, tokens or home directory paths.

## Where things go

| You want to | Edit |
|---|---|
| Add or change a feature | `packages/mesale-base/usr/lib/mesale/features/<name>` |
| Add a wallpaper | `artwork/looks.py` and `packages/mesale-live/etc/calamares/modules/packagechooser_look.conf` |
| Change desktop defaults | `packages/mesale-desktop/etc/dconf/db/local.d/00-mesale` |
| Change the command bar | `packages/mesale-desktop/usr/share/gnome-shell/extensions/mesale-shell@mesale/` |
| Change Mesale Center | `packages/mesale-desktop/usr/lib/mesale/center/` |
| Change the installer | `packages/mesale-live/etc/calamares/` and `usr/lib/calamares/modules/mesale/` |
| Change what is on the ISO | `config/packages.sh` |
| Bump the version | `config/mesale.conf` (each release is named after a celestial body) |

## Feature files

Shell fragments read by `mesale-feature`, the installer, Mesale Center and the website.

```sh
GROUP=gaming             # apps system drivers terminal gaming development more
NAME="Steam"
DESC="One short line"
NET=1                    # needs a network
PKGS="steam-devices"     # Debian packages
FLATPAKS="com.valvesoftware.Steam"
BIN=steam                # optional: command that proves it is installed
prepare() { ...; }       # optional: before apt
after() { ...; }         # optional: after apt
```

`GROUP=apps` means preinstalled on the ISO and removed when unchecked. `GROUP=system` must install offline: list its dependencies in `OFFLINE_FEATURES`.

## Updates

Every push that touches `packages/` publishes a signed apt repository at `https://mesflit.github.io/mesaleos/apt/`. Installed systems get it through `mesale.sources`. Versions come from the commit date, so they always increase.

The maintainer creates the key once with `nix run .#create-signing-key`. The private key lives only in the `APT_SIGNING_KEY` secret. Do not delete that secret: installed systems would stop getting updates. Never commit it, and never create or replace it without being asked. Without a key, builds work and simply have no update source.

## Things that break easily

- `GRUB_DISTRIBUTOR` must start with `debian` and `efiBootloaderId` must be `debian`. The signed GRUB only looks in `/EFI/debian`.
- Packages from testing are pinned by source at build time (`build/forky_pins.py`). Python modules follow the same pin.
- GNOME Shell APIs change every release. Check the running version's JavaScript before using one.
- Blur My Shell: keep `settings-version` at the extension's current value, or its migration crashes on our custom pipeline.
- Dash to Panel: monitor settings are keyed `"0"` to `"3"` in JSON strings.
- In the installer's chroot `/run` is empty, so DNS is copied in and Flatpaks are queued for first boot.
- Calamares base strings must be ASCII.

## Before pushing

```sh
nix flake check
```

Then, in a VM: the installer opens by itself, `Super+Space` works, menus are blurred, an installation boots from disk, and `systemctl --failed` is empty.
