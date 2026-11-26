# Design

> Write sections 1–2 **before generating anything**. Commit them first, because the git timestamp is your evidence.

## 1. Brief

- **Whose story:** a school morning in Ethiopia, drawn from my own childhood and the shared memory of my classmates and siblings. *(EDIT: add who you talked to about it, e.g. a sibling or old classmate, and what details they added.)*
- **Audience:** Ethiopians aged roughly 18–35 who went to school in Ethiopia (old classmates, siblings, cousins), including those now living abroad who haven't stood in a school assembly for years.
- **Where they watch:** on a phone, vertical, shared on Telegram, TikTok and WhatsApp. Often watched with sound on, but subtitles are needed for the English-speaking and diaspora viewers.
- **Intent:** at the end the viewer should **smile with recognition ("that was us")** and feel a small, warm pride. The anthem moment ("I was small, but I felt big") is the emotional peak the whole film builds toward.
- **Define:** How might we make Ethiopians who grew up here, wherever they are now, re-live the rush and the pride of a school morning in 70 seconds?
- **Logline:** A schoolgirl in Ethiopia races through her morning (lost shoe, missed breakfast, the departing service bus) and arrives just in time to stand with everyone and sing the national anthem.

### Story shape (beats)

| Beat | Shots | Energy | Music cue |
|---|---|---|---|
| Dark, quiet, sleepy | s01–s02 | low | intro |
| The rush (comic) | s03–s04 | rising | build |
| The chase, then made it! | s05 | **peak 1** (tension) | peak |
| Friends, chatter, play | s06–s07 | high, joyful | build / peak |
| Order: lines, flag | s08 | slows down | low |
| Anthem: "small but big" | s09 | **peak 2** (emotion) | peak |
| Calm in class | s10 | resolves | resolve |

Shot sizes vary on purpose: extreme-wide (where), close-up (sleepy face), medium (the rush), insert (bread and backpack), wide (chase, yard, assembly), close-up (anthem), medium (class). The **red backpack and white ribbons** are her visual anchors, which help identify her in wide shots and keep keyframes consistent.

## 2. Ideas considered (ideate)

| Option | Why I chose / rejected it |
|---|---|
| 1. **Chronological morning, wake-up to classroom (chosen)** | Universal for the audience: everyone remembers the rush, the service bus and the assembly. Simple linear story means fewer consistency problems. Natural build to an emotional peak (the anthem). |
| 2. Only the bus ride, told through friends' chatter | Strong for humour, but needs several consistent characters talking. That's hard for image models, and there's no clear emotional ending. |
| 3. Then vs now: an adult in a foreign city remembers school | More emotional for the diaspora, but two versions of the character double the consistency risk, and it splits a 70-second film. |

**Design decisions:**
- **One main character** (the girl) keeps consistency manageable. Mother, friends and other students appear only as hands, blurred or background figures.
- **Narrated by her adult self in first person.** Past tense ("ነበር") gives the nostalgic distance the intent needs.
- **Amharic narration, English subtitles.** Amharic is the language most of the audience went to school in. Subtitles reach diaspora relatives who no longer read Amharic comfortably.
- **No real anthem audio.** The anthem is shown, not played. That avoids lip-sync problems and keeps the narration line as the emotional focus.
- **No text inside images.** Signs and school names are left out, and the flag is described by its colours only, because image models garble text and emblems.

## 3. User test 1: radio cut (`make radio`)

Date: ___ · Format: (in person / Slack / WhatsApp voice note) · Version: git commit `___`

| # | Who (role, not name) | Fits the audience because | What they said / where they reacted |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

**Insights:**
-

**Changes to storyboard.json** (link to the commit):
-

## 4. User test 2: near-final cut

Date: ___ · Version: git commit `___`

| # | Who | What they said / where they reacted |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |

**Insights:**
-

**What changed:**
-

## 5. Shot reasons

Every shot's reason is in `storyboard.json` (`shots[].reason`). Shot sizes go from wide (establishing) to medium (action) to close-up (feeling), and the coffee motif appears in s03, returns in s08 and resolves in s09.
