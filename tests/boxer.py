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
           "BP_SYS": D + "/sys", "BX_CAPTURE": "seamless", "BX_CONFIRM": "off", "BX_MOUSE": "direct", "BX_MOUSEV": "2", "HIBR_MODPATH": ROOT + "/build", "XDG_CACHE_HOME": D + "/cache"}


def gamebox(name="Test Game"):
    """A gamebox folder: a program, a CD image, the person's own settings and a drive C."""
    b = os.path.join(D, name + ".boxer")
    shutil.rmtree(b, True)
    os.makedirs(b + "/engine")
    os.makedirs(b + "/drives/c/GAME")
    open(b + "/drives/c/GAME/RUN.EXE", "w").write("x")
    open(b + "/engine/dosbox.conf", "w").write("[cpu]\ncycles=max\n[autoexec]\necho mine\n[sdl]\nfullscreen=false\n")
    open(b + "/boxer.json", "w").write(
        '{"boxer":1,"title":"%s","engine":"dosbox",'
        '"launch":{"program":"C:\\\\GAME\\\\RUN.EXE","args":"-fast"},'
        '"mounts":[{"drive":"d","kind":"cdrom","path":"drives/d/game.cue"}],'
        '"display":{"aspect":"4:3"}}' % name)
    return b


def desk(body, box, pix=False, env=None, caps=None, pre=""):
    p = sx.scratch("boxer.hibr")
    open(p, "w").write(
        "%s. %s\n. %s/apps/boxerplay.hibr\n"
        "dt_open\n%s\nBID := dt_launch boxerplay \"%s\"\n%s\ndt_run\ndt_close\n"
        % (load("console", RETRO), DESK, ROOT, pre, box, body))
    kw = dict(cellw=8, cellh=16, caps=["kitty"]) if pix else dict(cellw=8, cellh=16, caps=caps) if caps else {}
    return Term(p, rows=26, cols=82, settle=1.0, env=dict(ENVBASE, **(env or {})), **kw)


box = gamebox()

# The run.conf: the person's own settings first, then an autoexec that mounts C:, the CD, enters the
# program's folder and starts it with its arguments.
hb = sx.HIBR
import subprocess
r = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/boxerplay.hibr\njson parse BPJ \"$(< '%s/boxer.json')\"\n"
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


# Three games in the games folder, one with a cover.
shelf = os.path.join(D, "shelf")
shutil.rmtree(shelf, True)
os.makedirs(shelf)
for nm in ("Alpha Quest", "Beta Racer", "Gamma Blast"):
    b = gamebox(nm)
    shutil.move(b, os.path.join(shelf, nm + ".boxer"))
png(os.path.join(shelf, "Beta Racer.boxer", "cover.png"), 60, 80, (200, 40, 40))


def appdesk(app, arg, pix=False, rows=40, cols=100):
    p = sx.scratch("boxerapp.hibr")
    open(p, "w").write(
        "%s. %s\n. %s/apps/boxerplay.hibr\n. %s/apps/Games/boxer.hibr\n"
        "dt_open\nBID := dt_launch %s \"%s\"\ndt_run\ndt_close\n"
        % (load("console", "img", RETRO), DESK, ROOT, ROOT, app, arg))
    kw = dict(cellw=8, cellh=16, caps=["kitty"]) if pix else {}
    return Term(p, rows=rows, cols=cols, settle=1.0, env=ENVBASE, **kw)


# The Boxer window is where a game is brought in: a diskette and a CD in half blocks, in pixels and without.
for pix in (True, False):
    t = appdesk("boxer", "", pix)
    t.collect(1.5)
    tx = t.screen().text()
    check("the Boxer window offers to take a game (%s): drop one, Import, and the games folder" % ("kitty" if pix else "half blocks"),
          all(w in tx for w in ("Drop a game here", "Import", "Open Games Folder", "Games are kept in")), t.screen())
    check("and it has a diskette and a CD drawn in it, not a list of games", tx.count("\u2580") + tx.count("\u2584") > 40
          and "Alpha Quest" not in tx, tx.count("\u2580"))
    t.close()

# A second game while one plays: Boxer says which is running, brings it forward and opens no window of its own.
import json
two = os.path.join(D, "Second Game.boxer")
shutil.copytree(box, two)
dj = json.load(open(two + "/boxer.json"))
dj["title"] = "Second Game"
json.dump(dj, open(two + "/boxer.json", "w"))
t = desk('sleep 1\nSID := dt_launch boxerplay "%s"\necho "[${BP[$SID]["name"]-gone}|${DT[$SID]["ws"]-none}]" > %s/second.out' % (two, D), box)
t.collect(3.0)
tx = t.screen().text()
check("a second game while one plays says so and names the one running", b"Test Game is already running" in t.raw.replace(b"\x1b[0m", b"") or (b"already running" in t.raw and b"Second Game" in t.raw), tx[:300])
check("and the second one opens no window and no core", os.path.exists(D + "/second.out") and "[gone|none]" in open(D + "/second.out").read() and tx.count("Second Game") == 0, tx[:300])
t.close()

# A game with a relative mouse is locked when it is captured, where the desktop can: raw motion goes to the core,
# the desktop's unlock ends the capture, a lock it refuses leaves a plain capture, and a direct mouse is never locked.
lockbox = os.path.join(D, "Lock Game.boxer")
shutil.copytree(box, lockbox)
def lockrun(mouse, can, steps):
    lj = json.load(open(lockbox + "/boxer.json"))
    lj.update({"title": "Lock Game", "capture": "click", "mouse": mouse})
    json.dump(lj, open(lockbox + "/boxer.json", "w"))
    for f in ("lock.log", "lock.out"):
        if os.path.exists(D + "/" + f):
            os.remove(D + "/" + f)
    pre = ('fn dt_ptrlockcan() { return %d; }\nfn dt_pointerlock(int id, st) { echo "$id:$st" >> %s/lock.log; return 0; }\ndeclare -A LI' % (0 if can else 1, D))
    body = ('sleep 1\nboxerplay_mouse "$BID" press left 10 10 ""\n' + steps +
            'LI := retro info "${BP[$BID]["p"]}"\necho "${LI[motion]}|${BP[$BID]["cap"]}|${BP[$BID]["lock"]}|${BP[$BID]["nolock"]-}" > %s/lock.out' % D)
    t = desk(body, lockbox, False, {}, None, pre)
    t.collect(3.0)
    t.close()
    log = open(D + "/lock.log").read().split() if os.path.exists(D + "/lock.log") else []
    return log, open(D + "/lock.out").read().strip() if os.path.exists(D + "/lock.out") else "no output"
