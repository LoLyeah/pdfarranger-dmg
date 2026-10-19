"""PyInstaller runtime hook for the macOS app bundle.

Runs before the application code and points the GTK stack at the copy of the
runtime data (schemas, icon themes, fontconfig config, GTK modules) that ships
inside the bundle instead of the Homebrew prefix it was built against.
"""

import os
import sys


def _prepend(name, value, sep=os.pathsep):
    current = os.environ.get(name)
    if current:
        os.environ[name] = value + sep + current
    else:
        os.environ[name] = value


def _setup():
    meipass = sys._MEIPASS
    share = os.path.join(meipass, 'share')

    # GSettings schemas (org.gtk.Settings.* is needed by GtkFileChooser, the
    # color chooser and friends).
    os.environ['GSETTINGS_SCHEMA_DIR'] = os.path.join(share, 'glib-2.0', 'schemas')

    # Icon themes (Adwaita) and the other XDG data shipped in the bundle.
    _prepend('XDG_DATA_DIRS', share)

    # fontconfig configuration for pango.
    fonts = os.path.join(meipass, 'etc', 'fonts')
    if os.path.isdir(fonts):
        os.environ['FONTCONFIG_PATH'] = fonts
        os.environ['FONTCONFIG_FILE'] = os.path.join(fonts, 'fonts.conf')

    # GTK3 modules (print backends, input methods) copied into the bundle.
    os.environ['GTK_PATH'] = meipass
    os.environ['GTK_EXE_PREFIX'] = meipass
    os.environ['GTK_DATA_PREFIX'] = meipass

    # Help dlopen() find the bundled shared libraries. pdfarranger loads
    # libintl.8.dylib through ctypes on macOS.
    _prepend('DYLD_LIBRARY_PATH', os.path.join(meipass, 'lib'))
    _prepend('DYLD_LIBRARY_PATH', meipass)


_setup()
del _setup
