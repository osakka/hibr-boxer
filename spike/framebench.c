#define _GNU_SOURCE

#include "hibr.h"
#include "display.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Monotonic time in milliseconds. */
static double fb_now(void)
{
	struct timespec t;

	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1000.0 + t.tv_nsec / 1e6;
}

/* Order two doubles for qsort. */
static int fb_cmp(const void *a, const void *b)
{
	double x = *(const double *)a, y = *(const double *)b;

	return x < y ? -1 : x > y;
}

/* One synthetic 320x200-style frame: busy cycles every pixel, calm moves a strip and sprites. */
static void fb_scene(unsigned char *p, int w, int h, int t, int busy)
{
	int x, y, k;
	unsigned char *q;

	for (y = 0; y < h; y++)
		for (x = 0; x < w; x++) {
			int v = (y * 255 / h + (busy ? t * 5 : 0)) & 255;
			int d = ((x ^ y) & 1) * 8;

			q = p + ((size_t)y * w + x) * 3;
			q[0] = (unsigned char)(v / 2 + d);
			q[1] = (unsigned char)(255 - v + d);
			q[2] = (unsigned char)(64 + v / 3);
			if (y > h * 2 / 3 && (((x + t * 3) / 16) & 1)) {
				q[0] = 200;
				q[1] = 160;
				q[2] = 40;
			}
		}
	for (k = 0; k < 3; k++) {
		int sx = (t * (2 + k) + k * 90) % (w - 24), sy = 20 + k * 40;

		for (y = 0; y < 16; y++)
			for (x = 0; x < 24; x++) {
				q = p + ((size_t)(sy + y) * w + sx + x) * 3;
				q[0] = (unsigned char)(255 - k * 60);
				q[1] = (unsigned char)(k * 90);
				q[2] = 255;
			}
	}
}

/* Draw a frame as half-block cells, nearest-sampled, the pen set per cell. */
static void fb_half(const dp_api *dp, const unsigned char *f, int w, int h,
		    int rows, int cols)
{
	int r, c;

	for (r = 0; r < rows; r++)
		for (c = 0; c < cols; c++) {
			const unsigned char *a = f + ((size_t)(r * 2 * h / (rows * 2)) * w + c * w / cols) * 3;
			const unsigned char *b = f + ((size_t)((r * 2 + 1) * h / (rows * 2)) * w + c * w / cols) * 3;

			dp->pen(DP_RGB | (unsigned)a[0] << 16 | (unsigned)a[1] << 8 | a[2],
				DP_RGB | (unsigned)b[0] << 16 | (unsigned)b[1] << 8 | b[2], 0);
			dp->put(r, c, "\xe2\x96\x80");
		}
}

/* framebench MODE SCENE W H ROWS COLS N OUTFILE: time N frames through the display. */
int m_framebench(sh *s, int ac, char **av)
{
	const dp_api *dp;
	int w, h, rows, cols, n, i, half, busy, cw = 0, ch = 0, ok = 0;
	unsigned char *f;
	double *ms, t0, t1, tot = 0, bytes = 0, T0;
	FILE *o;

	if (ac < 9) {
		lg(HIBR_LERR, "usage: framebench pixels|half busy|calm W H ROWS COLS N OUTFILE");
		return 2;
	}
	half = !strcmp(av[1], "half");
	busy = !strcmp(av[2], "busy");
	w = atoi(av[3]);
	h = atoi(av[4]);
	rows = atoi(av[5]);
	cols = atoi(av[6]);
	n = atoi(av[7]);
	dp = (const dp_api *)hibr_require(s, "display", DP_API_VER);
	if (!dp || !dp->isopen()) {
		lg(HIBR_LERR, "framebench: no display open");
		return HIBR_FAIL;
	}
	if (dp->cellpx)
		dp->cellpx(&cw, &ch);
	f = malloc((size_t)w * h * 3);
	ms = malloc(sizeof *ms * (size_t)n);
	dp->flush();
	T0 = fb_now();
	for (i = 0; i < n; i++) {
		fb_scene(f, w, h, i, busy);
		t0 = fb_now();
		if (half) {
			fb_half(dp, f, w, h, rows, cols);
			ok = 1;
		} else {
			ok = dp->image(s, 0, 0, 0, rows, cols, f, w, h, 0);
		}
		bytes += (double)dp->flush();
		t1 = fb_now();
		ms[i] = t1 - t0;
		tot += ms[i];
	}
	t1 = fb_now() - T0;
	qsort(ms, (size_t)n, sizeof *ms, fb_cmp);
	o = fopen(av[8], "w");
	if (o) {
		fprintf(o, "{\"mode\":\"%s\",\"scene\":\"%s\",\"src\":\"%dx%d\",\"cells\":\"%dx%d\","
			   "\"cellpx\":\"%dx%d\",\"accepted\":%d,\"frames\":%d,"
			   "\"mean_ms\":%.3f,\"p50_ms\":%.3f,\"p95_ms\":%.3f,\"max_ms\":%.3f,"
			   "\"kB_per_frame\":%.1f,\"wall_fps\":%.1f,\"cost_fps\":%.1f}\n",
			av[1], av[2], w, h, cols, rows, cw, ch, ok, n,
			tot / n, ms[n / 2], ms[n * 95 / 100], ms[n - 1],
			bytes / n / 1024.0, n * 1000.0 / t1, n * 1000.0 / tot);
		fclose(o);
	}
	free(f);
	free(ms);
	return HIBR_OK;
}

const hibr_bi framebench_bi[] = { { "framebench", m_framebench, "time synthetic frames through the display" }, HIBR_BI_END };
HIBR_MODULE("framebench", "0.1", "frame-rate spike for hibr-retro-gaming", framebench_bi, 0, 0);
