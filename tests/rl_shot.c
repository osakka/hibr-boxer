#define _GNU_SOURCE

#include "rl.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/* With MOUSE=x,y,buttons in the environment, once the program has drawn, the pointer is put there (in the core's
   -32767..32767) for a moment before the shot is taken.
   Run a core on a game for a while and write its latest frame as a PPM: rl_shot core game sysdir savedir secs out.ppm [keycode]: with a keycode, that RETROK_ key is tapped
   once the program has drawn something, and the shot is taken two seconds later; secs is then the longest to wait for it. */

/* How many pixels of a frame are bright: a program that has drawn something. */
int rl_lit(const unsigned char *f, int w, int h)
{
	int i, n = 0;

	for (i = 0; i < w * h; i++)
		if (f[i * 3] > 128)
			n++;
	return n;
}

int main(int argc, char **argv)
{
	char *err = 0;
	const char *opts[] = { 0, 0 };
	rl *r;
	const unsigned char *f;
	int w, h;
	unsigned long seq;
	FILE *o;

	if (argc < 7) {
		fprintf(stderr, "usage: rl_shot core game sysdir savedir secs out.ppm\n");
		return 2;
	}
	opts[0] = getenv("OPT");
	r = rl_open(argv[1], argv[2], argv[3], argv[4], (const char *const *)opts, &err);
	if (!r) {
		fprintf(stderr, "open: %s\n", err ? err : "failed");
		return 1;
	}
	if (getenv("MOUSE")) {
		int i, mx = 0, my = 0, mb = 0, n = atoi(argv[5]) * 10;

		sscanf(getenv("MOUSE"), "%d,%d,%d", &mx, &my, &mb);
		for (i = 0; i < n; i++) {
			f = rl_lock(r, &w, &h, &seq);
			if (f && rl_lit(f, w, h) > 50)
				break;
			usleep(100000);
		}
		usleep(500000);
		rl_pointer(r, mx, my, mb, 0);
		if (getenv("MOUSETAP")) {
			rl_pointer(r, mx, my, 0, 0);
		} else {
			usleep(600000);
			if (mb)
				rl_pointer(r, mx, my, 0, 0);
		}
		usleep(600000);
	} else if (argc > 7) {
		int i, n = atoi(argv[5]) * 10;

		for (i = 0; i < n; i++) {
			f = rl_lock(r, &w, &h, &seq);
			if (f && rl_lit(f, w, h) > 50)
				break;
			usleep(100000);
		}
		usleep(500000);
		rl_key(r, (unsigned)atoi(argv[7]), 0, 0, 1);
		usleep(150000);
		rl_key(r, (unsigned)atoi(argv[7]), 0, 0, 0);
		sleep(2);
	} else
		sleep((unsigned)atoi(argv[5]));
	f = rl_lock(r, &w, &h, &seq);
	if (!f) {
		fprintf(stderr, "no frame\n");
		rl_close(r);
		return 1;
	}
	o = fopen(argv[6], "wb");
	if (!o) {
		rl_close(r);
		return 1;
	}
	fprintf(o, "P6\n%d %d\n255\n", w, h);
	fwrite(f, 3, (size_t)w * (size_t)h, o);
	fclose(o);
	printf("%dx%d seq %lu\n", w, h, seq);
	rl_close(r);
	return 0;
}
