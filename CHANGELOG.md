# Changelog

What shipped, newest first. **Boxer** is the app (the catalogue's `boxer`, with `boxerplay` and
`boxerset`); **hibr-retro** is the deb (the `retro` module and DOSBox Pure). A line names the hibr
or Blit release a feature needs when it needs one. Dates are 2026.

## Boxer 1.40 (Nov 8)
- Tarballs (`.tar`, `.tar.gz`, `.tgz`) are opened by hibr's `archive` module alone, including one made with
  `tar czf x.tgz .` (hibr #487, fixed in 0.99.468); `tar` is only for `.tar.xz` and `.tar.bz2` now. Needs
  hibr 0.99.468.

## Boxer 1.39 (Nov 8)
- **More of it is hibr.** The cover matcher (strict and loose) is hibr script now, not awk: the same answers on
  483 real queries against the real lists (each name's matcher form is kept in the list's cache, so a search of
  all 20,000 names takes about half a second). The list of covers is read with `match` and `rsub`, not `grep`,
  `sed` and `paste`. A picture is checked and measured with `img` (not by its first bytes with `od`), and any
  PNG or JPEG is saved as a PNG cover by `img save`. Tarballs are opened by hibr's `archive` module (`tar` stays
  for `.tar.xz`, `.tar.bz2` and a tarball the module refuses). The search address is encoded in script.
- The README now lists what Boxer still calls outside hibr and why. Needs hibr 0.99.404.

## Boxer 1.38 (Nov 7)
- **No `curl` at all.** Downloads (the covers and the lists of names) use hibr's own `fetch` only; the `curl`
  fallback, which only ever hid a `fetch` that had failed, is gone. Without the `fetch` module a download fails
  and Find Cover says it could not get the list.

## Boxer 1.37 (Nov 7)
- Fixes 1.36 on a terminal that cannot report key releases: hibr says `press` for every key there, which 1.36 took
  for "releases are on" and so left such a key down in the game. Releases are now used only for the window the
  desktop names as having them (`DT_PHASEWIN`); otherwise a press is held for Key Held ms, as before.

## Boxer 1.36, hibr-retro 0.1.9 (Nov 7)
- **Real key releases** (hibr 0.99.466, a terminal that reports them: Blit 0.3.61). A key is down in the game for
  as long as it is held, so two keys at once work, lifting one while holding another is right, and Shift, Ctrl
  and Alt are keys of their own. Where releases are not reported a press is still held for Key Held ms. The
  module has `retro keyraw ID SPEC down|up [MODS]` for it (0.1.9); an older module is noticed and presses are held.
- Boxer 1.35 (hibr, Nov 7): the game window reads full screen from the desktop's own `_fullscreen` callback.

## hibr-retro 0.1.8 (Nov 3)
- Rebuilt against hibr 0.99.430, whose module ABI is 17 (a module built for 16 is refused at load). No change to
  the module's behaviour. Needs hibr 0.99.430 or newer; hibr's own package declares that it breaks an older
  hibr-retro, so apt upgrades them together.

## Boxer 1.34 (Nov 1)
- **DOS goes when the game does.** The game's program was started and DOS was left at its prompt when it ended,
  so the window stayed up with nothing in it until someone typed EXIT. With Close When Game Ends on (the
  default) the program is now followed by `exit`, so quitting the game closes the window, as in Boxer.

## Boxer 1.33 (Nov 1)
- A game that ends, or whose window closes, gives the pointer lock back first (`dt_pointerlock off`) instead of
  leaving it to the desktop to notice the window has gone.
- **The pointer lock is asked for only by a click in this run.** After a full-screen change Boxer used to ask for
  the lock again for 1.5 s if the display dropped it; a Release Pointer pressed then was answered by locking again.
  That is gone: a lock the display drops stays dropped (the capture is let go, "Mouse released") until the next click.

## Boxer 1.31 (Nov 1), 1.32 (Nov 1)
- **Full Screen Border** (Control Panel > Boxer): the colour behind the picture in full screen, black to begin
  with, chosen from a window of 32 coloured blocks (click, or arrows and Enter), so a 4:3 game on a wide display has solid bars even where windows are see-through. Opacity is the
  desktop's own setting.

## Boxer 1.30 (Nov 1)
- **Full screen paints what the picture does not cover black.** A 4:3 game on a 16:9 display left the
  rest of the screen to show the wallpaper; the game window now fills its whole pane with black behind
  the picture.

## Boxer 1.29 (Nov 1)
- **Find Cover searches the web too.** The search in the window is now made from a template and is not
  typed over (`{name} box cover` to begin with; `{name}`, `{year}` and `{program}` are filled in), and
  **Search the web** (button, or W) opens the Browser at it, on the person's search engine (DuckDuckGo
  images to begin with). Both are in Control Panel > Boxer > Cover Search. A picture found there becomes
  the cover through the Browser's "Use as cover for a game...". The candidates from the thumbnails project
  are still found by the game's name. (Typing a different search in the window is gone.)
- `bx_gamelist` fills the array `BX_GAMELIST` with the games in the games folder, for an app that cannot read printed output (`bx_games` still prints them).

## Boxer 1.28 (Nov 1)
- **Find Cover found nothing, always (1.25 to 1.27): fixed.** Downloads through hibr's `fetch` failed
  inside the desktop (the variable `fetch` sets was not declared there), so every list came back empty
  and the window said "Nothing found". It now declares it, falls back to `curl` if `fetch` fails, and
  says "Could not get the list of covers: is this machine online?" when no list can be had. Words such
  as "box", "cover" and "art" in a search are ignored. The suite now runs the `fetch` path for real.

## Boxer 1.27 (Nov 1)
- `bx_games` and `bx_setcover`: what another app calls to make a picture a game's cover (for the browser's
  "Use as cover for a game…"). A PNG as it is; another kind through hibr's `img save` once it has one.

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
