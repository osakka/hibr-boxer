#define _GNU_SOURCE

#include "rl.h"
#include "ra.h"
#include "libretro.h"
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* The functions a core must export, resolved by name. */
typedef struct rl_fn rl_fn;
struct rl_fn {
	void (*init)(void);
	void (*deinit)(void);
	unsigned (*apiver)(void);
	void (*sysinfo)(struct retro_system_info *);
	void (*avinfo)(struct retro_system_av_info *);
	void (*setenv)(retro_environment_t);
	void (*setvid)(retro_video_refresh_t);
	void (*setas)(retro_audio_sample_t);
	void (*setasb)(retro_audio_sample_batch_t);
	void (*setpoll)(retro_input_poll_t);
	void (*setinp)(retro_input_state_t);
	void (*reset)(void);
	void (*run)(void);
	size_t (*ssize)(void);
	bool (*ser)(void *, size_t);
	bool (*unser)(const void *, size_t);
	bool (*load)(const struct retro_game_info *);
	void (*unload)(void);
};

typedef struct rl_sym rl_sym;
struct rl_sym {
	const char *nm;
	size_t off;
};

const rl_sym rl_syms[] = {
	{ "retro_init", offsetof(rl_fn, init) },
	{ "retro_deinit", offsetof(rl_fn, deinit) },
	{ "retro_api_version", offsetof(rl_fn, apiver) },
	{ "retro_get_system_info", offsetof(rl_fn, sysinfo) },
	{ "retro_get_system_av_info", offsetof(rl_fn, avinfo) },
	{ "retro_set_environment", offsetof(rl_fn, setenv) },
	{ "retro_set_video_refresh", offsetof(rl_fn, setvid) },
	{ "retro_set_audio_sample", offsetof(rl_fn, setas) },
	{ "retro_set_audio_sample_batch", offsetof(rl_fn, setasb) },
	{ "retro_set_input_poll", offsetof(rl_fn, setpoll) },
	{ "retro_set_input_state", offsetof(rl_fn, setinp) },
	{ "retro_reset", offsetof(rl_fn, reset) },
	{ "retro_run", offsetof(rl_fn, run) },
	{ "retro_serialize_size", offsetof(rl_fn, ssize) },
	{ "retro_serialize", offsetof(rl_fn, ser) },
	{ "retro_unserialize", offsetof(rl_fn, unser) },
	{ "retro_load_game", offsetof(rl_fn, load) },
	{ "retro_unload_game", offsetof(rl_fn, unload) },
	{ 0, 0 }
};

/* A core option: its key, the value it has now, and every value it may take. */
typedef struct rl_var rl_var;
struct rl_var {
	char *key, *val, *all;
};

/* A key event waiting for the core's thread, and a key held until a time. */
typedef struct rl_ke rl_ke;
struct rl_ke {
	unsigned code;
	uint32_t chr;
	unsigned mods;
	int down;
	double dead;
};

struct rl {
	char *core, *game, *sysdir, *savedir, *cdir;
	void *dl;
	rl_fn f;
	pthread_t th;
	int started;
	pthread_mutex_t mu, fmu;
	pthread_cond_t cv;
	int state, quit, paused, ended;
	char *err, *name, *ver;
	int fmt;
	unsigned char *front, *back, *shown;
	size_t fcap, bcap, scap;
	unsigned long sseq;
	int sw, sh;
	int fw, fh;
	unsigned long seq, frames;
	int wake[2];
	double fps, rate, aspect;
	ra_ao ao;
	int aoopen, aud;
	char *sound;
	unsigned pad;
	unsigned char *keys;
	rl_ke *ev, *hold;
	int nev, nhold;
	retro_keyboard_event_t kcb;
	int px, py, pbtn, lpx, lpy, havep, mdx, mdy, wup, wdown;
	rl_var *vars;
	int nvars, vdirty;
	char **popt;
	char *live;
	int op;
	const char *oa, *ob;
	const unsigned char *oin;
	size_t oinn, oouts;
	unsigned char *oout;
	int ores, odone;
};

pthread_key_t rl_kcur;
pthread_once_t rl_once = PTHREAD_ONCE_INIT;
pthread_mutex_t rl_gmu = PTHREAD_MUTEX_INITIALIZER;
char **rl_live;
int rl_nlive;

/* Make the key that tells a callback which player its thread belongs to. */
void rl_mkkey(void)
{
	pthread_key_create(&rl_kcur, 0);
}