log, out = lockrun("relative", True, 'boxerplay_mouse "$BID" rel none 4 3 rel\nboxerplay_mouse "$BID" rel left -1 5 rel\n')
check("a click in a relative-mouse game asks the desktop for the lock, and its raw motion goes to the core", log[:1] == ["%s:on" % log[0].split(":")[0]] and out.startswith("8 3|1|1|"), (log, out))
log, out = lockrun("relative", True, 'boxerplay_mouse "$BID" rel none 4 3 rel\nboxerplay_mouse "$BID" unlock none 0 0 ""\n')
check("the desktop's unlock after use ends the capture", out.endswith("|0|0|") or out.endswith("|0|0"), (log, out))
log, out = lockrun("relative", True, 'boxerplay_mouse "$BID" unlock none 0 0 ""\n')
check("a lock the desktop refuses leaves a plain capture, and is not asked for again", out.split("|")[1:] == ["1", "0", "1"], (log, out))
log, out = lockrun("relative", False, "")
check("where no display can hold the pointer the capture is the plain one and no lock is asked for", log == [] and out.split("|")[1:3] == ["1", "0"], (log, out))
log, out = lockrun("direct", True, "")
check("a game with a direct mouse is captured but never locked", log == [] and out.split("|")[1:3] == ["1", "0"], (log, out))

# The same through the desktop's own pointer lock (hibr 0.99.365) on a terminal that answers for it: a click in the
# relative-mouse game asks for the lock, a report is raw motion for the core, Release Pointer gives it back.
if "ptrrelease" in open(HIBR_TREE + "/programs/desktop/wm/input.hibr").read():
    lj = json.load(open(lockbox + "/boxer.json"))
    lj.update({"title": "Lock Game", "capture": "click", "mouse": "relative"})
    json.dump(lj, open(lockbox + "/boxer.json", "w"))
    if os.path.exists(D + "/lock.dtlog"):
        os.remove(D + "/lock.dtlog")
    pre = 'dt_log() { echo "$*" >> %s/lock.dtlog; }' % D
    rd = lambda: open(D + "/lock.dtlog").read() if os.path.exists(D + "/lock.dtlog") else ""
    t = desk('dt_resize "$BID" 23 74\ndt_move "$BID" 3 8', lockbox, False, {"DT_HOVER": "on"}, ["lock"], pre)
    t.collect(2.5)
    t.send(sx.press(14, 45) + sx.release(14, 45))
    t.collect(1.0)
    check("a click in a relative-mouse game takes the desktop's pointer lock", b"\x1b[?7701h" in t.raw, t.raw[-200:])
    t.send(b"\x1b[<35;5;-3M")
    t.collect(0.8)
    check("and a report while it is held reaches the window as motion, and the desktop's log says so for a run read afterwards",
          "pointer lock: asked" in rd() and "holding: the first report came" in rd(), rd())
    t.send(b"\x1b[21;5~")
    t.collect(0.8)
    check("Release Pointer gives it back, and the capture ends with a notice", b"\x1b[?7701l" in t.raw and "Mouse released" in t.raw.decode("utf-8", "replace"), t.raw[-300:])
    check("and the log says it ended", "ended: the desktop gave the pointer back" in rd(), rd())
    t.send(sx.press(14, 45) + sx.release(14, 45))
    t.collect(1.0)
    check("a click after that takes the lock again, so the release really ended it", rd().count("pointer lock: asked") == 2, rd())
    t.close()
    # Going full screen with the mouse captured: the capture and the lock stay; and if the terminal lets go as the screen
    # is redrawn (played here by the display's own release), the lock is asked for again and the capture is not dropped.
    lj = json.load(open(lockbox + "/boxer.json"))
    lj.update({"title": "Lock Game", "capture": "click", "mouse": "relative"})
    json.dump(lj, open(lockbox + "/boxer.json", "w"))
    if os.path.exists(D + "/lock.dtlog"):
        os.remove(D + "/lock.dtlog")
    t = desk('dt_resize "$BID" 23 74\ndt_move "$BID" 3 8', lockbox, False, {"DT_HOVER": "on", "BX_FULLKEY": "alt-enter"}, ["lock"], pre)
    t.collect(2.5)
    t.send(sx.press(14, 45) + sx.release(14, 45))
    t.collect(1.5)
    t.send(b"\x1b\r")
    t.collect(0.5)
    t.send(b"\x1b[?7701;2$y")
    t.collect(1.5)
    check("full screen with the mouse captured keeps the capture, and takes no bar or frame", "File  Edit" not in t.screen().text()
          and "Mouse released" not in t.raw.decode("utf-8", "replace"), t.screen())
    check("and a release right after the change (the display letting go, played here) is answered by asking again",
          t.raw.count(b"\x1b[?7701h") == 2 and "asking for the lock again" in rd(), (t.raw.count(b"\x1b[?7701h"), rd()))
    t.close()
    # A capture that has had no report when Release Pointer is pressed (the click's own release never came) is let go, not taken for a refusal.
    t = desk('dt_resize "$BID" 23 74\ndt_move "$BID" 3 8', lockbox, False, {"DT_HOVER": "on"}, ["lock"], pre)
    t.collect(2.5)
    t.send(sx.press(14, 45))
    t.collect(1.0)
    t.send(b"\x1b[21;5~")
    t.collect(0.8)
    check("Release Pointer before the pointer has moved lets the capture go, as it should",
          b"\x1b[?7701h" in t.raw and "Mouse released" in t.raw.decode("utf-8", "replace"), t.raw[-300:])
    t.close()
    # A game on the default direct mouse says once, when it is captured, where the relative mouse is; the Game menu
    # switches it while playing, the core is told, the box remembers, and a captured game asks for the lock at once.
    lj = json.load(open(lockbox + "/boxer.json"))
    lj.update({"title": "Lock Game", "capture": "click", "mouse": "direct"})
    json.dump(lj, open(lockbox + "/boxer.json", "w"))
    if os.path.exists(D + "/lock.dtlog"):
        os.remove(D + "/lock.dtlog")
    t = desk('dt_resize "$BID" 23 74\ndt_move "$BID" 3 8', lockbox, False, {"DT_HOVER": "on"}, ["lock"], pre)
    t.collect(2.5)
    t.send(sx.press(14, 45) + sx.release(14, 45))
    t.collect(1.0)
    txt = t.raw.decode("utf-8", "replace")
    check("a captured game on the direct mouse says where the relative mouse is, and asks for no lock",
          "Doom-like?" in txt and "Mouse captured, f12 lets go" in txt and b"\x1b[?7701h" not in t.raw and "mouse is not relative" in rd(), (txt[-200:], rd()))
    t.collect(4.0)
    t.send(b"\x1b[21~\x1b[C\x1b[C\x1b[C")
    t.collect(0.8)
    check("and the Game menu has Relative Mouse", "Capture Mouse" in t.screen().text() and "Relative Mouse" in t.screen().text(), t.screen())
    t.send(b"m")
    t.collect(1.0)
    lj = json.load(open(lockbox + "/boxer.json"))
    check("choosing it writes mouse relative into the box, and a captured game asks for the lock at once",
          lj.get("mouse") == "relative" and b"\x1b[?7701h" in t.raw and "pointer lock: asked" in rd(), (lj.get("mouse"), rd()))
    t.close()

    t = desk('dt_resize "$BID" 23 74\ndt_move "$BID" 3 8', lockbox, False, {"DT_HOVER": "on"}, [], pre)
    t.collect(2.5)
    t.send(sx.press(14, 45) + sx.release(14, 45))
    t.collect(1.0)
    check("on a terminal that cannot hold the pointer none is asked for, and the click still captures",
          b"\x1b[?7701h" not in t.raw and "Mouse captured. f12" in t.raw.decode("utf-8", "replace"), t.raw[-200:])
    t.close()


