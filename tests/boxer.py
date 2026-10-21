#!/usr/bin/env python3
"""The Boxer apps in a real desktop session on a pty, with the test core standing in for DOSBox Pure:
what the gamebox turns into, and that the game's picture reaches the terminal as pixels and half blocks."""
import os, shutil, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIBR_TREE = os.environ.get("HIBR_TREE", os.path.join(ROOT, "..", "hibr"))
sys.path.insert(0, os.path.join(HIBR_TREE, "tests"))
import screen as sx
from screen import Term, check, report, load

D = tempfile.mkdtemp(prefix="hibr-boxer-")
CORE = ROOT + "/build/testcore.so"
RETRO = ROOT + "/build/retro.so"
DESK = HIBR_TREE + "/programs/desktop/desktop.hibr"
ENVBASE = {"XDG_RUNTIME_DIR": D, "HIBR_RETRO_AUDIO": "none", "BP_CORE": CORE,
           "BP_SYS": D + "/sys", "HIBR_MODPATH": ROOT + "/build"}


def gamebox(name="Test Game"):
    """A gamebox folder: a program, a CD image, the person's own settings and a drive C."""
    b = os.path.join(D, name + ".boxer")
    shutil.rmtree(b, True)
    os.makedirs(b + "/engine")
    os.makedirs(b + "/drives/c/GAME")
    open(b + "/drives/c/GAME/RUN.EXE", "w").write("x")
    open(b + "/engine/dosbox.conf", "w").write("[cpu]\ncycles=max\n[autoexec]\necho mine\n[sdl]\nfullscreen=false\n")
    open(b + "/gamebox.json", "w").write(
        '{"gamebox":1,"title":"%s","engine":"dosbox",'
        '"launch":{"program":"C:\\\\GAME\\\\RUN.EXE","args":"-fast"},'
        '"mounts":[{"drive":"d","kind":"cdrom","path":"drives/d/game.cue"}],'
        '"display":{"aspect":"4:3"}}' % name)
    return b


def desk(body, box, pix=False, env=None):
    p = sx.scratch("boxer.hibr")
    open(p, "w").write(
        "%s. %s\n. %s/apps/boxerplay.hibr\n"
        "dt_open\nBID := dt_launch boxerplay \"%s\"\n%s\ndt_run\ndt_close\n"
        % (load("console", RETRO), DESK, ROOT, box, body))
    kw = dict(cellw=8, cellh=16, caps=["kitty"]) if pix else {}
    return Term(p, rows=26, cols=82, settle=1.0, env=dict(ENVBASE, **(env or {})), **kw)


box = gamebox()

# The run.conf: the person's own settings first, then an autoexec that mounts C:, the CD, enters the
# program's folder and starts it with its arguments.
hb = sx.HIBR
import subprocess
r = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/boxerplay.hibr\njson parse BPJ \"$(< '%s/gamebox.json')\"\n"
                    "mkdir -p %s/o; f := bp_conf '%s' %s/o; cat \"$f\""
                    % (load("console"), DESK, ROOT, box, D, box, D)],
                   capture_output=True, text=True, env=dict(os.environ, **ENVBASE), timeout=60)
out = r.stdout
check("the person's own settings come first", "[cpu]\ncycles=max" in out, out[:300])
check("C: is the gamebox's drives/c", 'mount c "%s/drives/c"' % box in out, out)
check("a CD image is mounted on its drive", 'imgmount d "%s/drives/d/game.cue" -t iso' % box in out, out)
check("the program's folder is entered and the program run", "cd \\GAME\nRUN.EXE -fast" in out.replace("\r", ""), out)
check("a [autoexec] of the person's own is dropped, and what follows it kept",
      "echo mine" not in out and "fullscreen=false" in out and out.count("[autoexec]") == 1, out)
check("the autoexec comes last, so the settings cannot override it", "[autoexec]" in out and out.index("[cpu]") < out.index("[autoexec]"), out)

for pix in (True, False):
    t = desk("", box, pix)
    for _ in range(40):
        t.collect(0.25)
        sc = t.screen()
        if (pix and b"a=T" in t.raw) or (not pix and "▀" in sc.text()):
            break
    t.collect(1.0)
    sc = t.screen()
    placed = t.raw.count(b"a=T")
    if pix:
        check("the game is drawn as pixels on a terminal that takes them", placed >= 1, placed)
    else:
        check("and as half blocks on one that takes none", sum("▀" in sc.row(r) for r in range(2, 24)) > 10, sc)
    check("the window wears the gamebox's title", "Test Game" in sc.text(), sc)
    t.close()


def png(path, w, h, rgb):
    """A plain-colour PNG, written by hand."""
    import struct, zlib

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    raw = b"".join(b"\0" + bytes(rgb) * w for _ in range(h))
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


