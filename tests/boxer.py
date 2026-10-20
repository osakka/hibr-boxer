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
    b = os.path.join(D, name + ".gamebox")
    shutil.rmtree(b, True)
    os.makedirs(b + "/engine")
    os.makedirs(b + "/drives/c/GAME")
    open(b + "/drives/c/GAME/RUN.EXE", "w").write("x")
    open(b + "/engine/dosbox.conf", "w").write("[cpu]\ncycles=max\n")
    open(b + "/gamebox.json", "w").write(
        '{"gamebox":1,"title":"%s","engine":"dosbox",'
        '"launch":{"program":"C:\\\\GAME\\\\RUN.EXE","args":"-fast"},'
        '"mounts":[{"drive":"d","kind":"cdrom","path":"drives/d/game.cue"}],'
        '"display":{"aspect":"4:3"}}' % name)
    return b


def desk(body, box, pix=False):
    p = sx.scratch("boxer.hibr")
    open(p, "w").write(
        "%s. %s\n. %s/apps/boxerplay.hibr\n"
        "dt_open\nBID := dt_launch boxerplay \"%s\"\n%s\ndt_run\ndt_close\n"
        % (load("console", RETRO), DESK, ROOT, box, body))
    kw = dict(cellw=8, cellh=16, caps=["kitty"]) if pix else {}
    return Term(p, rows=26, cols=82, settle=1.0, env=ENVBASE, **kw)


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

shutil.rmtree(D, True)
report()
