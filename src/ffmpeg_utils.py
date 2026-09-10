"""
ffmpeg_utils.py
---------------
Resolves the ffmpeg/ffprobe executables to use across the project.

On Windows, ffmpeg is not always reliably available on PATH in every
shell/process context. This module first tries the system PATH and
falls back to a known local install location if PATH resolution fails,
so every module calls one shared resolver instead of hardcoding paths.
"""

import shutil

# Fallback install location for this project's Windows environment.
_FALLBACK_DIR = (
    r"C:\ffmpeg-8.1.2-essentials_build\ffmpeg-8.1.2-essentials_build\bin"
)


def _resolve(executable_name: str, fallback_filename: str) -> str:
    found = shutil.which(executable_name)

    if found:
        return found

    from pathlib import Path

    fallback_path = Path(_FALLBACK_DIR) / fallback_filename

    if fallback_path.exists():
        return str(fallback_path)

    raise FileNotFoundError(
        f"Could not locate '{executable_name}'. "
        "Make sure FFmpeg is installed and available on PATH."
    )


def get_ffmpeg_path() -> str:
    return _resolve("ffmpeg", "ffmpeg.exe")


def get_ffprobe_path() -> str:
    return _resolve("ffprobe", "ffprobe.exe")
