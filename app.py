"""
app.py
------
Main entry point for the Automated Video Dubbing System.

Pipeline:
1. Download YouTube video
2. Extract audio
3. Transcribe speech and detect source language
4. Translate transcript into English
5. Generate English speech
6. Align generated speech to original timestamps
7. Replace original video audio
8. Save final dubbed video

Usage
-----
    python app.py                      # prompts for a YouTube URL
    python app.py --url "https://www.youtube.com/watch?v=XXXX"
    python app.py --video data/videos/source.mp4 --resume
    python app.py --video data/videos/source.mp4 \
        --tts-backend chatterbox --reference-voice data/audio/reference.wav

Heavy dependencies (Whisper, IndicTrans2, Chatterbox) are imported only
when the stage that needs them runs.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from src.logger import log, log_error, log_success

TRANSLATED_PATH = Path("data/transcripts/translated.json")
LANGUAGE_PATH = Path("data/transcripts/language.txt")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dub a YouTube video into English."
    )

    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--url",
        help="YouTube URL to download and dub (prompted for if omitted).",
    )
    source.add_argument("--video", help="Path to an existing local video.")

    parser.add_argument(
        "--tts-backend",
        choices=["edge", "chatterbox"],
        default="edge",
        help="edge = stock voice (default); chatterbox = voice cloning (GPU).",
    )
    parser.add_argument(
        "--reference-voice",
        help="Reference WAV for the chatterbox backend.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse transcript/translation/TTS clips from a previous run.",
    )

    return parser


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_pipeline(args):
    """Run all stages. Returns (final_video_path, source_language)."""

    from src.audio_extractor import extract_audio
    from src.ffmpeg_utils import get_media_duration

    # Step 1: video -------------------------------------------------
    if args.url:
        from src.downloader import download_video

        log("STEP 1/7: Downloading video...")
        video_path = download_video(args.url)
    else:
        video_path = args.video
        log(f"STEP 1/7: Using local video {video_path}")

        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

    # Step 2: audio -------------------------------------------------
    log("STEP 2/7: Extracting audio...")
    audio_path = extract_audio(video_path)

    # Steps 3-4: transcript + translation ---------------------------
    if args.resume and TRANSLATED_PATH.exists() and LANGUAGE_PATH.exists():
        log("STEP 3-4/7: Resuming - reusing existing translation.")
        segments = _load_json(TRANSLATED_PATH)
        source_language = LANGUAGE_PATH.read_text(encoding="utf-8").strip()
    else:
        from src.transcriber import transcribe_audio
        from src.translator import translate_segments

        log("STEP 3/7: Transcribing audio...")
        transcript, source_language = transcribe_audio(audio_path)

        if not transcript:
            raise RuntimeError("No speech was detected in the video.")

        LANGUAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        LANGUAGE_PATH.write_text(source_language, encoding="utf-8")

        log(f"STEP 4/7: Translating from '{source_language}' to English...")
        segments = translate_segments(transcript, source_language)

        if not segments:
            raise RuntimeError("Translation produced no segments.")

    # Step 5: speech ------------------------------------------------
    from src.tts_engine import create_tts_files

    log("STEP 5/7: Generating English speech...")
    segments = create_tts_files(
        segments,
        backend=args.tts_backend,
        reference_voice=args.reference_voice,
        overwrite=not args.resume,
    )

    if not any(s.get("tts_path") for s in segments):
        raise RuntimeError("No TTS audio files were generated.")

    # Step 6: timeline ----------------------------------------------
    from src.merger import merge_tts_audio

    log("STEP 6/7: Aligning English speech to original timeline...")
    dubbed_audio = merge_tts_audio(segments, get_media_duration(video_path))

    # Step 7: mux ---------------------------------------------------
    from src.video_merger import merge_audio_with_video

    log("STEP 7/7: Creating final dubbed video...")
    final_video = merge_audio_with_video(video_path, dubbed_audio)

    return final_video, source_language


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.tts_backend == "chatterbox" and not args.reference_voice:
        log_error("--reference-voice is required with --tts-backend chatterbox")
        return 2

    if not args.url and not args.video:
        print("=" * 70)
        print("        AUTOMATED VIDEO DUBBING SYSTEM")
        print("=" * 70)
        args.url = input("\nEnter YouTube URL: ").strip()

        if not args.url:
            log_error("No YouTube URL provided.")
            return 2

    start_time = time.time()

    try:
        final_video, language = run_pipeline(args)
    except Exception as e:
        log_error(f"Pipeline failed: {e}")
        print(
            f"\nProcessing time before failure: "
            f"{(time.time() - start_time) / 60:.2f} minutes"
        )
        return 1

    print("\n" + "=" * 70)
    log_success("VIDEO DUBBING COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"\nSource language : {language}")
    print(f"Final video     : {final_video}")
    print(f"Processing time : {(time.time() - start_time) / 60:.2f} minutes")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
