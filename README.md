# hibr-boxer

DOSBox on the [hibr](https://git.home.arpa/itdlabs/hibr)
desktop, shelved the way [Boxer](https://boxer.thelaboratory.net/) shelves
them on a Mac (this is not that application, only inspired by it): one **gamebox** per game, a folder of them, shown by Files, with their
covers, double-click to play.

**Status: working; the deb is in the hibr apt repo and the apps are in hibr-apps.** DOSBox Pure runs through our own libretro frontend and is drawn by hibr's renderer; the Boxer window (`apps/Games/boxer.hibr`) is where a game is brought in (drop a folder, zip, CD image or program on it, or Import), a game is a `NAME.boxer` folder that Files plays on a double click (`apps/boxerplay.hibr`, which asks which program to run when none is chosen), and a right click in Files offers Get Info, Fetch Cover and Game Is Already Installed. Design: [docs/DESIGN.md](docs/DESIGN.md); the engine route is
[ADR 0001](docs/adr/0001-two-ways-to-put-an-emulator-in-a-window.md) (our own libretro frontend; spike passed, see [docs/spike-1-frame-rate.md](docs/spike-1-frame-rate.md)); DOS only: [ADR 0002](docs/adr/0002-dos-only.md).

```text
make && make core                      # the module, and DOSBox Pure from pinned source into build/cores
make check check-retro                 # the driver and the module
DBP_CORE=build/cores/dosbox_pure_libretro.so make check-boxer   # the apps, and the whole way on the real core
boxer.hibr import ~/Games/prince       # from a shell: a folder, zip, .iso/.cue or program
```

Settings: a game's Get Info also sets its 3dfx Voodoo (the core has it on, 8 MB; 12 MB for dual texture, 4 MB, or off) and its speed (multi-threaded or single, or low quality). Control Panel > Boxer is for every game (the games folder, which defaults to `~/Dos Games`; rendering, shape, full screen key, key hold, mouse, sound). A mouse is captured on a click (Control Panel > Boxer > Mouse Capture, or a game's own Capture; seamless instead has it all the time), hidden while it is, and let go on the release key (F12 to begin with) or when it leaves the window. The mouse is relative by default (Control Panel > Boxer > Mouse; the older default, direct, is moved to relative once). A game that wants the pointer to sit under the mouse is set to direct in its Get Info, and Game > Relative Mouse switches it while playing and remembers it for that game (the first capture of a game on the direct mouse says so), and Get Info's Mouse row sets it too. A game whose mouse is relative is also locked where the terminal can hold the pointer (Blit 0.2.42 with hibr 0.99.365): the pointer stays still and the game gets raw motion, so it can turn without end, and the desktop's Release Pointer key (Control Panel > Shortcuts, Ctrl+F10 to begin with) gives it back; elsewhere it is let go at the window's edge as before. The pointer follows the mouse over a game wherever hibr's hover is on (Auto on Blit, kitty and foot), to the pixel where the terminal reports pixels, and a press and drag elsewhere. A game's own go in its Get Info window (right-click it in Files), Boxer's own way, written into the box's `boxer.json`, where `default` means the Control Panel's: its name (changing it renames the folder too), the program (a drop-down of the DOS programs found), speed, graphics, sound card and its IRQ, DMA and port, MIDI and mouse. MIDI: Control Panel > Boxer > Synth Folder points at a folder of SoundFonts and Roland ROMs (MT32_CONTROL.ROM with MT32_PCM.ROM, ROM1.BIN for a Sound Canvas, or a .sf2), which DOSBox Pure plays through; MIDI Output chooses one, for every game or for one. The folder for a game is `NAME.boxer`; an older `NAME.gamebox` still shows.

How a game is read, and what the shelf does with it, follows Boxer's own rules: see [docs/boxer-rules.md](docs/boxer-rules.md). A game with an installer is set up to run it first (the source is D:); when you close the window what it put on C: is the game. `boxer.hibr import --installed PATH` skips the installer.

How a game is run: `boxer.json` names the program and the CD images, `engine/dosbox.conf` is the person's own settings; at launch they become one `run.conf` (settings first, then an `[autoexec]` that mounts `drives/c` as C: and starts the program) that DOSBox Pure is given as its content. The game's own saves go to `drives/c`, as on a real disk.

| piece | where it will live |
|---|---|
| **boxer**, the import window, and **boxerplay**, the game window | `apps/Games/` here; published to [hibr-apps](https://git.home.arpa/itdlabs/hibr-apps) with `addapp` |
| the **gamebox** format | [DESIGN.md §3](docs/DESIGN.md#3-the-gamebox) |
| `retro`, the native libretro-frontend module | `mods/retro/` here; packaged for deb, Homebrew and the AUR |
| the emulators themselves | DOSBox Pure, built from pinned source by `cores/build.sh` (3 MB); ScummVM was dropped, see [ADR 0002](docs/adr/0002-dos-only.md) |

Licence: MIT, as the rest of hibr.

## Box art

A game's cover is `.cover.png` in its box (`cover.png` is read too). One you put there always wins; one that came with a game, or sits beside it, is taken in on import. When **Control Panel > Boxer > Fetch Box Art** is on (it is off by default: it sends the game's name to a server), import also fetches the picture from the libretro thumbnails project (https://thumbnails.libretro.com/DOS/Named_Boxarts/), matched by name: the same name, or, for a numbered game such as "Leisure Suit Larry 2", the title that begins with it. A series name alone is not guessed at. A download is kept only if it is a PNG. Fetching waits on the network (up to half a minute a download), as an import waits on its copying. `boxer.hibr cover BOX [PNG]` fetches or sets one, `boxer.hibr covers` fills in the shelf, and a game's right-click menu in Files has Fetch Cover.

## What it runs on

The emulator is **DOSBox Pure**, by Bernhard Schelling, which is built on **DOSBox** by the DOSBox Team; inside it the MT-32 is **Munt** (Dean Beeler, Jerome Fisher, Sergey V. Mikayev, LGPL-2.1+) and the OPL3 and SC-55 are **Nuked** (Nuke.YKT). It speaks **libretro**. DOSBox Pure is GPL-2.0 or later. Boxer's About window names all of them, and the deb's `copyright` file lists them.

DOSBox Pure is built here from source and never changed. `cores/PINS` names a tag and the commit that tag must be, and `cores/build.sh` (`make core`) refuses anything else, however the source was reached: a url may be a list, and `CORES_URL_dosbox_pure` puts a mirror of your own first. It leaves `dosbox_pure_libretro.so.build` beside the core, recording the source, tag, commit, compiler and checksum of what was built, and the deb carries that record. The build is the same source with whatever compiler you have, so the checksum can differ from ours; the commit cannot. The suite checks that the core under test is the pinned version. DOSBox Pure's home is https://codeberg.org/schelling/dosbox-pure: it moved there when its author's account was renamed, and the old GitHub and `schellingb` addresses only point on.

## Credit

hibr-boxer is a tribute to Boxer, the DOS game box for the Mac, by Alun Bestor (https://boxerapp.com, https://github.com/alunbestor/Boxer). How a game is recognised, installed and shelved follows Boxer's own rules (see `docs/boxer-rules.md`); About Boxer says so.
