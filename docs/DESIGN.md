# hibr-boxer — design sketch

> **Superseded in part by [ADR 0002](adr/0002-dos-only.md): ScummVM is dropped and the project is DOS-only, named hibr-boxer.** The text below was written for both engines; wherever it says ScummVM, read it as history. The gamebox keeps an `engine` field so a second core can return as an additive package.

## Where it stands (2026-10-31)

This document was written as a sketch on 2026-10-20, before anything existed. What follows is how it
turned out; where it and the sketch below disagree, **this section wins**. [CHANGELOG.md](../CHANGELOG.md)
has it version by version and the [README](../README.md) is the manual.

- **Route B was built.** `mods/retro` is a libretro frontend module (`retro`, shipped as the
  `hibr-retro` deb), DOSBox Pure is the emulator, built from pinned source by `cores/build.sh`
  (`make core`) and never changed. ScummVM was dropped ([ADR 0002](adr/0002-dos-only.md)); the
  project is DOS only and is called hibr-boxer.
- **The Shelf is gone.** From Boxer 1.0 the **Boxer** window (`apps/Games/boxer.hibr`) imports
  (drop, or Import), a game is a `NAME.boxer` folder with a `boxer.json` (not `gamebox.json`), Files
  shows it with its cover and plays it on a double click (`apps/boxerplay.hibr`), and the right-click
  menu has Get Info, Find Cover and Game Is Already Installed. Sections 1, 4, 5 and 8 below describe
  the sketch.
- **The hibr prerequisites all shipped**, as tickets filed from here: the opener and bundle verbs
  (#318), covers as a bundle's icon (#336, hibr 0.99.281), hover with the pointer's pixel (#370,
  0.99.304), pointer hiding (#373, 0.99.311), **pointer lock** (#379, hibr 0.99.365 with Blit 0.2.42,
  blit#139), **true full screen** (#405, hibr 0.99.380; the stale picture on another display fixed in
  0.99.392). Still not possible in a terminal: key release (#315; keys are press and a held-for-a-moment
  tap), so a game that reads the keyboard's release does not.
- **The mouse** is relative by default with the pointer locked where the terminal can hold it (section 6).
- **Speed.** DOS games never sleep, so an emulator left to run flat out spends a core on their waiting
  loops. A Speed Limit by era (Pentium 100 by default) caps it; Boxer's own drawing costs 6 to 13% of a
  core at 70 frames a second (measured on an i3-N300). See the README.
- **Box art**: Find Cover shows the candidates and lets you choose; automatic fetching is matched against the libretro thumbnails list with rules that prefer no cover to a wrong
  one, and falls back to a title screen; fetching is a background job and is off until switched on.
- **Not done:** Homebrew and AUR packages (only the deb exists); another emulator (DOSBox-X for
  Windows 9x or PC-98 would be a second core, and an ADR); save states and rewind; a real game on
  every machine we claim (the suite runs a test game and a stand-in terminal; the owner has tried it
  by hand on Blit, one and two displays).

Status: sketch, 2026-10-20. Written against hibr 0.99.268 (module ABI 16).
Every claim about hibr below was read from its tree (`docs/display.md`,
`docs/modules.md`, `docs/catalogue.md`, ADRs 0037, 0041, 0044, 0046, 0047,
`mods/xscr`, `mods/media`) rather than remembered; where something was not
checked it says so.

## 0. What was asked, and four corrections

The ask: DOSBox and ScummVM inside hibr, drawn by hibr's own renderer, with a
Boxer-style shelf of games, packaged properly.

1. **The repo is `itdlabs/hibr-retro-gaming`**, not `itdlabs/hibr/retro/gaming`.
   Gitea has owner/repo and nothing deeper; the nested path is a 404, and the
   hyphenated one exists, empty, and is **public**.
