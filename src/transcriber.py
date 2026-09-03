import json
from pathlib import Path

from faster_whisper import WhisperModel

from src.logger import log

MODEL_SIZE = "medium"


def transcribe_audio(audio_path: str):
    """
    Transcribe audio and automatically detect the source language.

    Parameters
    ----------
    audio_path : str
        Path to the audio file.

    Returns
    -------
    tuple
        transcript_data, detected_language
    """

    Path("data/transcripts").mkdir(parents=True, exist_ok=True)

    log(f"Loading Faster-Whisper model: {MODEL_SIZE}")

    model = WhisperModel(
        MODEL_SIZE,
        compute_type="int8"
    )

    log("Starting transcription with automatic language detection...")

    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        task="transcribe",
        vad_filter=True,
        condition_on_previous_text=False,
    )

    detected_language = info.language

    log(f"Detected source language: {detected_language}")

    transcript_data = []

    for segment in segments:

        text = segment.text.strip()

        if not text:
            continue

        transcript_data.append(
            {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text,
            }
        )

        print(
            f"[{segment.start:7.1f}s -> "
            f"{segment.end:7.1f}s] {text}"
        )

    output_path = "data/transcripts/transcript.json"

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            transcript_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    log(
        f"Transcript saved -> {output_path}"
    )

    return transcript_data, detected_language