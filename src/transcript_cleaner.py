import json
from pathlib import Path

from src.logger import log


INPUT_PATH = "data/transcripts/transcript.json"
OUTPUT_PATH = "data/transcripts/cleaned_transcript.json"


def clean_transcript(segments):
    """
    Prepare the Whisper transcript for the translation stage.

    Keeps the original Whisper text and timestamps unchanged.
    Adds a separate cleaned_text field for later correction.
    """

    cleaned_segments = []

    for segment in segments:
        cleaned_segments.append(
            {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "cleaned_text": segment["text"],
            }
        )

    return cleaned_segments


def save_cleaned_transcript(segments):
    Path("data/transcripts").mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(
            segments,
            file,
            ensure_ascii=False,
            indent=2,
        )

    log(f"Cleaned transcript saved -> {OUTPUT_PATH}")


def clean_transcript_file():
    with open(INPUT_PATH, "r", encoding="utf-8") as file:
        segments = json.load(file)

    cleaned_segments = clean_transcript(segments)
    save_cleaned_transcript(cleaned_segments)

    return cleaned_segments


if __name__ == "__main__":
    clean_transcript_file()