# The full-screen key asks the desktop for the whole display where it can (hibr #405), and zooms where it cannot.
if os.path.exists(D + "/fs.log"):
    os.remove(D + "/fs.log")
t = desk("", box, False, {"BX_FULLKEY": "f11"}, None, 'fn dt_fullscreen(int id, how) { echo "$id:$how" >> %s/fs.log; return 0; }' % D)
t.collect(2.0)
t.send(b"\x1b[23~")
t.collect(1.0)
check("the full-screen key asks the desktop for full screen (toggle) when it has it",
      os.path.exists(D + "/fs.log") and open(D + "/fs.log").read().split()[-1].endswith(":toggle"), open(D + "/fs.log").read() if os.path.exists(D + "/fs.log") else "no call")
t.close()
t = desk("", box, False, {"BX_FULLKEY": "f11", "BX_TRUEFULL": "off"}, None, 'fn dt_fullscreen(int id, how) { echo "$id:$how" >> %s/fs2.log; return 0; }' % D)
t.collect(2.0)
w0 = t.screen().text()
t.send(b"\x1b[23~")
t.collect(1.0)
check("and zooms the window as before when true full screen is off (BX_TRUEFULL=off), and says why", t.screen().text() != w0 and not os.path.exists(D + "/fs2.log") and "true full screen is off" in t.raw.decode("utf-8", "replace"), t.screen())
t.close()

# True full screen on a hibr that has it (0.99.380): Alt+Enter takes the whole display, the picture stays, the desktop's
# leave key and Alt+Enter both give it back, in half blocks and in pixels.
if os.path.exists(HIBR_TREE + "/programs/desktop/wm/fullscreen.hibr"):
    def fst(t):
        tx = t.screen().text()
        return ("File  Edit" in tx, "Test Game" in tx, tx.count("\u2580"), t.raw.count(b"a=T"))
    for pix in (False, True):
        t = desk("", box, pix, {"BX_FULLKEY": "alt-enter"})
        t.collect(2.5)
        b0 = fst(t)
        t.send(b"\x1b\r")
        t.collect(2.5)
        b1 = fst(t)
        full = (not b1[0] and not b1[1] and (b1[2] > b0[2] if not pix else b1[3] > b0[3]))
        check("Alt+Enter takes the whole display (no bar, no frame) and the picture stays (%s)" % ("kitty" if pix else "half blocks"), full, (b0, b1))
        check("and the desktop says how to leave", "leaves it" in t.screen().text() or "leaves it" in t.raw.decode("utf-8", "replace"), t.raw[-200:])
        t.send(b"\x1b[23;5~")
        t.collect(2.0)
        b2 = fst(t)
        check("Ctrl+F11 gives the bar and frame back (%s)" % ("kitty" if pix else "half blocks"), b2[0] and b2[1], b2)
        t.send(b"\x1b\r")
        t.collect(2.0)
        t.send(b"\x1b\r")
        t.collect(2.0)
        b3 = fst(t)
        check("and Alt+Enter toggles it out again (%s)" % ("kitty" if pix else "half blocks"), b3[0] and b3[1], b3)
        t.close()

# Closing a playing game asks first (Confirm On Exit), and a game that ends closes its window (Close When Game Ends).
for conf in ("on", "off"):
    t = desk('sleep 1\ndt_closereq "$BID"\nsleep 0.2\necho "[${BP[$BID]["name"]-gone}]" > %s/closed.%s' % (D, conf), box, env={"BX_CONFIRM": conf})
    t.collect(3.5)
    tx = t.screen().text()
    left = open(D + "/closed." + conf).read() if os.path.exists(D + "/closed." + conf) else ""
    if conf == "on":
        check("closing a playing game asks first", "Quit Test Game?" in tx and "[Test Game]" in left, (tx[:200], left))
    else:
        check("with Confirm On Exit off the window just closes", "[gone]" in left and "Quit" not in tx, (tx[:200], left))
    t.close()
