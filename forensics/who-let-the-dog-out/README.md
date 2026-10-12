# Who Let the Dog Out

**Category:** Forensics · **Points:** 983 · **Author:** adithG17

> Someone left this recording lying around, and honestly… who let the dog out? It sounds like nothing more than a ridiculous dog laughing. But there seems to be something else hiding in the recording.

**Flag:** `kBxAc{_____________****tRUe_trUe_Fl@G__trUe_}`

> **Files:** `audio01.zip` (unzip to get `challenge.wav`) and [`solve.py`](solve.py).

---

## The idea

At first, the recording sounds like a dog laughing. The trick is that it's a **stereo** recording: it has a left and a right channel. The dog audio is almost identical in both, but a quiet hidden signal is different between them.

Think of the two channels as two copies of the same picture, with a tiny extra mark on one copy. If we subtract one copy from the other, the shared picture disappears and the mark stands out. Here, subtracting the right audio channel from the left cancels most of the dog sound and leaves the hidden tones.

## What was hidden?

The leftover signal starts **3 seconds** into the recording. It switches between two pitches:

| Tone | Meaning |
| --- | --- |
| 4,200 Hz | `0` |
| 7,200 Hz | `1` |

This is **frequency-shift keying (FSK)**: instead of writing zeroes and ones on a page, the creator used one frequency for each bit. Each bit lasts **0.06 seconds**. There are 360 bits total, which makes 45 groups of eight. Reading those groups as ASCII characters gives the flag.

The first eight bits are `01101011`, which is `k` in ASCII. The next eight are `01000010`, or `B`. That was a good sign we had the right bit order and tone mapping: the message begins `kB...`.

## Reproducing it

After unzipping `audio01.zip`, this short Python script decodes `challenge.wav`. It needs NumPy (`pip install numpy`).

```python
import wave
import numpy as np

with wave.open("challenge.wav", "rb") as wav:
    rate = wav.getframerate()
    samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
    stereo = samples.reshape(-1, 2).astype(np.float64)

# Remove the sound shared by the two channels.
hidden = stereo[:, 0] - stereo[:, 1]

bit_length = int(rate * 0.06)       # 2,646 samples per bit
start = 3 * rate                    # hidden data starts at 3 seconds
blocks = hidden[start:start + 360 * bit_length].reshape(360, bit_length)

# Each block is 0.06 seconds long, so its FFT bins are 16.67 Hz apart.
# 4,200 Hz lands on bin 252; 7,200 Hz lands on bin 432.
spectrum = np.abs(np.fft.rfft(blocks, axis=1))
bits = (spectrum[:, 432] > spectrum[:, 252]).astype(int)

message = "".join(
    chr(int("".join(map(str, bits[i:i + 8])), 2))
    for i in range(0, len(bits), 8)
)
print(message)
```

Output:

```text
kBxAc{_____________****tRUe_trUe_Fl@G__trUe_}
```

Yes, the long run of underscores and the four asterisks really are in the decoded text. Keep the capitalization and symbols exactly as shown.

## Flag

`kBxAc{_____________****tRUe_trUe_Fl@G__trUe_}`
