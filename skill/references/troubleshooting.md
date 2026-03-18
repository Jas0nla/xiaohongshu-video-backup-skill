# Troubleshooting

## GreenVideo parse failures

- Retry single failures one by one if batch mode times out.
- Treat `playwright-cli open` timeouts as tool-level noise before assuming the URL is invalid.
- Use a longer per-item wait window for older links. `45` seconds worked better than shorter waits.

## Naming

- Name videos with the parsed Xiaohongshu title, then append `.mp4`.
- Replace filesystem-illegal characters with `_` only when needed.

## Note generation

- `whisper --model turbo --language Chinese` is a reasonable default.
- CPU transcription is much slower than video download. Prefer running it in the background for large folders.
- Generate notes in a separate directory with the same basename as the video.
