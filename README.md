# Xiaohongshu Video Backup Skill

一个尽量傻瓜式的小红书视频备份工具包。

它可以帮你：

- 批量下载小红书视频
- 自动按小红书标题命名 `.mp4`
- 自动记录失败链接，方便补跑
- 把视频转成同名 `.txt` 转写和 `.md` 内容笔记

在线说明页：

[https://jas0nla.github.io/xiaohongshu-video-backup-skill/](https://jas0nla.github.io/xiaohongshu-video-backup-skill/)

## 最简单的用法

### 1. 下载这个仓库

```bash
git clone https://github.com/Jas0nla/xiaohongshu-video-backup-skill.git
cd xiaohongshu-video-backup-skill
```

### 2. 准备一个链接文本文件

新建一个 `urls.txt`，内容是一行一个小红书链接，例如：

```text
https://www.xiaohongshu.com/explore/xxxxxxxxxxxxxxxx
https://www.xiaohongshu.com/explore/yyyyyyyyyyyyyyyy
```

### 3. 直接下载视频

```bash
python3 skill/scripts/download_videos.py \
  --urls-file ./urls.txt \
  --output-dir ./xhs_videos \
  --failures-file ./download_failures.json
```

下载完成后：

- 视频会在 `./xhs_videos/`
- 失败链接会在 `./download_failures.json`

### 4. 生成同名文字笔记

```bash
python3 skill/scripts/generate_notes.py \
  --videos-dir ./xhs_videos \
  --transcripts-dir ./xhs_transcripts \
  --notes-dir ./xhs_notes
```

生成完成后：

- 转写文本会在 `./xhs_transcripts/`
- Markdown 笔记会在 `./xhs_notes/`

## 如果中途断了怎么办

不用重来。

看 `download_failures.json` 里面剩下哪些链接，把失败链接复制到一个新的文本文件里，比如 `retry.txt`，然后重新跑一次：

```bash
python3 skill/scripts/download_videos.py \
  --urls-file ./retry.txt \
  --output-dir ./xhs_videos \
  --failures-file ./retry_failures.json
```

## 给 Codex 当 Skill 用

如果你本身就在用 Codex，可以把这个 Skill 放到本机：

```bash
mkdir -p ~/.codex/skills
cp -R ./skill ~/.codex/skills/xiaohongshu-video-backup
```

然后在 Codex 里这样调用：

```text
Use $xiaohongshu-video-backup to download Xiaohongshu videos, retry failed links, and generate same-name Markdown notes.
```

## 运行前准备

这套工具默认你本机已经有这些环境：

- `python3`
- `curl`
- `npx`
- `whisper`
- Codex 的 `playwright` skill

如果你只是想手动跑脚本，不一定非得理解 Skill 是什么，按上面的命令一步一步复制即可。

## 仓库内容

- `skill/`：Skill 本体和脚本
- `docs/`：GitHub Pages 说明页
- `README.md`：这份傻瓜式说明
