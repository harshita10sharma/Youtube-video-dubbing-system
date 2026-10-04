"""
tts_engine.py
-------------
Worker 5: converts translated English text into speech.

Two backends are available:
  - "edge"        : Microsoft Edge TTS, stock English voice (CPU, online).
  - "chatterbox"  : Chatterbox voice cloning from a reference WAV
                    (needs a GPU; this is what produced the final video).

Each translated segment is saved as a separate audio file.
The original timestamps are preserved so the files can later be
placed correctly on the final audio timeline.
"""

import asyncio
from pathlib import Path

import edge_tts

from src.logger import log, log_error


VOICE = "en-US-AriaNeural"

OUTPUT_DIR = Path("data/audio/tts")


_chatterbox_model = None


def _get_chatterbox():
    """Load Chatterbox once; imported lazily because it is heavy."""

    global _chatterbox_model

    if _chatterbox_model is None:
        import torch
        from chatterbox.tts import ChatterboxTTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        log(f"Loading Chatterbox model on {device}...")
        _chatterbox_model = ChatterboxTTS.from_pretrained(device=device)

    return _chatterbox_model


def _generate_chatterbox(
    text: str,
    output_path: str,
    reference_voice: str,
    attempts: int = 2,
):
    """
    Generate one cloned-voice clip. Chatterbox is stochastic and can
    occasionally fail or return an empty clip, so retry once.
    """

    import torch
    import torchaudio

    model = _get_chatterbox()

    for attempt in range(1, attempts + 1):
        try:
            wav = model.generate(text, audio_prompt_path=reference_voice)

            if wav.numel() == 0:
                raise RuntimeError("empty audio returned")

            torchaudio.save(output_path, wav.cpu(), model.sr)
            return

        except Exception:
            if attempt == attempts:
                raise
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


async def _generate_speech(text: str, output_path: str):
    """
    Generate one English speech clip using Edge TTS.
    """

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
    )

    await communicate.save(output_path)


def _generate_one(text: str, output_path: str):
    """
    Run the asynchronous Edge TTS generation.
    """

    asyncio.run(
        _generate_speech(
            text,
            output_path,
        )
    )


def create_tts_files(
    segments,
    backend: str = "edge",
    reference_voice: str = None,
    overwrite: bool = False,
):
    """
    Generate one English TTS audio file for every translated segment.

    backend         : "edge" or "chatterbox"
    reference_voice : WAV used for cloning (required for chatterbox)
    overwrite       : regenerate clips that already exist on disk

    The generated file path is stored in the segment as 'tts_path'.
    """

    if backend not in ("edge", "chatterbox"):
        raise ValueError(f"Unknown TTS backend: {backend!r}")

    if backend == "chatterbox" and not (
        reference_voice and Path(reference_voice).exists()
    ):
        raise FileNotFoundError(
            "Chatterbox backend needs an existing reference voice WAV "
            f"(got {reference_voice!r})."
        )

    extension = "mp3" if backend == "edge" else "wav"

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    log(
        f"Generating English speech for {len(segments)} segments..."
    )

    successful = 0

    for i, segment in enumerate(segments):

        text = segment.get("translated", "").strip()

        if not text:
            log_error(
                f"Skipping segment {i}: translated text is empty."
            )
            continue

        output_path = OUTPUT_DIR / f"seg_{i:04d}.{extension}"

        try:

            if output_path.exists() and not overwrite:
                pass  # resume: keep the clip from a previous run
            elif backend == "chatterbox":
                _generate_chatterbox(
                    text,
                    str(output_path),
                    reference_voice,
                )
            else:
                _generate_one(
                    text,
                    str(output_path),
                )

            segment["tts_path"] = str(output_path)

            successful += 1

            print(
                f"      [{i + 1}/{len(segments)}] "
                f"TTS created -> {output_path}"
            )

        except Exception as e:

            log_error(
                f"TTS failed for segment {i}: {e}"
            )

    log(
        f"TTS generation complete: "
        f"{successful}/{len(segments)} files created."
    )

    return segments