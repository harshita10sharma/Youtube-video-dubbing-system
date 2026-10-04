import wave

import pytest

np = pytest.importorskip("numpy")

from src.transcriber import _load_audio


def _write_wav(path, samples, rate=16000, channels=1):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.asarray(samples, dtype=np.int16).tobytes())


def test_16k_mono_wav_becomes_float_array(tmp_path):
    path = tmp_path / "a.wav"
    _write_wav(path, [0, 16384, -16384, 32767])

    audio = _load_audio(str(path))

    assert audio.dtype == np.float32
    assert len(audio) == 4
    assert abs(audio[1] - 0.5) < 1e-3 and abs(audio[2] + 0.5) < 1e-3


def test_other_formats_fall_back_to_the_path(tmp_path):
    path = tmp_path / "b.wav"
    _write_wav(path, [0, 1, 2, 3], rate=44100)

    assert _load_audio(str(path)) == str(path)


def test_non_wav_file_falls_back_to_the_path(tmp_path):
    path = tmp_path / "c.mp3"
    path.write_bytes(b"not a wav")

    assert _load_audio(str(path)) == str(path)
