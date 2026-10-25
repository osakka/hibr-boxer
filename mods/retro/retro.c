#define _GNU_SOURCE

#include "hibr.h"
#include "display.h"
#include "libretro.h"
#include "rl.h"
#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* One running core, as the shell sees it: the driver, and how it is drawn. */
typedef struct rt_pl rt_pl;
struct rt_pl {
	int id;
	rl *r;
	int cols, rows, mode, hold, drew;
	double aspect;
	unsigned long drawn;
	int orow, ocol, tw, th, pr, pc;
};

vec rt_pls;
int rt_nextid;
const dp_api *rt_dp;

/* The module's answer: into the result slot, and printed unless := is catching it. */
void rt_say(sh *s, const char *t)
{
	hibr_ret(s, t);
	if (!s->bind)
		printf("%s\n", t);
}

/* A number, said. */
void rt_saynum(sh *s, long n)
{
	str b;

	s_init(&b);
	s_num(&b, n);
	rt_say(s, b.p);
	s_free(&b);
}

/* A player by its number, saying so when there is none. */
rt_pl *rt_get(const char *id)
{
	size_t i;
	int n = atoi(id);

	for (i = 0; i < rt_pls.n; i++)
		if (((rt_pl *)rt_pls.p[i])->id == n)
			return rt_pls.p[i];
	lg(HIBR_LERR, "retro: no player %s", id);
	return 0;
}

/* Close a player and forget it. */
void rt_forget(rt_pl *p)
{
	size_t i;

	for (i = 0; i < rt_pls.n; i++) {
		if (rt_pls.p[i] != p)
			continue;
		memmove(rt_pls.p + i, rt_pls.p + i + 1, (rt_pls.n - i - 1) * sizeof *rt_pls.p);
		rt_pls.n--;
		break;
	}
	rl_close(p->r);
	free(p);
}

/* Set one field of the info map, or print it as name, tab, value. */
void rt_field(sh *s, const char *k, const char *v)
{
	char *ks[1];

	if (s->bind) {
		ks[0] = (char *)k;
		hibr_setp(s, "RET", ks, 1, v ? v : "");
	} else {
		printf("%s\t%s\n", k, v ? v : "");
	}
}

/* One number of the info map. */
void rt_fieldn(sh *s, const char *k, double v)
{
	char *t = xm(64);

	if (v == (long)v)
		snprintf(t, 64, "%ld", (long)v);
	else
		snprintf(t, 64, "%.3f", v);
	rt_field(s, k, t);
	free(t);
}

/* A core's path from its name: the folders cores live in, searched in order. */
char *rt_corepath(const char *nm)
{
	const char *env = getenv("HIBR_RETRO_CORES"), *xd = getenv("XDG_DATA_HOME"), *home = getenv("HOME");
	str dirs, cand;
	char *r = 0, *d, *save, *list;
	static const char *const suf[] = { "_libretro.so", ".so", 0 };
	int i;

	if (strchr(nm, '/'))
		return xs(nm);
	s_init(&dirs);
	if (env) {
		s_cat(&dirs, env);
		s_ch(&dirs, ':');
	}
	if (xd && *xd) {
		s_cat(&dirs, xd);
		s_cat(&dirs, "/hibr/retro/cores:");
	} else if (home) {
		s_cat(&dirs, home);
		s_cat(&dirs, "/.local/share/hibr/retro/cores:");
	}
	s_cat(&dirs, "/usr/local/lib/hibr/cores:/usr/lib/hibr/cores");
	list = xs(dirs.p);
	s_free(&dirs);
	for (d = strtok_r(list, ":", &save); d && !r; d = strtok_r(0, ":", &save))
		for (i = 0; suf[i] && !r; i++) {
			s_init(&cand);
			s_cat(&cand, d);
			s_ch(&cand, '/');
			s_cat(&cand, nm);
			s_cat(&cand, suf[i]);
			if (access(cand.p, R_OK) == 0)
				r = xs(cand.p);
			s_free(&cand);
		}
	free(list);
	return r;
}

