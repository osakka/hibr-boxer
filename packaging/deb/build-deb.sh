#!/bin/sh
# Build the hibr-retro Debian package: the retro module and the DOSBox Pure core.
#
#   packaging/deb/build-deb.sh CORES [outdir]      default outdir: build/deb
#
# CORES is a folder holding dosbox_pure_libretro.so, as cores/build.sh leaves it. The module is
# built here, with tcc, against a hibr tree (HIBR, default ../hibr). Like hibr's own package it
# carries no applications: boxer and boxerplay come from the catalogue.
#
# The module is built against the hibr tree's ABI, which a module must match exactly, and hibr's
# package says nothing about its ABI, so this depends on the hibr release it was built and tested
# with, read from that tree, and a newer hibr needs a rebuild.

set -eu

SRC=$(cd "$(dirname "$0")/../.." && pwd)
CORES=${1:?usage: build-deb.sh CORES [outdir]}
OUT=${2:-$SRC/build/deb}
HIBR=${HIBR:-$SRC/../hibr}
VER=${HR_VERSION:-0.1.6}
REV=${DEB_REVISION:-1}
ARCH=$(dpkg --print-architecture)
PKG=hibr-retro_${VER}-${REV}_${ARCH}
STAGE=$OUT/$PKG
CORE=$CORES/dosbox_pure_libretro.so

[ -f "$CORE" ] || { echo "build-deb: no $CORE" >&2; exit 1; }
HVER=$(sed -n 's/^#define HIBR_VER "\(.*\)"/\1/p' "$HIBR/include/hibr.h")
HABI=$(sed -n 's/^#define HIBR_ABI \([0-9]*\)u.*/\1/p' "$HIBR/include/hibr.h")
[ -n "$HVER" ] && [ -n "$HABI" ] || { echo "build-deb: no hibr tree at $HIBR" >&2; exit 1; }
# The lowest hibr the package asks for: the release installed here when there is one, since a tree is
# often ahead of the last release and a package must not ask for what nobody can install.
HMIN=${HR_HIBR_MIN:-$(dpkg-query -W -f='${Version}' hibr 2> /dev/null | sed 's/-.*//')}
HMIN=${HMIN:-$HVER}
echo "== building hibr-retro $VER for $ARCH, against hibr $HVER (abi $HABI), asking for hibr >= $HMIN"

cd "$SRC"
make -s HIBR="$HIBR" build/retro.so
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/lib/hibr/cores" "$STAGE/usr/share/doc/hibr-retro"
install -m 755 build/retro.so "$STAGE/usr/lib/hibr/retro.so"
install -m 755 "$CORE" "$STAGE/usr/lib/hibr/cores/dosbox_pure_libretro.so"
[ -f "$CORE.build" ] && install -m 644 "$CORE.build" "$STAGE/usr/share/doc/hibr-retro/dosbox_pure_libretro.build"
strip --strip-unneeded "$STAGE/usr/lib/hibr/retro.so" "$STAGE/usr/lib/hibr/cores/dosbox_pure_libretro.so"

glibc=$(for f in "$STAGE"/usr/lib/hibr/retro.so "$STAGE"/usr/lib/hibr/cores/*.so; do
	objdump -T "$f"
done | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -uV | tail -1)
size=$(du -sk "$STAGE/usr" | cut -f1)

PIN=$(grep '^dosbox_pure ' cores/PINS)
set -- $PIN
DBURL=${2%%,*} DBTAG=$3 DBCOMMIT=$4
[ -f "$CORE.build" ] && DBURL=$(sed -n 's/^source: //p' "$CORE.build")
cat > "$STAGE/usr/share/doc/hibr-retro/copyright" <<COPY
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: hibr-retro
Source: https://git.home.arpa/itdlabs/hibr-boxer

Files: usr/lib/hibr/retro.so
Copyright: osakka
License: MIT

Files: usr/lib/hibr/cores/dosbox_pure_libretro.so
Copyright: Bernhard Schelling and the DOSBox Team
License: GPL-2+
Comment: DOSBox Pure, built unmodified from $DBURL
 at tag $DBTAG, commit $DBCOMMIT, by cores/build.sh in the source above.
 That repository is the source of this binary, and dosbox_pure_libretro.build
 in this directory records exactly what was built. The full text of the GPL
 is in /usr/share/common-licenses/GPL-2.

Files: usr/lib/hibr/cores/dosbox_pure_libretro.so
Copyright: Dean Beeler, Jerome Fisher, Sergey V. Mikayev (Munt MT-32 emulation);
 Nuke.YKT (Nuked OPL3)
License: LGPL-2.1+
Comment: Parts of the core above. The full text of the LGPL is in
 /usr/share/common-licenses/LGPL-2.1.

License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
 associated documentation files (the "Software"), to deal in the Software without restriction,
 including without limitation the rights to use, copy, modify, merge, publish, distribute,
 sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions: The above copyright notice and this
 permission notice shall be included in all copies or substantial portions of the Software. THE
 SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.
COPY
install -m 644 mods/retro/README.md "$STAGE/usr/share/doc/hibr-retro/README.md"
gzip -9n "$STAGE/usr/share/doc/hibr-retro/README.md"

cat > "$STAGE/DEBIAN/control" <<CTL
Package: hibr-retro
Version: $VER-$REV
Architecture: $ARCH
Maintainer: osakka <osakka@gmail.com>
Installed-Size: $size
Depends: hibr (>= $HMIN), libc6 (>= $glibc), libstdc++6, libgcc-s1
Suggests: libpulse0 | libasound2 | libasound2t64
Section: games
Priority: optional
Homepage: https://git.home.arpa/itdlabs/hibr-boxer
Description: libretro frontend for hibr, with the DOSBox Pure core
 The retro module runs a libretro core inside hibr's own shell and draws
 its picture with hibr's renderer: pixels where the terminal takes them,
 half blocks where it does not. The package brings DOSBox Pure, which
 runs DOS games. The applications that use it, boxer (a shelf of games)
 and boxerplay, come from the hibr catalogue: catalogue install boxer.
CTL

fakeroot dpkg-deb --build --root-owner-group "$STAGE" "$OUT/$PKG.deb" > /dev/null
rm -rf "$STAGE"
echo "== $OUT/$PKG.deb"
