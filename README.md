# hibr-boxer

DOSBox on the [hibr](https://git.home.arpa/itdlabs/hibr)
desktop, shelved the way [Boxer](https://boxer.thelaboratory.net/) shelves
them on a Mac (this is not that application, only inspired by it): one **gamebox** per game, a **shelf** of them with their
covers, double-click to play.

**Status: design sketch. Nothing is built.** Read
[docs/DESIGN.md](docs/DESIGN.md); the engine route is
[ADR 0001](docs/adr/0001-two-ways-to-put-an-emulator-in-a-window.md) (accepted: our own libretro frontend; spike 1 passed, see [docs/spike-1-frame-rate.md](docs/spike-1-frame-rate.md)).

| piece | where it will live |
|---|---|
| **boxer**, the application (the Shelf window), and its Control Panel pane | `apps/`, `control-panel/` here; published to [hibr-apps](https://git.home.arpa/itdlabs/hibr-apps) with `addapp` |
| the **gamebox** format | [DESIGN.md §3](docs/DESIGN.md#3-the-gamebox) |
| `retro`, the native libretro-frontend module | `mods/retro/` here; packaged for deb, Homebrew and the AUR |
| the emulators themselves | DOSBox Pure, built from pinned source by `cores/build.sh` (3 MB); ScummVM was dropped, see [ADR 0002](docs/adr/0002-dos-only.md) |

Licence: MIT, as the rest of hibr.