/* A flag shared between the core's thread and the caller's, read under the lock. */
int rl_geti(rl *r, int *p)
{
	int v;

	pthread_mutex_lock(&r->mu);
	v = *p;
	pthread_mutex_unlock(&r->mu);
	return v;
}

/* Set a shared flag and wake whoever waits on it. */
void rl_seti(rl *r, int *p, int v)
{
	pthread_mutex_lock(&r->mu);
	*p = v;
	pthread_cond_broadcast(&r->cv);
	pthread_mutex_unlock(&r->mu);
}

/* One more frame run. */
void rl_count(rl *r)
{
	pthread_mutex_lock(&r->mu);
	r->frames++;
	pthread_mutex_unlock(&r->mu);
}

/* A copy of a string, or null. */
char *rl_dup(const char *s)
{
	return s ? xs(s) : 0;
}

/* Log one line from a core, in the shell's own levels. */
void rl_logf(enum retro_log_level lv, const char *fmt, ...)
{
	va_list ap;
	char *m = 0;
	size_t n;

	va_start(ap, fmt);
	if (vasprintf(&m, fmt, ap) < 0)
		m = 0;
	va_end(ap);
	if (!m)
		return;
	n = strlen(m);
	while (n && (m[n - 1] == '\n' || m[n - 1] == '\r'))
		m[--n] = 0;
	lg(lv == RETRO_LOG_ERROR ? HIBR_LERR : HIBR_LDBG, "retro: core: %s", m);
	free(m);
}

/* Read a whole file into memory; null when it cannot be read. */
unsigned char *rl_slurp(const char *path, size_t *n)
{
	FILE *f = fopen(path, "rb");
	unsigned char *b = 0;
	size_t cap = 0, len = 0, k;

	if (!f)
		return 0;
	for (;;) {
		if (len + 65536 > cap) {
			cap = cap ? cap * 2 : 262144;
			b = xr(b, cap);
		}
		k = fread(b + len, 1, cap - len, f);
		if (!k)
			break;
		len += k;
	}
	fclose(f);
	*n = len;
	return b;
}

/* The folder a path is in, as a new string. */
char *rl_dir(const char *p)
{
	const char *s = strrchr(p, '/');
	char *d;

	if (!s)
		return xs(".");
	d = xs(p);
	d[s == p ? 1 : s - p] = 0;
	return d;
}

/* Find a variable by key. */
rl_var *rl_find(rl *r, const char *key)
{
	int i;

	for (i = 0; i < r->nvars; i++)
		if (!strcmp(r->vars[i].key, key))
			return &r->vars[i];
	return 0;
}

/* The value an option was given before the core started, or null. */
const char *rl_preset(rl *r, const char *key)
{
	char **o;
	size_t n = strlen(key);

	for (o = r->popt; o && *o; o++)
		if (!strncmp(*o, key, n) && (*o)[n] == '=')
			return *o + n + 1;
	return 0;
}

/* Take the core's list of variables: "Description; a|b|c", the first being the default. */
void rl_setvars(rl *r, const struct retro_variable *v)
{
	for (; v && v->key; v++) {
		rl_var *x = rl_find(r, v->key);
		const char *a = strchr(v->value, ';'), *p;
		char *def, *e;

		if (a) {
			a++;
			while (*a == ' ')
				a++;
		} else {
			a = v->value;
		}
		def = xs(a);
		e = strchr(def, '|');
		if (e)
			*e = 0;
		p = rl_preset(r, v->key);
		if (!x) {
			r->vars = xr(r->vars, sizeof *r->vars * (size_t)(r->nvars + 1));
			x = &r->vars[r->nvars++];
			x->key = xs(v->key);
			x->val = 0;
			x->all = 0;
		}
		free(x->val);
		x->val = xs(p ? p : def);
		free(x->all);
		x->all = xs(a);
		free(def);
	}
}

/* Set an option the core knows, or say it does not. */
int rl_setvar(rl *r, const char *key, const char *val)
{
	rl_var *x = rl_find(r, key);

	if (!x)
		return -1;
	free(x->val);
	x->val = xs(val);
	r->vdirty = 1;
	return 0;
}

/* The shape a core says its picture has: its own ratio, or else the base size's. */
double rl_aspect(const struct retro_game_geometry *g)
{
	if (g->aspect_ratio > 0)
		return g->aspect_ratio;
	return g->base_height ? (double)g->base_width / g->base_height : 0;
}

