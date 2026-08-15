"""
tts_engine.py
-------------
Worker 5: converts translated English text into speech using Edge TTS.

Each translated segment is saved as a separate audio file.
The original timestamps are preserved so the files can later be
placed correctly on the final audio timeline.
"""

import asyncio
from pathlib import Path

import edge_tts

from src.logger import log, log_error


VOICE = "en-US-AriaNeural"

OUTPUT_DIR = Path("data/audio/tts")


async def _generate_speech(text: str, output_path: str):
    """
    Generate one English speech clip using Edge TTS.
    """

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
    )

    await communicate.save(output_path)


def _generate_one(text: str, output_path: str):
    """
    Run the asynchronous Edge TTS generation.
    """

    asyncio.run(
        _generate_speech(
            text,
            output_path,
        )
    )


def create_tts_files(segments):
    """
    Generate one English TTS audio file for every translated segment.

    The generated file path is stored in the segment as 'tts_path'.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    log(
        f"Generating English speech for {len(segments)} segments..."
    )

    successful = 0

    for i, segment in enumerate(segments):

        text = segment.get("translated", "").strip()

        if not text:
            log_error(
                f"Skipping segment {i}: translated text is empty."
            )
            continue

        output_path = OUTPUT_DIR / f"seg_{i:04d}.mp3"

        try:

            _generate_one(
                text,
                str(output_path),
            )

            segment["tts_path"] = str(output_path)

            successful += 1

            print(
                f"      [{i + 1}/{len(segments)}] "
                f"TTS created -> {output_path}"
            )

        except Exception as e:

            log_error(
                f"TTS failed for segment {i}: {e}"
            )

    log(
        f"TTS generation complete: "
        f"{successful}/{len(segments)} files created."
    )

    return segments