#!/bin/bash
# Turns a screen recording of the dashboard into demo/claude-os.gif for the README.
# Needs ffmpeg (brew install ffmpeg). Record with: claude-os --mask, then Cmd+Shift+5 on macOS.
# Usage: bash demo/dashboard-gif.sh ~/Desktop/recording.mov
set -euo pipefail

in="${1:?usage: bash demo/dashboard-gif.sh <recording.mov>}"
out="$(cd "$(dirname "$0")" && pwd)/claude-os.gif"
pal="$(mktemp "${TMPDIR:-/tmp}/claude-os-palette.XXXXXX").png"
# 10 seconds at most, 15 frames a second, 1200 px wide: small enough for a README.
f="fps=15,scale=1200:-1:flags=lanczos"

ffmpeg -v error -y -t 10 -i "$in" -vf "$f,palettegen=stats_mode=diff" "$pal"
ffmpeg -v error -y -t 10 -i "$in" -i "$pal" -lavfi "$f [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=4" "$out"
ls -lh "$out"
