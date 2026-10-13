# Raw Sources — Immutable

This folder holds the original, immutable sources you ingest. Once a file is here,
it is never edited or deleted. It is the source of truth.

## What goes here

- PDFs, markdown articles, transcripts, exported notes
- Downloaded web pages from Obsidian Web Clipper
- Raw transcripts from meetings

## Naming

Use kebab-case descriptive slugs: `karpathy-llm-wiki-2026-04-04.md`. Keep original
extensions for non-markdown files.

## Rules

- NEVER edit files in this folder. Create a page in `raw/pages/` instead.
- If you need to correct a source, save a new version with a new name and re-ingest.
- The `processed.md` registry tracks which raw files have been ingested.

## Examples

- `karpathy-llm-wiki-2026-04-04.md`
- `q1-pricing-strategy-meeting-2026-03-12.md`
- `article-deep-universal-learning-2026-01-20.pdf`
