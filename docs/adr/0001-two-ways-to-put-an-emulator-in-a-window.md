# 0001 — Two ways to put an emulator in a window

Status: proposed (2026-10-20)

## Context

The Shelf must show DOSBox and ScummVM inside the hibr desktop. hibr can
already show an X program: `mods/xscr` runs it on an Xvfb and draws the screen
as pixels or half blocks. The owner has said the X Screen app does not perform
well enough, and asked whether it could be 10-50x faster, whether a GPU could
help, and otherwise to write our own.

## Options

- **A. xscr.** No new native code; Linux only; an extra X hop; fixed-size
  software screen; no key release, no hover, no clipboard.
- **B. a libretro frontend module (`mods/retro`).** Frames at the core's
  native size, no X, macOS too, save states; needs cores, a module package per
  OS, and an exact `HIBR_ABI` match.

## Decision (proposed)

B. A GPU does not address the cost (emulation is CPU-bound and small; the
terminal link is the limit, ADR 0037 of hibr), and the hops A adds are the ones
B removes. A 10-50x gain from tuning A is not credible; from B the gain comes
from sending fewer pixels, and is a claim to measure, not to promise.

**Gate:** a frame-rate spike with synthetic native-size frames through `image`
in half blocks, sixel and kitty. If kitty and half blocks are not comfortably
above 30 fps, the plan is revisited before any frontend code is written.

## Consequences

- The deb, Homebrew and AUR packages are needed (a module with native
  dependencies cannot be fetched whole by the catalogue).
- Keys without release and no hover are properties of hibr's console, not of
  either route, and are fixed upstream in `itdlabs/hibr`.
- The Shelf keeps one `shelf_launch` function so A remains available as a
  stopgap.
