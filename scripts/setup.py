#!/usr/bin/env python3
"""Check and prepare everything the reel-edit skill needs. Safe to run on every session (a few seconds when done).

Usage:  python3 setup.py        (or `python setup.py`, or `py -3 setup.py` on Windows)

Prints one STATUS line per item and READY at the end. Writes <skill>/.env.json with the exact Python to use.
Standard library only, so it runs before the skill's own Python exists.
"""
import json
import os
import platform
import shutil
import subprocess
import sys

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.path.join(SK, '.venv')
OS = {'Darwin': 'macos', 'Windows': 'windows'}.get(platform.system(), 'linux')
PKGS = ['faster-whisper==1.2.1', 'av>=12,<19']  # av 19 breaks faster-whisper 1.2.1 audio decoding

FIX = {
    'ffmpeg': {'macos': 'brew install ffmpeg', 'windows': 'winget install --id Gyan.FFmpeg -e',
               'linux': 'sudo apt install ffmpeg'},
    'node': {'macos': 'brew install node', 'windows': 'winget install --id OpenJS.NodeJS.LTS -e',
             'linux': 'install Node 22+ from https://nodejs.org'},
    'venv': {'macos': 'brew install python', 'windows': 'winget install --id Python.Python.3.12 -e',
             'linux': 'sudo apt install python3 python3-venv'},
}


def status(item, ok, note=''):
    print(f"STATUS {item}: {'OK' if ok else 'MISSING'}{(' - ' + note) if note else ''}", flush=True)
    return ok


def venv_python():
    return os.path.join(VENV, 'Scripts', 'python.exe') if OS == 'windows' else os.path.join(VENV, 'bin', 'python')


def main():
    ready = True
    if sys.version_info < (3, 10):
        ready &= status('python', False, f'need 3.10+, found {platform.python_version()}. Fix: {FIX["venv"][OS]}')
    else:
        status('python', True, platform.python_version())

    for t in ('ffmpeg', 'ffprobe'):
        ok = shutil.which(t) is not None
        ready &= status(t, ok, '' if ok else f'Fix: {FIX["ffmpeg"][OS]}' +
                        (' (then fully quit and reopen Claude Code)' if OS == 'windows' else ''))

    # Node is only needed for the OPTIONAL background cutout, so it never blocks READY.
    node = shutil.which('node')
    ver = ''
    if node:
        ver = subprocess.run([node, '--version'], capture_output=True, text=True).stdout.strip()
    node_ok = bool(ver) and int(ver.lstrip('v').split('.')[0]) >= 22
    status('node (optional, cutout only)', node_ok, ver if node_ok else f'Fix: {FIX["node"][OS]}')

    py = venv_python()
    if not os.path.exists(py):
        print('Creating the skill Python environment (once, about a minute)...', flush=True)
        r = subprocess.run([sys.executable, '-m', 'venv', VENV], capture_output=True, text=True)
        if r.returncode != 0:
            ready &= status('python venv', False, f'Fix: {FIX["venv"][OS]}')
    if os.path.exists(py):
        chk = subprocess.run([py, '-c', 'import faster_whisper, av; print(av.__version__)'],
                             capture_output=True, text=True)
        if chk.returncode != 0 or chk.stdout.strip().startswith('19'):
            print('Installing faster-whisper into the skill environment...', flush=True)
            subprocess.run([py, '-m', 'pip', 'install', '-q', '--upgrade', 'pip'], capture_output=True)
            r = subprocess.run([py, '-m', 'pip', 'install', '-q', *PKGS], capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stderr[-1500:])
        chk = subprocess.run([py, '-c', 'import faster_whisper'], capture_output=True, text=True)
        ready &= status('faster-whisper', chk.returncode == 0)

    with open(os.path.join(SK, '.env.json'), 'w', encoding='utf-8') as f:
        json.dump({'os': OS, 'python': py.replace('\\', '/'), 'skill': SK.replace('\\', '/'),
                   'cutout_available': node_ok,
                   'cutout_speed': 'fast (Apple GPU)' if OS == 'macos' and platform.machine() == 'arm64'
                   else 'slow (CPU)'}, f, indent=2)
    print('READY' if ready else 'NOT READY: fix the MISSING lines above, then run setup again.')
    sys.exit(0 if ready else 1)


if __name__ == '__main__':
    main()
