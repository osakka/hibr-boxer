# hibr-boxer

DOSBox on the [hibr](https://git.home.arpa/itdlabs/hibr)
desktop, shelved the way [Boxer](https://boxer.thelaboratory.net/) shelves
them on a Mac (this is not that application, only inspired by it): one **gamebox** per game, a **shelf** of them with their
covers, double-click to play.

**Status: working; the deb is in the hibr apt repo and the apps are in hibr-apps.** DOSBox Pure runs through our own libretro frontend and is drawn by hibr's renderer; the shelf (`apps/Games/boxer.hibr`) lists gameboxes as a grid of covers, a game plays in a window of its own (`apps/boxerplay.hibr`), and a folder, zip, CD image or program imports into a new gamebox. Design: [docs/DESIGN.md](docs/DESIGN.md); the engine route is
[ADR 0001](docs/adr/0001-two-ways-to-put-an-emulator-in-a-window.md) (our own libretro frontend; spike passed, see [docs/spike-1-frame-rate.md](docs/spike-1-frame-rate.md)); DOS only: [ADR 0002](docs/adr/0002-dos-only.md).

```text
make && cores/build.sh WORK OUT        # the module, and DOSBox Pure from pinned source
make check check-retro                 # the driver and the module
DBP_CORE=OUT/dosbox_pure_libretro.so make check-boxer   # the apps, and the whole way on the real core
boxer.hibr import ~/Games/prince       # from a shell: a folder, zip, .iso/.cue or program
```

How a game is run: `gamebox.json` names the program and the CD images, `engine/dosbox.conf` is the person's own settings; at launch they become one `run.conf` (settings first, then an `[autoexec]` that mounts `drives/c` as C: and starts the program) that DOSBox Pure is given as its content. The game's own saves go to `drives/c`, as on a real disk.

| piece | where it will live |
|---|---|
| **boxer**, the shelf window, and **boxerplay**, the game window | `apps/Games/` here; published to [hibr-apps](https://git.home.arpa/itdlabs/hibr-apps) with `addapp` |
| the **gamebox** format | [DESIGN.md §3](docs/DESIGN.md#3-the-gamebox) |
| `retro`, the native libretro-frontend module | `mods/retro/` here; packaged for deb, Homebrew and the AUR |
| the emulators themselves | DOSBox Pure, built from pinned source by `cores/build.sh` (3 MB); ScummVM was dropped, see [ADR 0002](docs/adr/0002-dos-only.md) |

Licence: MIT, as the rest of hibr.
