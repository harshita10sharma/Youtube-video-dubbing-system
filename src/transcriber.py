import json
import os
from pathlib import Path

from faster_whisper import WhisperModel

from src.logger import log

# "small" keeps CPU runs practical; on a GPU the much more accurate
# "large-v3" is fast enough (a T4 transcribes 15 minutes in ~2-3 minutes)
# and noticeably better for Hindi and other Indian languages.
# Override with the WHISPER_MODEL environment variable.
CPU_MODEL_SIZE = "small"
GPU_MODEL_SIZE = "large-v3"

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
        model_size = os.environ.get("WHISPER_MODEL") or (
            GPU_MODEL_SIZE if device == "cuda" else CPU_MODEL_SIZE
        )
        log(
            f"Loading Faster-Whisper model: {model_size} "
            f"({device}, {compute_type})"
        )
        _model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    return _model


def _load_audio(audio_path: str):
    """
    Read our 16 kHz mono 16-bit WAV straight into a float32 array.

    Faster-Whisper accepts a numpy array instead of a file path. Reading
    the WAV ourselves avoids its PyAV-based decoder, which fails with
    "open() got an unexpected keyword argument 'metadata_errors'" when an
    older PyAV is installed (a dependency conflict seen on Colab).
    Falls back to the path for any other audio format.
    """

    import wave

    try:
        import numpy as np

        with wave.open(audio_path, "rb") as wav:
            if (
                wav.getframerate() != 16000
                or wav.getnchannels() != 1
                or wav.getsampwidth() != 2
            ):
                return audio_path

            frames = wav.readframes(wav.getnframes())

        samples = np.frombuffer(frames, dtype=np.int16)
        return samples.astype(np.float32) / 32768.0

    except (ImportError, wave.Error, EOFError):
        return audio_path


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
        _load_audio(audio_path),
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