#define _GNU_SOURCE

#include "libretro.h"
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* A libretro core that is only a test: 320x200 at 60 fps, a moving block, a tone, and the state of its input
   drawn into the frame. After 120 frames it changes to 320x240. Options: testcore_format (xrgb8888, rgb565,
   0rgb1555) and testcore_tone (440, 880). */

retro_environment_t tc_env;
retro_video_refresh_t tc_vid;
retro_audio_sample_batch_t tc_aud;
retro_input_state_t tc_inp;
retro_input_poll_t tc_poll;
struct retro_keyboard_callback tc_kcb;

int tc_fmt = RETRO_PIXEL_FORMAT_XRGB8888;
int tc_w = 320, tc_h = 200;
unsigned long tc_n;
unsigned tc_keyev, tc_keydown_evs, tc_keyup_evs;
unsigned tc_shot;
unsigned long tc_nkeys;
double tc_phase;
double tc_tone = 440;

/* The core's own keyboard callback: count the events it is told of. */
void tc_key(bool down, unsigned code, uint32_t chr, uint16_t mods)
{
	(void)code;
	(void)chr;
	(void)mods;
	tc_keyev++;
	if (down && chr == 'q')
		tc_env(RETRO_ENVIRONMENT_SHUTDOWN, 0);
	if (down)
		tc_keydown_evs++;
	else
		tc_keyup_evs++;
}

unsigned retro_api_version(void)
{
	return RETRO_API_VERSION;
}

void retro_set_environment(retro_environment_t e)
{
	static const struct retro_variable vars[] = {
		{ "testcore_format", "Pixel format; xrgb8888|rgb565|0rgb1555" },
		{ "testcore_tone", "Tone; 440|880" },
		{ 0, 0 }
	};

	tc_env = e;
	e(RETRO_ENVIRONMENT_SET_VARIABLES, (void *)vars);
}

void retro_set_video_refresh(retro_video_refresh_t v)
{
	tc_vid = v;
}

void retro_set_audio_sample(retro_audio_sample_t a)
{
	(void)a;
}

void retro_set_audio_sample_batch(retro_audio_sample_batch_t a)
{
	tc_aud = a;
}

void retro_set_input_poll(retro_input_poll_t p)
{
	tc_poll = p;
}

void retro_set_input_state(retro_input_state_t s)
{
	tc_inp = s;
}

void retro_init(void)
{
	struct retro_variable v;

	v.key = "testcore_format";
	v.value = 0;
	if (tc_env(RETRO_ENVIRONMENT_GET_VARIABLE, &v) && v.value) {
		if (!strcmp(v.value, "rgb565"))
			tc_fmt = RETRO_PIXEL_FORMAT_RGB565;
		else if (!strcmp(v.value, "0rgb1555"))
			tc_fmt = RETRO_PIXEL_FORMAT_0RGB1555;
	}
	tc_env(RETRO_ENVIRONMENT_SET_PIXEL_FORMAT, &tc_fmt);
	tc_kcb.callback = tc_key;
	tc_env(RETRO_ENVIRONMENT_SET_KEYBOARD_CALLBACK, &tc_kcb);
}

void retro_deinit(void)
{
}

void retro_get_system_info(struct retro_system_info *i)
{
	memset(i, 0, sizeof *i);
	i->library_name = "testcore";
	i->library_version = "0.1";
	i->valid_extensions = "";
	i->need_fullpath = false;
}

void retro_get_system_av_info(struct retro_system_av_info *i)
{
	memset(i, 0, sizeof *i);
	i->geometry.base_width = 320;
	i->geometry.base_height = 200;
	i->geometry.max_width = 320;
	i->geometry.max_height = 240;
	i->geometry.aspect_ratio = 4.0f / 3;
	i->timing.fps = 60;
	i->timing.sample_rate = 44100;
}

void retro_set_controller_port_device(unsigned p, unsigned d)
{
	(void)p;
	(void)d;
}

bool retro_load_game(const struct retro_game_info *g)
{
	(void)g;
	return true;
}

void retro_unload_game(void)
{
}

void retro_reset(void)
{
	tc_n = 0;
}

/* Pack one pixel in the format asked for. */
void tc_put(unsigned char *p, int r, int g, int b)
{
	if (tc_fmt == RETRO_PIXEL_FORMAT_XRGB8888) {
		p[0] = (unsigned char)b;
		p[1] = (unsigned char)g;
		p[2] = (unsigned char)r;
		p[3] = 0;
	} else {
		unsigned v = tc_fmt == RETRO_PIXEL_FORMAT_RGB565 ? (unsigned)((r >> 3) << 11 | (g >> 2) << 5 | b >> 3)
								 : (unsigned)((r >> 3) << 10 | (g >> 3) << 5 | b >> 3);

		p[0] = (unsigned char)(v & 255);
		p[1] = (unsigned char)(v >> 8);
	}
}

