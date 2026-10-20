#define _GNU_SOURCE

#include "rl.h"
#include "libretro.h"
#include <dlfcn.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int fails, checks;

/* Say whether one thing held. */
void ck(int ok, const char *what)
{
	checks++;
	if (!ok)
		fails++;
	printf("%s  %s\n", ok ? "ok  " : "FAIL", what);
}

/* Sleep ms milliseconds. */
void nap(int ms)
{
	usleep((useconds_t)ms * 1000);
}

/* The pixel at x, y of the latest frame, or -1 when there is none. */
int pix(rl *r, int x, int y, int *rr, int *gg, int *bb)
{
	int w, h;
	unsigned long seq;
	const unsigned char *f = rl_lock(r, &w, &h, &seq);
	int ok = f && x < w && y < h;

	if (ok) {
		*rr = f[((size_t)y * w + x) * 3];
		*gg = f[((size_t)y * w + x) * 3 + 1];
		*bb = f[((size_t)y * w + x) * 3 + 2];
	}
	rl_unlock(r);
	return ok ? 0 : -1;
}

/* Within a few counts of what was expected, which a 565 or 1555 pixel is. */
int near3(int a, int b, int c, int x, int y, int z)
{
	return abs(a - x) <= 8 && abs(b - y) <= 8 && abs(c - z) <= 8;
}