# The shelf: three boxes, one with a cover; the grid shows their titles, the arrow keys move the selection and
# Enter opens the selected game in a window of its own.
shelf = os.path.join(D, "shelf")
shutil.rmtree(shelf, True)
os.makedirs(shelf)
for nm in ("Alpha Quest", "Beta Racer", "Gamma Blast"):
    b = gamebox(nm)
    shutil.move(b, os.path.join(shelf, nm + ".boxer"))
png(os.path.join(shelf, "Beta Racer.boxer", "cover.png"), 60, 80, (200, 40, 40))


def shelfdesk(pix):
    p = sx.scratch("boxer.hibr")
    open(p, "w").write(
        "%s. %s\n. %s/apps/boxerplay.hibr\n. %s/apps/Games/boxer.hibr\n"
        "dt_open\nBID := dt_launch boxer \"%s\"\ndt_run\ndt_close\n"
        % (load("console", "img", RETRO), DESK, ROOT, ROOT, shelf))
    kw = dict(cellw=8, cellh=16, caps=["kitty"]) if pix else {}
    return Term(p, rows=40, cols=100, settle=1.0, env=ENVBASE, **kw)


t = shelfdesk(True)
t.collect(2.0)
sc = t.screen()
check("the shelf lists every box by its title",
      all(n in sc.text() for n in ("Alpha Quest", "Beta Racer", "Gamma Blast")), sc)
t.send(b"r")
t.collect(1.0)
check("a cover.png is drawn as a picture", t.raw.count(b"a=T") >= 1, t.raw.count(b"a=T"))
t.send(b"\x1b[C")
t.collect(0.8)
sc2 = t.screen()
check("the arrow key moves the selection", sc2.style(sc.find("Beta Racer")[0], sc.find("Beta Racer")[1]) !=
      sc.style(sc.find("Beta Racer")[0], sc.find("Beta Racer")[1]), (sc.find("Beta Racer"),))
t.send(b"\r")
for _ in range(20):
    t.collect(0.3)
    if "Boxer Game" in t.screen().text():
        break
check("Enter opens the selected game in a window of its own", "Boxer Game" in t.screen().text(), t.screen())
check("and it is the selected one, not whichever is first: the window is titled Beta Racer and is not an error",
      "Beta Racer" in t.screen().text() and "Not a gamebox" not in t.screen().text(), t.screen())
t.close()


# Double click: a press on a tile selects it; two presses on the same tile plays it, and two on different
# tiles in a row does not.
t = shelfdesk(False)
t.collect(1.5)
sc = t.screen()
ra, ca = sc.find("Alpha Quest")
rb, cb = sc.find("Beta Racer")
t.send(sx.press(ra, ca + 2) + sx.release(ra, ca + 2) + sx.press(rb - 3, cb + 2) + sx.release(rb - 3, cb + 2))
t.collect(1.0)
check("a press on one tile then another does not play either", "Boxer Game" not in t.screen().text(),
      t.screen())
one = sx.press(rb - 3, cb + 2) + sx.release(rb - 3, cb + 2)
t.send(one)
t.collect(0.15)
t.send(one)
for _ in range(20):
    t.collect(0.3)
    if "Boxer Game" in t.screen().text():
        break
check("a second press on the same tile plays that game in a window of its own",
      "Boxer Game" in t.screen().text(), t.screen())
t.close()

# The Info drawer: `i` opens it with the selected game's settings; Tab goes into it, Down and Right change a
# field, and the choice is written into the box's own gamebox.json.
t = shelfdesk(False)
t.collect(1.5)
t.send(b"i")
t.collect(0.8)
sc = t.screen()
check("i opens the Info drawer for the selected game", "Rendering" in sc.text() and "Settings for this game" in sc.text(), sc)
t.send(b"\t")
t.send(b"\x1b[B")
t.send(b"\x1b[C")
t.collect(0.8)
doc = open(os.path.join(shelf, "Alpha Quest.boxer", "gamebox.json")).read()
check("a field changed with the keys is written into that box", '"render": "follow"' in doc, doc)
t.send(b"\x1b[B\x1b[B\x1b[C")
t.collect(0.6)
doc = open(os.path.join(shelf, "Alpha Quest.boxer", "gamebox.json")).read()
check("and the next one down too (Speed)", '"cycles": "auto"' in doc, doc)
t.close()


# A right click on a game opens its own menu; Get Info opens the settings in a window of their own, the same fields.
t = shelfdesk(False)
t.collect(1.5)
sc = t.screen()
rb, cb = sc.find("Beta Racer")
t.send(sx.press(rb - 3, cb + 2, 2) + sx.release(rb - 3, cb + 2, 2))
t.collect(1.0)
check("a right click on a game opens its menu with Play, Get Info and Show in Files",
      all(w in t.screen().text() for w in ("Play", "Get Info", "Show in Files")), t.screen())
