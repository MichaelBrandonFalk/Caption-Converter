# Caption Converter

Portable rebuild of the `Caption Converter` app so it can ship from one repo:

- A downloadable macOS app for Apple Silicon
- A Linux Mint `.deb` installer for 64-bit PCs
- A downloadable Windows executable
- A browser-only converter on GitHub Pages
- A cross-platform Python desktop app

## What It Does

- Converts `.srt` to `.vtt`
- Converts `.vtt` to `.srt`
- Creates `.ttml` output from `.srt` or `.vtt`
- Cleans cue ordering, zero-length cues, and overlapping timestamps

## Project Layout

- `Contents/`: legacy packaged macOS app bundle kept for historical reference
- `src/caption_converter/`: portable Python source
- `site/`: static in-browser converter for GitHub Pages
- `.github/workflows/`: Pages deployment and desktop release automation
- `scripts/`: local packaging helpers for Windows, macOS, and Linux Mint

## Local Python Usage

Create outputs for every selected format:

```bash
PYTHONPATH=src python -m caption_converter path/to/file.srt
```

Create only VTT:

```bash
PYTHONPATH=src python -m caption_converter --to-vtt path/to/file.srt
```

Launch the desktop GUI:

```bash
PYTHONPATH=src python -m caption_converter --gui
```

## GitHub Pages

The Pages site is fully client-side. Uploaded files stay in the browser.

Pushes to `main` deploy the `site/` directory through `.github/workflows/pages.yml`. If GitHub Pages has not been enabled for the repo yet, turn it on in repository settings when GitHub prompts for it.

## Downloadable Releases

The release workflow builds:

- `Caption-Converter-macos-arm64.zip`
- `Caption-Converter-linux-mint-amd64.deb`
- `Caption-Converter-windows-x64.zip`

The macOS downloads are unsigned and not notarized, so some users will need to allow the app manually the first time they open it.

To create a downloadable release:

1. Push the repo to GitHub.
2. Create a tag like `v1.1.0` and push it.
3. The release workflow will attach macOS Apple Silicon, Windows, and Linux Mint builds to the GitHub release.

You can also run the workflow manually to get an artifact without cutting a release.

## Linux Mint

The `.deb` installer targets **Linux Mint 21 and 22 (64-bit x86_64 / amd64)**, including Cinnamon, MATE, and Xfce. It bundles Python and Tcl/Tk; users do not need to install Python separately.

1. Download `Caption-Converter-linux-mint-amd64.deb` from the latest release.
2. Double-click it and select **Install Package**, or run this in the download folder:

   ```bash
   sudo apt install ./Caption-Converter-linux-mint-amd64.deb
   ```

3. Open **Caption Converter** from the applications menu, or run `caption-converter` in a terminal.

Remove it with `sudo apt remove caption-converter`.

To build locally on an x86_64 Ubuntu 22.04 or Linux Mint 21 machine:

```bash
sudo apt update
sudo apt install python3-venv python3-tk binutils
sh scripts/build_linux_mint.sh
```

The installer is written to `dist/`. Release automation builds on Ubuntu 22.04, the base of Mint 21, to keep the bundled runtime compatible with Mint 21 and Mint 22. Building on a newer distribution can require a newer glibc than Mint 21 provides; see [PyInstaller's Linux compatibility guidance](https://pyinstaller.org/en/stable/usage.html#making-gnu-linux-apps-forward-compatible).

Linux release checks install the package on Ubuntu 22.04 and 24.04 (the bases of Mint 21 and 22), convert a sample subtitle with the bundled executable, validate the applications menu entry, and check GUI startup under a virtual display. A complete Mint desktop session is still needed for manual installation and file-picker verification.

## Notes

- The original macOS app used a Swift dialog for format selection. This rebuild removes that dependency so the app can run on Windows, macOS, and Linux Mint from the same Python codebase.
- The browser version mirrors the core subtitle conversion flow but runs entirely in JavaScript because GitHub Pages cannot execute Python server code.
