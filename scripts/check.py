#!/usr/bin/env python3
"""QA a render: a contact sheet of the first frame after every cut (plus any extra moments) and the audio levels.

Usage:  PY check.py <project_dir> <render.mp4> [--at 1.2,4.5,9.0]

Writes work/check.jpg (4 frames per row, each labelled by position in the order: cuts first, then --at times)
and prints the times it shows, plus peak / mean volume. A good master peaks around -1.5 to -4 dB.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('render')
    ap.add_argument('--at', default='')
    a = ap.parse_args()
    proj = C.expand(a.project)
    render = a.render if os.path.isabs(a.render) else os.path.join(proj, a.render)
    segs = C.load(os.path.join(proj, 'segments.json'), [])
    times = [(s['startFrame'] + 1) / C.FPS for s in segs[1:]]
    times += [float(t) for t in a.at.split(',') if t.strip()]
    if not times:
        times = [0.5]
    sel = '+'.join(f'eq(n\\,{round(t * C.FPS)})' for t in times)
    out = os.path.join(proj, 'work', 'check.jpg')
    cols = min(4, len(times))
    rows = -(-len(times) // cols)
    C.ffmpeg(['-i', render, '-vf', f"select='{sel}',scale=270:480,tile={cols}x{rows}:padding=4",
              '-frames:v', '1', '-fps_mode', 'vfr', out])
    for i, t in enumerate(times):
        print(f'  frame {i + 1}: {t:.2f}s' + ('  (cut)' if i < len(segs) - 1 else ''))
    r = subprocess.run([C.tool('ffmpeg'), '-hide_banner', '-i', render, '-af', 'volumedetect', '-vn', '-f', 'null', '-'],
                       **C.TEXT)
    for line in r.stderr.splitlines():
        if 'max_volume' in line or 'mean_volume' in line:
            print('  ' + line.split(']')[-1].strip())
    print(f'OK {out}')


if __name__ == '__main__':
    main()
