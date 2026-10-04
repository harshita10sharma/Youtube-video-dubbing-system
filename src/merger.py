"""
merger.py
---------
Worker 6: places generated TTS clips onto the original video timeline.

Each TTS clip is positioned using the original segment's start timestamp.
If the generated speech is longer than its segment it may use the silent
gap before the next segment; if still too long it is sped up (capped at
1.5x) and only trimmed as a last resort. See src/timing.py.

This prevents overlapping speech between consecutive segments without
cutting words off.
"""

import os
import subprocess
import tempfile
from pathlib import Path

from pydub import AudioSegment

from src.ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path
from src.logger import log, log_error
from src.timing import available_window_ms, plan_fit

# pydub shells out to ffmpeg/ffprobe by name, which is not reliably
# resolvable on every Windows PATH. Point it at the resolved binaries.
AudioSegment.converter = get_ffmpeg_path()
AudioSegment.ffprobe = get_ffprobe_path()


OUTPUT_PATH = "data/audio/dubbed_audio.wav"


def _stretch(audio, speed):
    """
    Speed a clip up without changing pitch, using ffmpeg's atempo filter.

    atempo is a proper time-stretch and sounds much cleaner than
    pydub's chunk-based speedup, which produces audible artifacts.
    """

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.wav")
        dst = os.path.join(tmp, "out.wav")

        audio.export(src, format="wav")

        result = subprocess.run(
            [
                get_ffmpeg_path(),
                "-y", "-i", src,
                "-filter:a", f"atempo={speed:.4f}",
                dst,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"atempo failed:\n{result.stderr[-400:]}")

        return AudioSegment.from_file(dst)


def _fit_audio(audio, window_ms):
    """
    Fit a TTS clip into the time window available to it.

    Uses timing.plan_fit: keep as-is when it fits (including borrowing
    the silent gap after the segment), otherwise speed up (capped) and
    only as a last resort trim with a short fade-out.
    """

    speed, trim_ms = plan_fit(len(audio), window_ms)

    if speed > 1.0:
        audio = _stretch(audio, speed)

    was_trimmed = trim_ms is not None and len(audio) > trim_ms

    if was_trimmed:
        audio = audio[:trim_ms].fade_out(min(80, trim_ms))

    return audio, was_trimmed


def merge_tts_audio(segments, video_duration: float):
    """
    Place every TTS clip at its original timestamp and create one
    continuous English audio track.

    Parameters
    ----------
    segments : list
        Translated transcript segments containing:
        start, end and tts_path.

    video_duration : float
        Duration of the original video in seconds.

    Returns
    -------
    str
        Path to the generated synchronized audio file.
    """

    output_path = Path(OUTPUT_PATH)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Create a silent timeline matching the original video duration.
    timeline = AudioSegment.silent(
        duration=int(video_duration * 1000)
    )

    successful = 0
    sped_up = 0
    trimmed = 0

    log(
        f"Creating English audio timeline "
        f"({video_duration:.2f} seconds)..."
    )

    for i, segment in enumerate(segments):

        tts_path = segment.get("tts_path")

        if not tts_path:
            log_error(
                f"Segment {i} has no TTS file. Skipping."
            )
            continue

        if not Path(tts_path).exists():
            log_error(
                f"TTS file not found for segment {i}: "
                f"{tts_path}"
            )
            continue

        try:

            audio = AudioSegment.from_file(tts_path)

            start_ms = int(segment["start"] * 1000)
            end_ms = int(segment["end"] * 1000)

            target_duration_ms = end_ms - start_ms

            if target_duration_ms <= 0:
                log_error(
                    f"Invalid segment duration for segment {i}. "
                    f"Skipping."
                )
                continue

            window_ms = available_window_ms(
                segments,
                i,
                len(timeline),
            )

            original_audio_duration = len(audio)

            audio, was_trimmed = _fit_audio(audio, window_ms)

            if len(audio) < original_audio_duration:
                sped_up += 1

            if was_trimmed:
                trimmed += 1

            if len(audio) < original_audio_duration:
                print(
                    f"      [{i + 1}/{len(segments)}] "
                    f"Speed-adjusted "
                    f"{original_audio_duration / 1000:.2f}s -> "
                    f"{len(audio) / 1000:.2f}s"
                )

            # Do not allow the clip to start beyond the timeline.
            if start_ms >= len(timeline):
                log_error(
                    f"Segment {i} starts beyond video duration. "
                    f"Skipping."
                )
                continue

            # Make absolutely sure the clip cannot extend beyond
            # the original video timeline.
            remaining_ms = len(timeline) - start_ms

            if len(audio) > remaining_ms:
                audio = audio[:remaining_ms]

            timeline = timeline.overlay(
                audio,
                position=start_ms,
            )

            successful += 1

            print(
                f"      [{i + 1}/{len(segments)}] "
                f"Placed at {segment['start']:.2f}s "
                f"-> {segment['end']:.2f}s"
            )

        except Exception as e:

            log_error(
                f"Failed to place TTS for segment {i}: {e}"
            )

    timeline.export(
        output_path,
        format="wav",
    )

    log(
        f"Audio timeline created -> {output_path}"
    )

    log(
        f"Timing report: {sped_up} clips sped up, "
        f"{trimmed} clips hit the speed cap and were trimmed."
    )

    log(
        f"Successfully placed "
        f"{successful}/{len(segments)} TTS clips."
    )

    return str(output_path)