/* The one place a core asks for what the frontend knows. */
bool rl_env(unsigned cmd, void *data)
{
	rl *r = pthread_getspecific(rl_kcur);

	if (!r)
		return false;
	switch (cmd & ~(unsigned)(RETRO_ENVIRONMENT_EXPERIMENTAL | RETRO_ENVIRONMENT_PRIVATE)) {
	case RETRO_ENVIRONMENT_GET_OVERSCAN:
		*(bool *)data = false;
		return true;
	case RETRO_ENVIRONMENT_GET_CAN_DUPE:
		*(bool *)data = true;
		return true;
	case RETRO_ENVIRONMENT_SET_MESSAGE:
		lg(HIBR_LDBG, "retro: core says: %s", ((const struct retro_message *)data)->msg);
		return true;
	case RETRO_ENVIRONMENT_SET_MESSAGE_EXT:
		lg(HIBR_LDBG, "retro: core says: %s", ((const struct retro_message_ext *)data)->msg);
		return true;
	case RETRO_ENVIRONMENT_GET_MESSAGE_INTERFACE_VERSION:
		*(unsigned *)data = 0;
		return true;
	case RETRO_ENVIRONMENT_SHUTDOWN:
		rl_seti(r, &r->quit, 1);
		return true;
	case RETRO_ENVIRONMENT_SET_PERFORMANCE_LEVEL:
	case RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:
	case RETRO_ENVIRONMENT_SET_CONTROLLER_INFO:
	case RETRO_ENVIRONMENT_SET_SUBSYSTEM_INFO:
	case RETRO_ENVIRONMENT_SET_SUPPORT_NO_GAME:
	case RETRO_ENVIRONMENT_SET_SERIALIZATION_QUIRKS:
	case RETRO_ENVIRONMENT_SET_ROTATION:
	case RETRO_ENVIRONMENT_SET_SUPPORT_ACHIEVEMENTS:
		return true;
	case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
		*(const char **)data = r->sysdir;
		return true;
	case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
		*(const char **)data = r->savedir;
		return true;
	case RETRO_ENVIRONMENT_GET_CONTENT_DIRECTORY:
		*(const char **)data = r->cdir;
		return r->cdir != 0;
	case RETRO_ENVIRONMENT_GET_LIBRETRO_PATH:
		*(const char **)data = r->core;
		return true;
	case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT: {
		int f = *(const int *)data;

		if (f != RETRO_PIXEL_FORMAT_0RGB1555 && f != RETRO_PIXEL_FORMAT_XRGB8888 &&
		    f != RETRO_PIXEL_FORMAT_RGB565)
			return false;
		r->fmt = f;
		return true;
	}
	case RETRO_ENVIRONMENT_SET_KEYBOARD_CALLBACK:
		r->kcb = ((const struct retro_keyboard_callback *)data)->callback;
		return true;
	case RETRO_ENVIRONMENT_GET_VARIABLE: {
		struct retro_variable *v = data;
		rl_var *x = rl_find(r, v->key);

		v->value = x ? x->val : 0;
		return x != 0;
	}
	case RETRO_ENVIRONMENT_SET_VARIABLES:
		rl_setvars(r, data);
		return true;
	case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
		*(bool *)data = r->vdirty != 0;
		r->vdirty = 0;
		return true;
	case RETRO_ENVIRONMENT_SET_VARIABLE: {
		const struct retro_variable *v = data;

		if (!v)
			return true;
		return v->key && v->value && rl_setvar(r, v->key, v->value) == 0;
	}
	case RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION:
		*(unsigned *)data = 0;
		return true;
	case RETRO_ENVIRONMENT_GET_LOG_INTERFACE:
		((struct retro_log_callback *)data)->log = rl_logf;
		return true;
	case RETRO_ENVIRONMENT_GET_INPUT_DEVICE_CAPABILITIES:
		*(uint64_t *)data = (1u << RETRO_DEVICE_JOYPAD) | (1u << RETRO_DEVICE_MOUSE) |
				    (1u << RETRO_DEVICE_KEYBOARD) | (1u << RETRO_DEVICE_POINTER);
		return true;
	case RETRO_ENVIRONMENT_GET_INPUT_MAX_USERS:
		*(unsigned *)data = 1;
		return true;
	case RETRO_ENVIRONMENT_GET_LANGUAGE:
		*(unsigned *)data = RETRO_LANGUAGE_ENGLISH;
		return true;
	case RETRO_ENVIRONMENT_GET_JIT_CAPABLE:
		*(bool *)data = true;
		return true;
	case RETRO_ENVIRONMENT_SET_GEOMETRY:
		r->aspect = rl_aspect((const struct retro_game_geometry *)data);
		return true;
	case RETRO_ENVIRONMENT_SET_SYSTEM_AV_INFO: {
		const struct retro_system_av_info *a = data;

		r->fps = a->timing.fps;
		r->rate = a->timing.sample_rate;
		r->aspect = rl_aspect(&a->geometry);
		return true;
	}
	case RETRO_ENVIRONMENT_SET_HW_RENDER:
		lg(HIBR_LDBG, "retro: core asked for hardware rendering; software only");
		return false;
	default:
		lg(HIBR_LDBG, "retro: environment %u not handled", cmd);
		return false;
	}
}

