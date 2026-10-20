#!/bin/sh
# Build the libretro cores from the revisions in PINS: build.sh WORKDIR OUTDIR (WORKDIR must be new or empty).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
work=${1:?workdir}
out=${2:?outdir}
mkdir -p "$work" "$out"
while read -r name url tag commit; do
	case $name in '#'*|'') continue ;; esac
	git clone --depth 1 --branch "$tag" "$url" "$work/$name"
	got=$(git -C "$work/$name" rev-parse HEAD)
	[ "$got" = "$commit" ] || { echo "$name: $tag is $got, expected $commit" >&2; exit 1; }
	case $name in
	scummvm)
		d=$work/scummvm/backends/platform/libretro
		make -C "$d" -j"$(nproc)"
		make -C "$d" scummvm.zip
		strip -o "$out/scummvm_libretro.so" "$d/scummvm_libretro.so"
		cp "$d/scummvm.zip" "$out/"
		;;
	dosbox_pure)
		make -C "$work/dosbox_pure" -j2
		cp "$work/dosbox_pure/dosbox_pure_libretro.so" "$out/"
		;;
	esac
done < "$here/PINS"
