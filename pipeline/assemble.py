"""Stage: assembly (FFmpeg only, deterministic). Builds the timeline from the
storyboard, lays narration on it, ducks the score under the voice, normalises
loudness to -14 LUFS / -1 dBTP, burns in English subtitles, appends the AI end
card and exports 16:9 and 9:16. `--radio` makes the radio cut (black screen)."""
from __future__ import annotations

import argparse
import json
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont

from common import OUTPUTS, ffmpeg, load_storyboard, rel, wav_duration
from music import SCORE
from narration import narration_path
from shots import FPS, shot_clip_path, shot_duration

BUILD = OUTPUTS / "build"
FINAL = OUTPUTS / "final"
LINE_DELAY = 0.2  # narration starts this long after the cut
ASPECTS = {"16x9": (1920, 1080, 16), "9x16": (1080, 1920, 9)}  # w, h, subtitle font size


# ---------------------------------------------------------------- timeline
def timeline(sb: dict) -> list[dict]:
    t, rows = 0.0, []
    for shot in sb["shots"]:
        d = shot_duration(sb, shot)
        rows.append({"shot": shot, "start": round(t, 3), "dur": d})
        t += d
    return rows


# ---------------------------------------------------------------- audio
def build_voice(sb: dict, tl: list[dict], total: float):
    inputs, chains, labels = [], [], []
    for row in tl:
        if not row["shot"]["narration"].strip():
            continue
        p = narration_path(sb, row["shot"])
        if not p.exists():
            raise SystemExit(f"Missing narration for {row['shot']['id']} - run narration first.")
        idx = len(inputs) // 2
        inputs += ["-i", rel(p)]
        ms = int((row["start"] + LINE_DELAY) * 1000)
        chains.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{idx}]")
        labels.append(f"[v{idx}]")
    out = BUILD / "voice.wav"
    graph = ";".join(chains) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad=whole_dur={total}[out]"
    ffmpeg(*inputs, "-filter_complex", graph, "-map", "[out]", "-t", str(total), rel(out))
    return out


def mix(sb: dict, voice, total: float):
    """Level-match the sources, duck music under voice, then 2-pass loudnorm."""
    vol = sb["music"].get("volume", 0.6)
    premix = BUILD / "premix.wav"
    graph = (
        f"[0:a]loudnorm=I=-16:TP=-2,aresample=48000,asplit=2[voice][sc];"
        f"[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total},"
        f"loudnorm=I=-22:TP=-3,volume={vol},afade=t=out:st={max(total - 3, 0)}:d=3[music];"
        f"[music][sc]sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500[ducked];"
        f"[voice][ducked]amix=inputs=2:normalize=0[out]"
    )
    ffmpeg("-i", rel(voice), "-stream_loop", "-1", "-i", rel(SCORE), "-filter_complex", graph,
           "-map", "[out]", "-t", str(total), "-ar", "48000", rel(premix))
    # pass 1: measure
    res = ffmpeg("-i", rel(premix), "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
                 "-f", "null", "-", loglevel="info")
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S).group(0))
    # pass 2: apply
    final = BUILD / "mix.wav"
    af = (f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}:linear=true")
    ffmpeg("-i", rel(premix), "-af", af, "-ar", "48000", rel(final))
    (BUILD / "loudness.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
    return final


# ---------------------------------------------------------------- subtitles
def ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)):03}"


def build_srt(sb: dict, tl: list[dict]):
    cues = []
    for row in tl:
        text = row["shot"]["narration_en"].strip()
        if not text:
            continue
        p = narration_path(sb, row["shot"])
        speech = wav_duration(p) if p.exists() else row["dur"] - 0.5
        lines = textwrap.wrap(text, 40)
        chunks = ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
        total_chars = sum(len(c) for c in chunks)
        t = row["start"] + LINE_DELAY
        for c in chunks:
            d = speech * len(c) / total_chars
            cues.append((t, t + d, c))
            t += d
    out = BUILD / "subs.srt"
    out.write_text("\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{c}\n" for i, (a, b, c) in enumerate(cues, 1)),
                   encoding="utf-8")
    return out


