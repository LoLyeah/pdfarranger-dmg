# macOS packaging

Builds **PDF Arranger.app** — a self-contained macOS application (GTK3, Python
and pikepdf all inside the bundle, nothing to install) — and wraps it into a
`.dmg` (drag & drop install) and a `.zip`.

Everything runs in GitHub Actions: [`.github/workflows/macos-release.yml`](../../.github/workflows/macos-release.yml).

- **Manual build** (artifacts only): Actions → *macOS (dmg + zip)* → *Run workflow*.
- **Release**: push a `v*` tag; the run attaches the dmg, the zip and
  `SHA256SUMS` to a GitHub release.

## How it works

| File | Purpose |
| --- | --- |
| `build_app.sh` | The whole build: translations, icon, PyInstaller, post-processing, ad-hoc signature, smoke test, dmg + zip. Run it locally with `bash packaging/macos/build_app.sh`. |
| `pdfarranger-macos.spec` | PyInstaller spec: entry point, data files, GTK3 runtime data from Homebrew, the Poppler typelib/libraries, and the `.app` bundle (Info.plist, icon). |
| `rthook_macos.py` | Runtime hook: points GTK at the schemas / icon themes / fontconfig / GTK modules inside the bundle instead of the Homebrew prefix. |
| `verify_bundle.py` | Fails the build if a bundled Mach-O links outside the bundle or a required typelib/data file is missing. |
| `launcher.py` | Plain top-level entry script for PyInstaller. |

The GTK3 libraries come from Homebrew **at build time**: PyInstaller rewrites
their install names to `@loader_path/...` and copies them into
`Contents/Frameworks`, so the resulting app does not depend on Homebrew (or
Nix, or anything else) on the user's machine.

Two directories of the bundle need care:

- `Contents/Frameworks` — libraries, typelibs, schemas, icon themes, GTK modules.
- `Contents/MacOS/share` — the application's own data, because pdfarranger looks
  for `share/pdfarranger/*.ui` and `share/locale/` next to the executable.

## Build requirements (local Mac)

```bash
brew install pkgconf gtk+3 poppler gobject-introspection gettext adwaita-icon-theme librsvg
bash packaging/macos/build_app.sh          # needs python3; pip installs the rest
```

`SMOKE_STRICT=0` lets the build continue when the frozen app cannot be started
(useful over SSH, where there is no window server).

Artifacts land in `release/`: `pdfarranger-<version>-macos-<arch>.dmg`, `.zip`
and `SHA256SUMS`.

## Not signed / not notarized

The app is ad-hoc signed (`codesign -s -`), which is the minimum for Apple
Silicon, but it is neither signed with a Developer ID nor notarized — so macOS
Gatekeeper asks the user to right-click → *Open* on first start. Notarizing
would require a paid Apple Developer account and its credentials as repository
secrets.