/* Convert the core's frame to RGB triples in the back buffer. */
void rl_conv(rl *r, const void *data, unsigned w, unsigned h, size_t pitch)
{
	unsigned x, y;
	size_t need = (size_t)w * h * 3;
	unsigned char *o;

	if (need > r->bcap) {
		r->back = xr(r->back, need);
		r->bcap = need;
	}
	o = r->back;
	for (y = 0; y < h; y++) {
		const unsigned char *row = (const unsigned char *)data + y * pitch;

		for (x = 0; x < w; x++, o += 3) {
			if (r->fmt == RETRO_PIXEL_FORMAT_XRGB8888) {
				o[0] = row[x * 4 + 2];
				o[1] = row[x * 4 + 1];
				o[2] = row[x * 4];
			} else {
				unsigned v = row[x * 2] | row[x * 2 + 1] << 8;

				if (r->fmt == RETRO_PIXEL_FORMAT_RGB565) {
					o[0] = (unsigned char)((v >> 8 & 0xf8) | (v >> 13));
					o[1] = (unsigned char)((v >> 3 & 0xfc) | (v >> 9 & 3));
					o[2] = (unsigned char)((v << 3 & 0xf8) | (v >> 2 & 7));
				} else {
					o[0] = (unsigned char)((v >> 7 & 0xf8) | (v >> 12 & 7));
					o[1] = (unsigned char)((v >> 2 & 0xf8) | (v >> 7 & 7));
					o[2] = (unsigned char)((v << 3 & 0xf8) | (v >> 2 & 7));
				}
			}
		}
	}
}

/* The core has made a frame: convert it, make it the latest, and wake whoever waits. */
void rl_video(const void *data, unsigned w, unsigned h, size_t pitch)
{
	rl *r = pthread_getspecific(rl_kcur);
	unsigned char *t, b = 1;
	size_t tc;

	if (!r || !data || !w || !h)
		return;
	rl_conv(r, data, w, h, pitch);
	pthread_mutex_lock(&r->fmu);
	t = r->front;
	r->front = r->back;
	r->back = t;
	tc = r->fcap;
	r->fcap = r->bcap;
	r->bcap = tc;
	r->fw = (int)w;
	r->fh = (int)h;
	r->seq++;
	pthread_mutex_unlock(&r->fmu);
	if (write(r->wake[1], &b, 1) < 0 && errno != EAGAIN)
		lg(HIBR_LDBG, "retro: wake: %s", strerror(errno));
}

/* Sound from the core, a batch of stereo frames; the write is what paces the core. */
size_t rl_abatch(const int16_t *d, size_t n)
{
	rl *r = pthread_getspecific(rl_kcur);

	if (!r || !r->aoopen)
		return n;
	r->aud = 1;
	r->ao.write(&r->ao, d, (int)n);
	return n;
}

/* Sound from the core, one stereo frame. */
void rl_asample(int16_t l, int16_t rt)
{
	int16_t d[2];

	d[0] = l;
	d[1] = rt;
	rl_abatch(d, 1);
}

/* The core asks the frontend to look at its input; it is kept current already. */
void rl_poll(void)
{
}

