"""Shared helpers for every stage: storyboard loading + validation, content-hash
caching, retries with backoff, and one-line-per-model-call logging to runs.jsonl."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
STORYBOARD = ROOT / "storyboard.json"
SCHEMA = ROOT / "schema" / "storyboard.schema.json"
OUTPUTS = ROOT / "outputs"
RUNS_LOG = ROOT / "runs.jsonl"


# ---------------------------------------------------------------- env / secrets
def load_env() -> None:
    """Minimal .env loader so we don't need python-dotenv. Real env vars win."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def require_env(name: str) -> str:
    load_env()
    val = os.environ.get(name)
    if not val:
        raise SystemExit(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return val


# ---------------------------------------------------------------- storyboard
def load_storyboard(path: Path = STORYBOARD) -> dict:
    """Load storyboard.json and validate it against the JSON Schema. Every stage
    calls this first, so an invalid contract stops the run before any model call."""
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
    ids = [s["id"] for s in data["shots"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate shot ids: {ids}")
    return data


# ---------------------------------------------------------------- caching
def cache_key(*parts: Any) -> str:
    """Stable hash of everything that affects an output. Change any input
    (prompt, seed, model, params) and the key - and so the filename - changes."""
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def cached_path(stage: str, shot_id: str, key: str, ext: str) -> Path:
    d = OUTPUTS / stage
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{shot_id}_{key}.{ext}"


def stale_versions(path: Path) -> list[Path]:
    """Older outputs for the same shot (different hash) - kept for inspection."""
    shot_id = path.name.split("_")[0]
    return [p for p in path.parent.glob(f"{shot_id}_*{path.suffix}") if p != path]


# ---------------------------------------------------------------- logging
def log_call(**fields: Any) -> None:
    """Append one JSON line per model call (success or failure)."""
    fields.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    with RUNS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fields, ensure_ascii=False) + "\n")


def call_model(stage: str, shot: str, model: str, params: dict, fn: Callable[[], Any],
               cost_usd_equiv: float = 0.0, retries: int = 3, base_delay: float = 4.0) -> Any:
    """Run fn() with retries + exponential backoff, logging every attempt."""
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        t0 = time.time()
        try:
            result = fn()
            log_call(stage=stage, shot=shot, model=model, params=params,
                     seed=params.get("seed"), attempt=attempt, status="ok",
                     latency_s=round(time.time() - t0, 2), cost_usd_equiv=cost_usd_equiv)
            return result
        except Exception as e:  # noqa: BLE001 - we log and retry everything
            last_err = e
            log_call(stage=stage, shot=shot, model=model, params=params,
                     seed=params.get("seed"), attempt=attempt, status="error",
                     error=str(e)[:500], latency_s=round(time.time() - t0, 2))
            if attempt < retries:
                # Providers that rate-limit (HTTP 429) tell us how long to wait.
                delay = getattr(e, "retry_after", None) or base_delay * 2 ** (attempt - 1)
                print(f"  [{stage}/{shot}] attempt {attempt} failed: {e} - retrying in {delay:.0f}s")
                time.sleep(delay)
    raise RuntimeError(f"{stage}/{shot} failed after {retries} attempts: {last_err}")


# ---------------------------------------------------------------- ffmpeg
def ffmpeg_bin() -> str:
    """FFMPEG env var > ffmpeg on PATH > the binary bundled with imageio-ffmpeg."""
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg(*args: str, loglevel: str = "error") -> subprocess.CompletedProcess:
    cmd = [ffmpeg_bin(), "-hide_banner", "-nostats", "-loglevel", loglevel, "-y", *args]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd)}\n{res.stderr[-2000:]}")
    return res


def wav_duration(path: Path) -> float:
    import wave
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def rel(p: Path) -> str:
    """Path relative to repo root with forward slashes (safe inside ffmpeg filters)."""
    return p.resolve().relative_to(ROOT).as_posix()
