# Invisible Scan

**Category:** Misc · **Points:** 1000 · **Author:** HydraRoot

> A mysterious text file contains something hidden in plain sight. Look
> carefully at the patterns and uncover the secret.

**Flag:** `kBxAc{4$C1!_art_mas7eR_(aNvas_HidDen_1N_7He_P1xEls_of_7he_c0dE}`

---

## TL;DR

The handout is an ASCII-art **QR code**. Scanning it shows only a decoy
sentence — but the decoded text is sprinkled with **zero-width Unicode
characters**. Eight distinct invisible code points encode 3 bits each; a 16-bit
length header is followed by the flag bytes.

## What We're Given

`invisiblescan.zip` → `challenge.bin`. Despite the extension it's plain ASCII,
made almost entirely of spaces and `#`:

```bash
file challenge.bin          # ASCII text
xxd -l 1024 challenge.bin   # only 0x20 (space), 0x23 (#), 0x0a (newline)
```

The dimensions are telling:

```text
89 rows, each 178 characters wide
```

178 is exactly twice 89 — every QR module is drawn as two characters
(`##` = black, `  ` = white), so the real image is an **89×89 grid**. Three big
corner markers = a QR code.

## Stage 1 — Rebuild the QR

[`make_qr.py`](make_qr.py) turns each character pair into one module and
upscales it so a scanner can read it, then `zbarimg` extracts the payload:

```bash
python3 make_qr.py                            # -> qr.png
zbarimg --raw -q qr.png > qr_payload.txt
```

On screen the payload is just:

```text
Congratulations! You found the flag :)
```

…which contains no flag. The challenge name — **Invisible Scan** — is the hint
that there's more in the decoded data than the terminal shows.

## The Core Concept — Zero-Width Steganography

Counting the distinct code points in the payload reveals eight *invisible*
characters alongside the visible cover text:

| Character | Unicode name | Value | Bits |
|---|---|---:|---:|
| `U+200B` | Zero Width Space | 0 | `000` |
| `U+200C` | Zero Width Non-Joiner | 1 | `001` |
| `U+200D` | Zero Width Joiner | 2 | `010` |
| `U+2060` | Word Joiner | 3 | `011` |
| `U+2062` | Invisible Times | 4 | `100` |
| `U+2063` | Invisible Separator | 5 | `101` |
| `U+2064` | Invisible Plus | 6 | `110` |
| `U+FEFF` | Zero Width No-Break Space | 7 | `111` |

Eight symbols = exactly 3 bits each. Mapped in increasing code-point order and
stripped of all cover text, the 174 invisible symbols give 522 bits. The first
16 bits are a big-endian length (`0x003f` = 63 bytes); the next `63*8 = 504`
bits are the message, and the final 2 bits are padding.

## Building the Exploit

See [`solve.py`](solve.py):

```python
ALPHABET = "​‌‍⁠⁢⁣⁤﻿"
invisible = "".join(c for c in payload if c in ALPHABET)
bits = "".join(f"{ALPHABET.index(c):03b}" for c in invisible)
length = int(bits[:16], 2)                      # 16-bit length header
data = bits[16:16 + length * 8]
flag = bytes(int(data[i:i+8], 2) for i in range(0, len(data), 8)).decode()
```

## Running It

```console
$ python3 make_qr.py && zbarimg --raw -q qr.png > qr_payload.txt
$ python3 solve.py
kBxAc{4$C1!_art_mas7eR_(aNvas_HidDen_1N_7He_P1xEls_of_7he_c0dE}
```

## Key Takeaways

- The challenge hides data **twice**: a QR drawn as text, then a real message
  hidden in invisible Unicode inside the QR's decoded string.
- When a scan "works" but yields a suspiciously clean sentence, inspect the raw
  bytes for zero-width characters — redirect to a file, don't trust the terminal.
- Eight distinct symbols is a dead giveaway for a base-8 / 3-bit encoding.
