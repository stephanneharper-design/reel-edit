#!/usr/bin/env python3
"""Render the reel: A-roll + captions + optional inserts and sounds, in one ffmpeg pass. No zooms, no push-ins.

Usage:  PY render.py <project_dir> [--safe] [--draft] [--name slug]

  --safe    draw the Instagram unsafe area in red (for checking layout only, never for delivery)
  --draft   faster encode for a quick look (same layout, lower quality)

Reads (all optional except the A-roll and captions):
  work/aroll.mp4, work/captions.ass         from assemble.py / captions.py
  work/subject.webm + work/captions_back.ass  only if the optional cutout was made
  inserts.json  [{"file": "assets/app.png", "start": 4.2, "end": 7.0, "x": 140, "y": 300, "w": 800}]
                images or videos (transparent PNG / alpha WebM welcome), faded in and out, static (no zoom)
  sounds.json   [{"file": "assets/sfx/whoosh.mp3", "at": 4.2, "gain": 0.35}]  always quieter than the voice
Writes renders/<slug>-vN.mp4 (full quality) and renders/<slug>-vN-phone.mp4 (720p, small enough to send).
"""
import argparse
import glob
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def safe_guide():
    s = C.SAFE
    red = 'red@0.28'
    return (f",format=rgba,drawbox=x=0:y=0:w={C.W}:h={s['top']}:color={red}:t=fill"
            f",drawbox=x=0:y={s['bottom_y']}:w={C.W}:h={C.H - s['bottom_y']}:color={red}:t=fill"
            f",drawbox=x=0:y={s['top']}:w={s['side']}:h={s['bottom_y'] - s['top']}:color={red}:t=fill"
            f",drawbox=x={C.W - s['side']}:y={s['top']}:w={s['side']}:h={s['right_col_from_y'] - s['top']}:color={red}:t=fill"
            f",drawbox=x={C.W - s['right_col']}:y={s['right_col_from_y']}:w={s['right_col']}"
            f":h={s['bottom_y'] - s['right_col_from_y']}:color={red}:t=fill")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--safe', action='store_true')
    ap.add_argument('--draft', action='store_true')
    ap.add_argument('--name', default='')
    a = ap.parse_args()
    proj = C.expand(a.project)
    work = os.path.join(proj, 'work')
    if not os.path.exists(os.path.join(work, 'aroll.mp4')):
        sys.exit('work/aroll.mp4 missing: run assemble.py.')
    if not os.path.exists(os.path.join(work, 'captions.ass')):
        sys.exit('work/captions.ass missing: run captions.py.')

    # fonts next to the subtitles so every path in the filter graph is short and relative (Windows-safe)
    fdir = os.path.join(work, 'fonts')
    os.makedirs(fdir, exist_ok=True)
    for f in glob.glob(os.path.join(C.SK, 'assets', 'fonts', '*.ttf')):
        shutil.copy2(f, fdir)

    dur = C.frame_count(os.path.join(work, 'aroll.mp4')) / C.FPS
    inputs = ['-i', 'work/aroll.mp4']
    graph, v = [], '[0:v]'
    n = 1

    back = os.path.exists(os.path.join(work, 'captions_back.ass')) and os.path.exists(os.path.join(work, 'subject.webm'))
    if back:  # words behind the speaker: captions on the plate, then the cut-out speaker on top
        inputs += ['-c:v', 'libvpx-vp9', '-i', 'work/subject.webm']
        graph.append(f"{v}subtitles=work/captions_back.ass:fontsdir=work/fonts[vb]")
        graph.append(f'[vb][{n}:v]overlay=0:0:eof_action=pass:format=auto[vs]')
        v, n = '[vs]', n + 1

    for k, ins in enumerate(C.load(os.path.join(proj, 'inserts.json'), []) or []):
        f = ins['file'].replace('\\', '/')
        s, e = float(ins['start']), float(ins['end'])
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            inputs += ['-loop', '1', '-t', f'{e - s:.3f}', '-i', f]
        else:
            inputs += (['-c:v', 'libvpx-vp9'] if f.lower().endswith('.webm') else []) + ['-i', f]
        w = int(ins.get('w', 800))
        fd = float(ins.get('fade', 0.18))
        graph.append(f'[{n}:v]scale={w}:-2,format=yuva420p,trim=duration={e - s:.3f},'
                     f'fade=t=in:st=0:d={fd}:alpha=1,fade=t=out:st={max(0, e - s - fd):.3f}:d={fd}:alpha=1,'
                     f'setpts=PTS-STARTPTS+{s:.3f}/TB[i{k}]')
        graph.append(f"{v}[i{k}]overlay={int(ins.get('x', 140))}:{int(ins.get('y', 300))}:eof_action=pass"
                     f":enable='between(t,{s:.3f},{e:.3f})'[vi{k}]")
        v, n = f'[vi{k}]', n + 1

    graph.append(f"{v}subtitles=work/captions.ass:fontsdir=work/fonts{safe_guide() if a.safe else ''},format=yuv420p[v]")

    sounds = C.load(os.path.join(proj, 'sounds.json'), []) or []
    if sounds:
        labels = []
        for k, snd in enumerate(sounds):
            inputs += ['-i', snd['file'].replace('\\', '/')]
            ms = int(float(snd['at']) * 1000)
            graph.append(f"[{n}:a]aresample=48000,volume={min(float(snd.get('gain', 0.35)), 0.6)},"
                         f"adelay={ms}|{ms}[s{k}]")
            labels.append(f'[s{k}]')
            n += 1
        graph.append(f"[0:a]{''.join(labels)}amix=inputs={len(labels) + 1}:normalize=0:duration=first,"
                     f"alimiter=limit=0.89[a]")
        amap = '[a]'
    else:
        amap = '0:a'

    os.makedirs(os.path.join(proj, 'renders'), exist_ok=True)
    slug = a.name or os.path.basename(proj.rstrip('/\\'))
    ver = 1 + max([int(p.rsplit('-v', 1)[1].split('.')[0].split('-')[0])
                   for p in glob.glob(os.path.join(proj, 'renders', f'{slug}-v*.mp4'))
                   if p.rsplit('-v', 1)[1].split('.')[0].split('-')[0].isdigit()] or [0])
    # previews (--safe / --draft) overwrite one file and never use up a version number
    out = f'renders/{slug}-preview.mp4' if (a.safe or a.draft) else f'renders/{slug}-v{ver}.mp4'
    enc = ['-preset', 'veryfast', '-crf', '23'] if (a.draft or a.safe) else ['-preset', 'slow', '-crf', '17']
    print(f'Rendering {out} ({dur:.1f}s)...', flush=True)
    C.ffmpeg([*inputs, '-filter_complex', ';'.join(graph), '-map', '[v]', '-map', amap, '-t', f'{dur:.3f}',
              '-c:v', 'libx264', *enc, '-pix_fmt', 'yuv420p', '-r', str(C.FPS),
              '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], cwd=proj)
    if not (a.safe or a.draft):
        phone = out.replace('.mp4', '-phone.mp4')
        C.ffmpeg(['-i', out, '-vf', 'scale=720:1280', '-c:v', 'libx264', '-preset', 'fast', '-crf', '27',
                  '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', phone], cwd=proj)
        print(f'OK {out}\nOK {phone}')
    else:
        print(f'OK {out}')


if __name__ == '__main__':
    main()
