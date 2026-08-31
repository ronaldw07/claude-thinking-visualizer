#!/usr/bin/env python3
"""Preview the overlay without touching Claude Code: python3 demo.py"""

import sys
import time

from powerup import SURGE_FRAMES, TIERS, render

CONTEXT = "Opus 5 · REPOSITORIES"
FRAME_DELAY = 0.09
HOLD = 0.7


def show(text, lines_to_clear):
    if lines_to_clear:
        sys.stdout.write("\033[{}A\033[J".format(lines_to_clear))
    sys.stdout.write(text + "\n")
    sys.stdout.flush()
    return text.count("\n") + 1


def play(sequence):
    lines = 0
    for previous, level in zip(sequence, sequence[1:]):
        for frame in range(SURGE_FRAMES, 0, -1):
            lines = show(render(level, previous, frame, CONTEXT), lines)
            time.sleep(FRAME_DELAY)
        lines = show(render(level, previous, 0, CONTEXT), lines)
        time.sleep(HOLD)


def main():
    keys = [tier["key"] for tier in TIERS]
    print("Powering up...\n")
    play(keys)
    print("\nAnd back down...\n")
    play(list(reversed(keys)))


if __name__ == "__main__":
    main()
