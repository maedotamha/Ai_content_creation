# Architecture

## The contract

`storyboard.json` is the only interface between stages. It is validated against `schema/storyboard.schema.json` at the start of **every** stage (`common.load_storyboard`), so a malformed storyboard stops the run before any model is called. The schema enforces:

- 8–12 shots, ids `s01`…`s12`, a stated `reason` for every shot
- `shot_size` from a fixed vocabulary, a `seed` on every generative input
- narration in the film's language plus `narration_en` for subtitles
- an end card whose text must contain "AI"

Prompts and seeds live in the storyboard, not in code, so a run is reproducible and explainable from one file.

## Stages

| Stage | Script | Reads | Writes | Model / tool |
|---|---|---|---|---|
| narration | `pipeline/narration.py` | voice, shots[].narration | `outputs/narration/sNN_<hash>.wav` | Gemini TTS |
| keyframes | `pipeline/keyframes.py` | style_block, character, shots[].image_prompt, seed | `outputs/keyframes/{ref,sNN}_<hash>.png` | FLUX via Cloudflare Workers AI |
| shots | `pipeline/shots.py` | keyframe, motion_prompt, ken_burns, narration length | `outputs/shots/sNN_<hash>.mp4` (1080² 24 fps) | Wan 2.2 clip from `outputs/clips/`, else FFmpeg zoompan |
| music | `pipeline/music.py` | music.chosen | `outputs/music/score.wav` | ACE-Step candidate, else placeholder pad |
| assemble | `pipeline/assemble.py` | everything above | `outputs/final/film_{16x9,9x16}.mp4`, `radio_cut.mp4` | FFmpeg only |
| GPU jobs | `kaggle/wan_i2v.py`, `kaggle/acestep.py` | `outputs/wan_jobs.json`, `music_jobs.json` | clips/music + `runs_kaggle.jsonl` | Kaggle 2×T4 |

**Order:** narration runs first because **the voice sets the timing**. Each shot lasts `max(duration_s, narration length + 0.8 s)`, so pictures are cut to the voice, not the other way round.

**Why square keyframes and shots:** one 1:1 master serves both deliveries. Each aspect ratio places the square, uncropped, over a blurred and darkened copy of itself. Nothing important is ever cropped out of the vertical version, and the subject stays centred.

## Caching

Every generated file is named `<shot>_<sha256(inputs)[:12]>.<ext>`, where the hashed inputs are everything that affects the output:

| Stage | Hash inputs |
|---|---|
| narration | tts model, voice, style instruction, line |
| keyframes | image model, steps, full prompt (shot + character + style block), seed |
| Wan clip | video model, resolution, keyframe filename (itself a hash), motion prompt, seed |
| shot clip | keyframe filename, source (Wan clip name or Ken Burns move), duration, size, fps |

If the file exists, the stage skips it. Change one narration line and its hash changes: one TTS call, then that shot's duration and clip are rebuilt, and the assembly reruns (FFmpeg only, no model calls). Because the hashes chain, a keyframe change automatically invalidates its Wan clip and shot clip. Old versions stay on disk for comparison. `--force` ignores the cache, and `--only s03` limits a stage to some shots.

## Failure handling

- **Retries:** `common.call_model` retries each model call 3 times with exponential backoff (4 s, 8 s). It logs **every attempt**, including failures, to `runs.jsonl`.
- **Missing secrets:** a stage exits with a clear message naming the missing variable.
- **Missing upstream output:** for example, shots without a keyframe stops with "run keyframes first".
- **GPU stages:** the Kaggle scripts save each clip as soon as it finishes and skip existing ones, so a session timeout loses at most one clip. An OOM on one shot is logged and the loop continues.
- **Graceful degradation:** a missing Wan clip falls back to Ken Burns, and a missing chosen score falls back to a placeholder pad. The film always builds.

## Logging

`runs.jsonl` gets one line per model call:

```json
{"ts": "...", "stage": "keyframes", "shot": "s03", "model": "@cf/black-forest-labs/flux-1-schnell",
 "params": {"prompt": "...", "seed": 103, "steps": 8}, "seed": 103, "attempt": 1,
 "status": "ok", "latency_s": 2.4, "cost_usd_equiv": 0.0011}
```

Kaggle runs write `runs_kaggle.jsonl` (including `gpu_minutes`), which `run.py` merges into `runs.jsonl` exactly once.

## Audio chain (assemble)

1. Each narration WAV is placed at shot start + 0.2 s (`adelay`) and summed into a voice stem.
2. Voice is levelled to −16 LUFS and music to −22 LUFS first, so balance decisions are creative ones, not repairs.
3. Ducking: `sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500`, with the voice as the sidechain.
4. Two-pass `loudnorm` to **−14 LUFS integrated, −1 dBTP**. The measured values are saved to `outputs/build/loudness.json`.
5. Subtitles are generated from `narration_en`, wrapped at 40 characters, at most 2 lines per cue, and timed to the real narration length.
