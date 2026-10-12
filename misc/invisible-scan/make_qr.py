#!/usr/bin/env python3
"""Stage 1 of Invisible Scan.

challenge.bin (inside invisiblescan.zip) is an ASCII-art QR code: 89 rows of
178 chars, where every QR module is drawn as two characters ("##" = black,
"  " = white). Rebuild it as a real, upscaled PNG so a scanner can read it.

    unzip invisiblescan.zip            # -> challenge.bin
    python3 make_qr.py                 # -> qr.png
    zbarimg --raw -q qr.png > qr_payload.txt
    python3 solve.py                   # decodes the invisible payload
"""

from pathlib import Path

from PIL import Image

lines = Path("challenge.bin").read_text().splitlines()

modules = [[line[x:x + 2] == "##" for x in range(0, len(line), 2)] for line in lines]

scale = 8
height, width = len(modules), len(modules[0])
image = Image.new("1", (width * scale, height * scale), 1)
for y, row in enumerate(modules):
    for x, black in enumerate(row):
        if black:
            for py in range(y * scale, (y + 1) * scale):
                for px in range(x * scale, (x + 1) * scale):
                    image.putpixel((px, py), 0)

image.save("qr.png")
print("wrote qr.png")
