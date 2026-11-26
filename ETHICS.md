# Ethics: consent, licences, labelling

> **Grading gate:** any real person shown or voiced without a consent record here means the film scores zero. Fill this in **before** generating anything of them.

## Consent record

| Person (role) | Appears as | Consent given for | How recorded | Date | Words approved? |
|---|---|---|---|---|---|
| Me (the author): the story is my own childhood memory | A **fictional** AI girl described in text only, not my likeness | my own story, narration text, public posting | this record (I am the author) | 2026-11-26 | yes, I wrote it |
| *(EDIT if any real person is named or recognisable, e.g. a teacher, a friend or a school name)* | | | | | |

- **No real person is shown or voiced.** The girl, her mother, friends and classmates are generic fictional characters generated from text descriptions. No photos of real people, children or a real school were used as input.
- **Children:** all children are fictional and shown only in ordinary, wholesome school situations.
- **Voice:** narration uses a stock Gemini TTS voice (`Sulafat`), **not** a clone of any real person's voice.
- **Likeness:** no real photos were uploaded to any model.
- **National symbols:** the flag is shown respectfully, described by its colours only. The anthem is referenced in narration, and no anthem recording is used.
- **Private data:** names, exact locations and private details were kept out of prompts sent to free endpoints that may train on inputs.

## Licences

| Component | Licence / terms | Commercial use of output |
|---|---|---|
| FLUX.1 schnell | Apache 2.0 | yes |
| FLUX.2 klein 4B (if used) | Apache 2.0 (9B is non-commercial) | 4B yes |
| Wan 2.2 TI2V-5B | Apache 2.0 | yes |
| ACE-Step 1.5 | MIT, trained on licensed/royalty-free/synthetic data | yes |
| Gemini TTS | Google Gemini API terms (free tier: inputs may be used to improve products) | check terms |
| FFmpeg (imageio-ffmpeg build) | LGPL/GPL | tool only |
| Cloudflare Workers AI | Cloudflare terms + model licence | |

## Labelling plan

- A 3 s end card in the film itself reads "Made with AI" and lists the models (enforced by the schema).
- The platform's AI disclosure label is switched **on** when posting (TikTok "AI-generated content" / YouTube "altered or synthetic content" / Meta "AI info").
- The post caption states it was made with an AI pipeline and links the repo.
- No watermarks or provenance metadata (SynthID, C2PA) are stripped. The pipeline re-encodes but does not remove embedded marks on purpose.
- Style prompts describe qualities (warm, hand-painted, grainy) and never name a living artist.
