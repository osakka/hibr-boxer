HIBR ?= ../hibr
CC = tcc
CFLAGS = -g -Wall
INC = -Imods/retro -I$(HIBR)/include
B = build

.PHONY: all check check-retro check-boxer clean
all: $(B)/testcore.so $(B)/rl_harness

$(B):
	mkdir -p $(B)

$(B)/testcore.so: tests/testcore.c mods/retro/libretro.h | $(B)
	$(CC) $(CFLAGS) -fPIC -shared -Imods/retro -o $@ tests/testcore.c -lm

$(B)/rl_harness: tests/rl_harness.c tests/shim.c mods/retro/rl.c mods/retro/rl.h mods/retro/ra.c mods/retro/ra.h | $(B)
	$(CC) $(CFLAGS) $(INC) -o $@ tests/rl_harness.c tests/shim.c mods/retro/rl.c mods/retro/ra.c -ldl -lpthread -lm

$(B)/rl_shot: tests/rl_shot.c tests/shim.c mods/retro/rl.c mods/retro/rl.h mods/retro/ra.c mods/retro/ra.h | $(B)
	$(CC) $(CFLAGS) $(INC) -o $@ tests/rl_shot.c tests/shim.c mods/retro/rl.c mods/retro/ra.c -ldl -lpthread -lm

check: all
	HIBR_RETRO_AUDIO=wav:$(B)/harness.wav $(B)/rl_harness $(B)/testcore.so xrgb8888
	HIBR_RETRO_AUDIO=wav:$(B)/harness.wav $(B)/rl_harness $(B)/testcore.so rgb565
	HIBR_RETRO_AUDIO=wav:$(B)/harness.wav $(B)/rl_harness $(B)/testcore.so 0rgb1555

check-retro: all
	python3 -I tests/retro.py

check-boxer: $(B)/retro.so $(B)/testcore.so $(B)/rl_shot
	python3 tests/boxer.py

clean:
	rm -rf $(B)

RETRO_SRC = mods/retro/retro.c mods/retro/rl.c mods/retro/ra.c
$(B)/retro.so: $(RETRO_SRC) mods/retro/rl.h mods/retro/ra.h mods/retro/display.h | $(B)
	$(CC) $(CFLAGS) -fPIC -shared $(INC) -o $@ $(RETRO_SRC) -ldl -lpthread
all: $(B)/retro.so
