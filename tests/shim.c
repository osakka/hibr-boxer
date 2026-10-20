#define _GNU_SOURCE

#include "hibr.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int hibr_lv = HIBR_LINF;

/* The shell's allocator and logger, as plain libc, so the driver runs with no shell. */
void *xm(size_t n)
{
	void *p = malloc(n ? n : 1);

	if (!p)
		exit(70);
	return p;
}

void *xr(void *p, size_t n)
{
	void *q = realloc(p, n ? n : 1);

	if (!q)
		exit(70);
	return q;
}

char *xs(const char *s)
{
	char *p = strdup(s);

	if (!p)
		exit(70);
	return p;
}

void lg(int lv, const char *f, ...)
{
	va_list ap;

	if (lv > hibr_lv)
		return;
	va_start(ap, f);
	fputs("hibr: ", stderr);
	vfprintf(stderr, f, ap);
	fputc('\n', stderr);
	va_end(ap);
}