void retro_run(void)
{
	int bpp = tc_fmt == RETRO_PIXEL_FORMAT_XRGB8888 ? 4 : 2, x, y, k, i;
	size_t pitch = (size_t)tc_w * bpp + 8;
	unsigned char *f = calloc(pitch, (size_t)tc_h);
	int16_t a[735 * 2];
	struct retro_variable v;
	int bx = (int)(tc_n * 3 % (unsigned long)(tc_w - 20));
	int keys = 0, left = 0, mx, my, mb;

	tc_poll();
	if (tc_n == 120) {
		struct retro_game_geometry g;

		tc_h = 240;
		memset(&g, 0, sizeof g);
		g.base_width = 320;
		g.base_height = 240;
		g.max_width = 320;
		g.max_height = 240;
		tc_env(RETRO_ENVIRONMENT_SET_GEOMETRY, &g);
		free(f);
		f = calloc((size_t)tc_w * bpp + 8, (size_t)tc_h);
		pitch = (size_t)tc_w * bpp + 8;
	}
	v.key = "testcore_tone";
	v.value = 0;
	if (tc_env(RETRO_ENVIRONMENT_GET_VARIABLE, &v) && v.value)
		tc_tone = atof(v.value);
	for (k = 0; k < 512; k++)
		keys += tc_inp(0, RETRO_DEVICE_KEYBOARD, 0, (unsigned)k) ? 1 : 0;
	tc_nkeys = (unsigned long)keys;
	left = tc_inp(0, RETRO_DEVICE_KEYBOARD, 0, RETROK_LEFT);
	mx = tc_inp(0, RETRO_DEVICE_POINTER, 0, RETRO_DEVICE_ID_POINTER_X);
	my = tc_inp(0, RETRO_DEVICE_POINTER, 0, RETRO_DEVICE_ID_POINTER_Y);
	mb = tc_inp(0, RETRO_DEVICE_POINTER, 0, RETRO_DEVICE_ID_POINTER_PRESSED);
	for (y = 0; y < tc_h; y++)
		for (x = 0; x < tc_w; x++)
			tc_put(f + y * pitch + (size_t)x * bpp, x * 255 / tc_w, y * 255 / tc_h, 96);
	for (y = 90; y < 110; y++)
		for (x = bx; x < bx + 20; x++)
			tc_put(f + y * pitch + (size_t)x * bpp, 255, 255, 0);
	for (i = 0; i < keys && i < 30; i++)
		for (y = 4; y < 12; y++)
			for (x = 4 + i * 10; x < 12 + i * 10; x++)
				tc_put(f + y * pitch + (size_t)x * bpp, 255, 0, 0);
	if (left)
		for (y = 16; y < 24; y++)
			for (x = 4; x < 12; x++)
				tc_put(f + y * pitch + (size_t)x * bpp, 0, 255, 0);
	if (mb)
		for (y = 16; y < 24; y++)
			for (x = 20; x < 28; x++)
				tc_put(f + y * pitch + (size_t)x * bpp, 0, 128, 255);
	tc_shot = (unsigned)(mx < 0) + (unsigned)(my < 0);
	for (i = 0; i < 735; i++) {
		int16_t s = (int16_t)(8000 * sin(tc_phase));

		a[i * 2] = a[i * 2 + 1] = s;
		tc_phase += 2 * 3.14159265358979 * tc_tone / 44100;
	}
	tc_aud(a, 735);
	tc_vid(f, (unsigned)tc_w, (unsigned)tc_h, pitch);
	free(f);
	tc_n++;
}

size_t retro_serialize_size(void)
{
	return sizeof tc_n + sizeof tc_nkeys;
}

bool retro_serialize(void *d, size_t n)
{
	if (n < sizeof tc_n + sizeof tc_nkeys)
		return false;
	memcpy(d, &tc_n, sizeof tc_n);
	memcpy((char *)d + sizeof tc_n, &tc_nkeys, sizeof tc_nkeys);
	return true;
}

bool retro_unserialize(const void *d, size_t n)
{
	if (n < sizeof tc_n + sizeof tc_nkeys)
		return false;
	memcpy(&tc_n, d, sizeof tc_n);
	return true;
}

