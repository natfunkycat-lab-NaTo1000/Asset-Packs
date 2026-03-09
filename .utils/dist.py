#!/usr/bin/env python3
"""Build the dist/ directory by collecting all pack download files."""

import shutil

import common

from ext import tarball
from ext import ziparch


def build_dist() -> None:
    dist_dir = common.packs_root / "dist"
    shutil.rmtree(dist_dir, ignore_errors=True)
    dist_dir.mkdir(parents=True, exist_ok=True)

    pack_sets = [
        pack_set
        for pack_set in sorted(common.packs_root.iterdir())
        if not pack_set.name.startswith(".")
        and pack_set.is_dir()
        and pack_set.name != "dist"
    ]

    copied = []
    for pack_set in pack_sets:
        download_dir = pack_set / "download"
        if not download_dir.is_dir():
            print(f"Skipping '{pack_set.name}': no download directory", flush=True)
            continue

        for ext in (ziparch.ZIP_ARCH_EXTENSION, tarball.TAR_GZIP_EXTENSION):
            src = download_dir / (pack_set.name + ext)
            if src.exists():
                dest = dist_dir / src.name
                shutil.copy2(src, dest)
                copied.append(dest.name)
                print(f"  {pack_set.name}{ext}", flush=True)

    print(f"\nDist build complete: {len(copied)} files in {dist_dir}", flush=True)


if __name__ == "__main__":
    print("Building dist/...", flush=True)
    build_dist()
