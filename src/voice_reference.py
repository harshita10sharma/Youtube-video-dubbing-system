"""
voice_reference.py
------------------
Finds clean samples of the speaker's voice inside the source video so the
voice-cloning TTS (Chatterbox) can imitate the original speaker.

How it works (no ML model, takes seconds):
  1. Measure loudness in 100 ms frames across the extracted audio.
  2. Slide a ~12 s window over the timeline and score it: it should be
     almost entirely speech (few pauses) and steady in loudness (music,
     applause and crowd noise make loudness jump around).
  3. Keep the best few non-overlapping windows and cut them from the
     *video* at 24 kHz (the 16 kHz Whisper audio is too low quality to
     clone from).

The user listens to the candidates and confirms one (see web_app.py).
"""

import statistics
import subprocess
from pathlib import Path

from src.ffmpeg_utils import get_ffmpeg_path
from src.logger import log

FRAME_MS = 100
WINDOW_S = 12
OUTPUT_DIR = Path("data/audio/reference")


def frame_levels(audio, frame_ms: int = FRAME_MS):
    """Loudness (dBFS) of every frame of a pydub AudioSegment."""

    levels = []

    for i in range(0, len(audio) - frame_ms + 1, frame_ms):
        level = audio[i:i + frame_ms].dBFS
        levels.append(max(level, -80.0))  # silence is -inf

    return levels


def rank_windows(
    levels,
    frame_ms: int = FRAME_MS,
    window_s: float = WINDOW_S,
    step_s: float = 1.0,
    min_start_s: float = 10.0,
    top_n: int = 3,
    min_gap_s: float = 20.0,
):
    """
    Return up to top_n (start_seconds, score) windows, best first.

    Pure function over a list of per-frame loudness values so it can be
    unit-tested without audio files.
    """

    frames_per_window = int(window_s * 1000 / frame_ms)
    step = max(int(step_s * 1000 / frame_ms), 1)

    if len(levels) < frames_per_window:
        return []

    # A frame counts as speech when it is within 18 dB of the loud end.
    p90 = sorted(levels)[int(0.9 * (len(levels) - 1))]

    if p90 < -60.0:
        return []  # effectively silent

    speech_threshold = p90 - 18.0

    # Skip intros (often music) unless the video is too short for that.
    first = int(min_start_s * 1000 / frame_ms)
    if len(levels) - first < frames_per_window:
        first = 0

    scored = []

    for start in range(first, len(levels) - frames_per_window + 1, step):
        window = levels[start:start + frames_per_window]
        speech = [v for v in window if v > speech_threshold]

        if len(speech) < 2:
            continue

        ratio = len(speech) / len(window)
        spread = statistics.pstdev(speech)

        # Mostly speech and steady loudness wins.
        score = ratio - 0.02 * spread

        scored.append((score, start * frame_ms / 1000.0))

    scored.sort(reverse=True)

    chosen = []

    for score, start_s in scored:
        if all(abs(start_s - other) >= min_gap_s for other, _ in chosen):
            chosen.append((start_s, round(score, 3)))

        if len(chosen) == top_n:
            break

    return chosen


def extract_reference_candidates(
    video_path: str,
    audio_path: str,
    top_n: int = 3,
    window_s: float = WINDOW_S,
):
    """
    Cut the best voice samples out of the video and return their paths
    (best first). Raises RuntimeError if no usable speech is found.
    """

    # Importing merger configures pydub to use the resolved ffmpeg.
    import src.merger  # noqa: F401
    from pydub import AudioSegment

    log("Looking for clean samples of the speaker's voice...")

    audio = AudioSegment.from_file(audio_path)
    windows = rank_windows(
        frame_levels(audio),
        window_s=window_s,
        top_n=top_n,
    )

    if not windows:
        raise RuntimeError(
            "Could not find a clean stretch of speech to use as a voice "
            "sample. Upload a reference voice WAV instead."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    paths = []

    for i, (start_s, score) in enumerate(windows, start=1):
        out = OUTPUT_DIR / f"candidate_{i}.wav"

        result = subprocess.run(
            [
                get_ffmpeg_path(),
                "-y",
                "-ss", f"{start_s:.2f}",
                "-t", f"{window_s}",
                "-i", video_path,
                "-vn", "-ac", "1", "-ar", "24000",
                str(out),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-400:]}")

        log(
            f"  candidate {i}: {start_s:.0f}s-{start_s + window_s:.0f}s "
            f"(score {score})"
        )
        paths.append(str(out))

    return paths
