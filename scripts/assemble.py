#!/usr/bin/env python3
"""Cut the picked takes into one clean 1080x1920 30fps A-roll, straight from the original files (one encode).

Usage:  PY assemble.py <project_dir> [--no-loudnorm]

Reads <project_dir>/edl.json:
  [{"id": "hook", "clip": "c1", "in": 12.66, "out": 15.72, "line": "what is said"}, ...]
  Optional per segment, ONLY when the user asks for it: "zoom": 1.4, "cx": 0.5, "cy": 0.4 (a static crop for
  the whole segment, no animation). The default is no zoom at all.

Writes:
  work/aroll.mp4    H.264 + AAC, constant 30fps, loudness normalised to about -14 LUFS
  segments.json     per segment: id, start, end, startFrame, frames, line  (times in the A-roll)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

TONEMAP = ('zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,'
           'zscale=t=bt709:m=bt709:r=tv,format=yuv420p,')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--no-loudnorm', action='store_true')
    a = ap.parse_args()
    proj = C.expand(a.project)
    clips = {c['id']: c for c in C.load(os.path.join(proj, 'clips.json'), [])}
    edl = C.load(os.path.join(proj, 'edl.json'))
    if not edl:
        sys.exit('edl.json is missing or empty.')

    can_tonemap = C.has_filter('zscale')
    inputs, graph, cat, segs, frame0 = [], [], '', [], 0
    for i, s in enumerate(edl):
        c = clips.get(s['clip']) or sys.exit(f"Unknown clip {s['clip']} in segment {s.get('id', i)}")
        dur = float(s['out']) - float(s['in'])
        if dur <= 0.1:
            sys.exit(f"Segment {s.get('id', i)} is too short ({dur:.2f}s).")
        n = max(1, round(dur * C.FPS))
        inputs += ['-ss', f"{float(s['in']):.3f}", '-t', f'{dur + 0.5:.3f}', '-i', c['path']]
        z = float(s.get('zoom', 1.0) or 1.0)
        vf = TONEMAP if (c.get('hdr') and can_tonemap) else ''
        # fill 9:16 first, then an optional static crop-in around (cx, cy)
        vf += f'scale={C.W}:{C.H}:force_original_aspect_ratio=increase,crop={C.W}:{C.H},'
        if z > 1.001:
            cx, cy = float(s.get('cx', 0.5)), float(s.get('cy', 0.5))
            # scale up from the source resolution (4K stays sharp), then crop back to 1080x1920
            vf = (TONEMAP if (c.get('hdr') and can_tonemap) else '') + \
                f'scale={round(C.W * z / 2) * 2}:{round(C.H * z / 2) * 2}:force_original_aspect_ratio=increase:' \
                f'flags=lanczos,crop={C.W}:{C.H}:(iw-{C.W})*{cx}:(ih-{C.H})*{cy},'
        vf += f'fps={C.FPS},trim=end_frame={n},setpts=N/{C.FPS}/TB,setsar=1,format=yuv420p'
        graph.append(f'[{i}:v]{vf}[v{i}]')
        if c.get('has_audio', True):
            graph.append(f'[{i}:a]aresample=48000,atrim=end={n / C.FPS:.4f},asetpts=N/SR/TB,'
                         f'afade=t=in:d=0.008,afade=t=out:st={n / C.FPS - 0.012:.4f}:d=0.012,'
                         f'aformat=channel_layouts=stereo[a{i}]')
        else:
            graph.append(f'anullsrc=r=48000:cl=stereo,atrim=end={n / C.FPS:.4f}[a{i}]')
        cat += f'[v{i}][a{i}]'
        segs.append({'id': s.get('id', f's{i + 1}'), 'start': round(frame0 / C.FPS, 4),
                     'end': round((frame0 + n) / C.FPS, 4), 'startFrame': frame0, 'frames': n,
                     'clip': s['clip'], 'line': s.get('line', '')})
        frame0 += n
        if c.get('hdr') and not can_tonemap:
            print(f"WARNING: {s['clip']} is HDR and this ffmpeg has no zscale: colours may look washed out.")

    graph.append(f'{cat}concat=n={len(edl)}:v=1:a=1[v][a0]')
    graph.append('[a0]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]' if not a.no_loudnorm else '[a0]anull[a]')
    out = os.path.join(proj, 'work', 'aroll.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(f'Assembling {len(edl)} segments, {frame0 / C.FPS:.2f}s...', flush=True)
    C.ffmpeg([*inputs, '-filter_complex', ';'.join(graph), '-map', '[v]', '-map', '[a]',
              '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-r', str(C.FPS), '-fps_mode', 'cfr',
              '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out])
    got = C.frame_count(out)
    if got != frame0:
        print(f'WARNING: aroll has {got} frames, expected {frame0}.')
    C.save(os.path.join(proj, 'segments.json'), segs)
    for s in segs:
        print(f"  {s['id']:<12} {s['start']:6.2f}-{s['end']:6.2f}  {s['line'][:60]}")
    print(f'OK work/aroll.mp4 ({got} frames) + segments.json')


if __name__ == '__main__':
    main()