for ac in ("on", "off"):
    t = desk('sleep 1.5\nretro key "${BP[$BID]["p"]}" q tap', box, env={"BX_AUTOCLOSE": ac, "BX_CONFIRM": "off"})
    t.collect(6.0)
    tx = t.screen().text()
    check("a game that ends %s" % ("closes its window" if ac == "on" else "leaves its window when Close When Game Ends is off"),
          ("Test Game" not in tx) == (ac == "on"), tx[:200])
    t.close()

# Get Info opens the settings in a window of their own; a field changed there is written into the box.
t = appdesk("boxerinfo", os.path.join(shelf, "Beta Racer.boxer"))
t.collect(1.2)
sc = t.screen()
check("Get Info opens the game's settings: name, program, speed, graphics, sound card, IRQ, DMA, port, MIDI, mouse",
      all(w in sc.text() for w in ("Beta Racer Settings", "Name", "Program", "Speed", "Graphics", "Sound Card", "Sound IRQ",
                                   "Sound DMA", "Sound Port", "MIDI", "Mouse", "3D (Voodoo)", "3D Speed", "Speed Limit", "CPU")), sc)
t.send(b"\x1b[B" * 8 + b"\x1b[C")
t.collect(0.8)
doc = open(os.path.join(shelf, "Beta Racer.boxer", "boxer.json")).read()
check("a field changed in that window (Sound IRQ) is written into the box", '"irq": "3"' in doc, doc)
t.close()
# The CPU is the last row: the second choice after default, written into the box.
t = appdesk("boxerinfo", os.path.join(shelf, "Beta Racer.boxer"))
t.collect(1.2)
t.send(b"\x1b[B" * 15 + b"\x1b[C")
t.collect(0.8)
doc = open(os.path.join(shelf, "Beta Racer.boxer", "boxer.json")).read()
check("the CPU row of Get Info writes the emulated CPU type into the box", '"type": "auto"' in doc, doc)
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
    return json.load(open(os.path.join(b, "boxer.json")))


# A game dropped on it is made into a game and the window says so.
dd = os.path.join(D, "dropme", "Dropped Game")
os.makedirs(dd)
open(dd + "/GAME.EXE", "wb").write(b"MZ" + bytes(62))
out, err = imp("BX_SHELF=%s/dropgames; boxer_open 1 ''; boxer_drop 1 0 0 move '%s'; echo \"status=${BX[1][status]}\"" % (D, dd))
check("a game dropped on the window becomes a NAME.boxer in the games folder, and it is said", os.path.isdir(D + "/dropgames/Dropped Game.boxer")
      and "Added Dropped Game" in out, (out, err))


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
out, err = imp("bx_import_all 9 %s/src/Prince %s/src/nothing-here; echo \"status=${BX[9][status]}\"" % (D, D))
check("a drop imports what it can and skips what it cannot, the window saying what was added",
      "status=Added Prince" in out, out + err)

# The whole way, on the real core when DBP_CORE names one (cores/build.sh makes it): a folder holding a DOS
# program is imported, its run.conf is given to DOSBox Pure, and the program's text is on the screen -- with the
# banner and the mount message cleared away, so the text is alone at the top.
dbp = os.environ.get("DBP_CORE")
# The DOSBox Pure under test is the one cores/PINS names, so what is tested is what is shipped.
if dbp:
    pin = [l.split() for l in open(ROOT + "/cores/PINS") if l.startswith("dosbox_pure ")][0]
    check("the DOSBox Pure under test is the pinned version %s" % pin[2], pin[2].encode() in open(dbp, "rb").read(), dbp)
