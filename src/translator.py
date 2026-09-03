"""
translator.py
-------------
Worker 4: translates transcript segments from the detected
source language into natural English.

Before translation, short Whisper segments are merged into larger
sentence-level chunks so the translator has enough context to produce
more natural, meaning-based English.

Indic languages supported by IndicTrans2 are routed through
IndicTrans2. Other languages use the general GoogleTranslator.

Timestamps are preserved from the original transcript.
"""

import json
import time
from pathlib import Path

from deep_translator import GoogleTranslator

from src.logger import log, log_error


def merge_short_segments(
    segments,
    max_gap: float = 0.6,
    max_duration: float = 12.0,
):
    """
    Merge consecutive Whisper segments into larger sentence-level chunks
    before translation.

    Two segments are merged when:
    - the gap between them is <= max_gap seconds
    - the combined duration is <= max_duration seconds

    This gives the translator more context and produces more natural
    English instead of translating tiny fragments independently.
    """

    if not segments:
        return segments

    merged = [dict(segments[0])]

    for seg in segments[1:]:
        last = merged[-1]

        gap = seg["start"] - last["end"]
        combined_duration = seg["end"] - last["start"]

        if gap <= max_gap and combined_duration <= max_duration:
            last["text"] = (
                last["text"].rstrip()
                + " "
                + seg["text"].lstrip()
            ).strip()

            last["end"] = seg["end"]

        else:
            merged.append(dict(seg))

    return merged


def _get_indic_translator():
    """
    Import IndicTrans2 only when an Indic language is detected.

    This keeps the heavy IndicTrans2 dependencies from being loaded
    for non-Indic videos.
    """

    from src.indic_translator import (
        IndicTranslator,
        is_indic_language,
    )

    return IndicTranslator, is_indic_language


def translate_segments(
    segments,
    source_language: str,
    max_retries: int = 3,
):
    """
    Translate transcript segments from the detected source language
    into English.

    Indic languages supported by IndicTrans2 use IndicTrans2.
    Other languages use GoogleTranslator.

    Short/fragmented Whisper segments are merged first so that
    translation receives enough context.
    """

    Path("data/transcripts").mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # Merge fragmented Whisper segments
    # ---------------------------------------------------------

    original_count = len(segments)

    segments = merge_short_segments(segments)

    log(
        f"Merged {original_count} Whisper segments "
        f"into {len(segments)} translation chunks."
    )

    # ---------------------------------------------------------
    # Check whether the detected language is Indic
    # ---------------------------------------------------------

    _, is_indic_language = _get_indic_translator()

    if is_indic_language(source_language):

        log(
            f"Detected Indic language '{source_language}'. "
            f"Using IndicTrans2 for translation."
        )

        IndicTranslator, _ = _get_indic_translator()

        translator = IndicTranslator()

        segments = translator.translate_segments(
            segments,
            source_language=source_language,
            batch_size=8,
        )

        # Save translated result.
        _save_checkpoint(segments)

        log("IndicTrans2 translation complete.")

        return segments

    # ---------------------------------------------------------
    # General-language translation
    # ---------------------------------------------------------

    translator = GoogleTranslator(
        source=source_language,
        target="en",
    )

    log(
        f"Translating {len(segments)} segments "
        f"({source_language} -> en) using general translator..."
    )

    for i, segment in enumerate(segments):

        segment["translated"] = _translate_with_retry(
            translator,
            segment["text"],
            max_retries,
        )

        print(
            f"      [{i + 1}/{len(segments)}] "
            f"{segment['translated']}"
        )

        # Save progress every 20 segments.
        if (i + 1) % 20 == 0:
            _save_checkpoint(segments)

    # Final save.
    _save_checkpoint(segments)

    log("Translation complete.")

    return segments


def _translate_with_retry(
    translator,
    text: str,
    max_retries: int,
) -> str:
    """
    Translate one segment with retry handling.
    """

    for attempt in range(1, max_retries + 1):

        try:
            result = translator.translate(text)

            if result:
                return result

        except Exception as e:

            log_error(
                f"translation attempt "
                f"{attempt}/{max_retries} failed: {e}"
            )

            time.sleep(1.5)

    # If translation fails completely, preserve the original text.
    log_error(
        f"giving up on this segment, "
        f"keeping original text: {text[:50]!r}"
    )

    return text


def _save_checkpoint(segments):
    """
    Save translated segments so progress is not lost if translation stops.
    """

    output_path = "data/transcripts/translated.json"

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            segments,
            f,
            ensure_ascii=False,
            indent=2,
        )