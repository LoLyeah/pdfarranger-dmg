#!/usr/bin/env bash
#
# Functional smoke test: open a generated 3 page PDF in the built app, keep it
# running for a few seconds, capture the application's output and a screenshot
# of the screen. Used by build_app.sh for diagnosis; never fails the build.
#
#     bash packaging/macos/smoke_app.sh "dist/PDF Arranger.app" build/smoke

set -uo pipefail

APP="${1:?usage: smoke_app.sh <app bundle> <output dir>}"
OUT="${2:-build/smoke}"
mkdir -p "$OUT"

PYTHON="${PYTHON:-python3}"

echo "== smoke: generating test document =="
"$PYTHON" - "$OUT/test.pdf" <<'PYEOF'
import sys
from PIL import Image, ImageDraw
import img2pdf

identify = sys.argv[1]
pages = []
for number in (1, 2, 3):
    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([60, 60, 1180, 320], outline="black", width=8)
    draw.rectangle([60, 420, 600, 900], fill="black")
    draw.rectangle([660, 420, 1180, 900], outline="black", width=8)
    for line in range(1100, 1600, 100):
        draw.line([60, line, 1180, line], fill="black", width=6)
    draw.text((90, 120), f"PDF Arranger smoke test - page {number}", fill="black")
    path = f"/tmp/pdfarranger-smoke-{number}.png"
    image.save(path)
    pages.append(path)

with open(identify, "wb") as handle:
    handle.write(img2pdf.convert(pages))
print("test.pdf written:", identify)
PYEOF

echo "== smoke: seeding the config (skip the content-loss note dialog) =="
CONFIG_DIR="$HOME/Library/Preferences/pdfarranger"
mkdir -p "$CONFIG_DIR"
printf '%s\n' "[preferences]" "content-loss-warning = false" > "$CONFIG_DIR/config.ini"
cat "$CONFIG_DIR/config.ini"

echo "== smoke: launching the app with the test document =="
env -u DYLD_LIBRARY_PATH -u GI_TYPELIB_PATH -u GSETTINGS_SCHEMA_DIR -u GTK_PATH -u XDG_DATA_DIRS \
    PDFARRANGER_MACOS_DIAG=1 PDFARRANGER_MACOS_DROP_SELFTEST=1 \
    "$APP/Contents/MacOS/pdfarranger" "$OUT/test.pdf" >"$OUT/app-output.log" 2>&1 &
APP_PID=$!
sleep 25

if kill -0 "$APP_PID" 2>/dev/null; then
    echo "app still running after 15s"
else
    echo "WARNING: app exited before the screenshot"
fi

echo "== smoke: capturing the screen =="
screencapture -x "$OUT/screen.png" >"$OUT/screencapture.log" 2>&1
if [ -f "$OUT/screen.png" ]; then
    ls -lh "$OUT/screen.png"
else
    echo "WARNING: no screenshot taken:"
    cat "$OUT/screencapture.log"
fi

kill "$APP_PID" 2>/dev/null
sleep 2
kill -9 "$APP_PID" 2>/dev/null

echo "== smoke: application output ($OUT/app-output.log) =="
cat "$OUT/app-output.log"
echo "== smoke: warnings/errors =="
grep -nE "Traceback|Error|ERROR|WARNING|CRITICAL|Gtk-WARNING|glib" "$OUT/app-output.log" | head -40 \
    || echo "none"

echo "== smoke: bundled gsettings sees the schemas =="
GSL=""
for candidate in "$APP/Contents/Frameworks/gsettings" "$APP/Contents/Resources/gsettings"; do
    [ -x "$candidate" ] && GSL="$candidate" && break
done
if [ -n "$GSL" ]; then
    GSETTINGS_SCHEMA_DIR="$APP/Contents/Resources/share/glib-2.0/schemas" \
        "$GSL" list-recursively 2>&1 | grep -c . | sed 's/^/settings entries: /'
    GSETTINGS_SCHEMA_DIR="$APP/Contents/Resources/share/glib-2.0/schemas" \
        "$GSL" list-recursively 2>&1 | grep -m2 "org.gtk.Settings.ColorChooser" \
        || echo "WARNING: org.gtk.Settings.ColorChooser schema missing"
else
    echo "WARNING: gsettings not bundled"
fi

if grep -q "Found no schema files\|gsettings failed" "$OUT/app-output.log"; then
    echo "WARNING: the app could not verify the GSettings schemas"
fi
