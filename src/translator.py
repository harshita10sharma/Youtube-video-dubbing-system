"""
translator.py
-------------
Worker 4: translates each segment's text into natural English.
Keeps the original start/end timestamps untouched.
"""

import json
import time
from pathlib import Path

from deep_translator import GoogleTranslator

from src.logger import log, log_error


def translate_segments(segments, source_language: str, max_retries: int = 3):
    Path("data/transcripts").mkdir(parents=True, exist_ok=True)

    translator = GoogleTranslator(source=source_language, target="en")

    log(f"Translating {len(segments)} segments ({source_language} -> en)...")

    for i, segment in enumerate(segments):
        segment["translated"] = _translate_with_retry(
            translator,
            segment["text"],
            max_retries,
        )

        print(f"      [{i + 1}/{len(segments)}] {segment['translated']}")

        if (i + 1) % 20 == 0:
            _save_checkpoint(segments)

    _save_checkpoint(segments)
    log("Translation complete.")
    return segments


def _translate_with_retry(translator, text: str, max_retries: int) -> str:
    for attempt in range(1, max_retries + 1):
        try:
            result = translator.translate(text)
            if result:
                return result
        except Exception as e:
            log_error(f"translation attempt {attempt}/{max_retries} failed: {e}")
            time.sleep(1.5)

    log_error(f"giving up on this segment, keeping original text: {text[:50]!r}")
    return text


def _save_checkpoint(segments):
    with open("data/transcripts/translated.json", "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)