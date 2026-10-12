#!/usr/bin/env python3
"""Syringe (💉) — rebuild the JAB Code that was streamed to the "printer".

The pcap has one large TCP stream to port 9100 carrying a custom "LR" record
format. Stripping the record wrappers leaves 84,100 bytes = 21,025 four-byte
groups (07 RR GG BB) = a 145x145 pixel image: an 8-colour JAB Code. Decode the
rendered image with a JAB Code reader to get the flag.

Input: stream12.bin — the reassembled server->client payload of tcp.stream 12,
extracted from challenge.pcap with:

    tshark -r challenge.pcap \\
      -Y 'tcp.stream==12 && ip.src==10.10.20.15 && tcp.payload' \\
      -T fields -e tcp.payload | tr -d '\\n' | xxd -r -p > stream12.bin
"""

from pathlib import Path

from PIL import Image

stream = Path("stream12.bin").read_bytes()

# Concatenate every LR record's payload, dropping the 7-byte header and the
# 2-byte trailer/checksum on each record.
offset = 0
payload = bytearray()
while offset < len(stream):
    assert stream[offset:offset + 2] == b"LR", "lost record sync"
    length = int.from_bytes(stream[offset + 5:offset + 7], "big")
    payload.extend(stream[offset + 7:offset + 7 + length])
    offset += 7 + length + 2

# Each pixel is 07 RR GG BB; the 0x07 is a constant channel/control mask.
pixels = []
for i in range(0, len(payload), 4):
    control, red, green, blue = payload[i:i + 4]
    assert control == 0x07
    pixels.append((red, green, blue))

side = 145
assert len(pixels) == side * side, len(pixels)

img = Image.new("RGB", (side, side))
img.putdata(pixels)
img.save("display.png")
# Nearest-neighbour upscale keeps every colour module crisp for the decoder.
img.resize((side * 4, side * 4), Image.Resampling.NEAREST).save("display_4x.png")
print(f"wrote display.png ({side}x{side}) and display_4x.png")
print("Decode with a JAB Code reader, e.g. srlehn/jabcode:")
print("  jabcode decode --only current-c display_4x.png")
print("  -> kBxAc{________________Wow_kya_LaDka_ha1_8heRY_h4ND$oM_Ky4_maal_h@I}")
