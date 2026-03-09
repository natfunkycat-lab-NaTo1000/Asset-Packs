# https://github.com/Next-Flip/Momentum-Firmware/blob/dev/scripts/flipper/assets/heatshrink_stream.py
from __future__ import annotations

import struct


class HeatshrinkDataStreamHeader:
    MAGIC = 0x53445348
    VERSION = 1

    def __init__(self, window_size: int, lookahead_size: int) -> None:
        self.window_size = window_size
        self.lookahead_size = lookahead_size

    def pack(self) -> bytes:
        return struct.pack(
            "<IBBB", self.MAGIC, self.VERSION, self.window_size, self.lookahead_size
        )

    @staticmethod
    def unpack(data: bytes) -> HeatshrinkDataStreamHeader:
        if len(data) != 7:
            raise ValueError("Invalid header length")
        magic, version, window_size, lookahead_size = struct.unpack("<IBBB", data)
        if magic != HeatshrinkDataStreamHeader.MAGIC:
            raise ValueError("Invalid magic number")
        if version != HeatshrinkDataStreamHeader.VERSION:
            raise ValueError("Invalid version")
        return HeatshrinkDataStreamHeader(window_size, lookahead_size)
