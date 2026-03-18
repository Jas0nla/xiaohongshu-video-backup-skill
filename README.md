# Xiaohongshu Video Backup Skill

Codex Skill for backing up Xiaohongshu video links through GreenVideo, retrying failed downloads, and generating same-name transcript notes from downloaded MP4 files.

## What It Includes

- A reusable Codex Skill under [`skill/`](./skill)
- A downloader script that:
  - reads Xiaohongshu note URLs from a text file
  - resolves video URLs through `greenvideo.cc`
  - names each video by the parsed Xiaohongshu title
  - records failed links for retry
- A note generator that:
  - transcribes downloaded videos with `whisper`
  - saves raw `.txt` transcripts
  - saves same-name `.md` recap notes
- A static GitHub Pages site under [`docs/`](./docs)

## Skill Path

The Codex Skill lives at:

`skill/SKILL.md`

## Quick Start

Download videos:

```bash
python3 skill/scripts/download_videos.py \
  --urls-file /abs/path/urls.txt \
  --output-dir /abs/path/xhs_videos \
  --failures-file /abs/path/download_failures.json
```

Generate same-name notes:

```bash
python3 skill/scripts/generate_notes.py \
  --videos-dir /abs/path/xhs_videos \
  --transcripts-dir /abs/path/xhs_transcripts \
  --notes-dir /abs/path/xhs_notes
```

## GitHub Pages

The site entry is:

`docs/index.html`

You can publish it with GitHub Pages by serving from the `docs/` folder on the `main` branch.
