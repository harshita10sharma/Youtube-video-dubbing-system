import json
from pathlib import Path

from faster_whisper import WhisperModel

from src.logger import log

MODEL_SIZE = "small"

# Loaded once and reused across calls (loading is slow).
_model = None


def _pick_device():
    """GPU with float16 when CUDA is available, else CPU with int8."""

    try:
        import torch

        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass

    return "cpu", "int8"


def _get_model():
    global _model

    if _model is None:
        device, compute_type = _pick_device()
        log(
            f"Loading Faster-Whisper model: {MODEL_SIZE} "
            f"({device}, {compute_type})"
        )
        _model = WhisperModel(
            MODEL_SIZE,
            device=device,
            compute_type=compute_type,
        )

    return _model


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

    model = _get_model()

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