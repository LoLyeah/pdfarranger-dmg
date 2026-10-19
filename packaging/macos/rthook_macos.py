"""PyInstaller runtime hook for the macOS app bundle.

Runs before the application code and points the GTK stack at the copy of the
runtime data (schemas, icon themes, fontconfig config, GTK modules) that ships
inside the bundle instead of the Homebrew prefix it was built against.
"""

import ctypes
import os
import sys
from pathlib import Path


def _prepend(name, value, sep=os.pathsep):
    current = os.environ.get(name)
    if current:
        os.environ[name] = value + sep + current
    else:
        os.environ[name] = value


def _runtime_dir():
    """Return the directory that holds the bundled data (share/, etc/)."""
    candidates = [
        Path(sys._MEIPASS),
        Path(sys.executable).resolve().parent.parent / "Resources",
    ]
    for candidate in candidates:
        if (candidate / "share").is_dir():
            return candidate
    return candidates[0]


def _setup():
    runtime = _runtime_dir()
    share = str(runtime / "share")

    # GSettings schemas (org.gtk.Settings.* is needed by GtkFileChooser, the
    # color chooser and friends).
    os.environ['GSETTINGS_SCHEMA_DIR'] = os.path.join(share, 'glib-2.0', 'schemas')

    # Icon themes (Adwaita) and the other XDG data shipped in the bundle.
    _prepend('XDG_DATA_DIRS', share)

    # fontconfig configuration for pango.
    fonts = runtime / 'etc' / 'fonts'
    if fonts.is_dir():
        os.environ['FONTCONFIG_PATH'] = str(fonts)
        os.environ['FONTCONFIG_FILE'] = str(fonts / 'fonts.conf')

    # GTK3 modules (print backends, input methods) copied into the bundle.
    os.environ['GTK_PATH'] = str(runtime)
    os.environ['GTK_EXE_PREFIX'] = str(runtime)
    os.environ['GTK_DATA_PREFIX'] = str(runtime)

    # Help dlopen() find the bundled shared libraries.
    _prepend('DYLD_LIBRARY_PATH', os.path.join(str(runtime), 'lib'))
    _prepend('DYLD_LIBRARY_PATH', str(runtime))

    # Helper executables shipped in the bundle (gsettings, which pdfarranger
    # probes at startup to check that the schemas are reachable).
    _prepend('PATH', str(runtime))

    # pdfarranger loads libintl.8.dylib through ctypes by its bare file name on
    # macOS. dyld does not search the bundle for such a name, so resolve names
    # that exist inside the bundle to their bundled absolute path.
    lookup = os.path.join(str(runtime), 'lib')
    original_getitem = ctypes.LibraryLoader.__getitem__

    def _getitem(self, name):
        if "/" not in str(name) and not str(name).startswith("@"):
            for directory in (lookup, str(runtime), str(runtime / '..' / 'Frameworks')):
                candidate = os.path.join(directory, str(name))
                if os.path.exists(candidate):
                    name = candidate
                    break
        return original_getitem(self, name)

    ctypes.LibraryLoader.__getitem__ = _getitem


_setup()
del _setup