t.send(b"\x1b[B")
t.send(b"\r")
t.collect(1.2)
sc = t.screen()
check("Get Info opens the game's settings: program, speed, graphics, sound card, IRQ, DMA, port, MIDI, mouse",
      all(w in sc.text() for w in ("Beta Racer Settings", "Program", "Speed", "Graphics", "Sound Card", "Sound IRQ",
                                   "Sound DMA", "Sound Port", "MIDI", "Mouse")), sc)
t.send(b"\x1b[B" * 6 + b"\x1b[C")
t.collect(0.8)
doc = open(os.path.join(shelf, "Beta Racer.boxer", "gamebox.json")).read()
check("a field changed in that window (Sound IRQ) is written into the box", '"irq": "3"' in doc, doc)
t.close()

# MIDI: the synths in the folder are listed as DOSBox Pure knows them, and linked into its system folder.
md = os.path.join(D, "midi")
os.makedirs(md)
for f in ("MT32_CONTROL.ROM", "MT32_PCM.ROM", "ROM1.BIN", "gm.sf2", "notes.txt", "WAVEROM1.BIN"):
    open(os.path.join(md, f), "w").write("x")
sysd = os.path.join(D, "sysmidi")
os.makedirs(sysd)
q = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/boxerplay.hibr\nBX_MIDIDIR=%s\nBP_SYS=%s\n"
                    "echo \"list=$(bp_midilist | tr '\\n' ' ')\"; bp_midilink; ls %s | tr '\\n' ' '"
                    % (load("console"), DESK, ROOT, md, sysd, sysd)],
                   capture_output=True, text=True, env=dict(os.environ, **ENVBASE), timeout=60)
check("the folder's synths are listed (an MT-32 control ROM, an SC-55 ROM1.BIN, a SoundFont; not the rest)",
      "list=MT32_CONTROL.ROM gm.sf2 ROM1.BIN" in q.stdout.replace("  ", " ") or
      all(w in q.stdout.split("list=")[1].split("\n")[0] for w in ("MT32_CONTROL.ROM", "gm.sf2", "ROM1.BIN"))
      and "notes.txt" not in q.stdout.split("list=")[1].split("\n")[0] and "WAVEROM1" not in q.stdout.split("list=")[1].split("\n")[0],
      q.stdout + q.stderr)
check("and every ROM and SoundFont is linked into the core's system folder, the PCM ROM too",
      all(os.path.islink(os.path.join(sysd, f)) for f in ("MT32_CONTROL.ROM", "MT32_PCM.ROM", "ROM1.BIN", "gm.sf2"))
      and not os.path.exists(os.path.join(sysd, "notes.txt")), os.listdir(sysd))

# Import, by Boxer's own rules: DOS programs are told from Windows ones by their headers; boot-disk makers, readers
# and archivers are ignored; an installer (inst, setup, config in a name; install., setup. first) with nothing to
# say the game is installed means the installer is run first, from the source as D:; otherwise the files are copied.
DOSEXE = b"MZ" + b"\0" * 62
PEEXE = b"MZ" + b"\0" * 22 + b"\x40\0" + b"\0" * 34 + b"\x80\0\0\0" + b"\0" * 64 + b"PE\0\0" + b"\0" * 24


def mk(root, files):
    for f, c in files.items():
        os.makedirs(os.path.dirname(os.path.join(root, f)) or root, exist_ok=True)
        open(os.path.join(root, f), "wb").write(c)


src = os.path.join(D, "src", "Prince")
mk(src, {"GAME/PRINCE.EXE": DOSEXE, "GAME/SETUP.EXE": DOSEXE, "INSTALL.BAT": b"@echo off\r\n", "GAME/README.COM": b"x",
         "BOOTDISK.EXE": DOSEXE})
subprocess.run(["zip", "-qr", os.path.join(D, "src", "Zipped.zip"), "Prince"], cwd=D + "/src", check=True)
mk(D + "/src/inst", {"SETUP.EXE": DOSEXE})
ish = os.path.join(D, "ishelf")
shutil.rmtree(ish, True)
os.makedirs(ish)


def imp(*a):
    q = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/boxerplay.hibr\n. %s/apps/Games/boxer.hibr\nBX_SHELF=%s\n%s"
                        % (load("console"), DESK, ROOT, ROOT, ish, "\n".join(a))],
                       capture_output=True, text=True, env=dict(os.environ, **ENVBASE), timeout=60)
    return q.stdout, q.stderr


def doc(b):
    import json
    return json.load(open(os.path.join(b, "gamebox.json")))


