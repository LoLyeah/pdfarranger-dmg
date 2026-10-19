#!/usr/bin/env python3
"""Verify a built macOS .app bundle.

Run as:  python3 packaging/macos/verify_bundle.py "dist/PDF Arranger.app"

Fails (exit 1) when

* a bundled Mach-O file still links against an absolute path outside the
  bundle (e.g. /opt/homebrew/...) - that library would be missing on the
  user's Mac,
* a typelib of a GIRepository module we need is missing,
* a required runtime data file (schemas, icon theme, gdk-pixbuf loaders,
  application data) is missing.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

SYSTEM_PREFIXES = ("/usr/lib/", "/System/", "/Library/Apple/")
REQUIRED_TYPELIBS = (
    "Gtk-3.0",
    "Gdk-3.0",
    "GdkPixbuf-2.0",
    "Pango-1.0",
    "Poppler-0.18",
)
REQUIRED_FILES = (
    "Contents/Frameworks/libgtk-3.0.dylib",
    "Contents/Frameworks/gi_typelibs/Poppler-0.18.typelib",
    "Contents/MacOS/share/pdfarranger/pdfarranger.ui",
    "Contents/MacOS/share/pdfarranger/menu.ui",
)


def mach_o_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix in (".dylib", ".so", ".bundle") or os.access(path, os.X_OK):
            yield path


def dependencies(path: Path):
    result = subprocess.run(
        ["otool", "-L", str(path)], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return []
    deps = []
    for line in result.stdout.splitlines()[1:]:
        line = line.strip()
        if line:
            deps.append(re.split(r"\s+\(", line)[0])
    return deps


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    app = Path(sys.argv[1]).resolve()
    problems = []
    linked = 0

    for binary in mach_o_files(app / "Contents"):
        for dep in dependencies(binary):
            if dep == str(binary) or dep.startswith("@rpath/"):
                continue
            linked += 1
            if dep.startswith("/") and not dep.startswith(SYSTEM_PREFIXES):
                problems.append(f"{binary.relative_to(app)} links against {dep}")
            elif dep.startswith("@"):
                continue
            elif "/" not in dep:
                problems.append(f"{binary.relative_to(app)} links against bare name {dep}")

    for typelib in REQUIRED_TYPELIBS:
        if not (app / "Contents/Frameworks/gi_typelibs" / f"{typelib}.typelib").is_file():
            problems.append(f"missing typelib {typelib}")

    for filename in REQUIRED_FILES:
        if not (app / filename).exists():
            problems.append(f"missing file {filename}")

    if not list((app / "Contents/MacOS/share/locale").glob("*/LC_MESSAGES/pdfarranger.mo")):
        problems.append("missing translations in Contents/MacOS/share/locale")

    # Contents/MacOS must contain code only (data files there break
    # codesign --verify --deep --strict).
    for entry in (app / "Contents" / "MacOS").iterdir():
        if entry.is_symlink() or entry.name == "pdfarranger":
            continue
        problems.append(f"unexpected file in Contents/MacOS: {entry.name}")

    for typelib in (app / "Contents/Frameworks/gi_typelibs").glob("*.typelib"):
        data = typelib.read_bytes()
        match = re.search(rb"(/opt/homebrew[^\x00]*|/usr/local/Cellar[^\x00]*)", data)
        if match:
            problems.append(
                f"typelib {typelib.name} still references {match.group(1).decode()}"
            )

    print(f"checked {linked} library references in the bundle")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("bundle layout OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
