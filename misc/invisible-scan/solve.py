#!/usr/bin/env python3
"""Stage 2 of Invisible Scan.

Scanning the QR code (qr_payload.txt) shows only a decoy sentence. The real
payload is hidden in zero-width Unicode characters mixed into that text. Eight
distinct invisible code points encode 3 bits each (base-8). The first 16 bits
are a big-endian length header; the next length*8 bits are the flag.
"""

from pathlib import Path

# The eight invisible symbols, in increasing code-point order -> values 0..7.
ALPHABET = "​‌‍⁠⁢⁣⁤﻿"

payload = Path("qr_payload.txt").read_text().rstrip("\n")

invisible = "".join(c for c in payload if c in ALPHABET)
bits = "".join(f"{ALPHABET.index(c):03b}" for c in invisible)

length = int(bits[:16], 2)                       # 16-bit length header (bytes)
data = bits[16:16 + length * 8]                  # the flag bits (padding ignored)

flag = bytes(int(data[i:i + 8], 2) for i in range(0, len(data), 8)).decode()
print(flag)
