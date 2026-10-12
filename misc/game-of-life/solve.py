#!/usr/bin/env python3
from pathlib import Path


board = Path("final_board.txt").read_text().splitlines()

# The 600x64 board is a 75x8 array of independent 8x8 Life patterns.
tiles = [
    tuple(row[x : x + 8] for row in board[y : y + 8])
    for y in range(0, len(board), 8)
    for x in range(0, len(board[0]), 8)
]

alphabet = list(dict.fromkeys(tiles))
assert len(alphabet) == 2

# The pattern first encountered represents 0; bits in each byte are MSB-first.
bits = "".join(str(alphabet.index(tile)) for tile in tiles)
flag = bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))
print(flag.decode())
