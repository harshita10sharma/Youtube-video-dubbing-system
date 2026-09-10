"""
ffmpeg_utils.py
---------------
Resolves the ffmpeg/ffprobe executables to use across the project.

On Windows, ffmpeg is not always reliably available on PATH in every
shell/process context. This module first tries the system PATH and
falls back to a known local install location if PATH resolution fails,
so every module calls one shared resolver instead of hardcoding paths.
"""

import os
import shutil
from pathlib import Path

# Fallback install location for this project's Windows environment.
_FALLBACK_DIR = (
    r"C:\ffmpeg-8.1.2-essentials_build\ffmpeg-8.1.2-essentials_build\bin"
)

_path_patched = False


def _ensure_on_path():
    """
    Some libraries (e.g. pydub's media probing) shell out to a bare
    'ffmpeg'/'ffprobe' name via the OS PATH and ignore any path passed
    to them explicitly. If neither is resolvable on PATH, add the
    fallback install directory to this process's PATH once so every
    caller - ours and third-party - can find them.
    """

    global _path_patched

    if _path_patched:
        return

    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        if Path(_FALLBACK_DIR).is_dir():
            os.environ["PATH"] = _FALLBACK_DIR + os.pathsep + os.environ.get("PATH", "")

    _path_patched = True


def _resolve(executable_name: str, fallback_filename: str) -> str:
    _ensure_on_path()

    found = shutil.which(executable_name)

    if found:
        return found

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
