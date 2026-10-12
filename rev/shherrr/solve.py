#!/usr/bin/env python3
"""Shherrr — recover the flag from the hidden decrypt routine.

The "calculator" is a decoy. A hidden branch in the (Raku) binary holds an
encrypted byte array and a repeating 5-byte XOR key. XORing them back and
calling chr() on each result rebuilds the flag:  plain[i] = enc[i] ^ key[i % 5]
"""

encrypted = [
    0x78, 0x75, 0xb8, 0x9f, 0x21,
    0x68, 0x44, 0xa8, 0xed, 0x2e,
    0x7f, 0x68, 0xa3, 0xea, 0x2e,
    0x70, 0x68, 0xf1, 0xad, 0x1d,
    0x71, 0x45, 0xf0, 0xb5, 0x71,
    0x7d, 0x4a,
]

key = [19, 55, 192, 222, 66]

flag = "".join(chr(v ^ key[i % len(key)]) for i, v in enumerate(encrypted))
print(flag)
