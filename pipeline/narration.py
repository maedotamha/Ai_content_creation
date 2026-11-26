"""Stage: narration. One WAV per shot via Gemini TTS. Cached by hash of
(model, voice, style, line). Change one line -> only that shot re-generates."""
from __future__ import annotations

import argparse
import base64
import re
import time
import wave

import requests

from common import cache_key, cached_path, call_model, load_storyboard, require_env

SAMPLE_RATE = 24000  # Gemini TTS returns 16-bit mono PCM at 24 kHz
MIN_INTERVAL_S = 21  # free tier allows only a few TTS requests per minute - pace below 3 RPM
_last_call = [0.0]


class RateLimited(RuntimeError):
    def __init__(self, msg: str, retry_after: float):
        super().__init__(msg)
        self.retry_after = retry_after


def _pace() -> None:
    wait = MIN_INTERVAL_S - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()


def tts(model: str, voice: str, text: str, style: str | None = None) -> bytes:
    """`text` is spoken; `style` goes in systemInstruction so it is NOT read aloud
    (Gemini 3.8 TTS spoke an inline style prefix - see FAILURES.md F7)."""
    _pace()
    key = require_env("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    # Gemini 3.8 TTS reads inline instructions aloud (F7) and 3.8 Lite rejects
    # systemInstruction (F8), so the request carries ONLY the line to be spoken.
    r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=180)
    if r.status_code == 429:
        m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', r.text)
        raise RateLimited(f"HTTP 429 rate limited: {r.text[:200]}", float(m.group(1)) + 2 if m else 60)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    try:
        b64 = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"No audio in response: {r.text[:300]}") from e
    return base64.b64decode(b64)


def write_wav(path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)


def narration_path(sb: dict, shot: dict):
    model, v = shot.get("tts_model", sb["models"]["tts"]), sb["voice"]
    return cached_path("narration", shot["id"],
                       cache_key(model, v["name"], v["style"], shot["narration"]), "wav")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    sb = load_storyboard()
    model, v = sb["models"]["tts"], sb["voice"]
    print("[narration]")
    for shot in sb["shots"]:
        if args.only and shot["id"] not in args.only:
            continue
        if not shot["narration"].strip():
            print(f"  {shot['id']}: no narration")
            continue
        model = shot.get("tts_model", sb["models"]["tts"])
        out = narration_path(sb, shot)
        if out.exists() and not args.force:
            print(f"  {shot['id']}: cached ({out.name})")
            continue
        text = shot["narration"]
        params = {"voice": v["name"], "text": text, "system_instruction": v["style"],
                  "language": sb["language"]}
        pcm = call_model("narration", shot["id"], model, params,
                         lambda: tts(model, v["name"], text, v["style"]), retries=5)
        write_wav(out, pcm)
        secs = len(pcm) / 2 / SAMPLE_RATE
        # Sanity check: Amharic narration here runs ~1.5-2.5 words/s. Far longer means the
        # model added speech (spoke the instruction, or continued the story).
        expected = len(text.split()) / 1.5
        flag = "  <-- WARNING: much longer than expected, listen to it" if secs > 2 * expected + 2 else ""
        print(f"  {shot['id']}: generated -> {out.name} ({secs:.1f}s, expected <= {expected:.1f}s){flag}")


if __name__ == "__main__":
    main()
