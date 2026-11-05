#!/usr/bin/env python3
"""Turn words.json into animated captions (ASS subtitles rendered by ffmpeg/libass). Fast: no browser, no cutout.

Usage:  PY captions.py <project_dir>

Reads captions.json in the project (all keys optional, see references/styles.md):
  {"style": "bold" | "playful" | "artsy",
   "accent": "#E8B4A0",            brand colour (defaults to config.json accent)
   "emphasis": ["money", "free"],  words that get their own big accent moment
   "fixes": {"cloud": "Claude"},   whole-word replacements (case-insensitive)
   "hook": {"text": "Stop editing reels", "start": 0, "end": 2.6},
   "skip": [[8.2, 11.0]],          no captions in these A-roll ranges (an insert is on screen, for example)
   "overrides": [{"at": 3.2, "pos": [540, 420], "layer": "back", "size": 1.3}],
   "maxWords": 3,                  words per caption line (style default otherwise)
   "y": 1260}                      caption centre line (default 1260, the chest band)

"layer": "back" puts that chunk BEHIND the speaker; it only works after the optional cutout (cutout.py).
Writes work/captions.ass (+ work/captions_back.ass when needed) and work/chunks.txt (one line per caption chunk,
with its index and time, so you can target overrides).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

STYLES = {
    # BOLD: big white uppercase words, the spoken word lights up in the accent colour, each line pops in
    'bold': dict(font='Montserrat ExtraBold', size=100, color='#FFFFFF', case='upper', maxWords=2,
                 highlight=True, pop='pop', rainbow=False, sparkle=False,
                 emph_font='Montserrat ExtraBold', emph_size=150, emph_italic=False),
    # PLAYFUL: rounded, colourful uppercase words that bounce in, each word its own pastel colour
    'playful': dict(font='Fredoka Bold', size=96, color='#FFFFFF', case='upper', maxWords=2,
                    highlight=False, pop='bounce', rainbow=True, sparkle=False,
                    emph_font='Fredoka Bold', emph_size=150, emph_italic=False),
    # ARTSY: soft lowercase serif italics that fade in, punchlines get little sparkles
    'artsy': dict(font='DM Serif Display', size=86, color='#FFF8EF', case='lower', maxWords=3, italic=True,
                  highlight=False, pop=False, rainbow=False, sparkle=True,
                  emph_font='DM Serif Display', emph_size=140, emph_italic=True),
}
ALIASES = {'signature': 'bold', 'statement': 'bold', 'calm': 'artsy', 'cool girl': 'artsy', 'fun': 'playful'}
RAINBOW = ['#FFB0E8', '#7FD0FF', '#FAE67A', '#D8FD8B', '#FFBF8A']
STAR = 'm 0 -18 b 2 -4 4 -2 18 0 b 4 2 2 4 0 18 b -2 4 -4 2 -18 0 b -4 -2 -2 -4 0 -18'
PAUSE = 0.35          # a gap this long between words starts a new caption line
HOLD = 0.35           # how long the last line of a sentence stays after the last word


def ass_color(hexstr, alpha=0):
    h = hexstr.lstrip('#')
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f'&H{alpha:02X}{b}{g}{r}'.upper()


def ts(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f'{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}'


def clean(word, fixes, case):
    w = word.replace('—', ',').replace('–', '-').replace('{', '(').replace('}', ')').replace('\\', '/')
    for bad, good in fixes.items():
        w = re.sub(rf'(?i)\b{re.escape(bad)}\b', good, w)
    return w.lower() if case == 'lower' else w.upper() if case == 'upper' else w


def bare(w):
    return re.sub(r'[^\w]', '', w.lower())


def chunk(words, segs, emphasis, max_words, skip):
    chunks, cur = [], []
    seg_end = {s['id']: s['end'] for s in segs}
    for i, w in enumerate(words):
        if any(a <= w['s'] < b for a, b in skip):
            continue
        is_emph = bare(w['w']) in emphasis
        new = (not cur or len(cur) >= max_words or is_emph or cur[-1].get('emph')
               or w['seg'] != cur[-1]['seg'] or w['s'] - cur[-1]['e'] > PAUSE
               or cur[-1]['w'].rstrip()[-1:] in '.?!,:;')
        if new and cur:
            chunks.append(cur)
            cur = []
        cur.append({**w, 'emph': is_emph})
    if cur:
        chunks.append(cur)
    out = []
    for k, c in enumerate(chunks):
        start = c[0]['s'] - 0.04
        nxt = chunks[k + 1][0]['s'] - 0.04 if k + 1 < len(chunks) else None
        end = c[-1]['e'] + HOLD
        if nxt is not None:
            end = min(end, nxt)
        end = min(end, seg_end.get(c[-1]['seg'], end) - 0.002)  # never hold a caption across a cut
        if out and start < out[-1]['end']:
            start = out[-1]['end']
        out.append({'words': c, 'start': start, 'end': max(end, start + 0.12), 'emph': c[0]['emph']})
    return out


def header(st, accent, y):
    base = ass_color(st['color'])
    shadow = ass_color('#000000', 0x70)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {C.W}
PlayResY: {C.H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{st['font']},{st['size']},{base},{base},{shadow},{shadow},0,{-1 if st.get('italic') else 0},0,0,100,100,0,0,1,3,0,5,70,140,0,1
Style: Emph,{st['emph_font']},{st['emph_size']},{ass_color(accent)},{ass_color(accent)},{shadow},{shadow},0,{-1 if st['emph_italic'] else 0},0,0,100,100,0,0,1,3,0,5,70,140,0,1
Style: Hook,Montserrat ExtraBold,66,{ass_color('#1A1A1A')},{ass_color('#1A1A1A')},{ass_color(accent)},{ass_color(accent)},0,0,0,0,100,100,0,0,3,18,0,5,70,140,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def main():
    proj = C.expand(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
    cfg = C.load(os.path.join(proj, 'captions.json'), {}) or {}
    words = C.load(os.path.join(proj, 'words.json')) or sys.exit('Run transcribe.py first.')
    segs = C.load(os.path.join(proj, 'segments.json'))
    name = (cfg.get('style') or C.config().get('defaultStyle') or 'bold').lower()
    name = ALIASES.get(name, name)
    st = dict(STYLES.get(name, STYLES['bold']))
    accent = cfg.get('accent') or C.config().get('accent') or '#E8B4A0'
    y = int(cfg.get('y', 1260))
    fixes = cfg.get('fixes', {})
    emphasis = {bare(w) for w in cfg.get('emphasis', [])}
    chunks = chunk(words, segs, emphasis, int(cfg.get('maxWords', st['maxWords'])), cfg.get('skip', []))
    ovr = cfg.get('overrides', [])
    has_cutout = os.path.exists(os.path.join(proj, 'work', 'subject.webm'))

    front, back, listing = [], [], []
    acc = ass_color(accent)
    for k, ch in enumerate(chunks):
        o = next((o for o in ovr if ch['start'] - 0.05 <= o['at'] <= ch['end']), {})
        px, py = o.get('pos', [540, y - 40 if ch['emph'] else y])
        layer = 'back' if (o.get('layer') == 'back' and has_cutout) else 'front'
        if o.get('layer') == 'back' and not has_cutout:
            print(f'NOTE chunk {k}: "back" needs the cutout (cutout.py); showing it in front instead.')
        scale = float(o.get('size', 1.0))
        texts = [clean(w['w'], fixes, st['case']) for w in ch['words']]
        listing.append(f"{k:3d}  {ch['start']:6.2f}-{ch['end']:6.2f}  {'*' if ch['emph'] else ' '} {' '.join(texts)}")
        style = 'Emph' if ch['emph'] else 'Cap'
        sz = round(100 * scale)
        pop = st['pop'] or ('pop' if ch['emph'] else False)
        if pop == 'bounce':
            intro = (f'\\fscx{round(sz * .6)}\\fscy{round(sz * .6)}\\t(0,120,\\fscx{round(sz * 1.12)}'
                     f'\\fscy{round(sz * 1.12)})\\t(120,230,\\fscx{sz}\\fscy{sz})')
        elif pop:
            intro = f'\\fscx{round(sz * .82)}\\fscy{round(sz * .82)}\\t(0,140,\\fscx{sz}\\fscy{sz})'
        else:
            intro = f'\\fscx{sz}\\fscy{sz}'

        def paint(i, t):
            """Colour for word i: rainbow styles give every word (or every letter of a punchline) its own pastel."""
            if not st.get('rainbow'):
                return t
            if ch['emph']:
                return ''.join(f'{{\\c{ass_color(RAINBOW[(k + n) % len(RAINBOW)])}}}{c}' for n, c in enumerate(t))
            return f'{{\\c{ass_color(RAINBOW[(k + i) % len(RAINBOW)])}}}{t}'

        steps = range(len(texts)) if (st['highlight'] and not ch['emph'] and len(texts) > 1) else [None]
        for j in steps:
            a = ch['start'] if j in (None, 0) else ch['words'][j]['s'] - 0.02
            b = ch['end'] if j is None or j == len(texts) - 1 else ch['words'][j + 1]['s'] - 0.02
            if b <= a:
                continue
            body = ' '.join(f'{{\\c{acc}}}{t}{{\\r}}{{\\fscx{sz}\\fscy{sz}\\blur2}}' if i == j else paint(i, t)
                            for i, t in enumerate(texts))
            if st.get('sparkle') and ch['emph'] and j is None:
                # two little twinkling stars either side of the punchline
                half = len(' '.join(texts)) * st['emph_size'] * scale * 0.24 + 34
                for dx, dy, d0 in ((-half, -st['emph_size'] * 0.35, 0), (half, -st['emph_size'] * 0.5, 120)):
                    (back if layer == 'back' else front).append(
                        f'Dialogue: 2,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\an5\\pos({px + dx:.0f},{py + dy:.0f})'
                        f'\\c{acc}\\bord0\\shad0\\blur1\\fscx0\\fscy0\\t({d0},{d0 + 220},\\fscx170\\fscy170)'
                        f'\\fad(0,70)\\p1}}{STAR}{{\\p0}}')
            first, last = j in (None, 0), j is None or j == len(texts) - 1
            tags = f'\\an5\\pos({px},{py})\\blur2' + (intro if first else f'\\fscx{sz}\\fscy{sz}')
            tags += f"\\fad({90 if first else 0},{70 if last else 0})"
            line = f'Dialogue: 1,{ts(a)},{ts(b)},{style},,0,0,0,,{{{tags}}}{body}'
            (back if layer == 'back' else front).append(line)

    hook = cfg.get('hook')
    if hook and hook.get('text'):
        front.append(f"Dialogue: 2,{ts(hook.get('start', 0))},{ts(hook.get('end', 2.6))},Hook,,0,0,0,,"
                     f"{{\\an5\\pos(540,{hook.get('y', 360)})\\fad(120,120)}}{clean(hook['text'], fixes, 'as-is')}")

    work = os.path.join(proj, 'work')
    with open(os.path.join(work, 'captions.ass'), 'w', encoding='utf-8') as f:
        f.write(header(st, accent, y) + '\n'.join(front) + '\n')
    bpath = os.path.join(work, 'captions_back.ass')
    if back:
        with open(bpath, 'w', encoding='utf-8') as f:
            f.write(header(st, accent, y) + '\n'.join(back) + '\n')
    elif os.path.exists(bpath):
        os.remove(bpath)
    with open(os.path.join(work, 'chunks.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(listing) + '\n')
    print('\n'.join(listing))
    print(f"OK {len(chunks)} caption chunks, style {name}, accent {accent}"
          + (f', {len(back)} behind the speaker' if back else ''))


if __name__ == '__main__':
    main()
