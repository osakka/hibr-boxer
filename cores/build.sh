#!/bin/sh
# Build the libretro cores from the revisions in PINS: build.sh WORKDIR OUTDIR (WORKDIR must be new or empty).
# A pin is a tag and the commit that tag must be: the clone is refused if it is anything else. Its url may be
# a list, tried in turn, and CORES_URL_<name> (CORES_URL_dosbox_pure) is tried first, for a mirror of your own.
# OUTDIR gets each core, <core>.build (a record of what was built, from which source, and with what), and the
# pinned source as a tarball, which is what the packages offer under the GPL.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
work=${1:?workdir}
out=${2:?outdir}
mkdir -p "$work" "$out"
while read -r name urls tag commit; do
	case $name in '#'*|'') continue ;; esac
	eval "mirror=\${CORES_URL_$name:-}"
	got= used=
	for url in $mirror $(echo "$urls" | tr ',' ' '); do
		rm -rf "$work/$name"
		git clone --depth 1 --branch "$tag" "$url" "$work/$name" || continue
		got=$(git -C "$work/$name" rev-parse HEAD)
		[ "$got" = "$commit" ] && { used=$url; break; }
		echo "$name: $url has $tag at $got, expected $commit" >&2
	done
	[ -n "$used" ] || { echo "$name: no url gave $tag at $commit" >&2; exit 1; }
	case $name in
	dosbox_pure)
		make -C "$work/dosbox_pure" -j2
		grep -aq "$tag" "$work/dosbox_pure/dosbox_pure_libretro.so" || { echo "$name: the build does not carry its version $tag" >&2; exit 1; }
		cp "$work/dosbox_pure/dosbox_pure_libretro.so" "$out/"
		src=dosbox-pure-$tag-$(echo "$commit" | cut -c1-7).tar.gz
		git -C "$work/dosbox_pure" archive --format=tar --prefix="dosbox-pure-$tag/" "$commit" | gzip -9n > "$out/$src"
		{
			echo "core: $name"
			echo "source: $used"
			echo "tag: $tag"
			echo "commit: $commit"
			echo "compiler: $(${CXX:-c++} --version | head -n 1)"
			echo "sha256: $(sha256sum "$out/dosbox_pure_libretro.so" | cut -d' ' -f1)"
			echo "source-archive: $src"
			echo "source-sha256: $(sha256sum "$out/$src" | cut -d' ' -f1)"
		} > "$out/dosbox_pure_libretro.so.build"
		;;
	esac
done < "$here/PINS"
