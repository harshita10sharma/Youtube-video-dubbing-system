import pytest

from app import build_parser, main


def test_url_and_video_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--url", "u", "--video", "v"])


def test_source_is_optional_so_app_can_prompt():
    args = build_parser().parse_args([])
    assert args.url is None and args.video is None


def test_empty_prompt_exits_cleanly(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert main([]) == 2


def test_defaults():
    args = build_parser().parse_args(["--video", "x.mp4"])
    assert args.tts_backend == "edge" and not args.resume


def test_chatterbox_requires_reference_voice():
    assert main(["--video", "x.mp4", "--tts-backend", "chatterbox"]) == 2


def test_missing_video_fails_cleanly():
    assert main(["--video", "does_not_exist.mp4"]) == 1
