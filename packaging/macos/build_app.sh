#!/usr/bin/env bash
#
# Build "PDF Arranger.app" for macOS and wrap it into a .dmg and a .zip.
#
# Run from anywhere; it builds inside the checked out repository:
#
#     bash packaging/macos/build_app.sh
#
# Environment (all optional):
#   BREW_PREFIX   Homebrew prefix     (default: `brew --prefix`)
#   ARCH          artifact suffix     (default: build machine arch)
#   SMOKE_STRICT  fail the build when the frozen app does not start (default: 1)
#
# Requirements on the build machine: Homebrew packages gtk+3, poppler,
# gobject-introspection, gettext, adwaita-icon-theme, librsvg, pkgconf
# (see packaging/macos/README.md).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

BREW_PREFIX="${BREW_PREFIX:-$(brew --prefix)}"
export BREW_PREFIX
ARCH="${ARCH:-$(uname -m)}"
SMOKE_STRICT="${SMOKE_STRICT:-1}"
PYTHON="${PYTHON:-python3}"

# PyInstaller resolves the libraries of every GIRepository module (Gtk, Poppler,
# ...) in a child process; without these the Homebrew libraries are not found
# and the modules end up without their shared libraries inside the bundle.
export DYLD_LIBRARY_PATH="$BREW_PREFIX/lib${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
export GI_TYPELIB_PATH="$BREW_PREFIX/lib/girepository-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"

APP_NAME="PDF Arranger"
BUNDLE_ID="com.github.jeromerobert.pdfarranger"
APP="dist/${APP_NAME}.app"
DIST_RELEASE="release"

