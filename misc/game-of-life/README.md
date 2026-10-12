# Game of Life

**Category:** Misc · **Points:** 751

> Life plays the game, real one :(

**Flag:** `kBxAc{c0NWayS_liFe_foRg375_i7s_past_$o_wE_MakE_Z3_rEmeM8eR_i7_f0r_uS_agaiN}`

---

## TL;DR

The "Conway's Game of Life" theme is camouflage. The supplied board is a big
grid of `.` and `#` that divides perfectly into 8×8 tiles, and only **two**
distinct tiles exist. Treat them as binary `0`/`1`, read left-to-right /
top-to-bottom, and the 600 tiles become 75 ASCII bytes — the flag.

## What We're Given

`game-of-life.zip` contains a single file, `final_board.txt`: a large grid made
from periods and hash signs.

```text
................................................................
................................................................
..#.#.......##......##....#.#.......##....#.#.......##......##..
.#..#.....#..#....#..#...#..#.....#..#...#..#.....#..#....#..#..
..#.#.........#.......#...#.#.........#...#.#.........#.......#.
...#.......###.....###.....#.......###.....#.......###.....###..
................................................................
................................................................
```

The title points at Conway's Game of Life (`#` = live cell, `.` = dead), but we
never actually have to simulate anything — the board has a much simpler hidden
structure.

## Initial Recon

Check the dimensions first:

```bash
wc -lc final_board.txt   # 600 rows, every row 64 chars wide
```

Both numbers are divisible by 8 (`600/8 = 75`, `64/8 = 8`), a strong hint that
the board is a mosaic of **8×8 tiles** — 75 rows of 8 tiles = 600 tiles total.

## The Core Concept

When you compare all 600 tiles, there are only **two** unique designs:

```text
Pattern A (0)        Pattern B (1)
........             ........
........             ........
..#.#...             ....##..
.#..#...             ..#..#..
..#.#...             ......#.
...#....             ...###..
........             ........
........             ........
```

Two possible tiles ⇒ binary. 600 tiles ⇒ 600 bits ⇒ `600/8 = 75` bytes, a very
reasonable flag length. Assign the first tile seen to `0`, the second to `1`,
read in normal reading order, and regroup into bytes.

The first eight tiles decode to `01101011` = `0x6b` = ASCII `k`; the next bytes
give `B x A c {`, confirming the mapping is right. (If the mapping or bit order
were flipped the output would be garbage — only a couple of combinations to try.)

## Building the Exploit

See [`solve.py`](solve.py). It slices the board into 8×8 tiles, keeps the two
distinct designs as the binary alphabet, and reassembles the bytes:

```python
tiles = [
    tuple(row[x:x + 8] for row in board[y:y + 8])
    for y in range(0, len(board), 8)
    for x in range(0, len(board[0]), 8)
]
alphabet = list(dict.fromkeys(tiles))       # first tile -> 0, second -> 1
assert len(alphabet) == 2
bits = "".join(str(alphabet.index(t)) for t in tiles)
decoded = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
```

## Running It

```console
$ python3 solve.py
kBxAc{c0NWayS_liFe_foRg375_i7s_past_$o_wE_MakE_Z3_rEmeM8eR_i7_f0r_uS_agaiN}
```

## Key Takeaways

- A "Game of Life" board that is perfectly divisible into tiles with only two
  variants is almost never a simulation puzzle — it's binary in disguise.
- When a grid's dimensions factor cleanly by 8, try tiling + binary before
  anything heavier.