out, err = imp("b := bx_import %s/src/Prince; echo \"box=$b\"" % D)
b1 = out.split("box=")[1].strip() if "box=" in out else ""
d1 = doc(b1) if b1 else {}
check("a folder with an installer and nothing saying it is installed is set up to run the installer",
      d1.get("state") == "installing" and d1.get("launch", {}).get("program") == "D:\\INSTALL.BAT", (out, err, d1))
check("the source is the CD in D: (a disc image when xorriso is here, else the folder), and C: is empty for the installer to fill",
      (os.path.exists(b1 + "/drives/d/disc.iso") or os.path.exists(b1 + "/drives/d/GAME/PRINCE.EXE"))
      and not os.listdir(b1 + "/drives/c") and d1.get("mounts", [{}])[0].get("kind") == "cdrom", (out, d1))
out, err = imp("b := bx_import %s/src/Prince '' installed; echo \"box=$b\"" % D)
b2 = out.split("box=")[1].strip() if "box=" in out else ""
d2 = doc(b2) if b2 else {}
progs = d2.get("programs", [])
check("told it is installed, the files are copied into C:, in a folder of their own (programs at the top, no telltale)",
      d2.get("state") == "installed" and bool(__import__("glob").glob(b2 + "/drives/c/*/INSTALL.BAT")) and "PRINCE.EXE" in " ".join(progs),
      (out, err, d2))
check("what Boxer ignores is not listed (the boot-disk maker, the readme), what it does not is",
      not any("BOOTDISK" in x or "README" in x for x in progs) and any("SETUP.EXE" in x for x in progs), progs)
check("with several programs there is none chosen: the shelf asks which to run", not d2.get("launch", {}).get("program"), d2)
out, err = imp("b := bx_import %s/src/Zipped.zip; echo \"box=$b\"" % D)
bz = out.split("box=")[1].strip() if "box=" in out else ""
check("a zip is unpacked and treated the same way", bool(bz) and doc(bz).get("state") == "installing", (out, err))
out, err = imp("b := bx_import %s/src/Prince; echo \"box=$b\"" % D)
check("importing the same name again makes another box", "Prince 3.boxer" in out, out + err)
out, err = imp("b := bx_import %s/src/inst/SETUP.EXE; echo \"box=$b\"" % D)
bi = out.split("box=")[1].strip() if "box=" in out else ""
check("a lone installer is run from D:", bi and doc(bi).get("launch", {}).get("program") == "D:\\SETUP.EXE", (out, err))
# A Windows-only game, and a folder with no DOS programs, are turned away.
mk(D + "/src/winonly", {"GAME.EXE": PEEXE, "SETUP.EXE": PEEXE})
out, err = imp("bx_import %s/src/winonly; echo \\\"rc=$?\\\"" % D)
check("a Windows-only game is refused, and says so", "Windows game" in err, out + err)
mk(D + "/src/empty", {"notes.txt": b"x"})
out, err = imp("bx_import %s/src/empty; echo \\\"rc=$?\\\"" % D)
check("a folder with no DOS programs is refused", "no DOS programs" in err, out + err)
# The installer finishes: what it put on C: is the game, and the CD is kept; with nothing put there, the disc's
# files were the game and move to C:.
mk(b1 + "/drives/c", {"SIERRA/SIERRA.EXE": DOSEXE, "SIERRA/LSL2.EXE": DOSEXE, "SIERRA/BOOTDISK.EXE": DOSEXE})
out, err = imp("bd_finish '%s'; echo done" % b1)
d1 = doc(b1)
check("after an installer that put files on C:, the game is installed and the CD is kept as D:",
      d1.get("state") == "installed" and d1.get("mounts", [{}])[0].get("path") in ("drives/d", "drives/d/disc.iso"), (out, err, d1))
check("its programs are those on C:, the boot-disk maker left out, and none is chosen yet",
      sorted(d1.get("programs", [])) == ["C:\\SIERRA\\LSL2.EXE", "C:\\SIERRA\\SIERRA.EXE"] and not d1.get("launch", {}).get("program"), d1)
out, err = imp("b := bx_import %s/src/Prince; bd_finish \"$b\" 1; echo \"box=$b\"" % D)
bk = out.split("box=")[1].strip() if "box=" in out else ""
check("an installer box said to be installed already has the disc's files moved onto C:, and no CD",
      bool(__import__("glob").glob(bk + "/drives/c/*/GAME/PRINCE.EXE")) and not os.path.exists(bk + "/drives/d")
      and not doc(bk).get("mounts"), (out, err))
