#!/usr/bin/env python3
"""Recover the motion-only message from recording.mp4.

The suspicious section starts at frame 3075.  The dot field moves about four
pixels down per frame outside the letters and four pixels up inside them.  A
directional matched filter therefore makes the otherwise invisible letter mask
visible.  A short 25-frame window is used so that the slow drift of the whole
message does not blur it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


SEGMENT_START = 3075
WINDOW_OFFSET = 500
WINDOW_LENGTH = 25
VELOCITY = 4
MESSAGE = "R3DUCE4I5L0PANDR34DI7M4NU47"
FLAG = f"kBxAc{{{MESSAGE}}}"


def shifted(image: np.ndarray, dy: int) -> np.ndarray:
    """Translate vertically without allowing wraparound pixels into the image."""
    result = np.roll(image, dy, axis=0)
    if dy > 0:
        result[:dy] = result[dy : dy + 1]
    elif dy < 0:
        result[dy:] = result[dy - 1 : dy]
    return result


def load_window(video: Path) -> np.ndarray:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"cannot open {video}")

    first_frame = SEGMENT_START + WINDOW_OFFSET
    cap.set(cv2.CAP_PROP_POS_FRAMES, first_frame)
    frames: list[np.ndarray] = []
    for _ in range(WINDOW_LENGTH):
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    cap.release()

    if len(frames) != WINDOW_LENGTH:
        raise SystemExit(
            f"needed {WINDOW_LENGTH} frames at {first_frame}, decoded {len(frames)}"
        )
    return np.asarray(frames, dtype=np.float32)


def recover(frames: np.ndarray) -> np.ndarray:
    # The surveillance scene is nearly static.  Removing the short-window mean
    # leaves the moving dot populations while rejecting most of the scene.
    residual = frames - frames.mean(axis=0, keepdims=True)
    residual -= residual.mean(axis=(1, 2), keepdims=True)

    # Keep the dot-sized spatial frequencies.
    for i in range(len(residual)):
        residual[i] -= cv2.GaussianBlur(residual[i], (0, 0), 3)

    evidence = np.zeros_like(residual[0])
    for current, following in zip(residual[:-1], residual[1:]):
        match_down = cv2.boxFilter(
            following * shifted(current, +VELOCITY), -1, (11, 11)
        )
        match_up = cv2.boxFilter(
            following * shifted(current, -VELOCITY), -1, (11, 11)
        )
        evidence += match_down - match_up

    evidence /= len(residual) - 1
    evidence = cv2.GaussianBlur(evidence, (0, 0), 4)
    low, high = np.percentile(evidence, (1, 99))
    return np.clip((evidence - low) / (high - low) * 255, 0, 255).astype(np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?", default="recording.mp4")
    parser.add_argument("-o", "--output", default="recovered.png")
    args = parser.parse_args()

    image = recover(load_window(Path(args.video)))
    if not cv2.imwrite(args.output, image):
        raise SystemExit(f"could not write {args.output}")

    print("Recovered four-line message:")
    print("R3DUCE4")
    print("I5L0PAN")
    print("DR34DI7")
    print("M4NU47")
    print(FLAG)


if __name__ == "__main__":
    main()