/* What one input is doing now. */
int16_t rl_input(unsigned port, unsigned dev, unsigned idx, unsigned id)
{
	rl *r = pthread_getspecific(rl_kcur);
	int v = 0;

	if (!r || port)
		return 0;
	pthread_mutex_lock(&r->mu);
	switch (dev & RETRO_DEVICE_MASK) {
	case RETRO_DEVICE_JOYPAD:
		v = id == RETRO_DEVICE_ID_JOYPAD_MASK ? (int)r->pad : (int)(r->pad >> id & 1);
		break;
	case RETRO_DEVICE_KEYBOARD:
		v = id < RETROK_LAST ? r->keys[id] : 0;
		break;
	case RETRO_DEVICE_MOUSE:
		if (id == RETRO_DEVICE_ID_MOUSE_X) {
			v = r->mdx;
			r->mdx = 0;
		} else if (id == RETRO_DEVICE_ID_MOUSE_Y) {
			v = r->mdy;
			r->mdy = 0;
		} else if (id == RETRO_DEVICE_ID_MOUSE_LEFT) {
			v = r->pbtn & 1;
		} else if (id == RETRO_DEVICE_ID_MOUSE_RIGHT) {
			v = r->pbtn >> 1 & 1;
		} else if (id == RETRO_DEVICE_ID_MOUSE_MIDDLE) {
			v = r->pbtn >> 2 & 1;
		} else if (id == RETRO_DEVICE_ID_MOUSE_WHEELUP) {
			v = r->wup;
			r->wup = 0;
		} else if (id == RETRO_DEVICE_ID_MOUSE_WHEELDOWN) {
			v = r->wdown;
			r->wdown = 0;
		}
		break;
	case RETRO_DEVICE_POINTER:
		if (id == RETRO_DEVICE_ID_POINTER_X)
			v = r->px;
		else if (id == RETRO_DEVICE_ID_POINTER_Y)
			v = r->py;
		else if (id == RETRO_DEVICE_ID_POINTER_PRESSED)
			v = r->pbtn & 1;
		else if (id == RETRO_DEVICE_ID_POINTER_COUNT)
			v = r->havep;
		break;
	}
	pthread_mutex_unlock(&r->mu);
	return (int16_t)v;
}

/* Queue a key event for the core's thread; the caller holds the lock. */
void rl_qkey(rl *r, unsigned code, uint32_t chr, unsigned mods, int down)
{
	rl_ke *e;

	r->ev = xr(r->ev, sizeof *r->ev * (size_t)(r->nev + 1));
	e = &r->ev[r->nev++];
	e->code = code;
	e->chr = chr;
	e->mods = mods;
	e->down = down;
	e->dead = 0;
}

/* Hand the core what was waiting: key events, and the release of keys whose time has run out. */
void rl_pump(rl *r)
{
	int i, n;
	rl_ke *ev;
	double now = ra_now();

	pthread_mutex_lock(&r->mu);
	for (i = 0; i < r->nhold; i++)
		if (r->hold[i].dead <= now) {
			rl_qkey(r, r->hold[i].code, r->hold[i].chr, r->hold[i].mods, 0);
			r->hold[i--] = r->hold[--r->nhold];
		}
	ev = r->ev;
	n = r->nev;
	r->ev = 0;
	r->nev = 0;
	for (i = 0; i < n; i++)
		if (ev[i].code < RETROK_LAST)
			r->keys[ev[i].code] = (unsigned char)ev[i].down;
	pthread_mutex_unlock(&r->mu);
	for (i = 0; i < n; i++)
		if (r->kcb)
			r->kcb(ev[i].down != 0, ev[i].code, ev[i].chr, (uint16_t)ev[i].mods);
	free(ev);
}

/* Do the one operation a caller is waiting for, on the core's thread. */
void rl_op(rl *r)
{
	int op, res = 0;
	const char *a, *b;
	const unsigned char *in;
	size_t inn, outn = 0;
	unsigned char *out = 0;

	pthread_mutex_lock(&r->mu);
	if (!r->op || r->odone) {
		pthread_mutex_unlock(&r->mu);
		return;
	}
	op = r->op;
	a = r->oa;
	b = r->ob;
	in = r->oin;
	inn = r->oinn;
	pthread_mutex_unlock(&r->mu);
	if (op == 1) {
		rl_seti(r, &r->paused, a != 0);
	} else if (op == 2) {
		r->f.reset();
	} else if (op == 3) {
		res = rl_setvar(r, a, b);
	} else if (op == 4) {
		outn = r->f.ssize();
		out = outn ? xm(outn) : 0;
		if (!out || !r->f.ser(out, outn)) {
			free(out);
			out = 0;
			res = -1;
		}
	} else if (op == 5) {
		res = r->f.unser(in, inn) ? 0 : -1;
	}
	pthread_mutex_lock(&r->mu);
	r->ores = res;
	r->oout = out;
	r->oouts = outn;
	r->odone = 1;
	pthread_cond_broadcast(&r->cv);
	pthread_mutex_unlock(&r->mu);
}

