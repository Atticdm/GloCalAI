#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR=${1:-assets}
mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$OUTPUT_DIR/source.mp4"

echo "Generating demo video at $OUTPUT_FILE"
ffmpeg -y \
  -f lavfi -i color=c=#111111:s=1920x1080:r=25:d=8 \
  -f lavfi -i sine=frequency=440:duration=8 \
  -vf "drawtext=text='DEMO SOURCE':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2" \
  -c:v libx264 -preset veryfast -crf 22 \
  -c:a aac -b:a 160k \
  "$OUTPUT_FILE"

echo "Test video ready"
