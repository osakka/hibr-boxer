# retro

A libretro frontend as a hibr module: `need retro`. A core (DOSBox, ScummVM, the test core) is a shared
object; the module loads it, runs it on a thread of its own, and draws its picture through the display
interface, as pixels where the terminal has them and half blocks where it does not.

```text
need retro
id := retro open dosbox_pure ~/Games/doom.gamebox/drives/c -o dosbox_pure_machine=svga
fd := retro fd $id; console watch $fd          # readable once a new frame is there
retro size $id 80 25 pixels                    # the cells it fills
retro aspect $id 4:3                           # DOS pixels are not square
retro frame $id && retro draw $id 1 1          # a new frame? draw it
retro key $id left; retro mouse $id 10 20 1    # input
retro info $id                                 # core, version, width, height, fps, rate, frames, paused, ended, output, mode, drawn, error
retro close $id
```

| verb | does |
|---|---|
| `open CORE [GAME] [-s SYSDIR] [-S SAVEDIR] [-o key=value]...` | load a core by path or by name (`HIBR_RETRO_CORES`, `$XDG_DATA_HOME/hibr/retro/cores`, `/usr/local/lib/hibr/cores`, `/usr/lib/hibr/cores`; `NAME_libretro.so` or `NAME.so`); gives the player's number |
| `list`, `close ID\|all` | |
| `fd ID`, `wake ID` | a descriptor readable when a new frame is there, for `console watch`; empty it |
| `frame ID` | status 0 when a frame has been made since the last draw |
| `size ID COLS ROWS [pixels\|half]`, `aspect ID 4:3\|auto\|RATIO` | the cells it fills, and the shape of the picture in them |
| `draw ID ROW COL [-p PANE]` | the latest frame, its shape kept, in the rectangle |
| `key ID NAME [down\|up\|tap]` | a key by the console's name. `tap`, the default, holds it for `hold` ms after each report, since a terminal sends no key release (hibr #315) |
| `hold ID MS`, `mouse ID ROW COL BUTTONS [WHEEL]`, `pad ID MASK` | the hold time; the pointer at a screen cell over the picture, buttons 1 left 2 right 4 middle; the joypad |
| `pause`, `play`, `toggle`, `reset ID`, `option ID KEY VALUE`, `save ID FILE`, `load ID FILE` | |
| `info ID` | a map, or `name<TAB>value` lines |

Sound goes to PipeWire/Pulse/ALSA/AudioQueue as in hibr's `media`; `HIBR_RETRO_AUDIO` is `pulse`, `alsa`,
`audioqueue`, `none` or `wav:PATH`. The audio write is what paces the core.

## Files

| | |
|---|---|
| `rl.c`, `rl.h` | the driver: a core on its own thread, with no dependence on the shell or a display. Tested alone by `tests/rl_harness.c` |
| `retro.c` | the builtin |
| `ra.c`, `ra.h` | where sound goes: a copy of hibr's `mods/media/ao.c`, renamed |
| `libretro.h` | upstream's (MIT), libretro-common commit a3194c18, 2026-10-11 |
| `display.h` | hibr's `mods/display.h`, DP_API_VER 6. `make install` does not install it |

## What to know

- **One thread makes every call into a core**, from `retro_set_environment` to `retro_deinit`, because many
  cores insist. The shell thread only posts messages and reads the latest frame.
- **A core runs in the shell's process.** A crash in a core takes the desktop with it. A core file runs
  once in a process (a second `open` of the same file is refused, since its globals would be shared); a
  *copy* of the file is a separate core, and two different cores run together, the driver's callback state
  being per thread. The way out, if any of this bites, is the driver in a child process with frames over a pipe.
- **`hold` must be longer than the terminal's key-repeat delay to hold a key**, and shorter than a tap should
  last. A terminal reports a press and, after its initial delay (commonly 250-500 ms), repeats; with no release
  event (hibr #315) the default 120 ms makes a held key press, let go, then press again when repeats start.
  120 is chosen because a stuck key in a text field is worse than a stutter in a walk. It is a per-game
  setting; only #315 fixes it.
- **Built with tcc**, as hibr is (`make`; `make CC=gcc` for sanitizers). `rl_lock` hands back a copy of the
  frame, so drawing it never holds up the core.
- **Environment calls not handled are logged** at debug level (`hibr -d 3`) and refused; run a real core and
  add what it asks for. Hardware rendering is refused: software only.

## Real cores

`cores/build.sh WORKDIR OUTDIR` builds ScummVM and DOSBox Pure from the revisions in `cores/PINS`. Both load and run through `retro open`: ScummVM (v2026.4.0) detects a game directory and draws it, DOSBox Pure (1.0-preview7) runs at 70 fps. ScummVM needs `scummvm.zip` unpacked in the system directory (`-s`). `build/rl_shot` (`tests/rl_shot.c`) writes a core's latest frame as PPM.
