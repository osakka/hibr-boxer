#!/usr/bin/env python3
"""Frame-rate spike: synthetic native-size frames through hibr's display, into a pty
that is drained as fast as it will go. Measures the producer side only: encoding,
bytes, and the pty's own throughput. It does not measure a terminal painting them."""
import fcntl, json, os, pty, struct, subprocess, sys, tempfile, termios, threading, time

HIBR = os.environ.get("HIBR", "/home/osakka/hibr/build/hibr")
MODS = os.environ.get("HIBR_MODS", "/home/osakka/hibr/build/mods")
HERE = os.path.dirname(os.path.abspath(__file__))
CELL = (8, 16)

def run(gfx, mode, scene, w, h, rows, cols, n):
    out = tempfile.mktemp(prefix="fb-", suffix=".json")
    m, s = pty.openpty()
    fcntl.ioctl(s, termios.TIOCSWINSZ, struct.pack("HHHH", rows + 2, cols + 2, (cols + 2) * CELL[0], (rows + 2) * CELL[1]))
    env = dict(os.environ, TERM="xterm-256color", HIBR_GFX=gfx, HIBR_MODPATH=HERE + "/../build:" + MODS)
    script = "need console framebench; console open || exit 1; framebench %s %s %d %d %d %d %d %s; console close" % (mode, scene, w, h, rows, cols, n, out)
    p = subprocess.Popen([HIBR, "-c", script], stdin=s, stdout=s, stderr=s, env=env, close_fds=True, start_new_session=True,
                         preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0))
    os.close(s)
    got = [0]
    def drain():
        while True:
            try:
                d = os.read(m, 1 << 20)
            except OSError:
                return
            if not d:
                return
            got[0] += len(d)
    t = threading.Thread(target=drain, daemon=True); t.start()
    try:
        p.wait(timeout=300)
    except subprocess.TimeoutExpired:
        p.kill(); return {"error": "timeout"}
    time.sleep(0.1)
    try:
        r = json.load(open(out)); os.unlink(out)
    except Exception as e:
        return {"error": "no result: %s" % e}
    r["pty_kB_per_frame"] = round(got[0] / 1024.0 / n, 1)
    return r

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    w, h = 320, 200
    for rows, cols in ((25, 80), (40, 120)):
        for gfx, mode in (("kitty", "pixels"), ("sixel", "pixels"), ("off", "half")):
            for scene in ("calm", "busy"):
                r = run(gfx, mode, scene, w, h, rows, cols, n)
                print(gfx.ljust(6), json.dumps(r), flush=True)
