---
name: viewpoint-collection
description: Summarize a topic's recent viewpoints, data points, and events in Chinese from user-provided links or a fallback source whitelist, then group the output into bullish, bearish, and neutral sections for PPT-ready plain-text delivery. Use when the user asks things like “给这些 links 做观点总结”, “整理某 topic 过去一段时间的多空观点”, “某主题近期机构/人物看法汇总”, or “topic + links”.
---

# Viewpoint Collection

## Overview

Use this skill to turn a topic plus optional links into a short Chinese viewpoint roundup for a boss update or PPT draft.

Always save the final deliverable as a plain text file.

The output has two layers in a fixed order:

1. `逐条观点卡片`
2. `看多/积极`
3. `看空/负面`
4. `中性`
5. `来源`

Read [references/source-handling.md](references/source-handling.md) when choosing fallback sources, screening large batches of links, deduplicating repeated coverage, or deciding stance labels.

## Trigger And Scope

Use this skill when the user asks for a recent roundup such as:

- `给这些 links 做观点总结`
- `整理下面这些 links 的多空观点`
- `某个 topic，过去一段时间的观点/数据/事件总结`
- `topic + links`
- `把这批文章整理成看多、看空、中性三段`

Common input size is `10-30` links. The workflow should still work for a single link or a smaller batch.

The goal is not a long narrative article. The goal is a compressed, source-attributed summary that preserves who said what, when they said it, and why they held that view.

## Input Contract

Start by identifying:

- `links`: primary input, one or more URLs when available
- `topic`: optional but recommended
- `date_range` or `cutoff`: optional hard boundary

Apply these defaults:

1. Treat `links` as the first-priority input.
2. If `topic` is missing, infer it from the common subject across the supplied links.
3. If the user gives no explicit time range, default to the last 30 days.
4. If the user gives a cutoff or date range, do not use material published after that boundary.

## Time Rules

Apply these rules in order:

1. If the user gives an explicit date or range, treat it as a hard information boundary.
2. If no date is given, use a rolling 30-day window ending on the effective report date.
3. For supplied links, include only items that fit the time boundary unless the user explicitly asks for a longer historical comparison.
4. When multiple links discuss the same older event from different recent dates, use the publication date of each link for inclusion and the event date only inside the summary text.

State the boundary explicitly near the top of the final output:

- `时间范围：YYYY-MM-DD 至 YYYY-MM-DD`

## Workflow

Follow this sequence and do not skip screening:

### 1. Parse The Request

Write down:

- `主题`
- `时间范围`
- `来源模式`

`来源模式` must be one of:

- `用户 links`
- `source-list兜底`

### 2. Build The Candidate Set

If the user provides links:

1. Read all links first.
2. Extract author, institution or publication, publication date, title, and the main claim.
3. Only do a minimal follow-up lookup when the page itself is missing author, institution, or date.
4. If a media article mainly quotes a named institution or strategist, prefer attributing the view to the underlying speaker instead of the reporter.

If the user does not provide links:

1. Fetch the maintained source list at `https://raw.githubusercontent.com/peiminwu/source-list/refs/heads/main/list`.
2. Use it as a whitelist of preferred source types, not as a pool of articles.
3. Search around the topic with this order:
   - 一级原始数据源
   - 二级知名机构/人物
   - 三级严肃媒体
   - 四级观点与分析平台
   - 五级中国券商
4. Stop once you have enough attributable material for a reliable grouped summary.

### 3. Screen And Deduplicate

When working with `10-30` links, do not assume every link deserves a full card.

Do this first:

1. Remove exact duplicates, syndications, and near-identical rewrites.
2. Merge multiple links that only restate the same view from the same person or institution.
3. Keep the strongest or clearest version when the same claim appears in several places.
4. Prefer material with a named speaker, explicit stance, and concrete reasoning.

Target output size:

- Raw links processed: all supplied links
- Final card pool: usually `12-20`
- If repetition is high: allow `10-15`

Links that do not make the final card pool may still inform the grouped summary and source list.

### 4. Extract Per-Link Fields

For each retained item, extract:

- `人物/机构`
- `机构/媒体`
- `日期`
- `主要观点`
- `主要逻辑`
- `目标价/评级/仓位变化` if explicitly stated

Use these formatting rules:

1. Card title format: `某人或机构@某机构或媒体@YYYY-MM-DD`
2. If no named person is available, use `机构/媒体@机构/媒体@YYYY-MM-DD`
3. `主要逻辑`最多三条，压缩成短句，不展开成长段

### 5. Classify Stance

Use these buckets:

- `看多/积极`: explicit bullish, supportive, optimistic, add-position, positive-risk view
- `看空/负面`: explicit bearish, opposed, pessimistic, reduce-position, short, negative-risk view
- `中性`: data-heavy, event recap, mixed or conditional views, or pieces without a clear directional stance

If a source contains both positive and negative discussion, classify by the bottom-line call instead of by the loudest sentence.

### 6. Rank The Results

Within each stance bucket, sort by:

1. Strength and clarity of the view
2. Source quality and speaker prominence
3. Recency

Favor high-signal, well-attributed items over weakly sourced commentary.

### 7. Write The Final Txt

The final deliverable is a compact Chinese text file for direct reuse in PPT drafting.

Do not turn the grouped summary into prose paragraphs that bury the call. Each bullet should make the stance and core reason obvious at a glance.

### 8. Save The Deliverable

Use this naming rule:

- `主题-YYYYMMDD.txt`

Build the filename as follows:

1. Use the resolved topic as `主题`.
2. Remove path separators and other filesystem-hostile characters.
3. Keep Chinese characters when they are the clearest label.
4. Use the explicit cutoff date when provided.
5. Otherwise use the end date of the effective 30-day window.

## Output Template

Use this exact structure:

```text
主题：...
时间范围：YYYY-MM-DD 至 YYYY-MM-DD
来源模式：用户 links / source-list兜底
处理链接数：原始 N 条；入选 M 条
证据状态：充分 / 一般 / 不足

## 逐条观点卡片
某人或机构@某机构或媒体@YYYY-MM-DD
- 主要观点：...
- 主要逻辑：逻辑1；逻辑2；逻辑3

某人或机构@某机构或媒体@YYYY-MM-DD
- 主要观点：...
- 主要逻辑：逻辑1；逻辑2；逻辑3

## 看多/积极
- 某人或机构：一句话观点；一句话逻辑

## 看空/负面
- 某人或机构：一句话观点；一句话逻辑

## 中性
- 某人或机构：一句话观点；一句话逻辑

## 来源
- 机构或人物 | 标题 | YYYY-MM-DD | 链接
- ...
```

## Writing Rules

Enforce these rules:

1. Write in Chinese.
2. Keep the tone restrained and attribution-first.
3. Prefer short sentences and semicolon-separated logic.
4. Do not pad the output with generic background.
5. Separate facts from opinions when the source mixes both.
6. Do not upgrade one commentator into market consensus.
7. If evidence is thin, say `证据状态：一般` or `不足` instead of pretending certainty.
8. If a link is mostly event or data with no real stance, keep it brief and place it under `中性`.
9. Treat target prices, ratings, and explicit position changes as optional supplements, not mandatory fields.

## Stop Conditions

Stop and say the input is insufficient if:

- The links are mostly inaccessible and you cannot recover author, source, or date
- The topic implied by the links is too mixed to summarize honestly as one subject
- Nearly all material is duplicate coverage with no attributable viewpoints
- The user asks for a time boundary but the available sources do not support it cleanly
