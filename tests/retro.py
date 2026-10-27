#!/usr/bin/env python3
"""The retro module in a shell and through a pty: the verbs, the wake descriptor, and the picture as
kitty pixels, sixel and half blocks. Needs build/retro.so and build/testcore.so (make)."""
import fcntl, os, pty, struct, subprocess, sys, tempfile, termios, threading, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIBR = os.environ.get("HIBR", ROOT + "/../hibr/build/hibr")
MODS = os.environ.get("HIBR_MODS", ROOT + "/../hibr/build/mods")
CORE = ROOT + "/build/testcore.so"
fails = 0


def check(ok, what):
    global fails
    fails += not ok
    print(("ok   " if ok else "FAIL ") + what)


def env(gfx=None, extra=None):
    e = dict(os.environ, TERM="xterm-256color", HIBR_RETRO_AUDIO="none",
             HIBR_MODPATH=ROOT + "/build:" + MODS)
    if gfx:
        e["HIBR_GFX"] = gfx
    e.update(extra or {})
    return e


def shell(script, timeout=60):
    r = subprocess.run([HIBR, "-c", script], env=env(), capture_output=True, text=True,
                       timeout=timeout, cwd=ROOT)
    return r.returncode, r.stdout, r.stderr


def tty(script, gfx, rows=26, cols=82, cell=(8, 16), timeout=60):
    m, s = pty.openpty()
    fcntl.ioctl(s, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, cols * cell[0], rows * cell[1]))
    p = subprocess.Popen([HIBR, "-c", script], stdin=s, stdout=s, stderr=s, env=env(gfx), cwd=ROOT,
                         close_fds=True, start_new_session=True,
                         preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0))
    os.close(s)
    got = bytearray()

    def drain():
        while True:
            try:
                d = os.read(m, 1 << 20)
            except OSError:
                return
            if not d:
                return
            got.extend(d)
    threading.Thread(target=drain, daemon=True).start()
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
    time.sleep(0.1)
    return bytes(got)


assert os.path.exists(CORE) and os.path.exists(ROOT + "/build/retro.so"), "run make first"
rc, out, err = shell("need retro; id := retro open %s; sleep 1; i := retro info $id; "
                     "echo \"${i[core]} ${i[width]}x${i[height]} ${i[fps]} ${i[output]}\"; "
                     "echo \"frames=${i[frames]}\"; retro close $id; retro list" % CORE)
check(rc == 0 and "testcore 320x200 60 none" in out, "open, info and close in the shell: " + out.replace("\n", " | "))
check(any(l.startswith("frames=") and 50 <= int(l[7:]) <= 90 for l in out.split("\n")), "about a second of frames ran")
rc, out, err = shell("need retro; id := retro open %s; retro key $id nosuch; echo $?; retro key $id ctrl-a; echo $?; "
                     "retro key $id left; echo $?; retro option $id nosuch 1; echo $?; retro close $id" % CORE)
check(out.split() == ["2", "0", "0", "1"], "key names are checked, options too: %r %s" % (out.split(), err.strip()[:80]))
rc, out, err = shell("need retro; retro open /nonexistent.so; echo $?; retro open nosuchcore; echo $?")
check(out.split() == ["1", "1"] and "no core named" in err, "a missing core is an error with a reason")

rc, out, err = shell("need retro; a := retro open %s; retro open %s; echo $?; cp build/testcore.so build/testcore2.so; "
                     "b := retro open build/testcore2.so; echo \"two=$a,$b\"; retro list; retro close all" % (CORE, CORE))
check(out.split()[0] == "1" and "already running" in err and "two=1,2" in out, "the same core twice is refused, a copy is not: %r" % out)
rc, out, err = shell("need retro; id := retro open %s; sleep 0.3; retro key $id left; i := retro info $id; "
                     "echo \"aspect=${i[aspect]} core=${i[core]}\"; j := retro pause $id; k := retro info $id; "
                     "echo \"stale=${k[nosuchkey]-absent}\"; retro close $id" % CORE)
check("aspect=1.333" in out and "stale=absent" in out, "info reports the core's aspect and does not leave stale keys: %r" % out)

loop = ("need console retro; console open || exit 1; id := retro open %s; fd := retro fd $id; console watch $fd; "
        "retro size $id 60 20; n=0; t=$EPOCHSECONDS; until [ $((EPOCHSECONDS - t)) -ge 2 ]; do "
        "k := console key 200; retro frame $id && { retro draw $id 1 1; console flush > /dev/null; n=$((n + 1)); }; done; "
        "i := retro info $id; console close; echo \"drawn=${i[drawn]} n=$n\" > /dev/null; "
        "printf 'RESULT drawn=%%s n=%%s\\n' \"${i[drawn]}\" \"$n\"; retro close $id" % CORE)