VERSION="$("$PYTHON" -c "
import re, pathlib
src = pathlib.Path('pdfarranger/pdfarranger.py').read_text(encoding='utf-8')
print(re.search(r\"^VERSION = '([^']+)'\", src, re.M).group(1))
")"

DMG="${DIST_RELEASE}/pdfarranger-${VERSION}-macos-${ARCH}.dmg"
ZIP="${DIST_RELEASE}/pdfarranger-${VERSION}-macos-${ARCH}.zip"

step "Build info"
echo "repo         : $ROOT"
echo "version      : $VERSION"
echo "arch         : $ARCH"
echo "brew prefix  : $BREW_PREFIX"
echo "python       : $($PYTHON -V) ($(command -v "$PYTHON"))"

step "Diagnostics: GTK stack"
echo "gtk3 libs    : $(ls "$BREW_PREFIX"/lib/libgtk-3*.dylib 2>/dev/null | tr '\n' ' ')"
echo "typelibs     : $(ls "$BREW_PREFIX"/lib/girepository-1.0/ 2>/dev/null | grep -c . ) files"
ls "$BREW_PREFIX"/lib/girepository-1.0/{Gtk-3.0,Gdk-3.0,GdkPixbuf-2.0,Poppler-0.18,Pango-1.0}.typelib 2>/dev/null || true
echo "gir files    : $(ls "$BREW_PREFIX"/share/gir-1.0/{Gtk-3.0,Poppler-0.18}.gir 2>/dev/null | tr '\n' ' ')"
echo "gtk modules  :"
ls -d "$BREW_PREFIX"/lib/gtk-3.0/3.0.0/*/ 2>/dev/null || echo "  (none)"
echo "schemas      : $(ls "$BREW_PREFIX"/share/glib-2.0/schemas/gschemas.compiled 2>/dev/null || echo MISSING)"
echo "icon themes  : $(ls -d "$BREW_PREFIX"/share/icons/{Adwaita,hicolor} 2>/dev/null | tr '\n' ' ')"
echo "fonts.conf   : $(ls "$BREW_PREFIX"/etc/fonts/fonts.conf 2>/dev/null || echo MISSING)"
echo "pc files     : $(ls "$BREW_PREFIX"/lib/pkgconfig/{gobject-introspection-1.0,girepository-2.0,gtk+-3.0,poppler-glib}.pc 2>/dev/null | tr '\n' ' ')"

step "Clean previous build"
rm -rf build/mo build/macos build/pyinstaller dist "$DIST_RELEASE"
mkdir -p build/mo build/macos "$DIST_RELEASE"

step "Install build dependencies (pip)"
export PKG_CONFIG_PATH="$BREW_PREFIX/lib/pkgconfig:$BREW_PREFIX/share/pkgconfig:$BREW_PREFIX/opt/libffi/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
"$PYTHON" -m pip install --upgrade pip setuptools wheel
# pikepdf ships the qpdf library inside the wheel, no separate build needed.
"$PYTHON" -m pip install \
    "pikepdf>=6" "python-dateutil>=2.4.0" packaging "img2pdf>=0.3.4" \
    "PyGObject>=3.46" "pyinstaller>=6.0"

step "Build translations (gettext .mo files)"
for po in po/*.po; do
    lang="$(basename "$po" .po)"
    mkdir -p "build/mo/$lang/LC_MESSAGES"
    msgfmt "$po" -o "build/mo/$lang/LC_MESSAGES/pdfarranger.mo"
done
echo "locales built: $(find build/mo -name '*.mo' | wc -l | tr -d ' ')"

step "Build application icon (.icns)"
ICON_SVG="data/icons/hicolor/scalable/apps/${BUNDLE_ID}.svg"
ICONSET="build/macos/pdfarranger.iconset"
mkdir -p "$ICONSET"
for spec in "16 16x16" "32 16x16@2x" "32 32x32" "64 32x32@2x" "128 128x128" "256 128x128@2x" \
            "256 256x256" "512 256x256@2x" "512 512x512" "1024 512x512@2x"; do
    size="${spec%% *}"
    name="${spec##* }"
    rsvg-convert -w "$size" -h "$size" "$ICON_SVG" -o "$ICONSET/icon_${name}.png"
done
iconutil -c icns "$ICONSET" -o build/macos/pdfarranger.icns

step "Run PyInstaller"
"$PYTHON" -m PyInstaller --noconfirm --clean \
    --distpath dist --workpath build/pyinstaller \
    packaging/macos/pdfarranger-macos.spec

test -d "$APP" || { echo "ERROR: $APP was not created"; exit 1; }
rm -rf dist/pdfarranger   # plain COLLECT dir, only the .app is shipped

step "Post-process the bundle"
# pdfarranger looks for its data relative to the executable:
#   <exe dir>/share/pdfarranger/*.ui  and  <exe dir>/share/locale/
# PyInstaller puts data files into Contents/Frameworks, so copy the two
# directories where the application expects them.
mkdir -p "$APP/Contents/MacOS/share"
if [ -d "$APP/Contents/Frameworks/share/pdfarranger" ]; then
    ditto "$APP/Contents/Frameworks/share/pdfarranger" "$APP/Contents/MacOS/share/pdfarranger"
fi
if [ -d "$APP/Contents/Frameworks/share/locale" ]; then
    ditto "$APP/Contents/Frameworks/share/locale" "$APP/Contents/MacOS/share/locale"
fi
ls -la "$APP/Contents/MacOS/share/"

# pdfarranger loads libintl through ctypes by its bare file name on macOS;
# a link next to the executable puts it on the loader's search path.
if [ -f "$APP/Contents/Frameworks/libintl.8.dylib" ]; then
    ln -sf ../Frameworks/libintl.8.dylib "$APP/Contents/MacOS/libintl.8.dylib"
fi

step "Verify bundle layout and library references"
"$PYTHON" packaging/macos/verify_bundle.py "$APP"

step "Checks: no leftover Homebrew references in the main binary"
if otool -L "$APP/Contents/MacOS/pdfarranger" | grep -F "$BREW_PREFIX"; then
    echo "ERROR: the main executable still links against $BREW_PREFIX"
    exit 1
fi
if otool -L "$APP/Contents/MacOS/pdfarranger" | grep -E '^\s+/opt/|^\s+/usr/local/' | grep -v "^$BREW_PREFIX"; then
    echo "WARNING: unexpected absolute library references above"
fi

step "Check: minimum macOS version used by the bundled binaries"
find "$APP/Contents" -type f \( -name '*.dylib' -o -name '*.so' -o -name 'pdfarranger' \) -print0 \
    | xargs -0 -I{} sh -c 'otool -l "{}" 2>/dev/null | awk "/LC_BUILD_VERSION/{b=1} b&&/minos/{print \$2; exit}"' \
    | sort -V | uniq -c || true

step "Ad-hoc code signature (required to run on Apple Silicon)"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --verbose=2 "$APP"

step "Strip extended attributes (keeps AppleDouble files out of the artifacts)"
xattr -cr "$APP" || true

step "Smoke test: run the frozen app"
APP_BIN="$APP/Contents/MacOS/pdfarranger"
SMOKE_OUT="$(mktemp)"
set +e
env -u DYLD_LIBRARY_PATH -u GI_TYPELIB_PATH -u GSETTINGS_SCHEMA_DIR -u GTK_PATH -u XDG_DATA_DIRS \
    "$APP_BIN" --version >"$SMOKE_OUT" 2>&1
SMOKE_RC=$?
set -e
echo "exit code: $SMOKE_RC"
cat "$SMOKE_OUT"
if [ "$SMOKE_RC" -ne 0 ]; then
    if [ "$SMOKE_STRICT" = "1" ]; then
        echo "ERROR: the frozen app failed to start"
        exit 1
    else
        echo "WARNING: the frozen app failed to start"
    fi
fi
rm -f "$SMOKE_OUT"

step "Smoke test: open the application window"
# Launches the real app for 10 s. A CI runner may not have a desktop session,
# so a failure here is reported but does not fail the build.
GUI_LOG="$(mktemp)"
env -u DYLD_LIBRARY_PATH -u GI_TYPELIB_PATH -u GSETTINGS_SCHEMA_DIR -u GTK_PATH -u XDG_DATA_DIRS \
    "$APP_BIN" >"$GUI_LOG" 2>&1 &
GUI_PID=$!
sleep 10
if kill -0 "$GUI_PID" 2>/dev/null; then
    echo "app still running after 10s (pid $GUI_PID) - window created"
    kill "$GUI_PID" 2>/dev/null || true
    wait "$GUI_PID" 2>/dev/null || true
else
    echo "WARNING: the app exited within 10s (no desktop session on this runner?)"
fi
echo "--- application output ---"
cat "$GUI_LOG"
rm -f "$GUI_LOG"

step "Create dmg"
STAGE="build/macos/dmg"
rm -rf "$STAGE"
mkdir -p "$STAGE"
ditto --norsrc --noextattr "$APP" "$STAGE/${APP_NAME}.app"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "${APP_NAME} ${VERSION}" -srcfolder "$STAGE" \
    -ov -format UDZO "$DMG"

step "Create zip"
ditto -c -k --keepParent --norsrc --noextattr "$APP" "$ZIP"

step "Verify the dmg end-to-end"
MOUNT_POINT="$(mktemp -d)"
hdiutil attach "$DMG" -mountpoint "$MOUNT_POINT" -nobrowse -quiet
codesign --verify --deep --strict "$MOUNT_POINT/${APP_NAME}.app"
test -x "$MOUNT_POINT/${APP_NAME}.app/Contents/MacOS/pdfarranger"
if find "$MOUNT_POINT" -name '._*' | grep -q .; then
    echo "ERROR: AppleDouble files inside the dmg"
    find "$MOUNT_POINT" -name '._*' | head -10
    hdiutil detach "$MOUNT_POINT" -quiet || hdiutil detach "$MOUNT_POINT" -force -quiet
    exit 1
fi
"$MOUNT_POINT/${APP_NAME}.app/Contents/MacOS/pdfarranger" --version | head -3
hdiutil detach "$MOUNT_POINT" -quiet || hdiutil detach "$MOUNT_POINT" -force -quiet
rmdir "$MOUNT_POINT"
echo "dmg mounted, app inside is signed and starts"

step "Checksums and result"
( cd "$DIST_RELEASE" && shasum -a 256 ./*.dmg ./*.zip > SHA256SUMS && cat SHA256SUMS )
ls -lh "$DIST_RELEASE"

step "Done: $VERSION ($ARCH)"
