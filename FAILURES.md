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

### F3: Cloudflare FLUX.1 schnell rejects `seed`
- **Stage:** smoke test, keyframes
- **What broke:** `HTTP 400: AiError: Bad input: Additional or unevaluated properties '/seed' at '/' not allowed` (`runs.jsonl`, smoke/image)
- **What I tried:** fetched the model's input schema from `/ai/models/schema`. schnell accepts only `prompt` and `steps` (max 8), so there's no seed and no reference image.
- **Fix:** listed the available text-to-image models and switched to **`@cf/black-forest-labs/flux-2-klein-4b`** (Apache 2.0). It takes multipart form input with `seed`, `width`, `height` and **reference images** (`input_image_0`). `keyframes.py` now sends the character sheet as a reference for every shot that shows the girl.
- **Lesson:** the brief's suggested model was right, but its API on this provider differs from the docs I assumed. Read the provider's live schema, not memory.

### F4: The same seed does not give the same image on FLUX.2 klein
- **Stage:** keyframes
- **What broke:** two identical requests (same prompt, seed 7, 1024²) returned **different** images.
- **Workaround:** reproducibility comes from **caching the file**, not from re-running the seed. Every keyframe is saved under a hash of its inputs and never regenerated unless its inputs change. Seeds are still logged and sent.
- **Lesson:** "fixed seed means the same result" isn't guaranteed on hosted GPUs (non-deterministic kernels, batching). Experiments compare candidates side by side instead.

### F5: Gemini TTS returns no audio for some Amharic lines (`finishReason: OTHER`)
- **Stage:** narration
- **What broke:** a 200 response with no audio part: `"finishReason": "OTHER"`. It happened on s04 (once) and s05 (three times). The same text succeeded on a later attempt.
- **Fix:** treat it as retryable. Narration now gets 5 attempts with backoff, and every failed attempt is logged.
- **Lesson:** intermittent, and possibly language-related (both lines start with Amharic text after an English style instruction). Worth an experiment: write the style instruction in Amharic.

### F6: Free-tier TTS quota is 10 requests per day per model, and failures count
- **Stage:** narration (radio cut)
- **What broke:** first `HTTP 429` (per-minute limit) after 5 quick calls. Then, at s08: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: "10"`, `retryDelay: "65472s"` (about 18 h). The smoke test plus 3 `OTHER` failures used up the budget before all 10 lines were done.
- **What I tried:** 1) exponential backoff, which isn't enough for a per-minute window. 2) Honouring Google's `retryDelay` and pacing TTS calls to one per 21 s (`narration.py`), which fixed the per-minute limit. 3) The daily limit can't be waited out before the deadline.
- **Fix:** the quota is **per model**. Listed the available models (`/v1beta/models`) and switched the whole narration to **`gemini-3.8-flash-tts`**, the model the brief names. All 10 lines were regenerated with it so the film has one consistent voice, not two.
- **Lesson (F6):** on a 10-requests-per-day budget, every call matters.

### F7: Gemini 3.8 Flash TTS reads the style instruction aloud and continues the story
- **What broke:** lines came out about 3× too long (s01: 12.6 s vs 4.2 s on 2.5). A native-speaker listen confirmed that the English style prefix was spoken (in Amharic) and the speech ran on past the line.
- **Fix:** removed all instruction text. The request carries only the Amharic line. Added a length check in `narration.py` that warns when audio is much longer than about 1.5 words/s would predict.

### F8: Gemini 3.8 Flash Lite TTS rejects `systemInstruction`
- **What broke:** `HTTP 400: Developer instruction is not enabled for this model`.
- **Fix:** plain text only (see F7). The cost of that is that I can't steer the delivery (warm, unhurried).

### F9: Computer slept or lost network mid-run, and the background job was killed for low memory
- **What broke:** DNS failures from 18:05, then one attempt "took" 16,946 s. Earlier, a background run was killed by the OS for low memory.
- **Fix:** every stage is cached per shot, so the reruns resumed where they had stopped and no finished line or image was regenerated.

### F10: Daily TTS quota ran out on each model, so narration is split across models
- **What broke:** 3.8 Lite hit 10 requests/day at s08 (the 400s and DNS failures counted too).
- **Fix:** added an optional per-shot `tts_model` override to the schema. s08–s10 use `gemini-3.1-flash-tts-preview` with the same voice name (Sulafat). The 10 lines are now split across two TTS models. **To check by ear:** whether the voice change at s08 is noticeable.

### F11: Cloudflare safety filter flagged two keyframes
- **What broke:** s08 (assembly + flag) and s10 (classroom): `AiError: Your output has been flagged` (code 3030).
- **Fix:** an automatic retry succeeded on the second attempt for both. The filter is non-deterministic, so retries are worth more than rewriting the prompt. Narration is cached per line, so a re-take costs one call, not ten. Don't spend quota on smoke tests of the same model.
