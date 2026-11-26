"""Stage: moving shots. For each shot, use a Wan 2.2 clip if one exists for the
current keyframe + motion prompt (generated on Kaggle, see kaggle/wan_i2v.py),
otherwise fall back to a Ken Burns move over the keyframe. Output: one square
1080x1080 24fps clip per shot, timed so the narration fits."""
from __future__ import annotations

import argparse
import json

from common import (OUTPUTS, cache_key, cached_path, ffmpeg, load_storyboard, rel,
                    wav_duration)
from keyframes import latest_keyframe
from narration import narration_path

FPS = 24
SIZE = 1080
NARRATION_PAD = 0.8  # seconds of breathing room after each line


def shot_duration(sb: dict, shot: dict) -> float:
    d = float(shot["duration_s"])
    if shot["narration"].strip():
        n = narration_path(sb, shot)
        if n.exists():
            d = max(d, wav_duration(n) + NARRATION_PAD)
    return round(d, 2)


def wan_clip_name(sb: dict, shot: dict, keyframe) -> str:
    key = cache_key(sb["models"]["video"], sb["models"].get("video_resolution", "480p"),
                    keyframe.name, shot["motion_prompt"], shot["seed"])
    return f"{shot['id']}_{key}.mp4"


def ken_burns(img: str, out: str, dur: float, move: str) -> None:
    n = int(dur * FPS)
    z = 1.15
    exprs = {
        "zoom-in":   (f"1+{z - 1}*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
        "zoom-out":  (f"{z}-{z - 1}*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
        "pan-right": (f"{z}", f"(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),
        "pan-left":  (f"{z}", f"(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),
    }
    zz, x, y = exprs[move]
    vf = (f"scale={SIZE * 4}:{SIZE * 4}:force_original_aspect_ratio=increase,crop={SIZE * 4}:{SIZE * 4},"
          f"zoompan=z='{zz}':x='{x}':y='{y}':d={n}:s={SIZE}x{SIZE}:fps={FPS},format=yuv420p")
    ffmpeg("-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(n),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS), out)


def conform_wan(clip: str, out: str, dur: float) -> None:
    """Trim the weak first 0.25s, crop to square, hold the last frame if short."""
    vf = (f"trim=start=0.25,setpts=PTS-STARTPTS,fps={FPS},"
          f"scale={SIZE}:{SIZE}:force_original_aspect_ratio=increase,crop={SIZE}:{SIZE},"
          f"tpad=stop_mode=clone:stop_duration={dur},format=yuv420p")
    ffmpeg("-i", clip, "-vf", vf, "-t", str(dur), "-an",
           "-c:v", "libx264", "-crf", "18", "-r", str(FPS), out)


def shot_clip_path(sb: dict, shot: dict):
    kf = latest_keyframe(sb, shot)
    wan = OUTPUTS / "clips" / wan_clip_name(sb, shot, kf)
    source = wan.name if wan.exists() else f"kenburns:{shot.get('ken_burns', 'zoom-in')}"
    dur = shot_duration(sb, shot)
    key = cache_key(kf.name, source, dur, SIZE, FPS)
    return cached_path("shots", shot["id"], key, "mp4"), kf, wan, dur


def export_jobs(sb: dict) -> None:
    """Write the job list the Kaggle notebook consumes."""
    jobs = []
    for shot in sb["shots"]:
        kf = latest_keyframe(sb, shot)
        jobs.append({"shot": shot["id"], "keyframe": kf.name, "motion_prompt": shot["motion_prompt"],
                     "seed": shot["seed"], "out": wan_clip_name(sb, shot, kf),
                     "resolution": sb["models"].get("video_resolution", "480p")})
    path = OUTPUTS / "wan_jobs.json"
    path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {rel(path)} ({len(jobs)} jobs). Upload it + outputs/keyframes/ to Kaggle.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--export-jobs", action="store_true", help="write outputs/wan_jobs.json for Kaggle")
    args = ap.parse_args()
    sb = load_storyboard()
    print("[shots]")
    if args.export_jobs:
        export_jobs(sb)
        return
    for shot in sb["shots"]:
        if args.only and shot["id"] not in args.only:
            continue
        out, kf, wan, dur = shot_clip_path(sb, shot)
        if not kf.exists():
            raise SystemExit(f"Missing keyframe for {shot['id']} - run keyframes first.")
        if out.exists() and not args.force:
            print(f"  {shot['id']}: cached ({out.name})")
            continue
        if wan.exists():
            conform_wan(rel(wan), rel(out), dur)
            print(f"  {shot['id']}: Wan clip -> {out.name} ({dur}s)")
        else:
            ken_burns(rel(kf), rel(out), dur, shot.get("ken_burns", "zoom-in"))
            print(f"  {shot['id']}: Ken Burns fallback -> {out.name} ({dur}s)")


if __name__ == "__main__":
    main()