/* The core's key code, character and modifiers for one of the console's key names. */
int rt_keymap(const char *name, unsigned *code, uint32_t *chr, unsigned *mods)
{
	static const struct { const char *n; unsigned c; } nm[] = {
		{ "up", RETROK_UP }, { "down", RETROK_DOWN }, { "left", RETROK_LEFT },
		{ "right", RETROK_RIGHT }, { "home", RETROK_HOME }, { "end", RETROK_END },
		{ "pageup", RETROK_PAGEUP }, { "pagedown", RETROK_PAGEDOWN },
		{ "insert", RETROK_INSERT }, { "delete", RETROK_DELETE }, { "tab", RETROK_TAB },
		{ "shift-tab", RETROK_TAB }, { "enter", RETROK_RETURN },
		{ "backspace", RETROK_BACKSPACE }, { "escape", RETROK_ESCAPE },
		{ "space", RETROK_SPACE }, { 0, 0 }
	};
	static const char *const shifted = "!@#$%^&*()_+{}|:\"<>?~";
	static const char *const base = "1234567890-=[]\\;',./`";
	const unsigned char *t;
	int i;

	*code = RETROK_UNKNOWN;
	*chr = 0;
	*mods = 0;
	for (;;) {
		if (!strncmp(name, "ctrl-", 5) && name[5]) {
			*mods |= RETROKMOD_CTRL;
			name += 5;
		} else if (!strncmp(name, "alt-", 4) && name[4]) {
			*mods |= RETROKMOD_ALT;
			name += 4;
		} else if (!strncmp(name, "shift-", 6) && name[6] && strcmp(name, "shift-tab")) {
			*mods |= RETROKMOD_SHIFT;
			name += 6;
		} else {
			break;
		}
	}
	if (!strcmp(name, "shift-tab"))
		*mods |= RETROKMOD_SHIFT;
	for (i = 0; nm[i].n; i++)
		if (!strcmp(name, nm[i].n)) {
			*code = nm[i].c;
			if (*code == RETROK_SPACE)
				*chr = ' ';
			return 0;
		}
	if (name[0] == 'f' && isdigit((unsigned char)name[1])) {
		char *e;
		long k = strtol(name + 1, &e, 10);

		if (!*e && k >= 1 && k <= 12) {
			*code = RETROK_F1 + (unsigned)k - 1;
			return 0;
		}
	}
	t = (const unsigned char *)name;
	if (!t[0])
		return -1;
	if (t[0] < 0x80 && !t[1]) {
		const char *p;

		if (t[0] == ' ') {
			*code = RETROK_SPACE;
			*chr = ' ';
			return 0;
		}
		if (isupper(t[0])) {
			*code = (unsigned)tolower(t[0]);
			*chr = t[0];
			*mods |= RETROKMOD_SHIFT;
			return 0;
		}
		if (isalnum(t[0])) {
			*code = t[0];
			*chr = (*mods & RETROKMOD_CTRL) ? 0 : t[0];
			return 0;
		}
		p = strchr(shifted, t[0]);
		if (p) {
			*code = (unsigned char)base[p - shifted];
			*chr = t[0];
			*mods |= RETROKMOD_SHIFT;
			return 0;
		}
		*code = t[0];
		*chr = t[0];
		return 0;
	}
	if (t[0] >= 0xc0) {
		uint32_t c = t[0] >= 0xf0 ? t[0] & 7 : t[0] >= 0xe0 ? t[0] & 15 : t[0] & 31;
		int k = t[0] >= 0xf0 ? 3 : t[0] >= 0xe0 ? 2 : 1;

		for (i = 1; i <= k && t[i]; i++)
			c = c << 6 | (t[i] & 63);
		*chr = c;
		return 0;
	}
	return -1;
}

/* The rectangle of cells a frame fills inside the rows and columns it was given, its shape kept. */
void rt_fit(rt_pl *p, double core, int w, int h, int cw, int ch, int *tw, int *th)
{
	double a = p->aspect > 0 ? p->aspect : core > 0 ? core : (h > 0 ? (double)w / h : 4.0 / 3);
	double pw = (double)p->cols * cw, ph = (double)p->rows * ch, fw, fh;

	if (pw / ph > a) {
		fh = ph;
		fw = ph * a;
	} else {
		fw = pw;
		fh = pw / a;
	}
	*tw = (int)(fw / cw + 0.5);
	*th = (int)(fh / ch + 0.5);
	if (*tw < 1)
		*tw = 1;
	if (*th < 1)
		*th = 1;
	if (*tw > p->cols)
		*tw = p->cols;
	if (*th > p->rows)
		*th = p->rows;
}

