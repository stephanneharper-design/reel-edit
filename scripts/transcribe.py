#!/usr/bin/env python3
"""Word-level transcript of the assembled A-roll, used for caption timing.

Usage:  PY transcribe.py <project_dir> ["names and keywords said in the reel"] [--model small.en]

Pass the names and keywords (brand, product, app names) so Whisper spells them right.
Writes words.json: [{"w": "word", "s": start, "e": end, "seg": "segment id"}] in A-roll time, and prints the
words one segment per line so mishearings are easy to spot. Fix any wrong word by editing "w" in words.json
(or add it to "fixes" in captions.json); never change the times by hand unless a word is clearly misplaced.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('prompt', nargs='?', default='')
    ap.add_argument('--model', default='small.en')
    a = ap.parse_args()
    proj = C.expand(a.project)
    aroll = os.path.join(proj, 'work', 'aroll.mp4')
    segs = C.load(os.path.join(proj, 'segments.json')) or sys.exit('Run assemble.py first.')
    words, _ = C.transcribe(C.whisper(a.model), aroll, prompt=a.prompt or None)

    for w in words:
        mid = (w['s'] + w['e']) / 2
        seg = next((s for s in segs if s['start'] <= mid < s['end']), segs[-1])
        w['seg'] = seg['id']
        # a word never crosses a cut: clamp it into its own segment
        w['s'] = round(max(w['s'], seg['start']), 3)
        w['e'] = round(min(w['e'], seg['end'] - 0.01), 3)
    C.save(os.path.join(proj, 'words.json'), words)
    for s in segs:
        ws = [w for w in words if w['seg'] == s['id']]
        print(f"{s['id']:<12} {s['start']:6.2f}  " + ' '.join(f"{w['w']}" for w in ws))
    print(f'OK words.json ({len(words)} words)')


if __name__ == '__main__':
    main()