int main(int ac, char **av)
{
	char *err = 0;
	const char *core = ac > 1 ? av[1] : "build/testcore.so";
	const char *fmt = ac > 2 ? av[2] : "xrgb8888";
	char opt[64];
	const char *opts[2];
	rl *r;
	rl_st st;
	int cr, cg, cb, w, h;
	unsigned long seq, s1, s2;
	unsigned long *tn;
	unsigned *ud, *uu;
	void *dl;
	size_t n = 0;
	unsigned char *sv;
	const unsigned char *f;

	snprintf(opt, sizeof opt, "testcore_format=%s", fmt);
	opts[0] = opt;
	opts[1] = 0;
	r = rl_open(core, 0, "/tmp", "/tmp", opts, &err);
	ck(r != 0, "the core opens");
	if (!r) {
		printf("  %s\n", err ? err : "?");
		return 1;
	}
	dl = dlopen(core, RTLD_NOW | RTLD_NOLOAD);
	tn = dl ? dlsym(dl, "tc_n") : 0;
	ud = dl ? dlsym(dl, "tc_keydown_evs") : 0;
	uu = dl ? dlsym(dl, "tc_keyup_evs") : 0;
	ck(tn && ud && uu, "the test core's counters can be reached");
	nap(1200);
	rl_info(r, &st);
	ck(st.name && !strcmp(st.name, "testcore"), "it says what it is");
	ck(st.frames >= 55 && st.frames <= 90, "it runs at about 60 frames a second, paced by its sound");
	printf("      frames after 1.2 s: %lu\n", st.frames);
	ck(st.w == 320 && st.h == 200, "the first frame is 320x200");
	ck(st.fps == 60 && st.rate == 44100, "av info: 60 fps, 44100 Hz");
	rl_stfree(&st);
	ck(pix(r, 0, 0, &cr, &cg, &cb) == 0 && near3(cr, cg, cb, 0, 0, 96), "the top left pixel converts to RGB");
	ck(pix(r, 319, 199, &cr, &cg, &cb) == 0 && near3(cr, cg, cb, 254, 254, 96), "so does the bottom right");
	rl_wake(r);
	nap(100);
	ck(read(rl_fd(r), &cr, 1) == 1, "the wake descriptor is readable once frames arrive");
	rl_wake(r);
	nap(1000);
	rl_info(r, &st);
	ck(st.h == 240, "the geometry changes to 320x240 mid-run and the frame follows");
	rl_stfree(&st);
	ck(pix(r, 5, 239, &cr, &cg, &cb) == 0, "and the new rows can be read");
	rl_hold(r, RETROK_LEFT, 0, 0, 200);
	nap(80);
	ck(pix(r, 6, 18, &cr, &cg, &cb) == 0 && near3(cr, cg, cb, 0, 255, 0), "a held key is seen by the core");
	nap(350);
	ck(pix(r, 6, 18, &cr, &cg, &cb) == 0 && !near3(cr, cg, cb, 0, 255, 0), "and let go of when it stops repeating");
	ck(ud && uu && *ud == 1 && *uu == 1, "the core's keyboard callback saw one down and one up");
	rl_hold(r, RETROK_LEFT, 0, 0, 200);
	nap(120);
	rl_hold(r, RETROK_LEFT, 0, 0, 200);
	nap(120);
	rl_hold(r, RETROK_LEFT, 0, 0, 200);
	nap(120);
	ck(ud && *ud == 2, "repeats refresh the hold and are not new presses");
	rl_key(r, RETROK_LEFT, 0, 0, 0);
	nap(60);
	ck(pix(r, 6, 18, &cr, &cg, &cb) == 0 && !near3(cr, cg, cb, 0, 255, 0), "an explicit release lets go at once");
	rl_pointer(r, 0, 0, 1, 0);
	nap(80);
	ck(pix(r, 22, 18, &cr, &cg, &cb) == 0 && near3(cr, cg, cb, 0, 128, 255), "a pressed pointer is seen");
	rl_pointer(r, 0, 0, 0, 0);
	nap(60);
	ck(pix(r, 22, 18, &cr, &cg, &cb) == 0 && !near3(cr, cg, cb, 0, 128, 255), "and so is its release");
	ck(rl_option(r, "testcore_tone", "880") == 0, "a core option can be set");
	ck(rl_option(r, "no_such_option", "x") == -1, "an unknown one is refused");
	sv = rl_save(r, &n);
	ck(sv && n == sizeof(unsigned long), "state is saved");
	nap(300);
	ck(rl_load(r, sv, n) == 0, "and put back");
	ck(tn && (long)(*tn - *(unsigned long *)sv) < 6, "the core is where it was");
	free(sv);
	ck(rl_pause(r, 1) == 0, "pause");
	nap(100);
	rl_info(r, &st);
	s1 = st.frames;
	rl_stfree(&st);
	nap(300);
	rl_info(r, &st);
	s2 = st.frames;
	rl_stfree(&st);
	ck(s1 == s2, "no frames while paused");
	ck(rl_pause(r, 0) == 0, "resume");
	nap(200);
	rl_info(r, &st);
	ck(st.frames > s2, "frames again after");
	rl_stfree(&st);
	ck(rl_reset(r) == 0, "reset");
	rl_info(r, &st);
	ck(fabs(st.aspect - 4.0 / 3) < 0.01, "the core's own aspect ratio is kept");
	rl_stfree(&st);
	f = rl_lock(r, &w, &h, &seq);
	rl_info(r, &st);
	s1 = st.frames;
	rl_stfree(&st);
	nap(250);
	rl_info(r, &st);
	ck(f && st.frames - s1 >= 8, "holding a frame to draw it does not stall the core");
	printf("      frames during a 250 ms hold: %lu\n", st.frames - s1);
	rl_stfree(&st);
	rl_unlock(r);
	{
		rl *r2;
		void *d2;
		unsigned long *tn2, a1, a2;

		r2 = rl_open(core, 0, 0, 0, 0, &err);
		ck(!r2 && err && strstr(err, "already run"), "the same core file is refused twice");
		free(err);
		err = 0;
		ck(system("cp build/testcore.so build/testcore2.so") == 0, "a copy of the core file");
		r2 = rl_open("build/testcore2.so", 0, 0, 0, 0, &err);
		ck(r2 != 0, "is a core of its own and opens beside the first");
		if (r2) {
			d2 = dlopen("build/testcore2.so", RTLD_NOW | RTLD_NOLOAD);
			tn2 = d2 ? dlsym(d2, "tc_n") : 0;
			ck(tn2 && tn2 != tn, "with globals of its own");
			a1 = tn2 ? *tn2 : 0;
			nap(300);
			a2 = tn2 ? *tn2 : 0;
			ck(a2 - a1 >= 10, "and both run at once");
			ck(rl_reset(r2) == 0 && tn2 && *tn2 < a2 && *tn > 30, "resetting one leaves the other alone");
			rl_close(r2);
			ck(1, "the second closes and the first goes on");
		}
	}
	rl_close(r);
	ck(1, "closed with no crash");
	r = rl_open("/nonexistent/core.so", 0, 0, 0, 0, &err);
	ck(!r && err, "a missing core is refused with a reason");
	printf("      %s\n", err ? err : "");
	free(err);
	printf("\n%d checks, %d failed\n", checks, fails);
	return fails != 0;
}
