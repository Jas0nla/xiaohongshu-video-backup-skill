#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path


def normalize_text(text: str) -> str:
    text = re.sub(r"\[[0-9:. \-\->]+\]", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("请不吝点赞订阅", "")
    return text.strip()


def chunk_sentences(text: str):
    parts = re.split(r"(?<=[。！？])", text)
    parts = [p.strip() for p in parts if p.strip()]
    chunks = []
    current = ""
    for part in parts:
        if len(current) + len(part) <= 90:
            current += part
        else:
            if current:
                chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks


def build_note(title: str, transcript: str) -> str:
    cleaned = normalize_text(transcript)
    bullets = chunk_sentences(cleaned)
    body = "\n".join(f"- {item}" for item in bullets) if bullets else "- 暂无可用转写内容"
    return f"# {title}\n\n## 内容笔记\n{body}\n"


def transcribe(video_path: Path, transcripts_dir: Path) -> Path:
    txt_path = transcripts_dir / f"{video_path.stem}.txt"
    if txt_path.exists() and txt_path.stat().st_size > 0:
        return txt_path
    subprocess.run(
        [
            "whisper",
            str(video_path),
            "--language",
            "Chinese",
            "--model",
            "turbo",
            "--task",
            "transcribe",
            "--output_format",
            "txt",
            "--output_dir",
            str(transcripts_dir),
        ],
        check=True,
    )
    return txt_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos-dir", required=True)
    parser.add_argument("--transcripts-dir", required=True)
    parser.add_argument("--notes-dir", required=True)
    args = parser.parse_args()

    videos_dir = Path(args.videos_dir)
    transcripts_dir = Path(args.transcripts_dir)
    notes_dir = Path(args.notes_dir)
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)

    for video in sorted(videos_dir.glob("*.mp4")):
        txt_path = transcribe(video, transcripts_dir)
        transcript = txt_path.read_text(encoding="utf-8").strip()
        note = build_note(video.stem, transcript)
        md_path = notes_dir / f"{video.stem}.md"
        md_path.write_text(note, encoding="utf-8")
        print(f"done: {md_path.name}", flush=True)


if __name__ == "__main__":
    main()
