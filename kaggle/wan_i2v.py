"""Kaggle notebook script: Wan 2.2 TI2V-5B image-to-video for every job in wan_jobs.json.

Setup on Kaggle (GPU T4 x2, Internet ON):
  1. Locally:  python pipeline/shots.py --export-jobs
  2. Upload outputs/wan_jobs.json and outputs/keyframes/*.png as a Kaggle dataset.
  3. In a cell:  !pip install -q -U diffusers transformers accelerate ftfy imageio imageio-ffmpeg
  4. Set JOBS / KEYFRAMES below, run:  !python wan_i2v.py
  5. Download /kaggle/working/clips/ (mp4s + runs_kaggle.jsonl) into outputs/clips/ locally.
  6. Re-run `make film` - shots.py picks up any clip whose name matches the current storyboard.

VERIFY ON FIRST RUN: diffusers class/model id below match the current Wan 2.2 docs
(https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B). The script saves each clip as soon as it
finishes and skips existing ones, so a session timeout loses at most one clip.
"""
import json
import os
import time
from pathlib import Path

import torch
from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
from diffusers.utils import export_to_video
from PIL import Image

JOBS = Path(os.environ.get("JOBS", "/kaggle/input/film-jobs/wan_jobs.json"))
KEYFRAMES = Path(os.environ.get("KEYFRAMES", "/kaggle/input/film-jobs"))
OUT = Path("/kaggle/working/clips")
MODEL = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
SIZES = {"480p": (480, 480), "720p": (704, 704)}  # square: one crop serves both aspect ratios
FRAMES = 121       # ~5 s at 24 fps (must be 4k+1)
STEPS = int(os.environ.get("STEPS", 30))
GPU_USD_PER_HOUR = 0.35  # list-price equivalent of a T4, for COSTS.md
NEGATIVE = "blurry, distorted face, extra fingers, morphing, flicker, text, watermark, fast motion"

OUT.mkdir(parents=True, exist_ok=True)
log = OUT / "runs_kaggle.jsonl"

dtype = torch.float16  # T4 has no fast bf16
vae = AutoencoderKLWan.from_pretrained(MODEL, subfolder="vae", torch_dtype=torch.float32)
pipe = WanImageToVideoPipeline.from_pretrained(MODEL, vae=vae, torch_dtype=dtype)
pipe.enable_model_cpu_offload()   # needed to fit in 16 GB
pipe.vae.enable_tiling()

for job in json.loads(JOBS.read_text()):
    out = OUT / job["out"]
    if out.exists():
        print("skip", out.name)
        continue
    w, h = SIZES[job.get("resolution", "480p")]
    img = Image.open(KEYFRAMES / job["keyframe"]).convert("RGB").resize((w, h))
    params = {"motion_prompt": job["motion_prompt"], "w": w, "h": h, "frames": FRAMES,
              "steps": STEPS, "guidance": 5.0}
    t0 = time.time()
    status, err = "ok", None
    try:
        frames = pipe(image=img, prompt=job["motion_prompt"], negative_prompt=NEGATIVE,
                      height=h, width=w, num_frames=FRAMES, num_inference_steps=STEPS,
                      guidance_scale=5.0,
                      generator=torch.Generator("cpu").manual_seed(job["seed"])).frames[0]
        export_to_video(frames, str(out), fps=24)
    except Exception as e:  # OOM etc. - log and continue with the next shot
        status, err = "error", str(e)[:500]
        torch.cuda.empty_cache()
    dt = time.time() - t0
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "stage": "shots", "shot": job["shot"],
           "model": MODEL, "params": params, "seed": job["seed"], "status": status,
           "latency_s": round(dt, 1), "gpu_minutes": round(dt / 60, 2), "gpu": "T4",
           "cost_usd_equiv": round(dt / 3600 * GPU_USD_PER_HOUR, 4)}
    if err:
        rec["error"] = err
    with log.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(job["shot"], status, f"{dt:.0f}s")