# ---------------------------------------------------------------- end card
def font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf", "Arial.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def end_card(sb: dict, w: int, h: int):
    img = Image.new("RGB", (w, h), (12, 10, 8))
    d = ImageDraw.Draw(img)
    lines = sb["end_card"]["text"].split("\n")
    big, small = font(int(w * 0.07)), font(int(w * 0.03))
    fonts = [big] + [small] * (len(lines) - 1)
    heights = [d.textbbox((0, 0), ln, font=f)[3] for ln, f in zip(lines, fonts)]
    y = (h - sum(heights) - 30 * (len(lines) - 1)) / 2
    for ln, f, lh in zip(lines, fonts, heights):
        tw = d.textlength(ln, font=f)
        d.text(((w - tw) / 2, y), ln, font=f, fill=(240, 228, 210))
        y += lh + 30
    out = BUILD / f"endcard_{w}x{h}.png"
    img.save(out)
    return out


# ---------------------------------------------------------------- video
def concat_square(tl: list[dict], sb: dict):
    inputs = []
    for row in tl:
        p, *_ = shot_clip_path(sb, row["shot"])
        if not p.exists():
            raise SystemExit(f"Missing shot clip for {row['shot']['id']} - run shots first.")
        inputs += ["-i", rel(p)]
    n = len(tl)
    graph = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    out = BUILD / "master_square.mp4"
    ffmpeg(*inputs, "-filter_complex", graph, "-map", "[v]", "-c:v", "libx264", "-crf", "18",
           "-r", str(FPS), rel(out))
    return out


def export(sb: dict, master, audio, srt, body_dur: float, name: str, w: int, h: int, fs: int):
    card = end_card(sb, w, h)
    cd = sb["end_card"]["duration_s"]
    margin = 70 if h > w else 30
    style = f"FontName=Arial,FontSize={fs},Outline=2,Shadow=0,BorderStyle=1,MarginV={margin}"
    graph = (
        f"[0:v]split[a][b];"
        f"[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=30:3,eq=brightness=-0.15[bg];"
        f"[b]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,subtitles={rel(srt)}:force_style='{style}',"
        f"trim=0:{body_dur},setpts=PTS-STARTPTS,fps={FPS},format=yuv420p[body];"
        f"[1:v]fps={FPS},scale={w}:{h},format=yuv420p,fade=t=in:d=0.5[card];"
        f"[body][card]concat=n=2:v=1:a=0[v]"
    )
    out = FINAL / f"film_{name}.mp4"
    ffmpeg("-i", rel(master), "-loop", "1", "-t", str(cd), "-i", rel(card), "-i", rel(audio),
           "-filter_complex", graph, "-map", "[v]", "-map", "2:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", rel(out))
    print(f"  wrote {rel(out)}")


def radio_cut(audio, srt, total: float):
    out = FINAL / "radio_cut.mp4"
    ffmpeg("-f", "lavfi", "-i", f"color=c=black:s=720x720:r={FPS}:d={total}", "-i", rel(audio),
           "-vf", f"subtitles={rel(srt)}:force_style='FontName=Arial,FontSize=14'",
           "-c:v", "libx264", "-crf", "28", "-c:a", "aac", "-b:a", "192k", "-shortest", rel(out))
    print(f"  wrote {rel(out)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--radio", action="store_true", help="radio cut: narration + music on black")
    args = ap.parse_args()
    sb = load_storyboard()
    BUILD.mkdir(parents=True, exist_ok=True)
    FINAL.mkdir(parents=True, exist_ok=True)
    print("[assemble]")
    tl = timeline(sb)
    body = sum(r["dur"] for r in tl)
    total = round(body + sb["end_card"]["duration_s"], 3)
    voice = build_voice(sb, tl, total)
    audio = mix(sb, voice, total)
    srt = build_srt(sb, tl)
    (BUILD / "timeline.json").write_text(json.dumps(
        [{"shot": r["shot"]["id"], "start": r["start"], "dur": r["dur"]} for r in tl], indent=2),
        encoding="utf-8")
    print(f"  timeline: {len(tl)} shots, {body:.1f}s + end card = {total:.1f}s")
    if not 60 <= total <= 90:
        print(f"  WARNING: film is {total:.1f}s - the brief asks for 60-90s")
    if args.radio:
        radio_cut(audio, srt, total)
        return
    master = concat_square(tl, sb)
    for name, (w, h, fs) in ASPECTS.items():
        export(sb, master, audio, srt, body, name, w, h, fs)


if __name__ == "__main__":
    main()
