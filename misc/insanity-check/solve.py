#!/usr/bin/env python3
"""kBxAc CTF 2026 / Misc / Insanity Check.

The challenge hands us one long Base64 string. Decoding it six times reveals a
plain-language marker, "here is the flag : ", followed by the flag body. The
text after the marker *looks* like yet another encoding (ASCII85 -> Base64),
but that extra chain is a decoy that leads to a "wrong flag" message. The
correct move is to stop at the marker and wrap the remaining bytes verbatim.
"""

from base64 import b64decode
from pathlib import Path

PREFIX = b"here is the flag : "


def main() -> None:
    # The challenge blob is the only (long) line in challenge.txt.
    lines = [line.strip() for line in Path("challenge.txt").read_bytes().splitlines() if line.strip()]
    data = lines[-1]

    rounds = 0
    while not data.startswith(PREFIX):
        # validate=True rejects malformed input instead of silently dropping it.
        data = b64decode(data, validate=True)
        rounds += 1

    # Stop here. Preserve the body byte-for-byte: it contains quotes,
    # backslashes, backticks and punctuation that are all part of the flag.
    body = data.removeprefix(PREFIX).decode("ascii")
    flag = f"kBxAc{{{body}}}"

    print(f"Base64 rounds: {rounds}")
    print(flag)


if __name__ == "__main__":
    main()
