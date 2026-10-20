#ifndef HIBR_RA_H
#define HIBR_RA_H

#include "hibr.h"
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>

/* Where audio goes: a sound device, or nowhere at the pace of one. */
typedef struct ra_ao ra_ao;
struct ra_ao {
	const char *name;
	int rate, ch;
	void *h;
	void *st;
	int (*open)(ra_ao *, int rate, int ch);
	int (*write)(ra_ao *, const int16_t *, int frames);
	double (*delay)(ra_ao *);
	void (*flush)(ra_ao *);
	void (*close)(ra_ao *);
};

/* Seconds on a clock that only goes forward. */
double ra_now(void);

/* Open somewhere for sound to go; on failure plays silently and says why. */
int ra_audio(ra_ao *a, int rate, int ch, char **why);

#endif
