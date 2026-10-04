"""
timing.py
---------
Pure (dependency-free) helpers that decide how a generated speech clip
is fitted onto the original timeline.

Strategy, in order of preference (this avoids chopping off words):
  1. Clip fits its own segment window        -> keep unchanged.
  2. Clip may borrow the silent gap that follows the segment
     (up to the next segment's start)         -> keep unchanged.
  3. Still too long                           -> speed up, capped at
     MAX_SPEEDUP so speech stays intelligible.
  4. Still too long after the cap             -> trim with a fade-out
     (last resort, never reached for typical dubbing).
"""

MAX_SPEEDUP = 1.5


def available_window_ms(segments, index: int, video_duration_ms: int) -> int:
    """
    Milliseconds a clip starting at segments[index]["start"] may occupy:
    from its start until the next segment starts (or the video ends).
    """

    start_ms = int(segments[index]["start"] * 1000)

    if index + 1 < len(segments):
        limit_ms = int(segments[index + 1]["start"] * 1000)
    else:
        limit_ms = video_duration_ms

    limit_ms = min(limit_ms, video_duration_ms)

    return max(limit_ms - start_ms, 0)


def plan_fit(clip_ms: int, window_ms: int, max_speedup: float = MAX_SPEEDUP):
    """
    Decide how to fit a clip into a window.

    Returns (speed, trim_ms):
      speed   - playback speed factor to apply (1.0 = unchanged)
      trim_ms - length to trim to after speeding up, or None for no trim
    """

    if window_ms <= 0 or clip_ms <= window_ms:
        return 1.0, None

    required = clip_ms / window_ms
    speed = min(required, max_speedup)

    resulting_ms = int(clip_ms / speed)

    if resulting_ms > window_ms:
        return speed, window_ms

    return speed, None
