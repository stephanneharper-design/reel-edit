#!/usr/bin/env python3
"""OPTIONAL: cut the speaker out of the A-roll so caption words can sit behind them.

Only run this when the user asks for words behind their head. It is the slow step (minutes on an Apple Silicon
Mac, much longer on Windows/Linux CPUs) and the reel looks finished without it.

Usage:  PY cutout.py <project_dir>

Uses the open-source HyperFrames background remover (Apache-2.0, needs Node 22+):
  npx --yes hyperframes@0.8.34 remove-background work/aroll.mp4 -o work/subject.webm
Then checks the cutout has exactly as many frames as the A-roll (otherwise it drifts out of sync).
Re-run after every assemble.py, because the cutout belongs to one exact A-roll.
"""
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def main():
    proj = C.expand(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
    npx = shutil.which('npx') or shutil.which('npx.cmd')
    if not npx:
        sys.exit('Node 22+ is needed for the cutout. Run scripts/setup.py for the install command.')
    src, out = os.path.join('work', 'aroll.mp4'), os.path.join('work', 'subject.webm')
    if not os.path.exists(os.path.join(proj, src)):
        sys.exit('Run assemble.py first.')
    t0 = time.time()
    print('Cutting out the speaker (slow step; first run downloads a ~170 MB model)...', flush=True)
    r = subprocess.run([npx, '--yes', 'hyperframes@0.8.34', 'remove-background', src, '-o', out,
                        '--quality', 'balanced', *sys.argv[2:]], cwd=proj)
    if r.returncode != 0:
        sys.exit('Background removal failed (see the output above). The reel can still render without it.')
    a, b = C.frame_count(os.path.join(proj, src)), C.frame_count(os.path.join(proj, out))
    if a != b:
        sys.exit(f'Frame mismatch: aroll {a} vs cutout {b}. Re-run assemble.py, then this script.')
    print(f'OK work/subject.webm ({b} frames, {time.time() - t0:.0f}s). Re-run captions.py, then render.py.')


if __name__ == '__main__':
    main()
