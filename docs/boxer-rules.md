# How Boxer decides, and how hibr-boxer does the same

hibr-boxer follows Boxer (the Mac application, https://github.com/alunbestor/Boxer, commit
0062fc18e154cde6cef3bf3329be4b0658597e31) in how a game's files are read. The rules below are
Boxer's, read from its source (`BXInstallerScan.m`, `BXImportSession+BXImportPolicies.m`,
`BXFileTypes.m`, `BXGamebox.m`, `BXImportSession.m`, `BXExecutableConstants.h`) and kept the
same on purpose; the code is `bd_*` in `apps/boxerplay.hibr`. Boxer is GPL-2.0 and the lists
and thresholds here are taken from it: this project is MIT, so that provenance is worth a look
before the lists are shipped anywhere that cares.

| Boxer | here |
|---|---|
| a DOS program is a `.com`, a `.bat`, or an `.exe` whose header (`MZ`, relocation table at 0x40, a new header at 0x3C) is not NE/PE/W3/W4 (Windows) or LE/LX (OS/2), a large (> 3584 byte) stub counting as DOS | `bd_isdos` |
| ignored altogether: `directx`, `acrodos`, `acroread.exe`, `uvconfig.exe`, `univbe`, `unins000.`, `graphic mode setup.exe`, `gogwrap.exe`, a `dosbox*` folder, `autorun`, **`bootdisk.`**, `readme.`, `foo.bat`, `vinstall.bat`, `pkunzip.`, `pkunzjr.`, `arj.`, `lha.` (case-insensitive, on the path) | `BD_IGN`, `bd_ignored` |
| not listed as a program to run: `dos4gw.exe`, `pkunzip.exe`, `lha.com`, `arj.exe`, `deice.exe`, `pkunzjr.exe` | `BD_EXCL`, `bd_programs` |
| an installer is a DOS program with `inst`, `setup` or `config` in its name; the preferred one is the first by path depth that matches `^dosinst`, then `^install.`, then `^hdinstal.`, then `^setup.`, else the first | `bd_scan` (`BD_INST`) |
| already installed when a path has the extension `conf`, `iso`, `cue`, `cdr`, `inst`, `harddisk`, `cdrom` or `floppy`, or is `gfw_high.ico` | `BD_TELLS`, `BD_TELLY` |
| Windows programs and no DOS program that is not a batch file: a Windows game, refused; nothing DOS at all and nothing saying installed: refused | `bx_import` |
| not installed and has an installer: run the installer, the source mounted as D:; afterwards, if it put files on C: the source is kept as the game's disc, else the source's files are the game and are copied to C: | `bx_import` (installing), `bd_finish` |
| installed (or no installer): copy the files into C:, in a folder named for the game (`validDOSNameFromName`: lower case, letters digits and dots, 8.3) when the files have programs at the top and nothing marking them installed, else into the root | `bx_copyin`, `bd_wantsfolder`, `bd_dosname` |
| no default program is guessed: the program list is shown, the one run is remembered; a game with one program runs it | the shelf's chooser (`bx_play`), `bd_describe` |

Where it differs, because a terminal is not a Mac window: the installer's disc is a plain D:
folder, not an emulated CD-ROM (DOSBox Pure refuses a folder as a CD-ROM); the "this game is
already installed" button is *Game Is Already Installed* in the game's right-click menu; and
the program list is a drop-down under the game's tile, not a panel in the game window.

## Games that need their disc

A game that checks for its CD (Dungeon Keeper) needs the disc image as D: *as a CD-ROM*, in
the box, every time it is played. A disc image given to Boxer is copied into `drives/d/` and
mounted `imgmount d ... -t iso`, so DOS sees a CD-ROM; a cue sheet goes the same way. If
xorriso, 7z or bsdtar is here, the image is read to find an installer (run first, from D:) or,
for a game that runs from its disc, the programs on it (D: paths). A folder given as a game's
installation disc is made into an image too (xorriso), for the same reason. When the installer
has put files on C: the image stays; when it did not, or Game Is Already Installed is chosen,
the image's files are taken off it into C:.
