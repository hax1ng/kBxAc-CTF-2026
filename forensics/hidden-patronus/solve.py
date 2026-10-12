#!/usr/bin/env python3
"""Hidden Patronus — stage 1: fix the lying PNG height to reveal the key.

harry_potter.png declares 1100 rows in its IHDR, but its IDAT data decompresses
to 1200 rows (1200 x 3601 bytes/row). Bumping the IHDR height to 1200 (and
fixing the chunk CRC) exposes the hidden bottom 100 rows, which read
"KEY:Expecto_Patronum".

Stages 2-3 use external tools and are documented in the README:
  2. OpenStego RandomLSB extract from flag.bmp using that key.
  3. StegZero zero-width-Unicode decode of the extracted text -> the flag.
"""
import struct
import zlib

data = bytearray(open("harry_potter.png", "rb").read())

# Prove the hidden rows: decompress every IDAT and count rows (3601 bytes/row).
offset, compressed = 8, b""
while offset < len(data):
    length = struct.unpack(">I", data[offset:offset + 4])[0]
    chunk_type = data[offset + 4:offset + 8]
    if chunk_type == b"IDAT":
        compressed += data[offset + 8:offset + 8 + length]
    offset += 12 + length
raw = zlib.decompress(compressed)
print(f"decompressed {len(raw)} bytes -> {len(raw) // 3601} rows (header claims 1100)")

# Repair IHDR height 1100 -> 1200 and recompute the IHDR CRC.
assert data[12:16] == b"IHDR"
data[20:24] = struct.pack(">I", 1200)
data[29:33] = struct.pack(">I", zlib.crc32(data[12:29]) & 0xFFFFFFFF)
open("harry_full.png", "wb").write(data)
print("wrote harry_full.png (1200x1200); bottom rows now show KEY:Expecto_Patronum")
