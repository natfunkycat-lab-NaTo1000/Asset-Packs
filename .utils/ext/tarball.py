# https://github.com/Next-Flip/Momentum-Firmware/blob/dev/scripts/flipper/assets/tarball.py
from __future__ import annotations

import io
import gzip
import pathlib
import tarfile
import typing

import heatshrink2

from .heatshrink_stream import HeatshrinkDataStreamHeader

FLIPPER_TAR_FORMAT = tarfile.USTAR_FORMAT

TAR_HEATSHRINK_EXTENSION = ".ths"
TAR_GZIP_EXTENSION = ".tar.gz"


def tar_sanitizer_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    tarinfo.gid = tarinfo.uid = 0
    tarinfo.mtime = 0
    tarinfo.uname = tarinfo.gname = "furippa"
    if tarinfo.type == tarfile.DIRTYPE:
        tarinfo.mode = 0o40755  # drwxr-xr-x
    else:
        tarinfo.mode = 0o644  # ?rw-r--r--
    return tarinfo


def compress_tree_tarball(
    src_dir: str | pathlib.Path,
    output_name: str | pathlib.Path,
    filter: typing.Callable[[tarfile.TarInfo], tarfile.TarInfo] = tar_sanitizer_filter,
    hs_window: int = 13,
    hs_lookahead: int = 6,
    gz_level: int = 9,
) -> tuple[int, int]:
    output_path = pathlib.Path(output_name)
    plain_tar = io.BytesIO()
    with tarfile.open(
        fileobj=plain_tar,
        mode="w:",
        format=FLIPPER_TAR_FORMAT,
    ) as tarball:
        tarball.add(src_dir, arcname="", filter=filter)
    plain_tar.seek(0)
    src_data = plain_tar.read()

    output_suffixes = "".join(output_path.suffixes)
    if output_suffixes.endswith(TAR_HEATSHRINK_EXTENSION):
        compressed = heatshrink2.compress(
            src_data, window_sz2=hs_window, lookahead_sz2=hs_lookahead
        )
        header = HeatshrinkDataStreamHeader(hs_window, hs_lookahead)
        compressed = header.pack() + compressed

    elif output_suffixes.endswith(TAR_GZIP_EXTENSION):
        compressed = gzip.compress(src_data, compresslevel=gz_level, mtime=0)

    else:
        compressed = src_data

    output_path.write_bytes(compressed)
    return len(src_data), len(compressed)