/* Ask the core's thread to do something and wait for it; -1 when the core has ended. */
int rl_call(rl *r, int op, const char *a, const char *b, const unsigned char *in, size_t inn,
	    unsigned char **out, size_t *outn)
{
	int res;

	pthread_mutex_lock(&r->mu);
	while (r->op && !r->ended)
		pthread_cond_wait(&r->cv, &r->mu);
	if (r->ended) {
		pthread_mutex_unlock(&r->mu);
		return -1;
	}
	r->op = op;
	r->oa = a;
	r->ob = b;
	r->oin = in;
	r->oinn = inn;
	r->odone = 0;
	while (!r->odone && !r->ended)
		pthread_cond_wait(&r->cv, &r->mu);
	res = r->odone ? r->ores : -1;
	if (out)
		*out = r->oout;
	if (outn)
		*outn = r->oouts;
	r->op = 0;
	r->oout = 0;
	pthread_cond_broadcast(&r->cv);
	pthread_mutex_unlock(&r->mu);
	return res;
}

/* Fail the start: say why and let rl_open know. */
void rl_fail(rl *r, const char *fmt, ...)
{
	va_list ap;
	char *m = 0;

	va_start(ap, fmt);
	if (vasprintf(&m, fmt, ap) < 0)
		m = 0;
	va_end(ap);
	pthread_mutex_lock(&r->mu);
	r->err = m;
	r->state = -1;
	pthread_cond_broadcast(&r->cv);
	pthread_mutex_unlock(&r->mu);
}

/* Load the core, start it, and run it until told to stop: everything on this one thread. */
void *rl_thread(void *arg)
{
	rl *r = arg;
	const rl_sym *s;
	struct retro_system_info si;
	struct retro_system_av_info av;
	struct retro_game_info gi;
	unsigned char *data = 0;
	size_t dn = 0;
	int inited = 0, loaded = 0;
	char *why = 0;
	double next;

	pthread_setspecific(rl_kcur, r);
	r->dl = dlopen(r->core, RTLD_NOW | RTLD_LOCAL);
	if (!r->dl) {
		rl_fail(r, "%s", dlerror());
		goto out;
	}
	for (s = rl_syms; s->nm; s++) {
		void *p = dlsym(r->dl, s->nm);

		if (!p) {
			rl_fail(r, "%s is not a libretro core: no %s", r->core, s->nm);
			goto out;
		}
		*(void **)((char *)&r->f + s->off) = p;
	}
	if (r->f.apiver() != RETRO_API_VERSION) {
		rl_fail(r, "%s speaks libretro API %u, not %d", r->core, r->f.apiver(), RETRO_API_VERSION);
		goto out;
	}
	r->f.setenv(rl_env);
	r->f.setvid(rl_video);
	r->f.setas(rl_asample);
	r->f.setasb(rl_abatch);
	r->f.setpoll(rl_poll);
	r->f.setinp(rl_input);
	r->f.init();
	inited = 1;
	memset(&si, 0, sizeof si);
	r->f.sysinfo(&si);
	r->name = rl_dup(si.library_name);
	r->ver = rl_dup(si.library_version);
	memset(&gi, 0, sizeof gi);
	if (r->game) {
		gi.path = r->game;
		if (!si.need_fullpath) {
			data = rl_slurp(r->game, &dn);
			if (!data) {
				rl_fail(r, "cannot read %s: %s", r->game, strerror(errno));
				goto out;
			}
			gi.data = data;
			gi.size = dn;
		}
		r->cdir = rl_dir(r->game);
	}
	if (!r->f.load(r->game ? &gi : 0)) {
		rl_fail(r, "%s would not load %s", r->name ? r->name : "the core", r->game ? r->game : "nothing");
		goto out;
	}
	loaded = 1;
	memset(&av, 0, sizeof av);
	r->f.avinfo(&av);
	r->fps = av.timing.fps > 1 ? av.timing.fps : 60;
	r->rate = av.timing.sample_rate > 1000 ? av.timing.sample_rate : 44100;
	r->aspect = rl_aspect(&av.geometry);
	if (ra_audio(&r->ao, (int)(r->rate + 0.5), 2, &why) == HIBR_OK) {
		r->aoopen = 1;
		r->sound = rl_dup(r->ao.name ? r->ao.name : "none");
	}
	if (why)
		lg(HIBR_LDBG, "retro: sound: %s", why);
	free(why);
	pthread_mutex_lock(&r->mu);
	r->state = 1;
	pthread_cond_broadcast(&r->cv);
	pthread_mutex_unlock(&r->mu);
	next = ra_now();
	while (!rl_geti(r, &r->quit)) {
		rl_pump(r);
		rl_op(r);
		if (rl_geti(r, &r->paused)) {
			usleep(5000);
			next = ra_now();
			continue;
		}
		r->aud = 0;
		r->f.run();
		rl_count(r);
		next += 1.0 / r->fps;
		if (r->aud || ra_now() > next + 0.25)
			next = ra_now();
		else if (next > ra_now())
			usleep((useconds_t)((next - ra_now()) * 1e6));
	}
out:
	if (loaded)
		r->f.unload();
	if (inited)
		r->f.deinit();
	if (r->aoopen)
		r->ao.close(&r->ao);
	r->aoopen = 0;
	free(data);
	if (r->dl)
		dlclose(r->dl);
	pthread_mutex_lock(&r->mu);
	r->ended = 1;
	pthread_cond_broadcast(&r->cv);
	pthread_mutex_unlock(&r->mu);
	pthread_setspecific(rl_kcur, 0);
	return 0;
}