/* Draw a frame as half blocks, sampled to the cells: the pen is set per cell, only inside the clip. */
void rt_half(const dp_api *dp, const unsigned char *f, int w, int h, int row, int col, int th, int tw,
	     int prow, int pcol, int ph, int pw)
{
	int r, c;

	for (r = 0; r < th; r++) {
		int sr = row + r;

		if (sr < prow || sr >= prow + ph)
			continue;
		for (c = 0; c < tw; c++) {
			int sc = col + c;
			const unsigned char *a, *b;

			if (sc < pcol || sc >= pcol + pw)
				continue;
			a = f + ((size_t)(r * 2 * h / (th * 2)) * w + (size_t)c * w / tw) * 3;
			b = f + ((size_t)((r * 2 + 1) * h / (th * 2)) * w + (size_t)c * w / tw) * 3;
			dp->pen(DP_RGB | (unsigned)a[0] << 16 | (unsigned)a[1] << 8 | a[2],
				DP_RGB | (unsigned)b[0] << 16 | (unsigned)b[1] << 8 | b[2], 0);
			dp->put(sr, sc, "\xe2\x96\x80");
		}
	}
}

/* retro draw ID ROW COL [-p PANE]: the latest frame, in the rectangle, as pixels where they can be had. */
int rt_draw(sh *s, rt_pl *p, int ac, char **av)
{
	const char *pane = 0;
	int i, n = 0, v[2] = { 0, 0 }, prow = 0, pcol = 0, ph = 0, pw = 0, cw = 0, ch = 0, w, h, tw, th;
	int row, col, drew = 0;
	unsigned long seq;
	const unsigned char *f;
	rl_st st;

	for (i = 3; i < ac; i++) {
		if (!strcmp(av[i], "-p") && i + 1 < ac) {
			pane = av[++i];
			continue;
		}
		if (n < 2)
			v[n++] = atoi(av[i]);
	}
	if (n < 2) {
		lg(HIBR_LERR, "usage: retro draw id row col [-p pane]");
		return 2;
	}
	if (!rt_dp)
		rt_dp = (const dp_api *)hibr_require(s, "display", DP_API_VER);
	if (!rt_dp || !rt_dp->isopen()) {
		lg(HIBR_LERR, "retro draw: no display open");
		return HIBR_FAIL;
	}
	if (rt_dp->cellpx)
		rt_dp->cellpx(&cw, &ch);
	if (pane) {
		if (!rt_dp->prect || !rt_dp->prect(pane, &prow, &pcol, &ph, &pw)) {
			lg(HIBR_LERR, "retro draw: no such pane: %s", pane);
			return HIBR_FAIL;
		}
		v[0] += prow;
		v[1] += pcol;
	} else {
		rt_dp->size(&ph, &pw);
	}
	rl_info(p->r, &st);
	rl_stfree(&st);
	f = rl_lock(p->r, &w, &h, &seq);
	if (!f) {
		rl_unlock(p->r);
		return HIBR_FAIL;
	}
	rt_fit(p, st.aspect, w, h, cw > 1 && ch > 1 && p->mode == 0 ? cw : 1, cw > 1 && ch > 1 && p->mode == 0 ? ch : 2, &tw, &th);
	row = v[0] + (p->rows - th) / 2;
	col = v[1] + (p->cols - tw) / 2;
	rt_dp->pen(DP_RGB, DP_RGB, 0);
	rt_dp->fill(v[0], v[1], p->rows, p->cols, " ");
	if (p->mode == 0 && rt_dp->image && cw > 1 && ch > 1 &&
	    row >= prow && col >= pcol && row + th <= prow + ph && col + tw <= pcol + pw &&
	    rt_dp->image(s, pane, pane ? row - prow : row, pane ? col - pcol : col, th, tw, f, w, h, 0)) {
		drew = 1;
	} else {
		int hth = th;

		if (p->mode == 0 && cw > 1 && ch > 1)
			rt_fit(p, st.aspect, w, h, 1, 2, &tw, &hth);
		row = v[0] + (p->rows - hth) / 2;
		col = v[1] + (p->cols - tw) / 2;
		rt_half(rt_dp, f, w, h, row, col, hth, tw, prow, pcol, ph, pw);
		th = hth;
	}
	p->drawn = seq;
	p->drew = drew;
	p->pr = pane ? prow : 0;
	p->pc = pane ? pcol : 0;
	p->orow = row;
	p->ocol = col;
	p->tw = tw;
	p->th = th;
	rl_unlock(p->r);
	return HIBR_OK;
}