if dbp and os.path.exists(dbp):
    hsrc = os.path.join(D, "src", "Hello")
    os.makedirs(hsrc)
    open(hsrc + "/HELLO.COM", "wb").write(
        b"\xb4\x09\xba\x10\x01\xcd\x21\xb4\x00\xcd\x16\xb8\x00\x4c\xcd\x21Hello from Boxer$")
    out, err = imp(". %s/apps/boxerplay.hibr" % ROOT,
                   "b := bx_import %s; mkdir -p %s/hrun; json parse BPJ \"$(< \"$b/boxer.json\")\"; "
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
        open(cb + "/boxer.json", "w").write('{"boxer":1,"title":"Clicker","launch":{"program":"C:\\\\CLICK.COM"}}')
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
        open(pb + "/boxer.json", "w").write('{"boxer":1,"title":"Pointer","launch":{"program":"C:\\\\MOUSE.COM"}}')
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
        # With hovering on, the pointer needs no button: motion alone puts DOS's pointer under it.
        t = desk('dt_resize "$BID" 23 74\ndt_move "$BID" 3 8', pb, False, {"BP_CORE": dbp, "DT_HOVER": "on"}, None,
                 'fn dt_pointer(int id, shape = "") { echo "$id:$shape" >> %s/ptr; DT[$id]["ptr"]=$shape; }' % D)
        for _ in range(40):
            t.collect(0.25)
            if "▀" in t.screen().text():
                break
        t.collect(5.0)
        t.send(b"\x1b[<35;%d;%dM" % (45 + 1, 14 + 1))
        t.collect(1.5)
        got = [x for x in cells(t.screen()) if not (x[0] <= 5 and x[1] <= 14)]
        check("the pointer moving with no button down puts DOS's pointer there: %s" % (got[:2],),
              bool(got) and abs(got[0][0] - 14) <= 2 and abs(got[0][1] - 45) <= 2, got[:3])
        check("a playing game window asks the desktop to hide the terminal's pointer over it: %s" % (open(D + "/ptr").read() if os.path.exists(D + "/ptr") else "no request"),
              os.path.exists(D + "/ptr") and ":none" in open(D + "/ptr").read(), "")
        t.close()
        # A game set to capture on click: hovering does nothing until it is clicked in, then the pointer follows,
        # and F12 lets it go.
        open(pb + "/boxer.json", "w").write('{"boxer":1,"title":"Pointer","capture":"click","launch":{"program":"C:\\\\MOUSE.COM"}}')
        t = desk('dt_resize "$BID" 23 74\ndt_move "$BID" 3 8', pb, False, {"BP_CORE": dbp, "DT_HOVER": "on"})
        for _ in range(40):
            t.collect(0.25)
            if "▀" in t.screen().text():
                break
        t.collect(5.0)
        gotc = lambda: [x for x in cells(t.screen()) if not (x[0] <= 5 and x[1] <= 14)]
        g0 = gotc()
        t.send(b"\x1b[<35;%d;%dM" % (25 + 1, 20 + 1))
        t.collect(1.5)
        check("capture on click: the pointer moving over the window is not taken before a click: %s" % (g0[:1],), gotc() == g0, (g0[:2], gotc()[:2]))
        t.send(sx.press(10, 60) + sx.release(10, 60))
        t.collect(1.0)
        t.send(b"\x1b[<35;%d;%dM" % (60 + 1, 9 + 1))
        t.collect(1.5)
        g = gotc()
        check("and after a click in, the pointer follows: %s" % (g[:1],), bool(g) and abs(g[0][0] - 9) <= 2 and abs(g[0][1] - 60) <= 2, g[:3])
        t.send(b"\x1b[24~")
        t.collect(0.5)
        t.send(b"\x1b[<35;%d;%dM" % (45 + 1, 14 + 1))
        t.collect(1.5)
        g2 = gotc()
        check("and F12 lets it go: the pointer no longer follows", g2 == g, (g[:2], g2[:2]))
        t.close()
        open(pb + "/boxer.json", "w").write('{"boxer":1,"title":"Pointer","capture":"seamless","launch":{"program":"C:\\\\MOUSE.COM"}}')
        # A terminal that reports the pointer in pixels (hovering Auto turns on by itself): the pixel is turned into
        # a place over the picture, and DOS's pointer lands in the cell the pixel is in, not one over.
        t = desk('dt_resize "$BID" 23 74\ndt_move "$BID" 3 8', pb, False, {"BP_CORE": dbp}, ["mpix"])
        for _ in range(40):
            t.collect(0.25)
            if "▀" in t.screen().text():
                break
        t.collect(5.0)
        for (pr, pc) in ((14, 45), (9, 20)):
            t.send(b"\x1b[<35;%d;%dM" % (pc * 8 + 5, pr * 16 + 9))
            t.collect(1.5)
            got = [x for x in cells(t.screen()) if not (x[0] <= 5 and x[1] <= 14)]
            check("a pointer reported in pixels at row %d, column %d (hover Auto) puts DOS's pointer in that cell: %s" % (pr, pc, got[:1]),
                  bool(got) and abs(got[0][0] - pr) <= 1 and abs(got[0][1] - pc) <= 1, got[:3])
        # Closing a window on the real core ends a core and, for an installer, finishes the install, which is file work done
        # while the desktop reads nothing: the console says so (a descriptor ready for 2 s with nothing reading it), which is
        # its way of noticing a slow close and not a shell error. Only that note, only for this stretch.
        errs0 = len(sx.ERRS)
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
            sx.ERRS[errs0:] = [e for e in sx.ERRS[errs0:] if not e.startswith("console: watched descriptor")]
        # EXIT at the DOS prompt ends the real core only when it is told to exit, which Close When Game Ends does.
        for ac in ("on", "off"):
            t = desk("", hb_, False, {"BP_CORE": dbp, "BX_AUTOCLOSE": ac})
            t.collect(5.0)
            t.send(b" ")
            t.collect(2.0)
            for ch in (b"e", b"x", b"i", b"t", b"\r"):
                t.send(ch)
                t.collect(0.3)
            t.collect(8.0)
            tx = t.screen().text()
            check("EXIT at the DOS prompt %s with Close When Game Ends %s" % ("closes the window" if ac == "on" else "leaves the window", ac),
                  ("\u2524 Hello \u251c" not in tx) == (ac == "on"), tx[:300])
            t.close()
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
                    "for i in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26; do echo \"$i=${CP[40][$i][text]}|${CP[40][$i][val]}\"; done\n"
                    "BX_SHELF=x; boxerset_do 40 mouse 1; echo \"mouse=$BX_MOUSE\"; boxerset_do 40 sound 1; echo \"sound=$BX_SOUND\""
                    % (load("console"), DESK, ROOT, HIBR_TREE + "/programs/desktop", ROOT)],
                   capture_output=True, text=True, env=dict(os.environ, HOME=home, XDG_RUNTIME_DIR=D, BX_SHELF=home + "/Dos Games"),
                   timeout=60)
out = q.stdout
check("the pane lists the shelf folder, rendering, shape, full screen key, key hold, mouse and sound",
      all(w in out for w in ("Folder", "Rendering", "Shape", "Full Screen Key", "Release Mouse Key", "Key Held", "Mouse", "Mouse Capture", "Speed Limit", "Confirm On Exit", "Close When Game Ends", "Sound")), out + q.stderr)
check("a row steps through its choices: the mouse, relative by default, goes to off; sound toggles",
      "mouse=off" in out and "sound=off" in out, out + q.stderr)
check("the pane has Fetch Box Art, off until it is turned on", "Fetch Box Art|off" in out, out + q.stderr)

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
               "b='%s/Alpha Quest.boxer'; json parse BPJ \"$(< \"$b/boxer.json\")\"; mkdir -p %s/tune; "
               "json set BPJ .machine vgaonly -s; json set BPJ .sound.card sbpro2 -s; json set BPJ .sound.irq 5 -s; "
               "json set BPJ .sound.dma 3 -s; json set BPJ .sound.port 240 -s; json set BPJ .cpu.cycles 8000 -s; "
               "f := bp_conf \"$b\" %s/tune; cat \"$f\"" % (shelf, D, D))
