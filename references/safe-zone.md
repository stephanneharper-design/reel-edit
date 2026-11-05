# Safe zone and placement (1080x1920)

Instagram covers parts of the reel with its own interface. Keep text and inserts out of:
- the top 220 px (header),
- everything below y = 1470 (username, caption, audio),
- 35 px on each side,
- the right 100 px from y = 1155 down (like, comment, share buttons).

`render.py --safe` paints these areas red. Check a preview with `check.py --at <times>`, then render without
`--safe` for delivery.

## Where things go
- Captions: centred on the chest, y around 1150 to 1300. Never between the eyes and the chin.
- Emphasis words: same band, or just above the head when the user is framed low with headroom.
- Hook title: y around 330 to 400, above the head.
- Inserts (screenshots, app recordings, cards): width 700 to 900, bottom edge at or above y 1470. Either beside or
  above the head on the wall, or below the chin with captions moved up or skipped while it shows. Hold each for
  at least 1.5 s so it can be read.
- Words behind the head (cutout only): place the word so its bottom quarter goes behind the top of the head. If
  the head moves a lot during that word, put it in front over the chest instead.
