#define _GNU_SOURCE

#include "rl.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

/* Run a core on a game for a while and write its latest frame as a PPM: rl_shot core game sysdir savedir secs out.ppm [keycode]: with a keycode, that RETROK_ key is tapped
   halfway. */

int main(int argc, char **argv)
{
	char *err = 0;
	const char *const opts[] = { 0 };
	rl *r;
	const unsigned char *f;
	int w, h;
	unsigned long seq;
	FILE *o;

	if (argc < 7) {
		fprintf(stderr, "usage: rl_shot core game sysdir savedir secs out.ppm\n");
		return 2;
	}
	r = rl_open(argv[1], argv[2], argv[3], argv[4], opts, &err);
	if (!r) {
		fprintf(stderr, "open: %s\n", err ? err : "failed");
		return 1;
	}
	if (argc > 7) {
		sleep((unsigned)atoi(argv[5]) / 2);
		rl_key(r, (unsigned)atoi(argv[7]), 0, 0, 1);
		usleep(150000);
		rl_key(r, (unsigned)atoi(argv[7]), 0, 0, 0);
		sleep((unsigned)atoi(argv[5]) - (unsigned)atoi(argv[5]) / 2);
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