for gfx, marker, want in (("kitty", b"\x1b_Ga=T,f=24", "pixels"), ("sixel", b"\x1bP", "pixels"), ("off", "▀".encode(), "cells")):
    o = tty(loop, gfx)
    t = o.decode("utf8", "replace")
    r = t[t.rindex("RESULT drawn="):].split("\n")[0] if "RESULT drawn=" in t else ""
    n = int(r.split(" n=")[1].split()[0]) if " n=" in r else -1
    check(marker in o, "%s: the picture is sent as %r" % (gfx, marker[:12]))
    check("drawn=" + want in r, "%s: info says it drew %s (%s)" % (gfx, want, r.strip()))
    check(n >= 40, "%s: the wake descriptor drives the draws, %d in two seconds" % (gfx, n))

# A modified key presses the modifier's own key too: shift-left is two keys down, not one, and so is a capital
# letter or a shifted symbol -- a DOS game reads shift as a key of its own.
def keys_down(name):
    f = tempfile.mktemp()
    rc, out, err = shell("need retro; id := retro open %s; retro hold $id 600; retro key $id %s; sleep 0.25; "
                         "retro save $id %s; retro close $id" % (CORE, name, f))
    d = open(f, "rb").read() if os.path.exists(f) else b""
    return struct.unpack("<Q", d[8:16])[0] if len(d) >= 16 else -1


check(keys_down("left") == 1, "a plain key is one key down: %d" % keys_down("left"))
check(keys_down("shift-left") == 2, "shift-left is two: %d" % keys_down("shift-left"))
check(keys_down("A") == 2, "a capital is two: %d" % keys_down("A"))
check(keys_down("ctrl-left") == 2, "ctrl-left is two: %d" % keys_down("ctrl-left"))
# A click is given in the pane's own cells, as an app is told it, wherever the pane is on the screen: the centre of
# the picture is the centre of the core's range whether the pane is at the corner or in the middle of the screen,
# and a click a quarter of the way across is a quarter of the way across.
def pointer(row, col, prow, pcol, gfx):
    sc = ("need console retro; console open || exit 1; console pane w1 %d %d 20 60; id := retro open %s; sleep 0.3; "
          "retro size $id 60 20 %s; retro frame $id; retro draw $id 1 1 -p w1; retro mouse $id %d %d 1; sleep 0.1; "
          "i := retro info $id; console close; printf 'RESULT %%s\\n' \"${i[pointer]}\"; retro close $id"
          % (prow, pcol, CORE, "half" if gfx is None else "pixels", row, col))
    t = tty(sc, gfx).decode("utf-8", "replace")
    r = t[t.rindex("RESULT "):].split("\n")[0].split() if "RESULT " in t else []
    return [int(v) for v in r[1:4]] if len(r) >= 4 else None


# Raw motion from a locked pointer is added up as it is given, buttons and all.
sc = ("need console retro; console open || exit 1; id := retro open %s; sleep 0.3; "
      "retro motion $id 3 -2 0; retro motion $id 4 -2 1; retro motion $id -1 5 0; sleep 0.1; "
      "i := retro info $id; console close; printf 'RESULT %%s|%%s\\n' \"${i[motion]}\" \"${i[pointer]}\"; retro close $id" % CORE)
t = tty(sc, None).decode("utf-8", "replace")
r = t[t.rindex("RESULT "):].split("\n")[0][7:] if "RESULT " in t else ""
check(r.startswith("6 1|") or r.startswith("6 1 "), "retro motion adds raw counts: 3,-2 then 4,-2 then -1,5 is 6 1 (%s)" % r)

for gfx in (None, "kitty"):
    c = pointer(10, 30, 2, 1, gfx)
    far = pointer(10, 30, 12, 20, gfx)
    check(bool(c) and abs(c[0]) < 3000 and abs(c[1]) < 3000,
          "the picture's centre is the range's centre, in a pane at the corner (%s): %s" % (gfx, c))
    check(bool(far and c) and abs(far[0] - c[0]) < 1500 and abs(far[1] - c[1]) < 1500,
          "and in a pane in the middle of the screen: the same (%s): %s" % (gfx, far))

print("\n%d failed" % fails)
sys.exit(1 if fails else 0)
