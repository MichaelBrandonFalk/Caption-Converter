#!/bin/sh
set -eu

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller
pyinstaller --noconfirm --windowed --onedir \
  --name "Caption Converter" \
  --icon Contents/Resources/AppIcon.icns \
  --paths src \
  app.py

cd dist
ditto -c -k --sequesterRsrc --keepParent "Caption Converter.app" "Caption-Converter-macos-arm64.zip"
echo "Created dist/Caption-Converter-macos-arm64.zip"

