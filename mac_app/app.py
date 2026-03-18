#!/usr/bin/env python3
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional


APP_NAME = "Xiaohongshu Video Backup"
URL_PATTERN = re.compile(r"https?://[^\s]+")


def resolve_root() -> Path:
    env_root = os.environ.get("XHS_BACKUP_APP_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if (candidate / "skill" / "scripts").exists():
            return candidate

    if getattr(sys, "frozen", False):
        candidate = Path(sys.executable).resolve().parents[1] / "Resources" / "app"
        if (candidate / "skill" / "scripts").exists():
            return candidate

    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "skill" / "scripts").exists():
            return parent
    raise RuntimeError("Could not locate app root containing skill/scripts.")


def resolve_workspace() -> Path:
    env_workspace = os.environ.get("XHS_BACKUP_WORKSPACE")
    if env_workspace:
        return Path(env_workspace).expanduser()
    return Path.home() / "Documents" / APP_NAME


ROOT = resolve_root()
DOWNLOAD_SCRIPT = ROOT / "skill" / "scripts" / "download_videos.py"
NOTES_SCRIPT = ROOT / "skill" / "scripts" / "generate_notes.py"
DEFAULT_WORKSPACE = resolve_workspace()


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
    env.setdefault("HOME", str(Path.home()))
    env.setdefault("CODEX_HOME", str(Path.home() / ".codex"))
    return env


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Xiaohongshu Video Backup")
        self.root.geometry("980x760")
        self.root.minsize(860, 680)

        self.log_queue = queue.Queue()
        self.busy = False

        self.urls_file_var = tk.StringVar(value=str(DEFAULT_WORKSPACE / "urls.txt"))
        self.output_dir_var = tk.StringVar(value=str(DEFAULT_WORKSPACE / "xhs_videos"))
        self.failures_file_var = tk.StringVar(
            value=str(DEFAULT_WORKSPACE / "download_failures.json")
        )
        self.transcripts_dir_var = tk.StringVar(
            value=str(DEFAULT_WORKSPACE / "xhs_transcripts")
        )
        self.notes_dir_var = tk.StringVar(value=str(DEFAULT_WORKSPACE / "xhs_notes"))
        self.status_var = tk.StringVar(value="准备好了。先选链接文件或直接用默认路径。")
        self.progress_label_var = tk.StringVar(value="当前没有运行中的任务。")
        self.progress_detail_var = tk.StringVar(value="")
        self.progress_value_var = tk.DoubleVar(value=0.0)
        self.current_task_total = 0
        self.current_task_done = 0

        self._build_ui()
        self._ensure_workspace()
        self.root.after(150, self._drain_log_queue)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=18)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Xiaohongshu Video Backup",
            font=("SF Pro Display", 24, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="选好链接文件，点按钮下载视频，再点按钮生成同名文字笔记。",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        body = ttk.Frame(self.root, padding=(18, 0, 18, 18))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(4, weight=1)

        urls_frame = ttk.LabelFrame(body, text="直接输入 URL", padding=16)
        urls_frame.grid(row=0, column=0, sticky="nsew")
        urls_frame.columnconfigure(0, weight=1)
        urls_frame.rowconfigure(1, weight=1)

        ttk.Label(
            urls_frame,
            text="支持一次粘贴多个小红书链接，一行一个。这里有内容时，会优先使用这里的链接下载。",
        ).grid(row=0, column=0, sticky="w")

        self.urls_text = tk.Text(
            urls_frame,
            wrap="word",
            height=8,
            relief="flat",
            padx=12,
            pady=12,
        )
        self.urls_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        paths = ttk.LabelFrame(body, text="路径设置", padding=16)
        paths.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        paths.columnconfigure(1, weight=1)

        self._add_path_row(paths, 0, "链接文件", self.urls_file_var, self.pick_urls_file)
        self._add_path_row(paths, 1, "视频目录", self.output_dir_var, self.pick_output_dir)
        self._add_path_row(
            paths, 2, "失败记录", self.failures_file_var, self.pick_failures_file
        )
        self._add_path_row(
            paths, 3, "转写目录", self.transcripts_dir_var, self.pick_transcripts_dir
        )
        self._add_path_row(paths, 4, "笔记目录", self.notes_dir_var, self.pick_notes_dir)

        actions = ttk.LabelFrame(body, text="操作", padding=16)
        actions.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        for index in range(5):
            actions.columnconfigure(index, weight=1)

        self.download_button = ttk.Button(
            actions, text="1. 下载视频", command=self.start_download
        )
        self.download_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.notes_button = ttk.Button(
            actions, text="2. 生成笔记", command=self.start_notes
        )
        self.notes_button.grid(row=0, column=1, sticky="ew", padx=8)

        ttk.Button(actions, text="打开工作目录", command=self.open_workspace).grid(
            row=0, column=2, sticky="ew", padx=8
        )
        ttk.Button(actions, text="查看失败记录", command=self.open_failures_file).grid(
            row=0, column=3, sticky="ew", padx=8
        )
        ttk.Button(actions, text="清空 URL 输入", command=self.clear_url_inputs).grid(
            row=0, column=4, sticky="ew", padx=(8, 0)
        )

        progress_frame = ttk.LabelFrame(body, text="任务进度", padding=16)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        progress_frame.columnconfigure(0, weight=1)

        ttk.Label(progress_frame, textvariable=self.progress_label_var).grid(
            row=0, column=0, sticky="w"
        )
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            variable=self.progress_value_var,
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(10, 8))
        ttk.Label(progress_frame, textvariable=self.progress_detail_var).grid(
            row=2, column=0, sticky="w"
        )

        log_frame = ttk.LabelFrame(body, text="运行日志", padding=12)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(16, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            height=24,
            bg="#14110f",
            fg="#f9efe2",
            insertbackground="#f9efe2",
            relief="flat",
            padx=14,
            pady=14,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(self.root, padding=(18, 0, 18, 18))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

    def _add_path_row(self, parent, row, label, variable, command) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky="ew", padx=12, pady=6
        )
        ttk.Button(parent, text="选择", command=command).grid(row=row, column=2, pady=6)

    def _ensure_workspace(self) -> None:
        DEFAULT_WORKSPACE.mkdir(parents=True, exist_ok=True)
        Path(self.output_dir_var.get()).mkdir(parents=True, exist_ok=True)
        Path(self.transcripts_dir_var.get()).mkdir(parents=True, exist_ok=True)
        Path(self.notes_dir_var.get()).mkdir(parents=True, exist_ok=True)
        urls_file = Path(self.urls_file_var.get())
        if not urls_file.exists():
            urls_file.write_text("", encoding="utf-8")

    def pick_urls_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 urls.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.urls_file_var.set(path)

    def pick_output_dir(self) -> None:
        self._pick_directory(self.output_dir_var, "选择视频保存目录")

    def pick_failures_file(self) -> None:
        path = filedialog.asksaveasfilename(
            title="选择失败记录文件",
            defaultextension=".json",
            initialfile=Path(self.failures_file_var.get()).name,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.failures_file_var.set(path)

    def pick_transcripts_dir(self) -> None:
        self._pick_directory(self.transcripts_dir_var, "选择转写目录")

    def pick_notes_dir(self) -> None:
        self._pick_directory(self.notes_dir_var, "选择笔记目录")

    def _pick_directory(self, variable: tk.StringVar, title: str) -> None:
        path = filedialog.askdirectory(title=title, mustexist=False)
        if path:
            variable.set(path)

    def log(self, message: str) -> None:
        self.log_queue.put(message)

    def get_inline_urls(self) -> list:
        raw = self.urls_text.get("1.0", "end").strip()
        if not raw:
            return []
        found = URL_PATTERN.findall(raw)
        urls = []
        seen = set()
        for item in found:
            candidate = item.strip().rstrip("，。；;！？!）)]}>\"'")
            if "xhslink.com" not in candidate and "xiaohongshu.com" not in candidate:
                continue
            if candidate not in seen:
                seen.add(candidate)
                urls.append(candidate)

        if urls:
            return urls

        return [line.strip() for line in raw.splitlines() if line.strip()]

    def write_inline_urls_file(self) -> Path:
        urls = self.get_inline_urls()
        target = Path(self.urls_file_var.get()).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(urls) + "\n", encoding="utf-8")
        return target

    def clear_url_inputs(self) -> None:
        self.urls_text.delete("1.0", "end")
        self.status_var.set("已清空 URL 输入框。")

    def reset_progress(self, label: str) -> None:
        self.current_task_total = 0
        self.current_task_done = 0
        self.progress_value_var.set(0)
        self.progress_label_var.set(label)
        self.progress_detail_var.set("")

    def set_progress_total(self, total: int, label: str) -> None:
        self.current_task_total = max(total, 0)
        self.current_task_done = 0
        self.progress_value_var.set(0)
        self.progress_label_var.set(label)
        if total > 0:
            self.progress_detail_var.set(f"0 / {total}")
        else:
            self.progress_detail_var.set("")

    def update_progress(self, done: int, detail: str) -> None:
        self.current_task_done = max(done, 0)
        if self.current_task_total > 0:
            percent = min(100.0, (self.current_task_done / self.current_task_total) * 100)
            self.progress_value_var.set(percent)
        self.progress_detail_var.set(detail)

    def mark_progress_complete(self, label: str, detail: str) -> None:
        self.progress_label_var.set(label)
        self.progress_detail_var.set(detail)
        self.progress_value_var.set(100.0 if self.current_task_total else 0.0)

    def handle_download_output(self, line: str) -> None:
        match = re.match(r"^\[(\d+)/(\d+)\]\s+(.*)$", line)
        if match:
            index = int(match.group(1))
            total = int(match.group(2))
            url = match.group(3)
            if self.current_task_total != total:
                self.set_progress_total(total, "正在下载视频...")
            self.update_progress(index - 1, f"第 {index} / {total} 条，正在解析: {url}")
            return

        if line == "stage: resolving-share-url":
            if self.current_task_total > 0:
                current = min(self.current_task_done + 1, self.current_task_total)
                self.progress_detail_var.set(
                    f"第 {current} / {self.current_task_total} 条，正在解析分享短链..."
                )
            return

        if line.startswith("resolved-url: "):
            resolved = line.split(": ", 1)[1]
            if self.current_task_total > 0:
                current = min(self.current_task_done + 1, self.current_task_total)
                self.progress_detail_var.set(
                    f"第 {current} / {self.current_task_total} 条，已展开为: {resolved}"
                )
            return

        if line == "stage: extracting-video":
            if self.current_task_total > 0:
                current = min(self.current_task_done + 1, self.current_task_total)
                self.progress_detail_var.set(
                    f"第 {current} / {self.current_task_total} 条，正在获取视频信息..."
                )
            return

        if line.startswith("stage: downloading-file -> "):
            filename = line.split("-> ", 1)[1]
            if self.current_task_total > 0:
                current = min(self.current_task_done + 1, self.current_task_total)
                self.progress_detail_var.set(
                    f"第 {current} / {self.current_task_total} 条，正在下载: {filename}"
                )
            return

        if line.startswith("saved: "):
            saved_name = line[7:].strip()
            done = min(self.current_task_done + 1, self.current_task_total or self.current_task_done + 1)
            total = self.current_task_total or done
            self.update_progress(done, f"第 {done} / {total} 条已完成: {saved_name}")
            return

        if line.startswith("failed: "):
            done = min(self.current_task_done + 1, self.current_task_total or self.current_task_done + 1)
            total = self.current_task_total or done
            self.update_progress(done, f"第 {done} / {total} 条失败: {line[8:].strip()}")
            return

    def handle_notes_output(self, line: str) -> None:
        if line.startswith("done: "):
            done = min(self.current_task_done + 1, self.current_task_total or self.current_task_done + 1)
            total = self.current_task_total or done
            self.update_progress(done, f"第 {done} / {total} 个笔记已生成: {line[6:].strip()}")

    def _drain_log_queue(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.insert("end", message)
            if not message.endswith("\n"):
                self.log_text.insert("end", "\n")
            self.log_text.see("end")
        self.root.after(150, self._drain_log_queue)

    def set_busy(self, value: bool) -> None:
        self.busy = value
        state = "disabled" if value else "normal"
        self.download_button.configure(state=state)
        self.notes_button.configure(state=state)

    def validate_urls_file(self) -> Optional[Path]:
        path = Path(self.urls_file_var.get()).expanduser()
        if not path.exists():
            messagebox.showerror("缺少链接文件", "请先选择一个存在的 urls.txt 文件。")
            return None
        return path

    def start_download(self) -> None:
        if self.busy:
            return
        inline_urls = self.get_inline_urls()
        if inline_urls:
            urls_file = self.write_inline_urls_file()
            self.status_var.set(f"已自动识别出 {len(inline_urls)} 条有效链接，开始下载。")
            total_urls = len(inline_urls)
        else:
            urls_file = self.validate_urls_file()
            if not urls_file:
                return
            total_urls = len(
                [line.strip() for line in urls_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            )

        output_dir = Path(self.output_dir_var.get()).expanduser()
        failures_file = Path(self.failures_file_var.get()).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        failures_file.parent.mkdir(parents=True, exist_ok=True)
        self.set_progress_total(total_urls, "正在下载视频...")

        cmd = [
            "python3",
            str(DOWNLOAD_SCRIPT),
            "--urls-file",
            str(urls_file),
            "--output-dir",
            str(output_dir),
            "--failures-file",
            str(failures_file),
        ]
        self._run_background(
            "正在下载视频...", cmd, self._download_finished, self.handle_download_output
        )

    def _download_finished(self) -> None:
        failures_path = Path(self.failures_file_var.get()).expanduser()
        remaining = 0
        if failures_path.exists():
            try:
                remaining = len(json.loads(failures_path.read_text(encoding="utf-8")))
            except Exception:
                remaining = -1
        if remaining == 0:
            self.status_var.set("下载完成，没有失败链接。")
            self.mark_progress_complete(
                "下载完成", f"共处理 {self.current_task_total} 条链接，没有失败项。"
            )
        elif remaining > 0:
            self.status_var.set(f"下载完成，还有 {remaining} 条失败链接可补跑。")
            self.mark_progress_complete(
                "下载结束", f"共处理 {self.current_task_total} 条链接，剩余失败 {remaining} 条。"
            )
        else:
            self.status_var.set("下载结束，请检查失败记录文件。")
            self.mark_progress_complete("下载结束", "请检查失败记录文件。")

    def start_notes(self) -> None:
        if self.busy:
            return
        videos_dir = Path(self.output_dir_var.get()).expanduser()
        if not videos_dir.exists():
            messagebox.showerror("缺少视频目录", "请先下载视频，或手动选择一个存在的视频目录。")
            return
        transcripts_dir = Path(self.transcripts_dir_var.get()).expanduser()
        notes_dir = Path(self.notes_dir_var.get()).expanduser()
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        notes_dir.mkdir(parents=True, exist_ok=True)
        total_videos = len(list(videos_dir.glob("*.mp4")))
        self.set_progress_total(total_videos, "正在生成同名笔记...")
        cmd = [
            "python3",
            str(NOTES_SCRIPT),
            "--videos-dir",
            str(videos_dir),
            "--transcripts-dir",
            str(transcripts_dir),
            "--notes-dir",
            str(notes_dir),
        ]
        self._run_background(
            "正在生成同名笔记...", cmd, self._notes_finished, self.handle_notes_output
        )

    def _notes_finished(self) -> None:
        notes_dir = Path(self.notes_dir_var.get()).expanduser()
        count = len(list(notes_dir.glob("*.md"))) if notes_dir.exists() else 0
        self.status_var.set(f"笔记生成完成，当前共有 {count} 份 Markdown 笔记。")
        self.mark_progress_complete("笔记生成完成", f"当前共有 {count} 份 Markdown 笔记。")

    def _run_background(
        self,
        status_text: str,
        cmd: list,
        on_success: Callable[[], None],
        on_output: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.set_busy(True)
        self.status_var.set(status_text)
        self.log("\n" + "=" * 70)
        self.log("运行命令:")
        self.log(" ".join(cmd))
        self.log("=" * 70)

        def worker() -> None:
            try:
                process = subprocess.Popen(
                    cmd,
                    cwd=str(ROOT),
                    env=build_runtime_env(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert process.stdout is not None
                for line in process.stdout:
                    clean_line = line.rstrip("\n")
                    self.log(clean_line)
                    if on_output:
                        self.root.after(0, lambda text=clean_line: on_output(text))
                code = process.wait()
                if code != 0:
                    raise subprocess.CalledProcessError(code, cmd)
            except Exception as exc:
                self.root.after(0, lambda: self._task_failed(exc))
            else:
                self.root.after(0, lambda: self._task_succeeded(on_success))

        threading.Thread(target=worker, daemon=True).start()

    def _task_succeeded(self, callback) -> None:
        self.set_busy(False)
        callback()

    def _task_failed(self, exc: Exception) -> None:
        self.set_busy(False)
        self.status_var.set("任务失败了，请看下面日志。")
        self.progress_label_var.set("任务失败")
        self.progress_detail_var.set(str(exc))
        self.log(f"[error] {exc}")
        messagebox.showerror("任务失败", f"运行失败：{exc}")

    def open_workspace(self) -> None:
        subprocess.run(["open", str(DEFAULT_WORKSPACE)], check=False)

    def open_failures_file(self) -> None:
        target = Path(self.failures_file_var.get()).expanduser()
        if target.exists():
            subprocess.run(["open", "-R", str(target)], check=False)
        else:
            messagebox.showinfo("还没有失败记录", "当前还没有生成失败记录文件。")


def main() -> None:
    root = tk.Tk()
    try:
        root.tk.call("source", "/System/Library/Tcl/8.6/tk.tcl")
    except Exception:
        pass
    app = App(root)
    app.log("欢迎使用 Xiaohongshu Video Backup。")
    app.log(f"默认工作目录: {DEFAULT_WORKSPACE}")
    root.mainloop()


if __name__ == "__main__":
    main()