# A folder DOS cannot name as it is (a dot, a space, a long name) is renamed so the DOS path is the real one, and a
# folder that is the drive itself (C.harddisk, which also says the game is installed) is hoisted.
mk(D + "/src/Prince of Persia", {"C.harddisk/priceof/PRINCE.EXE": DOSEXE})
out, err = imp("b := bx_import '%s/src/Prince of Persia'; echo \"box=$b\"; find \"$b/drives/c\"" % D)
bp = out.split("box=")[1].split("\n")[0].strip() if "box=" in out else ""
dp = doc(bp) if bp else {}
check("a game in a C.harddisk folder is installed already, hoisted, and its one program is the one to run",
      dp.get("launch", {}).get("program", "").upper() == "C:\\PRICEOF\\PRINCE.EXE", (out, err, dp))
check("and names DOS cannot hold are changed, the path being a real file",
      bp and os.path.exists(bp + "/drives/c/" + dp["launch"]["program"].replace("C:\\", "").replace("\\", "/")),
      dp.get("launch"))
out, err = imp("bx_import_all 9 %s/src/Prince %s/src/nothing-here; echo \"n=${BX[9][n]}\"" % (D, D))
check("a drop imports what it can, skips what it cannot, and the shelf is read again",
      any(("n=%d" % k) in out for k in range(4, 9)), out + err)

