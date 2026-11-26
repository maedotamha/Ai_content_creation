"""Kaggle notebook script: ACE-Step 1.5 score candidates from music_jobs.json.

Setup on Kaggle (GPU, Internet ON):
  1. Locally:  python pipeline/music.py --export-jobs   -> outputs/music_jobs.json
  2. Upload it; in a cell:
       !git clone https://github.com/ACE-Step/ACE-Step-1.5 && pip install -q -e ACE-Step-1.5
  3. !python acestep.py
  4. Download /kaggle/working/music/ into outputs/music/ locally, listen to the candidates
     UNDER THE NARRATION at low volume, then set "music.chosen" in storyboard.json to the
     file you picked and log why in EXPERIMENTS.md.

ADAPT `generate_track` to the current ACE-Step 1.5 inference API (see the repo README).
Everything else - looping over seeds, timing, logging, naming - is done.
"""
import json
import os
import time
from pathlib import Path

JOBS = Path(os.environ.get("JOBS", "/kaggle/input/film-jobs/music_jobs.json"))
OUT = Path("/kaggle/working/music")
MODEL = "ACE-Step-1.5"
GPU_USD_PER_HOUR = 0.35
OUT.mkdir(parents=True, exist_ok=True)
log = OUT / "runs_kaggle.jsonl"


def generate_track(caption: str, duration: float, bpm: int, key: str, seed: int, out: Path) -> None:
    """TODO: call ACE-Step 1.5 here. Keep tempo/key in the metadata args, not the caption,
    and pass the instrumental flag so no vocals appear. Write a WAV to `out`."""
    raise NotImplementedError("Wire this to the ACE-Step 1.5 API from its README")


job = json.loads(JOBS.read_text())
for seed in job.get("seeds") or list(range(job["candidates"])):
    out = OUT / f"score_seed{seed}.wav"
    if out.exists():
        continue
    params = {"caption": job["caption"], "duration": job["duration_s"], "bpm": job["bpm"],
              "key": job.get("key"), "instrumental": True}
    t0, status, err = time.time(), "ok", None
    try:
        generate_track(job["caption"], job["duration_s"], job["bpm"], job.get("key"), seed, out)
    except Exception as e:
        status, err = "error", str(e)[:500]
    dt = time.time() - t0
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "stage": "music", "shot": f"seed{seed}",
           "model": MODEL, "params": params, "seed": seed, "status": status,
           "latency_s": round(dt, 1), "gpu_minutes": round(dt / 60, 2),
           "cost_usd_equiv": round(dt / 3600 * GPU_USD_PER_HOUR, 4)}
    if err:
        rec["error"] = err
    with log.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(seed, status, f"{dt:.1f}s")
