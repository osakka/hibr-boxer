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
check(out.split()[0] == "1" and "already run" in err and "two=1,2" in out, "the same core twice is refused, a copy is not: %r" % out)
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
print("\n%d failed" % fails)
sys.exit(1 if fails else 0)
