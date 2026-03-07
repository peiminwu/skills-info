---
name: xhs-content-extractor-for-mac
description: macOS 专用小红书图文提取器，使用 Safari 登录态和 Apple Vision OCR 按原帖顺序输出 TXT（小红书链接抓取 / Apple Vision OCR / xhs note extract / for mac）。
---

# XHS Content Extractor For Mac

## Purpose

输入一个小红书图文笔记链接或整段分享文案，输出 `txt` 文件：
1. 提取正文文字。
2. 对每张图片做 OCR。
3. 按图文顺序写入文本。
4. 使用 `UTF-8 with BOM` 规避中文乱码。
5. 运行输出中显示“页面候选图片数”和“实际提取图片数”，用于确认原帖是否带图。
6. 若输入的是整段分享文案，会在 OCR 前先校验“分享预览”和实际页面是否一致，不一致直接停止，避免白跑 OCR。
7. 默认启用 OCR 缓存；相同图片再次跑时会直接复用识别结果。
8. 图片 OCR 使用 Apple Vision，仅支持 macOS。

## Scope

1. 仅支持图文笔记。
2. 不处理评论区。
3. 不处理视频笔记。

## Required runtime assumptions

1. 本地已有小红书可用登录态（Safari）。
2. macOS 13+。
3. Python 3.9+。
4. 已安装依赖，并允许 Safari 自动化。

## Default behavior

1. 输出目录：`outputs/`
2. 编码：`utf-8-sig`
3. 抓取失败重试：3 次
4. 图片 OCR 失败：写占位并继续
5. 终端输出包含图片检测摘要，方便排查“原帖有图但未提取”的情况
6. 若检测到页面候选图片明显多于实际提取图片，会自动重跑整条笔记
7. OCR 引擎固定为 Apple Vision，不依赖 Paddle 模型下载

## How to run

```bash
python scripts/fetch_xhs_note.py "<xhs_url>" --out-dir outputs
```

也支持直接粘贴整段分享文案：

```bash
python scripts/fetch_xhs_note.py "【标题】摘要... http://xhslink.com/xxx Copy and open Xiaohongshu to view the full post！" --out-dir outputs
```

可选参数：
1. `--encoding`（默认 `utf-8-sig`）
2. `--max-retries`（默认 `3`）
3. `--timeout-sec`（默认 `30`）
4. `--download-workers`（默认 `4`，图片下载并发数）
5. `--ocr-max-side`（默认 `1280`，OCR 前图片长边缩放值；更小通常更快）
6. `--skip-share-verify`（跳过 OCR 前分享文案校验，默认不开启）
7. `--vision-recognition-level`（默认 `fast`，可选 `accurate`）
8. `--vision-recognition-languages`（默认 `zh-Hans,en-US`）
9. `--vision-min-text-height`（默认 `0.016`，更大通常更快）
10. `--vision-language-correction`（开启 Apple Vision 语言纠错）
11. `--vision-auto-detect-language`（开启 Apple Vision 自动识别语言）
12. `--disable-ocr-cache`（关闭 OCR 缓存）

## Output files

1. `outputs/<笔记标题>.txt`
2. `outputs/<笔记标题>/images/`（图片缓存）
3. 若标题不可用，则回退为 `note_id`

输出格式细节见：`references/output-format.md`
问题排查见：`references/troubleshooting.md`

## Execution workflow

1. 启动 Safari 自动化会话并复用当前 Safari 登录态。
2. 打开笔记页面并检查登录态。
3. 解析标题、正文块和图片顺序。
4. 下载图片并执行 Apple Vision OCR。
5. 生成 txt。

## Failure handling rules

1. 登录失效：直接报错并停止。
2. 单张图片下载/OCR失败：在 txt 中写失败占位，继续处理其他图片。
3. 页面结构变化：返回解析失败并输出错误信息。
