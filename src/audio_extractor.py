import subprocess
from pathlib import Path

from src.logger import log

def extract_audio(video_path: str) -> str:
    Path("data/audio").mkdir(parents=True, exist_ok=True)

    output_audio = "data/audio/original.wav"

    command = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_audio,
    ]

    log("Extracting audio track from video (16kHz mono WAV)...")

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    log(f"Audio extracted -> {output_audio}")
    return output_audio