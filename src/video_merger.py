"""
video_merger.py
--------------
Worker 7: combines the original video with the generated
synchronized English audio track.

The video stream is copied without re-encoding.
Only the audio is replaced.
"""

import subprocess
from pathlib import Path

from src.logger import log, log_error


OUTPUT_PATH = "data/output/dubbed_video.mp4"


def merge_audio_with_video(
    video_path: str,
    audio_path: str,
):
    """
    Replace the original video's audio with the generated
    synchronized English audio.

    The video stream is copied without re-encoding.
    """

    output_path = Path(OUTPUT_PATH)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]

    log("Combining original video with English audio...")

    try:
        subprocess.run(
            command,
            check=True,
        )

    except FileNotFoundError:
        log_error(
            "FFmpeg was not found. "
            "Make sure FFmpeg is installed and available in PATH."
        )
        raise

    except subprocess.CalledProcessError as e:
        log_error(
            f"FFmpeg failed with exit code {e.returncode}."
        )
        raise

    log(
        f"Dubbed video created -> {output_path}"
    )

    return str(output_path)