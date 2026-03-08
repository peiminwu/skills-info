---
name: reabble
description: macOS 专用 Kindle 推送技能。通过 Safari 打开 Reabble / Send to Kindle 发送页，把本地 TXT 内容自动填进 editor 后发送到 Kindle。适用于“发送到kindle”“发送到 Kindle”“推送到kindle”“推送到 Kindle”“把 txt 发到 Kindle”等请求。
---

# Reabble

## Purpose

把本地文件发送到 Kindle：
1. 接收一个或多个本地文件路径。
2. 把 `txt` 转成适合发送页 editor 的 HTML 内容。
3. 用 Safari 打开 Reabble 的 `Send to Kindle` 页面。
4. 自动把内容带入 editor 并点击 `Send`。
5. 默认尽量不激活 Safari，并在发送成功后自动关闭临时标签页或窗口。

## Required runtime assumptions

1. 仅支持 macOS。
2. 使用 Safari。
3. Safari 已启用 `Develop > Allow JavaScript from Apple Events`。
4. Reabble 的 `Send to Kindle` 页面已经至少手动配置过一次，或者你会在调用时提供 `--mail-to-name`。
5. 文件路径必须是本地可读的 `.txt`。

## How to use

单文件：

```bash
python scripts/send_to_kindle.py "/abs/path/file.txt"
```

多文件：

```bash
python scripts/send_to_kindle.py "/abs/path/a.txt" "/abs/path/b.txt"
```

只验证命令，不真正发送：

```bash
python scripts/send_to_kindle.py "/abs/path/file.txt" --dry-run
```

如果你只想把内容装进发送页，先不点 `Send`：

```bash
python scripts/send_to_kindle.py "/abs/path/file.txt" --no-auto-send
```

如果 Reabble 还没有记住你的 Kindle 地址，可以显式传入：

```bash
python scripts/send_to_kindle.py "/abs/path/file.txt" --mail-to-name "your_kindle_name" --mail-to-domain "free.kindle.com"
```

## Workflow

1. 校验文件存在、可读、后缀为 `.txt`。
2. 读取 `txt` 内容并转换成结构简单的 HTML 内容。
3. 用 Safari 打开 Reabble 发送页。
4. 把内容写入 editor，并按需要补上 Kindle 邮箱名。
5. 自动点击 `Send`，然后等待成功提示。
6. 发送成功后关闭技能临时打开的 Safari 标签页或窗口。

## Notes

1. 这个技能走的是 Reabble 网页链路，不再依赖 `Send to Kindle.app`。
2. 如果用户给的是相对路径，先解析成绝对路径。
3. 如果用户没有给路径但上下文里刚生成了 `txt`，可以先从最近生成的输出路径中选择，再调用脚本。
4. `--no-auto-send` 只负责把内容带入发送页，不会真的发出去。
5. 真正发送时，脚本默认会尽量静默运行；如果 Safari 原本没开，它可能仍会在后台短暂启动，然后在发送后自动退出。
