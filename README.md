# PDF Arranger for macOS — dmg builds

[![macOS (dmg + zip)](https://github.com/LoLyeah/pdfarranger-dmg/actions/workflows/macos-release.yml/badge.svg)](https://github.com/LoLyeah/pdfarranger-dmg/actions/workflows/macos-release.yml)

This is a **macOS packaging fork** of [PDF Arranger](https://github.com/pdfarranger/pdfarranger):
it builds a self-contained `PDF Arranger.app` (Apple Silicon), wraps it into a
`.dmg` and a `.zip`, and ships a handful of macOS fixes on top of upstream.

**It is not a general fork.** For Linux, Windows, BSD, Flathub, Snap or source
installs, use upstream — <https://github.com/pdfarranger/pdfarranger>.

![screenshot of PDF Arranger](https://github.com/pdfarranger/pdfarranger/raw/main/data/screenshot.png)

## Download

Latest release: **<https://github.com/LoLyeah/pdfarranger-dmg/releases/latest>**

| Asset | What it is |
| --- | --- |
| `pdfarranger-<version>-macos-arm64.dmg` | drag-install disk image (recommended) |
| `pdfarranger-<version>-macos-arm64.zip` | the same `.app`, zipped |
| `SHA256SUMS` | checksums (`shasum -a 256 -c SHA256SUMS`) |

Requirements: **Apple Silicon (arm64), macOS 15 (Sequoia) or newer.**
Intel Macs are not supported by these builds — current pikepdf releases have no
x86_64 macOS wheels. Intel users: run upstream via
[Nix](https://github.com/pdfarranger/pdfarranger/blob/main/macOS.md) or build
from source.

## Install

1. Open the dmg and drag **PDF Arranger** into **Applications**.
2. First start: **right-click the app → Open → Open**. The build is ad-hoc signed
   but not notarized by Apple (no Developer ID), so a plain double-click is
   refused once.
3. If macOS still complains, remove the quarantine flag:

   ```bash
   xattr -dr com.apple.quarantine "/Applications/PDF Arranger.app"
   ```

## What this fork changes

The bundle carries its own GTK3 / PyGObject / pikepdf / poppler / libhandy
runtime — no Homebrew, no Nix, nothing else to install. On top of that:

- **Dragging a page no longer deletes it.** Upstream macOS bug
  [#1334](https://github.com/pdfarranger/pdfarranger/issues/1334): GTK's quartz
  drag & drop loses the drag payload, and both of GTK's *own* drag handlers —
  the source-side `drag-data-delete` and the destination-side
  `drag-data-received` installed by `enable_model_drag_source/dest` — then act on
  a move that pdfarranger already performed. Both are now stopped on macOS and
  the drag is finished with `delete=FALSE`, so only pdfarranger's own move runs.
  Lost drops fall back to the dragged selection.
  Trade-off: dragging pages from one PDF Arranger window to another *copies*
  instead of moves on macOS (deleting the source is exactly the code path that
  loses pages there). Drag between windows is rare; losing pages is not.
- **Preferences → Theme works** (libhandy is bundled, so the libhandy header bar
  and the theme selector are available).
- **GSettings schemas + the `gsettings` CLI are inside the bundle** — no more
  "no schema files" warnings, and GTK's file-chooser settings resolve.
- Every build is stamped with its version, commit and date
  (`Contents/Resources/build-info.txt`).

Versioning: the release version is the app version, and it tracks upstream plus
the macOS fixes (`1.14.1` = upstream `1.14.0` + the fixes above).

## Build it yourself

```bash
git clone https://github.com/LoLyeah/pdfarranger-dmg.git
cd pdfarranger-dmg

brew install pkgconf gtk+3 poppler gobject-introspection gettext \
             adwaita-icon-theme librsvg libhandy

bash packaging/macos/build_app.sh
# -> release/pdfarranger-<version>-macos-arm64.dmg
# -> release/pdfarranger-<version>-macos-arm64.zip
```

Pushing a `v*` tag makes CI build, verify and publish both assets
([workflow](.github/workflows/macos-release.yml)); running the workflow manually
produces the artifacts without a release. How the bundle is assembled (and what
it checks) is described in [packaging/macos/README.md](packaging/macos/README.md).

## Everything else lives upstream

- **Linux / BSD / Windows / Flathub / Snap / source installs:**
  <https://github.com/pdfarranger/pdfarranger>
- Windows installers and portable zip:
  <https://github.com/pdfarranger/pdfarranger/releases>
- User manual: <https://github.com/pdfarranger/pdfarranger/wiki/User-Manual>
- Running from source on macOS (Nix / manual GTK setup): [macOS.md](macOS.md)

Issues: bundle/packaging problems belong in this repository; bugs in the
application itself belong upstream (please mention that it came from the macOS
dmg build).

## License

GNU GPL-3.0, same as upstream. PDF Arranger is a fork of Konstantinos Poulios'
PDF-Shuffler, maintained by the PDF Arranger contributors. These macOS builds are
unofficial and not affiliated with Apple or the upstream maintainers.
