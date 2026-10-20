#ifndef HIBR_RL_H
#define HIBR_RL_H

#include <stddef.h>
#include <stdint.h>

/* A libretro core driven on a thread of its own. This knows nothing of the shell or of any display: the
   module wraps it, and a test harness can run it alone. Every call into the core, from retro_set_environment
   to retro_deinit, is made on the one thread rl_open starts, since many cores insist on it. */

typedef struct rl rl;

/* What a running core says about itself, read without stopping it. */
typedef struct rl_st rl_st;
struct rl_st {
	int w, h, paused, ended;
	double fps, rate, aspect;
	unsigned long frames, seq;
	char *name, *ver, *err, *sound;
};

/* Load a core and its game and start running it; opts is a null-terminated list of key=value core options. */
rl *rl_open(const char *core, const char *game, const char *sysdir, const char *savedir,
	    const char *const *opts, char **err);

/* Stop the core, give back everything, and free the player. */
void rl_close(rl *r);

/* A descriptor that is readable whenever a new frame has been made; rl_wake empties it. */
int rl_fd(rl *r);
void rl_wake(rl *r);

/* The latest frame as RGB triples, a copy the caller keeps until its next rl_lock, so drawing it never holds up the
   core; null while there is none yet. rl_unlock is kept for symmetry and does nothing. */
const unsigned char *rl_lock(rl *r, int *w, int *h, unsigned long *seq);
void rl_unlock(rl *r);

/* Fill in what the core says about itself; the strings are the caller's to free with rl_stfree. */
void rl_info(rl *r, rl_st *st);
void rl_stfree(rl_st *st);

/* A key as the core's own RETROK_ code: pressed or let go, with the character it types and the modifiers. */
void rl_key(rl *r, unsigned code, uint32_t chr, unsigned mods, int down);

/* A key held for ms after its latest report, so a terminal that cannot say release still lets go. */
void rl_hold(rl *r, unsigned code, uint32_t chr, unsigned mods, int ms);

/* The pointer, in the core's own -0x7fff..0x7fff over the picture, and the buttons: 1 left, 2 right, 4 middle. */
void rl_pointer(rl *r, int x, int y, int buttons, int wheel);

/* The joypad, one bit per RETRO_DEVICE_ID_JOYPAD_ button. */
void rl_pad(rl *r, unsigned mask);

/* Pause or resume; reset the game; set a core option by key. Each is done on the core's thread, and waited for. */
int rl_pause(rl *r, int on);
int rl_reset(rl *r);
int rl_option(rl *r, const char *key, const char *val);

/* Save the game's state into a new buffer, or put one back; 0 when it worked. */
unsigned char *rl_save(rl *r, size_t *n);
int rl_load(rl *r, const unsigned char *buf, size_t n);

#endif
