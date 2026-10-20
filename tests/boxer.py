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

# Import: a folder, a zip and a lone installer each become a box; the program named for its folder is the one
# to launch, installers and tools sink, a lone installer marks the box, and the same name is not overwritten.
src = os.path.join(D, "src", "Prince")
os.makedirs(src + "/GAME")
for f in ("GAME/PRINCE.EXE", "GAME/SETUP.EXE", "INSTALL.BAT", "GAME/README.COM"):
    open(os.path.join(src, f), "w").write("x")
subprocess.run(["zip", "-qr", os.path.join(D, "src", "Zipped.zip"), "Prince"], cwd=D + "/src", check=True)
os.makedirs(D + "/src/inst")
open(D + "/src/inst/SETUP.EXE", "w").write("x")
ish = os.path.join(D, "ishelf")
shutil.rmtree(ish, True)
os.makedirs(ish)


def imp(*a):
    q = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/Games/boxer.hibr\nBX_SHELF=%s\n%s"
                        % (load("console"), DESK, ROOT, ish, "\n".join(a))],
                       capture_output=True, text=True, env=dict(os.environ, **ENVBASE), timeout=60)
    return q.stdout, q.stderr


out, err = imp("b := bx_import %s/src/Prince; echo \"box=$b\"; cat \"$b/gamebox.json\"" % D)
check("a folder is copied into drives/c of a new box on the shelf",
      "box=%s/Prince.boxer" % ish in out and os.path.exists(ish + "/Prince.boxer/drives/c/GAME/PRINCE.EXE"), out + err)
check("the program named for the folder is the one to launch",
      r'C:\\GAME\\PRINCE.EXE' in out.split('"launch"')[1].split("}")[0], out + err)
check("the others are listed, tools and installers last",
      out.index("PRINCE.EXE") < out.index("SETUP.EXE") and '"installer"' not in out, out)
out, err = imp("b := bx_import %s/src/Zipped.zip; echo \"box=$b\"" % D)
check("a zip is unpacked into a box of its own", os.path.exists(ish + "/Zipped.boxer/drives/c/Prince/GAME/PRINCE.EXE"), out + err)
out, err = imp("b := bx_import %s/src/Prince; echo \"box=$b\"" % D)
check("importing the same name again makes another box", "box=%s/Prince 2.boxer" % ish in out, out + err)
out, err = imp("b := bx_import %s/src/inst/SETUP.EXE; cat \"$b/gamebox.json\"" % D)
check("a lone installer is marked, and is what launches", '"installer": true' in out and "SETUP.EXE" in out, out + err)
# A folder DOS cannot name as it is (a dot, a space, a long name) is renamed so the DOS path is the real one.
os.makedirs(D + "/src/Prince of Persia/C.harddisk/priceof")
open(D + "/src/Prince of Persia/C.harddisk/priceof/PRINCE.EXE", "w").write("x")
out, err = imp("b := bx_import '%s/src/Prince of Persia'; echo \"box=$b\"; cat \"$b/gamebox.json\"; find \"$b/drives/c\"" % D)
prog = [l for l in out.split("\n") if '"program"' in l]
check("a game in folders DOS cannot hold as named is imported with names it can",
      prog and "PRINCE.EXE" in prog[0] and "C.harddisk" not in out.split("find")[-1] and "C~" not in prog[0],
      out + err)
check("and the program's path, taken to the folders as renamed, is a real file",
      prog and os.path.exists(ish + "/Prince of Persia.boxer/drives/c/" + prog[0].split('"')[3].replace("C:\\\\", "").replace("\\\\", "/")),
      prog)
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
        t = desk("", hb_, True, {"BP_CORE": dbp})
        for _ in range(60):
            t.collect(0.25)
            if b"a=T" in t.raw:
                break
        t.collect(1.0)
        check("and the same box plays in the desktop's window through the real core",
              b"a=T" in t.raw and "Hello" in t.screen().text(), t.screen())
        t.close()

shutil.rmtree(D, True)
report()
