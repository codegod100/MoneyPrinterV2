#!/usr/bin/env python3
import argparse

from recovery import recover_last_video


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover the last generated video from .mp artifacts.")
    parser.add_argument("--wav", help="Optional path to a specific WAV file")
    parser.add_argument("--window-minutes", type=int, default=120, help="How far back to look for PNGs before the WAV timestamp")
    parser.add_argument("--output", help="Optional output MP4 path")
    args = parser.parse_args()

    recover_last_video(
        wav_path=args.wav,
        output_path=args.output,
        window_minutes=args.window_minutes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
