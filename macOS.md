# PDF Arranger on macOS

Ready-made Apple Silicon builds (dmg/zip, self-contained, nothing to install) are
published on the [releases page](https://github.com/LoLyeah/pdfarranger-dmg/releases) —
see the [README](README.md). Everything below is for running pdfarranger from
source, which is also how you run it on Intel Macs.

## Run with Nix

Nix provides a `pdfarranger` package and works on Apple Silicon and Intel.

Install Nix (Determinate installer):

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
```

Run it ad hoc — Nix downloads pdfarranger and its dependencies into `/nix`:

```bash
nix-shell -p pdfarranger --run pdfarranger
```

For a permanent entry in Applications, set up
[nix-darwin](https://github.com/LnL7/nix-darwin).

## Run from source

Dependencies: GTK3, PyGObject, poppler and gettext. With Homebrew:

```bash
brew install pygobject3 gtk+3 poppler gettext
python3 -m pip install --user pikepdf python-dateutil img2pdf packaging
```

pdfarranger needs two environment variables on macOS:

```bash
export GSETTINGS_SCHEMA_DIR="$(brew --prefix)/share/glib-2.0/schemas"  # org.gtk.Settings.FileChooser.gschema.xml
export DYLD_LIBRARY_PATH="$(brew --prefix gettext)/lib"                # libintl.8.dylib
```

Then:

```bash
./setup.py build
python3 -m pdfarranger
```
