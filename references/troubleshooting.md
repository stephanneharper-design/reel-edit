# Troubleshooting

## Setup
- `python3` on Windows opens the Microsoft Store or says "Python was not found": use `python` or `py -3`.
- Something installed while Claude Code is open is not found: fully quit and reopen Claude Code (it keeps the PATH
  it started with).
- Transcription fails with `unexpected keyword argument 'metadata_errors'`: the environment has PyAV 19. Run
  setup.py again; it pins a compatible version.
- `cublas64_12.dll` not found on an NVIDIA PC: the scripts already force Whisper onto the CPU; do the same
  (`device='cpu'`) in any one-off Whisper call.
- The first transcription downloads the Whisper model (small.en, about 0.5 GB). It needs internet once.

## Timing
- Whisper word times can be 0.1 to 0.3 s off, and it sometimes invents a word at a cut. Trust the silence map in
  transcript.txt over a single word time when trimming.
- When you change an in or out point, every later A-roll time moves. Re-run transcribe.py and captions.py instead
  of shifting times by hand.
- Captions never cross a cut: captions.py ends each line at its segment boundary.

## Picture
- Washed-out, grey footage from an iPhone: it was HDR and this ffmpeg has no `zscale` filter. Install a full
  ffmpeg build (Homebrew, winget Gyan.FFmpeg, or a static build) or turn HDR off on the phone.
- Soft-looking zoom: zoom only works well from 4K sources. Keep zoom at 1.3 or less on 1080p clips.
- A caption is too wide and wraps to two lines: lower `maxWords` or give that chunk `"size": 0.85`.

## Cutout (optional step)
- Needs Node 22+. On Windows and Linux it runs on the CPU and can take a long time: run it in the background and
  keep working on captions meanwhile.
- "Frame mismatch": the A-roll changed after the cutout. Re-run cutout.py.
- Words set to `"layer": "back"` show in front until `work/subject.webm` exists.

## Delivery
- Big files can fail to upload into chat: send the `-phone.mp4` copy (720p) and keep the full render on disk.
