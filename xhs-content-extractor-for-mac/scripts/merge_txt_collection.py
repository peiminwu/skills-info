#!/usr/bin/env python3
"""Merge multiple TXT exports into a single anthology TXT."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge multiple TXT files into a single anthology TXT.")
    parser.add_argument("inputs", nargs="+", help="Input TXT files in anthology order")
    parser.add_argument("--output", required=True, help="Output TXT path")
    parser.add_argument("--title", help="Anthology title shown at the top of the merged file")
    parser.add_argument("--encoding", default="utf-8-sig", help="Output encoding (default: utf-8-sig)")
    return parser.parse_args()


def resolve_inputs(raw_inputs: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw in raw_inputs:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise ValueError(f"Not a file: {path}")
        if path.suffix.lower() != ".txt":
            raise ValueError(f"Only .txt inputs are supported: {path}")
        resolved.append(path)
    return resolved


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8")


def build_merged_text(inputs: list[Path], title: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts: list[str] = [title, f"生成时间：{timestamp}", "", "目录"]
    for index, path in enumerate(inputs, start=1):
        parts.append(f"{index}. {path.stem}")

    for index, path in enumerate(inputs, start=1):
        body = read_text(path).strip()
        parts.extend(
            [
                "",
                "",
                "=" * 24,
                f"第 {index} 篇｜{path.stem}",
                "=" * 24,
                "",
                body,
            ]
        )

    return "\n".join(parts).strip() + "\n"


def main() -> int:
    args = parse_args()
    inputs = resolve_inputs(list(args.inputs))
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    title = args.title or f"{inputs[0].stem} 等{len(inputs)}篇合集"
    merged = build_merged_text(inputs, title)
    output.write_text(merged, encoding=args.encoding)

    print(output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
