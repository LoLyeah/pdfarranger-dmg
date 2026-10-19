# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: build "PDF Arranger.app" for macOS.

Run through packaging/macos/build_app.sh (which prepares the translations and
the icon). Requires the Homebrew GTK3 stack, see packaging/macos/README.md.

    pyinstaller --noconfirm --clean packaging/macos/pdfarranger-macos.spec
"""

import os
import re
from pathlib import Path

from PyInstaller.utils.hooks.gi import GiModuleInfo

SPEC_DIR = Path(SPECPATH).resolve()  # noqa: F821 - provided by PyInstaller
ROOT = SPEC_DIR.parent.parent
BREW_PREFIX = Path(os.environ.get("BREW_PREFIX") or "/opt/homebrew")

APP_NAME = "PDF Arranger"
BUNDLE_ID = "com.github.jeromerobert.pdfarranger"

VERSION = re.search(
    r"^VERSION = '([^']+)'",
    (ROOT / "pdfarranger" / "pdfarranger.py").read_text(encoding="utf-8"),
    re.MULTILINE,
).group(1)

datas = []
binaries = []
hiddenimports = [
    "gi.repository.Gtk",
    "gi.repository.Gdk",
    "gi.repository.GdkPixbuf",
    "gi.repository.Gio",
    "gi.repository.GLib",
    "gi.repository.GObject",
    "gi.repository.Pango",
    "gi.repository.PangoCairo",
    "gi.repository.cairo",
    "pikepdf",
    "img2pdf",
    "dateutil",
]

# PyInstaller ships no GI hook for Poppler and does not pick
# ``gi.repository.Poppler`` up from the source (gi imports it lazily), so its
# typelib and shared libraries have to be collected explicitly.
poppler = GiModuleInfo("Poppler", "0.18")
if not poppler.available:
    raise SystemExit(
        "Poppler GIRepository module not found - install poppler (brew install poppler)"
    )
poppler_binaries, poppler_datas, poppler_hiddenimports = poppler.collect_typelib_data()
binaries += poppler_binaries
datas += poppler_datas
hiddenimports += poppler_hiddenimports


def add_tree(src, dest):
    """Add a directory tree of data files to the bundle."""
    src = Path(src)
    if not src.is_dir():
        return
    for path in sorted(src.rglob("*")):
        if path.is_file():
            datas.append((str(path), str(Path(dest) / path.parent.relative_to(src))))


# --- application files ------------------------------------------------------

datas += [
    (str(ROOT / "data" / "pdfarranger.ui"), "share/pdfarranger"),
    (str(ROOT / "data" / "menu.ui"), "share/pdfarranger"),
    (str(ROOT / "COPYING"), "share/pdfarranger"),
]
add_tree(ROOT / "data" / "icons" / "hicolor", "share/icons/hicolor")

# Translations, built by build_app.sh with msgfmt (po/*.po -> build/mo/<lang>/LC_MESSAGES)
for mo in sorted((ROOT / "build" / "mo").rglob("pdfarranger.mo")):
    dest = Path("share/locale") / mo.parent.relative_to(ROOT / "build" / "mo")
    datas.append((str(mo), str(dest)))

# --- GTK3 runtime data from Homebrew ---------------------------------------

# GSettings schemas (org.gtk.Settings.* used by GtkFileChooser, color chooser, ...).
datas.append(
    (str(BREW_PREFIX / "share" / "glib-2.0" / "schemas" / "gschemas.compiled"),
     "share/glib-2.0/schemas")
)

# Icon themes.
for theme in ("Adwaita", "hicolor"):
    add_tree(BREW_PREFIX / "share" / "icons" / theme, f"share/icons/{theme}")

# fontconfig configuration, needed by pango to find fonts.
add_tree(BREW_PREFIX / "etc" / "fonts", "etc/fonts")

# GTK3 modules: print backends and input methods are dlopen()ed at runtime,
# so PyInstaller cannot discover them on its own.
for module_dir in ("immodules", "printbackends"):
    for so in sorted((BREW_PREFIX / "lib" / "gtk-3.0" / "3.0.0" / module_dir).glob("*.so")):
        binaries.append((str(so), f"lib/gtk-3.0/3.0.0/{module_dir}"))

# pdfarranger runs `gsettings list-recursively` on macOS at startup to verify
# that the GSettings schemas are reachable. Bundle the CLI (it is a normal
# Mach-O executable, so PyInstaller rewrites its library references too) and
# put the bundle on PATH at runtime.
gsettings_bin = BREW_PREFIX / "bin" / "gsettings"
if gsettings_bin.is_file():
    binaries.append((str(gsettings_bin), "."))

# --- PyInstaller analysis ---------------------------------------------------

a = Analysis(
    [str(SPEC_DIR / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hooksconfig={
        "gi": {
            "module-versions": {
                "Gtk": "3.0",
                "Poppler": "0.18",
            },
        },
    },
    runtime_hooks=[str(SPEC_DIR / "rthook_macos.py")],
    excludes=["tkinter", "Tkinter", "unittest", "pydoc_data", "test"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)  # noqa: F821

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pdfarranger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="pdfarranger",
)

app = BUNDLE(  # noqa: F821
    coll,
    name=f"{APP_NAME}.app",
    icon=str(ROOT / "build" / "macos" / "pdfarranger.icns"),
    bundle_identifier=BUNDLE_ID,
    version=VERSION,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "LSApplicationCategoryType": "public.app-category.productivity",
        "NSHumanReadableCopyright": "GNU GPL-3.0. PDF Arranger is a fork of PDF-Shuffler.",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "PDF document",
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": ["com.adobe.pdf"],
                "CFBundleTypeExtensions": ["pdf"],
            }
        ],
    },
)
