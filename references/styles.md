# Caption styles

Captions are ASS subtitles rendered by ffmpeg (libass), so there is no browser step and renders are fast.
Fonts ship in `assets/fonts` (Montserrat ExtraBold / SemiBold, DM Serif Display Italic, SIL Open Font License).

## The three styles
| style | look | words per line | motion |
|---|---|---|---|
| `signature` (default) | bold white Montserrat, the word being spoken lights up in the accent colour | 3 | gentle pop-in per line |
| `calm` | soft lowercase cream text, no highlight | 5 | fade only |
| `statement` | big uppercase, one or two words at a time | 2 | pop-in, word highlight |

In every style, `emphasis` words get their own moment: big serif italic (or heavy caps in `statement`) in the
accent colour, popped in. Use them for the punchline of each idea, 2 to 6 per reel. More than that and nothing
stands out.

There is no zoom or camera motion in any style. Movement comes from the captions only.

## captions.json keys
```json
{
  "style": "signature",
  "accent": "#E8B4A0",
  "emphasis": ["free", "minutes"],
  "fixes": {"cloud": "Claude", "real south": "Real Self"},
  "hook": {"text": "Stop editing reels by hand", "start": 0, "end": 2.6, "y": 360},
  "skip": [[8.2, 11.0]],
  "overrides": [{"at": 3.2, "pos": [540, 980], "size": 1.2}],
  "maxWords": 3,
  "y": 1260
}
```
- `y`: the caption centre line. 1260 sits on the chest of a normally framed talking head. Raise it (1150) if the
  user is framed low; never above the chin.
- `hook`: a title on an accent box near the top for the opening seconds. Keep it under ~28 characters.
- `skip`: no captions during an insert that needs the space (or move them with an override instead).
- `overrides`: target one chunk by any time inside it (see `work/chunks.txt`). `pos` moves it, `size` scales it,
  `"layer": "back"` puts it behind the speaker (needs cutout.py).
- `fixes`: whole-word, case-insensitive. Use for names Whisper gets wrong.

## Brand defaults (Real.Self.Steph)
- Accent `#E8B4A0` (soft peach) unless config.json says otherwise. White or cream text, dark soft shadow.
- Sentence case for `signature`, lowercase for `calm`.
- Avoid: orange or neon captions, captions pinned to a left edge, @handle watermarks in a corner, date stamps,
  more than one emphasis word on screen at once.

## Changing a style
Styles live in `STYLES` at the top of `scripts/captions.py` (font, size, colour, case, words per line, highlight,
pop). Add a new entry rather than editing one the user already likes. Extra fonts: drop a .ttf (with its licence)
into `assets/fonts` and use its family name.