# The whole way, on the real core when DBP_CORE names one (cores/build.sh makes it): a folder holding a DOS
# program is imported, its run.conf is given to DOSBox Pure, and the program's text is on the screen -- with the
# banner and the mount message cleared away, so the text is alone at the top.
dbp = os.environ.get("DBP_CORE")
if dbp and os.path.exists(dbp):
    hsrc = os.path.join(D, "src", "Hello")
    os.makedirs(hsrc)
    open(hsrc + "/HELLO.COM", "wb").write(
        b"\xb4\x09\xba\x10\x01\xcd\x21\xb4\x00\xcd\x16\xb8\x00\x4c\xcd\x21Hello from Boxer$")
    out, err = imp(". %s/apps/boxerplay.hibr" % ROOT,
                   "b := bx_import %s; mkdir -p %s/hrun; json parse BPJ \"$(< \"$b/gamebox.json\")\"; "
                   "f := bp_conf \"$b\" %s/hrun; echo \"$b|$f\"" % (hsrc, D, D))
    out = out.strip()
    check("the real core: a folder is imported and its conf made", "|" in out, out + err)
    if "|" in out:
        hb_, conf = out.split("|")
        ppm = os.path.join(D, "hello.ppm")
        rs = subprocess.run([ROOT + "/build/rl_shot", dbp, conf, D + "/sys", hb_ + "/saves", "5", ppm],
                            env=dict(os.environ, HIBR_RETRO_AUDIO="none"), capture_output=True, text=True, timeout=60)
        raw = open(ppm, "rb").read() if os.path.exists(ppm) else b""
        w, h = (640, 400)
        px = raw[len(raw) - w * h * 3:] if raw else b""
        lit = lambda y0, y1: sum(1 for i in range(y0 * w * 3, y1 * w * 3, 3) if px[i] > 128)
        check("the program ran and its text is on the screen, alone at the top",
              px and lit(0, 20) > 20 and lit(60, 400) == 0, (lit(0, 20), lit(60, 400)) if px else (rs.stdout + rs.stderr)[-400:])
        ppm2 = os.path.join(D, "hello2.ppm")
        subprocess.run([ROOT + "/build/rl_shot", dbp, conf, D + "/sys", hb_ + "/saves", "6", ppm2, "97"],
                       env=dict(os.environ, HIBR_RETRO_AUDIO="none"), capture_output=True, timeout=60)
        raw2 = open(ppm2, "rb").read() if os.path.exists(ppm2) else b""
        px2 = raw2[len(raw2) - w * h * 3:] if raw2 else b""
        beside = lambda p: sum(1 for y in range(16) for x in range(130, 170) if p[(y * w + x) * 3] > 128)
        check("a key reaches the program: it was waiting for one, and ends, the prompt following its text",
              px2 and beside(px2) > 10 and beside(px) == 0, (beside(px2), beside(px)) if px2 else "no frame")
        # The mouse, through the desktop's own window: a program that prints X when the left button is down.
        cb = gamebox("Clicker")
        shutil.rmtree(cb + "/drives/c")
        os.makedirs(cb + "/drives/c")
        open(cb + "/drives/c/CLICK.COM", "wb").write(
            b"\xb8\x00\x00\xcd\x33\xb8\x01\x00\xcd\x33\xb8\x03\x00\xcd\x33\xf6\xc3\x01\x74\xf6"
            b"\xb4\x02\xb2\xdb\xcd\x21\xb4\x02\xb2\xdb\xcd\x21\xb8\x00\x4c\xcd\x21")
        open(cb + "/gamebox.json", "w").write('{"gamebox":1,"title":"Clicker","launch":{"program":"C:\\\\CLICK.COM"}}')
        t = desk("", cb, False, {"BP_CORE": dbp})
        for _ in range(40):
            t.collect(0.25)
            if "▀" in t.screen().text():
                break
        t.collect(6.0)
        lit = lambda sc: sum(1 for r in range(2, 5) for c in range(9, 18)
                             if any(v and v != "#000000" for v in (sc.style(r, c).get("fg"), sc.style(r, c).get("bg"))))
        before = lit(t.screen())
        t.send(sx.press(10, 30) + sx.release(10, 30))
        t.collect(2.0)
        after = lit(t.screen())
        check("a click in the window reaches DOS: the program that waits for the left button prints its X",
              after > before, (before, after))
        t.close()
        # Where DOS puts its pointer is where the click was, in a window that is neither at the corner of the screen
        # nor the size it opened at: the cursor block lands within a cell or two of the press.
        pb = gamebox("Pointer")
        shutil.rmtree(pb + "/drives/c")
        os.makedirs(pb + "/drives/c")
        open(pb + "/drives/c/MOUSE.COM", "wb").write(
            b"\xb8\x00\x00\xcd\x33\xb8\x01\x00\xcd\x33\xb4\x00\xcd\x16\xb8\x00\x4c\xcd\x21")
        open(pb + "/gamebox.json", "w").write('{"gamebox":1,"title":"Pointer","launch":{"program":"C:\\\\MOUSE.COM"}}')
        t = desk('dt_resize "$BID" 23 74\ndt_move "$BID" 3 8', pb, False, {"BP_CORE": dbp})
        for _ in range(40):
            t.collect(0.25)
            if "▀" in t.screen().text():
                break
        t.collect(5.0)
        cells = lambda sc: [(r, c) for r in range(5, 25) for c in range(10, 80)
                            if any(v and v != "#000000" for v in (sc.style(r, c).get("fg"), sc.style(r, c).get("bg")))]
        for (pr, pc) in ((14, 45), (10, 60), (20, 25)):
            t.send(sx.press(pr, pc) + sx.release(pr, pc))
            t.collect(1.5)
            got = [x for x in cells(t.screen()) if not (x[0] <= 5 and x[1] <= 14)]
            check("a click at row %d, column %d in an offset, resized window puts DOS's pointer there: %s" % (pr, pc, got[:2]),
                  bool(got) and abs(got[0][0] - pr) <= 2 and abs(got[0][1] - pc) <= 2, got[:3])
        t.close()
        # The installer, on the real core: a game with an installer is set up to run it from D:, the installer puts a
        # file on C:, and closing the window finishes the install: the game is installed, its programs found.
        isrc = os.path.join(D, "src", "Installable")
        mk(isrc, {"INSTALL.COM": b"\xb4\x3c\x31\xc9\xba\x0d\x01\xcd\x21\xb4\x4c\xcd\x21C:\\NEWGAME.COM\0"})
        out, err = imp("b := bx_import '%s'; echo \"box=$b\"" % isrc)
        ib = out.split("box=")[1].strip() if "box=" in out else ""
        check("an installer box starts out installing", ib and doc(ib).get("state") == "installing", (out, err))
        if ib:
            t = desk("", ib, False, {"BP_CORE": dbp})
            t.collect(7.0)
            xr, xc = t.screen().find("x├")
            t.send(sx.press(xr, xc) + sx.release(xr, xc))
            t.collect(1.5)
            t.close()
            di = doc(ib)
            check("the installer ran from D: and wrote to C:, so closing the window finished the install",
                  os.path.exists(ib + "/drives/c/NEWGAME.COM") and di.get("state") == "installed"
                  and "C:\\NEWGAME.COM" in di.get("programs", []), (os.listdir(ib + "/drives/c"), di))
            check("and with one program, that is the one to run", di.get("launch", {}).get("program") == "C:\\NEWGAME.COM", di)
        t = desk("", hb_, True, {"BP_CORE": dbp})
        for _ in range(60):
            t.collect(0.25)
            if b"a=T" in t.raw:
                break
        t.collect(1.0)
        check("and the same box plays in the desktop's window through the real core",
              b"a=T" in t.raw and "Hello" in t.screen().text(), t.screen())
        t.close()

# The default shelf: Dos Games in the home folder; an older shelf is kept in use when it is there and the new one is
# not; the pane lists what is set and the dialog's Save makes the folder.
home = os.path.join(D, "home")
os.makedirs(home + "/.local/share/hibr/shelf")
def withhome(*lines):
    q = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/Games/boxer.hibr\n%s" % (load("console"), DESK, ROOT, "\n".join(lines))],
                       capture_output=True, text=True, env=dict(os.environ, HOME=home, XDG_DATA_HOME=home + "/.local/share",
                                                               XDG_RUNTIME_DIR=D, BX_SHELF=""), timeout=60)
    return q.stdout, q.stderr
