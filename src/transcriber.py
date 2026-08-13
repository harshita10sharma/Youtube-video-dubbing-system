import json
from pathlib import Path

from faster_whisper import WhisperModel

from src.logger import log

MODEL_SIZE = "base"

def transcribe_audio(audio_path: str):
    Path("data/transcripts").mkdir(parents=True, exist_ok=True)

    log(f"Loading Faster-Whisper model: {MODEL_SIZE}")

    model = WhisperModel(MODEL_SIZE, compute_type="int8")

    log("Starting transcription...")

    segments, info = model.transcribe(
    audio_path,
    beam_size=5,
    language="hi",
    task="transcribe"
    )

    transcript_data = []

    for segment in segments:
        transcript_data.append(
            {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
            }
        )

    output_path = "data/transcripts/transcript.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(transcript_data, file, ensure_ascii=False, indent=2)

    log(f"Detected language: {info.language}")
    log(f"Transcript saved -> {output_path}")

    return transcript_data