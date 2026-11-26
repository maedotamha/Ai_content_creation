# Before the Bell (ደወሉ ሳይደወል)

> A schoolgirl in Ethiopia races through her morning (lost shoe, missed breakfast, the departing service bus) and arrives just in time to stand with everyone and sing the national anthem. A ~70 s short film narrated in **Amharic** with English subtitles, made by a code pipeline from one file: `storyboard.json`.

**Watch:** [vertical 9:16](LINK) · [horizontal 16:9](LINK) · [walkthrough](LINK) · [post](LINK)

## Run it

```bash
git clone <this repo> && cd <repo>
pip install -r requirements.txt        # FFmpeg comes bundled via imageio-ffmpeg
cp .env.example .env                   # add GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
make film                              # or: python pipeline/run.py
```

Output: `outputs/final/film_9x16.mp4` and `outputs/final/film_16x9.mp4`.

Other commands:

| Command | What it does |
|---|---|
| `make smoke` | Calls each hosted provider once and logs latency |
| `make validate` | Validates `storyboard.json` against `schema/storyboard.schema.json` |
| `make radio` | Radio cut: narration + score on black, with subtitles |
| `make wan-jobs` / `make music-jobs` | Exports job files for the Kaggle GPU notebooks in `kaggle/` |
| `python pipeline/<stage>.py --only s03 --force` | Regenerates one shot of one stage |

## What it does

```
storyboard.json ─► narration ─► keyframes ─► shots ─► music ─► assemble ─► film_9x16.mp4 / film_16x9.mp4
 (validated)      Gemini TTS   FLUX (CF)    Wan 2.2    ACE-Step  FFmpeg
                  1 wav/shot   1 png/shot   or Ken     (Kaggle)  duck, loudnorm,
                                            Burns                subtitles, end card
```

Every output's filename contains a hash of its inputs, so editing one line in `storyboard.json` regenerates only that shot. Every model call is logged to `runs.jsonl`. See [ARCHITECTURE.md](ARCHITECTURE.md).

**Wan 2.2 and ACE-Step need a GPU** and run on Kaggle (`kaggle/`). Their outputs are committed in `outputs/clips/` and `outputs/music/`, so `make film` on a clean clone reuses them. If a Wan clip is missing, that shot falls back to a Ken Burns move over its keyframe.

## What it costs

Measured numbers are in [COSTS.md](COSTS.md). Summary: **$0 actually paid**, about **$X list-price equivalent**, about **N T4 GPU minutes**.

## Docs

[DESIGN](DESIGN.md) · [ARCHITECTURE](ARCHITECTURE.md) · [EXPERIMENTS](EXPERIMENTS.md) · [FAILURES](FAILURES.md) · [COSTS](COSTS.md) · [ETHICS](ETHICS.md)
