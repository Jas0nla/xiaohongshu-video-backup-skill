---
name: xiaohongshu-video-backup
description: Download Xiaohongshu videos through GreenVideo, retry failed parses, name files by the parsed Xiaohongshu title, and generate same-name text notes from downloaded MP4s. Use when Codex needs to back up Xiaohongshu video links to local files, resume interrupted download batches, or turn a folder of downloaded Xiaohongshu videos into transcript-based Markdown notes.
---

# Xiaohongshu Video Backup

## Workflow

1. Collect Xiaohongshu note URLs into a plain text file, one URL per line.
2. Download videos through GreenVideo with the bundled downloader script.
3. Inspect the failures file and rerun if any entries remain.
4. Generate transcript-based Markdown notes for the downloaded MP4 files.

## Download Videos

Use the bundled downloader for GreenVideo-based resolution and title naming:

```bash
python3 scripts/download_videos.py \
  --urls-file /abs/path/urls.txt \
  --output-dir /abs/path/xhs_videos \
  --failures-file /abs/path/download_failures.json
```

Expected behavior:

- Open `greenvideo.cc` with Playwright CLI.
- Parse each Xiaohongshu URL through the page's `window.__NUXT__.pinia` state.
- Save the MP4 using the parsed Xiaohongshu title as the basename.
- Write unresolved URLs to the failures file for later retry.

## Resume Interrupted Runs

- Re-run the downloader against a smaller URLs file containing only failed links.
- Prefer single-item retries if batch parsing starts timing out.
- Read [references/troubleshooting.md](references/troubleshooting.md) before assuming failed URLs are invalid.

## Generate Same-Name Notes

Use the bundled note generator after videos are downloaded:

```bash
python3 scripts/generate_notes.py \
  --videos-dir /abs/path/xhs_videos \
  --transcripts-dir /abs/path/xhs_transcripts \
  --notes-dir /abs/path/xhs_notes
```

Expected behavior:

- Transcribe each MP4 with `whisper --model turbo --language Chinese`.
- Save raw transcripts as `.txt`.
- Save a same-basename Markdown note with a short bullet-style content recap.

## Notes

- Keep video files and Markdown notes in separate directories, but preserve the same basename.
- For large folders, start note generation in the background because CPU transcription is slow.
- If a user wants higher-quality editorial notes instead of transcript-style notes, generate transcripts first, then rewrite the Markdown files afterward.
