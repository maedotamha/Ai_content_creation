"""Call each hosted provider once and log latency to runs.jsonl.
Run this first:  python pipeline/smoke_test.py"""
from __future__ import annotations

from common import OUTPUTS, call_model, ffmpeg_bin, load_storyboard
from keyframes import generate
from narration import tts, write_wav


def main() -> None:
    sb = load_storyboard()
    print("storyboard schema: OK")
    print(f"ffmpeg: {ffmpeg_bin()}")
    smoke = OUTPUTS / "smoke"
    smoke.mkdir(parents=True, exist_ok=True)

    m = sb["models"]["image"]
    try:
        img = call_model("smoke", "image", m, {"prompt": "a red apple", "seed": 1, "steps": 4},
                         lambda: generate(m, "a red apple on a wooden table", 1, 4), retries=1)
        (smoke / "image.png").write_bytes(img)
        print(f"Cloudflare {m}: OK")
    except Exception as e:  # noqa: BLE001
        print(f"Cloudflare {m}: FAILED - {e}")

    m = sb["models"]["tts"]
    try:
        pcm = call_model("smoke", "tts", m, {"text": "hello", "voice": sb["voice"]["name"]},
                         lambda: tts(m, sb["voice"]["name"], "Say warmly: Hello, this is a test."), retries=1)
        write_wav(smoke / "tts.wav", pcm)
        print(f"Gemini {m}: OK")
    except Exception as e:  # noqa: BLE001
        print(f"Gemini {m}: FAILED - {e}")

    print("results logged in runs.jsonl; outputs in outputs/smoke/")


if __name__ == "__main__":
    main()
