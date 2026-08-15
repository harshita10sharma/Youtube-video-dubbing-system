"""
merger.py
---------
Worker 6: places generated TTS clips onto the original video timeline.

Each TTS clip is positioned using the original segment's start timestamp.
This prevents synchronization drift caused by simply concatenating clips.
"""

from pathlib import Path

from pydub import AudioSegment

from src.logger import log, log_error


OUTPUT_PATH = "data/audio/dubbed_audio.wav"


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

            # Do not allow the clip to start beyond the timeline.
            if start_ms >= len(timeline):
                log_error(
                    f"Segment {i} starts beyond video duration. "
                    f"Skipping."
                )
                continue

            # Trim only if the generated audio extends beyond
            # the original video duration.
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
                f"Placed at {segment['start']:.2f}s"
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
        f"Successfully placed {successful}/"
        f"{len(segments)} TTS clips."
    )

    return str(output_path)