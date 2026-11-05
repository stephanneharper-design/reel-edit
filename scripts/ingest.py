#!/usr/bin/env python3
"""Register raw clips, transcribe every take with word timing, map silences, and make a contact sheet.

Usage:  PY ingest.py <project_dir> <clip files or one folder> [--newest N] [--model small.en] [--prompt "names"]

Originals are only read, never copied or changed. Writes in <project_dir>:
  clips.json        id (c1, c2...), path, duration, size, fps, hdr
  transcript.json   per clip: lines + words with times + silences
  transcript.txt    readable version: every line with clip id and times, then the silence map
  work/sheet.jpg    3 frames per clip (start / middle / end), one row per clip
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

VIDEO = ('.mp4', '.mov', '.m4v', '.mkv', '.webm')


def find_clips(items, newest):
    files = []
    for it in items:
        it = C.expand(it)
        if os.path.isdir(it):
            files += [p for p in glob.glob(os.path.join(it, '*')) if p.lower().endswith(VIDEO)]
        elif os.path.isfile(it):
            files.append(it)
        else:
            sys.exit(f'Not found: {it}')
    if newest:
        files = sorted(files, key=os.path.getmtime)[-newest:]
    return sorted(set(files), key=os.path.getmtime)  # filming order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('clips', nargs='+')
    ap.add_argument('--newest', type=int, default=0)
    ap.add_argument('--model', default='small.en')
    ap.add_argument('--prompt', default='')
    a = ap.parse_args()

    proj = C.expand(a.project)
    os.makedirs(os.path.join(proj, 'work'), exist_ok=True)
    files = find_clips(a.clips, a.newest)
    if not files:
        sys.exit('No video files found.')

    clips = []
    for i, f in enumerate(files, 1):
        info = C.probe(f)
        clips.append({'id': f'c{i}', 'path': f.replace('\\', '/'), **info})
        print(f"c{i}: {os.path.basename(f)}  {info['duration']:.1f}s  {info['width']}x{info['height']}"
              f"  {info['fps']}fps{'  HDR' if info['hdr'] else ''}", flush=True)
    C.save(os.path.join(proj, 'clips.json'), clips)

    model = C.whisper(a.model)
    tr, txt = {}, []
    for c in clips:
        print(f"Transcribing {c['id']}...", flush=True)
        words, lines = C.transcribe(model, c['path'], prompt=a.prompt or None)
        sil = C.silences(c['path'])
        tr[c['id']] = {'lines': lines, 'words': words, 'silences': sil}
        txt.append(f"=== {c['id']}  {os.path.basename(c['path'])}  ({c['duration']:.2f}s)")
        txt += [f"[{c['id']} {l['s']:7.2f}-{l['e']:7.2f}] {l['text']}" for l in lines]
        txt.append('silences: ' + ', '.join(f'{s:.2f}-{e:.2f}' for s, e in sil))
        txt.append('')
    C.save(os.path.join(proj, 'transcript.json'), tr)
    with open(os.path.join(proj, 'transcript.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(txt))

    # contact sheet: 3 thumbnails per clip
    thumbs = []
    for c in clips:
        for k, frac in enumerate((0.1, 0.5, 0.9)):
            out = os.path.join(proj, 'work', f"thumb_{c['id']}_{k}.jpg")
            C.ffmpeg(['-ss', f"{c['duration'] * frac:.2f}", '-i', c['path'], '-frames:v', '1',
                      '-vf', 'scale=270:480:force_original_aspect_ratio=decrease,pad=270:480:(ow-iw)/2:(oh-ih)/2',
                      out])  # row N of the sheet = clip cN
            thumbs.append(out)
    rows = len(clips)
    inputs = sum([['-i', t] for t in thumbs], [])
    layout = '|'.join(f'{(i % 3) * 270}_{(i // 3) * 480}' for i in range(len(thumbs)))
    graph = ''.join(f'[{i}:v]' for i in range(len(thumbs))) + f'xstack=inputs={len(thumbs)}:layout={layout}[v]'
    C.ffmpeg([*inputs, '-filter_complex', graph, '-map', '[v]', '-frames:v', '1',
              os.path.join(proj, 'work', 'sheet.jpg')])
    for t in thumbs:
        os.remove(t)
    print(f'Done: {len(clips)} clips. Read transcript.txt and look at work/sheet.jpg ({rows} rows).')


if __name__ == '__main__':
    main()
