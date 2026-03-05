---
name: what-happened-brief
description: Produce a balanced Chinese brief answering what happened, why it happened, and what the market expects next for a natural-language question about a company, asset, market move, policy issue, international event, historical episode, or broader phenomenon. Use when the user asks things like "最近发生了什么", "为什么涨这么多", "为什么跌了这么多", "站在某个时间点怎么看", or wants a source-driven summary with a strict cutoff date, neutral tone, and clearly separated facts, causes, and market views.
---

# What Happened Brief

## Overview

Use this skill to turn a natural-language question into a neutral, source-driven Chinese brief with a fixed structure:

1. `极简摘要`
2. `最近发生了什么`
3. `为什么`
4. `未来会怎样`
5. `来源`

Keep facts and viewpoints separate. Summarize mainstream views instead of taking sides. Stop instead of forcing a conclusion when the evidence is too weak.

Always save the final deliverable as a plain text file.

Read [references/source-handling.md](references/source-handling.md) when selecting sources, validating quoted opinions, or deciding whether a source is strong enough to support a claim.

## Trigger And Scope

Use this skill when the user asks a natural-language question such as:

- `最近伊朗/以色列发生了什么事`
- `2月5日比特币为什么跌了这么多`
- `二月份为什么日本股票涨了这么多`
- `芝商所 CME 今年为什么涨了这么多`
- `美股 2026-01-19 为什么涨了这么多`
- `A股港股为什么 2026-02-02 大涨`
- `比特币2月份为什么跌了这么多 -极简`

Accept three common input shapes:

- A recent event or market move with no explicit date
- A question anchored to a specific date or cutoff
- A historical event or long-running phenomenon that is not about "recent" developments

Accept one output modifier:

- `-极简`: switch to a compact mode that outputs only `极简摘要`, with the summary focusing mainly on `为什么`

Reject or ask the user to narrow the question if it is too broad to cover without distortion.

## Time Rules

Apply these rules in order:

1. If the user gives an explicit date or cutoff, treat it as a hard information boundary.
2. Use only material that was available on or before that cutoff date.
3. Do not use hindsight, post-cutoff articles, or later price action to validate earlier views.
4. If a source was published after the cutoff, do not cite it even if it discusses older events.
5. If the user does not give a time range, interpret `最近` by topic:
   - Financial markets: default to the last 30 days
   - Fast-moving international events: default to the last 14 days
   - Major ongoing events: trace back to the start of the current episode if a shorter window would mislead
6. If the question is clearly historical or about a long-term phenomenon, do not force a `最近` window. Build around the event's key phase instead.

State the time boundary explicitly near the top:

- `时间截面：截至 YYYY-MM-DD`

## Market-Move Conventions

For questions like `为什么涨了这么多` or `为什么跌了这么多`, use these defaults unless the user says otherwise:

1. Measure by closing move versus the previous trading day's close.
2. Use the relevant market's local trading calendar for stocks, ETFs, and indexes.
3. For crypto and international events, state the date convention you used.
4. Do not silently switch to intraday ranges unless the user asked for intraday analysis and the sources support it.

## Workflow

Follow this sequence and do not skip validation:

### 1. Parse The Question

Identify:

- The core subject
- Whether the user is asking about facts, causes, market reaction, or all three
- Whether the question is recent, historical, or anchored to a cutoff date
- Whether the scope is narrow enough to answer reliably

If the subject is ambiguous or too broad, stop and ask the user to narrow it.

### 2. Set The Boundary

Write down:

- `问题`
- `时间截面`
- `范围说明`
- `证据状态`

Use `范围说明` to state what is covered and excluded. Use `证据状态` with one of:

- `充分`
- `一般`
- `不足`

### 3. Collect Facts

Start with the highest-quality factual sources:

- Primary data sources and official institutions
- Serious media for fast-moving developments

Build a simple chronology before writing. Confirm dates, sequence, and whether the reported move or event actually happened as framed.

### 4. Collect Explanations

Separate:

- Direct triggers
- Deeper structural drivers

Do not present commentary as verified fact. If the causal chain is debated, say so explicitly.

### 5. Collect Market Views

Summarize mainstream expectations instead of issuing your own call.

For this section, capture:

