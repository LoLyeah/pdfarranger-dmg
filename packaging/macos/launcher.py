#!/usr/bin/env python3
"""Frozen-app entry point for the macOS bundle.

PyInstaller needs a plain top-level script as its entry point (a package
``__main__.py`` would break the relative imports).
"""

from pdfarranger.pdfarranger import main

main()
