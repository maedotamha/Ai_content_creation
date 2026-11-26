# Failures

Write one entry **the moment** something breaks. Real blockers count: quota, memory, consistency, language, tools that moved.

## Template

### F#: short title
- **When / stage:**
- **What broke:** (exact error text, `runs.jsonl` line)
- **What I tried:** 1. … 2. …
- **What fixed it / workaround:**
- **Lesson:**

---

### F1: No FFmpeg on the Windows machine
- **Stage:** setup / assemble
- **What broke:** `ffmpeg : The term 'ffmpeg' is not recognized`
- **Fix:** depend on `imageio-ffmpeg`, which ships a static FFmpeg binary. `common.ffmpeg_bin()` prefers `$FFMPEG`, then `ffmpeg` on PATH, then the bundled binary. A clean clone needs only `pip install -r requirements.txt`.
- **Lesson:** reproducibility means removing system prerequisites, not documenting them.

### F2: Loudness measurement returned nothing
- **Stage:** assemble
- **What broke:** the two-pass `loudnorm` regex found no JSON, because FFmpeg ran with `-loglevel error` and loudnorm prints its measurements at info level.
- **Fix:** `ffmpeg(..., loglevel="info")` for the measurement pass only.

### F3:
