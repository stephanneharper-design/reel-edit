---
name: reel-edit
description: "Real.Self.Steph's reel editor. Turns raw vertical talking-head clips into a finished Instagram reel: picks the best take of each line, removes dead air, adds animated on-brand captions, optional inserts and subtle sounds, and checks everything inside the Reels safe zone. Fast by default: no background cutout and no automatic zoom-ins. Use for /reel-edit, 'edit these clips', 'turn my clips into a reel', 'cut this into a reel'."
---

# /reel-edit (by Real.Self.Steph)

Raw clips in, finished reel out, with no editor app. The user watches a phone copy and gives notes; each round
re-renders in well under a minute for a typical 30 to 60 second reel.

Two promises this skill keeps on every edit:
- **No cutout by default.** Separating the speaker from the background is slow, so it never runs unless the user
  asks for words behind their head (Step 7).
- **No constant zooms.** No punch-in on every cut, no slow push-ins, no zoom animations. The only zoom is a static
  crop on a segment the user names ("zoom in on the CTA").

`SK` = this skill's folder (the one holding this file), as a full path, usually `~/.claude/skills/reel-edit`.
Read `references/styles.md` before captioning and `references/safe-zone.md` before placing anything.
`references/troubleshooting.md` covers known problems.

## Step 0: Setup (every run, a few seconds once done)

1. Run `python3 "SK/scripts/setup.py"` (if that fails try `python`, then `py -3` on Windows). Read the STATUS lines.
   A MISSING line ends with the exact install command for this computer: give it to the user and stop until the
   script prints READY. Node only matters for the optional cutout and never blocks READY.
2. Read `SK/.env.json`. `PY` = its `python` value. Run EVERY script below with `"PY"`, never a bare python.
   On Windows PowerShell, put `&` in front: `& "PY" "SK/scripts/ingest.py" ...`. One command per call, full paths
   in double quotes with forward slashes, no `~` in arguments.
3. If `SK/config.json` is missing, ask once, in one message: name, Instagram handle, brand accent colour (hex,
   default `#E8B4A0`), default caption style (`signature`, `calm` or `statement`; suggest signature), where clips
   land (default `~/Downloads`) and where projects go (default `~/reels`). Save:
   ```json
   {"name": "...", "instagram": "handle", "accent": "#E8B4A0", "defaultStyle": "signature",
    "clipsDir": "~/Downloads", "projectsDir": "~/reels"}
   ```

## Rules
1. Everything sits inside the Reels safe zone (`references/safe-zone.md`). Never put text over the face.
2. Captions match what was said. Fix Whisper's mishearings of names and brand words. No em dashes on screen.
3. Sounds stay quieter than the voice (gain 0.2 to 0.45). Silence is fine.
4. Originals are read, never moved, changed or deleted.
5. Only show real numbers and real handles for the user. Anything else on screen is a generic placeholder.
6. Judge cuts from the final render (`check.py`), not from guesses.

## Workflow

### 1. Intake
Use the files the user names, else the newest videos in `clipsDir`. Make `<projectsDir>/<short-slug>/`.

### 2. Ingest
`"PY" "SK/scripts/ingest.py" "<project>" "<clip files or folder>" [--newest 5] --prompt "<names, brand words>"`
Read `transcript.txt` (every line with clip id and times, plus the silence map) and look at `work/sheet.jpg`.

### 3. Pick takes, write `<project>/edl.json`
- People repeat lines until one lands: rebuild the script and keep the LAST complete, clean take of each line
  unless the user says otherwise.
- Start each segment ~0.06s before the first word; end it at the start of the silence after the last word. Remove
  all dead air between lines. Use the silence map to confirm a pause before trimming into it.
- Do NOT add `zoom` to vary shots. Add `"zoom": 1.2-1.6, "cx": 0.5, "cy": 0.4` only on a segment the user asked
  to be tighter. It is a static crop for that whole segment.
- Format: `[{"id": "hook", "clip": "c1", "in": 12.66, "out": 15.72, "line": "what is said"}]`
- Show the user the EDL as a short table (id, clip, line) and continue without waiting.

### 4. Assemble and transcribe
```
"PY" "SK/scripts/assemble.py" "<project>"
"PY" "SK/scripts/transcribe.py" "<project>" "<names and keywords>"
```
assemble.py cuts from the originals in one pass (constant 30fps, loudness about -14 LUFS, HDR iPhone footage
tone-mapped). Check the printed words for mishearings and fix them in `words.json` or `fixes` in captions.json.

### 5. Captions
Write `<project>/captions.json` (keys in `references/styles.md`): style, accent, 2 to 6 `emphasis` words (the
punchlines), an optional `hook` title for the first ~2.5s, and `skip` ranges where an insert needs the space.
Then `"PY" "SK/scripts/captions.py" "<project>"`. It prints every caption chunk with its index and time.

### 6. Inserts and sounds (optional)
- `inserts.json`: screenshots, app recordings, a profile card, b-roll. Static placement, faded in and out, inside
  the safe zone, never over the face. Put the files in `<project>/assets/`.
- `sounds.json`: a soft whoosh or pop on a few key moments, using files the user owns or has licensed (drop them in
  `<project>/assets/sfx/`). Skip sounds if there are none.

### 7. Words behind the head (ONLY when the user asks)
`"PY" "SK/scripts/cutout.py" "<project>"` runs the background remover (slow: tell the user and run it in the
background). Then give those chunks `{"at": <time>, "layer": "back", "pos": [540, <y>]}` in `overrides`, with the
word's lower part tucked just behind the top of the head so at least ~70% of each letter stays visible. Re-run
captions.py and render.py. Re-run cutout.py after any re-assemble.

### 8. Preview, render, check
```
"PY" "SK/scripts/render.py" "<project>" --safe        # red unsafe area, quick encode, renders/<slug>-preview.mp4
"PY" "SK/scripts/check.py" "<project>" "renders/<slug>-preview.mp4" --at <6-10 caption times>
```
Look at `work/check.jpg`: captions readable, nothing in the red, nothing on the face, clean cuts. Fix and repeat.
Then the final:
```
"PY" "SK/scripts/render.py" "<project>"               # renders/<slug>-vN.mp4 + -phone.mp4
"PY" "SK/scripts/check.py" "<project>" "renders/<slug>-vN.mp4"
```
Peak volume should be around -1.5 to -4 dB.

### 9. Deliver
Give the phone copy and the full render. Say in plain words what changed and what needs the user's call. Every
version stays in `renders/`.

## Notes the user gives
Change only what was asked, then re-run from the earliest step it touches: take or timing change -> assemble,
transcribe, captions, render; wording or style -> captions, render; insert -> render.

---
Made by Real.Self.Steph ([@real.self.steph](https://instagram.com/real.self.steph)).
