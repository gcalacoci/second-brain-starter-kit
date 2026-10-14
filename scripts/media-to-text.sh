#!/usr/bin/env bash
# media-to-text.sh — Extract text from media files for Second Brain ingestion.
#
# Usage: media-to-text.sh <file> [outdir]
#   Converts: pdf -> text, docx -> markdown, audio/video -> text (if whisper installed)
#   Images:   not converted (agent reads them directly with its vision capability)
#   Output:   <outdir>/<basename>.txt (or .md) — original file is never modified
#
# Requirements (all optional, checked at runtime):
#   pdftotext (poppler-utils)  — PDFs
#   pandoc                     — DOCX
#   whisper                    — audio/video transcription
set -uo pipefail

FILE="${1:-}"
OUTDIR="${2:-}"

if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "usage: media-to-text.sh <file> [outdir]" >&2
  exit 1
fi

BASE="$(basename "$FILE")"
STEM="${BASE%.*}"
EXT="${BASE##*.}"
EXT_LC="$(echo "$EXT" | tr '[:upper:]' '[:lower:]')"
OUTDIR="${OUTDIR:-$(dirname "$FILE")}"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/$STEM.txt"

case "$EXT_LC" in
  pdf)
    if command -v pdftotext >/dev/null 2>&1; then
      pdftotext -layout "$FILE" "$OUT" && echo "OK: $OUT" && exit 0
    else
      echo "SKIP: pdftotext not installed (poppler-utils). Install: apt install poppler-utils | brew install poppler" >&2
      exit 3
    fi
    ;;
  docx)
    if command -v pandoc >/dev/null 2>&1; then
      pandoc "$FILE" -t markdown -o "${OUT%.txt}.md" && echo "OK: ${OUT%.txt}.md" && exit 0
    else
      echo "SKIP: pandoc not installed. Install: apt install pandoc | brew install pandoc" >&2
      exit 3
    fi
    ;;
  txt|md|markdown)
    cp "$FILE" "$OUT" && echo "OK: $OUT" && exit 0
    ;;
  mp3|wav|m4a|mp4|ogg|flac|webm)
    if command -v whisper >/dev/null 2>&1; then
      # whisper writes <stem>.txt next to the input by default; redirect to OUTDIR
      (cd "$(dirname "$FILE")" && whisper "$FILE" --output_format txt --output_dir "$OUTDIR") \
        && echo "OK: $OUTDIR/$STEM.txt" && exit 0
    else
      echo "SKIP: whisper not installed. Install: pip install openai-whisper (needs ffmpeg)" >&2
      exit 3
    fi
    ;;
  png|jpg|jpeg|gif|webp|bmp|heic)
    echo "VISION: images are not converted — the agent reads them directly during ingest (multimodal Read)." >&2
    exit 2
    ;;
  *)
    echo "SKIP: unsupported extension .$EXT_LC" >&2
    exit 3
    ;;
esac
