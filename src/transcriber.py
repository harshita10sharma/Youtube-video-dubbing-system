import json
from pathlib import Path

from faster_whisper import WhisperModel

from src.logger import log

MODEL_SIZE = "medium"  # "base" is too weak to reliably pick Devanagari over Urdu script

# This Devanagari sample text "primes" the decoder to continue writing
# in Devanagari script instead of drifting into Urdu/Perso-Arabic script.
# It doesn't have to match the video's actual content - it's just there
# to bias the model's script choice.
HINDI_SCRIPT_PROMPT = (
    "यह एक हिंदी भाषण है। यह कहानी, ज़िंदगी, दुनिया, समझ, "
    "दोस्तों, बातचीत, और लोगों के बारे में है।"
)
def transcribe_audio(audio_path: str):
    Path("data/transcripts").mkdir(parents=True, exist_ok=True)

    log(f"Loading Faster-Whisper model: {MODEL_SIZE}")

    model = WhisperModel(MODEL_SIZE, compute_type="int8")

    log("Starting transcription...")

    segments, info = model.transcribe(
    audio_path,
    beam_size=5,
    language="hi",
    task="transcribe",
    vad_filter=True,
    initial_prompt=HINDI_SCRIPT_PROMPT,
    condition_on_previous_text=False,
)

    transcript_data = []

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        transcript_data.append(
            {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": text,
            }
        )
        print(f"      [{segment.start:7.1f}s -> {segment.end:7.1f}s] {text}")

    output_path = "data/transcripts/transcript.json"

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(transcript_data, file, ensure_ascii=False, indent=2)

    log(f"Detected language: {info.language}")
    log(f"Transcript saved -> {output_path}")

    return transcript_data, info.language