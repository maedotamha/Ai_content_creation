# Experiments

Format: **hypothesis → change (one thing, fixed seed) → result (evidence) → decision.** Aim for 10 or more. Reference `runs.jsonl` lines or output filenames as evidence.

| # | Stage | Hypothesis | Change | Result (evidence) | Decision |
|---|---|---|---|---|---|
| E1 | narration | A style instruction improves the voice more than switching voices | Same line, voice X, with and without "slowly and warmly" | | |
| E2 | narration | Voice A suits the story better than voice B | Same line and style, two voices | | |
| E3 | narration | TTS mispronounces place and person names in my language | Native speaker listens to s0X | | |
| E4 | keyframes | Repeating the identical character description keeps the face consistent | Character text injected vs paraphrased per shot, same seed | | |
| E5 | keyframes | A fixed seed makes FLUX.2 klein reproducible, so I can compare prompts fairly | Same prompt + seed 7 sent twice | **Rejected:** the two images were different (see FAILURES F4). Latency 6.3 s vs 4.8 s. | Reproducibility comes from caching files by input hash. Compare candidates side by side. |
| E5b | keyframes | FLUX.2 klein with a reference image keeps the girl more consistent than text-only FLUX.1 schnell | schnell has no seed or reference input; klein accepts `input_image_0` (tested: 200 OK, 5.5 s) | Klein chosen. Consistency comparison to fill in after keyframes. | Switched `models.image` to klein-4b |
| E6 | keyframes | The style block alone fixes the look across shots | With and without style block | | |
| E7 | shots | An I2V motion prompt with only motion and camera beats a full re-description | Two prompts, same keyframe + seed | | |
| E8 | shots | 480p drafts are good enough to judge motion and save GPU minutes | 480p vs 720p on one shot | GPU minutes | |
| E9 | shots | Ken Burns is acceptable for still-life shots, keeping Wan for people | Viewer preference | | |
| E10 | music | Candidate with the quietest texture works best under the voice | 3 ACE-Step seeds, listened under the narration | | |
| E11 | mix | Ducking ratio 6 with 1.5 s release sounds natural | ratio 4 vs 6 vs 10 | | |
| E12 | | | | | |
