# Reel Edit
### A Claude Code skill by Real.Self.Steph ([@real.self.steph](https://instagram.com/real.self.steph))

Film your talking-head clips, drop them in a folder, type `/reel-edit`, and Claude turns them into a finished
Instagram reel: best take of every line, no dead air, animated on-brand captions, and a safe-zone check. You
watch the result, give notes, and it re-renders in under a minute.

Built for speed:
- **No background cutout unless you ask for it.** It is the slowest part of reel editing, so it's opt-in.
- **No constant zoom-ins.** Clean, steady shots. A zoom only happens on a line you ask for.

## Requirements
- Claude Code on a Mac, Windows or Linux computer
- ffmpeg and Python 3.10+ (the skill checks and gives you the exact install line if something is missing)
- Optional: Node.js 22+, only for words behind your head

## Install
**Easiest:** open Claude Code and paste:
```
Install this skill for me: https://github.com/stephanneharper-design/reel-edit
```

**Or download it:** grab [reel-edit.zip](https://github.com/stephanneharper-design/reel-edit/raw/main/reel-edit.zip) and unzip it into your Claude skills folder so you get:
- Mac / Linux: `~/.claude/skills/reel-edit/SKILL.md`
- Windows: `C:\Users\<you>\.claude\skills\reel-edit\SKILL.md`

**Or in Terminal:**
```bash
git clone https://github.com/stephanneharper-design/reel-edit "$HOME/.claude/skills/reel-edit"
```

Then type `/reel-edit`. The first run asks your name, handle, brand colour and caption style, then sets itself
up (about 2 minutes, once).

## Use it
```
/reel-edit I just dropped 4 clips in my downloads
/reel-edit use the calm style and put "free" behind my head
the captions feel small and cut the pause before "and here's why"
```

## Credits
Captions use Montserrat and DM Serif Display (SIL Open Font License, licences in `assets/fonts`). Transcription by
[faster-whisper](https://github.com/SYSTRAN/faster-whisper). The optional cutout uses the open-source
[HyperFrames](https://github.com/heygen-com/hyperframes) background remover (Apache-2.0).
