# Ghost Frame

**Category:** Forensics · **Points:** 1000 · **Author:** adithG17

> A surveillance recording was recovered from an internal monitoring system. At first glance the footage appears completely ordinary and plays without any obvious issues — but it may contain more than what is visible during normal playback.

**Flag:** `kBxAc{R3DUCE4I5L0PANDR34DI7M4NU47}`

> **Challenge file:** the original 87 MB `recording.mp4` is not committed — download it from the organiser link: <https://drive.google.com/file/d/15ECL69jVBADBHtSf3V33lbz5eM7r-lwR/view>. [`solve.py`](solve.py) processes it and writes [`recovered.png`](recovered.png).

---

## Analysis

The MP4 has one suspicious independently encoded interval: frames 3075–3682
(about 123.0–147.3 seconds).  Static frames from this interval do not contain
readable text, but they show a faint field of regularly spaced dots that is not
present immediately before or after it.

The important property is motion rather than pixel LSBs or container metadata.
In most of the image the dots move downward by about four pixels per frame.  In
the hidden letter shapes, an otherwise identical population moves upward.  A
single frame consequently has nearly the same dot statistics inside and outside
the letters.

To recover the mask:

1. Take a short 25-frame window from the anomalous interval.  A short window
   avoids blurring caused by the slow drift of the complete message.
2. Subtract the temporal mean to suppress the stationary surveillance scene.
3. Apply a small spatial high-pass filter to retain the dot field.
4. For every adjacent pair, compare the local correlation after shifting the
   first frame by `+4` and `-4` pixels vertically.
5. Accumulate `match_down - match_up` and lightly blur the result.

The resulting image contains four lines:

```text
R3DUCE4
I5L0PAN
DR34DI7
M4NU47
```

Joining the wrapped lines and adding the challenge wrapper gives the flag.

Run:

```bash
python3 solve.py recording.mp4
```

This writes `recovered.png` and prints the flag.
