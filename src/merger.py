"""
merger.py
---------
Worker 6: places generated TTS clips onto the original video timeline.

Each TTS clip is positioned using the original segment's start timestamp.
If the generated speech is longer than the original segment duration,
the speech is sped up slightly so that it fits inside that segment.

This prevents overlapping speech between consecutive segments.
"""

from pathlib import Path

from pydub import AudioSegment
from pydub.effects import speedup

from src.logger import log, log_error


OUTPUT_PATH = "data/audio/dubbed_audio.wav"


def _fit_audio_to_duration(audio, target_duration_ms):
    """
    Fit a TTS clip inside its original segment duration.

    If the TTS clip is already short enough, it is returned unchanged.

    If it is longer than the available segment duration, its playback
    speed is increased so that it fits without overlapping the next
    segment.
    """

    if target_duration_ms <= 0:
        return audio

    if len(audio) <= target_duration_ms:
        return audio

    required_speed = len(audio) / target_duration_ms

    # Only speed up when the adjustment is reasonable.
    # Avoid extreme speed changes that would make the speech unnatural.
    if required_speed <= 1.35:
        audio = speedup(
            audio,
            playback_speed=required_speed,
            chunk_size=150,
            crossfade=25,
        )

    # Make absolutely sure the clip does not exceed its segment.
    if len(audio) > target_duration_ms:
        audio = audio[:target_duration_ms]

    return audio


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

            # Fit generated speech inside the original segment window.
            original_audio_duration = len(audio)

            audio = _fit_audio_to_duration(
                audio,
                target_duration_ms,
            )

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
        f"Successfully placed "
        f"{successful}/{len(segments)} TTS clips."
    )

    return str(output_path)