rl *rl_open(const char *core, const char *game, const char *sysdir, const char *savedir,
	    const char *const *opts, char **err)
{
	rl *r;
	int n = 0, i;
	char *rp = realpath(core, 0);

	pthread_once(&rl_once, rl_mkkey);
	if (!rp)
		rp = xs(core);
	pthread_mutex_lock(&rl_gmu);
	for (i = 0; i < rl_nlive; i++)
		if (!strcmp(rl_live[i], rp)) {
			pthread_mutex_unlock(&rl_gmu);
			*err = rl_dup("that core has already run in this process; a core file runs once, since DOSBox Pure crashes when loaded again");
			free(rp);
			return 0;
		}
	rl_live = xr(rl_live, sizeof *rl_live * (size_t)(rl_nlive + 1));
	rl_live[rl_nlive++] = rp;
	pthread_mutex_unlock(&rl_gmu);
	r = xm(sizeof *r);
	memset(r, 0, sizeof *r);
	r->live = rp;
	r->core = xs(core);
	r->game = rl_dup(game);
	r->sysdir = xs(sysdir ? sysdir : ".");
	r->savedir = xs(savedir ? savedir : ".");
	r->fmt = RETRO_PIXEL_FORMAT_0RGB1555;
	r->keys = xm(RETROK_LAST);
	memset(r->keys, 0, RETROK_LAST);
	pthread_mutex_init(&r->mu, 0);
	pthread_mutex_init(&r->fmu, 0);
	pthread_cond_init(&r->cv, 0);
	if (pipe2(r->wake, O_NONBLOCK | O_CLOEXEC) < 0) {
		*err = xs(strerror(errno));
		rl_close(r);
		return 0;
	}
	for (; opts && opts[n]; n++)
		;
	r->popt = xm(sizeof *r->popt * (size_t)(n + 1));
	for (n = 0; opts && opts[n]; n++)
		r->popt[n] = xs(opts[n]);
	r->popt[n] = 0;
	if (pthread_create(&r->th, 0, rl_thread, r)) {
		*err = xs("cannot start a thread");
		rl_close(r);
		return 0;
	}
	r->started = 1;
	pthread_mutex_lock(&r->mu);
	while (!r->state)
		pthread_cond_wait(&r->cv, &r->mu);
	pthread_mutex_unlock(&r->mu);
	if (r->state < 0) {
		*err = r->err ? xs(r->err) : xs("the core would not start");
		rl_close(r);
		return 0;
	}
	return r;
}

void rl_close(rl *r)
{
	int i;

	if (r->started) {
		pthread_mutex_lock(&r->mu);
		r->quit = 1;
		pthread_cond_broadcast(&r->cv);
		pthread_mutex_unlock(&r->mu);
		pthread_join(r->th, 0);
	}
	for (i = 0; i < r->nvars; i++) {
		free(r->vars[i].key);
		free(r->vars[i].val);
		free(r->vars[i].all);
	}
	for (i = 0; r->popt && r->popt[i]; i++)
		free(r->popt[i]);
	if (r->wake[0] > 0)
		close(r->wake[0]);
	if (r->wake[1] > 0)
		close(r->wake[1]);
	free(r->vars);
	free(r->popt);
	free(r->front);
	free(r->shown);
	free(r->back);
	free(r->keys);
	free(r->ev);
	free(r->hold);
	free(r->core);
	free(r->game);
	free(r->sysdir);
	free(r->savedir);
	free(r->cdir);
	free(r->err);
	free(r->name);
	free(r->ver);
	free(r->sound);
	pthread_mutex_destroy(&r->mu);
	pthread_mutex_destroy(&r->fmu);
	pthread_cond_destroy(&r->cv);
	free(r);
}

int rl_fd(rl *r)
{
	return r->wake[0];
}

void rl_wake(rl *r)
{
	char b[256];

	while (read(r->wake[0], b, sizeof b) > 0)
		;
}

