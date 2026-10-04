from src.timing import MAX_SPEEDUP, available_window_ms, plan_fit


def test_clip_that_fits_is_unchanged():
    assert plan_fit(3000, 4000) == (1.0, None)


def test_slightly_long_clip_is_sped_up_without_trim():
    speed, trim = plan_fit(5000, 4000)
    assert speed == 1.25 and trim is None


def test_very_long_clip_is_capped_then_trimmed():
    speed, trim = plan_fit(10000, 4000)
    assert speed == MAX_SPEEDUP and trim == 4000


def test_zero_window_is_left_alone():
    assert plan_fit(1000, 0) == (1.0, None)


def test_window_borrows_gap_until_next_segment():
    segs = [{"start": 1.0, "end": 2.0}, {"start": 4.0, "end": 5.0}]
    assert available_window_ms(segs, 0, 10000) == 3000


def test_last_segment_window_ends_at_video_end():
    segs = [{"start": 1.0, "end": 2.0}, {"start": 4.0, "end": 5.0}]
    assert available_window_ms(segs, 1, 6000) == 2000


def test_stretch_shortens_clip_when_ffmpeg_available():
    import pytest

    try:
        from pydub import AudioSegment
        from src.ffmpeg_utils import get_ffmpeg_path

        get_ffmpeg_path()
    except Exception:
        pytest.skip("pydub/ffmpeg not available")

    from src.merger import _stretch

    clip = AudioSegment.silent(duration=3000)
    out = _stretch(clip, 1.5)
    assert 1900 <= len(out) <= 2100
