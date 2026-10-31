# Changelog

What shipped, newest first. **Boxer** is the app (the catalogue's `boxer`, with `boxerplay` and
`boxerset`); **hibr-retro** is the deb (the `retro` module and DOSBox Pure). A line names the hibr
or Blit release a feature needs when it needs one. Dates are 2026.

## Boxer 1.26 (Nov 1)
- **Full screen is the desktop's own** (hibr 0.99.403): Boxer's own full-screen key and its Control Panel
  row are gone, and so is the zoom fallback. Alt+Enter, Window > Full Screen and the title bar's menu
  work on a game like any window, and Ctrl+F11 leaves it. A key the desktop has assigned is handed back
  to it, so nothing is lost. Needs hibr 0.99.403.

## Boxer 1.25 (Oct 31)
- **Find Cover** replaces Fetch Cover: a window with the game's name already searched, the candidates
  side by side as pictures (box art, title screens, screenshots, found loosely, so different spellings
  show together), the best one marked so Enter keeps it; type to change the search, arrows or a click to
  choose, Esc to close, a dropped picture to use it. Nothing to answer.
- Downloads use hibr's own `fetch` (HTTPS, certificates checked) instead of `curl`, which is the
  fallback.

## Boxer 1.24 (Oct 31)
- **Box art, matched better and with no questions.** The matcher now reads names the way the
  libretro list writes them (colons as underscores, "The" at the end, years, demos, apostrophes),
  handles sequels, Roman numerals, `&`, missing spaces ("Sim City", "keen1"), short DOS folder
  names (PRINCE, LSL2, KQ5, WOLF3D), and one slip of a letter in a long name; and it refuses a
  sequel for its first game and a plural for another game. A game with no box art gets its title
  screen. Fetch Cover no longer asks first: choosing it is the asking. Fetching is a background
  job, one at a time, with a note. A renamed game with no cover is looked for by its new name.
  Still off by default (it sends the game's name to a server).

## Boxer 1.23 (Oct 30)
- A captured relative-mouse game whose pointer is not held says so and why ("no screen can hold
  it: Restart Desktop, or Blit older than 0.2.42", no focus, refused).

## Boxer 1.22 (Oct 29)
- When a game ends its window asks to be closed (`dt_wantclose`) instead of deleting itself in the
  middle of a frame, which was the cause of a stale-position warning in hibr (#408).

## Boxer 1.21 (Oct 29)
- **The program list takes the mouse.** A click on a program runs it. (The desktop sends a click to
  `_mouse` and never to `_click` when an app has both, so the list only ever worked with keys.)
- A captured mouse survives going full screen: the pointer is hidden again, and a lock that drops
  within 1.5 s of the change is asked for again.

## Boxer 1.20 – 1.17 (Oct 29)
- 1.20: **CPU** in Get Info (auto, 386, 386 slow, 386 prefetch, 486 slow, Pentium slow).
- 1.19: **Speed Limit**, by era, for all games and per game; Pentium 100 by default.
- 1.18: Alt+Enter says why when it can only maximise.
- 1.17: **true full screen** (hibr 0.99.380): Alt+Enter takes the whole display; Ctrl+F11 or Alt+Enter
  leaves it. 1.16 turned it off for a day while hibr drew blank under it; 1.15 first wired it.

## Boxer 1.14 – 1.12 (Oct 28)
- 1.14: **the mouse is relative by default**; an old saved `direct` moves to relative once.
- 1.13: **Game > Relative Mouse**, live and remembered per game; the first capture of a direct game
  says where it is.
- 1.12: the pointer lock logs in `desktop.log` why it was or was not asked and how it ended.

## Boxer 1.11, hibr-retro 0.1.6 and 0.1.7 (Oct 27–28)
- **Pointer lock** (hibr 0.99.365, Blit 0.2.42): a captured relative-mouse game is locked, the game
  gets raw motion (`retro motion`), the desktop's Release Pointer key lets it go.
- About credits what it runs on; `make core` builds DOSBox Pure from pinned source and records what
  was built; hibr-retro 0.1.7 cites the source tarball kept in the apt repo.

## Boxer 1.10 – 1.8 (Oct 26–27), hibr-retro 0.1.4 and 0.1.5
- 1.10: typing `EXIT` at the DOS prompt closes the window (the core is told to exit).
- 1.9: **Confirm On Exit** and **Close When Game Ends**; the module wakes the desktop when a core ends.
- 1.8: a second game while one plays says which is running and brings it forward.
- hibr-retro 0.1.4: a window over a game no longer blanks it (`retro draw` places the picture in its pane).

## Boxer 1.7 – 1.1 (Oct 23–24), hibr-retro 0.1.3
- 1.7: mouse capture on a click (or seamless), a release key.
- 1.5: the MIDI Output list showed nothing (an undeclared variable); fixed.
- 1.4: **3dfx Voodoo** per game.
- 1.3: the terminal's pointer is hidden over a playing game (hibr 0.99.311, Blit 0.2.8).
- 1.1: the pointer follows the mouse over a game (hover, hibr 0.99.304), to the pixel where the
  terminal reports pixels; the mouse degrades step by step.

## Boxer 1.0 and before (Oct 20–21)
- 1.0: the shelf is gone: the **Boxer** window imports (drop or Import), games are `NAME.boxer`
  folders played from Files, the program chooser is in the game window.
- 0.9 – 0.6: `boxer.json`, rename in Game Settings, box art, `.boxer` folders registered with hibr.
- 0.x: how a game is read follows Boxer's own rules; discs are CD-ROMs in D:; MIDI (SoundFonts, MT-32,
  Sound Canvas); sound card IRQ, DMA, port; Control Panel pane; per-game settings.
- hibr-retro 0.1.0 – 0.1.2: the libretro frontend module (`retro`), DOSBox Pure built from pinned
  source, the first deb. The engine route is [ADR 0001](docs/adr/0001-two-ways-to-put-an-emulator-in-a-window.md);
  ScummVM was dropped ([ADR 0002](docs/adr/0002-dos-only.md)).
