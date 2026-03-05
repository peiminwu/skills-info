---
name: xhs-content-extractor
description: 输入小红书图文链接并抓取正文与图片OCR，按原帖顺序输出TXT（小红书链接抓取 / 小红书 OCR / xhs note extract / 给链接输出 txt）。
---

# XHS Content Extractor

## Purpose

输入一个小红书图文笔记链接，输出 `txt` 文件：
1. 提取正文文字。
2. 对每张图片做 OCR。
3. 按图文顺序写入文本。
4. 使用 `UTF-8 with BOM` 规避中文乱码。
5. 运行输出中显示“页面候选图片数”和“实际提取图片数”，用于确认原帖是否带图。

## Scope

1. 仅支持图文笔记。
2. 不处理评论区。
3. 不处理视频笔记。

## Required runtime assumptions

1. 本地已有小红书可用登录态（Safari）。
2. Python 3.10+。
3. 已安装依赖和 Playwright 浏览器内核。

## Default behavior

1. 输出目录：`outputs/`
2. 编码：`utf-8-sig`
3. 抓取失败重试：3 次
4. 图片 OCR 失败：写占位并继续
5. 终端输出包含图片检测摘要，方便排查“原帖有图但未提取”的情况
6. 若检测到页面候选图片明显多于实际提取图片，会自动重跑整条笔记

## How to run

```bash
python scripts/fetch_xhs_note.py "<xhs_url>" --out-dir outputs
```

可选参数：
1. `--encoding`（默认 `utf-8-sig`）
2. `--max-retries`（默认 `3`）
3. `--timeout-sec`（默认 `30`）

## Output files

1. `outputs/<note_id>.txt`
2. `outputs/<note_id>/images/`（图片缓存）

输出格式细节见：`references/output-format.md`
问题排查见：`references/troubleshooting.md`

## Execution workflow

1. 启动 Safari 自动化会话并复用当前 Safari 登录态。
2. 打开笔记页面并检查登录态。
3. 解析标题、正文块和图片顺序。
4. 下载图片并执行 PaddleOCR。
5. 生成 txt。

## Failure handling rules

1. 登录失效：直接报错并停止。
2. 单张图片下载/OCR失败：在 txt 中写失败占位，继续处理其他图片。
3. 页面结构变化：返回解析失败并输出错误信息。