- The dominant market view
- The main disagreement or competing scenarios
- The key indicators or events that the market is watching next

### 6. Validate Sources

Before quoting or paraphrasing:

1. Confirm that the publication date respects the cutoff.
2. Confirm that each key fact is supported by a strong source.
3. Confirm that a named person's view has at least two independent sources.
4. Prefer the most-circulated or highest-visibility version when using platform commentary as a supplement.

### 7. Write The Brief

Write in Chinese with a neutral, restrained tone. Keep facts and opinions visibly separate. Avoid sensational language. Do not give portfolio advice or position sizing advice.

If the user includes `-极简`, switch to compact mode:

1. Output only the metadata block, `极简摘要`, and `来源`.
2. Do not output `最近发生了什么`, `为什么`, or `未来会怎样` as separate sections.
3. Concentrate the summary on the direct and deeper causes.
4. Keep only the minimum factual setup needed to explain the causes.
5. Target about 300-500 Chinese characters unless the user asks for a different length.

### 8. Save The Deliverable

Write the final output to a `.txt` file using this naming rule:

- `主题-YYYYMMDD.txt`

Build the filename as follows:

1. Use the core subject as `主题`.
2. Remove path separators and other filesystem-hostile characters.
3. Replace internal spaces with hyphens when needed.
4. Keep Chinese characters if they are the cleanest subject label.
5. Use the cutoff date for `YYYYMMDD`.
6. If there is no explicit cutoff date, use the effective report date implied by the skill's time boundary.

Examples:

- `比特币-20260228.txt`
- `伊朗以色列-20260302.txt`
- `CME-20260228.txt`

## Output Template

Use this exact section order for the standard mode:

```text
问题：...
时间截面：截至 YYYY-MM-DD
范围说明：...
证据状态：充分 / 一般 / 不足

## 极简摘要
...

## 最近发生了什么
...

## 为什么
...

## 未来会怎样
...

## 来源
- 机构或人物 | 标题 | YYYY-MM-DD | 链接
- ...
```

Use this exact section order for `-极简` mode:

```text
问题：...
时间截面：截至 YYYY-MM-DD
范围说明：...
证据状态：充分 / 一般 / 不足

极简摘要：...

来源
- 机构或人物 | 标题 | YYYY-MM-DD | 链接
- ...
```

Apply these writing constraints:

- Standard mode `极简摘要`: 300-500 Chinese characters
- `最近发生了什么`: 2000-3000 Chinese characters
- `为什么`: 2000-3000 Chinese characters
- `未来会怎样`: 2000-3000 Chinese characters
- `-极简` mode: output only `极简摘要`, mainly about `为什么`, usually 300-500 Chinese characters
- `来源` does not count toward the length limits
- Keep the structure strict; do not add extra body sections
- Put all citations in the final `来源` block instead of inline
- Save the complete output to a text file named `主题-YYYYMMDD.txt`

## Writing Rules

Enforce these rules:

1. Balance facts and views; do not flatter the user's prior belief.
2. Treat facts, explanations, and outlook as different evidence categories.
3. Use wording such as `目前已知的是`, `更直接的原因可能是`, `市场主流观点是`, and `仍存在分歧` when certainty is limited.
4. Do not turn one bank, one strategist, or one personality into `市场共识`.
5. Do not make unsupported causal claims.
6. Do not omit material disagreements in the `未来会怎样` section.

## Stop Conditions

Stop and say what is missing instead of forcing an answer if any of the following is true:

1. The question is too broad to narrow without distorting the topic.
2. The available material is too thin to support the three-part structure.
3. You cannot verify whether key material was published before the cutoff date.
4. A key fact or quoted named opinion relies on only one source.

## Final Self-Check

Before delivering, verify all of the following:

- The cutoff date is explicit.
- No source crosses the cutoff boundary.
- The chronology is internally consistent.
- Facts are not sourced only from weak commentary platforms.
- Named opinions have two-source confirmation.
- The `未来会怎样` section summarizes mainstream views, major disagreements, and watchpoints.
- The tone stays neutral and non-prescriptive.
- In `-极简` mode, only the compact structure is used and the summary remains cause-focused.
- The text file name follows `主题-YYYYMMDD.txt`.