check("a game's speed, graphics and sound are written into the conf after the person's own",
      "[cpu]\ncycles=8000" in out and "[dosbox]\nmachine=vgaonly" in out
      and "[sblaster]\nsbtype=sbpro2\nsbbase=240\nirq=5\ndma=3" in out
      and out.index("cycles=max") < out.index("cycles=8000"), out + err)

# 3dfx Voodoo: left to the core when nothing is set, and the settings reach it as its own options.
vox = os.path.join(D, "voodoo")
os.makedirs(vox)
def voo(js):
    open(vox + "/boxer.json", "w").write(js)
    r = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/boxerplay.hibr\njson parse BPJ \"$(< '%s/boxer.json')\"\nv := bp_voodoo BPJ; echo \"[$v]\"\n"
                        % (load("console"), DESK, ROOT, vox)],
                       capture_output=True, text=True, env=dict(os.environ, **ENVBASE), timeout=60)
    return r.stdout.strip() + r.stderr
check("a game with no Voodoo setting leaves the core's own: nothing is passed", voo('{"boxer":1}') == "[]", voo('{"boxer":1}'))
got = voo('{"boxer":1,"voodoo":"12mb","voodoospeed":"single"}')
check("a Voodoo memory and speed are passed as the core's options", got == "[dosbox_pure_voodoo=12mb dosbox_pure_voodoo_perf=0]", got)
got = voo('{"boxer":1,"voodoo":"off"}')
check("Voodoo off is passed as off", got == "[dosbox_pure_voodoo=off]", got)

# The mouse is relative unless chosen otherwise; a setting that still says direct from before the default changed is
# moved once, and a direct chosen since then stays.
def mousedef(**env):
    e = {k: v for k, v in os.environ.items() if not k.startswith("BX_")}
    e.update(env)
    r = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/boxerplay.hibr\necho \"mouse=$BX_MOUSE v=$BX_MOUSEV\"\n" % (load("console"), DESK, ROOT)],
                       capture_output=True, text=True, env=e, timeout=60)
    return r.stdout.strip() + r.stderr
got = mousedef()
check("the mouse is relative by default", "mouse=relative v=2" in got, got)
got = mousedef(BX_MOUSE="direct")
check("a direct saved before the default changed was the old default and becomes relative, once", "mouse=relative v=2" in got, got)
got = mousedef(BX_MOUSE="direct", BX_MOUSEV="2")
check("a direct chosen since stays direct", "mouse=direct v=2" in got, got)
got = mousedef(BX_MOUSE="off")
check("and an off is never touched", "mouse=off v=2" in got, got)

# The speed limit: how fast the emulated machine may go, since DOS games never sleep and a core would be spent on their
# waiting loops. The names stand for the core's own cycles.
def lim(*names):
    r = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/boxerplay.hibr\nfor n in %s; do v := bp_limit \"$n\"; echo \"$n=$v\"; done\n"
                        % (load("console"), DESK, ROOT, " ".join(names))],
                       capture_output=True, text=True, env=dict(os.environ, **ENVBASE), timeout=60)
    return r.stdout.split() + ([r.stderr] if r.stderr.strip() else [])
got = lim("unlimited", "pentium2", "pentium", "486dx2", "486dx", "386", "bogus")
check("a speed limit name is the core's cycles for that machine, and an unknown one is the default (Pentium)",
      got == ["unlimited=none", "pentium2=200000", "pentium=77000", "486dx2=26800", "486dx=13400", "386=4720", "bogus=77000"], got)

# The pane's MIDI Output dropdown lists the same synths, with the player loaded as it is in the desktop.
q = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/Games/boxer.hibr\n. %s/system/panel.hibr\n. %s/control-panel/boxerset.hibr\n"
                    ". %s/apps/boxerplay.hibr\nBX_MIDIDIR=%s\nm := bxs_midis; echo \"[$m]\""
                    % (load("console", RETRO), DESK, ROOT, HIBR_TREE + "/programs/desktop", ROOT + "", ROOT, md)],
                   capture_output=True, text=True, env=dict(os.environ, **ENVBASE), timeout=60)
check("the MIDI Output dropdown offers disabled and each synth in the folder",
      "[disabled MT32_CONTROL.ROM ROM1.BIN gm.sf2]" in q.stdout or ("MT32_CONTROL.ROM" in q.stdout and "gm.sf2" in q.stdout and "disabled" in q.stdout),
      q.stdout + q.stderr)

# The defaults: a mouse is captured on a click, and F12 lets it go.
env0 = dict(os.environ, **ENVBASE)
env0.pop("BX_CAPTURE", None)
env0.pop("BX_RELKEY", None)
q = subprocess.run([hb, "-c", "%s. %s\n. %s/apps/Games/boxer.hibr\n. %s/system/panel.hibr\n. %s/control-panel/boxerset.hibr\n"
                    "echo \"$BX_CAPTURE $BX_RELKEY\""
                    % (load("console", RETRO), DESK, ROOT, HIBR_TREE + "/programs/desktop", ROOT)],
                   capture_output=True, text=True, env=env0, timeout=60)
check("a mouse is captured on a click by default, and F12 lets it go", q.stdout.strip() == "click f12", q.stdout + q.stderr)

# A game with several programs and none chosen asks which to run, in its own window, and remembers the answer.
csh = os.path.join(D, "chooser")
os.makedirs(csh)
shutil.copytree(b2, os.path.join(csh, os.path.basename(b2)))
t = appdesk("boxerplay", os.path.join(csh, os.path.basename(b2)))
t.collect(1.5)
check("playing a game with no program chosen offers its programs", "PRINCE.EXE" in t.screen().text() and "Which program" in t.screen().text(),
      t.screen())
