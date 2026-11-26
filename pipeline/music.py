"""Stage: music. ACE-Step runs on Kaggle (kaggle/acestep.py) and its candidates
land in outputs/music/. This stage resolves the score for assembly:
  - storyboard music.chosen set and the file exists -> use it
  - otherwise -> a quiet synthesised placeholder pad (logged as such)"""
from __future__ import annotations

import argparse
import json
import shutil

from common import OUTPUTS, ffmpeg, load_storyboard, rel

SCORE = OUTPUTS / "music" / "score.wav"


def placeholder(out, dur: float) -> None:
    """Soft D-minor pad with slow tremolo - a temp track, not the final score."""
    chord = "+".join(f"0.18*sin(2*PI*{f}*t)" for f in (146.83, 174.61, 220.0, 293.66))
    ffmpeg("-f", "lavfi", "-i", f"aevalsrc='{chord}':s=48000:d={dur}",
           "-af", f"tremolo=f=0.2:d=0.4,lowpass=f=1200,afade=t=in:d=3,afade=t=out:st={dur - 4}:d=4",
           "-ac", "2", rel(out))


def export_jobs(sb: dict) -> None:
    m = sb["music"]
    path = OUTPUTS / "music_jobs.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {rel(path)} - upload to Kaggle with kaggle/acestep.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-jobs", action="store_true")
    ap.add_argument("--duration", type=float, help="placeholder length (set by run.py)")
    args = ap.parse_args()
    sb = load_storyboard()
    print("[music]")
    if args.export_jobs:
        export_jobs(sb)
        return
    SCORE.parent.mkdir(parents=True, exist_ok=True)
    chosen = sb["music"].get("chosen")
    if chosen and (OUTPUTS / "music" / chosen).exists():
        src = OUTPUTS / "music" / chosen
        if src.suffix == ".wav":
            shutil.copyfile(src, SCORE)
        else:
            ffmpeg("-i", rel(src), "-ar", "48000", "-ac", "2", rel(SCORE))
        print(f"  using chosen score {chosen}")
    else:
        dur = args.duration or sb["music"]["duration_s"]
        placeholder(SCORE, dur)
        print(f"  no chosen ACE-Step track - placeholder pad ({dur:.0f}s)")


if __name__ == "__main__":
    main()
