#!/usr/bin/env python3
"""
Crossword 2 - kBxAc CTF 2026 (Crypto)

A 104 x 101 "codeword" crossword rendered as a PNG: every letter is replaced by
a number 1-26 (not in A=1 order). Cells with the same number are pixel-for-pixel
identical, so instead of OCR we just group the 40x40 tiles by their raw bytes --
there are exactly 27 unique tiles (26 numbers + 1 black "empty" tile).

The substitution below was recovered by hand from a few long, unusual answers
(XENOTRANSPLANTATION pins 11 letters at once, then XERORADIOGRAPHIC,
QUINQUAGENARIAN, ZYGODACTYLOUS, ... fill in the rest).

Flag = for each row, keep every filled cell L->R and decode it; join the 101
rows with '_' and wrap in kBxAc{...}.
"""
from PIL import Image

IMAGE = "attachments/crossword.png"
CELL = 40

# Values of the unique tiles in order of first appearance (None == black/empty).
tile_values = [
    None, 13, 24, 2, 25, 16, 21, 11, 3,
    15, 19, 6, 5, 26, 10, 18, 8, 9, 4,
    23, 20, 17, 12, 22, 7, 14, 1,
]

# Substitution recovered from the long answers in the grid.
number_to_letter = {
    1: "D",  2: "O",  3: "H",  4: "C",  5: "M",  6: "E",
    7: "Y",  8: "B",  9: "I", 10: "Q", 11: "X", 12: "A",
    13: "K", 14: "P", 15: "U", 16: "R", 17: "W", 18: "F",
    19: "S", 20: "L", 21: "Z", 22: "G", 23: "V", 24: "N",
    25: "T", 26: "J",
}

image = Image.open(IMAGE).convert("L")
width, height = image.size
assert width % CELL == 0 and height % CELL == 0
columns, rows = width // CELL, height // CELL

# Map each distinct 40x40 bitmap to an id, then to its hand-labelled value.
seen_tiles = {}
grid = []
for row in range(rows):
    decoded_row = []
    for column in range(columns):
        box = (column * CELL, row * CELL, (column + 1) * CELL, (row + 1) * CELL)
        tile = image.crop(box).tobytes()
        seen_tiles.setdefault(tile, len(seen_tiles))
        decoded_row.append(tile_values[seen_tiles[tile]])
    grid.append(decoded_row)

assert len(seen_tiles) == 27, f"expected 27 tiles, got {len(seen_tiles)}"

# Keep every filled cell in each row (vertical-answer letters included on purpose).
flag_rows = [
    "".join(number_to_letter[v] for v in row if v is not None)
    for row in grid
]
flag = "kBxAc{" + "_".join(flag_rows) + "}"
print(flag)
