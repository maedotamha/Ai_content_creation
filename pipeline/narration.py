"""Stage: narration. One WAV per shot via Gemini TTS. Cached by hash of
(model, voice, style, line). Change one line -> only that shot re-generates."""
from __future__ import annotations

import argparse
import base64
import wave

import requests

from common import cache_key, cached_path, call_model, load_storyboard, require_env

SAMPLE_RATE = 24000  # Gemini TTS returns 16-bit mono PCM at 24 kHz


def tts(model: str, voice: str, text: str) -> bytes:
    key = require_env("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=180)
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
    model, v = sb["models"]["tts"], sb["voice"]
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
        out = narration_path(sb, shot)
        if out.exists() and not args.force:
            print(f"  {shot['id']}: cached ({out.name})")
            continue
        prompt = f"{v['style']} {shot['narration']}"
        params = {"voice": v["name"], "text": prompt, "language": sb["language"]}
        pcm = call_model("narration", shot["id"], model, params, lambda: tts(model, v["name"], prompt))
        write_wav(out, pcm)
        print(f"  {shot['id']}: generated -> {out.name} ({len(pcm) / 2 / SAMPLE_RATE:.1f}s)")


if __name__ == "__main__":
    main()
