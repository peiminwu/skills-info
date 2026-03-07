#!/usr/bin/env python3
"""Apple Vision OCR helpers for macOS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
from typing import Any


@dataclass(frozen=True)
class VisionOCRConfig:
    recognition_level: str
    recognition_languages: tuple[str, ...]
    uses_language_correction: bool
    automatically_detects_language: bool
    minimum_text_height: float


def _load_frameworks() -> tuple[Any, Any, Any]:
    try:
        import Quartz
        import Vision
        from Foundation import NSURL
    except ImportError as exc:
        raise RuntimeError(
            "缺少 Apple Vision 运行依赖。请先执行 `pip install -r scripts/requirements.txt`。"
        ) from exc
    return Quartz, Vision, NSURL


class VisionOCREngine:
    def __init__(self, config: VisionOCRConfig) -> None:
        if platform.system() != "Darwin":
            raise RuntimeError("Apple Vision OCR 仅支持 macOS。")

        quartz_mod, vision_mod, nsurl_cls = _load_frameworks()
        self._quartz = quartz_mod
        self._vision = vision_mod
        self._nsurl = nsurl_cls
        self._config = config

    def _load_image(self, image_path: Path) -> Any:
        image_url = self._nsurl.fileURLWithPath_(str(image_path))
        image_source = self._quartz.CGImageSourceCreateWithURL(image_url, None)
        if image_source is None:
            raise RuntimeError(f"无法读取图片: {image_path}")

        cg_image = self._quartz.CGImageSourceCreateImageAtIndex(image_source, 0, None)
        if cg_image is None:
            raise RuntimeError(f"无法解码图片: {image_path}")
        return cg_image

    def _make_request(self) -> Any:
        request = self._vision.VNRecognizeTextRequest.alloc().init()

        level_map = {
            "fast": self._vision.VNRequestTextRecognitionLevelFast,
            "accurate": self._vision.VNRequestTextRecognitionLevelAccurate,
        }
        request.setRecognitionLevel_(level_map[self._config.recognition_level])
        request.setRecognitionLanguages_(list(self._config.recognition_languages))
        request.setUsesLanguageCorrection_(bool(self._config.uses_language_correction))

        if hasattr(request, "setAutomaticallyDetectsLanguage_"):
            request.setAutomaticallyDetectsLanguage_(bool(self._config.automatically_detects_language))

        if self._config.minimum_text_height > 0:
            request.setMinimumTextHeight_(float(self._config.minimum_text_height))

        return request

    @staticmethod
    def _observation_sort_key(observation: Any) -> tuple[float, float]:
        box = observation.boundingBox()
        top = float(box.origin.y + box.size.height)
        left = float(box.origin.x)
        return (-round(top, 4), round(left, 4))

    def recognize(self, image_path: Path) -> list[str]:
        cg_image = self._load_image(image_path)
        request = self._make_request()
        handler = self._vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)

        success, error = handler.performRequests_error_([request], None)
        if not success:
            if error is not None:
                raise RuntimeError(str(error))
            raise RuntimeError("Vision OCR 请求失败")

        observations = list(request.results() or [])
        observations.sort(key=self._observation_sort_key)

        output: list[str] = []
        for observation in observations:
            candidates = observation.topCandidates_(1)
            if not candidates:
                continue
            text = str(candidates[0].string()).strip()
            if text:
                output.append(text)
        return output


def build_vision_ocr_engine(config: VisionOCRConfig) -> VisionOCREngine:
    return VisionOCREngine(config)
