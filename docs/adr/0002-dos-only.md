# 0002 — DOS only; drop ScummVM; hibr-boxer

Status: accepted (2026-10-20)

## Context

Both cores were built from source and run through `retro open`. DOSBox Pure is
2.97 MB stripped. ScummVM with every engine is 142 MB stripped, and its
`scummvm.zip` (themes, engine data) another 80 MB. The owner called that size
unacceptable. Boxer itself is DOS-only.

## Options

- **DOS only.** One 3 MB core, one `dosbox.conf` per game, half the test
  matrix, a simpler import flow. Loses ScummVM-only content (data-only
  freeware releases, Amiga/Mac/Windows versions) and save-anywhere.
- **ScummVM with `LITE=1`** (its libretro Makefile; 32 classic-adventure
  engines in `lite_engines.list`). Not measured; probably tens of MB.
- **Raw DOSBox source.** Rejected: upstream is tied to SDL, so the backend
  DOSBox Pure already has would be rewritten, and save states, zip/ISO
  mounting and the start menu would be lost.

## Decision

DOS only, on DOSBox Pure. The repository and project are **hibr-boxer**; the
`retro` module keeps its name and stays a generic libretro frontend.

## Consequences

- `cores/` builds only DOSBox Pure. The gamebox keeps an `engine` field; a
  ScummVM core, if wanted, is an extra package and a shelf entry, built with
  `LITE=1` after measuring it.
- A core file that has run before is loaded as a copy (DOSBox Pure crashes
  when loaded twice in one process); a shelf running several DOS games at once
  copies the core per game.
- "Boxer" is another application's name; the README says this is inspired by
  it, not it.