out, err = withhome("echo \"shelf=$BX_SHELF\"")
check("an older shelf is kept in use while there is no Dos Games folder", "shelf=%s/.local/share/hibr/shelf" % home in out, out + err)
os.makedirs(home + "/Dos Games")
out, err = withhome("echo \"shelf=$BX_SHELF\"")
check("the default shelf is Dos Games in the home folder once it is there", "shelf=%s/Dos Games" % home in out, out + err)
q = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/Games/boxer.hibr\n. %s/system/panel.hibr\n. %s/control-panel/boxerset.hibr\n"
                    "declare -gA CP; boxerset_rows 40 > /dev/null\n"
                    "for i in 0 1 2 3 4 5 6 7 8 9 10 11; do echo \"$i=${CP[40][$i][text]}|${CP[40][$i][val]}\"; done\n"
                    "BX_SHELF=x; boxerset_do 40 mouse 1; echo \"mouse=$BX_MOUSE\"; boxerset_do 40 sound 1; echo \"sound=$BX_SOUND\""
                    % (load("console"), DESK, ROOT, HIBR_TREE + "/programs/desktop", ROOT)],
                   capture_output=True, text=True, env=dict(os.environ, HOME=home, XDG_RUNTIME_DIR=D, BX_SHELF=home + "/Dos Games"),
                   timeout=60)
out = q.stdout
check("the pane lists the shelf folder, rendering, shape, full screen key, key hold, mouse and sound",
      all(w in out for w in ("Folder", "Rendering", "Shape", "Full Screen Key", "Key Held", "Mouse", "Sound")), out + q.stderr)
check("a row steps through its choices: mouse direct goes to relative, sound toggles",
      "mouse=relative" in out and "sound=off" in out, out + q.stderr)

# The folder dialog in a real desktop: the field is typed into and Save makes the folder and keeps it.
target = os.path.join(D, "My Games")
pth = sx.scratch("boxerdlg.hibr")
open(pth, "w").write(
    "%s. %s\n. %s/system/panel.hibr\n. %s/control-panel/boxerset.hibr\nBX_SHELF=%s/old\n"
    "dt_open\nbxs_dialog\ndt_run\ndt_close\necho \"SHELF=$BX_SHELF\" > %s/shelf.out\n"
    % (load("console"), DESK, HIBR_TREE + "/programs/desktop", ROOT, D, D))
t = Term(pth, rows=26, cols=82, settle=1.0, env=dict(ENVBASE, HOME=home))
t.collect(0.8)
check("the dialog shows the folder it keeps games in", "NAME.boxer" in t.screen().text() and "/old" in t.screen().text(),
      t.screen())
t.send(b"\x7f" * 80)
t.send(target.encode())
t.collect(0.4)
t.send(b"\r")
t.collect(0.8)
t.quit()
t.close()
check("Save makes the folder", os.path.isdir(target), os.listdir(D))

# What the drawer wrote is what DOSBox is told: sections after the person's own, so they win.
out, err = imp(". %s/apps/boxerplay.hibr" % ROOT,
               "b='%s/Alpha Quest.boxer'; json parse BPJ \"$(< \"$b/gamebox.json\")\"; mkdir -p %s/tune; "
               "json set BPJ .machine vgaonly -s; json set BPJ .sound.card sbpro2 -s; json set BPJ .sound.irq 5 -s; "
               "json set BPJ .sound.dma 3 -s; json set BPJ .sound.port 240 -s; json set BPJ .cpu.cycles 8000 -s; "
               "f := bp_conf \"$b\" %s/tune; cat \"$f\"" % (shelf, D, D))
check("a game's speed, graphics and sound are written into the conf after the person's own",
      "[cpu]\ncycles=8000" in out and "[dosbox]\nmachine=vgaonly" in out
      and "[sblaster]\nsbtype=sbpro2\nsbbase=240\nirq=5\ndma=3" in out
      and out.index("cycles=max") < out.index("cycles=8000"), out + err)

# A game with several programs and none chosen asks which to run, when played, and remembers the answer.
csh = os.path.join(D, "chooser")
os.makedirs(csh)
shutil.copytree(b2, os.path.join(csh, os.path.basename(b2)))
p2 = sx.scratch("boxer.hibr")
open(p2, "w").write(
    "%s. %s\n. %s/apps/boxerplay.hibr\n. %s/apps/Games/boxer.hibr\n"
    "dt_open\nBID := dt_launch boxer \"%s\"\ndt_run\ndt_close\n"
    % (load("console", "img", RETRO), DESK, ROOT, ROOT, csh))
t = Term(p2, rows=40, cols=100, settle=1.0, env=ENVBASE)
t.collect(1.5)
t.send(b"\r")
t.collect(1.0)
check("playing a game with no program chosen offers its programs", "PRINCE.EXE" in t.screen().text() and "Boxer Game" not in t.screen().text(),
      t.screen())
