#!/usr/bin/env python3
"""Send local TXT files to Kindle through the Reabble send page in Safari."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Iterable


SEND_PAGE_URL = "https://send.reabble.cn/send?from=bookmarklet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send local TXT files to Kindle through the Reabble send page in Safari."
    )
    parser.add_argument("files", nargs="+", help="Local TXT file paths to send")
    parser.add_argument(
        "--mail-to-name",
        help="Kindle mailbox local part, e.g. 'myname' for myname@free.kindle.com",
    )
    parser.add_argument(
        "--mail-to-domain",
        default="free.kindle.com",
        help="Kindle mailbox domain, e.g. free.kindle.com or kindle.com",
    )
    parser.add_argument(
        "--no-auto-send",
        action="store_true",
        help="Open the Reabble send page with the content loaded, but do not click Send",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the files that would be sent without opening Safari",
    )
    parser.add_argument(
        "--page-timeout-sec",
        type=int,
        default=30,
        help="How long to wait for page loads and bookmarklet navigation",
    )
    parser.add_argument(
        "--send-timeout-sec",
        type=int,
        default=30,
        help="How long to wait for the final Send success state",
    )
    return parser.parse_args()


def resolve_files(raw_files: Iterable[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw in raw_files:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise ValueError(f"Not a file: {path}")
        if path.suffix.lower() != ".txt":
            raise ValueError(f"Only .txt files are supported by this workflow: {path}")
        if not path.stat().st_size:
            raise ValueError(f"Empty file: {path}")
        resolved.append(path)
    return resolved


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8")


def build_html_document(title: str, text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    first_non_empty = next((line for line in lines if line), "")
    normalized_title = " ".join(title.split())
    normalized_first = " ".join(first_non_empty.split())
    if normalized_title and normalized_first == normalized_title:
        skipped = False
        filtered: list[str] = []
        for line in lines:
            if not skipped and line and " ".join(line.split()) == normalized_title:
                skipped = True
                continue
            filtered.append(line)
        lines = filtered

    body_parts: list[str] = [f"<h1>{html.escape(title)}</h1>"]
    for line in lines:
        if line:
            body_parts.append(f"<p>{html.escape(line)}</p>")
        else:
            body_parts.append("<p><br></p>")

    body_html = "\n".join(body_parts)
    return textwrap.dedent(
        f"""\
        <!doctype html>
        <html lang="zh-CN">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>{html.escape(title)}</title>
          <style>
            body {{
              font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
              margin: 40px auto;
              max-width: 760px;
              padding: 0 24px 80px;
              line-height: 1.75;
              color: #111;
            }}
            h1 {{ line-height: 1.2; margin-bottom: 1.2rem; }}
            p {{ margin: 0 0 1rem; }}
          </style>
        </head>
        <body>
        {body_html}
        </body>
        </html>
        """
    )


def build_submit_js(mail_to_name: str | None, mail_to_domain: str) -> str:
    name_value = repr(mail_to_name or "")
    domain_value = repr(mail_to_domain or "free.kindle.com")
    return textwrap.dedent(
        f"""
        (() => {{
          const nameInput = document.getElementById('input-mail-to-name');
          const domainSelect = document.querySelector('select[name="mailToDomain"]');
          const form = document.getElementById('form-send');
          const button = document.getElementById('btn-send');
          if (!nameInput || !domainSelect || !form || !button) {{
            return 'error:send-form-not-ready';
          }}

          const configuredName = {name_value};
          const configuredDomain = {domain_value};

          if (configuredName) {{
            nameInput.value = configuredName;
            localStorage.setItem('mailToName-value', configuredName);
          }}

          if (configuredDomain) {{
            let hasOption = Array.from(domainSelect.options).some((option) => option.value === configuredDomain);
            if (!hasOption) {{
              const option = document.createElement('option');
              option.value = configuredDomain;
              option.text = '@' + configuredDomain;
              domainSelect.appendChild(option);
            }}
            domainSelect.value = configuredDomain;
            localStorage.setItem('mailToDomain-value', configuredDomain);
          }}

          if (!nameInput.value.trim()) {{
            return 'error:mail-to-name-empty';
          }}

          button.disabled = false;
          form.dispatchEvent(new Event('submit', {{ bubbles: true, cancelable: true }}));
          return 'submitted:' + nameInput.value.trim() + '@' + domainSelect.value;
        }})()
        """
    ).strip()


def build_load_js(content_html: str) -> str:
    html_value = json.dumps(content_html)
    return textwrap.dedent(
        f"""
        (() => {{
          const editor = document.getElementById('editor');
          const urlInput = document.getElementById('input-url');
          if (!editor) {{
            return 'error:editor-not-ready';
          }}

          editor.innerHTML = {html_value};
          editor.classList.remove('editor-empty');
          if (urlInput) {{
            urlInput.value = '';
          }}
          if (window.Send && typeof window.Send.editorUpdate === 'function') {{
            window.Send.editorUpdate();
          }}
          return 'loaded';
        }})()
        """
    ).strip()


def run_applescript(script: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("LC_ALL", "en_US.UTF-8")
    return subprocess.run(
        ["osascript", "-", *args],
        input=script,
        text=True,
        capture_output=True,
        env=env,
    )


def run_safari_flow(
    load_js: str,
    submit_js: str,
    auto_send: bool,
    page_timeout_sec: int,
    send_timeout_sec: int,
) -> str:
    applescript = r'''
on cleanupSafari(targetWindowId, createdWindow, createdTabIndex, previousTabIndex, shouldQuit)
    tell application "Safari"
        try
            set targetWindow to first window whose id is targetWindowId
            if createdWindow then
                close targetWindow
            else
                try
                    close current tab of targetWindow
                end try
                if previousTabIndex is not missing value then
                    try
                        set current tab of targetWindow to tab previousTabIndex of targetWindow
                    end try
                end if
            end if
            if shouldQuit then
                quit
            end if
        end try
    end tell
end cleanupSafari

on run argv
    set pageUrl to item 1 of argv
    set loadJs to item 2 of argv
    set submitJs to item 3 of argv
    set autoSendFlag to item 4 of argv
    set pageTimeoutSec to (item 5 of argv) as integer
    set sendTimeoutSec to (item 6 of argv) as integer
    set createdWindow to false
    set createdTabIndex to missing value
    set previousTabIndex to missing value
    set targetWindowId to missing value
    set shouldQuit to false

    tell application "Safari"
        if not running then
            launch
            set shouldQuit to true
            delay 0.5
        end if
        if (count of windows) = 0 then
            make new document
            set createdWindow to true
        end if
        tell front window
            set targetWindowId to id
            if not createdWindow then
                set previousTabIndex to index of current tab
            end if
            set current tab to (make new tab with properties {URL:pageUrl})
            set createdTabIndex to index of current tab
        end tell
    end tell

    try
        set deadline to (current date) + pageTimeoutSec
        repeat while (current date) is less than deadline
            tell application "Safari"
                set currentUrl to URL of current tab of front window
            end tell
            if currentUrl starts with pageUrl then exit repeat
            delay 0.5
        end repeat

        set readyDeadline to (current date) + pageTimeoutSec
        repeat while (current date) is less than readyDeadline
            tell application "Safari"
                try
                    set pageState to do JavaScript "document.readyState + '|' + (!!document.getElementById(\"editor\"))" in current tab of front window
                on error
                    set pageState to ""
                end try
            end tell
            if pageState is "complete|true" then exit repeat
            delay 0.5
        end repeat

        tell application "Safari"
            set loadResult to do JavaScript loadJs in current tab of front window
        end tell
        if loadResult starts with "error:" then error loadResult

        if autoSendFlag is "false" then
            return "READY"
        end if

        tell application "Safari"
            set submitResult to do JavaScript submitJs in current tab of front window
        end tell
        if submitResult starts with "error:" then error submitResult

        set sendDeadline to (current date) + sendTimeoutSec
        repeat while (current date) is less than sendDeadline
            tell application "Safari"
                set statusResult to do JavaScript "(() => { const ok = document.getElementById('send-success-notification'); if (ok && !ok.classList.contains('hidden')) { return 'success'; } const notice = document.getElementById('notification'); if (notice && !notice.classList.contains('hidden')) { return 'error:' + notice.innerText.trim(); } return 'pending'; })()" in current tab of front window
            end tell
            if statusResult is "success" then
                my cleanupSafari(targetWindowId, createdWindow, createdTabIndex, previousTabIndex, shouldQuit)
                return "SENT"
            end if
            if statusResult starts with "error:" then error statusResult
            delay 0.5
        end repeat

        error "Timed out waiting for send confirmation"
    on error errMsg number errNum
        if autoSendFlag is not "false" then
            my cleanupSafari(targetWindowId, createdWindow, createdTabIndex, previousTabIndex, shouldQuit)
        end if
        error errMsg number errNum
    end try
end run
'''
    proc = run_applescript(
        applescript,
        [
            SEND_PAGE_URL,
            load_js,
            submit_js,
            "false" if not auto_send else "true",
            str(page_timeout_sec),
            str(send_timeout_sec),
        ],
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        if "error:mail-to-name-empty" in stderr:
            raise RuntimeError(
                "Reabble page does not have a configured Kindle mailbox. "
                "Pass --mail-to-name or fill it once manually on https://send.reabble.cn/send?from=bookmarklet"
            )
        if "error:send-form-not-ready" in stderr:
            raise RuntimeError("Reabble send form did not finish loading")
        if "error:editor-not-ready" in stderr:
            raise RuntimeError("Reabble editor did not finish loading")
        raise RuntimeError(stderr or "Safari automation failed")
    return (proc.stdout or "").strip()


def send_file(path: Path, args: argparse.Namespace) -> str:
    title = path.stem
    text = read_text(path)
    content_html = build_html_document(title, text)
    load_js = build_load_js(content_html)
    submit_js = build_submit_js(args.mail_to_name, args.mail_to_domain)

    return run_safari_flow(
        load_js=load_js,
        submit_js=submit_js,
        auto_send=not args.no_auto_send,
        page_timeout_sec=int(args.page_timeout_sec),
        send_timeout_sec=int(args.send_timeout_sec),
    )


def main() -> int:
    args = parse_args()
    files = resolve_files(args.files)

    if args.dry_run:
        print("DRY RUN")
        for path in files:
            print(path)
        print("AUTO_SEND")
        print("false" if args.no_auto_send else "true")
        print("DELIVERY")
        print("reabble")
        return 0

    for path in files:
        result = send_file(path, args)
        print(result)
        print(path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
