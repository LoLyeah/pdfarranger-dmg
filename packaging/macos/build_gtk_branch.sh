#!/usr/bin/env bash
#
# Build GTK3 from the upstream gtk-3-24 branch (post-3.24.52 fixes) and install
# it over Homebrew's bottle. Used by the experimental CI build; the branch is
# not a release, so the app built against it is a test build.
#
#     bash packaging/macos/build_gtk_branch.sh

set -euo pipefail

BRANCH="${GTK_BRANCH:-gtk-3-24}"
TARBALL="https://github.com/GNOME/gtk/archive/refs/heads/${BRANCH}.tar.gz"
TMP="$(mktemp -d)"

echo "=== downloading GTK branch ${BRANCH} ==="
curl -sSL "$TARBALL" -o "$TMP/gtk-branch.tar.gz"
SHA="$(shasum -a 256 "$TMP/gtk-branch.tar.gz" | awk '{print $1}')"
echo "tarball sha256: $SHA"

echo "=== patching the Homebrew gtk+3 formula to build the branch ==="
brew cat gtk+3 > "$TMP/gtk+3.rb"
python3 - "$TMP/gtk+3.rb" "$TARBALL" "$SHA" <<'PY'
import re
import sys

path, url, sha = sys.argv[1:4]
src = open(path, encoding="utf-8").read()
src, n_url = re.subn(r'url "https://download\.gnome\.org[^"]+"', f'url "{url}"', src, count=1)
src, n_sha = re.subn(r'sha256 "[0-9a-f]{64}"', f'sha256 "{sha}"', src, count=1)
# a branch snapshot has no release revision
src = re.sub(r'^\s*revision \d+\n', '', src, flags=re.M)
open(path, "w", encoding="utf-8").write(src)
print(f"patched url={n_url} sha256={n_sha}")
PY
sed -n '/url "/p;/sha256 "/p' "$TMP/gtk+3.rb" | head -4

echo "=== building GTK3 from source (this takes a while) ==="
# Homebrew refuses formulae outside a tap, so stage it in a throwaway local tap
TAP="local/gtk-branch"
brew tap-new "$TAP" --no-git >/dev/null 2>&1 || true
TAP_DIR="$(brew --repository "$TAP")"
cp "$TMP/gtk+3.rb" "$TAP_DIR/Formula/gtk+3.rb"
brew uninstall --ignore-dependencies gtk+3 >/dev/null 2>&1 || true
HOMEBREW_NO_AUTO_UPDATE=1 brew install --build-from-source "$TAP/gtk+3"

echo "=== installed GTK3 ==="
pkg-config --modversion gtk+-3.0
gtk3-demo --version 2>/dev/null || true
