# Asset-Pack Downloader

A full-stack command-line downloader for [Momentum Firmware](https://github.com/Next-Flip/Momentum-Firmware) asset packs, written in C++17.

It queries the official API (`https://up.momentum-fw.dev/asset-packs`), lists available packs, and downloads them as `.zip` or `.tar.gz` archives.

## Requirements

- C++17-capable compiler (GCC ≥ 9, Clang ≥ 9, MSVC ≥ 2019)
- CMake ≥ 3.14
- [libcurl](https://curl.se/libcurl/) with SSL support

Install libcurl on common systems:
```bash
# Debian / Ubuntu
sudo apt install libcurl4-openssl-dev

# Fedora / RHEL
sudo dnf install libcurl-devel

# macOS (Homebrew)
brew install curl

# Arch Linux
sudo pacman -S curl
```

## Build

```bash
cd downloader
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

The binary is placed at `build/asset-pack-dl` (or `build/asset-pack-dl.exe` on Windows).

## Usage

```
asset-pack-dl --list
    List all available asset packs

asset-pack-dl --download <pack-id> [options]
    Download a specific asset pack

asset-pack-dl --all [options]
    Download all asset packs

Options:
  --format <fmt>   Download format: zip (default) or tar.gz
  --output <dir>   Output directory (default: current directory)
  --help           Show help message
```

## Examples

```bash
# List all available packs
./build/asset-pack-dl --list

# Download a single pack (ZIP)
./build/asset-pack-dl --download black-flags

# Download a single pack as tar.gz into ~/flipper/packs
./build/asset-pack-dl --download pokemon --format tar.gz --output ~/flipper/packs

# Download every pack as zip into ./all-packs/
./build/asset-pack-dl --all --output all-packs
```

## Installing the downloaded pack

Copy the downloaded `.zip` or `.tar.gz` file to your Flipper Zero's SD card at:

```
/ext/asset_packs/<pack-name>/
```

Then select the pack in **Momentum Settings → Interface → Asset Pack**.
