#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
  echo "Build this installer on x86_64 Linux (Ubuntu 22.04 for Mint 21/22 compatibility)." >&2
  exit 1
fi

# Use the distribution Python so PyInstaller can bundle its matching Tcl/Tk libraries.
# Prerequisites: sudo apt install python3-venv python3-tk binutils
python3 -m venv .venv/linux-build
.venv/linux-build/bin/python -m pip install --upgrade pip
.venv/linux-build/bin/python -m pip install 'pyinstaller>=6.0,<7'
.venv/linux-build/bin/python -m PyInstaller --noconfirm --clean --onedir \
  --name caption-converter --paths src app.py

package_root=$(mktemp -d)
trap 'rm -rf "$package_root"' EXIT HUP INT TERM
mkdir -p "$package_root/DEBIAN" "$package_root/opt/caption-converter" \
  "$package_root/usr/bin" "$package_root/usr/share/applications"
cp -R dist/caption-converter/. "$package_root/opt/caption-converter/"
ln -s /opt/caption-converter/caption-converter "$package_root/usr/bin/caption-converter"

version=$(.venv/linux-build/bin/python -c 'import re; from pathlib import Path; print(re.search(r"^version = \"([^\"]+)\"", Path("pyproject.toml").read_text(), re.M).group(1))')
installed_size=$(du -sk "$package_root/opt" | cut -f1)
cat > "$package_root/DEBIAN/control" <<EOF
Package: caption-converter
Version: $version
Section: video
Priority: optional
Architecture: amd64
Maintainer: Brandon Falk
Installed-Size: $installed_size
Depends: libc6 (>= 2.35), libx11-6, libxext6, libxft2, libxrender1, libfontconfig1, libxss1, libexpat1, libfreetype6, zlib1g
Homepage: https://michaelbrandonfalk.github.io/Caption-Converter/
Description: Desktop subtitle converter for Linux Mint
 Convert SRT and VTT subtitle files to SRT, WebVTT, and TTML.
 Includes the Python runtime and Tcl/Tk desktop interface.
 Built for Linux Mint 21 and 22 on 64-bit PCs.
EOF

cat > "$package_root/usr/share/applications/caption-converter.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Caption Converter
Comment=Convert subtitle files to SRT, WebVTT, and TTML
Exec=/opt/caption-converter/caption-converter --gui
Icon=video-x-generic
Terminal=false
Categories=AudioVideo;Utility;
StartupNotify=true
EOF

chmod 755 "$package_root" "$package_root/DEBIAN"
chmod 644 "$package_root/DEBIAN/control" "$package_root/usr/share/applications/caption-converter.desktop"
dpkg-deb --build --root-owner-group "$package_root" dist/Caption-Converter-linux-mint-amd64.deb
echo "Created dist/Caption-Converter-linux-mint-amd64.deb"