const unsigned char *rl_lock(rl *r, int *w, int *h, unsigned long *seq)
{
	pthread_mutex_lock(&r->fmu);
	if (r->seq != r->sseq && r->seq) {
		size_t n = (size_t)r->fw * r->fh * 3;

		if (n > r->scap) {
			r->shown = xr(r->shown, n);
			r->scap = n;
		}
		memcpy(r->shown, r->front, n);
		r->sseq = r->seq;
		r->sw = r->fw;
		r->sh = r->fh;
	}
	pthread_mutex_unlock(&r->fmu);
	*w = r->sw;
	*h = r->sh;
	*seq = r->sseq;
	return r->sseq ? r->shown : 0;
}

void rl_unlock(rl *r)
{
	(void)r;
}

void rl_info(rl *r, rl_st *st)
{
	memset(st, 0, sizeof *st);
	pthread_mutex_lock(&r->fmu);
	st->w = r->fw;
	st->h = r->fh;
	st->seq = r->seq;
	pthread_mutex_unlock(&r->fmu);
	pthread_mutex_lock(&r->mu);
	st->paused = r->paused;
	st->ended = r->ended;
	st->fps = r->fps;
	st->rate = r->rate;
	st->aspect = r->aspect;
	st->frames = r->frames;
	st->name = rl_dup(r->name);
	st->ver = rl_dup(r->ver);
	st->err = rl_dup(r->err);
	st->sound = rl_dup(r->sound);
	pthread_mutex_unlock(&r->mu);
}

void rl_stfree(rl_st *st)
{
	free(st->name);
	free(st->ver);
	free(st->err);
	free(st->sound);
}

void rl_key(rl *r, unsigned code, uint32_t chr, unsigned mods, int down)
{
	int i;

	pthread_mutex_lock(&r->mu);
	for (i = 0; i < r->nhold; i++)
		if (r->hold[i].code == code && !down) {
			r->hold[i] = r->hold[--r->nhold];
			break;
		}
	rl_qkey(r, code, chr, mods, down);
	pthread_mutex_unlock(&r->mu);
}

void rl_hold(rl *r, unsigned code, uint32_t chr, unsigned mods, int ms)
{
	int i;

	pthread_mutex_lock(&r->mu);
	for (i = 0; i < r->nhold && r->hold[i].code != code; i++)
		;
	if (i == r->nhold) {
		r->hold = xr(r->hold, sizeof *r->hold * (size_t)(r->nhold + 1));
		r->nhold++;
		r->hold[i].code = code;
		r->hold[i].chr = chr;
		r->hold[i].mods = mods;
		rl_qkey(r, code, chr, mods, 1);
	}
	r->hold[i].dead = ra_now() + ms / 1000.0;
	pthread_mutex_unlock(&r->mu);
}

void rl_pointer(rl *r, int x, int y, int buttons, int wheel)
{
	int fw, fh;

	pthread_mutex_lock(&r->fmu);
	fw = r->fw ? r->fw : 320;
	fh = r->fh ? r->fh : 200;
	pthread_mutex_unlock(&r->fmu);
	pthread_mutex_lock(&r->mu);
	if (r->havep) {
		r->mdx += (int)((long long)(x - r->lpx) * fw / 65534);
		r->mdy += (int)((long long)(y - r->lpy) * fh / 65534);
	}
	r->lpx = r->px = x;
	r->lpy = r->py = y;
	r->havep = 1;
	r->pbtn = buttons;
	if (wheel > 0)
		r->wup += wheel;
	else if (wheel < 0)
		r->wdown -= wheel;
	pthread_mutex_unlock(&r->mu);
}

void rl_pad(rl *r, unsigned mask)
{
	pthread_mutex_lock(&r->mu);
	r->pad = mask;
	pthread_mutex_unlock(&r->mu);
}

int rl_pause(rl *r, int on)
{
	return rl_call(r, 1, on ? "1" : 0, 0, 0, 0, 0, 0);
}

int rl_reset(rl *r)
{
	return rl_call(r, 2, 0, 0, 0, 0, 0, 0);
}

int rl_option(rl *r, const char *key, const char *val)
{
	return rl_call(r, 3, key, val, 0, 0, 0, 0);
}

unsigned char *rl_save(rl *r, size_t *n)
{
	unsigned char *b = 0;

	*n = 0;
	if (rl_call(r, 4, 0, 0, 0, 0, &b, n) < 0)
		return 0;
	return b;
}

int rl_load(rl *r, const unsigned char *buf, size_t n)
{
	return rl_call(r, 5, 0, 0, buf, n, 0, 0);
}
