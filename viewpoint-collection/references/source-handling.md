# Source Handling

Use this reference file only when selecting fallback sources, screening large link batches, deduplicating repeated coverage, or deciding whether a source is strong enough to support a stance label.

The source hierarchy below is derived from the maintained source list at:
[source-list](https://raw.githubusercontent.com/peiminwu/source-list/refs/heads/main/list)

## Source Priority

Apply this hierarchy in order.

### 1. Primary factual sources

Use first for hard facts, official data, filings, policy text, exchange notices, and macro releases.

- Bureau of Economic Analysis
- Bureau of Labor Statistics
- Federal Reserve
- FRED
- SEC
- 国家统计局
- 中国人民银行
- 财政部
- 上海证券交易所
- 深圳证券交易所
- 香港交易所
- IMF
- World Bank
- OECD

### 2. Institutional research and major investors

Use mainly for interpretation and named views.

- NBER
- Moody's
- S&P Global
- Fitch
- Goldman Sachs
- J.P. Morgan
- Morgan Stanley
- UBS
- Barclays
- HSBC
- Deutsche Bank
- Citi
- Jefferies
- Morningstar
- Value Line
- Zacks
- GuruFocus
- Bridgewater
- Oaktree
- George Soros
- Mark Spitznagel
- Nassim Taleb
- Warren Buffett
- 李录
- Seth Klarman
- Charlie Munger
- 段永平
- Michael Burry
- Cathie Wood
- Joel Greenblatt

### 3. Serious media

Use for interviews, event sequencing, and public summaries of what a named person or institution said.

- The Wall Street Journal
- Bloomberg
- Reuters
- Financial Times
- The Economist
- Barron's
- Fortune
- Forbes
- Business Insider
- The Washington Post
- The New York Times
- The Atlantic
- MarketWatch
- Nikkei Asia
- Institutional Investor
- Project Syndicate
- 财新
- 华尔街见闻

### 4. Opinion and analysis platforms

Use only as supplementary signal when higher-tier material is unavailable or when the platform hosts the original published opinion.

- Seeking Alpha
- arXiv
- Google Scholar
- PubMed
- 雪球
- 新浪财经
- 东方财富网
- 富途牛牛资讯

### 5. China broker research

Use mainly for market framing, mainland or Hong Kong strategy takes, and broker-sourced viewpoint summaries.

- 中信证券
- 中金公司
- 国泰君安
- 华泰证券
- 广发证券
- 招商证券
- 申万宏源
- 中信建投
- 国信证券
- 东方证券

## Screening Large Link Sets

When the user provides `10-30` links:

1. Read or inspect all links at least once.
2. Build a candidate table with source, speaker, date, stance, and one-line claim.
3. Remove exact duplicates first.
4. Collapse syndicated or rewritten coverage of the same underlying interview, note, or statement.
5. Keep the clearest source when several links repeat the same view.

Prefer keeping links that satisfy more of these conditions:

- named speaker
- clear institution or publication
- explicit directional stance
- concrete logic rather than generic market color
- stronger source tier
- cleaner publication date

Prefer dropping links that are mostly:

- duplicate rewrites
- thin market chatter
- title-only commentary without attributable substance
- inaccessible pages with no recoverable metadata

## Deduplication Rules

Treat items as duplicates when the underlying speaker, core claim, and publication window are materially the same, even if headlines differ.

Use these defaults:

1. Same person, same institution, same claim, different reposts: keep one.
2. Same institution note quoted by several media outlets: keep the original note if available; otherwise keep the clearest serious-media version.
3. Same event recap with no distinct viewpoint: merge into grouped summary only, not individual cards.
4. Same speaker expressing the same stance across several days: keep the strongest or most recent formulation unless the view clearly changed.
5. Same media package split into multiple follow-up articles with no new incremental view: keep one card and use the rest only as background.

## Fact Versus View Rules

Apply these defaults:

1. Facts: prefer level 1, then level 3 for rapid reporting.
2. Views: prefer level 2, named investors, and level 5.
3. Platform commentary: use only as a supplement, unless it is the original publication venue for the viewpoint.

## Attribution Rules

For each retained card, aim to capture:

- who said it
- where it appeared
- when it was published
- what the bottom-line call was
- why the source argued that way

If the author is missing:

1. Use the institution or publication name in both title slots.
2. Do not invent a person based on social reposts or second-hand summaries.
3. If neither a person nor a reliable institution can be identified, exclude the item from cards.

If a media article summarizes a named institution's view:

1. Attribute the `人物/机构` field to the underlying institution or strategist when the source makes that clear.
2. Keep the media outlet in the `机构/媒体` field.
3. Do not collapse several distinct institutions into one card unless the article itself is explicitly framed as a grouped market consensus piece.

## Stance Classification Rules

Use these labels consistently:

- `看多/积极`: bullish, supportive, optimistic, add-position, positive risk-reward
- `看空/负面`: bearish, skeptical, opposed, reduce-position, short, negative risk-reward
- `中性`: descriptive, mixed, conditional, wait-and-see, event-only, or data-only

When classification is unclear:

1. Use the bottom-line conclusion, not one colorful quote.
2. If no bottom-line conclusion exists, mark it `中性`.
3. Do not force a directional tag onto pure data releases or event recaps.

## Evidence Strength

Use these defaults:

- `充分`: multiple high-quality, attributable sources with consistent signals
- `一般`: some strong material exists, but part of the picture relies on indirect reporting or mixed-quality coverage
- `不足`: attribution, timing, or source quality is too weak for a confident grouped summary

## Writing Constraints For PPT Use

The final text is meant for a boss update or slide deck, so compress aggressively.

Apply these rules:

1. `主要观点` should usually fit in one short sentence.
2. `主要逻辑` should be at most three short fragments separated by `；`.
3. Grouped bullets should surface the call first, then one short reason.
4. Avoid jargon unless it is necessary to preserve the meaning of the source.
5. Do not write long narrative transitions between bullets.

## Fallback Search Guidance

When no links are supplied:

1. Use the topic as the search anchor.
2. Search higher-priority source types first.
3. Stop once you can build a balanced grouped summary with attributable items.
4. Do not pad the output with low-quality commentary just to fill all three buckets.
5. It is acceptable for one bucket to be sparse if the available evidence is lopsided.
