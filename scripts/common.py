"""Shared helpers for the reel-edit skill. Standard library only, works on macOS, Linux and Windows."""
import json
import os
import shutil
import subprocess
import sys

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
W, H = 1080, 1920
TEXT = dict(capture_output=True, text=True, encoding='utf-8', errors='replace')

# Instagram Reels safe zone on a 1080x1920 frame (keep text and inserts inside it)
SAFE = dict(top=220, bottom_y=1470, side=35, right_col=100, right_col_from_y=1155)


def tool(name):
    p = shutil.which(name)
    if not p:
        sys.exit(f'{name} not found on PATH. Run scripts/setup.py for the install command.')
    return p


def run(argv, cwd=None, quiet=True):
    r = subprocess.run(argv, cwd=cwd, **TEXT)
    if r.returncode != 0:
        tail = '\n'.join((r.stderr or r.stdout).strip().splitlines()[-25:])
        sys.exit(f'Command failed ({os.path.basename(argv[0])}):\n{tail}')
    if not quiet:
        print(r.stdout)
    return r


def ffmpeg(args, cwd=None):
    return run([tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-y', *args], cwd=cwd)


def probe(path):
    out = run([tool('ffprobe'), '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', path]).stdout
    d = json.loads(out)
    v = next((s for s in d['streams'] if s['codec_type'] == 'video'), None)
    a = next((s for s in d['streams'] if s['codec_type'] == 'audio'), None)
    if not v:
        sys.exit(f'No video stream in {path}')
    num, den = (v.get('avg_frame_rate') or '30/1').split('/')
    rot = 0
    for sd in v.get('side_data_list', []) or []:
        if 'rotation' in sd:
            rot = int(float(sd['rotation']))
    rot = int(v.get('tags', {}).get('rotate', rot) or rot)
    w, h = int(v['width']), int(v['height'])
    if abs(rot) in (90, 270):
        w, h = h, w
    return {
        'duration': float(d['format'].get('duration') or v.get('duration') or 0),
        'width': w, 'height': h,
        'fps': round(float(num) / float(den or 1), 3) if float(den or 1) else 30.0,
        'hdr': v.get('color_transfer') in ('arib-std-b67', 'smpte2084'),
        'has_audio': a is not None,
    }


def frame_count(path):
    out = run([tool('ffprobe'), '-v', 'error', '-count_packets', '-select_streams', 'v:0',
               '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', path]).stdout
    return int(out.strip().split(',')[0])


def has_filter(name):
    r = subprocess.run([tool('ffmpeg'), '-hide_banner', '-filters'], **TEXT)
    return any(line.split()[1:2] == [name] for line in r.stdout.splitlines() if len(line.split()) > 1)


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def config():
    return load(os.path.join(SK, 'config.json'), {}) or {}


def expand(p):
    return os.path.abspath(os.path.expanduser(p))


def whisper(model_name='small.en'):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit('faster-whisper is missing. Run this script with the skill Python from scripts/setup.py.')
    # device='cpu' on purpose: 'auto' picks CUDA on NVIDIA PCs without the CUDA libraries and crashes.
    return WhisperModel(model_name, device='cpu', compute_type='int8')


def transcribe(model, path, prompt=None, start=None, end=None):
    """-> list of {w, s, e} word dicts (seconds), plus the segments' text."""
    kw = dict(word_timestamps=True, vad_filter=False, beam_size=5, language='en')
    if prompt:
        kw['initial_prompt'] = prompt
    if start is not None:
        kw['clip_timestamps'] = [start, end] if end is not None else [start]
    segs, _ = model.transcribe(path, **kw)
    words, lines = [], []
    for s in segs:
        lines.append({'s': round(s.start, 3), 'e': round(s.end, 3), 'text': s.text.strip()})
        for w in s.words or []:
            words.append({'w': w.word.strip(), 's': round(w.start, 3), 'e': round(w.end, 3)})
    return words, lines


def silences(path, noise='-40dB', d=0.25):
    r = subprocess.run([tool('ffmpeg'), '-hide_banner', '-i', path, '-vn', '-af',
                        f'silencedetect=n={noise}:d={d}', '-f', 'null', '-'], **TEXT)
    out, cur = [], None
    for line in r.stderr.splitlines():
        if 'silence_start:' in line:
            cur = float(line.split('silence_start:')[1].split()[0])
        elif 'silence_end:' in line and cur is not None:
            out.append([round(max(cur, 0), 3), round(float(line.split('silence_end:')[1].split()[0]), 3)])
            cur = None
    return out
