#!/usr/bin/env python3
"""Who Let the Dog Out — FSK hidden in the stereo channel difference.

The "dog laughing" is (almost) identical in both channels; subtracting the
right channel from the left cancels it and leaves a quiet FSK signal that
starts 3 s in. Each 0.06 s bit is 4200 Hz (= 0) or 7200 Hz (= 1); 360 bits =
45 ASCII bytes = the flag.

Unzip audio01.zip first to get challenge.wav. Needs numpy (`pip install numpy`).
"""
import wave

import numpy as np

with wave.open("challenge.wav", "rb") as wav:
    rate = wav.getframerate()
    samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
    stereo = samples.reshape(-1, 2).astype(np.float64)

hidden = stereo[:, 0] - stereo[:, 1]          # cancel the shared dog audio

bit_length = int(rate * 0.06)                 # samples per bit
start = 3 * rate                              # data starts at 3 seconds
blocks = hidden[start:start + 360 * bit_length].reshape(360, bit_length)

# 0.06 s blocks -> 16.67 Hz FFT bins; 4200 Hz = bin 252, 7200 Hz = bin 432.
spectrum = np.abs(np.fft.rfft(blocks, axis=1))
bits = (spectrum[:, 432] > spectrum[:, 252]).astype(int)

flag = "".join(
    chr(int("".join(map(str, bits[i:i + 8])), 2))
    for i in range(0, len(bits), 8)
)
print(flag)
