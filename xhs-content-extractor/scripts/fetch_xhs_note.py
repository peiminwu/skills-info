#!/usr/bin/env python3
"""Fetch a Xiaohongshu image-note and export text + OCR blocks to TXT."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from difflib import SequenceMatcher
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from PIL import Image


DEFAULT_ENCODING = "utf-8-sig"
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SEC = 30

# Avoid remote hoster probing on every run; speed up startup.
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


@dataclass
class NoteData:
    note_id: str
    url: str
    title: str
    author: str
    blocks: list[dict[str, str]]
    image_urls: list[str]


def log(message: str) -> None:
    print(message, file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a Xiaohongshu note and export OCR TXT.")
    parser.add_argument("url", help="Xiaohongshu note URL")
    parser.add_argument("--out-dir", default="outputs", help="Output directory (default: outputs)")
    parser.add_argument("--encoding", default=DEFAULT_ENCODING, help="Output text encoding (default: utf-8-sig)")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="Retry times (default: 3)")
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC, help="Timeout seconds (default: 30)")
    parser.add_argument("--show-browser", action="store_true", help="Show Safari window while running")
    parser.add_argument(
        "--use-active-tab",
        action="store_true",
        help="Reuse current Safari front tab session (no Selenium)",
    )
    return parser.parse_args()


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise ValueError("URL is empty")
    if not re.match(r"^https?://", url):
        url = "https://" + url
    return url


def extract_note_id(url: str) -> str:
    patterns = [
        r"/explore/([a-zA-Z0-9]+)",
        r"/discovery/item/([a-zA-Z0-9]+)",
        r"noteId=([a-zA-Z0-9]+)",
        r"source=note&note_id=([a-zA-Z0-9]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return f"xhs_{int(time.time())}"


def extract_note_id_if_present(url: str) -> str | None:
    patterns = [
        r"/explore/([a-zA-Z0-9]+)",
        r"/discovery/item/([a-zA-Z0-9]+)",
        r"noteId=([a-zA-Z0-9]+)",
        r"source=note&note_id=([a-zA-Z0-9]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def clean_title(raw_title: str) -> str:
    title = (raw_title or "").strip()
    # Remove Xiaohongshu site suffix from browser title.
    title = re.sub(r"\s*-\s*小红书.*$", "", title).strip()
    return title


def safe_filename(name: str, fallback: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>]', " ", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    if not cleaned:
        cleaned = fallback
    if len(cleaned) > 100:
        cleaned = cleaned[:100].rstrip()
    if not (cleaned.startswith("《") and cleaned.endswith("》")):
        cleaned = f"《{cleaned}》"
    return cleaned


def looks_like_title(text: str) -> bool:
    candidate = (text or "").strip()
    if not candidate:
        return False
    if any(key in candidate for key in ["登录后推荐更懂你的笔记", "手机号登录", "扫码登录", "获取验证码"]):
        return False
    if candidate in {"关注", "可用", "新用户可直接登录"}:
        return False
    if "【" in candidate and "】" in candidate:
        return True
    if "|" in candidate:
        return True
    return len(candidate) <= 40


class SafariPage:
    def __init__(self, driver: Any) -> None:
        self.driver = driver

    def goto(self, url: str, timeout_ms: int | None = None, timeout: int | None = None) -> None:
        timeout_val = timeout_ms if timeout_ms is not None else timeout
        if timeout_val is None:
            timeout_val = 30000
        self.driver.set_page_load_timeout(max(10, int(timeout_val / 1000)))
        self.driver.get(url)
        self.wait_for_load_state("networkidle", timeout_ms=timeout_val)

    def wait_for_timeout(self, ms: int) -> None:
        time.sleep(max(0, ms) / 1000)

    def wait_for_load_state(self, _state: str, timeout_ms: int | None = None, timeout: int | None = None) -> None:
        timeout_val = timeout_ms if timeout_ms is not None else timeout
        if timeout_val is None:
            timeout_val = 30000
        end = time.time() + (timeout_val / 1000)
        while time.time() < end:
            ready = self.driver.execute_script("return document.readyState")
            if ready == "complete":
                return
            time.sleep(0.2)

    def evaluate(self, script: str) -> Any:
        expr = script.strip()
        return self.driver.execute_script(f"return ({expr})();")

    def title(self) -> str:
        return self.driver.title or ""

    def current_url(self) -> str:
        return self.driver.current_url or ""


class SafariActiveTabPage:
    def __init__(self, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms

    def goto(self, url: str, timeout_ms: int | None = None, timeout: int | None = None) -> None:
        timeout_val = timeout_ms if timeout_ms is not None else timeout
        if timeout_val is None:
            timeout_val = self.timeout_ms
        subprocess.run(
            [
                "osascript",
                "-e",
                "on run argv",
                "-e",
                'tell application "Safari"',
                "-e",
                'if (count of windows) = 0 then error "No Safari window"',
                "-e",
                "set current tab of front window to (current tab of front window)",
                "-e",
                "set URL of current tab of front window to item 1 of argv",
                "-e",
                "end tell",
                "-e",
                "end run",
                url,
            ],
            check=True,
        )
        self.wait_for_load_state("domcontentloaded", timeout_ms=timeout_val)

    def wait_for_timeout(self, ms: int) -> None:
        time.sleep(max(0, ms) / 1000)

    def wait_for_load_state(self, _state: str, timeout_ms: int | None = None, timeout: int | None = None) -> None:
        timeout_val = timeout_ms if timeout_ms is not None else timeout
        if timeout_val is None:
            timeout_val = self.timeout_ms
        end = time.time() + (timeout_val / 1000)
        while time.time() < end:
            ready = self.evaluate("() => document.readyState")
            if ready == "complete":
                return
            time.sleep(0.2)

    def evaluate(self, script: str) -> Any:
        expr = " ".join(script.strip().splitlines())
        js = f"JSON.stringify((() => {{ const value = ({expr})(); return value === undefined ? null : value; }})())"
        try:
            proc = subprocess.run(
                [
                    "osascript",
                    "-e",
                    "on run argv",
                    "-e",
                    'tell application "Safari"',
                    "-e",
                    'if (count of windows) = 0 then error "No Safari window"',
                    "-e",
                    "set t to current tab of front window",
                    "-e",
                    "set js to item 1 of argv",
                    "-e",
                    "try",
                    "-e",
                    "return do JavaScript js in t",
                    "-e",
                    "on error",
                    "-e",
                    "return missing value",
                    "-e",
                    "end try",
                    "-e",
                    "end tell",
                    "-e",
                    "end run",
                    js,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(exc.stderr.strip() or "Safari JavaScript execution failed") from exc
        out = (proc.stdout or "").strip()
        if out == "" or out.lower() == "missing value":
            return None
        if out in {"true", "false"}:
            return out == "true"
        try:
            return json.loads(out)
        except Exception:
            return out

    def title(self) -> str:
        value = self.evaluate("() => document.title")
        return value or ""

    def current_url(self) -> str:
        value = self.evaluate("() => window.location.href")
        return value or ""


def launch_safari_page(timeout_ms: int) -> tuple[Any, SafariPage]:
    try:
        from selenium import webdriver
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("缺少 selenium 依赖，请先安装后重试。") from exc

    try:
        driver = webdriver.Safari()
        driver.set_page_load_timeout(max(10, int(timeout_ms / 1000)))
        return driver, SafariPage(driver)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "无法启动 Safari 自动化。请在 Safari 开启“Develop > Allow Remote Automation”，并保持已登录小红书。"
        ) from exc


def launch_active_safari_page(timeout_ms: int) -> tuple[Any, SafariActiveTabPage]:
    page = SafariActiveTabPage(timeout_ms=timeout_ms)
    return None, page


def hide_safari_ui() -> None:
    """Best-effort hide/minimize Safari so automation runs unobtrusively."""
    scripts = [
        'tell application "Safari" to set visible to false',
        'tell application "Safari" to if (count of windows) > 0 then set miniaturized of front window to true',
    ]
    for script in scripts:
        try:
            subprocess.run(["osascript", "-e", script], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def with_retry(max_retries: int, fn: Any) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == max_retries:
                raise
            time.sleep(min(2 * attempt, 5))
    raise RuntimeError("Unexpected retry failure") from last_error


def wait_for_content(page: Any, timeout_ms: int) -> None:
    end = time.time() + (timeout_ms / 1000)
    while time.time() < end:
        has_content = page.evaluate(
            """
            () => {
                return !!(
                    document.querySelector('#detail-desc') ||
                    document.querySelector('.note-content') ||
                    document.querySelector('.desc') ||
                    document.querySelector('article')
                );
            }
            """
        )
        if has_content:
            return
        time.sleep(0.2)


def is_login_page_text(page: Any) -> bool:
    return bool(
        page.evaluate(
            """
            () => {
                const text = (document.body?.innerText || '').slice(0, 4000);
                const keys = [
                    '手机号登录',
                    '获取验证码',
                    '扫码登录',
                    '请先登录',
                    '登录后查看更多',
                    '小红书如何扫码'
                ];
                if (keys.some(k => text.includes(k))) return true;
                const inputs = [
                    'input[type="password"]',
                    'input[name*="phone"]',
                    'input[placeholder*="验证码"]',
                ];
                return inputs.some(s => document.querySelector(s));
            }
            """
        )
    )


def is_login_required(page: Any) -> bool:
    return bool(
        page.evaluate(
            """
            () => {
                if (window.location.pathname.includes('/login')) return true;
                const text = (document.body?.innerText || '').slice(0, 5000);
                const keys = ['登录后查看更多', '请先登录', '扫码登录', '登录后可见', '马上登录即可'];
                const hasLoginText = keys.some(k => text.includes(k));
                const hasTitle = !!document.querySelector('h1');
                const hasContent = !!(
                    document.querySelector('#detail-desc') ||
                    document.querySelector('.note-content') ||
                    document.querySelector('.desc') ||
                    document.querySelector('article')
                );
                if (hasContent || hasTitle) return false;
                return hasLoginText;
            }
            """
        )
    )


def extract_dom_blocks(page: Any) -> dict[str, Any]:
    return page.evaluate(
        r"""
        () => {
            const title = (document.querySelector('h1')?.textContent || '').trim();
            const candidates = [
                '#detail-desc',
                '.note-content',
                '.desc',
                '.note-scroller .content',
                '.note-detail .content',
                'article'
            ];
            let container = null;
            for (const sel of candidates) {
                const el = document.querySelector(sel);
                if (el && el.innerText && el.innerText.trim().length > 0) {
                    container = el;
                    break;
                }
            }
            if (!container) container = document.body;

            const blocks = [];
            const textBuffer = [];
            const imageUrls = [];

            const pushText = () => {
                const text = textBuffer
                    .join(' ')
                    .replace(/\s+/g, ' ')
                    .replace(/\s*\n\s*/g, '\n')
                    .trim();
                textBuffer.length = 0;
                if (text) blocks.push({ type: 'text', text });
            };

            const isVisible = (el) => {
                if (!(el instanceof Element)) return true;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden';
            };

            const isValidImage = (img) => {
                const src = img.currentSrc || img.src || '';
                if (!src || !/^https?:\/\//.test(src)) return false;
                if (/avatar|profile|icon|emoji/i.test(src)) return false;
                if (/data:image\//i.test(src)) return false;
                const rect = img.getBoundingClientRect();
                if (rect.width > 80 && rect.height > 80) return true;
                if ((img.naturalWidth || 0) > 120 && (img.naturalHeight || 0) > 120) return true;
                return false;
            };

            const blockTags = new Set(['P', 'DIV', 'SECTION', 'ARTICLE', 'LI', 'BR', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6']);

            const walk = (node) => {
                if (!node) return;
                if (node.nodeType === Node.TEXT_NODE) {
                    const text = (node.textContent || '').trim();
                    if (text) textBuffer.push(text);
                    return;
                }
                if (node.nodeType !== Node.ELEMENT_NODE) return;
                const el = node;
                if (!isVisible(el)) return;
                const tag = el.tagName;

                if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') return;

                if (tag === 'IMG' && isValidImage(el)) {
                    pushText();
                    const src = el.currentSrc || el.src;
                    blocks.push({ type: 'image', src });
                    imageUrls.push(src);
                    return;
                }

                for (const child of el.childNodes) {
                    walk(child);
                }

                if (blockTags.has(tag)) {
                    pushText();
                }
            };

            walk(container);
            pushText();

            const contentLines = (container?.innerText || '')
                .split(/\n+/)
                .map(line => line.trim())
                .filter(Boolean)
                .slice(0, 10);
            const contentTitle = contentLines.length ? contentLines[0] : '';

            const pageImgs = Array.from(document.querySelectorAll('img'));
            for (const img of pageImgs) {
                const src = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                if (!src || !/^https?:\/\//.test(src)) continue;
                if (/avatar|profile|icon|emoji/i.test(src)) continue;
                if (!/xhs|xhscdn|sns-webpic/i.test(src)) continue;
                if (!imageUrls.includes(src)) imageUrls.push(src);
            }

            const author = (
                document.querySelector('.author-wrapper .name')?.textContent ||
                document.querySelector('[class*=author] [class*=name]')?.textContent ||
                ''
            ).trim();

            return { title, content_title: contentTitle, content_lines: contentLines, author, blocks, image_urls: imageUrls };
        }
        """
    )


def extract_state_note(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
            const out = { title: '', author: '', desc: '', image_urls: [], note_id: '' };
            const scripts = Array.from(document.querySelectorAll('script[type=\"application/ld+json\"]'));
            for (const script of scripts) {
                try {
                    const data = JSON.parse(script.textContent || '{}');
                    if (typeof data?.headline === 'string' && !out.title) out.title = data.headline.trim();
                    if (typeof data?.description === 'string' && !out.desc) out.desc = data.description.trim();
                    if (typeof data?.author?.name === 'string' && !out.author) out.author = data.author.name.trim();
                    if (Array.isArray(data?.image)) {
                        for (const image of data.image) {
                            if (typeof image === 'string' && image) out.image_urls.push(image);
                        }
                    }
                } catch (_) {}
            }
            const match = window.location.pathname.match(/\\/explore\\/([a-zA-Z0-9]+)/);
            if (match && match[1]) out.note_id = match[1];
            return out;
        }
        """
    )


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if not item:
            continue
        if item.startswith("//"):
            item = "https:" + item
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output


def build_note_data(page: Any, url: str) -> NoteData:
    dom_data = extract_dom_blocks(page)
    state_data = extract_state_note(page)

    page_title = clean_title(page.title())
    content_title = clean_title((dom_data.get("content_title") or "").strip())
    if not looks_like_title(content_title):
        content_title = ""
    if not content_title:
        for line in dom_data.get("content_lines") or []:
            candidate = clean_title(str(line).strip())
            if looks_like_title(candidate):
                content_title = candidate
                break

    preferred_page_title = page_title if page_title and page_title not in {"小红书 - 你的生活兴趣社区", "小红书"} else ""

    title = (
        clean_title((dom_data.get("title") or "").strip())
        or clean_title((state_data.get("title") or "").strip())
        or content_title
        or preferred_page_title
        or page_title
    )
    author = (dom_data.get("author") or "").strip() or (state_data.get("author") or "").strip()

    blocks = dom_data.get("blocks") if isinstance(dom_data.get("blocks"), list) else []
    cleaned_blocks: list[dict[str, str]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("type") or "").strip()
        if block_type == "text":
            text = str(block.get("text") or "").strip()
            if text:
                if cleaned_blocks and cleaned_blocks[-1].get("type") == "text" and cleaned_blocks[-1].get("text") == text:
                    continue
                cleaned_blocks.append({"type": "text", "text": text})
        elif block_type == "image":
            src = str(block.get("src") or "").strip()
            if src:
                cleaned_blocks.append({"type": "image", "src": src})

    if not any(block.get("type") == "text" for block in cleaned_blocks):
        desc = (state_data.get("desc") or "").strip()
        if desc:
            for line in [x.strip() for x in re.split(r"\r?\n+", desc) if x.strip()]:
                cleaned_blocks.append({"type": "text", "text": line})

    image_urls = dedupe_keep_order(
        [
            *(dom_data.get("image_urls") or []),
            *(state_data.get("image_urls") or []),
        ]
    )

    has_image_in_blocks = any(block.get("type") == "image" for block in cleaned_blocks)
    if image_urls and not has_image_in_blocks:
        for img in image_urls:
            cleaned_blocks.append({"type": "image", "src": img})

    block_images = dedupe_keep_order([block.get("src", "") for block in cleaned_blocks if block.get("type") == "image"])
    for extra in image_urls:
        if extra not in block_images:
            cleaned_blocks.append({"type": "image", "src": extra})

    note_id = (state_data.get("note_id") or "").strip() or extract_note_id(url)
    if not title:
        title = note_id

    return NoteData(
        note_id=note_id,
        url=url,
        title=title,
        author=author,
        blocks=cleaned_blocks,
        image_urls=image_urls,
    )


def detect_page_media(page: Any) -> dict[str, Any]:
    data = page.evaluate(
        r"""
        () => {
            const imgs = Array.from(document.querySelectorAll('img'));
            const candidateUrls = [];
            let loadedCandidateCount = 0;
            for (const img of imgs) {
                const src = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                if (!src || !/^https?:\/\//.test(src)) continue;
                if (/avatar|profile|icon|emoji/i.test(src)) continue;
                if (!/xhs|xhscdn|sns-webpic/i.test(src)) continue;
                candidateUrls.push(src);
                const rect = img.getBoundingClientRect();
                if (rect.width > 80 && rect.height > 80) loadedCandidateCount += 1;
            }
            return {
                page_img_count: imgs.length,
                candidate_image_count: Array.from(new Set(candidateUrls)).length,
                loaded_candidate_count: loadedCandidateCount,
            };
        }
        """
    )
    if not isinstance(data, dict):
        return {
            "page_img_count": 0,
            "candidate_image_count": 0,
            "loaded_candidate_count": 0,
        }
    return {
        "page_img_count": int(data.get("page_img_count") or 0),
        "candidate_image_count": int(data.get("candidate_image_count") or 0),
        "loaded_candidate_count": int(data.get("loaded_candidate_count") or 0),
    }


def count_image_blocks(note_data: NoteData) -> int:
    return sum(1 for block in note_data.blocks if block.get("type") == "image")


def should_retry_note_extraction(media_info: dict[str, Any], extracted_images: int) -> bool:
    candidate_count = int(media_info.get("candidate_image_count") or 0)
    if candidate_count <= 0:
        return False
    if extracted_images >= candidate_count:
        return False
    return extracted_images <= max(1, candidate_count // 2)


def collect_note_data(page: Any, url: str, timeout_ms: int) -> tuple[NoteData, dict[str, Any]]:
    note_data = build_note_data(page, url)
    media_info = detect_page_media(page)

    retries = 0
    while media_info["candidate_image_count"] > 0 and count_image_blocks(note_data) == 0 and retries < 3:
        retries += 1
        log(
            "Detected candidate page images but extracted 0 image blocks; "
            f"retrying parse ({retries}/3)."
        )
        time.sleep(1.0)
        wait_for_content(page, timeout_ms=min(2000, timeout_ms))
        note_data = build_note_data(page, url)
        media_info = detect_page_media(page)

    return note_data, media_info


def download_image(url: str, target: Path, timeout_sec: int, max_retries: int) -> None:
    if url.startswith("//"):
        url = "https:" + url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.xiaohongshu.com/",
    }

    def _do_request() -> None:
        resp = requests.get(url, headers=headers, timeout=timeout_sec)
        resp.raise_for_status()
        target.write_bytes(resp.content)

    with_retry(max_retries, _do_request)


def run_ocr(ocr_engine: Any, image_path: Path) -> str:
    lines: list[str] = []

    if hasattr(ocr_engine, "predict"):
        result = ocr_engine.predict(str(image_path))
        for page_result in result or []:
            if hasattr(page_result, "get"):
                rec_texts = page_result.get("rec_texts") or []
                for text in rec_texts:
                    text_s = str(text).strip()
                    if text_s:
                        lines.append(text_s)
        return compact_ocr_lines(lines)

    result = ocr_engine.ocr(str(image_path), cls=True)
    if not result:
        return ""
    for page_result in result:
        if not page_result:
            continue
        for row in page_result:
            if not isinstance(row, list) or len(row) < 2:
                continue
            text_info = row[1]
            if isinstance(text_info, (list, tuple)) and text_info:
                text = str(text_info[0]).strip()
                if text:
                    lines.append(text)
    return compact_ocr_lines(lines)


def compact_ocr_lines(lines: list[str]) -> str:
    """Merge OCR line wraps while preserving blank line separators."""
    expanded: list[str] = []
    for raw in lines:
        if raw is None:
            continue
        for part in str(raw).split("\n"):
            expanded.append(part)

    normalized: list[str] = []
    for line in expanded:
        if line.strip() == "":
            normalized.append("")
        else:
            normalized.append(re.sub(r"\s+", " ", line).strip())

    paragraphs: list[list[str]] = []
    current: list[str] = []
    blank_runs: list[int] = []
    blank_count = 0

    for line in normalized:
        if line == "":
            if current:
                paragraphs.append(current)
                current = []
            blank_count += 1
            continue
        if blank_count:
            blank_runs.append(blank_count)
            blank_count = 0
        current.append(line)
    if current:
        paragraphs.append(current)
    if blank_count:
        blank_runs.append(blank_count)

    merged_paragraphs: list[str] = []
    for para in paragraphs:
        if not para:
            continue
        merged = para[0]
        for nxt in para[1:]:
            if not merged:
                merged = nxt
                continue
            prev_last = merged[-1]
            next_first = nxt[0] if nxt else ""
            # If OCR split indicates a sentence-ended line then a new line,
            # keep a blank line between them to preserve original visual paragraphing.
            if prev_last in "。！？!?；;" and next_first:
                merged = f"{merged}\n\n{nxt}"
                continue
            # For latin words/numbers split by OCR, keep a space; for Chinese, join directly.
            if prev_last.isascii() and prev_last.isalnum() and next_first.isascii() and next_first.isalnum():
                merged = f"{merged} {nxt}"
            else:
                merged = f"{merged}{nxt}"
        merged_paragraphs.append(merged.strip())

    if not merged_paragraphs:
        return ""

    output: list[str] = [merged_paragraphs[0]]
    for idx, para in enumerate(merged_paragraphs[1:], start=1):
        blanks = blank_runs[idx - 1] if idx - 1 < len(blank_runs) else 1
        output.append("\n" * max(1, blanks))
        output.append(para)

    return "".join(output).strip()


def prepare_image_for_ocr(image_path: Path, max_side: int = 1280) -> Path:
    """Downscale large images for faster OCR while keeping readability."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            longest = max(width, height)
            if longest <= max_side:
                return image_path
            scale = max_side / float(longest)
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
            ocr_path = image_path.with_name(f"{image_path.stem}_ocr.jpg")
            resized.save(ocr_path, format="JPEG", quality=85, optimize=True)
            return ocr_path
    except Exception:  # noqa: BLE001
        return image_path


def indent_paragraphs(text: str, indent: str = "　　") -> str:
    """Indent the first line of each paragraph by 2em (two full-width spaces)."""
    if not text:
        return text
    lines = text.split("\n")
    output: list[str] = []
    at_paragraph_start = True
    for line in lines:
        if line.strip() == "":
            output.append("")
            at_paragraph_start = True
            continue
        if at_paragraph_start:
            output.append(f"{indent}{line}")
            at_paragraph_start = False
        else:
            output.append(line)
    return "\n".join(output)


def indent_body_preserving_header(text: str, indent: str = "　　") -> str:
    """Indent every paragraph in body while keeping title/author unindented."""
    lines = text.split("\n")
    if not lines:
        return text

    # Identify header lines: title (first non-empty), optional author line.
    idx = 0
    header_lines: list[str] = []
    while idx < len(lines) and lines[idx].strip() == "":
        header_lines.append(lines[idx])
        idx += 1
    if idx < len(lines):
        header_lines.append(lines[idx])
        idx += 1
    if idx < len(lines) and lines[idx].startswith("作者:"):
        header_lines.append(lines[idx])
        idx += 1

    body_text = "\n".join(lines[idx:]).lstrip("\n")
    if not body_text:
        return "\n".join(header_lines).rstrip()
    body_text = indent_paragraphs(body_text, indent=indent)
    return "\n".join(header_lines).rstrip() + "\n\n" + body_text


def normalize_for_compare(text: str) -> str:
    if not text:
        return ""
    # Keep CJK/latin/numbers, remove separators for robust duplicate detection.
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).lower()


def is_duplicate_ocr_block(ocr_text: str, existing_text: str) -> bool:
    ocr_norm = normalize_for_compare(ocr_text)
    existing_norm = normalize_for_compare(existing_text)
    if not ocr_norm or not existing_norm:
        return False
    # Quick containment check first.
    if len(ocr_norm) >= 80 and ocr_norm in existing_norm:
        return True
    # Fuzzy check for near-duplicate long blocks.
    if len(ocr_norm) >= 120:
        ratio = SequenceMatcher(None, ocr_norm[:4000], existing_norm[:4000]).ratio()
        if ratio >= 0.90:
            return True
        # Robust duplicate detection under OCR noise:
        # if a very long common contiguous fragment exists, treat as duplicate.
        longest = SequenceMatcher(None, ocr_norm, existing_norm).find_longest_match(0, len(ocr_norm), 0, len(existing_norm)).size
        if longest >= 200 and (longest / max(1, len(ocr_norm))) >= 0.55:
            return True
    return False


def ensure_paths(out_dir: Path, file_stem: str) -> tuple[Path, Path]:
    note_dir = out_dir / file_stem
    image_dir = note_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    # Clean previous images to avoid stale ordering/confusion across runs.
    for old in image_dir.glob("image_*.jpg"):
        old.unlink(missing_ok=True)
    txt_path = out_dir / f"{file_stem}.txt"
    return txt_path, image_dir


def render_note_content(
    note_data: NoteData,
    media_info: dict[str, Any],
    txt_path: Path,
    image_dir: Path,
    args: argparse.Namespace,
    paddle_ocr_cls: Any,
) -> tuple[int, Any]:
    body_segments: list[str] = []
    existing_text_for_dedupe = ""

    ocr_engine: Any | None = None
    image_counter = 0
    total_images = count_image_blocks(note_data)
    deferred_first_image: list[str] | None = None

    for block in note_data.blocks:
        block_type = block.get("type")

        if block_type == "text":
            content = (block.get("text") or "").strip()
            if content:
                indented = indent_paragraphs(content)
                body_segments.append(indented)
                existing_text_for_dedupe += "\n" + indented
            continue

        if block_type != "image":
            continue

        image_counter += 1
        image_url = (block.get("src") or "").strip()
        if not image_url:
            line = f"[图片{image_counter} OCR失败：empty image url]"
            if image_counter == 1 and total_images > 1:
                deferred_first_image = [line]
            else:
                body_segments.append(line)
                existing_text_for_dedupe += "\n" + line
            continue

        image_path = image_dir / f"image_{image_counter:03d}.jpg"

        try:
            log(f"OCR processing image {image_counter} ...")
            download_image(image_url, image_path, timeout_sec=args.timeout_sec, max_retries=args.max_retries)
            if ocr_engine is None:
                ocr_engine = paddle_ocr_cls(
                    lang="ch",
                    ocr_version="PP-OCRv4",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    text_det_limit_side_len=960,
                    text_recognition_batch_size=6,
                )

            ocr_input = prepare_image_for_ocr(image_path, max_side=1280)
            ocr_text = run_ocr(ocr_engine, ocr_input)
            if ocr_input != image_path and ocr_input.exists():
                ocr_input.unlink(missing_ok=True)
            if not ocr_text:
                raise RuntimeError("OCR empty result")

            if is_duplicate_ocr_block(ocr_text, existing_text_for_dedupe):
                continue

            if image_counter == 1 and total_images > 1:
                deferred_first_image = [ocr_text]
            else:
                indented_ocr = indent_paragraphs(ocr_text)
                body_segments.append(indented_ocr)
                existing_text_for_dedupe += "\n" + indented_ocr
        except Exception as exc:  # noqa: BLE001
            error_text = str(exc)
            line = f"[图片{image_counter} OCR失败：{error_text}]"
            if image_counter == 1 and total_images > 1:
                deferred_first_image = [line]
            else:
                body_segments.append(line)
                existing_text_for_dedupe += "\n" + line

    if deferred_first_image:
        if not is_duplicate_ocr_block("\n".join(deferred_first_image), existing_text_for_dedupe):
            indented_deferred = [indent_paragraphs(x) for x in deferred_first_image]
            body_segments.extend(indented_deferred)
            existing_text_for_dedupe += "\n" + "\n".join(indented_deferred)

    header = note_data.title.strip()
    if note_data.author:
        header += "\n\n" + f"作者: {note_data.author}"
    body = "".join(body_segments).strip()
    content = (header + ("\n\n" + body if body else "")).strip() + "\n"
    txt_path.write_text(content, encoding=args.encoding)

    extracted_images = count_image_blocks(note_data)
    print(
        "图片检测: "
        f"页面候选图片 {media_info['candidate_image_count']} 张, "
        f"实际提取图片 {extracted_images} 张",
        file=sys.stderr,
    )
    return extracted_images, ocr_engine


def main() -> int:
    args = parse_args()
    from paddleocr import PaddleOCR
    url = normalize_url(args.url)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    timeout_ms = int(args.timeout_sec * 1000)

    driver = None
    page = None

    try:
        if args.use_active_tab:
            driver, page = launch_active_safari_page(timeout_ms=timeout_ms)
        else:
            driver, page = launch_safari_page(timeout_ms=timeout_ms)
            if not args.show_browser:
                hide_safari_ui()

        log(f"Opening URL: {url}")

        def _goto() -> None:
            page.goto(url, timeout_ms=timeout_ms)
            # Extract as soon as DOM is ready to reduce bot-redirect window.
            page.wait_for_timeout(250)
            page.wait_for_load_state("domcontentloaded", timeout_ms=timeout_ms)

        with_retry(args.max_retries, _goto)
        final_url = page.current_url()
        input_id = extract_note_id_if_present(url)
        final_id = extract_note_id_if_present(final_url)
        if input_id and final_id and input_id != final_id:
            raise RuntimeError("页面已跳转到不同笔记，跳过保存与OCR。")
        wait_for_content(page, timeout_ms=min(5000, timeout_ms))
        note_data, media_info = collect_note_data(page, url, timeout_ms=timeout_ms)
        has_text_block = any((b.get("type") == "text" and (b.get("text") or "").strip()) for b in note_data.blocks)
        has_image_block = any(b.get("type") == "image" for b in note_data.blocks)
        login_page = is_login_required(page) or is_login_page_text(page)
        if (
            (login_page or note_data.title in {"小红书 - 你的生活兴趣社区", "小红书"})
            and not (has_text_block or has_image_block)
        ):
            if not args.use_active_tab:
                log("Detected login intercept in automated Safari session; retrying with active Safari tab.")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None
                page = launch_active_safari_page(timeout_ms=timeout_ms)[1]
                with_retry(args.max_retries, _goto)
                final_url = page.current_url()
                input_id = extract_note_id_if_present(url)
                final_id = extract_note_id_if_present(final_url)
                if input_id and final_id and input_id != final_id:
                    raise RuntimeError("页面已跳转到不同笔记，跳过保存与OCR。")
                wait_for_content(page, timeout_ms=min(5000, timeout_ms))
                note_data, media_info = collect_note_data(page, url, timeout_ms=timeout_ms)
                has_text_block = any((b.get("type") == "text" and (b.get("text") or "").strip()) for b in note_data.blocks)
                has_image_block = any(b.get("type") == "image" for b in note_data.blocks)
                login_page = is_login_required(page) or is_login_page_text(page)
            if (
                (login_page or note_data.title in {"小红书 - 你的生活兴趣社区", "小红书"})
                and not (has_text_block or has_image_block)
            ):
                raise RuntimeError("需重新登录小红书：当前页面显示登录拦截。")
        invalid_titles = {"小红书 - 你的生活兴趣社区", "小红书", "登录后推荐更懂你的笔记"}
        if note_data.title in invalid_titles:
            # Give it one more chance to load real content.
            wait_for_content(page, timeout_ms=min(15000, timeout_ms))
            note_data, media_info = collect_note_data(page, url, timeout_ms=timeout_ms)
            has_text_block = any((b.get("type") == "text" and (b.get("text") or "").strip()) for b in note_data.blocks)
            has_image_block = any(b.get("type") == "image" for b in note_data.blocks)
        if note_data.title in invalid_titles and not (has_text_block or has_image_block):
            raise RuntimeError("无效页面标题，跳过保存与OCR。")
        output_stem = safe_filename(note_data.title, note_data.note_id)
        txt_path, image_dir = ensure_paths(out_dir, output_stem)

        extracted_images, _ocr_engine = render_note_content(
            note_data=note_data,
            media_info=media_info,
            txt_path=txt_path,
            image_dir=image_dir,
            args=args,
            paddle_ocr_cls=PaddleOCR,
        )

        reruns = 0
        while should_retry_note_extraction(media_info, extracted_images) and reruns < 2:
            reruns += 1
            log(
                "Detected suspicious image extraction mismatch; "
                f"retrying full note extraction ({reruns}/2)."
            )
            with_retry(args.max_retries, _goto)
            wait_for_content(page, timeout_ms=min(5000, timeout_ms))
            note_data, media_info = collect_note_data(page, url, timeout_ms=timeout_ms)
            output_stem = safe_filename(note_data.title, note_data.note_id)
            txt_path, image_dir = ensure_paths(out_dir, output_stem)
            extracted_images, _ocr_engine = render_note_content(
                note_data=note_data,
                media_info=media_info,
                txt_path=txt_path,
                image_dir=image_dir,
                args=args,
                paddle_ocr_cls=PaddleOCR,
            )

        print(str(txt_path))
        return 0

    except Exception as exc:  # noqa: BLE001
        log(f"Error: {exc}")
        return 1
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
