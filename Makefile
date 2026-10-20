HIBR ?= ../hibr
CC ?= gcc
CFLAGS ?= -O2 -g -Wall
INC = -Imods/retro -I$(HIBR)/include
B = build

.PHONY: all check clean
all: $(B)/testcore.so $(B)/rl_harness

$(B):
	mkdir -p $(B)

$(B)/testcore.so: tests/testcore.c mods/retro/libretro.h | $(B)
	$(CC) $(CFLAGS) -fPIC -shared -Imods/retro -o $@ tests/testcore.c -lm

$(B)/rl_harness: tests/rl_harness.c tests/shim.c mods/retro/rl.c mods/retro/rl.h mods/retro/ra.c mods/retro/ra.h | $(B)
	$(CC) $(CFLAGS) $(INC) -o $@ tests/rl_harness.c tests/shim.c mods/retro/rl.c mods/retro/ra.c -ldl -lpthread -lm

check: all
	HIBR_RETRO_AUDIO=wav:$(B)/harness.wav $(B)/rl_harness $(B)/testcore.so xrgb8888
	HIBR_RETRO_AUDIO=wav:$(B)/harness.wav $(B)/rl_harness $(B)/testcore.so rgb565
	HIBR_RETRO_AUDIO=wav:$(B)/harness.wav $(B)/rl_harness $(B)/testcore.so 0rgb1555

clean:
	rm -rf $(B)
