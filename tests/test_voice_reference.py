from src.voice_reference import rank_windows

LOUD, QUIET = -20.0, -70.0


def frames(*parts):
    """parts: (level, seconds) pairs -> list of 100 ms frame levels."""
    out = []
    for level, seconds in parts:
        out += [level] * int(seconds * 10)
    return out


def test_picks_steady_speech_over_choppy_audio():
    # 0-30 s: choppy (speech/silence alternating); 30-60 s: steady speech
    choppy = frames(*[(LOUD, 1), (QUIET, 1)] * 15)
    steady = frames((LOUD, 30))
    start, _ = rank_windows(choppy + steady, min_start_s=0, top_n=1)[0]
    assert start >= 30


def test_returns_separated_candidates():
    starts = [
        s for s, _ in rank_windows(frames((LOUD, 120)), min_start_s=0, top_n=3)
    ]
    assert len(starts) == 3
    assert all(
        abs(a - b) >= 20
        for i, a in enumerate(starts)
        for b in starts[i + 1:]
    )


def test_skips_intro_when_video_is_long_enough():
    start, _ = rank_windows(frames((LOUD, 60)), min_start_s=10, top_n=1)[0]
    assert start >= 10


def test_too_short_audio_gives_no_candidates():
    assert rank_windows(frames((LOUD, 5))) == []


def test_silence_gives_no_candidates():
    assert rank_windows(frames((QUIET, 60)), min_start_s=0) == []