/* retro info ID: what the core is and what it is doing. */
int rt_info(sh *s, rt_pl *p)
{
	rl_st st;

	rl_info(p->r, &st);
	if (s->bind)
		hibr_ret(s, "");
	rt_field(s, "core", st.name);
	rt_field(s, "version", st.ver);
	rt_fieldn(s, "width", st.w);
	rt_fieldn(s, "height", st.h);
	rt_fieldn(s, "fps", st.fps);
	rt_fieldn(s, "rate", st.rate);
	rt_fieldn(s, "aspect", st.aspect);
	rt_fieldn(s, "frames", (double)st.frames);
	rt_field(s, "paused", st.paused ? "1" : "0");
	rt_field(s, "ended", st.ended ? "1" : "0");
	rt_field(s, "output", st.sound);
	rt_field(s, "mode", p->mode == 0 ? "pixels" : "half");
	rt_field(s, "drawn", p->drew ? "pixels" : "cells");
	{
		char pt[64];

		snprintf(pt, sizeof pt, "%d %d %d", st.px, st.py, st.pbtn);
		rt_field(s, "pointer", pt);
	}
	rt_field(s, "error", st.err);
	rl_stfree(&st);
	return HIBR_OK;
}

/* A cell as written: 12 is the middle of cell 12, and 12.25 is a quarter of the way across it. */
double rt_cell(const char *s)
{
	double v = strtod(s, 0);

	return strchr(s, '.') ? v : v + 0.5;
}

/* The usage line. */
void rt_usage(void)
{
	lg(HIBR_LERR, "usage: retro open core [game] [-s sysdir] [-S savedir] [-o key=value]... | list | "
		      "close id|all | fd|wake|frame|info|pause|play|toggle|reset id | size id cols rows [pixels|half] | "
		      "aspect id 4:3|auto|ratio | draw id row col [-p pane] | key id name [down|up|tap] | "
		      "hold id ms | mouse id row col buttons [wheel] | pad id mask | option id key value | "
		      "save id file | load id file");
}

/* retro open CORE [GAME] [options]: start a core. */
int rt_open(sh *s, int ac, char **av)
{
	const char *game = 0, *sysd = 0, *saved = 0;
	char *core, *err = 0, **opts = xm(sizeof *opts * (size_t)(ac + 1));
	int i, n = 0;
	rt_pl *p;
	rl *r;

	for (i = 3; i < ac; i++) {
		if (!strcmp(av[i], "-s") && i + 1 < ac)
			sysd = av[++i];
		else if (!strcmp(av[i], "-S") && i + 1 < ac)
			saved = av[++i];
		else if (!strcmp(av[i], "-o") && i + 1 < ac)
			opts[n++] = av[++i];
		else if (!game)
			game = av[i];
	}
	opts[n] = 0;
	core = rt_corepath(av[2]);
	if (!core) {
		lg(HIBR_LERR, "retro: no core named %s (looked in HIBR_RETRO_CORES, the data folder's hibr/retro/cores, "
			      "/usr/local/lib/hibr/cores and /usr/lib/hibr/cores)", av[2]);
		free(opts);
		return HIBR_FAIL;
	}
	r = rl_open(core, game, sysd, saved, (const char *const *)opts, &err);
	free(core);
	free(opts);
	if (!r) {
		lg(HIBR_LERR, "retro: %s", err ? err : "the core would not start");
		free(err);
		return HIBR_FAIL;
	}
	p = xm(sizeof *p);
	memset(p, 0, sizeof *p);
	p->r = r;
	p->id = ++rt_nextid;
	p->cols = 80;
	p->rows = 24;
	p->hold = 120;
	v_add(&rt_pls, p);
	rt_saynum(s, p->id);
	return HIBR_OK;
}