# The mouse picks a program too: a click on its row (the desktop sends it to _mouse, never to _click).
cbox = os.path.join(csh, os.path.basename(b2))
pos = t.screen().find("PRINCE.EXE")
t.send(sx.press(pos[0], pos[1] + 2) + sx.release(pos[0], pos[1] + 2))
t.collect(2.0)
saved = doc(cbox).get("launch", {}).get("program", "")
check("a click on a program in the list runs it and remembers it, as Enter does", saved.upper().endswith("PRINCE.EXE") and "Which program" not in t.screen().text(), (saved, t.screen()))
t.close()
d0 = doc(cbox)
d0.get("launch", {}).pop("program", None)
json.dump(d0, open(os.path.join(cbox, "boxer.json"), "w"))
t = appdesk("boxerplay", cbox)
t.collect(1.5)
t.send(b"\r")
t.collect(1.5)
saved = doc(os.path.join(csh, os.path.basename(b2))).get("launch", {}).get("program", "")
check("choosing one runs it and is remembered as the program to run",
      "Which program" not in t.screen().text() and (saved.endswith(".EXE") or saved.endswith(".BAT")), (saved, t.screen()))
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
                         "b='%s'; json parse BPJ \"$(< \"$b/boxer.json\")\"; mkdir -p %s/cdrun; f := bp_conf \"$b\" %s/cdrun; echo \"CONF=$f\"" % (br, D, D))
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

# The verbs Files offers on a .boxer folder: Get Info, Fetch Cover and Game Is Already Installed, each a small window.
out, err = imp("mkdir -p %s/bun/V.boxer; dt_openverbs %s/bun/V.boxer; for i in \"${DT_OVLIST[@]}\"; do echo \"verb=${DT_OPENVERBS[$i][label]}\"; done" % (D, D))
check("a .boxer folder is offered Get Info, Fetch Cover and Game Is Already Installed",
      all(w in out for w in ("verb=Get Info...", "verb=Fetch Cover...", "verb=Game Is Already Installed...")), out + err)
t = appdesk("boxercover", os.path.join(shelf, "Beta Racer.boxer"))
t.collect(1.0)
check("Fetch Cover asks first, and says the game's name goes to the server",
      "Fetch the box art for Beta Racer" in t.screen().text() and "thumbnails.libretro.com" in t.screen().text(), t.screen())
t.send(b"\x1b")
t.collect(0.6)
check("and Escape lets it go without fetching", "Fetch the box art" not in t.screen().text() and not os.path.exists(os.path.join(shelf, "Beta Racer.boxer", ".cover.png")), t.screen())
t.close()
t = appdesk("boxerdone", os.path.join(shelf, "Beta Racer.boxer"))
t.collect(1.0)
check("Game Is Already Installed says so when the game is not waiting for an install", "not waiting to be installed" in t.screen().text(), t.screen())
t.close()

# About Boxer names Boxer, says this is a tribute, and gives its author and where it lives.
pa = sx.scratch("boxerabout.hibr")
open(pa, "w").write(
    "%s. %s\n. %s/apps/boxerplay.hibr\n. %s/apps/Games/boxer.hibr\n"
    "dt_open\nboxer_about\ndt_run\ndt_close\n" % (load("console", "img", RETRO), DESK, ROOT, ROOT))
t = Term(pa, rows=40, cols=100, settle=1.0, env=ENVBASE)
t.collect(1.0)
tx = t.screen().text()
check("About Boxer is a tribute to Boxer, with its author and its address",
      all(w in tx for w in ("tribute to Boxer", "Alun Bestor", "https://boxerapp.com", "github.com/alunbestor/Boxer", "and contributors)", "thumbnails project.")), t.screen())
check("and it names what Boxer runs on: DOSBox Pure and its author, DOSBox, Munt, Nuked, libretro",
      all(w in tx for w in ("DOSBox Pure", "Bernhard Schelling", "DOSBox Team", "codeberg.org/schelling/dosbox-pure", "Munt", "Nuke.YKT", "libretro")), t.screen())
check("and the buttons are not drawn over the credits", "OK" in tx and "thumbnails project." in tx and "runs on hibr" in tx, t.screen())
t.send(b"\r")
t.collect(0.6)
check("and Enter closes it", "tribute to Boxer" not in t.screen().text(), t.screen())
t.close()
# On a short terminal the blank lines go before any credit does.
t = Term(pa, rows=24, cols=80, settle=1.0, env=ENVBASE)
t.collect(1.0)
tx = t.screen().text()
check("About on a 24-row terminal still names DOSBox Pure, DOSBox, Munt, Nuked and libretro, and has its button",
      all(w in tx for w in ("DOSBox Pure", "DOSBox Team", "Munt", "Nuke.YKT", "libretro", "OK")), t.screen())
t.close()

def boxnamed(n):
    b = os.path.join(D, "art-" + n + ".boxer")
    shutil.rmtree(b, True)
    os.makedirs(b + "/drives/c")
    open(b + "/boxer.json", "w").write('{"boxer":1,"title":"%s"}' % n)
    return b


# A box made when its file was gamebox.json has it renamed boxer.json when touched, the rest kept.
ob = os.path.join(D, "Old Game.boxer")
shutil.rmtree(ob, True)
os.makedirs(ob + "/drives/c")
open(ob + "/gamebox.json", "w").write('{"gamebox":1,"title":"Old Game","launch":{"program":"C:\\\\X.EXE"}}')
out, err = imp("bm_up '%s'; ls '%s'; json parse BXJ \"$(< '%s/boxer.json')\"; json get BXJ .launch.program" % (ob, ob, ob))
check("a box with the old gamebox.json name has it renamed boxer.json, and what it held is kept",
      "boxer.json" in out and "gamebox.json" not in out and "X.EXE" in out, (out, err))

# The game's name is in its Game Settings window: typed there it changes the title and the folder together; a name
# another game has is refused.
rb = boxnamed("Rename Me")
os.rename(rb, os.path.join(D, "Rename Me.boxer"))
rb = os.path.join(D, "Rename Me.boxer")
boxnamed("Taken")
os.rename(os.path.join(D, "art-Taken.boxer"), os.path.join(D, "Taken.boxer"))
pr = sx.scratch("boxerren.hibr")
open(pr, "w").write(
    "%s. %s\n. %s/apps/boxerplay.hibr\n. %s/apps/Games/boxer.hibr\n"
    "dt_open\nBID := dt_launch boxerinfo \"%s\"\ndt_run\ndt_close\n" % (load("console", "img", RETRO), DESK, ROOT, ROOT, rb))
