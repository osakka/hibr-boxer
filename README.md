# hibr-boxer

DOS games on the [hibr](https://git.home.arpa/itdlabs/hibr) desktop, kept the way
[Boxer](https://boxerapp.com) keeps them on a Mac (this is not that application, only inspired by
it): one **`NAME.boxer`** folder per game, shown by Files with its cover, double-click to play. The
emulator is DOSBox Pure, run through our own libretro frontend and drawn by hibr's own renderer, so
it works in any terminal hibr runs in.

Design history: [docs/DESIGN.md](docs/DESIGN.md) (start with "Where it stands"). What changed and
when: [CHANGELOG.md](CHANGELOG.md). Why the engine is what it is:
[ADR 0001](docs/adr/0001-two-ways-to-put-an-emulator-in-a-window.md) (our own libretro frontend),
[ADR 0002](docs/adr/0002-dos-only.md) (DOS only).

## Install

```text
sudo apt install hibr-retro            # the retro module and DOSBox Pure, from the hibr apt repo
```

then, in the hibr desktop, install **Boxer** from the catalogue (it is in Games, and brings its own
Control Panel pane), and Restart Desktop. `hibr-retro` needs hibr 0.99.365 or newer; what each
feature needs is in the table at the end of "Playing".

## Playing

- **Bring a game in.** Open **Boxer** (the window with a diskette and a CD). Drop a folder, a zip,
  a CD image (`.iso`, `.cue`) or a program on it, or press **Import**. Boxer reads what is there
  the way Boxer does ([docs/boxer-rules.md](docs/boxer-rules.md)): a game with an installer runs
  it first (the source is D:), and when you close the window what it put on C: is the game;
  a game already installed is copied in. It lands in the games folder (`~/Dos Games`; Control Panel
  > Boxer > Folder, under Games). From a shell: `boxer.hibr import PATH` (`--installed` skips the
  installer).
- **Play.** Double-click the `.boxer` folder in Files. A game with several programs and none chosen
  asks which to run, in a list you can click or use the arrow keys on; the choice is remembered. Only
  one game runs at a time: opening a second says which one is running and brings it forward.
- **Get Info.** Right-click a game in Files for **Get Info** (its own settings, written into its
  `boxer.json`; `default` means the Control Panel's): name (the folder is renamed with it), program,
  speed, graphics, 3dfx Voodoo and its speed, sound card and its IRQ, DMA and port, MIDI, mouse,
  capture, **Speed Limit** and **CPU**. The same menu has **Fetch Cover** and **Game Is Already
  Installed**.
- **Quitting.** **Close When Game Ends** closes the window when the game ends (typing `EXIT` at the
  DOS prompt ends it); **Confirm On Exit** asks before closing a game that is playing. Both are on
  by default (Control Panel > Boxer).

### The mouse

- **Relative by default** (Control Panel > Boxer > Mouse), which is what games that turn with the
  mouse want (Doom and the like). A game that wants the pointer to sit under the mouse is set to
  `direct` in its Get Info. **Game > Relative Mouse** switches it while you play and remembers it
  for that game; the first capture of a game on the direct mouse says so.
- **Capture.** A click in the game captures the mouse (Control Panel > Boxer > Mouse Capture, or a
  game's own Capture; *seamless* has it all the time). It is hidden while captured. If the pointer
  is not actually held (a terminal that cannot), the note says so and why.
- **Pointer lock.** Where the terminal can hold the pointer still (Blit 0.2.42 and newer, with hibr
  0.99.365 and newer), a captured relative-mouse game is locked: the game gets raw motion and can
  turn without end. The desktop's **Release Pointer** key (Control Panel > Shortcuts, Ctrl+F10 to
  begin with) lets it go. Elsewhere the pointer is let go at the window's edge, on **Release Mouse
  Key** (Control Panel > Boxer; F12 to begin with).
- The pointer follows the mouse over a game wherever hibr's hover is on (Auto on Blit, kitty and
  foot), to the pixel where the terminal reports pixels.

### Full screen

**Alt+Enter** takes the whole display, with no menu bar or frame; **Ctrl+F11** (the desktop's own
Leave Full Screen key) or Alt+Enter again gives it back. The key is Control Panel > Boxer > Full
Screen Key. On a hibr older than 0.99.380 Alt+Enter only maximises, and says so.

### Speed

DOS games never sleep: they loop, waiting for the next frame. An emulator left to run as fast as it
can spends a whole core on that loop. So the emulated machine is **limited to a Pentium 100** by
default (Control Panel > Boxer > Speed Limit, or a game's own Speed Limit in Get Info: unlimited,
Pentium II 300, Pentium 100, 486 DX2/66, 486 DX/33 or 386). Measured on an i3-N300 at an idle
prompt: 100% of a core unlimited, 71% at Pentium II, 40% at Pentium 100, 20% at a 486 DX2; Boxer's
own drawing cost 6 to 13% of a core for a full-screen repaint at 70 frames a second. A game that
needs more is raised in its Get Info. **CPU** in Get Info sets the emulated CPU type for the rare
game that wants a particular one (the core's own Auto is fastest).

### Sound and MIDI

Control Panel > Boxer > Sound and Sound Card. **Synth Folder** points at a folder of SoundFonts and
Roland ROMs (`MT32_CONTROL.ROM` with `MT32_PCM.ROM`, `ROM1.BIN` for a Sound Canvas, or a `.sf2`),
which DOSBox Pure plays through; **MIDI Output** chooses one, for every game or for one.

### What each thing needs

| feature | needs |
|---|---|
| the player, import, Get Info, speed limit | hibr 0.99.365 with `hibr-retro` 0.1.7 |
| a cover shown in Files | hibr 0.99.281 |
| hover, and the pointer to the pixel | hibr 0.99.304; Blit, kitty or foot |
| pointer hiding while captured | hibr 0.99.311; Blit 0.2.8 |
| pointer lock | hibr 0.99.365 and `hibr-retro` 0.1.6; Blit 0.2.42; Restart Desktop after upgrading |
| true full screen | hibr 0.99.380; 0.99.392 for two displays |

## Box art

A game's cover is `.cover.png` in its box (`cover.png` is read too). One you put there always wins;
one that came with a game, or sits beside it, is taken in on import.

**Fetching** is from the libretro thumbnails project (https://thumbnails.libretro.com/DOS/): the
game's box art, or, for a game with none, its title screen (which is at least never another game's
box; Boxer records which it is). It sends the game's name to that server, so it is **off by default**.

- **Fetch Cover** (right-click a game in Files) looks at once and says what it found: choosing it is
  the asking, there is no question. A found cover closes the window by itself.
- **Control Panel > Boxer > Fetch Box Art**, when on, gives every import its cover, and a game that
  has none gets one when it is renamed to its proper name. Inside the desktop each fetch is a
  background job, one at a time, with a note when it is done; from a shell it waits.
- **Matching** is careful, because a wrong cover is worse than none. Names are made alike first
  (case, `(year)` and `[tags]`, apostrophes, a leading or trailing "the", `&` and "and", spaces
  ("SimCity", "Sim City"), `keen1` as "keen 1", Roman numerals), then the same name wins, then a
  numbered game ("Larry 2") finds the title with its subtitle, a format suffix (`sci`, `vga`) is
  allowed, and one slip of a letter in a long name is forgiven, never in a number or at the end
  (which is the difference between a game and its sequel). A series name alone is not guessed at, a
  sequel is not taken for its first game, and a demo is the last choice. A few short folder names
  (PRINCE, LSL2, KQ5, WOLF3D) are spelled out first. Against the real 4,659-name list, every name
  finds itself and none finds another game's.
- A download is kept only if it is a PNG of a sane size.
- From a shell: `boxer.hibr cover BOX [PNG]` fetches or sets one, `boxer.hibr covers` fills in the
  shelf (and swaps a title screen for box art where there is some).

## What it runs on

The emulator is **DOSBox Pure**, by Bernhard Schelling, which is built on **DOSBox** by the DOSBox
Team; inside it the MT-32 is **Munt** (Dean Beeler, Jerome Fisher, Sergey V. Mikayev, LGPL-2.1+) and
the OPL3 and SC-55 are **Nuked** (Nuke.YKT). It speaks **libretro**. DOSBox Pure is GPL-2.0 or
later. Boxer's About window names all of them, and the deb's `copyright` file lists them.

## Building

```text
make && make core                      # the module, and DOSBox Pure from pinned source into build/cores
make check check-retro                 # the driver and the module
DBP_CORE=build/cores/dosbox_pure_libretro.so make check-boxer   # the apps, and the whole way on the real core
```

DOSBox Pure is built here from source and never changed. `cores/PINS` names a tag and the commit
that tag must be, and `cores/build.sh` (`make core`) refuses anything else, however the source was
reached: a url may be a list, and `CORES_URL_dosbox_pure` puts a mirror of your own first. It leaves
`dosbox_pure_libretro.so.build` beside the core, recording the source, tag, commit, compiler and
checksum, and the source as a tarball; the deb carries the record and cites the tarball, which is
kept in the apt repo. The build is the same source with whatever compiler you have, so the checksum
can differ from ours; the commit cannot. The suite checks that the core under test is the pinned
version. DOSBox Pure's home is https://codeberg.org/schelling/dosbox-pure (it moved there when its
author's account was renamed; the old GitHub and `schellingb` addresses only point on).

`packaging/deb/build-deb.sh CORES` builds the `hibr-retro` package; `mods/retro/README.md` is the
module's own documentation (the `retro` command).

| piece | where |
|---|---|
| **boxer** (the import window) and **boxerplay** (the game window), with their Control Panel pane | `apps/Games/boxer.hibr`, `apps/boxerplay.hibr`, `control-panel/boxerset.hibr`; published to hibr-apps with `addapp` |
| the **gamebox** format | [DESIGN.md §3](docs/DESIGN.md#3-the-gamebox) |
| `retro`, the native libretro-frontend module | `mods/retro/`; packaged as `hibr-retro` |
| the emulator | DOSBox Pure, built by `cores/build.sh` (3 MB) |

How a game is run: `boxer.json` names the program and the CD images, `engine/dosbox.conf` is the
person's own settings; at launch they become one `run.conf` (settings first, then an `[autoexec]` that
mounts `drives/c` as C: and starts the program) that DOSBox Pure is given as its content. The game's
own saves go to `drives/c`, as on a real disk. An older `NAME.gamebox` folder still shows.

## Credit

hibr-boxer is a tribute to Boxer, the DOS game box for the Mac, by Alun Bestor
(https://boxerapp.com, https://github.com/alunbestor/Boxer). How a game is recognised, installed and
shelved follows Boxer's own rules (see [docs/boxer-rules.md](docs/boxer-rules.md)); About Boxer says so.

Licence: MIT, as the rest of hibr.