/* retro: run emulators on libretro cores, the picture drawn into the display. */
int m_retro(sh *s, int ac, char **av)
{
	const char *sub = ac > 1 ? av[1] : "";
	rt_pl *p;
	str b;
	size_t i, n;
	unsigned code, mods;
	uint32_t chr;
	unsigned char *buf;
	FILE *fp;

	if (!strcmp(sub, "open")) {
		if (ac < 3) {
			rt_usage();
			return 2;
		}
		return rt_open(s, ac, av);
	}
	if (!strcmp(sub, "list")) {
		s_init(&b);
		for (i = 0; i < rt_pls.n; i++) {
			if (b.n)
				s_ch(&b, ' ');
			s_num(&b, ((rt_pl *)rt_pls.p[i])->id);
		}
		rt_say(s, b.p ? b.p : "");
		s_free(&b);
		return HIBR_OK;
	}
	if (ac < 3) {
		rt_usage();
		return 2;
	}
	if (!strcmp(sub, "close") && !strcmp(av[2], "all")) {
		while (rt_pls.n)
			rt_forget(rt_pls.p[rt_pls.n - 1]);
		return HIBR_OK;
	}
	p = rt_get(av[2]);
	if (!p)
		return HIBR_FAIL;
	if (!strcmp(sub, "close")) {
		rt_forget(p);
		return HIBR_OK;
	}
	if (!strcmp(sub, "fd")) {
		rt_saynum(s, rl_fd(p->r));
		return HIBR_OK;
	}
	if (!strcmp(sub, "wake")) {
		rl_wake(p->r);
		return HIBR_OK;
	}
	if (!strcmp(sub, "frame")) {
		int w, h, fresh;
		unsigned long seq;

		rl_wake(p->r);
		rl_lock(p->r, &w, &h, &seq);
		fresh = seq != p->drawn;
		rl_unlock(p->r);
		return fresh ? HIBR_OK : HIBR_FAIL;
	}
	if (!strcmp(sub, "info"))
		return rt_info(s, p);
	if (!strcmp(sub, "pause") || !strcmp(sub, "play") || !strcmp(sub, "toggle")) {
		rl_st st;
		int on = sub[1] == 'a';

		if (sub[0] == 't') {
			rl_info(p->r, &st);
			on = !st.paused;
			rl_stfree(&st);
		}
		return rl_pause(p->r, on) < 0 ? HIBR_FAIL : HIBR_OK;
	}
	if (!strcmp(sub, "reset"))
		return rl_reset(p->r) < 0 ? HIBR_FAIL : HIBR_OK;
	if (!strcmp(sub, "size")) {
		if (ac < 5) {
			rt_usage();
			return 2;
		}
		p->cols = atoi(av[3]) > 0 ? atoi(av[3]) : 1;
		p->rows = atoi(av[4]) > 0 ? atoi(av[4]) : 1;
		if (ac > 5)
			p->mode = !strcmp(av[5], "half") ? 1 : 0;
		return HIBR_OK;
	}
	if (!strcmp(sub, "aspect")) {
		if (ac < 4) {
			rt_usage();
			return 2;
		}
		if (!strcmp(av[3], "auto")) {
			p->aspect = 0;
		} else if (strchr(av[3], ':')) {
			double a = atof(av[3]), c = atof(strchr(av[3], ':') + 1);

			p->aspect = c > 0 ? a / c : 0;
		} else {
			p->aspect = atof(av[3]);
		}
		return HIBR_OK;
	}
	if (!strcmp(sub, "draw"))
		return rt_draw(s, p, ac, av);
	if (!strcmp(sub, "hold") && ac > 3) {
		p->hold = atoi(av[3]) > 0 ? atoi(av[3]) : 1;
		return HIBR_OK;
	}
	if (!strcmp(sub, "key")) {
		if (ac < 4 || rt_keymap(av[3], &code, &chr, &mods) < 0) {
			lg(HIBR_LERR, "retro key: no such key: %s", ac > 3 ? av[3] : "");
			return 2;
		}
		{
			static const struct {
				unsigned mod, key;
			} mk[] = { { RETROKMOD_SHIFT, RETROK_LSHIFT }, { RETROKMOD_CTRL, RETROK_LCTRL },
				   { RETROKMOD_ALT, RETROK_LALT } };
			int i, down = ac > 4 && !strcmp(av[4], "down"), up = ac > 4 && !strcmp(av[4], "up");

			for (i = 0; i < 3; i++)
				if (mods & mk[i].mod) {
					if (up)
						rl_key(p->r, mk[i].key, 0, mods, 0);
					else if (down)
						rl_key(p->r, mk[i].key, 0, mods, 1);
					else
						rl_hold(p->r, mk[i].key, 0, mods, p->hold);
				}
			if (down)
				rl_key(p->r, code, chr, mods, 1);
			else if (up)
				rl_key(p->r, code, chr, mods, 0);
			else
				rl_hold(p->r, code, chr, mods, p->hold);
		}
		return HIBR_OK;
	}
	if (!strcmp(sub, "mouse")) {
		int x, y, btn, wheel;
		double row, col;

		if (ac < 6) {
			rt_usage();
			return 2;
		}
		row = rt_cell(av[3]);
		col = rt_cell(av[4]);
		btn = atoi(av[5]);
		wheel = ac > 6 ? atoi(av[6]) : 0;
		if (p->tw < 1 || p->th < 1) {
			x = 0;
			y = 0;
		} else {
			x = (int)(((col + p->pc - p->ocol) / p->tw) * 65534 - 32767);
			y = (int)(((row + p->pr - p->orow) / p->th) * 65534 - 32767);
			x = x < -32767 ? -32767 : x > 32767 ? 32767 : x;
			y = y < -32767 ? -32767 : y > 32767 ? 32767 : y;
		}
		rl_pointer(p->r, x, y, btn, wheel);
		return HIBR_OK;
	}
	if (!strcmp(sub, "pad") && ac > 3) {
		rl_pad(p->r, (unsigned)strtoul(av[3], 0, 0));
		return HIBR_OK;
	}
	if (!strcmp(sub, "option") && ac > 4)
		return rl_option(p->r, av[3], av[4]) < 0 ? HIBR_FAIL : HIBR_OK;
	if (!strcmp(sub, "save") && ac > 3) {
		buf = rl_save(p->r, &n);
		if (!buf) {
			lg(HIBR_LERR, "retro save: the core has no state to give");
			return HIBR_FAIL;
		}
		fp = fopen(av[3], "wb");
		if (!fp || fwrite(buf, 1, n, fp) != n) {
			lg(HIBR_LERR, "retro save: %s: %s", av[3], strerror(errno));
			if (fp)
				fclose(fp);
			free(buf);
			return HIBR_FAIL;
		}
		fclose(fp);
		free(buf);
		return HIBR_OK;
	}
	if (!strcmp(sub, "load") && ac > 3) {
		size_t k = 0, cap = 1 << 20;
		int res;

		fp = fopen(av[3], "rb");
		if (!fp) {
			lg(HIBR_LERR, "retro load: %s: %s", av[3], strerror(errno));
			return HIBR_FAIL;
		}
		buf = xm(cap);
		while ((n = fread(buf + k, 1, cap - k, fp)) > 0) {
			k += n;
			if (k == cap) {
				cap *= 2;
				buf = xr(buf, cap);
			}
		}
		fclose(fp);
		res = rl_load(p->r, buf, k);
		free(buf);
		return res < 0 ? HIBR_FAIL : HIBR_OK;
	}
	lg(HIBR_LERR, "retro: no subcommand %s", sub);
	return 2;
}

/* Nothing to set up until a core is opened. */
int rt_ini(sh *s)
{
	(void)s;
	return HIBR_OK;
}

/* Stop every core when the module goes. */
void rt_fini(sh *s)
{
	(void)s;
	while (rt_pls.n)
		rt_forget(rt_pls.p[rt_pls.n - 1]);
	v_free(&rt_pls);
	rt_dp = 0;
}

const hibr_bi retro_bi[] = {
	{ "retro", m_retro, "run emulators on libretro cores, the picture drawn into the display" },
	HIBR_BI_END
};

HIBR_MODULE("retro", "0.1", "a libretro frontend: DOSBox and the rest as cores", retro_bi, rt_ini, rt_fini);
