# Spike 1 — frame rate through hibr's display

Run 2026-10-20 on the owner's machine, hibr 0.99.269 (ABI 16), tree build.
`spike/framebench.c` is a throwaway module that draws synthetic 320x200 frames
through the display interface; `spike/run.py` runs it in a pty drained as fast
as Python can, with the terminal's pixel protocol forced by `HIBR_GFX` and an
8x16 cell. Run it again: `gcc -O2 -shared -fPIC -I../hibr/include -I../hibr/mods
-o build/framebench.so spike/framebench.c && python3 -I spike/run.py 120`.

## What it measures, and what it does not

- Measured: the producer's cost per frame (scaling, encoding, writing the diff)
  and the bytes that go down the pty.
- **Not measured:** a real terminal receiving and painting those bytes. A pty
  drained by a script is faster than any terminal. The producer numbers are a
  ceiling, not a frame rate you will see.
- The scene is synthetic. "calm" moves a strip and three sprites; "busy"
  cycles every pixel. Kitty sends the whole frame either way; half blocks only
  send cells that changed.
- `xscr` was **not** measured, so "the X Screen app is N times slower" is still
  an unmeasured claim. (No DOSBox is installed here; a trivial X client would do.)

## Results (60 frames each; per-frame producer cost; max producer fps = 1000/mean)

| terminal says | cells | mean ms | p95 ms | kB/frame to the terminal | max fps (producer) |
|---|---|---|---|---|---|
| kitty, native 320x200 | 80x25 | 3.0-3.5 | 4.0-4.6 | 251 | ~280-330 |
| kitty, native 320x200 | 120x40 | 3.6-3.8 | 5.8-6.8 | 251 | ~260-275 |
| sixel | 80x25 | 13.0-13.4 | 14.3-15.6 | 40 | ~75 |
| sixel | 120x40 | 32-33 | 36 | 80-84 | **~31** |
| half blocks | 80x25 | 0.49 | 0.9-2.0 | 6-11 | ~2000 |
| half blocks | 120x40 | 0.9 (calm), 2.0 (busy) | 2.0-3.3 | 15 (calm), **108** (busy) | ~490-1090 |

## What it says

1. **The gate passes for kitty and half blocks.** Producer cost is far below a
   30 fps budget (33 ms) and below 60 fps (16.7 ms).
2. **Kitty is bytes-bound, not CPU-bound.** The console already sends a bitmap
   at the source's own size and lets the terminal scale it (image.c: "never
   larger than the source"), so native-size sending is not a thing route B has
   to add. A frame is 251 kB of base64: 15 MB/s at 60 fps. Fine on a local
   terminal; unusable over a slow ssh link. The levers that remain are zlib
   (`o=z`, currently only for a wallpaper), shared memory or file transfer
   (`t=s`/`t=t`, local only), and not resending an unchanged frame.
3. **Sixel is the weak path and gets worse with window size**: it must be
   scaled to the pixel exactly, so 120x40 cells is 960x640 pixels per frame
   for a 320x200 picture. About 31 fps at that size on the producer side
   alone, before the terminal paints it. An integer 2x or 3x render at a
   smaller cell footprint is the thing to try.
4. **Half blocks cost bytes only when a lot changes** (108 kB/frame when every
   pixel cycles at 120x40), and nothing in CPU.
5. This does not support a "10-50x faster" claim for route B over `xscr`; it
   shows route B's own costs are small. The comparison has not been run.

## Next

- Run `spike/run.py` inside a real kitty and a real foot (or WezTerm) and read
  the achieved rate with a human watching; the pty number is not that.
- Time `xscr` on a trivial X client for the baseline.
- Try zlib and `t=s` for non-wallpaper kitty frames in a scratch build.