2. **The render path is not a four-step cascade.** ADR 0037: a picture is
   drawn as *pixels* where the terminal can place them, else as *half blocks*.
   Which pixel protocol is decided by what the terminal is, not by trying one
   and falling through: kitty, ghostty, WezTerm and konsole speak the kitty
   graphics protocol; foot, mlterm, contour, yaft, iTerm2 and mintty speak
   sixel. "kitty, else sixel" would be wrong, since kitty has never drawn a
   sixel. ASCII and mono exist, but only in `media`, not in the display
   interface. So the chain is **pixels (kitty | sixel) → half blocks**, and an
   application asks one question (`dt_imgpix`: are there pixels to be had?).
   Nothing in this repo touches a protocol; it hands the display a bitmap and a
   rectangle in cells.
3. **"The modules need a package" is true only for one of two designs.** See
   section 2. The reason is not that a catalogue cannot carry a module (it can,
   per architecture, signed: ADR 0044) but that a module with native
   dependencies cannot be fetched with them.
4. **The hardest problem is the keyboard, not the picture.** See section 6.

## 1. Pieces

```
hibr-retro-gaming/
  apps/Games/boxer.hibr          the Boxer window (import, Get Info, Find Cover) -> hibr-apps
  apps/boxerplay.hibr            the game window, a # part: of boxer              -> hibr-apps
  control-panel/boxerset.hibr    the Control Panel pane, a # part: of boxer       -> hibr-apps
  mods/retro/                    the libretro frontend as a hibr module (the deb)
  cores/                         PINS and build.sh: DOSBox Pure from pinned source
  packaging/deb/                 the hibr-retro package
  tests/                         pty suites on hibr's harness, a test core
  docs/  README.md  CHANGELOG.md
```
(The sketch's layout, with a Shelf and a `lib/`, is superseded: see "Where it stands".)

Two kinds of thing, two homes, as ADR 0041/0044 draw the line:

- **Scripts** (the app, its pane): plain `.hibr` files, readable before they
  run, published to `hibr-apps` with `addapp` and installed by
  `catalogue install shelf`.
- **Native code** (a module) and **the emulators**: operating-system packages.
  Neither can be fetched by the catalogue with its own dependencies.

## 2. The decision: how does an emulator get into a window?

Two ways exist. This is the only genuinely open architecture question, and it
is recorded as [ADR 0001](adr/0001-two-ways-to-put-an-emulator-in-a-window.md).

### Route A — run the real emulator under Xvfb, through `xscr`

hibr already has this. `mods/xscr` starts an `Xvfb`, speaks X11 over its socket
(DAMAGE for "something changed", XTEST for input), maps the screen file Xvfb
keeps, and draws it into a window as pixels or half blocks. `apps/xscreen.hibr`
runs Firefox, GTK and Qt programs this way today. DOSBox and ScummVM are SDL
programs with an X11 backend, so they work unchanged.

| | |
|---|---|
| new native code | **none** |
| packages needed | `xvfb`, `dosbox`, `scummvm` from the OS; no hibr package at all |
| ships as | one app in `hibr-apps` (and a pane) |
| works on | Linux. `xscr` execs `Xvfb` and the tree has no darwin path for it (grep for `darwin` in `mods/xscr/xscr.c` finds nothing). Whether Xvfb is obtainable on macOS was not checked |
| sound | the emulator talks to PipeWire/Pulse/ALSA itself; hibr is not in the path |
| costs | one extra hop (SDL → X → mapped file → pixels), fixed screen size per window, software rendering only (Xvfb has no GPU, so `output=surface` for DOSBox, a software `gfx_mode` for ScummVM) |
| known gaps (xscr's own list) | no hover with no button held; no clipboard; US key map only |
| runs in a `hold`ed session | yes, as xscreen does |

### Route B — a libretro frontend module, `mods/retro`

libretro cores are the emulators built as shared objects with a small C
interface. A module `dlopen`s a core and implements the frontend side:
`retro_run` at the core's frame rate; video callback → framebuffer →
`DP_IMG` exactly as `media/draw.c` does; audio callback → the sound-server
output pattern of `media/ao.c`; input callback ← the console's key names. It
is a close match for what Boxer does (it embeds DOSBox in-process) and for
hibr's own habits: `dlopen` at first use, nothing linked, no header needed to
build, no fork, no X.

| | |
|---|---|
| new native code | a frontend: roughly the shape and size of `mods/media` (not estimated) |
| packages needed | a `hibr-retro` package per OS **and** the cores |
| works on | Linux and macOS |
| costs | cores must be obtained: no libretro DOSBox or ScummVM core turned up in Debian 12's archive (`apt-cache search libretro` found none), so we build them, or fetch libretro's own builds, which is a supply-chain decision |
| audio | `ao.c` is internal to `media` (nothing `hibr_provide`s it), so either `retro` carries its own copy or the output is lifted into an interface in hibr proper |
| extras | save states, rewind and a real pause come with the libretro API; ScummVM's and DOSBox's own configuration is reached through core options, not their config files |
| ABI | an out-of-tree `.so` is pinned to `HIBR_ABI` exactly. `hw-manager` is the precedent for a sibling repo that does this: it records `HIBR_ABI` and `HIBR_VERSION` in `packaging/` and copies the ABI file into its package |

### What running a core in the shell's process means

Written down after building the driver (`mods/retro/rl.c`):

- A core that crashes (a SIGSEGV in DOSBox) takes the whole desktop with it,
  every window, exactly as hibr's modules.md says of SIGPIPE.
- A core is a process-wide singleton: its globals are shared by any second
  copy of the same file, so `retro open` refuses a second open of one file
  (a *copy* of the file is a separate core: verified, each has its own
  globals). The driver keeps its own state per thread (POSIX keys, which tcc
  has), so two different cores run side by side.
- Escape hatch if either bites: run `rl` in a child process and send frames
  and PCM over a pipe, the shape `media feed` already has. `rl` was written
  with no shell or display dependency so that move is mechanical.

### Recommendation

**Route B: our own frontend.** Revised 2026-10-20 after the owner said the
X Screen app "does not perform well enough" and asked whether it could be made
10-50x faster, or use a GPU, or else be written fresh.

Why route A cannot plausibly get there (reasoned from ADR 0037 and `xscr`'s
design; **not measured**, see the gate below):

- **A GPU does not touch the bottleneck.** The emulators are CPU-bound and
  draw 320x200 to 640x480 pictures. Xvfb is a software server with no GPU by
  design. A GPU-backed X server (Xorg with a real driver, or Xwayland under a
  compositor) is a much heavier stack, and it would still end in the same
  place: a bitmap read back to the CPU and pushed through a terminal.
- **The cost is mostly after the emulator.** ADR 0037's film numbers, per
  frame: sixel 23 ms at 100x34 cells, kitty 351 kB of base64 pixels. The
  terminal link is the limit, whoever produced the frame.
- **Route A adds hops route B does not have**: SDL → X11 → DAMAGE event →
  mapped screen file → scale to the window → encode. And the screen is a fixed
  Xvfb size scaled to the window, not the game's own native size.

What route B changes, which is where a large gain can honestly come from:

- Frames arrive **at the core's native size** (e.g. 320x200, 192 kB raw).
  The console already sends a kitty picture no larger than its source and lets
  the terminal scale it (`mods/console/image.c`), so this lever exists today
  and is not something we add; sixel has no such option, since it paints 1:1.
- On a **local** kitty-protocol terminal, transmit by shared memory or file
  (`t=s`/`t=t`) instead of base64 over the pty. ADR 0037 names this and
  notes it cannot work over ssh, so it must be a detected fast path, not
  the only path.
- Dirty-region or palette-aware encoding: DOS games are 256-colour, so an
  indexed bitmap is a third of the bytes; sixel can reuse the palette
  across frames.
- No X server, no extra process, no polling; the emulator thread produces
  frames and the display thread takes the latest.
- Honest ceiling: the terminal still has to receive and paint the frame, so
  "10-50x" will not be a number we can promise; the target should be stated
  in frames per second at a given cell size, per protocol, and measured.

**Spike 1 result (2026-10-20, [docs/spike-1-frame-rate.md](spike-1-frame-rate.md)):
the gate passes for kitty and half blocks** (producer cost 3-4 ms and ~0.5-2 ms
per frame, far inside a 33 ms budget). Kitty is bytes-bound (251 kB a frame,
15 MB/s at 60 fps), sixel is the weak path (~31 fps at 120x40 on the producer
alone), and nothing was measured on a real terminal or on `xscr`.

**The gate that was set before committing to the full module:** a one-day spike. Time how many
native-size 320x200 frames per second the existing `image` path can place for
half blocks, sixel and kitty (pty and a real terminal), with a synthetic frame
source and no emulator. If that number is not comfortably above 30 fps for
kitty and half blocks, no frontend will fix it and the plan changes. This is
cheap and is the number that should have been taken first. Optionally also time
`xscr` with a trivial X client as the baseline to quantify the gap.

The Shelf (gamebox format, import, covers, launch) is independent of the
engine route, and the app is written so the engine is one function
(`shelf_launch`). Route A remains a stopgap on Linux for trying the Shelf
before the module exists, not the destination.

## 3. The gamebox

Boxer's idea, kept: a game is **one folder you can copy, share and delete as
a unit**, and the desktop treats it as one object. Extension `.gamebox`
(Boxer's `.boxer` is its own). Layout:

```
Prince of Persia.gamebox/
  boxer.json         identity and launch recipe (see below)
  cover.png            the box art; a generated tile when absent
  engine/
    dosbox.conf        per-game overrides, layered over the shelf's base conf
    scummvm.ini        ScummVM: the gamebox's own config, never ~/.config/scummvm
  drives/
    c/                 the DOS C: drive, a plain folder
    d/                 a CD: an .iso/.cue image or a folder
    a/                 floppy images
  saves/               the game's own saves; ScummVM savepath points here
  extras/              manual, maps, screenshots
  MANIFEST.sha256      optional; makes a gamebox verifiable when it is shared
```

`boxer.json`, JSON because the desktop's data convention is JSON (ADR 0028):

```json
{
  "gamebox": 1,
  "title": "Prince of Persia",
  "engine": "dosbox",
  "launch": { "program": "C:\\PRINCE\\PRINCE.EXE", "args": "megahit" },
  "programs": ["C:\\PRINCE\\PRINCE.EXE", "C:\\PRINCE\\SETUP.EXE"],
  "mounts": [ { "drive": "d", "kind": "cdrom", "path": "drives/d/game.cue" } ],
  "display": { "aspect": "4:3", "scale": "integer" },
  "input":   { "release": "auto", "mouse": "grab" },
  "source":  { "imported": "2026-10-20", "from": "installer" }
}
```

ScummVM: `"engine": "scummvm"`, `"launch": {"target": "monkey"}`, `drives/` is
replaced by `game/`, and `engine/scummvm.ini` holds the target. It is passed
`--config=` and `--savepath=` so nothing leaks into the user's own ScummVM.

Where gameboxes live: **shelves**, which are folders. The default is
`$XDG_DATA_HOME/hibr/shelf/`; more are added in the pane. A shelf is scanned,
and the result cached in an index beside it; nothing registers a gamebox, which
is how hibr treats every other installable (ADR 0041: *placing a file where the
desktop already looks*).

### What "like Boxer, but better" means, concretely

| Boxer | here |
|---|---|
| DOSBox only | DOSBox **and** ScummVM, one gamebox format |
| a Mac app | runs where hibr runs, **including over ssh and inside a held session** |
| import is a wizard | import is a wizard *and* `shelf import PATH` from a script |
| one DOSBox, bundled | the OS's DOSBox/ScummVM; an engine can be chosen per gamebox |
| opaque package | a folder; `tar`, `rsync` and `catalogue show`-style reading all work, and an optional manifest makes it verifiable |
| — | GOG offline installers unpacked with `innoextract` when it is present (optional) |

Nothing is claimed here about what Boxer does beyond its public shape: a
shelf of covers, game packages, an import flow that installs into a package,
a program picker. Details of Boxer's behaviour should be confirmed against the
app itself before we promise to match them.

## 4. The Shelf (the application)

> **Superseded.** The Shelf was dropped for the Boxer window and Files (see "Where it stands"). Kept as the
> design it was.

A hibr desktop app: a script with `app shelf "…" 1.0`, `# modules:` and
`# part:` lines (see `apps/xscreen.hibr` for the shape).

```
┌ Shelf ─────────────────────────────────────────────── ─ □ × ┐
│ [Import]  [Settings]            / search            ▢ ▣ size │
│ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐                      │
│ │ cover │ │ cover │ │ cover │ │ cover │   Prince of Persia   │
│ │       │ │       │ │       │ │       │   DOSBox · 1989      │
│ └───────┘ └───────┘ └───────┘ └───────┘   last played 3d ago │
│ Prince…   Monkey I… Lemmings  Doom        [Play] [Info]      │
└──────────────────────────────────────────────────────────────┘
```

- **Covers** are drawn through the display's `image` interface: pixels where
  the terminal has them, half blocks where it does not, and a generated text
  tile (title on a colour derived from its name) where there is no cover. The
  app never asks which protocol.
- **Keys and mouse**: arrows move, enter or double-click plays, `/`
  searches, `i` info, `e` settings, `n` import. *How a double-click is
  recognised, and whether a **folder** can be an opener target for Files'
  Open With, has not been checked.* `dt_opener` registers by file extension
  (`handlers.hibr`), and a gamebox is a directory, so this is the first thing
  to verify.
- **Playing** opens the game in a window of its own, one per running game.
  The shelf stays. A second game can be started if it is a *different core*
  (DOSBox and ScummVM together); two games on the **same** core file share
  that core's globals and cannot: `retro open` refuses it. A *copy* of the core
  file is a separate core (verified), so the Shelf can copy a core per running
  game if it must, or the core can run in a child process (see below).
- **Per-game panel** (Boxer's inspector): launch program, drives, display
  aspect and scaling, input behaviour, emulator speed, "open folder in Files",
  "eject disc".
- **Pane** (`shelfset.hibr`): shelf folders, default engine, base confs,
  where saves go, input policy.
- **Not shared with other apps.** ADR 0046: an installable reaches only what
  every scope has, and asks before using another app. So the Shelf drives
  `xscr` itself rather than opening the X Screen app, and `need retro` /
  `need xscr` must fail with a plain message, never assume.

## 5. Import

Drop (or pick) a folder, a `.zip`, an `.iso`/`.cue`, a floppy image, or an
installer. The pipeline:

1. **Unpack** with the `archive` module (zip/tar are in hibr already).
2. **Detect.** ScummVM: `scummvm --detect --path=…` names the target. DOS:
   walk for `.exe` `.com` `.bat`, and rank names like `install`, `setup`,
   `config` as installers and tools, everything else as launchers.
3. **Build the gamebox**: create the folder, copy into `drives/c/`, write
   `boxer.json` and a stub conf.
4. **If an installer was found**, run it once inside the gamebox's own C:
   drive (so the installed game lands in the box), then rescan for programs
   and let the person pick the launcher.
5. **Cover**: a supplied image, or the generated tile. Fetching box art from
   a database is a later, optional feature: it needs a key and has terms.

The app ships and fetches no games. A shelf is only ever what the person puts
on it.

## 6. The constraint that decides playability: input

Everything above makes a game *appear*. Making it *playable* depends on two
things neither route can fix from this repo.

**Keys have no release.** `console key` returns a decoded key name on press.
Only the mouse has press and release, and no kitty keyboard protocol was found
in `mods/console` (a grep for it found nothing). A DOS game that reads "left
is down" will hold the character walking forever, or never see a held key at
all. `xscr key` is a press-and-release pair; there is no key-down.

Options, in order of preference:
1. **Enable the kitty keyboard protocol** (progressive enhancement, flag for
   event types) where the terminal speaks it, giving real press, repeat and
   release. That is a change to hibr's console, and it is the right fix.
2. **Synthesize release** where it is not available: treat a key as held until
   no repeat has arrived for a short gap. The first repeat arrives after the
   terminal's *initial* delay (commonly several hundred ms), so a short gap
   makes held keys stutter and a long gap makes taps stick. Needs a per-game
   `input.release` setting and honest documentation.
3. A per-game **sticky mode** for games that only need a toggle.

**Hover.** `xscr` documents that the pointer moves only with a button held,
because the desktop does not ask the terminal for every movement.
`console mouse motion` exists but is **not** a cheap switch: hibr's CLAUDE.md
records that mode 1003 was tried for the Control Strip's hover and reverted,
because the flood of reports broke shift-drag copy and made selection lag behind
stale hover reports. The plan is therefore: only the focused game window asks,
only while focused, with reports coalesced against `console waiting`.
ScummVM's point-and-click wants this; DOS games with a mouse want it too.

Both are changes in `itdlabs/hibr`: **#315** (key release) and **#316** (hover).
Hover shipped as hibr 0.99.304 (#370): the desktop hears the pointer with no
button down where the display reports it in pixels (Control Panel > Mouse >
Hover, Auto), and tells a window's `_hover` the cell, with the pixel in
`DT_PX`/`DT_PY`.

**The mouse degrades in steps**, each the one above less something, none needing
a setting:

1. Pixels and hover (Blit, kitty, foot): DOS's pointer follows every move, to
   the part of a cell it is over (`retro mouse` takes `12.25`).
2. Hover, cells only (Hover set On): the same, a cell at a time.
3. No hover: DOS's pointer follows a press and a drag, as before.
4. An older `retro` module takes the whole cell of a fractional position, and an
   older hibr never calls `_hover`: steps 2 and 3.

Hiding the pointer over the game is asked of the desktop (`dt_pointer`, hibr 0.99.311, #373) and is a no-op where it cannot be done.
Capture Mouse says which step the session is on.

**Pointer lock** (hibr #379 with Blit's, blit#139; Blit 0.2.42, hibr 0.99.365) is the step above step 1 for a game whose mouse is relative. When such a game is captured on a click and the desktop says a display can hold the pointer (`dt_ptrlockcan`), Boxer asks for it (`dt_pointerlock "$id" on`): the pointer stays still and the window is told how far it moved in raw counts (`_mouse` with `rel`, DY then DX), which `retro motion` hands to the core as the mouse's own, so Doom and the like turn without end. The desktop gives it back on its Release Pointer key, a menu, focus moving or the display letting go, and tells the window (`_mouse ... unlock`); that is taken as the truth. A lock refused outright, an unlock within 400 ms with no report, leaves the plain capture and is not asked for again in that window. Where no display can hold the pointer (kitty, foot) the game is let go at the window's edge, as it was.

**Frame cost.** ADR 0037 measured film frames: half blocks 0.5 ms / 14 kB at
100x34 cells, sixel 23 ms / 34 kB, kitty 6.8 ms / 351 kB at half resolution.
A 320x200 DOS game at an integer scale is a small bitmap; expect it to be fine
in half blocks and kitty, and watch sixel at large sizes. Measure early.

## 7. Packaging and distribution

> **Superseded in part.** Route B was chosen, so the `hibr-retro` deb exists (built by
> `packaging/deb/build-deb.sh`, published to the hibr apt repo, with the pinned DOSBox Pure source kept
> beside it for the GPL); the apps go to hibr-apps with `addapp`. Homebrew and the AUR do not exist yet.
> The text below is the sketch.

**Phase 1 (route A) needs no package of ours.**

| artefact | how it reaches a user |
|---|---|
| `shelf` app + `shelfset` pane | `catalogue install shelf` from `hibr-apps` (published with `addapp`; the pane is the app's `# part:`) |
| `xvfb`, `dosbox`, `scummvm` | the OS. The app checks `command -v` at launch and prints the install line for this OS, rather than failing opaquely |

Debian 12's archive has `dosbox` 0.74-3 and `scummvm` 2.7.0; `dosbox-staging`
has no candidate there, so a newer DOSBox is the person's own decision, and
the engine command is a setting.

**Phase 2 (route B) adds a module, and then the user's instinct applies.**
The catalogue *can* carry a third-party module (`mods/` kind, per
architecture, signed index required, refused otherwise). It still must not be
the only route, because the module's own dependencies (the cores, the sound
libraries) are not something a catalogue entry can pull in. So:

| platform | package | notes |
|---|---|---|
| Debian/Ubuntu | `hibr-retro` `.deb`, added to the existing `hibr-apt` pool | `Depends` on a hibr of the **same ABI**; rebuilt on every `HIBR_ABI` bump. Does hibr's deb expose its ABI as a `Provides`? Not checked; if not, ask upstream, or pin `hibr (= X)` |
| macOS | formula `hibr-retro` in the `osakka/hibr` tap | builds from source like `hibr` itself (no bottle) |
| Arch | AUR `hibr-retro` `PKGBUILD` | `make`, like hibr's own |

Out-of-tree builds need `hibr.h`; `make install` already places it at
`$(PREFIX)/include/hibr/hibr.h`.

**Ordering matters.** `catalogue install` refuses an entry whose `# modules:`
line names a module that neither hibr nor the catalogue provides ("Nothing was
installed"). So the OS package must be installed before the app, and the app's
`modules:` line only names `retro` once route B is real. Route A's app names
`xscr`, which hibr ships.

## 8. Phases

> **Done through phase 5 for the deb and hibr-apps** (not Homebrew or the AUR); phase 6 is partly done
> (per-game Get Info). The list is the sketch's.

| | |
|---|---|
| **0** | this repo: README, design, ADR, licence (done) |
| **1** | the **frame-rate spike** (section 2 gate): done, passed for kitty and half blocks, see [spike-1](spike-1-frame-rate.md) |
| **2** | `mods/retro`: libretro frontend (video, audio, input), loading a core, with a test core: **done** (driver, module, 39 + 14 checks, tcc-built, ASan/UBSan/TSan clean); next, the real cores built from source |
| **3** | the Shelf: gamebox format and library, shelf window with covers, import, launch through `retro`; a stub-core test suite |
| **4** | prerequisites in `itdlabs/hibr`: key release, motion on focus (can start in parallel with 2) |
| **5** | packages for deb, Homebrew and the AUR; publish `shelf` to `hibr-apps` |
| **6** | polish: per-game inspector, save states and rewind, shelf sharing/verification |

Tests ride on hibr's own pty harness (`tests/*.py`, as in the hibr tree), with
a shell-script **stub emulator** standing in for DOSBox and ScummVM, so import,
detection and launch are tested without either installed.

## 9. Open questions

> **Answered**: route B; cores built by us from pinned source; Linux first; the module is `retro`, the
> application is Boxer and the folder `.boxer`; stock-compatible DOSBox Pure; the prerequisites in `itdlabs/hibr`
> were done there; box art is the person's own or an opt-in lookup (off by default); the repo stays public.

1. **Route.** B, decided 2026-10-20. Cores: **built by us from source** (decided 2026-10-20), not fetched
   from libretro's builds, so we control what runs and can build per OS. Both
   are GPL; they are separate objects loaded at run time, never linked into
   hibr. Which core repos and revisions: to be chosen and pinned in `cores/`.
2. **Platforms.** Linux and macOS both from the start? (Route B allows it.)
3. **Names.** Application "Shelf", extension `.gamebox`, module `retro`? (The
   Games submenu in `hibr-apps` already holds snake, mines and bricks; Shelf
   would sit there.)
4. **DOSBox flavour.** Stock `dosbox` 0.74, or `dosbox-staging`/`dosbox-x`
   where available, and is the engine command a per-gamebox setting?
5. **Upstream changes.** May I plan key-release and focus-motion work in
   `itdlabs/hibr`? They are the difference between "launches" and "plays".
6. **Box art.** Supplied by the person only, or an optional lookup?
7. **Repo visibility.** The repo is public. Fine, since no games ever go in it?
