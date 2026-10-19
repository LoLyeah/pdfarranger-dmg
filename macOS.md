# PDF Arranger on macOS

## Download a ready-to-use app

Prebuilt `.dmg` and `.zip` (Apple Silicon, macOS 15+, self-contained, no
Homebrew/Nix needed) are published on the
[releases page](https://github.com/LoLyeah/pdfarranger-dmg/releases) of this
fork. Open the dmg, drag *PDF Arranger* to Applications, and right-click →
*Open* the first time (the build is not notarized by Apple).

The build is done by GitHub Actions — see
[packaging/macos](packaging/macos) for how it works.

## Run with Nix  

To use pdfarranger on macOS, is suggested to use [Nix](https://nixos.org/), which already provides [pdfarranger package](https://github.com/NixOS/nixpkgs/blob/master/pkgs/by-name/pd/pdfarranger/package.nix). 

### Install Nix on macOS

If this is your first time using Nix on macOS, it's recommended to use [Determinate Nix Installer](https://github.com/DeterminateSystems/nix-installer). Just type this one-liner command in terminal:  
```
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
```

Instead of [Determinate Nix Installer](https://github.com/DeterminateSystems/nix-installer), you can also use [Official Nix Installer](https://nixos.org/download/#nix-install-macos):  
```
sh <(curl -L https://nixos.org/nix/install)
```

### Run pdfarranger Ad hoc
After installation, run `nix-shell -p pdfarranger --run pdfarranger` in terminal to launch pdfarranger. Nix will download pdfarranger and its dependencies to `/nix`.

### Add pdfarranger to Applications
You may consider set up [nix-darwin](https://github.com/LnL7/nix-darwin).

## Run pdfarranger manually
If you want to run pdfarranger without nix, you can install dependencies manually ([Homebrew](https://brew.sh/) / [MacPort](https://www.macports.org/) / etc.). 

You'll need
1. [GTK3](https://docs.gtk.org/gtk3/)  
2. [gettext](https://www.gnu.org/software/gettext/)  


After installation, set two environment variables:  
1. `GSETTINGS_SCHEMA_DIR`:  The file `$GSETTINGS_SCHEMA_DIR/org.gtk.Settings.FileChooser.gschema.xml` should exist.  
2. `DYLD_LIBRARY_PATH`: The file `$DYLD_LIBRARY_PATH/libintl.8.dylib` should exist.  

Finally, you can run
```
./setup.py build
python3 -m pdfarranger
```

