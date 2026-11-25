<img src="https://mesflit.github.io/mesaleos/img/mesale-logo.svg" width="88" align="right" alt="">

# Mesale OS

A Linux desktop you assemble yourself: a Debian base with the newest kernel, drivers and GNOME.

**Website:** https://mesflit.github.io/mesaleos  ·  **Builds:** [Releases](https://github.com/mesflit/mesaleos/releases)

> In development. GNOME and the libraries it needs come from Debian testing. Try it in a virtual machine first.

| Part | Source |
|---|---|
| Base system | Debian 13 (trixie) |
| Kernel, Mesa, firmware | trixie-backports |
| GNOME 51 and its dependencies | Debian testing, pinned per source package |
| NVIDIA driver | NVIDIA's Debian repository, only if you select it |
| Installer | Calamares, starts by itself in the live session |

## Try it

```sh
git clone https://github.com/mesflit/mesaleos && cd mesaleos
nix run
```


| Command | What it does |
|---|---|
| `nix run` | Download the latest ISO and boot it in a VM |
| `nix run . -- bios` | Same, with legacy BIOS |
| `nix run . -- disk` | Boot the disk you installed to |
| `nix run . -- reset` | Delete the virtual disk |
| `nix flake check` | Run every check |
| `nix build .#debs` | Build the packages |
| `nix build .#artwork` | Generate wallpapers and logos |
| `nix build .#website` | Build the website |
| `nix run .#build` | Build the ISO locally (GitHub Actions normally does this) |

## Layout

| Path | Contents |
|---|---|
| `packages/` | One directory per `.deb`, laid out as installed |
| `packages/mesale-base/usr/lib/mesale/features/` | One file per installable feature |
| `artwork/` | Python that draws every image |
| `build/` | ISO build: `base`, `rootfs`, `iso` |
| `config/` | Version, package sets, ISO boot menu |
| `nix/` | Derivations and commands |
| `website/` | Website source |
| `vendor/` | Archive keys and repository definitions |

Contributors and coding agents: read [AGENTS.md](AGENTS.md).