t.send(b"\r")
t.collect(1.5)
saved = doc(os.path.join(csh, os.path.basename(b2))).get("launch", {}).get("program", "")
check("choosing one runs it in a window of its own and is remembered as the program to run",
      "Boxer Game" in t.screen().text() and saved.endswith(".EXE") or saved.endswith(".BAT"), (saved, t.screen()))
t.close()

# A game that lives on its disc (Dungeon Keeper wants its CD in D: to be played at all): the image is the box's D:,
# an installer on it is run first, and a game with no installer lists its programs on D: and runs from there.
if shutil.which("xorriso"):
    mk(D + "/cd/dk", {"INSTALL.COM": b"\xb4\x3c\x31\xc9\xba\x0d\x01\xcd\x21\xb4\x4c\xcd\x21C:\\KEEPER.COM\0", "DATA/A.DAT": b"x"})
    subprocess.run(["xorriso", "-as", "mkisofs", "-quiet", "-r", "-iso-level", "1", "-o", D + "/cd/dk.iso", D + "/cd/dk"], check=True,
                   capture_output=True)
    out, err = imp("b := bx_import %s/cd/dk.iso; echo \"box=$b\"" % D)
    bd_ = out.split("box=")[1].strip() if "box=" in out else ""
    dd = doc(bd_) if bd_ else {}
    check("a disc image with an installer: the image is D: as a CD, and the installer on it is what runs",
          dd.get("state") == "installing" and dd.get("launch", {}).get("program") == "D:\\INSTALL.COM"
          and dd.get("mounts", [{}])[0].get("path", "").endswith(".iso") and os.path.exists(bd_ + "/drives/d/dk.iso"), (out, err, dd))
    mk(D + "/cd/run", {"HELLO.COM": b"\xb4\x09\xba\x10\x01\xcd\x21\xb8\x00\x4c\xcd\x21Hello from the CD$", "X.DAT": b"x"})
    subprocess.run(["xorriso", "-as", "mkisofs", "-quiet", "-r", "-iso-level", "1", "-o", D + "/cd/run.iso", D + "/cd/run"], check=True,
                   capture_output=True)
    out, err = imp("b := bx_import %s/cd/run.iso; echo \"box=$b\"" % D)
    br = out.split("box=")[1].strip() if "box=" in out else ""
    dr = doc(br) if br else {}
    check("a disc with no installer runs from the disc: its programs are D: paths, and one program is the one to run",
          dr.get("state") == "installed" and dr.get("programs") == ["D:\\HELLO.COM"] and dr.get("launch", {}).get("program") == "D:\\HELLO.COM", (out, err, dr))
    if dbp and os.path.exists(dbp) and br:
        out2, err2 = imp(". %s/apps/boxerplay.hibr" % ROOT,
                         "b='%s'; json parse BPJ \"$(< \"$b/gamebox.json\")\"; mkdir -p %s/cdrun; f := bp_conf \"$b\" %s/cdrun; echo \"CONF=$f\"" % (br, D, D))
        conf = out2.split("CONF=")[1].strip() if "CONF=" in out2 else ""
        ppm = os.path.join(D, "cd.ppm")
        if conf:
            subprocess.run([ROOT + "/build/rl_shot", dbp, conf, D + "/sys", br + "/saves", "6", ppm],
                           env=dict(os.environ, HIBR_RETRO_AUDIO="none"), capture_output=True, timeout=60)
        raw = open(ppm, "rb").read() if os.path.exists(ppm) else b""
        pxc = raw[len(raw) - 640 * 400 * 3:] if raw else b""
        litc = sum(1 for i in range(0, 640 * 30 * 3, 3) if pxc[i] > 128) if pxc else 0
        check("and it plays from the CD: the program on D: ran from the image DOS sees as a CD-ROM", litc > 20, (litc, out2[-300:], err2[-300:]))

# Boxer registers itself for .boxer folders (hibr #318): a box is a bundle, opened by the game window, with Get Info as a verb.
out, err = imp("mkdir -p %s/bun/X.boxer %s/bun/Y.dir; dt_isbundle %s/bun/X.boxer && echo bundle; dt_isbundle %s/bun/Y.dir && echo plain; "
               "dt_openverbs %s/bun/X.boxer; echo \"verb=${DT_OVLIST[*]}:${DT_OPENVERBS[0][label]}:${DT_OPENVERBS[0][app]}\"" % ((D,) * 5))
check("a .boxer folder is a bundle for Boxer, and has Get Info... as a verb that opens the settings window",
      "bundle" in out and "plain" not in out and "Get Info..." in out and ":boxerinfo" in out, out + err)

shutil.rmtree(D, True)
report()
