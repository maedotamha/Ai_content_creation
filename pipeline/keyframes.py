"""Stage: keyframes. One character reference image, then one keyframe per shot,
via Cloudflare Workers AI (FLUX). Cached by hash of (model, steps, full prompt, seed)."""
from __future__ import annotations

import argparse
import base64

import requests

from common import cache_key, cached_path, call_model, load_storyboard, require_env

# Rough list-price equivalent per image (USD) for COSTS.md. Update with what you find.
COST_PER_IMAGE = 0.0011


def full_prompt(sb: dict, body: str, with_character: bool) -> str:
    parts = [body]
    if with_character:
        parts.append(sb["character"]["description"])
    parts.append(sb["style_block"])
    return ", ".join(parts)


def generate(model: str, prompt: str, seed: int, steps: int) -> bytes:
    account = require_env("CLOUDFLARE_ACCOUNT_ID")
    token = require_env("CLOUDFLARE_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                      json={"prompt": prompt, "seed": seed, "steps": steps}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    ctype = r.headers.get("content-type", "")
    if ctype.startswith("image/"):
        return r.content
    data = r.json()
    img = (data.get("result") or {}).get("image")
    if not img:
        raise RuntimeError(f"No image in response: {str(data)[:300]}")
    return base64.b64decode(img)


def render(sb: dict, shot_id: str, body: str, seed: int, with_character: bool, force: bool) -> None:
    model = sb["models"]["image"]
    steps = sb["models"].get("image_steps", 4)
    prompt = full_prompt(sb, body, with_character)
    key = cache_key(model, steps, prompt, seed)
    out = cached_path("keyframes", shot_id, key, "png")
    if out.exists() and not force:
        print(f"  {shot_id}: cached ({out.name})")
        return
    params = {"prompt": prompt, "seed": seed, "steps": steps}
    img = call_model("keyframes", shot_id, model, params,
                     lambda: generate(model, prompt, seed, steps), cost_usd_equiv=COST_PER_IMAGE)
    out.write_bytes(img)
    print(f"  {shot_id}: generated -> {out.name}")


def latest_keyframe(sb: dict, shot: dict):
    """Path of the keyframe matching the current storyboard for this shot."""
    model = sb["models"]["image"]
    steps = sb["models"].get("image_steps", 4)
    prompt = full_prompt(sb, shot["image_prompt"], shot.get("uses_character", True))
    return cached_path("keyframes", shot["id"], cache_key(model, steps, prompt, shot["seed"]), "png")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="shot ids to render (default: all)")
    ap.add_argument("--force", action="store_true", help="ignore cache")
    args = ap.parse_args()
    sb = load_storyboard()
    print("[keyframes]")
    ch = sb["character"]
    if not args.only or "ref" in args.only:
        render(sb, "ref", ch["reference_prompt"], ch["seed"], True, args.force)
    for shot in sb["shots"]:
        if args.only and shot["id"] not in args.only:
            continue
        render(sb, shot["id"], shot["image_prompt"], shot["seed"],
               shot.get("uses_character", True), args.force)


if __name__ == "__main__":
    main()