t = Term(pr, rows=40, cols=100, settle=1.0, env=ENVBASE)
t.collect(1.0)
check("the Game Settings window has the game's name in a field of its own", "Name" in t.screen().text() and "Rename Me" in t.screen().text(), t.screen())
t.send(b"\t")
t.send(b"\x7f" * 9 + b"Taken\r")
t.collect(0.8)
check("a name another game has is refused and nothing is renamed", os.path.isdir(rb) and "Taken" not in open(rb + "/boxer.json").read(), t.screen())
t.send(b"\x7f" * 9 + b"Brand New\r")
t.collect(0.8)
nb = os.path.join(D, "Brand New.boxer")
check("a new name changes the title and the folder together",
      os.path.isdir(nb) and not os.path.isdir(rb) and '"title": "Brand New"' in open(nb + "/boxer.json").read(), (os.listdir(D), t.screen()))
check("and the window is called by it", "Brand New Settings" in t.screen().text(), t.screen())
t.close()

# Box art: a cover is .cover.png in the box; one placed there wins, one beside the game is taken in, and, only when
# Control Panel > Boxer says so, one is fetched by the game's name from a server of covers (here a local one standing in).
import http.server, threading
art = os.path.join(D, "art")
os.makedirs(art)
png(art + "/Dungeon Keeper (1997).png", 8, 8, (200, 30, 30))
png(art + "/Leisure Suit Larry 2 - Goes looking for Love in Several Wrong Places (1988).png", 8, 8, (30, 200, 30))
png(art + "/7th Guest, The (1993).png", 8, 8, (30, 30, 200))
png(art + "/Prince of Persia (1990).png", 8, 8, (90, 90, 90))
open(art + "/Broken Game (1990).png", "wb").write(b"<html>not a png at all" * 20)
hits = []


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=art, **k)

    def log_message(self, *a):
        hits.append(self.path)


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = "http://127.0.0.1:%d/" % srv.server_address[1]
ENVBASE["BX_ART_URL"] = url


def lit(path):
    return open(path, "rb").read(8) == b"\x89PNG\r\n\x1a\n"


m = {}
for n in ("Dungeon Keeper", "Leisure Suit Larry 2", "The 7th Guest", "Prince of Persia 2", "Leisure Suit Larry", "Nothing Like This", "Broken Game", "LS"):
    b = boxnamed(n)
    out, err = imp("bc_fetch '%s'; echo \"st=$?\"" % b)
    m[n] = (out.strip().split("st=")[-1], lit(b + "/.cover.png") if os.path.exists(b + "/.cover.png") else None)
check("a cover is found by the game's name: the same name, with the year dropped",
      m["Dungeon Keeper"] == ("0", True), m)
check("a short name finds the longer title it starts: Larry 2 is the one with its subtitle", m["Leisure Suit Larry 2"] == ("0", True), m)
check("The 7th Guest is found as 7th Guest, The", m["The 7th Guest"] == ("0", True), m)
check("a name that is nobody's is not matched, nor is a too-short one, nor 2 taken for the first game, nor a series name for one of its games",
      m["Nothing Like This"][0] == "1" and m["LS"][0] == "1" and m["Prince of Persia 2"][0] == "1"
      and m["Leisure Suit Larry"][0] == "1", m)
check("what comes back that is not a PNG is refused and nothing is kept", m["Broken Game"] == ("2", None), m)

shutil.rmtree(D + "/cache", True)
hits.clear()
src = os.path.join(D, "artsrc", "Dungeon Keeper")
os.makedirs(src)
open(src + "/KEEPER.EXE", "wb").write(b"MZ" + bytes(62))
out, err = imp("b := bx_import '%s'; echo \"box=$b\"" % src)
bx_ = out.split("box=")[1].strip()
check("off by default: an import fetches nothing and asks the server for nothing", not os.path.exists(bx_ + "/.cover.png") and not hits, (hits, out, err))

shutil.rmtree(bx_, True)
out, err = imp("BX_ART=on; b := bx_import '%s'; echo \"box=$b\"" % src)
bx_ = out.split("box=")[1].strip()
check("on: an import gives the box its cover, fetched by name", os.path.exists(bx_ + "/.cover.png") and lit(bx_ + "/.cover.png"), (out, err))

shutil.rmtree(bx_, True)
png(src + "/cover.png", 4, 4, (1, 2, 3))
hits.clear()
out, err = imp("BX_ART=on; b := bx_import '%s'; echo \"box=$b\"" % src)
bx_ = out.split("box=")[1].strip()
check("a cover that came with the game is the one kept, and nothing is fetched for it",
      os.path.exists(bx_ + "/.cover.png") and open(bx_ + "/.cover.png", "rb").read() == open(src + "/cover.png", "rb").read() and not hits, (hits, out, err))

png(D + "/mine.png", 4, 4, (9, 9, 9))
out, err = imp("bc_set '%s' '%s'; echo st=$?" % (bx_, D + "/mine.png"))
check("a cover of the person's own is put in as .cover.png", open(bx_ + "/.cover.png", "rb").read() == open(D + "/mine.png", "rb").read(), (out, err))
open(D + "/mine.jpg", "wb").write(b"\xff\xd8\xff\xe0" + bytes(300))
out, err = imp("bc_set '%s' '%s'; echo st=$?" % (bx_, D + "/mine.jpg"))
check("a JPEG is turned away: a cover must be a PNG", "st=1" in out and "must be a PNG" in err, (out, err))
srv.shutdown()

shutil.rmtree(D, True)
# hibr's console notes a game's descriptor that went unread for a couple of seconds ("watched descriptor N has been ready
# for N ms with nothing reading it") when a test session starts or quits while the machine is busy; it is a timing note
# about a slow desktop, not a shell error. A game left idle in a window or in full screen does not make it (looked at
# directly), so it is not counted here.
sx.ERRS[:] = [e for e in sx.ERRS if not e.startswith("console: watched descriptor")]
import glob
for f in glob.glob("/tmp/hibr-boxer*-%d.hibr" % os.getpid()):
    os.remove(f)
report()
