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
"""

import subprocess
import time

from src.audio_extractor import extract_audio
from src.downloader import download_video
from src.ffmpeg_utils import get_ffprobe_path
from src.logger import log, log_error, log_success
from src.merger import merge_tts_audio
from src.transcriber import transcribe_audio
from src.translator import translate_segments
from src.tts_engine import create_tts_files
from src.video_merger import merge_audio_with_video


def main():
    print("=" * 70)
    print("        AUTOMATED VIDEO DUBBING SYSTEM")
    print("=" * 70)

    url = input("\nEnter YouTube URL: ").strip()

    if not url:
        log_error("No YouTube URL provided.")
        return

    start_time = time.time()

    try:
        # ---------------------------------------------------------
        # Step 1: Download video
        # ---------------------------------------------------------
        log("STEP 1/7: Downloading video...")
        video_path = download_video(url)

        # ---------------------------------------------------------
        # Step 2: Extract audio
        # ---------------------------------------------------------
        log("STEP 2/7: Extracting audio...")
        audio_path = extract_audio(video_path)

        # ---------------------------------------------------------
        # Step 3: Transcribe + detect language
        # ---------------------------------------------------------
        log("STEP 3/7: Transcribing audio...")
        transcript_segments, source_language = transcribe_audio(audio_path)

        if not transcript_segments:
            raise RuntimeError("No speech was detected in the video.")

        # ---------------------------------------------------------
        # Step 4: Translate to English
        # ---------------------------------------------------------
        log(
            f"STEP 4/7: Translating from "
            f"'{source_language}' to English..."
        )

        translated_segments = translate_segments(
            transcript_segments,
            source_language,
        )

        if not translated_segments:
            raise RuntimeError("Translation produced no segments.")

        # ---------------------------------------------------------
        # Step 5: Generate English TTS
        # ---------------------------------------------------------
        log("STEP 5/7: Generating English speech...")
        tts_segments = create_tts_files(translated_segments)

        successful_tts = [
            segment
            for segment in tts_segments
            if segment.get("tts_path")
        ]

        if not successful_tts:
            raise RuntimeError("No TTS audio files were generated.")

        # ---------------------------------------------------------
        # Step 6: Create synchronized English audio timeline
        # ---------------------------------------------------------
        log("STEP 6/7: Aligning English speech to original timeline...")

        duration_result = subprocess.run(
            [
                get_ffprobe_path(),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        video_duration = float(duration_result.stdout.strip())

        dubbed_audio_path = merge_tts_audio(
            tts_segments,
            video_duration,
        )

        # ---------------------------------------------------------
        # Step 7: Replace original audio in video
        # ---------------------------------------------------------
        log("STEP 7/7: Creating final dubbed video...")

        final_video_path = merge_audio_with_video(
            video_path,
            dubbed_audio_path,
        )

        elapsed_time = time.time() - start_time

        print("\n" + "=" * 70)
        log_success("VIDEO DUBBING COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print(f"\nSource language : {source_language}")
        print(f"Final video     : {final_video_path}")
        print(f"Processing time : {elapsed_time / 60:.2f} minutes")
        print("=" * 70)

    except Exception as e:
        elapsed_time = time.time() - start_time

        log_error(f"Pipeline failed: {e}")
        print(f"\nProcessing time before failure: {elapsed_time / 60:.2f} minutes")
        raise


if __name__ == "__main__":
    main()