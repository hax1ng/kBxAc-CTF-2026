# Hidden Patronus

**Category:** Forensics · **Points:** 1000 · **Author:** HydraRoot

> Harry Potter is everyones favourite right? isn't it?

**Flag:** `kBxAc{z3r0_w1dth_1nv1s1bl3_1nf0_3xp3ct0_p4tr0num_8f7e6d5c4b3a2f1e0d9c}`

> **Files:** `harry_potter.png` and `flag.bmp` (challenge inputs); [`solve.py`](solve.py) performs stage 1 (the PNG-height repair).

---

## Files provided

```text
attachments/
├── flag.bmp
└── harry_potter.png
```

## TL;DR

The PNG lied about its height. It claimed to be 1,100 pixels tall even though it contained 1,200 rows of image data. Repairing the height revealed the password `Expecto_Patronum`. That password extracted a text file from `flag.bmp` with OpenStego. The resulting text looked like a failure message, but it contained invisible Unicode characters that decoded to the flag.

## Step 1: Basic file checks

I started with the usual file and metadata checks:

```bash
file attachments/*
exiftool attachments/*
pngcheck -v attachments/harry_potter.png
```

The files appeared to be ordinary images:

```text
flag.bmp:         PC bitmap, Windows 3.x format, 800 x 800 x 24
harry_potter.png: PNG image data, 1200 x 1100, 8-bit/color RGB
```

However, ImageMagick gave an important warning when reading the PNG:

```text
IDAT: Too much image data
```

In plain English, the PNG header said, "this image has 1,100 rows," but the compressed pixel data contained more information than 1,100 rows should require. That suggested that part of the image had been hidden simply by giving the decoder a false height.

## Step 2: Proving that the PNG contains extra rows

PNG image pixels are stored in one or more `IDAT` chunks. After joining and decompressing those chunks, we can compare the amount of data to the image dimensions.

The PNG is:

- 1,200 pixels wide
- RGB, so each pixel uses 3 bytes
- non-interlaced
- one filter byte at the start of every row

Therefore, one row needs:

```text
(1200 × 3) + 1 = 3601 bytes
```

This script joins and decompresses the IDAT chunks:

```python
import struct
import zlib

data = open("attachments/harry_potter.png", "rb").read()
offset = 8                     # Skip the PNG signature
compressed = b""

while offset < len(data):
    length = struct.unpack(">I", data[offset:offset + 4])[0]
    chunk_type = data[offset + 4:offset + 8]
    chunk_data = data[offset + 8:offset + 8 + length]

    if chunk_type == b"IDAT":
        compressed += chunk_data

    offset += 12 + length      # length + type + data + CRC

raw = zlib.decompress(compressed)
print("Decompressed bytes:", len(raw))
print("Number of rows:", len(raw) // 3601)
```

The result was:

```text
Decompressed bytes: 4321200
Number of rows: 1200
```

That is an exact match for a **1200 × 1200** RGB image:

```text
1200 × 3601 = 4321200
```

The header only declared 1,100 rows, leaving the final 100 rows hidden.

## Step 3: Repairing the PNG height

The image height lives in the PNG's `IHDR` chunk. In this file it occupies bytes 20 through 23. I changed it from 1,100 to 1,200 and recalculated the IHDR CRC so the repaired PNG would remain valid.

```python
import struct
import zlib

source = "attachments/harry_potter.png"
destination = "harry_full.png"

data = bytearray(open(source, "rb").read())

# Confirm that this really is the IHDR chunk.
assert data[12:16] == b"IHDR"

# Replace the big-endian height with 1200.
data[20:24] = struct.pack(">I", 1200)

# A PNG chunk CRC covers the chunk type and chunk data.
data[29:33] = struct.pack(">I", zlib.crc32(data[12:29]) & 0xffffffff)

open(destination, "wb").write(data)
print(f"Wrote {destination}")
```

Checking the result confirms that it is now a valid square image:

```bash
file harry_full.png
pngcheck harry_full.png
```

```text
harry_full.png: PNG image data, 1200 x 1200, 8-bit/color RGB
No errors detected in harry_full.png
```

Opening the repaired image reveals text in the newly visible bottom section:

```text
KEY:Expecto_Patronum
```

So the key for the next stage is:

```text
Expecto_Patronum
```

## Step 4: Extracting data from `flag.bmp`

At first glance, `flag.bmp` looks completely black. Looking more closely at its pixel values shows that nearly every color value is zero, with a small number of values set to one. That is a strong hint that information was placed in the least significant bits of the image.

Standard tools such as `steghide` did not recognize it. The correct tool was **OpenStego**, using its RandomLSB method.

After downloading OpenStego, I extracted the payload with the key from the repaired PNG:

```bash
java -jar openstego.jar extract \
    -sf attachments/flag.bmp \
    -xd output \
    -p Expecto_Patronum
```

OpenStego reported:

```text
Extracted file: output/flag.txt
```

The extracted file appeared to say:

```text
Bruhh Your Hardwork Failed
```

That was clearly suspicious. The challenge had already used one hidden layer, and the extracted file was much larger than this short sentence should have been.

## Step 5: Finding the invisible Unicode message

Hex-dumping the text file showed many multi-byte UTF-8 characters between the visible letters:

```bash
xxd output/flag.txt | head
```

Examples included:

```text
U+200B  ZERO WIDTH SPACE
U+200C  ZERO WIDTH NON-JOINER
U+200D  ZERO WIDTH JOINER
U+2060  WORD JOINER
U+2062  INVISIBLE TIMES
U+2063  INVISIBLE SEPARATOR
U+2064  INVISIBLE PLUS
U+FEFF  ZERO WIDTH NO-BREAK SPACE
```

These characters affect formatting but normally draw nothing on the screen. Since there are eight different characters, each one can represent one of eight values, or exactly three bits of data.

The character set and framing match the standard format used by [StegZero](https://github.com/Clevis22/StegZero). Its decoder can be run directly with Node.js:

```bash
git clone https://github.com/Clevis22/StegZero.git
node StegZero/bin/stegzero.js reveal output/flag.txt
```

The hidden message finally decoded to:

```text
kBxAc{z3r0_w1dth_1nv1s1bl3_1nf0_3xp3ct0_p4tr0num_8f7e6d5c4b3a2f1e0d9c}
```

## Flag

```text
kBxAc{z3r0_w1dth_1nv1s1bl3_1nf0_3xp3ct0_p4tr0num_8f7e6d5c4b3a2f1e0d9c}
```

## Takeaways

This challenge used three simple ideas, stacked together:

1. **A falsified PNG height** hid valid rows below the visible image.
2. **Password-protected RandomLSB steganography** hid a file inside a black bitmap.
3. **Zero-width Unicode characters** hid the real message inside an innocent-looking sentence.

The most important clue was the `Too much image data` warning. Image-format warnings are easy to dismiss, but in a forensics challenge they often point directly at the trick.
