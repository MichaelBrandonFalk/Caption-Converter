@echo off
setlocal

python -m pip install --upgrade pip
pip install pyinstaller
pyinstaller --noconfirm --windowed --onefile --name "Caption Converter" --paths src app.py

powershell -Command "Compress-Archive -Path 'dist/Caption Converter.exe' -DestinationPath 'dist/Caption-Converter-windows-x64.zip' -Force"
echo Windows build created in dist\Caption-Converter-windows-x64.zip
