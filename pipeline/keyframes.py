"""Stage: keyframes. One character reference sheet, then one keyframe per shot,
via Cloudflare Workers AI (FLUX). With FLUX.2 klein the reference sheet is passed
as input_image_0 for every shot that shows the character, for consistency.
Cached by hash of (model, steps, full prompt, seed, reference file)."""
from __future__ import annotations

import argparse
import base64

import requests

from common import cache_key, cached_path, call_model, load_storyboard, require_env

# Rough list-price equivalent per image (USD) for COSTS.md. Update with what you find.
COST_PER_IMAGE = 0.0011
SIZE = 1024


def full_prompt(sb: dict, body: str, with_character: bool) -> str:
    parts = [body]
    if with_character:
        parts.append(sb["character"]["description"])
    parts.append(sb["style_block"])
    return ", ".join(parts)


def generate(model: str, prompt: str, seed: int, steps: int, ref: bytes | None = None) -> bytes:
    account = require_env("CLOUDFLARE_ACCOUNT_ID")
    token = require_env("CLOUDFLARE_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {token}"}
    if "flux-2" in model:
        # FLUX.2 on Workers AI takes multipart form data and accepts reference images.
        fields = {"prompt": prompt, "seed": str(seed), "width": str(SIZE), "height": str(SIZE)}
        files = {"input_image_0": ("ref.png", ref, "image/png")} if ref else {"_": (None, "")}
        r = requests.post(url, headers=headers, data=fields, files=files, timeout=180)
    else:
        # FLUX.1 schnell: JSON, prompt + steps only (no seed - see FAILURES.md).
        r = requests.post(url, headers=headers, json={"prompt": prompt, "steps": steps}, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    if r.headers.get("content-type", "").startswith("image/"):
        return r.content
    img = (r.json().get("result") or {}).get("image")
    if not img:
        raise RuntimeError(f"No image in response: {r.text[:300]}")
    return base64.b64decode(img)


def _key(sb: dict, prompt: str, seed: int, ref_name: str | None) -> str:
    return cache_key(sb["models"]["image"], sb["models"].get("image_steps", 4), prompt, seed, ref_name)


def reference_path(sb: dict):
    ch = sb["character"]
    prompt = full_prompt(sb, ch["reference_prompt"], True)
    return cached_path("keyframes", "ref", _key(sb, prompt, ch["seed"], None), "png")


def latest_keyframe(sb: dict, shot: dict):
    """Path of the keyframe matching the current storyboard for this shot."""
    uses = shot.get("uses_character", True)
    prompt = full_prompt(sb, shot["image_prompt"], uses)
    ref = reference_path(sb).name if uses and "flux-2" in sb["models"]["image"] else None
    return cached_path("keyframes", shot["id"], _key(sb, prompt, shot["seed"], ref), "png")


def render(sb: dict, shot_id: str, prompt: str, seed: int, out, ref_path, force: bool) -> None:
    if out.exists() and not force:
        print(f"  {shot_id}: cached ({out.name})")
        return
    model = sb["models"]["image"]
    steps = sb["models"].get("image_steps", 4)
    ref = ref_path.read_bytes() if ref_path else None
    params = {"prompt": prompt, "seed": seed, "steps": steps,
              "reference": ref_path.name if ref_path else None}
    img = call_model("keyframes", shot_id, model, params,
                     lambda: generate(model, prompt, seed, steps, ref), cost_usd_equiv=COST_PER_IMAGE)
    out.write_bytes(img)
    print(f"  {shot_id}: generated -> {out.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="shot ids to render, 'ref' for the reference sheet")
    ap.add_argument("--force", action="store_true", help="ignore cache")
    args = ap.parse_args()
    sb = load_storyboard()
    print("[keyframes]")
    ch = sb["character"]
    ref = reference_path(sb)
    if not args.only or "ref" in args.only:
        render(sb, "ref", full_prompt(sb, ch["reference_prompt"], True), ch["seed"], ref, None, args.force)
    use_ref = "flux-2" in sb["models"]["image"]
    for shot in sb["shots"]:
        if args.only and shot["id"] not in args.only:
            continue
        uses = shot.get("uses_character", True)
        render(sb, shot["id"], full_prompt(sb, shot["image_prompt"], uses), shot["seed"],
               latest_keyframe(sb, shot), ref if (uses and use_ref) else None, args.force)


if __name__ == "__main__":
    main()
