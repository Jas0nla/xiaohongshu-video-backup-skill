#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path


def sanitize(title: str) -> str:
    title = re.sub(r'[\\/:*?"<>|]', "_", title).strip()
    title = re.sub(r"\s+", " ", title)
    return title[:180] or "untitled"


def parse_result(stdout: str) -> dict:
    match = re.search(r"### Result\n(.*?)(?:\n### Ran Playwright code|\Z)", stdout, re.S)
    if not match:
        raise RuntimeError("could not parse Playwright result block")
    return json.loads(match.group(1).strip())


def build_runtime_env() -> dict:
    env = os.environ.copy()
    path_parts = env.get("PATH", "").split(":") if env.get("PATH") else []
    common_paths = [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
        str(Path.home() / "miniconda3" / "bin"),
    ]
    merged = []
    for item in common_paths + path_parts:
        if item and item not in merged:
            merged.append(item)
    env["PATH"] = ":".join(merged)
    env["CODEX_HOME"] = str(Path.home() / ".codex")
    return env


def resolve_share_url(url: str, timeout_seconds: int) -> str:
    if "xhslink.com" not in url:
        return url

    share_url = url.replace("http://xhslink.com", "https://xhslink.com")
    result = subprocess.run(
        [
            "curl",
            "-Ls",
            "--max-time",
            str(timeout_seconds),
            "-o",
            "/dev/null",
            "-w",
            "%{url_effective}",
            share_url,
        ],
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 5,
        check=True,
    )
    final_url = result.stdout.strip() or share_url
    return final_url


def resolve_video(pwcli: str, env: dict, url: str, timeout_seconds: int) -> dict:
    js = f"""async () => {{
      const url = {json.dumps(url, ensure_ascii=False)};
      const input = document.querySelector('textarea, input[type=text]');
      input.value = url;
      input.dispatchEvent(new Event('input', {{ bubbles: true }}));
      const startBtn = Array.from(document.querySelectorAll('button')).find(
        b => b.innerText.trim() === '开始'
      );
      startBtn.click();
      const start = Date.now();
      while (Date.now() - start < {timeout_seconds * 1000}) {{
        const state = window.__NUXT__.pinia.video;
        const info = state && state.videoExtractInfo;
        const items = (info && info.videoItemVoList) || [];
        const item = items.find(x => x.fileType === 'video' && (x.downloadUrl || x.baseUrl));
        if (state && state.inputUrl === url && info && info.displayTitle && item) {{
          return {{
            title: info.displayTitle,
            downloadUrl: item.downloadUrl || item.baseUrl
          }};
        }}
        await new Promise(r => setTimeout(r, 500));
      }}
      return {{ error: "timeout", url }};
    }}"""
    subprocess.run(
        [pwcli, "open", "https://greenvideo.cc/"],
        env=env,
        capture_output=True,
        text=True,
        timeout=40,
        check=True,
    )
    result = subprocess.run(
        [pwcli, "eval", js],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 30,
        check=True,
    )
    parsed = parse_result(result.stdout)
    if parsed.get("error"):
        raise RuntimeError(parsed["error"])
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--failures-file", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    args = parser.parse_args()

    urls = [line.strip() for line in Path(args.urls_file).read_text().splitlines() if line.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    failures = []

    pwcli = str(Path.home() / ".codex/skills/playwright/scripts/playwright_cli.sh")
    env = build_runtime_env()

    for index, url in enumerate(urls, 1):
        print(f"[{index}/{len(urls)}] {url}", flush=True)
        try:
            print("stage: resolving-share-url", flush=True)
            effective_url = resolve_share_url(url, min(args.timeout_seconds, 20))
            if effective_url != url:
                print(f"resolved-url: {effective_url}", flush=True)
            print("stage: extracting-video", flush=True)
            info = resolve_video(pwcli, env, effective_url, args.timeout_seconds)
            title = sanitize(info["title"])
            target = output_dir / f"{title}.mp4"
            print(f"stage: downloading-file -> {target.name}", flush=True)
            subprocess.run(
                ["curl", "-L", info["downloadUrl"], "-o", str(target)],
                check=True,
                env=env,
                timeout=240,
            )
            print(f"saved: {target.name}", flush=True)
        except Exception as exc:
            failures.append({"url": url, "error": str(exc)})
            print(f"failed: {exc}", flush=True)
        time.sleep(args.sleep_seconds)

    Path(args.failures_file).write_text(json.dumps(failures, ensure_ascii=False, indent=2))
    print(f"remaining_failures={len(failures)}", flush=True)


if __name__ == "__main__":
    main()
